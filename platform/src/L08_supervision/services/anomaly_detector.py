"""
L08 Supervision Layer - Anomaly Detector

Statistical anomaly detection using Z-score and IQR ensemble methods
with rolling baseline computation.
"""

import statistics
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from collections import deque

from ..models.domain import (
    Anomaly,
    AnomalySeverity,
    BaselineStats,
)
from ..models.config import SupervisionConfiguration
from ..models.error_codes import ErrorCodes, AnomalyError
from ..integration.l01_bridge import L08Bridge
from .audit_manager import AuditManager

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """
    Statistical anomaly detector using Z-score and IQR ensemble.

    Features:
    - Rolling baseline computation (30-day window)
    - Z-score detection (3σ threshold)
    - IQR (Interquartile Range) detection
    - Ensemble method for higher confidence
    - Severity classification based on deviation
    """

    def __init__(
        self,
        l01_bridge: L08Bridge,
        audit_manager: AuditManager,
        config: SupervisionConfiguration
    ):
        """
        Initialize Anomaly Detector.

        Args:
            l01_bridge: L01 bridge for persistence
            audit_manager: Audit manager for logging
            config: Supervision configuration
        """
        self.l01 = l01_bridge
        self.audit = audit_manager
        self.config = config

        # Baseline statistics per agent+metric
        self._baselines: Dict[str, BaselineStats] = {}

        # Detected anomalies (in memory + persisted to L01)
        self._anomalies: List[Anomaly] = []

        # Metrics
        self._detection_count: int = 0
        self._anomaly_count: int = 0

        logger.info("AnomalyDetector initialized")

    async def initialize(self) -> None:
        """Initialize anomaly detector"""
        logger.info("AnomalyDetector ready")

    async def record_observation(
        self,
        agent_id: str,
        metric_name: str,
        value: float
    ) -> None:
        """
        Record an observation and update the rolling baseline.

        Args:
            agent_id: Agent identifier
            metric_name: Name of the metric being observed
            value: Observed value
        """
        key = f"{agent_id}:{metric_name}"

        if key not in self._baselines:
            self._baselines[key] = BaselineStats(
                values=deque(maxlen=self.config.baseline_sample_size)
            )

        baseline = self._baselines[key]
        baseline.values.append(value)
        baseline.sample_count = len(baseline.values)
        baseline.last_updated = datetime.utcnow()

        # Recompute statistics if enough samples
        if len(baseline.values) >= self.config.min_baseline_samples:
            self._recompute_baseline_stats(baseline)

    def _recompute_baseline_stats(self, baseline: BaselineStats) -> None:
        """Recompute statistical measures for baseline"""
        values = list(baseline.values)

        baseline.mean = statistics.mean(values)
        baseline.std = statistics.stdev(values) if len(values) > 1 else 0.0
        baseline.min_val = min(values)
        baseline.max_val = max(values)

        # Compute quartiles for IQR
        if len(values) >= 4:
            quantiles = statistics.quantiles(values, n=4)
            baseline.q1 = quantiles[0]
            baseline.q3 = quantiles[2]
        else:
            baseline.q1 = baseline.mean
            baseline.q3 = baseline.mean

    async def detect(
        self,
        agent_id: str,
        metric_name: str,
        value: float
    ) -> Tuple[List[Anomaly], Optional[str]]:
        """
        Detect anomalies using Z-score and IQR ensemble.

        Args:
            agent_id: Agent identifier
            metric_name: Name of the metric
            value: Observed value to check

        Returns:
            Tuple of (list of detected anomalies, error message)
        """
        self._detection_count += 1
        key = f"{agent_id}:{metric_name}"

        baseline = self._baselines.get(key)

        if not baseline or baseline.sample_count < self.config.min_baseline_samples:
            return [], f"{ErrorCodes.INSUFFICIENT_BASELINE_DATA.value}: Need at least {self.config.min_baseline_samples} samples"

        anomalies = []
        detection_methods = []

        # Z-score detection
        z_score = 0.0
        if baseline.std > 0:
            z_score = abs(value - baseline.mean) / baseline.std
            if z_score > self.config.z_score_threshold:
                detection_methods.append("z_score")

        # IQR detection
        iqr = baseline.q3 - baseline.q1
        iqr_score = 0.0
        lower_bound = baseline.q1 - (self.config.iqr_multiplier * iqr)
        upper_bound = baseline.q3 + (self.config.iqr_multiplier * iqr)

        if iqr > 0:
            if value < lower_bound:
                iqr_score = abs(value - lower_bound) / iqr
                detection_methods.append("iqr")
            elif value > upper_bound:
                iqr_score = abs(value - upper_bound) / iqr
                detection_methods.append("iqr")

        # Create anomaly if any method detected
        if detection_methods:
            # Determine severity based on deviation
            severity = self._classify_severity(z_score, iqr_score, len(detection_methods))

            # Determine confidence based on ensemble agreement
            confidence = 0.5 + (0.25 * len(detection_methods))  # 0.5-1.0 range

            anomaly = Anomaly(
                agent_id=agent_id,
                metric_name=metric_name,
                anomaly_type=f"{metric_name}_deviation",
                severity=severity,
                description=self._generate_description(
                    metric_name, value, baseline, z_score, detection_methods
                ),
                baseline_value=baseline.mean,
                observed_value=value,
                z_score=z_score,
                iqr_score=iqr_score,
                detection_method="+".join(detection_methods) if len(detection_methods) > 1 else detection_methods[0],
                confidence=confidence,
                detected_at=datetime.utcnow(),
            )

            # Store anomaly
            self._anomalies.append(anomaly)
            await self.l01.store_anomaly(anomaly.to_dict())
            self._anomaly_count += 1

            # Log to audit
            await self.audit.log_anomaly_detected(
                anomaly_id=anomaly.anomaly_id,
                agent_id=agent_id,
                metric_name=metric_name,
                severity=severity.value,
                z_score=z_score,
            )

            anomalies.append(anomaly)

            logger.info(
                f"Anomaly detected: {anomaly.anomaly_id} "
                f"(agent={agent_id}, metric={metric_name}, severity={severity.value})"
            )

        return anomalies, None

    def _classify_severity(
        self,
        z_score: float,
        iqr_score: float,
        methods_count: int
    ) -> AnomalySeverity:
        """
        Classify anomaly severity based on deviation scores.

        Severity levels:
        - CRITICAL: z_score > 5 or both methods detect with high scores
        - HIGH: z_score > 3 (3σ threshold exceeded)
        - MEDIUM: 1 < z_score <= 3
        - LOW: z_score <= 1 or single method with low score
        """
        # Ensemble: If both methods detect with high scores, increase severity
        if methods_count >= 2 and (z_score > 4 or iqr_score > 2):
            return AnomalySeverity.CRITICAL

        if z_score > 5:
            return AnomalySeverity.CRITICAL
        elif z_score > 3:
            return AnomalySeverity.HIGH
        elif z_score > 1:
            return AnomalySeverity.MEDIUM
        else:
            return AnomalySeverity.LOW

    def _generate_description(
        self,
        metric_name: str,
        value: float,
        baseline: BaselineStats,
        z_score: float,
        methods: List[str]
    ) -> str:
        """Generate human-readable anomaly description"""
        deviation_pct = ((value - baseline.mean) / max(baseline.mean, 0.001)) * 100

        direction = "above" if value > baseline.mean else "below"

        desc = (
            f"{metric_name} value {value:.2f} is {abs(deviation_pct):.1f}% {direction} "
            f"baseline ({baseline.mean:.2f}). "
            f"Detection: {', '.join(methods)} (z-score={z_score:.2f})"
        )

        return desc

    async def acknowledge_anomaly(
        self,
        anomaly_id: str,
        acknowledged_by: str,
        notes: str = ""
    ) -> Tuple[Optional[Anomaly], Optional[str]]:
        """
        Acknowledge an anomaly.

        Args:
            anomaly_id: Anomaly ID to acknowledge
            acknowledged_by: User acknowledging the anomaly
            notes: Optional notes

        Returns:
            Tuple of (updated anomaly, error message)
        """
        try:
            # Find anomaly
            anomaly = None
            for a in self._anomalies:
                if a.anomaly_id == anomaly_id:
                    anomaly = a
                    break

            if not anomaly:
                return None, f"{ErrorCodes.ANOMALY_NOT_FOUND.value}: Anomaly {anomaly_id} not found"

            anomaly.acknowledged = True
            anomaly.acknowledged_by = acknowledged_by
            anomaly.acknowledged_at = datetime.utcnow()

            # Log to audit
            await self.audit.log_action(
                action="anomaly_acknowledged",
                actor_id=acknowledged_by,
                actor_type="user",
                resource_type="anomaly",
                resource_id=anomaly_id,
                details={"notes": notes},
            )

            logger.info(f"Anomaly {anomaly_id} acknowledged by {acknowledged_by}")
            return anomaly, None

        except Exception as e:
            logger.error(f"Failed to acknowledge anomaly: {e}")
            return None, str(e)

    async def set_baseline(
        self,
        agent_id: str,
        metric_name: str,
        values: List[float]
    ) -> Tuple[bool, Optional[str]]:
        """
        Set baseline from historical values.

        Args:
            agent_id: Agent identifier
            metric_name: Metric name
            values: Historical values for baseline

        Returns:
            Tuple of (success, error message)
        """
        if len(values) < self.config.min_baseline_samples:
            return False, (
                f"{ErrorCodes.INSUFFICIENT_BASELINE_DATA.value}: "
                f"Need at least {self.config.min_baseline_samples} samples, got {len(values)}"
            )

        key = f"{agent_id}:{metric_name}"
        baseline = BaselineStats(
            values=deque(values, maxlen=self.config.baseline_sample_size)
        )
        baseline.sample_count = len(values)
        self._recompute_baseline_stats(baseline)

        self._baselines[key] = baseline

        logger.info(
            f"Set baseline for {key}: mean={baseline.mean:.2f}, std={baseline.std:.2f}"
        )
        return True, None

    def get_baseline(
        self,
        agent_id: str,
        metric_name: str
    ) -> Optional[BaselineStats]:
        """Get baseline for an agent+metric"""
        key = f"{agent_id}:{metric_name}"
        return self._baselines.get(key)

    async def get_anomalies(
        self,
        agent_id: Optional[str] = None,
        severity: Optional[AnomalySeverity] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 100
    ) -> List[Anomaly]:
        """Get anomalies with filters"""
        results = self._anomalies

        if agent_id:
            results = [a for a in results if a.agent_id == agent_id]
        if severity:
            results = [a for a in results if a.severity == severity]
        if acknowledged is not None:
            results = [a for a in results if a.acknowledged == acknowledged]

        # Sort by detected_at descending
        results = sorted(results, key=lambda a: a.detected_at, reverse=True)

        return results[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """Get anomaly detector statistics"""
        severity_counts = {
            "critical": len([a for a in self._anomalies if a.severity == AnomalySeverity.CRITICAL]),
            "high": len([a for a in self._anomalies if a.severity == AnomalySeverity.HIGH]),
            "medium": len([a for a in self._anomalies if a.severity == AnomalySeverity.MEDIUM]),
            "low": len([a for a in self._anomalies if a.severity == AnomalySeverity.LOW]),
        }

        return {
            "detection_count": self._detection_count,
            "anomaly_count": self._anomaly_count,
            "anomaly_rate": self._anomaly_count / max(1, self._detection_count),
            "baselines_tracked": len(self._baselines),
            "unacknowledged": len([a for a in self._anomalies if not a.acknowledged]),
            "severity_counts": severity_counts,
        }

    async def health_check(self) -> Dict[str, Any]:
        """Health check for anomaly detector"""
        return {
            "status": "healthy",
            "stats": self.get_stats(),
            "config": {
                "z_score_threshold": self.config.z_score_threshold,
                "iqr_multiplier": self.config.iqr_multiplier,
                "min_baseline_samples": self.config.min_baseline_samples,
            }
        }

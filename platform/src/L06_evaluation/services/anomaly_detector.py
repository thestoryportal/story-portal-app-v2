"""Anomaly detector using z-score based statistical detection"""

import asyncio
import logging
from datetime import datetime, timedelta, UTC
from typing import Optional

from ..models.anomaly import Anomaly, AnomalySeverity, Baseline
from ..models.quality_score import QualityScore
from ..models.error_codes import ErrorCode
from .cache_manager import CacheManager

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """
    Detects statistical anomalies using z-score.

    Per spec Section 3.2 (Component Responsibilities #5):
    - Z-score based detection
    - Baseline training period (1-2 hours)
    - Configurable deviation threshold (default 3.0)
    - Cold-start handling
    """

    def __init__(
        self,
        cache_manager: Optional[CacheManager] = None,
        deviation_threshold: float = 3.0,
        baseline_window_hours: int = 24,
        cold_start_samples: int = 100,
    ):
        """
        Initialize anomaly detector.

        Args:
            cache_manager: CacheManager for baseline storage (optional)
            deviation_threshold: Z-score threshold for anomaly (default: 3.0)
            baseline_window_hours: Hours of data for baseline (default: 24)
            cold_start_samples: Minimum samples before baseline established (default: 100)
        """
        self.cache = cache_manager
        self.threshold = deviation_threshold
        self.baseline_window_hours = baseline_window_hours
        self.cold_start_samples = cold_start_samples
        self._initialized = False

        # In-memory baseline cache
        self._baselines: dict[str, Baseline] = {}

        # Statistics
        self.anomalies_detected = 0
        self.baselines_trained = 0

    async def initialize(self):
        """Initialize anomaly detector."""
        if self._initialized:
            return

        # Load baselines from cache if available
        if self.cache:
            # TODO: Load baselines from cache
            pass

        self._initialized = True
        logger.info("AnomalyDetector initialized")

    async def cleanup(self):
        """Cleanup anomaly detector resources."""
        # Save baselines to cache if available
        if self.cache:
            # TODO: Save baselines to cache
            pass

        self._baselines.clear()
        self._initialized = False
        logger.info("AnomalyDetector cleaned up")

    async def detect(self, score: QualityScore) -> Optional[Anomaly]:
        """
        Detect anomaly in quality score.

        Args:
            score: QualityScore to check

        Returns:
            Anomaly if detected, None otherwise
        """
        try:
            metric_name = f"quality_score:{score.agent_id}"

            # Get baseline
            baseline = await self._get_baseline(metric_name)

            if not baseline or not baseline.is_established(self.cold_start_samples):
                # Still in cold-start, update baseline and return None
                await self._update_baseline(metric_name, score.overall_score)
                logger.debug(f"Cold-start: updating baseline for {metric_name}")
                return None

            # Calculate z-score
            z_score = baseline.calculate_z_score(score.overall_score)

            # Check if anomaly
            if z_score >= self.threshold:
                # Anomaly detected!
                severity = Anomaly.determine_severity(z_score)

                anomaly = Anomaly(
                    anomaly_id="",  # Auto-generated
                    metric_name=metric_name,
                    severity=severity,
                    baseline_value=baseline.mean,
                    current_value=score.overall_score,
                    z_score=z_score,
                    detected_at=score.timestamp,
                    agent_id=score.agent_id,
                    tenant_id=score.tenant_id,
                )

                self.anomalies_detected += 1
                logger.warning(
                    f"Anomaly detected: {metric_name} z-score={z_score:.2f} "
                    f"(baseline={baseline.mean:.1f}, current={score.overall_score:.1f})"
                )

                return anomaly

            # No anomaly, update baseline with new data point
            await self._update_baseline(metric_name, score.overall_score)

            return None

        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return None

    async def _get_baseline(self, metric_name: str) -> Optional[Baseline]:
        """Get baseline from cache or memory"""
        # Check memory first
        if metric_name in self._baselines:
            return self._baselines[metric_name]

        # Check cache
        if self.cache:
            cached = await self.cache.get_baseline(metric_name)
            if cached:
                baseline = Baseline.from_dict(cached)
                self._baselines[metric_name] = baseline
                return baseline

        return None

    async def _update_baseline(self, metric_name: str, value: float):
        """Update baseline with new value"""
        baseline = await self._get_baseline(metric_name)

        if baseline is None:
            # Create new baseline
            baseline = Baseline(
                metric_name=metric_name,
                mean=value,
                stddev=0.0,
                sample_count=1,
                last_updated=datetime.now(UTC),
                window_hours=self.baseline_window_hours,
            )
            self._baselines[metric_name] = baseline
            self.baselines_trained += 1
        else:
            # Update existing baseline (running statistics)
            n = baseline.sample_count
            old_mean = baseline.mean

            # Welford's online algorithm for mean and variance
            new_mean = old_mean + (value - old_mean) / (n + 1)
            new_m2 = (baseline.stddev ** 2) * n + (value - old_mean) * (value - new_mean)
            new_stddev = (new_m2 / (n + 1)) ** 0.5 if n > 0 else 0.0

            baseline.mean = new_mean
            baseline.stddev = new_stddev
            baseline.sample_count += 1
            baseline.last_updated = datetime.utcnow()

        # Cache updated baseline
        if self.cache:
            await self.cache.set_baseline(metric_name, baseline.to_dict(), ttl=3600)

    async def get_baseline(self, metric_name: str) -> Optional[Baseline]:
        """Public method to get baseline for metric"""
        return await self._get_baseline(metric_name)

    async def clear_baseline(self, metric_name: str):
        """Clear baseline for metric"""
        self._baselines.pop(metric_name, None)
        if self.cache:
            await self.cache.delete(f"baseline:{metric_name}")

    async def clear_all_baselines(self):
        """Clear all baselines"""
        self._baselines.clear()
        if self.cache:
            await self.cache.clear("baseline:*")

    def get_statistics(self) -> dict:
        """Get anomaly detector statistics"""
        return {
            "anomalies_detected": self.anomalies_detected,
            "baselines_trained": self.baselines_trained,
            "baselines_in_memory": len(self._baselines),
            "deviation_threshold": self.threshold,
            "cold_start_samples": self.cold_start_samples,
        }

    def reset_statistics(self):
        """Reset statistics counters"""
        self.anomalies_detected = 0
        self.baselines_trained = 0

"""
L06 Evaluation Layer - L01 Data Layer Bridge

Bridge between L06 Evaluation Layer and L01 Data Layer for persistent evaluation tracking.

This bridge records evaluation activities in L01 for monitoring, analytics, and long-term
quality tracking across the platform.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from ...L01_data_layer.client import L01Client
from ..models.quality_score import QualityScore
from ..models.metric import MetricPoint
from ..models.anomaly import Anomaly
from ..models.compliance import ComplianceResult
from ..models.alert import Alert


logger = logging.getLogger(__name__)


class L06Bridge:
    """
    Bridge between L06 Evaluation Layer and L01 Data Layer.

    Responsibilities:
    - Record quality scores with multi-dimensional evaluation
    - Track time-series metrics with Prometheus-style labels
    - Record detected anomalies with z-score and baseline
    - Store compliance results with violations
    - Track alert delivery status
    """

    def __init__(self, l01_base_url: str = "http://localhost:8002"):
        """Initialize L06 bridge.

        Args:
            l01_base_url: Base URL for L01 Data Layer API
        """
        self.l01_client = L01Client(base_url=l01_base_url)
        self.enabled = True
        logger.info(f"L06Bridge initialized with base_url={l01_base_url}")

    async def initialize(self) -> None:
        """Initialize bridge (async setup if needed)."""
        logger.info("L06Bridge initialized")

    async def record_quality_score(
        self,
        score: QualityScore,
        agent_id: Optional[str] = None
    ) -> bool:
        """Record a quality score in L01.

        Args:
            score: QualityScore instance to record
            agent_id: Optional UUID of agent (if known)

        Returns:
            True if recorded successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            # Serialize dimensions to dict format
            dimensions_dict = {}
            for dim_name, dim_score in score.dimensions.items():
                dimensions_dict[dim_name] = {
                    "dimension": dim_score.dimension,
                    "score": dim_score.score,
                    "weight": dim_score.weight,
                    "raw_metrics": dim_score.raw_metrics
                }

            # Record in L01
            await self.l01_client.record_quality_score(
                score_id=score.score_id,
                agent_did=score.agent_id,  # Note: score.agent_id is actually agent_did in L06
                tenant_id=score.tenant_id,
                timestamp=score.timestamp.isoformat(),
                overall_score=score.overall_score,
                assessment=score.assessment.value,
                dimensions=dimensions_dict,
                agent_id=agent_id,
                data_completeness=score.data_completeness,
                cached=score.cached,
                metadata={}
            )

            logger.info(
                f"Recorded quality score {score.score_id} in L01 "
                f"(overall={score.overall_score:.4f}, assessment={score.assessment.value})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to record quality score in L01: {e}")
            return False

    async def record_metric(
        self,
        metric: MetricPoint,
        agent_id: Optional[str] = None
    ) -> bool:
        """Record a metric point in L01.

        Args:
            metric: MetricPoint instance to record
            agent_id: Optional UUID of agent (if known)

        Returns:
            True if recorded successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            # Extract tenant_id from labels if present
            tenant_id = metric.labels.get("tenant_id")

            await self.l01_client.record_metric(
                metric_name=metric.metric_name,
                value=metric.value,
                timestamp=metric.timestamp.isoformat(),
                metric_type=metric.metric_type.value,
                labels=metric.labels,
                agent_id=agent_id,
                tenant_id=tenant_id
            )

            logger.info(
                f"Recorded metric {metric.metric_name}={metric.value} in L01"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to record metric in L01: {e}")
            return False

    async def record_anomaly(
        self,
        anomaly: Anomaly,
        agent_id: Optional[str] = None
    ) -> bool:
        """Record a detected anomaly in L01.

        Args:
            anomaly: Anomaly instance to record
            agent_id: Optional UUID of agent (if known)

        Returns:
            True if recorded successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            await self.l01_client.record_anomaly(
                anomaly_id=anomaly.anomaly_id,
                metric_name=anomaly.metric_name,
                severity=anomaly.severity.value,
                baseline_value=anomaly.baseline_value,
                current_value=anomaly.current_value,
                z_score=anomaly.z_score,
                detected_at=anomaly.detected_at.isoformat(),
                agent_id=agent_id,
                agent_did=anomaly.agent_id,
                tenant_id=anomaly.tenant_id,
                deviation_percent=anomaly.deviation_percent,
                confidence=anomaly.confidence,
                status=anomaly.status,
                alert_sent=anomaly.alert_sent
            )

            logger.info(
                f"Recorded anomaly {anomaly.anomaly_id} in L01 "
                f"(metric={anomaly.metric_name}, severity={anomaly.severity.value}, "
                f"z_score={anomaly.z_score:.2f})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to record anomaly in L01: {e}")
            return False

    async def update_anomaly_status(
        self,
        anomaly_id: str,
        status: str,
        resolved_at: Optional[datetime] = None,
        alert_sent: Optional[bool] = None
    ) -> bool:
        """Update anomaly status in L01.

        Args:
            anomaly_id: Anomaly ID to update
            status: New status value
            resolved_at: Timestamp when anomaly was resolved
            alert_sent: Whether alert was sent

        Returns:
            True if updated successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            resolved_at_str = resolved_at.isoformat() if resolved_at else None

            await self.l01_client.update_anomaly_status(
                anomaly_id=anomaly_id,
                status=status,
                resolved_at=resolved_at_str,
                alert_sent=alert_sent
            )

            logger.info(f"Updated anomaly {anomaly_id} status to {status} in L01")
            return True

        except Exception as e:
            logger.error(f"Failed to update anomaly status in L01: {e}")
            return False

    async def record_compliance_result(
        self,
        result: ComplianceResult,
        agent_id: Optional[str] = None
    ) -> bool:
        """Record a compliance validation result in L01.

        Args:
            result: ComplianceResult instance to record
            agent_id: Optional UUID of agent (if known)

        Returns:
            True if recorded successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            # Serialize violations to dict format
            violations_list = [v.to_dict() for v in result.violations]

            # Serialize constraints to dict format
            constraints_list = [c.to_dict() for c in result.constraints_checked]

            await self.l01_client.record_compliance_result(
                result_id=result.result_id,
                execution_id=result.execution_id,
                agent_did=result.agent_id,
                tenant_id=result.tenant_id,
                timestamp=result.timestamp.isoformat(),
                compliant=result.compliant,
                violations=violations_list,
                constraints_checked=constraints_list,
                agent_id=agent_id
            )

            logger.info(
                f"Recorded compliance result {result.result_id} in L01 "
                f"(compliant={result.compliant}, violations={len(result.violations)})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to record compliance result in L01: {e}")
            return False

    async def record_alert(
        self,
        alert: Alert,
        agent_id: Optional[str] = None
    ) -> bool:
        """Record an alert in L01.

        Args:
            alert: Alert instance to record
            agent_id: Optional UUID of agent (if known)

        Returns:
            True if recorded successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            # Convert channels to string list
            channels = [c.value for c in alert.channels]

            await self.l01_client.record_alert(
                alert_id=alert.alert_id,
                timestamp=alert.timestamp.isoformat(),
                severity=alert.severity.value,
                alert_type=alert.type,
                metric=alert.metric,
                message=alert.message,
                channels=channels,
                agent_id=agent_id,
                agent_did=alert.agent_id,
                tenant_id=alert.tenant_id,
                metadata=alert.metadata
            )

            logger.info(
                f"Recorded alert {alert.alert_id} in L01 "
                f"(severity={alert.severity.value}, type={alert.type})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to record alert in L01: {e}")
            return False

    async def update_alert_delivery(
        self,
        alert_id: str,
        delivery_attempts: int,
        delivered: bool,
        last_attempt: Optional[datetime] = None
    ) -> bool:
        """Update alert delivery status in L01.

        Args:
            alert_id: Alert ID to update
            delivery_attempts: Number of delivery attempts
            delivered: Whether alert was delivered
            last_attempt: Timestamp of last delivery attempt

        Returns:
            True if updated successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            last_attempt_str = last_attempt.isoformat() if last_attempt else None

            await self.l01_client.update_alert_delivery(
                alert_id=alert_id,
                delivery_attempts=delivery_attempts,
                delivered=delivered,
                last_attempt=last_attempt_str
            )

            logger.info(
                f"Updated alert {alert_id} delivery status in L01 "
                f"(attempts={delivery_attempts}, delivered={delivered})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to update alert delivery in L01: {e}")
            return False

    async def cleanup(self) -> None:
        """Cleanup bridge resources."""
        try:
            await self.l01_client.close()
            logger.info("L06Bridge cleanup complete")
        except Exception as e:
            logger.warning(f"L06Bridge cleanup failed: {e}")

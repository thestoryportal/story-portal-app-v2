"""Main evaluation service orchestrator"""

import asyncio
import logging
from datetime import datetime, timedelta, UTC
from typing import List, Optional, Dict, Any

from ..models.cloud_event import CloudEvent
from ..models.quality_score import QualityScore
from ..models.anomaly import Anomaly
from ..models.alert import Alert
from .event_validator import EventValidator, ValidationError
from .deduplication_engine import DeduplicationEngine
from .metrics_engine import MetricsEngine
from .quality_scorer import QualityScorer
from .anomaly_detector import AnomalyDetector
from .compliance_validator import ComplianceValidator
from .alert_manager import AlertManager
from .storage_manager import StorageManager
from .cache_manager import CacheManager
from .config_manager import ConfigManager
from .audit_logger import AuditLogger
from .query_engine import QueryEngine
from .l01_bridge import L06Bridge

logger = logging.getLogger(__name__)


class EvaluationService:
    """
    Main orchestrator for L06 Evaluation Layer.

    Coordinates all evaluation components:
    1. Event validation
    2. Deduplication
    3. Metrics ingestion
    4. Quality scoring
    5. Anomaly detection
    6. Compliance validation
    7. Alert routing
    8. Audit logging
    """

    def __init__(
        self,
        redis_client: Optional[any] = None,
        postgres_conn: Optional[any] = None,
        slack_webhook_url: Optional[str] = None,
        l01_bridge: Optional[L06Bridge] = None,
    ):
        """
        Initialize evaluation service.

        Args:
            redis_client: Redis client for caching (optional)
            postgres_conn: PostgreSQL connection for storage (optional)
            slack_webhook_url: Slack webhook for alerts (optional)
            l01_bridge: L06Bridge for L01 Data Layer integration (optional)
        """
        # Initialize managers
        self.cache = CacheManager(redis_client)
        self.storage = StorageManager(redis_client, postgres_conn)
        self.config = ConfigManager()
        self.audit = AuditLogger(postgres_conn)

        # Initialize L01 Data Layer bridge
        self.l01_bridge = l01_bridge or L06Bridge()

        # Initialize core services
        self.validator = EventValidator()
        self.dedup = DeduplicationEngine(redis_client)
        self.metrics = MetricsEngine(self.storage, self.cache)
        self.scorer = QualityScorer(self.metrics, None, self.cache)
        self.anomaly = AnomalyDetector(self.cache)
        self.compliance = ComplianceValidator(self.metrics)
        self.alerts = AlertManager(slack_webhook_url)
        self.query = QueryEngine(self.metrics, self.cache)

        self._initialized = False

    async def initialize(self):
        """Initialize service"""
        if self._initialized:
            return

        logger.info("Initializing L06 Evaluation Service")

        # Initialize L01 bridge
        await self.l01_bridge.initialize()

        # Initialize scorer (which creates scorers dict)
        await self.scorer.initialize()

        # Update scorer with compliance validator after scorers are created
        if "compliance" in self.scorer.scorers:
            self.scorer.scorers["compliance"].compliance_validator = self.compliance

        await self.audit.log("service.started", {"service": "L06_evaluation"})
        self._initialized = True

    async def process_event(self, event: CloudEvent) -> bool:
        """
        Process incoming CloudEvent.

        Pipeline:
        1. Validate event
        2. Check duplicate
        3. Ingest metrics
        4. Compute quality score
        5. Detect anomalies
        6. Send alerts if needed
        7. Write audit log

        Args:
            event: CloudEvent to process

        Returns:
            True if processed successfully
        """
        try:
            # 1. Validate event
            validated = await self.validator.validate(event)

            # 2. Check duplicate
            if await self.dedup.is_duplicate(validated):
                logger.debug(f"Duplicate event: {event.id}")
                return True  # Success (idempotent)

            # 3. Ingest metrics from event
            metrics = await self.metrics.ingest_from_event(validated)
            logger.debug(f"Ingested {len(metrics)} metrics from event {event.id}")

            # Record metrics in L01
            for metric in metrics:
                await self.l01_bridge.record_metric(metric)

            # 4. Compute quality score (if relevant event type)
            if event.type in ["task.completed", "agent.execution.finished"]:
                agent_id = event.data.get("agent_id", "unknown")
                tenant_id = event.data.get("tenant_id", "default")

                # Compute score for last hour
                end = datetime.now(UTC)
                start = end - timedelta(hours=1)

                try:
                    score = await self.scorer.compute_score(
                        agent_id, tenant_id, (start, end)
                    )

                    # Record quality score in L01
                    await self.l01_bridge.record_quality_score(score)

                    # 5. Detect anomalies
                    anomaly = await self.anomaly.detect(score)

                    # 6. Send alert if anomaly detected
                    if anomaly:
                        # Record anomaly in L01
                        await self.l01_bridge.record_anomaly(anomaly)

                        alert = Alert.from_anomaly(anomaly)

                        # Record alert in L01
                        await self.l01_bridge.record_alert(alert)

                        # Send alert to configured channels
                        await self.alerts.send_alert(alert)

                except Exception as e:
                    logger.error(f"Quality scoring failed: {e}")

            # 7. Write audit log
            await self.audit.log("event.processed", {
                "event_id": event.id,
                "event_type": event.type,
                "source": event.source,
            })

            return True

        except ValidationError as e:
            logger.warning(f"Event validation failed: {e.message}")
            await self.audit.log("event.validation_failed", {
                "event_id": event.id,
                "error": e.to_dict(),
            })
            return False

        except Exception as e:
            logger.error(f"Event processing failed: {e}")
            await self.audit.log("event.processing_failed", {
                "event_id": event.id,
                "error": str(e),
            })
            return False

    async def get_quality_scores(
        self,
        agent_id: str,
        start: datetime,
        end: datetime,
        tenant_id: str = "default",
    ) -> List[QualityScore]:
        """
        Query quality scores for agent.

        Args:
            agent_id: Agent identifier
            start: Start timestamp
            end: End timestamp
            tenant_id: Tenant identifier

        Returns:
            List of QualityScores
        """
        try:
            # For now, compute a single score for the entire window
            score = await self.scorer.compute_score(agent_id, tenant_id, (start, end))
            return [score]

        except Exception as e:
            logger.error(f"Quality score query failed: {e}")
            return []

    async def get_anomalies(
        self,
        start: datetime,
        end: datetime,
        agent_id: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> List[Anomaly]:
        """
        Query anomalies from L01.

        Args:
            start: Start timestamp
            end: End timestamp
            agent_id: Filter by agent (optional)
            severity: Filter by severity (optional)

        Returns:
            List of Anomalies
        """
        try:
            anomalies = await self.l01_bridge.get_anomalies(
                start=start,
                end=end,
                agent_id=agent_id,
                severity=severity
            )
            return anomalies
        except Exception as e:
            logger.error(f"Failed to get anomalies: {e}")
            return []

    async def aggregate_metrics(
        self,
        agent_id: str,
        metric_names: List[str],
        start: datetime,
        end: datetime,
        aggregation: str = "avg"
    ) -> Dict[str, float]:
        """
        Aggregate metrics for an agent.

        Args:
            agent_id: Agent identifier
            metric_names: List of metric names to aggregate
            start: Start timestamp
            end: End timestamp
            aggregation: Aggregation function (avg, sum, min, max, count)

        Returns:
            Dictionary of metric_name -> aggregated value
        """
        results = {}

        for metric_name in metric_names:
            try:
                value = await self.query.aggregate(
                    agent_id=agent_id,
                    metric_name=metric_name,
                    start=start,
                    end=end,
                    aggregation=aggregation
                )
                results[metric_name] = value
            except Exception as e:
                logger.warning(f"Failed to aggregate {metric_name}: {e}")
                results[metric_name] = 0.0

        return results

    async def get_agent_summary(
        self,
        agent_id: str,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get comprehensive summary for an agent.

        Args:
            agent_id: Agent identifier
            hours: Number of hours to look back

        Returns:
            Summary dictionary
        """
        end = datetime.now(UTC)
        start = end - timedelta(hours=hours)

        try:
            # Get quality score
            scores = await self.get_quality_scores(
                agent_id=agent_id,
                start=start,
                end=end
            )
            latest_score = scores[-1] if scores else None

            # Get anomalies
            anomalies = await self.get_anomalies(
                start=start,
                end=end,
                agent_id=agent_id
            )

            # Aggregate key metrics
            metrics = await self.aggregate_metrics(
                agent_id=agent_id,
                metric_names=[
                    "task_success_rate",
                    "avg_response_time_ms",
                    "error_rate",
                    "throughput"
                ],
                start=start,
                end=end
            )

            return {
                "agent_id": agent_id,
                "period_hours": hours,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "quality_score": latest_score.overall_score if latest_score else None,
                "quality_grade": latest_score.grade if latest_score else None,
                "anomaly_count": len(anomalies),
                "critical_anomalies": sum(
                    1 for a in anomalies if a.severity == "critical"
                ),
                "metrics": metrics,
            }

        except Exception as e:
            logger.error(f"Failed to get agent summary: {e}")
            return {
                "agent_id": agent_id,
                "error": str(e)
            }

    async def run_compliance_check(
        self,
        agent_id: str,
        tenant_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Run compliance check for an agent.

        Args:
            agent_id: Agent identifier
            tenant_id: Tenant identifier

        Returns:
            Compliance check results
        """
        try:
            result = await self.compliance.check_compliance(
                agent_id=agent_id,
                tenant_id=tenant_id
            )
            return result.to_dict() if hasattr(result, 'to_dict') else result
        except Exception as e:
            logger.error(f"Compliance check failed: {e}")
            return {"error": str(e), "compliant": False}

    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up L06 Evaluation Service")
        await self.audit.log("service.stopped", {"service": "L06_evaluation"})

    def get_statistics(self) -> dict:
        """Get service statistics"""
        return {
            "validator": {"events_processed": self.validator.__dict__.get("events_validated", 0)},
            "deduplication": self.dedup.get_statistics(),
            "metrics": self.metrics.get_statistics(),
            "quality_scorer": self.scorer.get_statistics(),
            "anomaly_detector": self.anomaly.get_statistics(),
            "compliance": self.compliance.get_statistics(),
            "alerts": self.alerts.get_statistics(),
            "storage": self.storage.get_statistics(),
            "cache": self.cache.get_statistics(),
            "audit": self.audit.get_statistics(),
        }

    def get_health_status(self) -> dict:
        """Get service health status"""
        return {
            "healthy": self._initialized,
            "initialized": self._initialized,
            "components": {
                "validator": True,
                "deduplication": True,
                "metrics_engine": True,
                "quality_scorer": True,
                "anomaly_detector": True,
                "compliance_validator": True,
                "alert_manager": True,
                "storage_manager": True,
                "cache_manager": True,
                "query_engine": True,
            },
            "l01_bridge_available": self.l01_bridge is not None,
        }

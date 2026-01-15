"""Main evaluation service orchestrator"""

import asyncio
import logging
from datetime import datetime, timedelta, UTC
from typing import List, Optional

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
    ):
        """
        Initialize evaluation service.

        Args:
            redis_client: Redis client for caching (optional)
            postgres_conn: PostgreSQL connection for storage (optional)
            slack_webhook_url: Slack webhook for alerts (optional)
        """
        # Initialize managers
        self.cache = CacheManager(redis_client)
        self.storage = StorageManager(redis_client, postgres_conn)
        self.config = ConfigManager()
        self.audit = AuditLogger(postgres_conn)

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

                    # 5. Detect anomalies
                    anomaly = await self.anomaly.detect(score)

                    # 6. Send alert if anomaly detected
                    if anomaly:
                        alert = Alert.from_anomaly(anomaly)
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
        Query anomalies.

        Args:
            start: Start timestamp
            end: End timestamp
            agent_id: Filter by agent (optional)
            severity: Filter by severity (optional)

        Returns:
            List of Anomalies
        """
        # Stub implementation - would query from database
        return []

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

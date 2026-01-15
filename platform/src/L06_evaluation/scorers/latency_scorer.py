"""Latency scorer for p95 latency vs target"""

import logging
from datetime import datetime

from .base import Scorer
from ..models.quality_score import DimensionScore
from ..models.metric import MetricAggregation

logger = logging.getLogger(__name__)


class LatencyScorer(Scorer):
    """
    Scores latency based on p95 latency vs target.

    Metrics used:
    - task_duration_seconds (p95)
    """

    def __init__(
        self,
        metrics_engine: any,
        weight: float = 0.25,
        target_latency_seconds: float = 5.0,
        max_latency_seconds: float = 30.0,
    ):
        """
        Initialize latency scorer.

        Args:
            metrics_engine: MetricsEngine for querying metrics
            weight: Weight for latency dimension (default: 0.25)
            target_latency_seconds: Target latency (default: 5s)
            max_latency_seconds: Maximum acceptable latency (default: 30s)
        """
        super().__init__("latency", weight)
        self.metrics_engine = metrics_engine
        self.target_latency = target_latency_seconds
        self.max_latency = max_latency_seconds

    async def compute_score(
        self,
        agent_id: str,
        tenant_id: str,
        time_window: tuple[datetime, datetime],
    ) -> DimensionScore:
        """Compute latency score"""
        try:
            start, end = time_window
            labels = {"agent_id": agent_id, "tenant_id": tenant_id}

            # Get p95 latency
            latency_metrics = await self.metrics_engine.query(
                metric_name="task_duration_seconds",
                start=start,
                end=end,
                labels=labels,
                aggregation=MetricAggregation.P95,
            )

            if not latency_metrics:
                # No data, return neutral score
                return self._create_dimension_score(
                    50.0,
                    {"error": "No latency data available"},
                )

            p95_latency = sum(m.value for m in latency_metrics) / len(latency_metrics)

            # Also get p50 and p99 for context
            p50_metrics = await self.metrics_engine.query(
                metric_name="task_duration_seconds",
                start=start,
                end=end,
                labels=labels,
                aggregation=MetricAggregation.P50,
            )
            p99_metrics = await self.metrics_engine.query(
                metric_name="task_duration_seconds",
                start=start,
                end=end,
                labels=labels,
                aggregation=MetricAggregation.P99,
            )

            p50_latency = sum(m.value for m in p50_metrics) / len(p50_metrics) if p50_metrics else 0
            p99_latency = sum(m.value for m in p99_metrics) / len(p99_metrics) if p99_metrics else 0

            # Calculate score (lower latency is better)
            score = self._linear_score(
                p95_latency,
                min_value=self.target_latency,
                max_value=self.max_latency,
                invert=True,  # Lower is better
            )

            raw_metrics = {
                "p50_latency_seconds": p50_latency,
                "p95_latency_seconds": p95_latency,
                "p99_latency_seconds": p99_latency,
                "target_latency_seconds": self.target_latency,
                "max_latency_seconds": self.max_latency,
            }

            return self._create_dimension_score(score, raw_metrics)

        except Exception as e:
            logger.error(f"Latency scoring failed: {e}")
            return self._create_dimension_score(
                50.0,
                {"error": str(e)},
            )

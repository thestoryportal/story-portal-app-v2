"""Reliability scorer for success rate and error rate"""

import logging
from datetime import datetime

from .base import Scorer
from ..models.quality_score import DimensionScore
from ..models.metric import MetricAggregation

logger = logging.getLogger(__name__)


class ReliabilityScorer(Scorer):
    """
    Scores reliability based on success rate and error rate.

    Metrics used:
    - task_completed_total{status=success/failure} (success rate)
    - errors_total (error rate)
    """

    def __init__(
        self,
        metrics_engine: any,
        weight: float = 0.2,
        target_success_rate: float = 0.99,
        max_error_rate: float = 0.1,
    ):
        """
        Initialize reliability scorer.

        Args:
            metrics_engine: MetricsEngine for querying metrics
            weight: Weight for reliability dimension (default: 0.2)
            target_success_rate: Target success rate (default: 0.99)
            max_error_rate: Maximum acceptable error rate (default: 0.1)
        """
        super().__init__("reliability", weight)
        self.metrics_engine = metrics_engine
        self.target_success_rate = target_success_rate
        self.max_error_rate = max_error_rate

    async def compute_score(
        self,
        agent_id: str,
        tenant_id: str,
        time_window: tuple[datetime, datetime],
    ) -> DimensionScore:
        """Compute reliability score"""
        try:
            start, end = time_window
            labels = {"agent_id": agent_id, "tenant_id": tenant_id}

            # Get success and failure counts
            success_metrics = await self.metrics_engine.query(
                metric_name="task_completed_total",
                start=start,
                end=end,
                labels={**labels, "status": "success"},
                aggregation=MetricAggregation.SUM,
            )

            failure_metrics = await self.metrics_engine.query(
                metric_name="task_completed_total",
                start=start,
                end=end,
                labels={**labels, "status": "failure"},
                aggregation=MetricAggregation.SUM,
            )

            success_count = sum(m.value for m in success_metrics) if success_metrics else 0
            failure_count = sum(m.value for m in failure_metrics) if failure_metrics else 0
            total_count = success_count + failure_count

            # Calculate success rate
            if total_count > 0:
                success_rate = success_count / total_count
            else:
                success_rate = 1.0  # No failures if no data

            # Get error count
            error_metrics = await self.metrics_engine.query(
                metric_name="errors_total",
                start=start,
                end=end,
                labels=labels,
                aggregation=MetricAggregation.SUM,
            )

            error_count = sum(m.value for m in error_metrics) if error_metrics else 0
            error_rate = error_count / total_count if total_count > 0 else 0.0

            # Calculate score based on success rate (70%) and error rate (30%)
            success_score = self._linear_score(
                success_rate,
                min_value=1.0 - self.max_error_rate,  # 0.9
                max_value=self.target_success_rate,  # 0.99
                invert=False,  # Higher is better
            )

            error_score = self._linear_score(
                error_rate,
                min_value=0.0,
                max_value=self.max_error_rate,
                invert=True,  # Lower is better
            )

            # Weighted combination
            score = (success_score * 0.7) + (error_score * 0.3)

            raw_metrics = {
                "success_count": success_count,
                "failure_count": failure_count,
                "error_count": error_count,
                "success_rate": success_rate,
                "error_rate": error_rate,
                "target_success_rate": self.target_success_rate,
            }

            return self._create_dimension_score(score, raw_metrics)

        except Exception as e:
            logger.error(f"Reliability scoring failed: {e}")
            return self._create_dimension_score(
                50.0,
                {"error": str(e)},
            )

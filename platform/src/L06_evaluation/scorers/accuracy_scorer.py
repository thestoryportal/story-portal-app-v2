"""Accuracy scorer for goal achievement and correctness"""

import logging
from datetime import datetime

from .base import Scorer
from ..models.quality_score import DimensionScore
from ..models.metric import MetricAggregation

logger = logging.getLogger(__name__)


class AccuracyScorer(Scorer):
    """
    Scores accuracy based on goal achievement and correctness.

    Metrics used:
    - task_completed_total{status=success} / task_completed_total (success rate)
    - goal_achievement_rate (if available)
    - correctness_score (if available)
    """

    def __init__(self, metrics_engine: any, weight: float = 0.3):
        """
        Initialize accuracy scorer.

        Args:
            metrics_engine: MetricsEngine for querying metrics
            weight: Weight for accuracy dimension (default: 0.3)
        """
        super().__init__("accuracy", weight)
        self.metrics_engine = metrics_engine

    async def compute_score(
        self,
        agent_id: str,
        tenant_id: str,
        time_window: tuple[datetime, datetime],
    ) -> DimensionScore:
        """Compute accuracy score"""
        try:
            start, end = time_window
            labels = {"agent_id": agent_id, "tenant_id": tenant_id}

            # Get success count
            success_metrics = await self.metrics_engine.query(
                metric_name="task_completed_total",
                start=start,
                end=end,
                labels={**labels, "status": "success"},
                aggregation=MetricAggregation.SUM,
            )

            # Get total count
            total_metrics = await self.metrics_engine.query(
                metric_name="task_completed_total",
                start=start,
                end=end,
                labels=labels,
                aggregation=MetricAggregation.SUM,
            )

            success_count = sum(m.value for m in success_metrics) if success_metrics else 0
            total_count = sum(m.value for m in total_metrics) if total_metrics else 0

            # Calculate success rate
            if total_count > 0:
                success_rate = success_count / total_count
            else:
                # No data available, return neutral score
                success_rate = 0.5

            # Convert success rate to score (0-100)
            # Success rate is already 0-1, so multiply by 100
            score = success_rate * 100.0

            raw_metrics = {
                "success_count": success_count,
                "total_count": total_count,
                "success_rate": success_rate,
            }

            # Try to get goal achievement rate if available
            goal_metrics = await self.metrics_engine.query(
                metric_name="goal_achievement_rate",
                start=start,
                end=end,
                labels=labels,
                aggregation=MetricAggregation.AVG,
            )

            if goal_metrics:
                goal_rate = sum(m.value for m in goal_metrics) / len(goal_metrics)
                raw_metrics["goal_achievement_rate"] = goal_rate
                # Blend with success rate (70% success, 30% goal achievement)
                score = (score * 0.7) + (goal_rate * 100.0 * 0.3)

            return self._create_dimension_score(score, raw_metrics)

        except Exception as e:
            logger.error(f"Accuracy scoring failed: {e}")
            # Return default score on error
            return self._create_dimension_score(
                50.0,
                {"error": str(e)},
            )

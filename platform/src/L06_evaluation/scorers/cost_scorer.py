"""Cost scorer for token/resource cost vs budget"""

import logging
from datetime import datetime

from .base import Scorer
from ..models.quality_score import DimensionScore
from ..models.metric import MetricAggregation

logger = logging.getLogger(__name__)


class CostScorer(Scorer):
    """
    Scores cost based on actual cost vs budget.

    Metrics used:
    - model_cost_dollars (sum)
    - model_tokens_used (sum)
    """

    def __init__(
        self,
        metrics_engine: any,
        weight: float = 0.15,
        budget_dollars: float = 1.0,
    ):
        """
        Initialize cost scorer.

        Args:
            metrics_engine: MetricsEngine for querying metrics
            weight: Weight for cost dimension (default: 0.15)
            budget_dollars: Budget in dollars (default: $1.00)
        """
        super().__init__("cost", weight)
        self.metrics_engine = metrics_engine
        self.budget = budget_dollars

    async def compute_score(
        self,
        agent_id: str,
        tenant_id: str,
        time_window: tuple[datetime, datetime],
    ) -> DimensionScore:
        """Compute cost score"""
        try:
            start, end = time_window
            labels = {"agent_id": agent_id, "tenant_id": tenant_id}

            # Get total cost
            cost_metrics = await self.metrics_engine.query(
                metric_name="model_cost_dollars",
                start=start,
                end=end,
                labels=labels,
                aggregation=MetricAggregation.SUM,
            )

            total_cost = sum(m.value for m in cost_metrics) if cost_metrics else 0.0

            # Get token usage for context
            token_metrics = await self.metrics_engine.query(
                metric_name="model_tokens_used",
                start=start,
                end=end,
                labels=labels,
                aggregation=MetricAggregation.SUM,
            )

            total_tokens = sum(m.value for m in token_metrics) if token_metrics else 0

            # Calculate score (lower cost is better)
            # 100 if under budget, 0 if over 2x budget
            max_cost = self.budget * 2.0
            score = self._linear_score(
                total_cost,
                min_value=self.budget,
                max_value=max_cost,
                invert=True,  # Lower is better
            )

            # Bonus for significantly under budget
            if total_cost < self.budget * 0.5:
                score = min(100.0, score + 10.0)

            raw_metrics = {
                "total_cost_dollars": total_cost,
                "total_tokens": total_tokens,
                "budget_dollars": self.budget,
                "cost_ratio": total_cost / self.budget if self.budget > 0 else 0,
            }

            return self._create_dimension_score(score, raw_metrics)

        except Exception as e:
            logger.error(f"Cost scoring failed: {e}")
            return self._create_dimension_score(
                50.0,
                {"error": str(e)},
            )

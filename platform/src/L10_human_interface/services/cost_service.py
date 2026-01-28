"""
L10 Human Interface Layer - Cost Service

Track and aggregate costs from L06 metrics.
"""

import logging
from datetime import datetime, timedelta, UTC
from typing import Optional, Dict, Any

from ..models import CostSummary, ErrorCode, InterfaceError
from ..integration.l06_bridge import L06Bridge

logger = logging.getLogger(__name__)


# Cost per 1K tokens by model (approximate pricing)
MODEL_COST_PER_1K_TOKENS: Dict[str, float] = {
    "claude-opus-4-5-20251101": 0.015,  # $15/M input, $75/M output (avg)
    "claude-sonnet-4-20250514": 0.003,  # $3/M input, $15/M output (avg)
    "claude-3-5-sonnet-20241022": 0.003,
    "claude-3-opus-20240229": 0.015,
    "claude-3-sonnet-20240229": 0.003,
    "claude-3-haiku-20240307": 0.00025,
    "gpt-4": 0.03,
    "gpt-4-turbo": 0.01,
    "gpt-3.5-turbo": 0.0005,
    "default": 0.001,
}


class CostService:
    """Cost service for tracking usage costs via L06 metrics."""

    def __init__(
        self,
        l06_bridge: Optional[L06Bridge] = None,
        metrics_engine=None,
    ):
        """Initialize CostService.

        Args:
            l06_bridge: Bridge to L06 Evaluation Layer
            metrics_engine: Optional legacy metrics engine (for backward compat)
        """
        self.l06_bridge = l06_bridge
        self.metrics_engine = metrics_engine

    async def get_cost_summary(self, tenant_id: str) -> CostSummary:
        """Get cost summary for tenant.

        Aggregates costs by model and agent from L06 metrics.

        Args:
            tenant_id: Tenant ID

        Returns:
            CostSummary with total cost, breakdown by model/agent, projections

        Raises:
            InterfaceError: E10601 if cost calculation fails
        """
        try:
            now = datetime.now(UTC)
            # Query last 30 days for monthly projection
            start_time = now - timedelta(days=30)

            if not self.l06_bridge:
                logger.warning("L06 bridge not configured, returning zero costs")
                return CostSummary(timestamp=now)

            # Query cost metrics from L06
            cost_metrics = await self.l06_bridge.query_metrics(
                metric_name="model_cost_dollars",
                start_time=start_time,
                end_time=now,
                labels={"tenant_id": tenant_id} if tenant_id else None,
                aggregation="sum",
            )

            # Query token usage metrics
            token_metrics = await self.l06_bridge.query_metrics(
                metric_name="model_tokens_used",
                start_time=start_time,
                end_time=now,
                labels={"tenant_id": tenant_id} if tenant_id else None,
                aggregation="sum",
            )

            # Aggregate costs by model and agent
            total_cost = 0.0
            cost_by_model: Dict[str, float] = {}
            cost_by_agent: Dict[str, float] = {}

            # Process cost metrics directly if available
            for metric in cost_metrics:
                value = metric.get("value", 0.0)
                labels = metric.get("labels", {})
                model = labels.get("model", "unknown")
                agent_id = labels.get("agent_id", "unknown")

                total_cost += value
                cost_by_model[model] = cost_by_model.get(model, 0.0) + value
                cost_by_agent[agent_id] = cost_by_agent.get(agent_id, 0.0) + value

            # If no cost metrics, calculate from token usage
            if not cost_metrics and token_metrics:
                for metric in token_metrics:
                    tokens = metric.get("value", 0)
                    labels = metric.get("labels", {})
                    model = labels.get("model", "unknown")
                    agent_id = labels.get("agent_id", "unknown")

                    # Calculate cost from tokens
                    cost_rate = MODEL_COST_PER_1K_TOKENS.get(
                        model,
                        MODEL_COST_PER_1K_TOKENS["default"]
                    )
                    cost = (tokens / 1000) * cost_rate

                    total_cost += cost
                    cost_by_model[model] = cost_by_model.get(model, 0.0) + cost
                    cost_by_agent[agent_id] = cost_by_agent.get(agent_id, 0.0) + cost

            # Calculate projected monthly cost
            # Based on usage over the query period (30 days)
            days_in_period = 30
            days_in_month = 30
            projected_monthly = total_cost * (days_in_month / days_in_period)

            logger.debug(
                f"Cost summary for tenant {tenant_id}: "
                f"total=${total_cost:.2f}, projected=${projected_monthly:.2f}"
            )

            return CostSummary(
                total_cost_dollars=round(total_cost, 4),
                cost_by_model={k: round(v, 4) for k, v in cost_by_model.items()},
                cost_by_agent={k: round(v, 4) for k, v in cost_by_agent.items()},
                projected_monthly_cost=round(projected_monthly, 2),
                budget_remaining=None,  # Would require budget configuration
                timestamp=now,
            )

        except Exception as e:
            logger.error(f"Cost calculation failed: {e}")
            raise InterfaceError.from_code(
                ErrorCode.E10601,
                details={"tenant_id": tenant_id, "error": str(e)},
            )

    async def get_agent_cost(
        self,
        agent_id: str,
        start: datetime,
        end: datetime,
    ) -> Dict[str, Any]:
        """Get cost for specific agent in time range.

        Args:
            agent_id: Agent ID
            start: Start timestamp
            end: End timestamp

        Returns:
            Dictionary with agent_id, total_cost, and cost_by_model

        Raises:
            InterfaceError: E10601 if cost query fails
        """
        try:
            if not self.l06_bridge:
                logger.warning("L06 bridge not configured, returning zero costs")
                return {
                    "agent_id": agent_id,
                    "total_cost": 0.0,
                    "cost_by_model": {},
                    "tokens_used": 0,
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                }

            # Query cost metrics filtered by agent_id
            cost_metrics = await self.l06_bridge.query_metrics(
                metric_name="model_cost_dollars",
                start_time=start,
                end_time=end,
                labels={"agent_id": agent_id},
                aggregation="sum",
            )

            # Query token metrics for additional context
            token_metrics = await self.l06_bridge.query_metrics(
                metric_name="model_tokens_used",
                start_time=start,
                end_time=end,
                labels={"agent_id": agent_id},
                aggregation="sum",
            )

            total_cost = 0.0
            total_tokens = 0
            cost_by_model: Dict[str, float] = {}
            tokens_by_model: Dict[str, int] = {}

            # Process cost metrics
            for metric in cost_metrics:
                value = metric.get("value", 0.0)
                labels = metric.get("labels", {})
                model = labels.get("model", "unknown")

                total_cost += value
                cost_by_model[model] = cost_by_model.get(model, 0.0) + value

            # Process token metrics
            for metric in token_metrics:
                tokens = int(metric.get("value", 0))
                labels = metric.get("labels", {})
                model = labels.get("model", "unknown")

                total_tokens += tokens
                tokens_by_model[model] = tokens_by_model.get(model, 0) + tokens

            # If no cost metrics, estimate from tokens
            if not cost_metrics and token_metrics:
                for model, tokens in tokens_by_model.items():
                    cost_rate = MODEL_COST_PER_1K_TOKENS.get(
                        model,
                        MODEL_COST_PER_1K_TOKENS["default"]
                    )
                    cost = (tokens / 1000) * cost_rate
                    total_cost += cost
                    cost_by_model[model] = cost

            logger.debug(
                f"Agent {agent_id} cost: ${total_cost:.4f} "
                f"({total_tokens} tokens) from {start} to {end}"
            )

            return {
                "agent_id": agent_id,
                "total_cost": round(total_cost, 4),
                "cost_by_model": {k: round(v, 4) for k, v in cost_by_model.items()},
                "tokens_used": total_tokens,
                "tokens_by_model": tokens_by_model,
                "start": start.isoformat(),
                "end": end.isoformat(),
            }

        except Exception as e:
            logger.error(f"Agent cost query failed: {e}")
            raise InterfaceError.from_code(
                ErrorCode.E10601,
                details={"agent_id": agent_id, "error": str(e)},
            )

    async def get_cost_trend(
        self,
        tenant_id: str,
        days: int = 7,
    ) -> list[Dict[str, Any]]:
        """Get daily cost trend for tenant.

        Args:
            tenant_id: Tenant ID
            days: Number of days to include in trend

        Returns:
            List of daily cost data points
        """
        try:
            now = datetime.now(UTC)
            trend = []

            if not self.l06_bridge:
                return trend

            for i in range(days):
                day_end = now - timedelta(days=i)
                day_start = day_end - timedelta(days=1)

                cost_metrics = await self.l06_bridge.query_metrics(
                    metric_name="model_cost_dollars",
                    start_time=day_start,
                    end_time=day_end,
                    labels={"tenant_id": tenant_id} if tenant_id else None,
                    aggregation="sum",
                )

                daily_total = sum(m.get("value", 0.0) for m in cost_metrics)

                trend.append({
                    "date": day_start.date().isoformat(),
                    "cost": round(daily_total, 4),
                })

            # Reverse to have oldest first
            trend.reverse()
            return trend

        except Exception as e:
            logger.error(f"Cost trend query failed: {e}")
            return []

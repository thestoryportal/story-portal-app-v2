"""
L10 Human Interface Layer - Cost Service

Track and aggregate costs from L06 metrics.
"""

import logging
from datetime import datetime, timedelta, UTC

from ..models import CostSummary, ErrorCode, InterfaceError

logger = logging.getLogger(__name__)


class CostService:
    """Cost service for tracking usage costs."""

    def __init__(self, metrics_engine=None):
        self.metrics_engine = metrics_engine

    async def get_cost_summary(self, tenant_id: str) -> CostSummary:
        """Get cost summary for tenant."""
        try:
            # Placeholder: Query cost metrics from L06
            return CostSummary(timestamp=datetime.now(UTC))

        except Exception as e:
            logger.error(f"Cost calculation failed: {e}")
            raise InterfaceError.from_code(ErrorCode.E10601, details={"tenant_id": tenant_id, "error": str(e)})

    async def get_agent_cost(self, agent_id: str, start: datetime, end: datetime) -> dict:
        """Get cost for specific agent in time range."""
        try:
            # Placeholder: Query agent-specific costs
            return {"agent_id": agent_id, "total_cost": 0.0, "cost_by_model": {}}

        except Exception as e:
            logger.error(f"Agent cost query failed: {e}")
            raise InterfaceError.from_code(ErrorCode.E10601, details={"agent_id": agent_id, "error": str(e)})

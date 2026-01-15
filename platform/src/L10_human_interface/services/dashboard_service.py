"""
L10 Human Interface Layer - Dashboard Service

Aggregates dashboard data from L02 (agent state) and L06 (metrics).
Uses hybrid pull + push model with Redis caching.
"""

import json
import logging
from datetime import datetime, timedelta, UTC
from typing import Optional, Dict, List, Any
import redis.asyncio as redis

from ..models import (
    AgentState,
    AgentStateInfo,
    AgentsSummary,
    MetricsSummary,
    CostSummary,
    AlertSummary,
    DashboardOverview,
    ErrorCode,
    InterfaceError,
)
from ..config import get_settings

logger = logging.getLogger(__name__)


class DashboardService:
    """
    Dashboard service for aggregating real-time system state.

    Responsibilities:
    - Aggregate agent state from L02 StateManager
    - Query metrics from L06 MetricsEngine
    - Cache results in Redis with TTL
    - Subscribe to L11 events for cache invalidation
    - Gracefully degrade when dependencies unavailable
    """

    def __init__(
        self,
        state_manager=None,
        metrics_engine=None,
        event_bus=None,
        redis_client: Optional[redis.Redis] = None,
        circuit_breaker=None,
    ):
        self.state_manager = state_manager
        self.metrics_engine = metrics_engine
        self.event_bus = event_bus
        self.redis = redis_client
        self.circuit_breaker = circuit_breaker
        self.settings = get_settings()

        self._initialized = False

    async def initialize(self):
        """Initialize dashboard service and subscribe to events."""
        if self._initialized:
            return

        # Subscribe to agent state change events for cache invalidation
        if self.event_bus:
            try:
                await self.event_bus.subscribe(
                    topic="agent.state.*",
                    handler=self._handle_agent_state_change,
                    service_name="L10_dashboard",
                )
                logger.info("Subscribed to agent state change events")
            except Exception as e:
                logger.warning(f"Failed to subscribe to events: {e}")

        self._initialized = True
        logger.info("Dashboard service initialized")

    async def cleanup(self):
        """Cleanup resources."""
        self._initialized = False
        logger.info("Dashboard service cleaned up")

    async def get_dashboard_overview(self, tenant_id: str) -> DashboardOverview:
        """
        Get complete dashboard overview.

        Args:
            tenant_id: Tenant ID for multi-tenancy

        Returns:
            DashboardOverview with agents, metrics, cost, alerts
        """
        cache_key = f"dashboard:overview:{tenant_id}"

        # Try cache first
        if self.redis:
            try:
                cached = await self.redis.get(cache_key)
                if cached:
                    logger.debug(f"Dashboard cache hit: {cache_key}")
                    data = json.loads(cached)
                    # Return cached data (could deserialize into models if needed)
                    return data
            except Exception as e:
                logger.warning(f"Cache read failed: {e}")

        # Cache miss - aggregate from sources
        logger.debug("Dashboard cache miss, aggregating from sources")
        dashboard_data = await self._aggregate_dashboard_data(tenant_id)

        # Cache result
        if self.redis:
            try:
                await self.redis.setex(
                    cache_key,
                    self.settings.cache_ttl_dashboard,
                    json.dumps(dashboard_data.to_dict()),
                )
            except Exception as e:
                logger.warning(f"Cache write failed: {e}")

        return dashboard_data

    async def _aggregate_dashboard_data(self, tenant_id: str) -> DashboardOverview:
        """
        Aggregate data from multiple sources.

        Uses asyncio.gather with return_exceptions=True for graceful degradation.
        """
        import asyncio

        # Query all sources in parallel
        agents_summary, metrics_summary, cost_summary, alert_summary = await asyncio.gather(
            self._get_agents_summary(tenant_id),
            self._get_metrics_summary(tenant_id),
            self._get_cost_summary(tenant_id),
            self._get_alert_summary(tenant_id),
            return_exceptions=True,
        )

        # Handle errors gracefully
        if isinstance(agents_summary, Exception):
            logger.error(f"Failed to get agents summary: {agents_summary}")
            agents_summary = AgentsSummary(total=0, by_state={}, agents=[], timestamp=datetime.now(UTC))

        if isinstance(metrics_summary, Exception):
            logger.error(f"Failed to get metrics summary: {metrics_summary}")
            metrics_summary = MetricsSummary(timestamp=datetime.now(UTC))

        if isinstance(cost_summary, Exception):
            logger.error(f"Failed to get cost summary: {cost_summary}")
            cost_summary = CostSummary(timestamp=datetime.now(UTC))

        if isinstance(alert_summary, Exception):
            logger.error(f"Failed to get alert summary: {alert_summary}")
            alert_summary = AlertSummary(timestamp=datetime.now(UTC))

        return DashboardOverview(
            agents=agents_summary,
            metrics=metrics_summary,
            cost=cost_summary,
            alerts=alert_summary,
            timestamp=datetime.now(UTC),
        )

    async def _get_agents_summary(self, tenant_id: str) -> AgentsSummary:
        """Get agents summary from L02 StateManager with caching."""
        cache_key = f"agents:summary:{tenant_id}"

        # Try cache
        if self.redis:
            try:
                cached = await self.redis.get(cache_key)
                if cached:
                    data = json.loads(cached)
                    # Simple deserialization (could be improved)
                    agents = [
                        AgentStateInfo(**agent_data)
                        for agent_data in data.get("agents", [])
                    ]
                    return AgentsSummary(
                        total=data["total"],
                        by_state=data["by_state"],
                        agents=agents,
                        timestamp=datetime.fromisoformat(data["timestamp"]),
                    )
            except Exception as e:
                logger.warning(f"Cache read failed: {e}")

        # Query L02 StateManager
        if not self.state_manager:
            raise InterfaceError.from_code(
                ErrorCode.E10102,
                details={"tenant_id": tenant_id, "reason": "StateManager not available"},
            )

        try:
            # This is a placeholder - actual API may differ
            # In practice, L02 StateManager may have different methods
            agents = await self._query_agents_from_state_manager(tenant_id)

            # Count by state
            by_state = {}
            for agent in agents:
                state = agent.state.value if isinstance(agent.state, AgentState) else agent.state
                by_state[state] = by_state.get(state, 0) + 1

            summary = AgentsSummary(
                total=len(agents),
                by_state=by_state,
                agents=agents,
                timestamp=datetime.now(UTC),
            )

            # Cache
            if self.redis:
                try:
                    await self.redis.setex(
                        cache_key,
                        self.settings.cache_ttl_agent_list,
                        json.dumps(summary.to_dict()),
                    )
                except Exception as e:
                    logger.warning(f"Cache write failed: {e}")

            return summary

        except Exception as e:
            logger.error(f"Failed to query agents from StateManager: {e}")
            raise InterfaceError.from_code(
                ErrorCode.E10102,
                details={"tenant_id": tenant_id, "error": str(e)},
            )

    async def _query_agents_from_state_manager(self, tenant_id: str) -> List[AgentStateInfo]:
        """
        Query agents from L02 StateManager.

        This is a placeholder implementation. Actual integration depends on
        L02 StateManager API.
        """
        # Placeholder: Return empty list if no state manager
        if not self.state_manager:
            return []

        # Attempt to query agents
        # Actual method may be different (e.g., list_agents, get_all_agents, etc.)
        try:
            # Check if state_manager has a method to list agents
            if hasattr(self.state_manager, "list_agents"):
                agents_data = await self.state_manager.list_agents(tenant_id=tenant_id)
            elif hasattr(self.state_manager, "get_all_agents"):
                agents_data = await self.state_manager.get_all_agents()
            else:
                # Fallback: Return empty list
                logger.warning("StateManager has no list_agents or get_all_agents method")
                return []

            # Convert to AgentStateInfo
            agents = []
            for agent_data in agents_data:
                agent = AgentStateInfo(
                    agent_id=agent_data.get("agent_id") or agent_data.get("id"),
                    name=agent_data.get("name", "Unknown"),
                    state=AgentState(agent_data.get("state", "idle")),
                    tenant_id=agent_data.get("tenant_id", tenant_id),
                    current_task_id=agent_data.get("current_task_id"),
                    last_event_at=agent_data.get("last_event_at"),
                    updated_at=agent_data.get("updated_at"),
                )
                agents.append(agent)

            return agents

        except Exception as e:
            logger.error(f"Error querying agents from StateManager: {e}")
            return []

    async def _get_metrics_summary(self, tenant_id: str, time_window_minutes: int = 60) -> MetricsSummary:
        """Get metrics summary from L06 MetricsEngine with caching."""
        cache_key = f"metrics:summary:{tenant_id}:{time_window_minutes}"

        # Try cache
        if self.redis:
            try:
                cached = await self.redis.get(cache_key)
                if cached:
                    data = json.loads(cached)
                    return MetricsSummary(**data)
            except Exception as e:
                logger.warning(f"Cache read failed: {e}")

        # Query L06 MetricsEngine
        if not self.metrics_engine:
            # Return default metrics if not available
            return MetricsSummary(time_window_minutes=time_window_minutes, timestamp=datetime.now(UTC))

        try:
            # Placeholder: Actual API may differ
            end_time = datetime.now(UTC)
            start_time = end_time - timedelta(minutes=time_window_minutes)

            # Query key metrics (placeholder - actual implementation depends on L06 API)
            summary = MetricsSummary(
                avg_task_duration_sec=0.0,
                task_success_count=0,
                task_failure_count=0,
                total_tokens_used=0,
                avg_response_time_ms=0.0,
                error_rate_percent=0.0,
                time_window_minutes=time_window_minutes,
                timestamp=datetime.now(UTC),
            )

            # Cache
            if self.redis:
                try:
                    await self.redis.setex(
                        cache_key,
                        self.settings.cache_ttl_metrics,
                        json.dumps(summary.to_dict()),
                    )
                except Exception as e:
                    logger.warning(f"Cache write failed: {e}")

            return summary

        except Exception as e:
            logger.error(f"Failed to query metrics: {e}")
            return MetricsSummary(time_window_minutes=time_window_minutes, timestamp=datetime.now(UTC))

    async def _get_cost_summary(self, tenant_id: str) -> CostSummary:
        """Get cost summary (placeholder)."""
        # Placeholder implementation
        return CostSummary(timestamp=datetime.now(UTC))

    async def _get_alert_summary(self, tenant_id: str) -> AlertSummary:
        """Get active alerts summary (placeholder)."""
        # Placeholder implementation
        return AlertSummary(timestamp=datetime.now(UTC))

    async def _handle_agent_state_change(self, event):
        """
        Handle agent state change event (push model).

        Invalidates cache and pushes update to WebSocket subscribers.
        """
        try:
            agent_id = event.payload.get("agent_id")
            tenant_id = event.payload.get("tenant_id")

            # Invalidate caches
            cache_keys = [
                f"dashboard:overview:{tenant_id}",
                f"agents:summary:{tenant_id}",
                f"agent:detail:{agent_id}",
            ]

            if self.redis:
                await self.redis.delete(*cache_keys)

            logger.info(f"Agent state change processed: {agent_id}")

        except Exception as e:
            logger.error(f"Failed to handle agent state change: {e}")

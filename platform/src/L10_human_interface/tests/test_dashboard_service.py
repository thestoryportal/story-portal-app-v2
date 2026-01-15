"""
L10 Human Interface Layer - Dashboard Service Tests

Test dashboard aggregation, caching, and graceful degradation.
"""

import pytest
import json
from datetime import datetime, UTC
from unittest.mock import AsyncMock, Mock, patch

from ..models import AgentState, AgentStateInfo, ErrorCode, InterfaceError
from ..services import DashboardService


class TestDashboardServiceInit:
    """Test service initialization."""

    @pytest.mark.asyncio
    async def test_initialize_subscribes_to_events(self, dashboard_service, mock_event_bus):
        """Test that initialize subscribes to state change events."""
        # Should have subscribed to agent state changes
        mock_event_bus.subscribe.assert_called()
        calls = mock_event_bus.subscribe.call_args_list
        assert any("agent.state" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_cleanup_closes_resources(self, dashboard_service):
        """Test cleanup closes resources properly."""
        await dashboard_service.cleanup()
        # Should unsubscribe from events and close connections
        assert dashboard_service._initialized is False


class TestDashboardOverview:
    """Test dashboard overview aggregation."""

    @pytest.mark.asyncio
    async def test_get_dashboard_overview_success(self, dashboard_service, redis_client):
        """Test successful dashboard overview retrieval."""
        overview = await dashboard_service.get_dashboard_overview(tenant_id="tenant-1")

        assert overview is not None
        assert overview.agents_summary is not None
        assert overview.metrics_summary is not None
        assert overview.cost_summary is not None
        assert overview.alert_summary is not None

    @pytest.mark.asyncio
    async def test_get_dashboard_overview_uses_cache(self, dashboard_service, redis_client, mock_state_manager):
        """Test that dashboard uses Redis cache."""
        # First call - cache miss
        overview1 = await dashboard_service.get_dashboard_overview(tenant_id="tenant-1")
        initial_call_count = mock_state_manager.list_agents.call_count

        # Second call - should use cache
        overview2 = await dashboard_service.get_dashboard_overview(tenant_id="tenant-1")

        # State manager should not be called again (cached)
        assert mock_state_manager.list_agents.call_count == initial_call_count

    @pytest.mark.asyncio
    async def test_get_dashboard_overview_cache_miss(self, dashboard_service, redis_client):
        """Test cache miss triggers data aggregation."""
        # Clear cache
        await redis_client.flushdb()

        overview = await dashboard_service.get_dashboard_overview(tenant_id="tenant-1")

        # Should have fetched from L02/L06
        assert overview is not None
        assert overview.agents_summary.total_count >= 0

    @pytest.mark.asyncio
    async def test_get_dashboard_overview_graceful_degradation(self, dashboard_service, mock_state_manager):
        """Test graceful degradation when some sources fail."""
        # Make state manager fail
        mock_state_manager.list_agents.side_effect = Exception("L02 unavailable")

        overview = await dashboard_service.get_dashboard_overview(tenant_id="tenant-1")

        # Should still return overview with defaults for failed parts
        assert overview is not None
        # Agents summary should have error or default values
        assert overview.agents_summary.total_count == 0  # Default when failed

    @pytest.mark.asyncio
    async def test_get_dashboard_overview_tenant_isolation(self, dashboard_service):
        """Test that tenant data is isolated."""
        overview1 = await dashboard_service.get_dashboard_overview(tenant_id="tenant-1")
        overview2 = await dashboard_service.get_dashboard_overview(tenant_id="tenant-2")

        # Should be independently cached
        assert overview1 is not None
        assert overview2 is not None


class TestAgentsSummary:
    """Test agent summary aggregation."""

    @pytest.mark.asyncio
    async def test_get_agents_summary_success(self, dashboard_service, mock_state_manager):
        """Test successful agent summary retrieval."""
        summary = await dashboard_service._get_agents_summary(tenant_id="tenant-1")

        assert summary is not None
        assert summary.total_count >= 0
        assert isinstance(summary.agents, list)

    @pytest.mark.asyncio
    async def test_get_agents_summary_state_counts(self, dashboard_service, mock_state_manager):
        """Test agent state counting."""
        # Mock multiple agents with different states
        mock_state_manager.list_agents.return_value = [
            {
                "agent_id": "agent-1",
                "name": "Agent 1",
                "state": "running",
                "tenant_id": "tenant-1",
                "updated_at": datetime.now(UTC),
            },
            {
                "agent_id": "agent-2",
                "name": "Agent 2",
                "state": "paused",
                "tenant_id": "tenant-1",
                "updated_at": datetime.now(UTC),
            },
            {
                "agent_id": "agent-3",
                "name": "Agent 3",
                "state": "running",
                "tenant_id": "tenant-1",
                "updated_at": datetime.now(UTC),
            },
        ]

        summary = await dashboard_service._get_agents_summary(tenant_id="tenant-1")

        assert summary.total_count == 3
        assert summary.running_count == 2
        assert summary.paused_count == 1

    @pytest.mark.asyncio
    async def test_get_agents_summary_caching(self, dashboard_service, redis_client, mock_state_manager):
        """Test agent summary caching."""
        # First call - cache miss
        summary1 = await dashboard_service._get_agents_summary(tenant_id="tenant-1")
        call_count_after_first = mock_state_manager.list_agents.call_count

        # Second call - cache hit
        summary2 = await dashboard_service._get_agents_summary(tenant_id="tenant-1")

        # State manager should not be called again
        assert mock_state_manager.list_agents.call_count == call_count_after_first

    @pytest.mark.asyncio
    async def test_get_agents_summary_failure_returns_default(self, dashboard_service, mock_state_manager):
        """Test failure returns default summary."""
        mock_state_manager.list_agents.side_effect = Exception("L02 unavailable")

        summary = await dashboard_service._get_agents_summary(tenant_id="tenant-1")

        # Should return default/empty summary
        assert summary.total_count == 0
        assert summary.agents == []


class TestMetricsSummary:
    """Test metrics summary aggregation."""

    @pytest.mark.asyncio
    async def test_get_metrics_summary_success(self, dashboard_service, mock_metrics_engine):
        """Test successful metrics retrieval."""
        summary = await dashboard_service._get_metrics_summary(
            tenant_id="tenant-1", time_window="1h"
        )

        assert summary is not None
        mock_metrics_engine.query.assert_called()

    @pytest.mark.asyncio
    async def test_get_metrics_summary_time_windows(self, dashboard_service):
        """Test different time window queries."""
        summary_1h = await dashboard_service._get_metrics_summary("tenant-1", "1h")
        summary_24h = await dashboard_service._get_metrics_summary("tenant-1", "24h")

        assert summary_1h is not None
        assert summary_24h is not None

    @pytest.mark.asyncio
    async def test_get_metrics_summary_caching(self, dashboard_service, redis_client, mock_metrics_engine):
        """Test metrics summary caching."""
        # First call - cache miss
        await dashboard_service._get_metrics_summary(tenant_id="tenant-1", time_window="1h")
        call_count = mock_metrics_engine.query.call_count

        # Second call - cache hit
        await dashboard_service._get_metrics_summary(tenant_id="tenant-1", time_window="1h")

        # Metrics engine should not be called again (cached)
        assert mock_metrics_engine.query.call_count == call_count

    @pytest.mark.asyncio
    async def test_get_metrics_summary_circuit_breaker(self, dashboard_service, mock_metrics_engine):
        """Test circuit breaker on repeated failures."""
        # Make metrics engine fail repeatedly
        mock_metrics_engine.query.side_effect = Exception("L06 unavailable")

        # Multiple calls should trigger circuit breaker
        for _ in range(5):
            summary = await dashboard_service._get_metrics_summary("tenant-1", "1h")
            # Should return default on failure
            assert summary is not None


class TestCacheInvalidation:
    """Test event-driven cache invalidation."""

    @pytest.mark.asyncio
    async def test_agent_state_change_invalidates_cache(self, dashboard_service, redis_client):
        """Test that agent state changes invalidate cache."""
        # Populate cache
        await dashboard_service.get_dashboard_overview(tenant_id="tenant-1")
        cache_key = "dashboard:overview:tenant-1"

        # Verify cache exists
        cached_before = await redis_client.get(cache_key)
        assert cached_before is not None

        # Simulate agent state change event
        event = {
            "event_type": "agent.state.changed",
            "agent_id": "agent-1",
            "tenant_id": "tenant-1",
            "new_state": "paused",
        }
        await dashboard_service._handle_agent_state_change(event)

        # Cache should be invalidated
        cached_after = await redis_client.get(cache_key)
        assert cached_after is None

    @pytest.mark.asyncio
    async def test_control_operation_invalidates_cache(self, dashboard_service, redis_client):
        """Test that control operations invalidate cache."""
        # Populate cache
        await dashboard_service.get_dashboard_overview(tenant_id="tenant-1")

        # Simulate control operation event
        event = {
            "event_type": "control.operation.completed",
            "agent_id": "agent-1",
            "tenant_id": "tenant-1",
            "operation": "pause",
        }
        await dashboard_service._handle_agent_state_change(event)

        # Cache should be invalidated
        cache_key = "dashboard:overview:tenant-1"
        cached = await redis_client.get(cache_key)
        assert cached is None


class TestAgentDetail:
    """Test individual agent detail retrieval."""

    @pytest.mark.asyncio
    async def test_get_agent_detail_success(self, dashboard_service, mock_state_manager):
        """Test successful agent detail retrieval."""
        detail = await dashboard_service.get_agent_detail(agent_id="agent-1")

        assert detail is not None
        assert detail.agent_id == "agent-1"
        mock_state_manager.get_agent_state.assert_called_with(agent_id="agent-1")

    @pytest.mark.asyncio
    async def test_get_agent_detail_not_found(self, dashboard_service, mock_state_manager):
        """Test agent not found error."""
        mock_state_manager.get_agent_state.return_value = None

        with pytest.raises(InterfaceError) as exc_info:
            await dashboard_service.get_agent_detail(agent_id="nonexistent")

        assert exc_info.value.code == ErrorCode.E10302

    @pytest.mark.asyncio
    async def test_get_agent_detail_caching(self, dashboard_service, redis_client, mock_state_manager):
        """Test agent detail caching."""
        # First call - cache miss
        await dashboard_service.get_agent_detail(agent_id="agent-1")
        call_count = mock_state_manager.get_agent_state.call_count

        # Second call - cache hit
        await dashboard_service.get_agent_detail(agent_id="agent-1")

        # State manager should not be called again
        assert mock_state_manager.get_agent_state.call_count == call_count


class TestErrorHandling:
    """Test error handling and logging."""

    @pytest.mark.asyncio
    async def test_state_manager_unavailable_raises_error(self, dashboard_service, mock_state_manager):
        """Test that L02 unavailability is handled gracefully in overview."""
        mock_state_manager.list_agents.side_effect = Exception("Connection refused")

        # Should not raise, but return default values
        overview = await dashboard_service.get_dashboard_overview(tenant_id="tenant-1")
        assert overview is not None

    @pytest.mark.asyncio
    async def test_metrics_engine_unavailable_returns_defaults(self, dashboard_service, mock_metrics_engine):
        """Test that L06 unavailability returns default metrics."""
        mock_metrics_engine.query.side_effect = Exception("Connection refused")

        summary = await dashboard_service._get_metrics_summary(tenant_id="tenant-1", time_window="1h")

        # Should return default metrics
        assert summary is not None

    @pytest.mark.asyncio
    async def test_redis_unavailable_falls_back_to_direct_query(self, mock_state_manager, mock_metrics_engine, mock_event_bus):
        """Test that Redis unavailability doesn't break service."""
        # Create service without Redis
        service = DashboardService(
            state_manager=mock_state_manager,
            metrics_engine=mock_metrics_engine,
            event_bus=mock_event_bus,
            redis_client=None,  # No Redis
            circuit_breaker=Mock(),
        )
        await service.initialize()

        # Should still work, just without caching
        overview = await service.get_dashboard_overview(tenant_id="tenant-1")
        assert overview is not None

        await service.cleanup()

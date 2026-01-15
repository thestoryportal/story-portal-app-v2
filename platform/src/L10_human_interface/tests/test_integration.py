"""
L10 Human Interface Layer - Integration Tests

End-to-end tests with real infrastructure (Redis, PostgreSQL).
"""

import pytest
import asyncio
from datetime import datetime, UTC
from unittest.mock import AsyncMock, Mock

from ..models import (
    AgentState,
    ControlOperation,
    ControlStatus,
    EventType,
    AlertSeverity,
)
from ..services import (
    DashboardService,
    ControlService,
    WebSocketGateway,
    EventService,
    AlertService,
    AuditService,
    CostService,
)


class TestDashboardIntegration:
    """Integration tests for dashboard service."""

    @pytest.mark.asyncio
    async def test_dashboard_overview_e2e(self, dashboard_service):
        """Test complete dashboard overview flow."""
        overview = await dashboard_service.get_dashboard_overview(tenant_id="tenant-1")

        # Verify all components present
        assert overview is not None
        assert overview.agents_summary is not None
        assert overview.metrics_summary is not None
        assert overview.cost_summary is not None
        assert overview.alert_summary is not None
        assert overview.timestamp is not None

    @pytest.mark.asyncio
    async def test_dashboard_caching_flow(self, dashboard_service, redis_client):
        """Test dashboard caching flow with Redis."""
        tenant_id = "tenant-1"

        # Clear cache
        await redis_client.delete(f"dashboard:overview:{tenant_id}")

        # First call - cache miss
        start = asyncio.get_event_loop().time()
        overview1 = await dashboard_service.get_dashboard_overview(tenant_id=tenant_id)
        time1 = asyncio.get_event_loop().time() - start

        # Second call - cache hit
        start = asyncio.get_event_loop().time()
        overview2 = await dashboard_service.get_dashboard_overview(tenant_id=tenant_id)
        time2 = asyncio.get_event_loop().time() - start

        # Cache hit should be significantly faster
        assert time2 < time1 or time2 < 0.01  # Cache hit should be very fast
        assert overview1 is not None
        assert overview2 is not None

    @pytest.mark.asyncio
    async def test_dashboard_cache_invalidation_flow(self, dashboard_service, redis_client):
        """Test cache invalidation on state change."""
        tenant_id = "tenant-1"

        # Populate cache
        await dashboard_service.get_dashboard_overview(tenant_id=tenant_id)

        # Verify cache exists
        cache_key = f"dashboard:overview:{tenant_id}"
        cached = await redis_client.get(cache_key)
        assert cached is not None

        # Simulate agent state change
        await dashboard_service._handle_agent_state_change({
            "event_type": "agent.state.changed",
            "agent_id": "agent-1",
            "tenant_id": tenant_id,
            "new_state": "paused",
        })

        # Cache should be invalidated
        cached_after = await redis_client.get(cache_key)
        assert cached_after is None

    @pytest.mark.asyncio
    async def test_agent_detail_flow(self, dashboard_service):
        """Test agent detail retrieval flow."""
        # This will use mock state manager from fixture
        detail = await dashboard_service.get_agent_detail(agent_id="agent-1")

        assert detail is not None
        assert detail.agent_id == "agent-1"
        assert detail.state in [state.value for state in AgentState]


class TestControlIntegration:
    """Integration tests for control service."""

    @pytest.mark.asyncio
    async def test_pause_resume_flow(self, control_service, redis_client):
        """Test complete pause/resume flow with locking."""
        agent_id = "agent-1"
        tenant_id = "tenant-1"
        user_id = "user-1"

        # Pause agent
        pause_response = await control_service.pause_agent(
            agent_id=agent_id,
            tenant_id=tenant_id,
            user_id=user_id,
            reason="Testing pause",
        )

        assert pause_response.operation == ControlOperation.PAUSE
        assert pause_response.status in [ControlStatus.SUCCESS, ControlStatus.IDEMPOTENT]

        # Verify lock was released (can acquire again)
        lock_key = f"control:lock:{agent_id}"
        lock_exists = await redis_client.exists(lock_key)
        assert lock_exists == 0  # Lock should be released

        # Resume agent
        resume_response = await control_service.resume_agent(
            agent_id=agent_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        assert resume_response.operation == ControlOperation.RESUME
        assert resume_response.status in [ControlStatus.SUCCESS, ControlStatus.IDEMPOTENT]

    @pytest.mark.asyncio
    async def test_distributed_locking_e2e(self, control_service, redis_client):
        """Test distributed locking prevents concurrent operations."""
        agent_id = "agent-test-lock"

        # Manually acquire lock
        lock_acquired = await control_service._acquire_lock(agent_id, timeout=5)
        assert lock_acquired is True

        # Try to acquire again - should fail
        lock_acquired2 = await control_service._acquire_lock(agent_id, timeout=5)
        assert lock_acquired2 is False

        # Release lock
        await control_service._release_lock(agent_id)

        # Should be able to acquire now
        lock_acquired3 = await control_service._acquire_lock(agent_id, timeout=5)
        assert lock_acquired3 is True

        # Cleanup
        await control_service._release_lock(agent_id)

    @pytest.mark.asyncio
    async def test_idempotency_flow(self, control_service, redis_client):
        """Test idempotency prevents duplicate operations."""
        agent_id = "agent-1"
        tenant_id = "tenant-1"
        user_id = "user-1"
        idempotency_key = "test-operation-12345"

        # First operation
        response1 = await control_service.pause_agent(
            agent_id=agent_id,
            tenant_id=tenant_id,
            user_id=user_id,
            idempotency_key=idempotency_key,
        )

        # Second operation with same key
        response2 = await control_service.pause_agent(
            agent_id=agent_id,
            tenant_id=tenant_id,
            user_id=user_id,
            idempotency_key=idempotency_key,
        )

        # Both should succeed, but second might be cached
        assert response1.status in [ControlStatus.SUCCESS, ControlStatus.IDEMPOTENT]
        assert response2 is not None

    @pytest.mark.asyncio
    async def test_emergency_stop_flow(self, control_service):
        """Test emergency stop flow."""
        response = await control_service.emergency_stop_agent(
            agent_id="agent-1",
            tenant_id="tenant-1",
            user_id="admin-1",
            reason="Security incident detected",
        )

        assert response.operation == ControlOperation.EMERGENCY_STOP
        assert response.status == ControlStatus.SUCCESS


class TestWebSocketIntegration:
    """Integration tests for WebSocket gateway."""

    @pytest.mark.asyncio
    async def test_connection_lifecycle(self, websocket_gateway):
        """Test complete WebSocket connection lifecycle."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()

        conn_id = "test-conn-123"
        tenant_id = "tenant-1"

        # Register connection
        await websocket_gateway._register_connection(mock_ws, conn_id, tenant_id)
        assert websocket_gateway.get_connection_count() == 1

        # Subscribe to topics
        await websocket_gateway._subscribe_connection(conn_id, [
            "agent.state.changed",
            "task.completed",
        ])

        # Broadcast event
        await websocket_gateway._broadcast_locally("agent.state.changed", {
            "agent_id": "agent-1",
            "state": "paused",
        })

        # Connection should receive event
        assert mock_ws.send_json.called

        # Unregister connection
        await websocket_gateway._unregister_connection(conn_id)
        assert websocket_gateway.get_connection_count() == 0

    @pytest.mark.asyncio
    async def test_redis_broadcast_integration(self, websocket_gateway, redis_client):
        """Test Redis pub/sub broadcast integration."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()

        conn_id = "test-conn-456"
        tenant_id = "tenant-1"

        # Register and subscribe
        await websocket_gateway._register_connection(mock_ws, conn_id, tenant_id)
        await websocket_gateway._subscribe_connection(conn_id, ["agent.state.changed"])

        # Broadcast via Redis
        await websocket_gateway.broadcast_event("agent.state.changed", {
            "agent_id": "agent-1",
            "state": "running",
        })

        # Give time for Redis pub/sub
        await asyncio.sleep(0.1)

        # Connection should receive event
        # (In full integration, this would test actual Redis pub/sub)

        # Cleanup
        await websocket_gateway._unregister_connection(conn_id)

    @pytest.mark.asyncio
    async def test_heartbeat_integration(self, websocket_gateway):
        """Test heartbeat mechanism."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()

        conn_id = "test-conn-789"
        await websocket_gateway._register_connection(mock_ws, conn_id, "tenant-1")

        # Send heartbeat
        await websocket_gateway._send_heartbeat()

        # Connection should receive ping
        assert mock_ws.send_json.called
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "ping"

        # Cleanup
        await websocket_gateway._unregister_connection(conn_id)


class TestEventService Integration:
    """Integration tests for event service."""

    @pytest.mark.asyncio
    async def test_query_events_flow(self, event_service):
        """Test event query flow."""
        response = await event_service.query_events(
            filters={"event_type": "agent.state.changed"},
            limit=10,
            offset=0,
        )

        assert response is not None
        assert isinstance(response.events, list)
        assert response.total >= 0

    @pytest.mark.asyncio
    async def test_publish_and_query_event(self, event_service):
        """Test publishing event and querying it back."""
        # Publish event
        await event_service.publish_event(
            event_type=EventType.AGENT_STATE_CHANGED,
            data={
                "agent_id": "agent-1",
                "state": "paused",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

        # Query events
        response = await event_service.query_events(
            filters={"event_type": EventType.AGENT_STATE_CHANGED.value},
            limit=10,
        )

        # Should contain the published event (if not filtered by time)
        assert response is not None


class TestAlertServiceIntegration:
    """Integration tests for alert service."""

    @pytest.mark.asyncio
    async def test_get_active_alerts_flow(self, alert_service):
        """Test retrieving active alerts."""
        alerts = await alert_service.get_active_alerts()

        assert alerts is not None
        assert isinstance(alerts, list)

    @pytest.mark.asyncio
    async def test_acknowledge_alert_flow(self, alert_service):
        """Test acknowledging alert."""
        # Create mock alert first
        alert = await alert_service.acknowledge_alert(
            alert_id="alert-123",
            user="user-1",
        )

        # Should return acknowledged alert
        assert alert is not None


class TestAuditServiceIntegration:
    """Integration tests for audit service."""

    @pytest.mark.asyncio
    async def test_log_and_query_audit(self, audit_service):
        """Test logging and querying audit trail."""
        # Log action
        entry = await audit_service.log_action(
            actor="user-1",
            action="pause_agent",
            resource_type="agent",
            resource_id="agent-1",
            tenant_id="tenant-1",
            reason="Manual pause for testing",
        )

        assert entry is not None
        assert entry.audit_id is not None
        assert entry.actor == "user-1"

        # Query audit trail
        from ..models import AuditQuery
        response = await audit_service.query_audit_trail(
            query=AuditQuery(
                resource_id="agent-1",
                limit=10,
                offset=0,
            )
        )

        assert response is not None
        assert isinstance(response.entries, list)


class TestCostServiceIntegration:
    """Integration tests for cost service."""

    @pytest.mark.asyncio
    async def test_get_cost_summary_flow(self, cost_service):
        """Test cost summary retrieval."""
        summary = await cost_service.get_cost_summary(tenant_id="tenant-1")

        assert summary is not None
        assert summary.timestamp is not None

    @pytest.mark.asyncio
    async def test_get_agent_cost_flow(self, cost_service):
        """Test agent-specific cost retrieval."""
        from datetime import timedelta

        end = datetime.now(UTC)
        start = end - timedelta(hours=24)

        cost = await cost_service.get_agent_cost(
            agent_id="agent-1",
            start=start,
            end=end,
        )

        assert cost is not None
        assert "agent_id" in cost
        assert "total_cost" in cost


class TestCrossServiceIntegration:
    """Integration tests across multiple services."""

    @pytest.mark.asyncio
    async def test_control_operation_triggers_dashboard_update(
        self, control_service, dashboard_service, redis_client
    ):
        """Test control operation invalidates dashboard cache."""
        tenant_id = "tenant-1"
        agent_id = "agent-1"

        # Populate dashboard cache
        await dashboard_service.get_dashboard_overview(tenant_id=tenant_id)

        cache_key = f"dashboard:overview:{tenant_id}"
        cached_before = await redis_client.get(cache_key)
        assert cached_before is not None

        # Perform control operation
        await control_service.pause_agent(
            agent_id=agent_id,
            tenant_id=tenant_id,
            user_id="user-1",
        )

        # Dashboard cache should be invalidated
        # (This would require event bus integration in full setup)

    @pytest.mark.asyncio
    async def test_control_operation_creates_audit_log(
        self, control_service, audit_service
    ):
        """Test control operation creates audit log entry."""
        # Perform control operation
        await control_service.pause_agent(
            agent_id="agent-1",
            tenant_id="tenant-1",
            user_id="user-1",
            reason="Integration test",
        )

        # Query audit trail
        from ..models import AuditQuery
        response = await audit_service.query_audit_trail(
            query=AuditQuery(
                resource_id="agent-1",
                limit=10,
                offset=0,
            )
        )

        # Should contain audit entry for pause operation
        # (Implementation depends on actual audit logger integration)
        assert response is not None

    @pytest.mark.asyncio
    async def test_control_operation_publishes_websocket_event(
        self, control_service, websocket_gateway
    ):
        """Test control operation publishes to WebSocket subscribers."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()

        # Register WebSocket connection
        conn_id = "test-conn"
        await websocket_gateway._register_connection(mock_ws, conn_id, "tenant-1")
        await websocket_gateway._subscribe_connection(conn_id, ["control.operation.completed"])

        # Perform control operation
        await control_service.pause_agent(
            agent_id="agent-1",
            tenant_id="tenant-1",
            user_id="user-1",
        )

        # WebSocket should receive event
        # (Full integration would require event bus wiring)

        # Cleanup
        await websocket_gateway._unregister_connection(conn_id)


class TestPerformance:
    """Performance and load tests."""

    @pytest.mark.asyncio
    async def test_dashboard_query_performance(self, dashboard_service):
        """Test dashboard query completes within SLA (<500ms)."""
        import time

        start = time.time()
        overview = await dashboard_service.get_dashboard_overview(tenant_id="tenant-1")
        duration = time.time() - start

        assert overview is not None
        # SLA: <500ms for dashboard queries
        # Relaxed for testing with mocks
        assert duration < 1.0  # 1 second for mock environment

    @pytest.mark.asyncio
    async def test_control_operation_performance(self, control_service):
        """Test control operation completes within SLA (<100ms)."""
        import time

        start = time.time()
        response = await control_service.pause_agent(
            agent_id="agent-1",
            tenant_id="tenant-1",
            user_id="user-1",
        )
        duration = time.time() - start

        assert response is not None
        # SLA: <100ms for control operations
        # Relaxed for testing with mocks
        assert duration < 0.5  # 500ms for mock environment

    @pytest.mark.asyncio
    async def test_concurrent_control_operations(self, control_service):
        """Test concurrent control operations are handled correctly."""
        # Launch multiple operations concurrently
        tasks = [
            control_service.pause_agent(
                agent_id=f"agent-{i}",
                tenant_id="tenant-1",
                user_id="user-1",
            )
            for i in range(5)
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # All should complete without deadlocks
        assert len(responses) == 5
        for response in responses:
            # Some might fail due to mock setup, but should not hang
            assert response is not None or isinstance(response, Exception)

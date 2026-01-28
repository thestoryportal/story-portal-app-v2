"""
L10 Human Interface Layer - Test Fixtures

Pytest fixtures for testing L10 services.
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, Mock, MagicMock
from datetime import datetime, UTC
import redis.asyncio as redis

from ..models import AgentState, Alert, AlertStatus, AlertSeverity, ErrorCode
from ..services import (
    DashboardService,
    ControlService,
    WebSocketGateway,
    EventService,
    AlertService,
    AuditService,
    CostService,
)
from ..integration import L06Bridge, L01EventBridge


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def redis_client():
    """Redis client fixture (uses real Redis if available)."""
    try:
        client = await redis.from_url("redis://localhost:6379", decode_responses=True)
        yield client
        await client.flushdb()  # Clean up
        await client.aclose()
    except Exception:
        # Fallback to mock if Redis not available
        yield AsyncMock()


@pytest.fixture
def mock_state_manager():
    """Mock L02 StateManager."""
    mock = AsyncMock()
    mock.get_agent_state.return_value = {
        "agent_id": "agent-1",
        "state": "running",
        "tenant_id": "tenant-1",
    }
    mock.update_agent_state.return_value = None
    mock.update_agent_quotas.return_value = None
    mock.list_agents.return_value = [
        {
            "agent_id": "agent-1",
            "name": "Test Agent",
            "state": "running",
            "tenant_id": "tenant-1",
            "updated_at": datetime.now(UTC),
        }
    ]
    return mock


@pytest.fixture
def mock_metrics_engine():
    """Mock L06 MetricsEngine."""
    mock = AsyncMock()
    mock.query.return_value = [
        Mock(
            metric_name="task_duration_seconds",
            value=0.15,
            timestamp=datetime.now(UTC),
            labels={"tenant_id": "tenant-1"},
        )
    ]
    return mock


@pytest.fixture
def mock_event_bus():
    """Mock L11 EventBusManager."""
    mock = AsyncMock()
    mock.publish.return_value = None
    mock.subscribe.return_value = "sub-id-123"
    return mock


@pytest.fixture
def mock_audit_logger():
    """Mock L06 AuditLogger."""
    mock = AsyncMock()
    mock.log.return_value = None
    return mock


# ============================================================================
# Bridge Fixtures
# ============================================================================

@pytest.fixture
def mock_l06_bridge():
    """Mock L06 Bridge for AlertService and CostService."""
    mock = AsyncMock(spec=L06Bridge)
    mock.enabled = True

    # Default alert responses
    test_alert = Alert(
        alert_id="alert-1",
        rule_name="high_cpu",
        severity=AlertSeverity.WARNING,
        message="CPU usage above threshold",
        metric="cpu_percent",
        current_value=85.0,
        threshold=80.0,
        triggered_at=datetime.now(UTC),
        status=AlertStatus.TRIGGERED,
        tenant_id="tenant-1",
    )

    mock.get_alerts.return_value = [test_alert]
    mock.get_alert_by_id.return_value = test_alert
    mock.acknowledge_anomaly.return_value = True
    mock.get_alert_stats.return_value = {
        "alerts_sent": 10,
        "alerts_failed": 1,
        "alerts_rate_limited": 0,
        "success_rate": 0.9,
    }

    # Default metric responses for cost service
    mock.query_metrics.return_value = [
        {
            "metric_name": "model_cost_dollars",
            "value": 0.05,
            "timestamp": datetime.now(UTC).isoformat(),
            "labels": {"model": "claude-3-sonnet", "agent_id": "agent-1"},
        }
    ]

    mock.cleanup.return_value = None

    return mock


@pytest.fixture
def mock_l01_event_bridge():
    """Mock L01 Event Bridge for EventService."""
    mock = AsyncMock(spec=L01EventBridge)
    mock.enabled = True

    from ..models import EventSummary, EventDetail

    test_event_summary = EventSummary(
        event_id="event-1",
        event_type="agent.state.changed",
        aggregate_id="agent-1",
        aggregate_type="agent",
        timestamp=datetime.now(UTC),
        tenant_id="tenant-1",
        severity="info",
        summary="Agent state changed",
    )

    test_event_detail = EventDetail(
        event_id="event-1",
        event_type="agent.state.changed",
        aggregate_id="agent-1",
        aggregate_type="agent",
        timestamp=datetime.now(UTC),
        tenant_id="tenant-1",
        payload={"previous_state": "idle", "new_state": "running"},
        metadata={"source": "l10"},
    )

    mock.query_events.return_value = ([test_event_summary], 1)
    mock.get_event.return_value = test_event_detail
    mock.record_event.return_value = True
    mock.cleanup.return_value = None

    return mock


# ============================================================================
# Service Fixtures with Bridge Injection
# ============================================================================

@pytest_asyncio.fixture
async def dashboard_service(mock_state_manager, mock_metrics_engine, mock_event_bus, redis_client):
    """Dashboard service fixture with mocked dependencies."""
    service = DashboardService(
        state_manager=mock_state_manager,
        metrics_engine=mock_metrics_engine,
        event_bus=mock_event_bus,
        redis_client=redis_client,
        circuit_breaker=Mock(),
    )
    await service.initialize()
    yield service
    await service.cleanup()


@pytest_asyncio.fixture
async def control_service(mock_state_manager, mock_event_bus, mock_audit_logger, redis_client):
    """Control service fixture."""
    service = ControlService(
        state_manager=mock_state_manager,
        event_bus=mock_event_bus,
        audit_logger=mock_audit_logger,
        redis_client=redis_client,
    )
    yield service


@pytest_asyncio.fixture
async def websocket_gateway(mock_event_bus, redis_client):
    """WebSocket gateway fixture."""
    gateway = WebSocketGateway(
        event_bus=mock_event_bus,
        redis_client=redis_client,
    )
    await gateway.start()
    yield gateway
    await gateway.stop()


@pytest.fixture
def event_service(mock_l01_event_bridge):
    """Event service fixture with L01 bridge."""
    return EventService(l01_event_bridge=mock_l01_event_bridge)


@pytest.fixture
def event_service_legacy(mock_event_bus):
    """Event service fixture with legacy event bus (no bridge)."""
    return EventService(event_bus=mock_event_bus)


@pytest.fixture
def alert_service(mock_l06_bridge, mock_audit_logger):
    """Alert service fixture with L06 bridge."""
    return AlertService(
        l06_bridge=mock_l06_bridge,
        audit_logger=mock_audit_logger,
    )


@pytest.fixture
def alert_service_legacy(mock_metrics_engine):
    """Alert service fixture with legacy metrics engine (no bridge)."""
    return AlertService(metrics_engine=mock_metrics_engine)


@pytest.fixture
def audit_service(mock_audit_logger):
    """Audit service fixture."""
    return AuditService(audit_logger=mock_audit_logger)


@pytest.fixture
def cost_service(mock_l06_bridge):
    """Cost service fixture with L06 bridge."""
    return CostService(l06_bridge=mock_l06_bridge)


@pytest.fixture
def cost_service_legacy(mock_metrics_engine):
    """Cost service fixture with legacy metrics engine (no bridge)."""
    return CostService(metrics_engine=mock_metrics_engine)


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_alert():
    """Sample alert for testing."""
    return Alert(
        alert_id="alert-test-1",
        rule_name="memory_warning",
        severity=AlertSeverity.WARNING,
        message="Memory usage is high",
        metric="memory_percent",
        current_value=92.5,
        threshold=90.0,
        triggered_at=datetime.now(UTC),
        status=AlertStatus.TRIGGERED,
        tenant_id="tenant-1",
    )


@pytest.fixture
def sample_critical_alert():
    """Sample critical alert for testing."""
    return Alert(
        alert_id="alert-critical-1",
        rule_name="error_rate_critical",
        severity=AlertSeverity.CRITICAL,
        message="Error rate exceeds critical threshold",
        metric="error_rate",
        current_value=15.0,
        threshold=10.0,
        triggered_at=datetime.now(UTC),
        status=AlertStatus.TRIGGERED,
        tenant_id="tenant-1",
    )

"""
L10 Human Interface Layer - Test Fixtures

Pytest fixtures for testing L10 services.
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, Mock
from datetime import datetime, UTC
import redis.asyncio as redis

from ..models import AgentState, ErrorCode
from ..services import (
    DashboardService,
    ControlService,
    WebSocketGateway,
    EventService,
    AlertService,
    AuditService,
    CostService,
)


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
def event_service(mock_event_bus):
    """Event service fixture."""
    return EventService(event_bus=mock_event_bus)


@pytest.fixture
def alert_service(mock_metrics_engine):
    """Alert service fixture."""
    return AlertService(metrics_engine=mock_metrics_engine)


@pytest.fixture
def audit_service(mock_audit_logger):
    """Audit service fixture."""
    return AuditService(audit_logger=mock_audit_logger)


@pytest.fixture
def cost_service(mock_metrics_engine):
    """Cost service fixture."""
    return CostService(metrics_engine=mock_metrics_engine)

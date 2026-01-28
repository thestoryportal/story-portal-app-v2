"""
L11 Integration Layer - Test Configuration.

Pytest fixtures and configuration for L11 tests.
"""

import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from .fixtures.mock_redis import MockRedis, MockPubSub
from .fixtures.mock_http import MockHTTPClient


# ============================================================================
# Pytest Configuration
# ============================================================================


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "l11: L11 Integration Layer tests")
    config.addinivalue_line("markers", "unit: Unit tests (no external deps)")
    config.addinivalue_line("markers", "integration: Integration tests (requires services)")
    config.addinivalue_line("markers", "slow: Slow tests (>30s)")


# ============================================================================
# Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    return MockRedis()


@pytest.fixture
def mock_pubsub(mock_redis):
    """Create a mock Redis PubSub."""
    return mock_redis.pubsub()


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client."""
    client = MockHTTPClient()
    client.set_default_response({"status": "ok"}, status_code=200)
    return client


# ============================================================================
# Service Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def service_registry():
    """Create a ServiceRegistry instance for testing."""
    from L11_integration.services import ServiceRegistry

    # Create with mock bridge
    registry = ServiceRegistry(l11_bridge=None)
    await registry.start()
    yield registry
    await registry.stop()


@pytest_asyncio.fixture
async def circuit_breaker():
    """Create a CircuitBreaker instance for testing."""
    from L11_integration.services import CircuitBreaker

    cb = CircuitBreaker(l11_bridge=None)
    yield cb


@pytest_asyncio.fixture
async def event_router(mock_http_client):
    """Create an EventRouter instance with mock HTTP client."""
    from L11_integration.services import EventRouter

    router = EventRouter()
    await router.start()
    # Replace HTTP client with mock
    router._http_client = mock_http_client
    yield router
    await router.stop()


@pytest_asyncio.fixture
async def observability_collector():
    """Create an ObservabilityCollector instance for testing."""
    from L11_integration.services import ObservabilityCollector

    collector = ObservabilityCollector(output_file=None)
    await collector.start()
    yield collector
    await collector.stop()


@pytest_asyncio.fixture
async def request_orchestrator(service_registry, circuit_breaker, mock_http_client):
    """Create a RequestOrchestrator instance with mocks."""
    from L11_integration.services import RequestOrchestrator

    orchestrator = RequestOrchestrator(
        service_registry=service_registry,
        circuit_breaker=circuit_breaker,
    )
    await orchestrator.start()
    # Replace HTTP client with mock
    orchestrator._http_client = mock_http_client
    yield orchestrator
    await orchestrator.stop()


@pytest_asyncio.fixture
async def saga_orchestrator(request_orchestrator):
    """Create a SagaOrchestrator instance for testing."""
    from L11_integration.services import SagaOrchestrator

    orchestrator = SagaOrchestrator(
        request_orchestrator=request_orchestrator,
        l11_bridge=None,
    )
    yield orchestrator


# ============================================================================
# Integration Layer Fixture
# ============================================================================


@pytest_asyncio.fixture
async def integration_layer():
    """Create an IntegrationLayer instance for testing."""
    from L11_integration.integration_layer import IntegrationLayer

    # Patch Redis to use mock
    with patch("L11_integration.services.event_bus.aioredis") as mock_redis_module:
        mock_redis_module.from_url = AsyncMock(return_value=MockRedis())

        layer = IntegrationLayer(
            redis_url="redis://localhost:6379/0",
            observability_output_file=None,
        )
        await layer.start()
        yield layer
        await layer.stop()


# ============================================================================
# Event Data Fixtures
# ============================================================================


@pytest.fixture
def agent_event():
    """Create a sample agent event."""
    from .fixtures.event_data import sample_agent_event
    return sample_agent_event()


@pytest.fixture
def tool_event():
    """Create a sample tool event."""
    from .fixtures.event_data import sample_tool_event
    return sample_tool_event()


@pytest.fixture
def plan_event():
    """Create a sample plan event."""
    from .fixtures.event_data import sample_plan_event
    return sample_plan_event()


@pytest.fixture
def session_event():
    """Create a sample session event."""
    from .fixtures.event_data import sample_session_event
    return sample_session_event()


@pytest.fixture
def unknown_event():
    """Create a sample unknown event."""
    from .fixtures.event_data import sample_unknown_event
    return sample_unknown_event()

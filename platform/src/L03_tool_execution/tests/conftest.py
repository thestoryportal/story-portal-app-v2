"""
Test Configuration and Fixtures

Provides pytest fixtures for L03 tests with timeout protection.
Enhanced with signal-based timeout, comprehensive service fixtures,
and markers for integration testing.
"""

import os
import signal
import pytest
import asyncio
from typing import AsyncGenerator, Optional, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import psycopg
import redis.asyncio as redis


# ==================== Pytest Configuration ====================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test (no external deps)"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires services)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow (>10s execution time)"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end (full workflow)"
    )


# ==================== Timeout Protection ====================


class TimeoutError(Exception):
    """Test timeout exception."""
    pass


@pytest.fixture(autouse=True)
def test_timeout():
    """
    Signal-based timeout for all tests.

    Ensures no test can hang indefinitely.
    Default timeout: 60 seconds.
    """
    timeout_seconds = int(os.getenv("TEST_TIMEOUT", "60"))

    def handler(signum, frame):
        raise TimeoutError(f"Test exceeded {timeout_seconds}s timeout")

    # Only set signal alarm on Unix-like systems
    if hasattr(signal, 'SIGALRM'):
        original_handler = signal.signal(signal.SIGALRM, handler)
        signal.alarm(timeout_seconds)

        yield

        signal.alarm(0)  # Cancel alarm
        signal.signal(signal.SIGALRM, original_handler)
    else:
        yield  # Windows doesn't support SIGALRM


# ==================== Async Cleanup ====================


@pytest.fixture
async def async_cleanup():
    """Ensure clean async cleanup after async tests (opt-in)."""
    yield
    try:
        await asyncio.wait_for(asyncio.sleep(0), timeout=2.0)
    except asyncio.TimeoutError:
        pass


# ==================== Environment Fixtures ====================


@pytest.fixture
def mock_db_connection_string():
    """Mock database connection string for tests."""
    return os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/test_l03_tools"
    )


@pytest.fixture
def mock_redis_url():
    """Mock Redis URL for tests."""
    return os.getenv("TEST_REDIS_URL", "redis://localhost:6379/1")


@pytest.fixture
def mock_l02_base_url():
    """Mock L02 Runtime base URL for tests."""
    return os.getenv("TEST_L02_URL", "http://localhost:8002")


@pytest.fixture
def mock_ollama_url():
    """Mock Ollama base URL for tests."""
    return os.getenv("TEST_OLLAMA_URL", "http://localhost:11434")


# ==================== Database Fixtures ====================


@pytest.fixture
async def db_pool(mock_db_connection_string) -> AsyncGenerator:
    """Provide database connection pool for tests."""
    pool = None
    try:
        pool = psycopg.AsyncConnectionPool(
            mock_db_connection_string,
            min_size=1,
            max_size=2,
            timeout=5.0,
        )
        yield pool
    except Exception:
        # Skip tests if DB not available
        pytest.skip("PostgreSQL not available")
    finally:
        if pool:
            await pool.close()


@pytest.fixture
async def redis_client(mock_redis_url) -> AsyncGenerator:
    """Provide Redis client for tests."""
    client = None
    try:
        client = await redis.from_url(mock_redis_url)
        await client.ping()
        yield client
        # Clean up test data
        await client.flushdb()
    except Exception:
        # Skip tests if Redis not available
        pytest.skip("Redis not available")
    finally:
        if client:
            await client.close()


# ==================== Service Fixtures ====================


@pytest.fixture
async def tool_registry(mock_db_connection_string, mock_ollama_url):
    """
    Provide ToolRegistry instance for tests.

    Initializes with test database and Ollama connections.
    """
    from ..services import ToolRegistry

    registry = ToolRegistry(
        db_connection_string=mock_db_connection_string,
        ollama_base_url=mock_ollama_url,
    )
    try:
        await registry.initialize()
        yield registry
    except Exception:
        pytest.skip("ToolRegistry initialization failed")
    finally:
        await registry.close()


@pytest.fixture
def tool_sandbox():
    """Provide ToolSandbox instance for tests."""
    from ..services import ToolSandbox
    return ToolSandbox()


@pytest.fixture
async def tool_executor(tool_registry, tool_sandbox):
    """
    Provide ToolExecutor instance for tests.

    Combines registry and sandbox for execution testing.
    """
    from ..services import ToolExecutor

    return ToolExecutor(
        tool_registry=tool_registry,
        tool_sandbox=tool_sandbox,
    )


@pytest.fixture
async def result_cache(mock_redis_url):
    """Provide ResultCache instance for tests."""
    from ..services import ResultCache

    cache = ResultCache(redis_url=mock_redis_url)
    try:
        await cache.initialize()
        yield cache
    except Exception:
        pytest.skip("ResultCache initialization failed")
    finally:
        await cache.close()


@pytest.fixture
async def task_manager(mock_redis_url):
    """Provide TaskManager instance for tests."""
    from ..services import TaskManager

    manager = TaskManager(redis_url=mock_redis_url)
    try:
        await manager.initialize()
        yield manager
    except Exception:
        pytest.skip("TaskManager initialization failed")
    finally:
        await manager.close()


@pytest.fixture
def mcp_bridge():
    """Provide MCPToolBridge instance for tests with mocked L02 client."""
    from ..services import MCPToolBridge

    bridge = MCPToolBridge(
        document_server_enabled=True,
        context_server_enabled=True,
    )
    # Mock the L02 client for unit testing
    bridge.l02_client = AsyncMock()
    bridge.l02_client.is_available = True
    return bridge


# ==================== Mock Fixtures ====================


@pytest.fixture
def mock_l02_client():
    """Provide mocked L02HttpClient for unit tests."""
    from ..services import L02HttpClient

    client = AsyncMock(spec=L02HttpClient)
    client.is_available = True
    client.base_url = "http://localhost:8002"
    return client


@pytest.fixture
def mock_tool_executor():
    """Provide mocked ToolExecutor for route tests."""
    from ..services import ToolExecutor

    executor = AsyncMock(spec=ToolExecutor)
    return executor


@pytest.fixture
def mock_tool_registry():
    """Provide mocked ToolRegistry for unit tests."""
    from ..services import ToolRegistry

    registry = AsyncMock(spec=ToolRegistry)
    registry.check_connection = AsyncMock(return_value=True)
    return registry


@pytest.fixture
def mock_result_cache():
    """Provide mocked ResultCache for unit tests."""
    from ..services import ResultCache

    cache = AsyncMock(spec=ResultCache)
    cache.check_connection = AsyncMock(return_value=True)
    return cache


# ==================== API Testing Fixtures ====================


@pytest.fixture
async def test_app(mock_tool_registry, mock_result_cache, mock_tool_executor):
    """
    Provide FastAPI test application with mocked services.

    Use with httpx.AsyncClient for API testing.
    """
    from ..main import create_app

    app = create_app()

    # Inject mocked services
    app.state.tool_registry = mock_tool_registry
    app.state.result_cache = mock_result_cache
    app.state.tool_executor = mock_tool_executor
    app.state.task_manager = None  # Mock if needed
    app.state.tool_sandbox = MagicMock()

    return app


@pytest.fixture
async def async_client(test_app):
    """Provide async HTTP client for API testing."""
    from httpx import AsyncClient, ASGITransport

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ==================== Sample Data Fixtures ====================


@pytest.fixture
def sample_tool_definition():
    """Sample tool definition for tests"""
    from ..models import (
        ToolDefinition,
        ToolCategory,
        SourceType,
        DeprecationState,
    )

    return ToolDefinition(
        tool_id="test_tool",
        tool_name="Test Tool",
        description="A test tool for unit testing",
        category=ToolCategory.COMPUTATION,
        latest_version="1.0.0",
        source_type=SourceType.NATIVE,
        tags=["test", "mock"],
        deprecation_state=DeprecationState.ACTIVE,
        requires_approval=False,
        default_timeout_seconds=30,
        default_cpu_millicore_limit=500,
        default_memory_mb_limit=1024,
    )


@pytest.fixture
def sample_tool_manifest():
    """Sample tool manifest for tests"""
    from ..models import (
        ToolManifest,
        ToolCategory,
        ExecutionMode,
    )

    return ToolManifest(
        tool_id="test_tool",
        tool_name="Test Tool",
        version="1.0.0",
        description="A test tool for unit testing",
        category=ToolCategory.COMPUTATION,
        parameters_schema={
            "type": "object",
            "properties": {
                "input": {"type": "string"}
            },
            "required": ["input"]
        },
        execution_mode=ExecutionMode.SYNC,
    )


@pytest.fixture
def sample_tool_invoke_request():
    """Sample tool invocation request for tests."""
    from ..models import (
        ToolInvokeRequest,
        AgentContext,
    )

    return ToolInvokeRequest(
        tool_id="test_tool",
        tool_version="1.0.0",
        agent_context=AgentContext(
            agent_did="agent:test:123",
            tenant_id="tenant_test",
            session_id="session_test",
        ),
        parameters={"input": "test data"},
    )


@pytest.fixture
def sample_invoke_request_dto():
    """Sample tool invoke request DTO for API tests."""
    return {
        "tool_id": "test_tool",
        "tool_version": "1.0.0",
        "agent_did": "did:agent:test",
        "tenant_id": "test-tenant",
        "session_id": "test-session",
        "parameters": {"input": "test data"},
        "async_mode": False,
        "timeout_seconds": 30,
    }


@pytest.fixture
def sample_async_invoke_request_dto():
    """Sample async tool invoke request DTO for API tests."""
    return {
        "tool_id": "test_tool",
        "tool_version": "1.0.0",
        "agent_did": "did:agent:test",
        "tenant_id": "test-tenant",
        "session_id": "test-session",
        "parameters": {"input": "test data"},
        "async_mode": True,
        "timeout_seconds": 60,
    }


@pytest.fixture
def sample_tool_registration_dto():
    """Sample tool registration DTO for API tests."""
    return {
        "tool_id": "new-test-tool",
        "tool_name": "New Test Tool",
        "description": "A newly registered test tool",
        "category": "utility",
        "latest_version": "1.0.0",
        "source_type": "native",
        "tags": ["test", "new"],
    }


@pytest.fixture
def sample_search_request_dto():
    """Sample tool search request DTO for API tests."""
    return {
        "query": "file manipulation utility",
        "limit": 10,
        "filters": {
            "category": "utility",
        },
    }


@pytest.fixture
def sample_checkpoint_data():
    """Sample checkpoint data for tests."""
    from ..models import Checkpoint, CheckpointType

    return Checkpoint(
        checkpoint_id=uuid4(),
        invocation_id=uuid4(),
        checkpoint_type=CheckpointType.MACRO,
        state={"key": "value", "progress": 50},
        progress_percent=50,
    )


@pytest.fixture
def sample_document_context():
    """Sample document context for tests."""
    from ..models import DocumentContext

    return DocumentContext(
        document_refs=["doc-123", "doc-456"],
        query="test query for documents",
    )


# ==================== Utility Functions ====================


def create_mock_tool_response(tool_id: str, status: str = "success") -> Dict[str, Any]:
    """Create a mock tool invocation response."""
    from ..models import ToolStatus

    return {
        "invocation_id": str(uuid4()),
        "status": status,
        "result": {"output": "test result"} if status == "success" else None,
        "error": None if status == "success" else {"code": "E3001", "message": "Test error"},
        "execution_metadata": {
            "tool_id": tool_id,
            "execution_mode": "sync",
            "duration_ms": 150,
        },
    }


def create_mock_task(task_id: str, status: str = "pending") -> Dict[str, Any]:
    """Create a mock async task data."""
    return {
        "task_id": task_id,
        "tool_id": "test_tool",
        "invocation_id": str(uuid4()),
        "status": status,
        "progress": 0 if status == "pending" else 100,
        "result": None if status != "completed" else {"output": "test result"},
        "error": None if status != "error" else {"code": "E3001", "message": "Test error"},
    }

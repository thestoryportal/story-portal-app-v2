"""
Test Configuration and Fixtures

Provides pytest fixtures for L03 tests with timeout protection.
"""

import pytest
import asyncio
from typing import AsyncGenerator
import psycopg
import redis.asyncio as redis


@pytest.fixture(autouse=True)
async def cleanup_timeout():
    """Ensure clean async cleanup after each test"""
    yield
    try:
        await asyncio.wait_for(asyncio.sleep(0), timeout=2.0)
    except asyncio.TimeoutError:
        pass


@pytest.fixture
def mock_db_connection_string():
    """Mock database connection string for tests"""
    return "postgresql://postgres:postgres@localhost:5432/test_l03_tools"


@pytest.fixture
def mock_redis_url():
    """Mock Redis URL for tests"""
    return "redis://localhost:6379/1"


@pytest.fixture
async def db_pool(mock_db_connection_string) -> AsyncGenerator:
    """Provide database connection pool for tests"""
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
    """Provide Redis client for tests"""
    client = None
    try:
        client = await redis.from_url(mock_redis_url)
        await client.ping()
        yield client
    except Exception:
        # Skip tests if Redis not available
        pytest.skip("Redis not available")
    finally:
        if client:
            await client.close()


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
    """Sample tool invocation request for tests"""
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

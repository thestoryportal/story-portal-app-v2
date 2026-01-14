"""
Tests for Agent Executor

Basic tests for agent execution, tool invocation, and context management.
"""

import pytest
import asyncio
from typing import Dict, Any

from ..services.agent_executor import (
    AgentExecutor,
    ExecutorError,
    ToolInvocation,
    ExecutionContext,
)
from ..models import (
    AgentConfig,
    TrustLevel,
    ResourceLimits,
    ToolDefinition,
)


@pytest.fixture
def executor():
    """Create AgentExecutor instance"""
    return AgentExecutor(config={
        "max_concurrent_tools": 5,
        "tool_timeout_seconds": 10,
        "context_window_tokens": 1000,
    })


@pytest.fixture
def agent_config():
    """Create test AgentConfig"""
    return AgentConfig(
        agent_id="test-agent-1",
        trust_level=TrustLevel.STANDARD,
        resource_limits=ResourceLimits(),
        tools=[
            ToolDefinition(
                name="test_tool",
                description="A test tool",
                parameters={"param1": "string"},
            )
        ],
    )


@pytest.mark.asyncio
async def test_executor_initialization(executor):
    """Test executor initialization"""
    await executor.initialize()
    assert executor.max_concurrent_tools == 5
    assert executor.tool_timeout == 10
    assert executor.context_window_tokens == 1000


@pytest.mark.asyncio
async def test_create_context(executor, agent_config):
    """Test execution context creation"""
    await executor.initialize()

    context = await executor.create_context(
        agent_id="test-agent-1",
        session_id="session-1",
        config=agent_config,
    )

    assert context.agent_id == "test-agent-1"
    assert context.session_id == "session-1"
    assert len(context.tools) == 1
    assert context.context_window_tokens == 1000


@pytest.mark.asyncio
async def test_tool_registration(executor):
    """Test tool registration"""
    await executor.initialize()

    async def test_handler(params: Dict[str, Any]):
        return {"result": "success"}

    executor.register_tool("test_tool", test_handler)
    assert "test_tool" in executor._tool_registry

    executor.unregister_tool("test_tool")
    assert "test_tool" not in executor._tool_registry


@pytest.mark.asyncio
async def test_tool_invocation(executor, agent_config):
    """Test tool invocation"""
    await executor.initialize()

    # Create context
    await executor.create_context(
        agent_id="test-agent-1",
        session_id="session-1",
        config=agent_config,
    )

    # Register test tool
    async def test_handler(params: Dict[str, Any]):
        return {"result": params.get("value", 0) * 2}

    executor.register_tool("test_tool", test_handler)

    # Invoke tool
    invocation = ToolInvocation(
        tool_name="test_tool",
        parameters={"value": 5},
    )

    result = await executor.invoke_tool("test-agent-1", invocation)

    assert result.success is True
    assert result.result == {"result": 10}
    assert result.tool_name == "test_tool"


@pytest.mark.asyncio
async def test_tool_invocation_not_registered(executor, agent_config):
    """Test tool invocation with unregistered tool"""
    await executor.initialize()

    await executor.create_context(
        agent_id="test-agent-1",
        session_id="session-1",
        config=agent_config,
    )

    invocation = ToolInvocation(
        tool_name="nonexistent_tool",
        parameters={},
    )

    with pytest.raises(ExecutorError) as exc_info:
        await executor.invoke_tool("test-agent-1", invocation)

    assert exc_info.value.code == "E2001"


@pytest.mark.asyncio
async def test_tool_timeout(executor, agent_config):
    """Test tool timeout"""
    await executor.initialize()

    await executor.create_context(
        agent_id="test-agent-1",
        session_id="session-1",
        config=agent_config,
    )

    # Register slow tool
    async def slow_handler(params: Dict[str, Any]):
        await asyncio.sleep(2)
        return {"result": "done"}

    executor.register_tool("slow_tool", slow_handler)

    # Invoke with short timeout
    invocation = ToolInvocation(
        tool_name="slow_tool",
        parameters={},
        timeout_seconds=1,
    )

    with pytest.raises(ExecutorError) as exc_info:
        await executor.invoke_tool("test-agent-1", invocation)

    assert exc_info.value.code == "E2002"


@pytest.mark.asyncio
async def test_parallel_tool_invocation(executor, agent_config):
    """Test parallel tool invocation"""
    await executor.initialize()

    await executor.create_context(
        agent_id="test-agent-1",
        session_id="session-1",
        config=agent_config,
    )

    # Register test tool
    async def test_handler(params: Dict[str, Any]):
        await asyncio.sleep(0.1)
        return {"value": params.get("value", 0)}

    executor.register_tool("test_tool", test_handler)

    # Create multiple invocations
    invocations = [
        ToolInvocation(tool_name="test_tool", parameters={"value": i})
        for i in range(3)
    ]

    results = await executor.invoke_tools_parallel("test-agent-1", invocations)

    assert len(results) == 3
    assert all(r.success for r in results)
    assert [r.result["value"] for r in results] == [0, 1, 2]


@pytest.mark.asyncio
async def test_context_cleanup(executor, agent_config):
    """Test context cleanup"""
    await executor.initialize()

    await executor.create_context(
        agent_id="test-agent-1",
        session_id="session-1",
        config=agent_config,
    )

    assert "test-agent-1" in executor._contexts

    await executor.cleanup_context("test-agent-1")

    assert "test-agent-1" not in executor._contexts


@pytest.mark.asyncio
async def test_execute_stub(executor, agent_config):
    """Test execute method (stub implementation)"""
    await executor.initialize()

    await executor.create_context(
        agent_id="test-agent-1",
        session_id="session-1",
        config=agent_config,
    )

    result = await executor.execute(
        agent_id="test-agent-1",
        input_data={"content": "test input"},
        stream=False,
    )

    assert result["agent_id"] == "test-agent-1"
    assert "response" in result

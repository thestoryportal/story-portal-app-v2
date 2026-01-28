"""
Tests for L02 Execution HTTP API Routes

Tests for agent execution endpoints: execute and execute/stream (SSE).
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ..routes.execution import router as execution_router
from ..services.agent_executor import AgentExecutor, ExecutorError


@pytest.fixture
def mock_runtime():
    """Create mock AgentRuntime"""
    runtime = MagicMock()
    runtime.agent_executor = MagicMock(spec=AgentExecutor)
    return runtime


@pytest.fixture
def app(mock_runtime):
    """Create test FastAPI app"""
    app = FastAPI()
    app.include_router(execution_router)
    app.state.runtime = mock_runtime
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


class TestExecuteEndpoint:
    """Tests for POST /api/agents/{agent_id}/execute"""

    def test_execute_basic(self, client, mock_runtime):
        """Test basic agent execution"""
        mock_runtime.agent_executor.execute = AsyncMock(return_value={
            "agent_id": "test-agent",
            "session_id": "session-123",
            "request_id": "req-456",
            "model_id": "claude-opus-4-5-20251101",
            "provider": "claude_code",
            "response": "Hello! How can I help you?",
            "tool_calls": [],
            "tokens_used": 50,
            "token_usage": {
                "input_tokens": 20,
                "output_tokens": 30,
                "total_tokens": 50
            },
            "latency_ms": 150,
            "cached": False,
        })

        response = client.post("/api/agents/test-agent/execute", json={
            "content": "Hello!"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == "test-agent"
        assert data["session_id"] == "session-123"
        assert data["response"] == "Hello! How can I help you?"
        assert data["model_id"] == "claude-opus-4-5-20251101"
        assert data["token_usage"]["total_tokens"] == 50

    def test_execute_with_options(self, client, mock_runtime):
        """Test execution with full options"""
        mock_runtime.agent_executor.execute = AsyncMock(return_value={
            "agent_id": "test-agent",
            "session_id": "session-123",
            "request_id": "req-789",
            "model_id": "claude-sonnet-4-20250514",
            "provider": "claude_code",
            "response": "Here is your code...",
            "tool_calls": [],
            "tokens_used": 100,
            "token_usage": {
                "input_tokens": 40,
                "output_tokens": 60,
                "total_tokens": 100
            },
            "latency_ms": 250,
            "cached": False,
        })

        response = client.post("/api/agents/test-agent/execute", json={
            "content": "Write a function",
            "system_prompt": "You are a code assistant",
            "temperature": 0.5,
            "max_tokens": 1000,
        })

        assert response.status_code == 200

        # Verify executor was called with correct params
        call_args = mock_runtime.agent_executor.execute.call_args
        input_data = call_args[1]["input_data"]
        assert input_data["content"] == "Write a function"
        assert input_data["system_prompt"] == "You are a code assistant"
        assert input_data["temperature"] == 0.5
        assert input_data["max_tokens"] == 1000

    def test_execute_with_tool_calls(self, client, mock_runtime):
        """Test execution that returns tool calls"""
        from ..services.agent_executor import ToolInvocation

        tool_invocation = ToolInvocation(
            tool_name="calculator",
            parameters={"a": 5, "b": 3},
            invocation_id="tool-123",
        )

        mock_runtime.agent_executor.execute = AsyncMock(return_value={
            "agent_id": "test-agent",
            "session_id": "session-123",
            "request_id": "req-456",
            "model_id": "claude-opus-4-5-20251101",
            "provider": "claude_code",
            "response": "I'll calculate that for you.",
            "tool_calls": [tool_invocation],
            "tokens_used": 40,
            "token_usage": {"input_tokens": 20, "output_tokens": 20, "total_tokens": 40},
            "latency_ms": 100,
            "cached": False,
        })

        response = client.post("/api/agents/test-agent/execute", json={
            "content": "Calculate 5 + 3"
        })

        assert response.status_code == 200
        data = response.json()
        assert len(data["tool_calls"]) == 1
        assert data["tool_calls"][0]["name"] == "calculator"
        assert data["tool_calls"][0]["arguments"] == {"a": 5, "b": 3}

    def test_execute_context_overflow(self, client, mock_runtime):
        """Test execution with context overflow"""
        mock_runtime.agent_executor.execute = AsyncMock(
            side_effect=ExecutorError("E2003", "Context window exceeded")
        )

        response = client.post("/api/agents/test-agent/execute", json={
            "content": "Very long message..."
        })

        assert response.status_code == 400
        data = response.json()["detail"]
        assert data["error_code"] == "E2003"

    def test_execute_agent_not_found(self, client, mock_runtime):
        """Test execution with non-existent agent"""
        mock_runtime.agent_executor.execute = AsyncMock(
            side_effect=ExecutorError("E2000", "Agent not found")
        )

        response = client.post("/api/agents/nonexistent/execute", json={
            "content": "Hello"
        })

        assert response.status_code == 404

    def test_execute_without_runtime(self, client, mock_runtime):
        """Test execution when runtime is not initialized"""
        client.app.state.runtime = None

        response = client.post("/api/agents/test-agent/execute", json={
            "content": "Hello"
        })

        assert response.status_code == 503


class TestExecuteStreamEndpoint:
    """Tests for POST /api/agents/{agent_id}/execute/stream"""

    def test_stream_basic(self, client, mock_runtime):
        """Test basic streaming execution"""

        async def mock_stream_generator():
            yield {"type": "start", "agent_id": "test-agent", "session_id": "session-123"}
            yield {"type": "content", "delta": "Hello", "request_id": "req-456"}
            yield {"type": "content", "delta": " World", "request_id": "req-456"}
            yield {"type": "end", "agent_id": "test-agent", "session_id": "session-123",
                   "request_id": "req-456", "tokens_used": 10, "content_length": 11}

        mock_runtime.agent_executor.execute = AsyncMock(
            return_value=mock_stream_generator()
        )

        response = client.post(
            "/api/agents/test-agent/execute/stream",
            json={"content": "Hello"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

        # Parse SSE events
        events = []
        for line in response.text.split("\n"):
            if line.startswith("data: ") and line != "data: [DONE]":
                data_str = line[6:]
                events.append(json.loads(data_str))

        assert len(events) == 4
        assert events[0]["type"] == "start"
        assert events[1]["type"] == "content"
        assert events[1]["delta"] == "Hello"
        assert events[2]["type"] == "content"
        assert events[2]["delta"] == " World"
        assert events[3]["type"] == "end"

    def test_stream_error(self, client, mock_runtime):
        """Test streaming with error"""

        async def mock_error_generator():
            yield {"type": "start", "agent_id": "test-agent", "session_id": "session-123"}
            yield {"type": "error", "agent_id": "test-agent",
                   "error_code": "E2005", "message": "LLM error"}

        mock_runtime.agent_executor.execute = AsyncMock(
            return_value=mock_error_generator()
        )

        response = client.post(
            "/api/agents/test-agent/execute/stream",
            json={"content": "Hello"},
        )

        assert response.status_code == 200

        # Parse SSE events
        events = []
        for line in response.text.split("\n"):
            if line.startswith("data: ") and line != "data: [DONE]":
                data_str = line[6:]
                events.append(json.loads(data_str))

        # Should have start and error events
        assert any(e["type"] == "error" for e in events)

    def test_stream_without_runtime(self, client, mock_runtime):
        """Test streaming when runtime is not initialized"""
        client.app.state.runtime = None

        response = client.post(
            "/api/agents/test-agent/execute/stream",
            json={"content": "Hello"},
        )

        assert response.status_code == 503


class TestToolCallParsing:
    """Tests for tool call parsing in execution responses"""

    def test_parse_dict_tool_calls(self, client, mock_runtime):
        """Test parsing tool calls as dictionaries"""
        mock_runtime.agent_executor.execute = AsyncMock(return_value={
            "agent_id": "test-agent",
            "session_id": "session-123",
            "request_id": "req-456",
            "model_id": "claude-opus-4-5-20251101",
            "provider": "claude_code",
            "response": "Let me use tools.",
            "tool_calls": [
                {"id": "tc-1", "name": "search", "arguments": {"query": "test"}},
                {"id": "tc-2", "name": "read_file", "arguments": {"path": "/tmp/test"}},
            ],
            "tokens_used": 50,
            "token_usage": {"input_tokens": 20, "output_tokens": 30, "total_tokens": 50},
            "latency_ms": 150,
            "cached": False,
        })

        response = client.post("/api/agents/test-agent/execute", json={
            "content": "Use tools to help me"
        })

        assert response.status_code == 200
        data = response.json()
        assert len(data["tool_calls"]) == 2
        assert data["tool_calls"][0]["id"] == "tc-1"
        assert data["tool_calls"][0]["name"] == "search"
        assert data["tool_calls"][1]["id"] == "tc-2"
        assert data["tool_calls"][1]["name"] == "read_file"

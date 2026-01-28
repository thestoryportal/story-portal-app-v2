"""
Route Unit Tests

Tests for API route endpoints using mocked dependencies.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from uuid import uuid4
from datetime import datetime, timezone

from ..routes import health_router, tools_router, execution_router, tasks_router
from ..models import (
    ToolDefinition,
    ToolCategory,
    SourceType,
    DeprecationState,
    ToolInvokeResponse,
    ToolStatus,
    ToolResult,
    ExecutionMetadata,
)
from ..models.error_codes import ErrorCode, ToolExecutionError


@pytest.fixture
def app():
    """Create FastAPI app with routes."""
    app = FastAPI()
    app.include_router(health_router)
    app.include_router(tools_router, prefix="/tools")
    app.include_router(execution_router)
    app.include_router(tasks_router, prefix="/tasks")
    return app


@pytest.fixture
def mock_registry():
    """Create mock tool registry."""
    registry = MagicMock()
    registry.db_pool = MagicMock()
    return registry


@pytest.fixture
def mock_executor():
    """Create mock tool executor."""
    return AsyncMock()


@pytest.fixture
def mock_task_manager():
    """Create mock task manager."""
    return AsyncMock()


@pytest.fixture
def client_with_mocks(app, mock_registry, mock_executor, mock_task_manager):
    """Create test client with mocked services."""
    app.state.tool_registry = mock_registry
    app.state.tool_executor = mock_executor
    app.state.task_manager = mock_task_manager
    return TestClient(app)


class TestHealthRoutes:
    """Tests for health check endpoints."""

    def test_liveness_probe(self, app):
        """Test liveness endpoint always returns alive."""
        client = TestClient(app)
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.json() == {"status": "alive"}

    def test_health_no_registry(self, app):
        """Test health endpoint reports degraded without registry."""
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["dependencies"]["postgresql"] == "not_configured"

    def test_readiness_no_registry(self, app):
        """Test readiness returns 503 without registry."""
        client = TestClient(app)
        response = client.get("/health/ready")
        assert response.status_code == 503


class TestToolsRoutes:
    """Tests for tool registry endpoints."""

    def test_list_tools_empty(self, client_with_mocks, mock_registry):
        """Test listing tools returns empty list."""
        mock_registry.list_tools = AsyncMock(return_value=[])

        response = client_with_mocks.get("/tools")
        assert response.status_code == 200
        data = response.json()
        assert data["tools"] == []
        assert data["total"] == 0

    def test_list_tools_with_results(self, client_with_mocks, mock_registry, sample_tool_definition):
        """Test listing tools returns tool list."""
        mock_registry.list_tools = AsyncMock(return_value=[sample_tool_definition])

        response = client_with_mocks.get("/tools")
        assert response.status_code == 200
        data = response.json()
        assert len(data["tools"]) == 1
        assert data["tools"][0]["tool_id"] == "test_tool"
        assert data["total"] == 1

    def test_list_tools_with_category_filter(self, client_with_mocks, mock_registry):
        """Test listing tools with category filter."""
        mock_registry.list_tools = AsyncMock(return_value=[])

        response = client_with_mocks.get("/tools?category=computation")
        assert response.status_code == 200
        mock_registry.list_tools.assert_called_once()

    def test_list_tools_invalid_category(self, client_with_mocks, mock_registry):
        """Test listing tools with invalid category returns 400."""
        response = client_with_mocks.get("/tools?category=invalid")
        assert response.status_code == 400
        assert "Invalid category" in response.json()["detail"]["message"]

    def test_get_tool_success(self, client_with_mocks, mock_registry, sample_tool_definition):
        """Test getting a tool by ID."""
        mock_registry.get_tool = AsyncMock(return_value=sample_tool_definition)

        response = client_with_mocks.get("/tools/test_tool")
        assert response.status_code == 200
        data = response.json()
        assert data["tool_id"] == "test_tool"
        assert data["tool_name"] == "Test Tool"

    def test_get_tool_not_found(self, client_with_mocks, mock_registry):
        """Test getting non-existent tool returns 404."""
        mock_registry.get_tool = AsyncMock(
            side_effect=ToolExecutionError(ErrorCode.E3001, message="Tool not found")
        )

        response = client_with_mocks.get("/tools/nonexistent")
        assert response.status_code == 404

    def test_search_tools(self, client_with_mocks, mock_registry, sample_tool_definition):
        """Test semantic search for tools."""
        mock_registry.semantic_search = AsyncMock(
            return_value=[(sample_tool_definition, 0.95)]
        )

        response = client_with_mocks.post(
            "/tools/search",
            json={"query": "compute something", "limit": 5}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["tool"]["tool_id"] == "test_tool"
        assert data[0]["similarity_score"] == 0.95

    def test_search_tools_embedding_unavailable(self, client_with_mocks, mock_registry):
        """Test semantic search returns 503 when embedding service down."""
        mock_registry.semantic_search = AsyncMock(
            side_effect=ToolExecutionError(ErrorCode.E3005, message="Embedding failed")
        )

        response = client_with_mocks.post(
            "/tools/search",
            json={"query": "test query"}
        )
        assert response.status_code == 503

    def test_register_tool(self, client_with_mocks, mock_registry, sample_tool_definition):
        """Test registering a new tool."""
        mock_registry.register_tool = AsyncMock(return_value=True)
        mock_registry.get_tool = AsyncMock(return_value=sample_tool_definition)

        response = client_with_mocks.post(
            "/tools",
            json={
                "tool_id": "new-tool",
                "tool_name": "New Tool",
                "description": "A new tool for testing registration",
                "category": "computation",
                "version": "1.0.0",
                "source_type": "native",
            }
        )
        assert response.status_code == 201
        mock_registry.register_tool.assert_called_once()

    def test_register_tool_duplicate(self, client_with_mocks, mock_registry):
        """Test registering duplicate tool returns 409."""
        mock_registry.register_tool = AsyncMock(
            side_effect=ToolExecutionError(ErrorCode.E3007, message="Tool already exists")
        )

        response = client_with_mocks.post(
            "/tools",
            json={
                "tool_id": "existing-tool",
                "tool_name": "Existing Tool",
                "description": "A tool that already exists",
                "category": "computation",
                "version": "1.0.0",
                "source_type": "native",
            }
        )
        assert response.status_code == 409


class TestExecutionRoutes:
    """Tests for tool execution endpoints."""

    def test_invoke_tool_success(self, client_with_mocks, mock_executor):
        """Test successful tool invocation."""
        invocation_id = uuid4()
        mock_executor.execute = AsyncMock(
            return_value=ToolInvokeResponse(
                invocation_id=invocation_id,
                status=ToolStatus.SUCCESS,
                result=ToolResult(result={"output": "done"}),
                execution_metadata=ExecutionMetadata(duration_ms=150),
            )
        )

        response = client_with_mocks.post(
            "/tools/test-tool/invoke",
            json={
                "tool_id": "test-tool",
                "agent_did": "did:agent:test",
                "tenant_id": "test-tenant",
                "session_id": "test-session",
                "parameters": {"input": "test"},
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["execution_metadata"]["duration_ms"] == 150

    def test_invoke_tool_async(self, client_with_mocks, mock_executor):
        """Test async tool invocation returns task_id."""
        from ..models import PollingInfo

        invocation_id = uuid4()
        mock_executor.execute = AsyncMock(
            return_value=ToolInvokeResponse(
                invocation_id=invocation_id,
                status=ToolStatus.PENDING,
                polling_info=PollingInfo(
                    task_id="task:test:abc",
                    poll_url="/tasks/task:test:abc",
                    poll_interval_seconds=2,
                ),
            )
        )

        response = client_with_mocks.post(
            "/tools/test-tool/invoke",
            json={
                "tool_id": "test-tool",
                "agent_did": "did:agent:test",
                "tenant_id": "test-tenant",
                "session_id": "test-session",
                "async_mode": True,
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["task_id"] == "task:test:abc"
        assert data["polling_info"]["poll_interval_ms"] == 2000

    def test_invoke_tool_not_found(self, client_with_mocks, mock_executor):
        """Test invocation of non-existent tool returns 404."""
        mock_executor.execute = AsyncMock(
            side_effect=ToolExecutionError(ErrorCode.E3001, message="Tool not found")
        )

        response = client_with_mocks.post(
            "/tools/nonexistent/invoke",
            json={
                "tool_id": "nonexistent",
                "agent_did": "did:agent:test",
                "tenant_id": "test-tenant",
                "session_id": "test-session",
            }
        )

        assert response.status_code == 404

    def test_invoke_tool_rate_limited(self, client_with_mocks, mock_executor):
        """Test invocation returns 429 when rate limited."""
        mock_executor.execute = AsyncMock(
            side_effect=ToolExecutionError(ErrorCode.E3106, message="Concurrent limit exceeded")
        )

        response = client_with_mocks.post(
            "/tools/test-tool/invoke",
            json={
                "tool_id": "test-tool",
                "agent_did": "did:agent:test",
                "tenant_id": "test-tenant",
                "session_id": "test-session",
            }
        )

        assert response.status_code == 429


class TestTasksRoutes:
    """Tests for async task management endpoints."""

    def test_get_task_status(self, client_with_mocks, mock_task_manager):
        """Test getting task status."""
        task = MagicMock()
        task.task_id = "task:test:abc"
        task.tool_id = "test-tool"
        task.invocation_id = uuid4()
        task.status = "running"
        task.progress_percent = 50
        task.created_at = datetime.now(timezone.utc)
        task.updated_at = datetime.now(timezone.utc)
        task.completed_at = None
        task.result = None
        task.error = None

        mock_task_manager.get_task = AsyncMock(return_value=task)

        response = client_with_mocks.get("/tasks/task:test:abc")
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "task:test:abc"
        assert data["status"] == "running"
        assert data["progress_percent"] == 50

    def test_get_task_not_found(self, client_with_mocks, mock_task_manager):
        """Test getting non-existent task returns 404."""
        mock_task_manager.get_task = AsyncMock(return_value=None)

        response = client_with_mocks.get("/tasks/nonexistent")
        assert response.status_code == 404

    def test_cancel_task_success(self, client_with_mocks, mock_task_manager):
        """Test cancelling a running task."""
        task = MagicMock()
        task.status = "running"
        mock_task_manager.get_task = AsyncMock(return_value=task)
        mock_task_manager.cancel_task = AsyncMock(return_value=True)

        response = client_with_mocks.delete("/tasks/task:test:abc")
        assert response.status_code == 200
        data = response.json()
        assert data["cancelled"] is True

    def test_cancel_task_already_completed(self, client_with_mocks, mock_task_manager):
        """Test cancelling already completed task."""
        task = MagicMock()
        task.status = "success"
        mock_task_manager.get_task = AsyncMock(return_value=task)

        response = client_with_mocks.delete("/tasks/task:test:abc")
        assert response.status_code == 200
        data = response.json()
        assert data["cancelled"] is False
        assert "terminal state" in data["message"]

    def test_list_tasks(self, client_with_mocks, mock_task_manager):
        """Test listing tasks."""
        task1 = MagicMock()
        task1.task_id = "task:test:1"
        task1.tool_id = "tool-a"
        task1.invocation_id = uuid4()
        task1.status = "running"
        task1.progress_percent = 50
        task1.created_at = datetime.now(timezone.utc)
        task1.updated_at = datetime.now(timezone.utc)
        task1.completed_at = None

        task2 = MagicMock()
        task2.task_id = "task:test:2"
        task2.tool_id = "tool-b"
        task2.invocation_id = uuid4()
        task2.status = "success"
        task2.progress_percent = 100
        task2.created_at = datetime.now(timezone.utc)
        task2.updated_at = datetime.now(timezone.utc)
        task2.completed_at = datetime.now(timezone.utc)

        mock_task_manager.list_tasks = AsyncMock(return_value=[task1, task2])

        response = client_with_mocks.get("/tasks")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

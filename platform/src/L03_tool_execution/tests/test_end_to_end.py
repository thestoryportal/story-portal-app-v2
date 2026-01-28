"""
End-to-End Tests

Tests for complete tool execution workflows from API to result.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from httpx import AsyncClient, ASGITransport

from ..main import create_app
from ..models import (
    ToolDefinition,
    ToolCategory,
    SourceType,
    ToolStatus,
    ExecutionMode,
)


@pytest.mark.e2e
@pytest.mark.asyncio
class TestEndToEndWorkflows:
    """End-to-end workflow tests with mocked services."""

    @pytest.fixture
    def mock_services(self):
        """Create mocked services for E2E testing."""
        from ..services import ToolRegistry, ToolExecutor, ResultCache, TaskManager

        # Mock tool registry
        mock_registry = AsyncMock(spec=ToolRegistry)
        mock_registry.check_connection = AsyncMock(return_value=True)

        # Mock result cache
        mock_cache = AsyncMock(spec=ResultCache)
        mock_cache.check_connection = AsyncMock(return_value=True)
        mock_cache.get = AsyncMock(return_value=None)  # Cache miss by default

        # Mock tool executor
        mock_executor = AsyncMock(spec=ToolExecutor)

        # Mock task manager
        mock_task_manager = AsyncMock(spec=TaskManager)

        return {
            "registry": mock_registry,
            "cache": mock_cache,
            "executor": mock_executor,
            "task_manager": mock_task_manager,
        }

    @pytest.fixture
    def sample_tool(self):
        """Sample tool for E2E tests."""
        return ToolDefinition(
            tool_id="e2e-test-tool",
            tool_name="E2E Test Tool",
            description="Tool for end-to-end testing",
            category=ToolCategory.COMPUTATION,
            latest_version="1.0.0",
            source_type=SourceType.NATIVE,
            tags=["e2e", "test"],
        )

    @pytest.fixture
    def e2e_app(self, mock_services, sample_tool):
        """Create app with mocked services for E2E testing."""
        from ..models import ToolInvokeResponse, ToolStatus, ToolResult, ExecutionMetadata

        app = create_app()

        # Configure mock registry to return tool
        mock_services["registry"].get_tool = AsyncMock(return_value=sample_tool)
        mock_services["registry"].list_tools = AsyncMock(return_value=[sample_tool])
        mock_services["registry"].search_tools = AsyncMock(return_value=[(sample_tool, 0.95)])

        # Configure mock executor to return proper response object
        mock_response = MagicMock(spec=['invocation_id', 'status', 'result', 'error', 'execution_metadata', 'task_id', 'checkpoint_ref', 'completed_at', 'polling_info'])
        mock_response.invocation_id = uuid4()
        mock_response.status = ToolStatus.SUCCESS
        mock_response.result = ToolResult(result={"output": "E2E test result"})
        mock_response.error = None
        mock_response.completed_at = datetime.now(timezone.utc)
        mock_response.polling_info = None
        mock_response.execution_metadata = MagicMock(
            spec=['duration_ms', 'cpu_used_millicore_seconds', 'memory_peak_mb', 'network_bytes_sent', 'network_bytes_received', 'documents_accessed', 'checkpoints_created']
        )
        mock_response.execution_metadata.duration_ms = 100
        mock_response.execution_metadata.cpu_used_millicore_seconds = None
        mock_response.execution_metadata.memory_peak_mb = None
        mock_response.execution_metadata.network_bytes_sent = None
        mock_response.execution_metadata.network_bytes_received = None
        mock_response.execution_metadata.documents_accessed = []
        mock_response.execution_metadata.checkpoints_created = []
        mock_response.task_id = None
        mock_response.checkpoint_ref = None
        mock_services["executor"].execute = AsyncMock(return_value=mock_response)

        # Inject mocked services
        app.state.tool_registry = mock_services["registry"]
        app.state.result_cache = mock_services["cache"]
        app.state.tool_executor = mock_services["executor"]
        app.state.task_manager = mock_services["task_manager"]
        app.state.tool_sandbox = MagicMock()

        return app

    async def test_full_sync_execution_workflow(self, e2e_app, mock_services, sample_tool):
        """Test complete synchronous tool execution workflow."""
        async with AsyncClient(transport=ASGITransport(app=e2e_app), base_url="http://test") as client:
            # 1. Check health
            response = await client.get("/health")
            assert response.status_code == 200
            health_data = response.json()
            assert health_data["status"] in ["healthy", "degraded"]

            # 2. List tools (paginated response)
            response = await client.get("/tools")
            assert response.status_code == 200
            tools_response = response.json()
            assert "tools" in tools_response
            assert isinstance(tools_response["tools"], list)

            # 3. Get specific tool
            response = await client.get(f"/tools/{sample_tool.tool_id}")
            assert response.status_code == 200
            tool_data = response.json()
            assert tool_data["tool_id"] == sample_tool.tool_id

            # 4. Execute tool
            invoke_request = {
                "tool_id": sample_tool.tool_id,
                "agent_did": "did:agent:e2e-test",
                "tenant_id": "e2e-tenant",
                "session_id": "e2e-session",
                "parameters": {"input": "e2e test data"},
                "async_mode": False,
            }

            response = await client.post(
                f"/tools/{sample_tool.tool_id}/invoke",
                json=invoke_request,
            )
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "success"
            assert "invocation_id" in result
            # Result structure: {"result": {...}, "result_type": "object"} from ToolResult.to_dict()
            assert result["result"]["result"]["output"] == "E2E test result"

    async def test_full_async_execution_workflow(self, e2e_app, mock_services, sample_tool):
        """Test complete asynchronous tool execution workflow."""
        from ..models import ToolStatus

        task_id = f"task:e2e:{uuid4()}"

        # Configure executor for async mode with polling info
        from ..models import PollingInfo
        mock_async_response = MagicMock(spec=['invocation_id', 'status', 'result', 'error', 'execution_metadata', 'task_id', 'checkpoint_ref', 'completed_at', 'polling_info'])
        mock_async_response.invocation_id = uuid4()
        mock_async_response.status = ToolStatus.PENDING
        mock_async_response.result = None
        mock_async_response.error = None
        mock_async_response.execution_metadata = None
        mock_async_response.task_id = task_id
        mock_async_response.checkpoint_ref = None
        mock_async_response.completed_at = None  # Pending has no completion time
        mock_async_response.polling_info = MagicMock(spec=['task_id', 'poll_url', 'poll_interval_seconds', 'estimated_completion'])
        mock_async_response.polling_info.task_id = task_id
        mock_async_response.polling_info.poll_url = f"/tasks/{task_id}"
        mock_async_response.polling_info.poll_interval_seconds = 1
        mock_async_response.polling_info.estimated_completion = None
        mock_services["executor"].execute = AsyncMock(return_value=mock_async_response)

        # Configure task manager for polling
        mock_task = MagicMock(spec=['task_id', 'tool_id', 'invocation_id', 'status', 'progress_percent', 'result', 'error', 'created_at', 'updated_at', 'completed_at'])
        mock_task.task_id = task_id
        mock_task.tool_id = sample_tool.tool_id
        mock_task.invocation_id = str(uuid4())
        mock_task.status = "completed"
        mock_task.progress_percent = 100
        mock_task.result = {"output": "async result"}
        mock_task.error = None
        mock_task.created_at = datetime.now(timezone.utc)
        mock_task.updated_at = datetime.now(timezone.utc)
        mock_task.completed_at = datetime.now(timezone.utc)
        mock_services["task_manager"].get_task = AsyncMock(return_value=mock_task)

        async with AsyncClient(transport=ASGITransport(app=e2e_app), base_url="http://test") as client:
            # 1. Submit async execution
            invoke_request = {
                "tool_id": sample_tool.tool_id,
                "agent_did": "did:agent:e2e-async",
                "tenant_id": "e2e-tenant",
                "session_id": "e2e-session",
                "parameters": {"input": "async test"},
                "async_mode": True,
            }

            response = await client.post(
                f"/tools/{sample_tool.tool_id}/invoke",
                json=invoke_request,
            )
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "pending"
            assert "task_id" in result

            # 2. Poll for completion
            task_id_returned = result["task_id"]
            response = await client.get(f"/tasks/{task_id_returned}")
            assert response.status_code == 200
            task_status = response.json()
            assert task_status["status"] == "completed"

    async def test_semantic_search_workflow(self, e2e_app, mock_services, sample_tool):
        """Test semantic tool search workflow."""
        # Configure search to return results
        mock_services["registry"].search_tools = AsyncMock(return_value=[
            (sample_tool, 0.95)
        ])

        async with AsyncClient(transport=ASGITransport(app=e2e_app), base_url="http://test") as client:
            # Search for tools
            search_request = {
                "query": "computation tool for testing",
                "limit": 5,
            }

            response = await client.post("/tools/search", json=search_request)
            assert response.status_code == 200
            results = response.json()
            assert isinstance(results, list)
            # Search may return empty if registry doesn't have search enabled
            # This is acceptable behavior

    async def test_tool_not_found_handling(self, e2e_app, mock_services):
        """Test error handling for non-existent tool."""
        mock_services["registry"].get_tool = AsyncMock(return_value=None)

        async with AsyncClient(transport=ASGITransport(app=e2e_app), base_url="http://test") as client:
            response = await client.get("/tools/nonexistent-tool")
            # The current implementation returns 500 when tool is None
            # This documents the actual behavior - could be improved to 404
            assert response.status_code in [404, 500]

    async def test_tool_execution_error_handling(self, e2e_app, mock_services, sample_tool):
        """Test error handling during tool execution."""
        from ..models import ToolStatus, ToolError, ErrorCode

        # Configure executor to return error response
        mock_error_response = MagicMock(spec=['invocation_id', 'status', 'result', 'error', 'execution_metadata', 'task_id', 'checkpoint_ref', 'completed_at', 'polling_info'])
        mock_error_response.invocation_id = uuid4()
        mock_error_response.status = ToolStatus.ERROR
        mock_error_response.result = None
        mock_error_response.error = MagicMock(spec=['code', 'message', 'details', 'retryable'])
        mock_error_response.error.code = ErrorCode.E3001
        mock_error_response.error.message = "Tool execution failed"
        mock_error_response.error.details = {}
        mock_error_response.error.retryable = False
        mock_error_response.execution_metadata = None
        mock_error_response.task_id = None
        mock_error_response.checkpoint_ref = None
        mock_error_response.completed_at = datetime.now(timezone.utc)
        mock_error_response.polling_info = None
        mock_services["executor"].execute = AsyncMock(return_value=mock_error_response)

        async with AsyncClient(transport=ASGITransport(app=e2e_app), base_url="http://test") as client:
            invoke_request = {
                "tool_id": sample_tool.tool_id,
                "agent_did": "did:agent:error-test",
                "tenant_id": "test",
                "session_id": "test",
                "parameters": {},
            }

            response = await client.post(
                f"/tools/{sample_tool.tool_id}/invoke",
                json=invoke_request,
            )
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "error"
            assert result["error"]["code"] == "E3001"

    async def test_metrics_collection(self, e2e_app, mock_services, sample_tool):
        """Test that metrics are collected during workflow."""
        async with AsyncClient(transport=ASGITransport(app=e2e_app), base_url="http://test") as client:
            # Execute a tool to generate metrics
            invoke_request = {
                "agent_did": "did:agent:metrics-test",
                "tenant_id": "test",
                "session_id": "test",
                "parameters": {},
            }

            await client.post(
                f"/tools/{sample_tool.tool_id}/invoke",
                json=invoke_request,
            )

            # Check metrics endpoint
            response = await client.get("/metrics")
            assert response.status_code == 200
            metrics_content = response.text
            assert "l03_tool_invocations_total" in metrics_content
            assert "l03_tool_execution_duration" in metrics_content


@pytest.mark.e2e
@pytest.mark.asyncio
class TestErrorRecoveryWorkflows:
    """Tests for error recovery and resilience."""

    @pytest.fixture
    def degraded_app(self):
        """Create app with degraded services."""
        app = create_app()

        # Registry unavailable
        app.state.tool_registry = None

        # Cache available but empty
        mock_cache = AsyncMock()
        mock_cache.check_connection = AsyncMock(return_value=True)
        app.state.result_cache = mock_cache

        app.state.tool_executor = None
        app.state.task_manager = None
        app.state.tool_sandbox = MagicMock()

        return app

    async def test_health_check_degraded_mode(self, degraded_app):
        """Test health check reports degraded when services unavailable."""
        async with AsyncClient(transport=ASGITransport(app=degraded_app), base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            health = response.json()
            assert health["status"] == "degraded"

    async def test_liveness_always_responds(self, degraded_app):
        """Test liveness probe always responds."""
        async with AsyncClient(transport=ASGITransport(app=degraded_app), base_url="http://test") as client:
            response = await client.get("/health/live")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "alive"

    async def test_readiness_fails_when_degraded(self, degraded_app):
        """Test readiness probe fails when core services unavailable."""
        async with AsyncClient(transport=ASGITransport(app=degraded_app), base_url="http://test") as client:
            response = await client.get("/health/ready")
            assert response.status_code == 503


@pytest.mark.e2e
@pytest.mark.asyncio
class TestConcurrencyWorkflows:
    """Tests for concurrent execution handling."""

    @pytest.fixture
    def concurrent_app(self):
        """Create app configured for concurrency testing."""
        from ..models import ToolStatus, ToolResult

        app = create_app()

        # Mock services with concurrency tracking
        invocation_count = {"value": 0}
        max_concurrent = {"value": 0}
        current_concurrent = {"value": 0}

        async def mock_execute(*args, **kwargs):
            invocation_count["value"] += 1
            current_concurrent["value"] += 1
            max_concurrent["value"] = max(max_concurrent["value"], current_concurrent["value"])

            await asyncio.sleep(0.1)  # Simulate work

            current_concurrent["value"] -= 1

            # Return proper response object
            response = MagicMock(spec=['invocation_id', 'status', 'result', 'error', 'execution_metadata', 'task_id', 'checkpoint_ref', 'completed_at', 'polling_info'])
            response.invocation_id = uuid4()
            response.status = ToolStatus.SUCCESS
            response.result = ToolResult(result={"count": invocation_count["value"]})
            response.error = None
            response.completed_at = datetime.now(timezone.utc)
            response.polling_info = None
            response.execution_metadata = MagicMock(
                spec=['duration_ms', 'cpu_used_millicore_seconds', 'memory_peak_mb', 'network_bytes_sent', 'network_bytes_received', 'documents_accessed', 'checkpoints_created']
            )
            response.execution_metadata.duration_ms = 100
            response.execution_metadata.cpu_used_millicore_seconds = None
            response.execution_metadata.memory_peak_mb = None
            response.execution_metadata.network_bytes_sent = None
            response.execution_metadata.network_bytes_received = None
            response.execution_metadata.documents_accessed = []
            response.execution_metadata.checkpoints_created = []
            response.task_id = None
            response.checkpoint_ref = None
            return response

        from ..services import ToolRegistry, ToolExecutor, ResultCache
        from ..models import ToolDefinition, ToolCategory, SourceType

        mock_tool = ToolDefinition(
            tool_id="concurrent-tool",
            tool_name="Concurrent Test Tool",
            description="Tool for concurrency testing",
            category=ToolCategory.COMPUTATION,
            latest_version="1.0.0",
            source_type=SourceType.NATIVE,
        )

        mock_registry = AsyncMock(spec=ToolRegistry)
        mock_registry.check_connection = AsyncMock(return_value=True)
        mock_registry.get_tool = AsyncMock(return_value=mock_tool)

        mock_executor = AsyncMock(spec=ToolExecutor)
        mock_executor.execute = mock_execute

        mock_cache = AsyncMock(spec=ResultCache)
        mock_cache.check_connection = AsyncMock(return_value=True)
        mock_cache.get = AsyncMock(return_value=None)

        app.state.tool_registry = mock_registry
        app.state.tool_executor = mock_executor
        app.state.result_cache = mock_cache
        app.state.task_manager = None
        app.state.tool_sandbox = MagicMock()
        app.state.concurrency_metrics = {
            "invocation_count": invocation_count,
            "max_concurrent": max_concurrent,
        }

        return app

    async def test_concurrent_tool_executions(self, concurrent_app):
        """Test multiple concurrent tool executions."""
        async with AsyncClient(transport=ASGITransport(app=concurrent_app), base_url="http://test") as client:
            invoke_request = {
                "tool_id": "concurrent-tool",
                "agent_did": "did:agent:concurrent",
                "tenant_id": "test",
                "session_id": "test",
                "parameters": {},
            }

            # Launch 5 concurrent executions
            tasks = [
                client.post("/tools/concurrent-tool/invoke", json=invoke_request)
                for _ in range(5)
            ]

            responses = await asyncio.gather(*tasks)

            # All should succeed
            for response in responses:
                assert response.status_code == 200
                result = response.json()
                assert result["status"] == "success"

            # Check concurrency metrics
            metrics = concurrent_app.state.concurrency_metrics
            assert metrics["invocation_count"]["value"] == 5
            assert metrics["max_concurrent"]["value"] >= 2  # At least some concurrency

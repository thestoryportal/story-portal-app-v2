"""
E2E Test: L03 Tool Execution - L01 Data Layer Integration

Tests the complete integration between L03 Tool Execution and L01 Data Layer
for persistent tool execution tracking.
"""

import pytest
from uuid import uuid4
from datetime import datetime


class TestL03L01Integration:
    """Test L03-L01 integration end-to-end."""

    @pytest.fixture
    async def l03_bridge(self):
        """Initialize L03 bridge with L01."""
        from src.L03_tool_execution.services.l01_bridge import L03Bridge

        bridge = L03Bridge(l01_base_url="http://localhost:8002")
        await bridge.initialize()
        yield bridge
        await bridge.cleanup()

    @pytest.mark.asyncio
    async def test_bridge_initialization(self, l03_bridge):
        """Test L03 bridge initializes correctly."""
        assert l03_bridge is not None
        assert l03_bridge.enabled is True
        assert l03_bridge.l01_client is not None
        print("✓ L03Bridge initialized successfully")

    @pytest.mark.asyncio
    async def test_record_tool_invocation_start(self, l03_bridge):
        """Test recording tool invocation start in L01."""
        from src.L03_tool_execution.models.tool_result import (
            ToolInvokeRequest,
            AgentContext,
            ResourceLimits,
            ExecutionOptions
        )

        invocation_id = uuid4()

        # Create tool invocation request
        request = ToolInvokeRequest(
            invocation_id=invocation_id,
            tool_id="test_calculation_tool",
            tool_version="1.0.0",
            agent_context=AgentContext(
                agent_did="did:test:agent_calculator",
                tenant_id="tenant_math",
                session_id="session_calc_001",
                parent_sandbox_id="sandbox_calc"
            ),
            parameters={"operation": "add", "a": 5, "b": 3},
            resource_limits=ResourceLimits(
                cpu_millicore_limit=500,
                memory_mb_limit=512,
                timeout_seconds=30
            ),
            execution_options=ExecutionOptions(
                async_mode=False,
                priority=7,
                idempotency_key="calc-key-123"
            )
        )

        # Record invocation start
        result = await l03_bridge.record_invocation_start(request)
        assert result is True
        print(f"✓ Tool invocation {invocation_id} recorded in L01")

        # Verify it was recorded
        execution = await l03_bridge.get_execution_history(invocation_id)
        assert execution is not None
        assert execution["invocation_id"] == str(invocation_id)
        assert execution["tool_name"] == "test_calculation_tool"
        assert execution["status"] == "pending"
        assert execution["agent_did"] == "did:test:agent_calculator"
        assert execution["priority"] == 7
        print(f"✓ Execution record verified in L01: {execution['tool_name']} - {execution['status']}")

    @pytest.mark.asyncio
    async def test_update_invocation_status(self, l03_bridge):
        """Test updating tool invocation status through L03 bridge."""
        from src.L03_tool_execution.models.tool_result import (
            ToolInvokeRequest,
            ToolStatus
        )

        invocation_id = uuid4()

        # Create and record invocation
        request = ToolInvokeRequest(
            invocation_id=invocation_id,
            tool_id="status_test_tool",
            parameters={"test": "status_update"}
        )
        await l03_bridge.record_invocation_start(request)
        print(f"✓ Created invocation {invocation_id}")

        # Update to RUNNING
        result = await l03_bridge.update_invocation_status(invocation_id, ToolStatus.RUNNING)
        assert result is True

        # Verify update
        execution = await l03_bridge.get_execution_history(invocation_id)
        assert execution["status"] == "running"
        print(f"✓ Status updated to: {execution['status']}")

    @pytest.mark.asyncio
    async def test_record_successful_execution(self, l03_bridge):
        """Test recording successful tool execution with results."""
        from src.L03_tool_execution.models.tool_result import (
            ToolInvokeRequest,
            ToolInvokeResponse,
            ToolStatus,
            ToolResult,
            ExecutionMetadata
        )

        invocation_id = uuid4()
        started_at = datetime.utcnow()

        # Create and record invocation
        request = ToolInvokeRequest(
            invocation_id=invocation_id,
            tool_id="success_tool",
            parameters={"input": "test_data"}
        )
        await l03_bridge.record_invocation_start(request)
        await l03_bridge.update_invocation_status(invocation_id, ToolStatus.RUNNING)
        print(f"✓ Tool execution started: {invocation_id}")

        # Create successful response with metadata
        response = ToolInvokeResponse(
            invocation_id=invocation_id,
            status=ToolStatus.SUCCESS,
            result=ToolResult(
                result={"output": "processed_data", "count": 42, "items": [1, 2, 3]},
                result_type="object"
            ),
            execution_metadata=ExecutionMetadata(
                duration_ms=1250,
                cpu_used_millicore_seconds=1000,
                memory_peak_mb=128,
                network_bytes_sent=1024,
                network_bytes_received=2048,
                documents_accessed=[
                    {"document_id": "doc_spec_001"},
                    {"document_id": "doc_ref_002"}
                ],
                checkpoints_created=[{"checkpoint_id": "checkpoint_final"}]
            ),
            checkpoint_ref="final_checkpoint_abc123",
            completed_at=datetime.utcnow()
        )

        # Record result
        result = await l03_bridge.record_invocation_result(response, started_at)
        assert result is True
        print("✓ Success result recorded with metadata")

        # Verify complete execution record
        execution = await l03_bridge.get_execution_history(invocation_id)
        assert execution["status"] == "success"
        assert execution["output_result"]["result"]["output"] == "processed_data"
        assert execution["output_result"]["result"]["count"] == 42
        assert execution["duration_ms"] == 1250
        assert execution["cpu_used_millicore_seconds"] == 1000
        assert execution["memory_peak_mb"] == 128
        assert "doc_spec_001" in execution["documents_accessed"]
        assert "doc_ref_002" in execution["documents_accessed"]
        assert "checkpoint_final" in execution["checkpoints_created"]
        assert execution["checkpoint_ref"] == "final_checkpoint_abc123"
        print("✓ All execution metadata verified:")
        print(f"  - Duration: {execution['duration_ms']}ms")
        print(f"  - CPU: {execution['cpu_used_millicore_seconds']} millicore-seconds")
        print(f"  - Memory: {execution['memory_peak_mb']}MB")
        print(f"  - Documents: {len(execution['documents_accessed'])}")
        print(f"  - Checkpoints: {len(execution['checkpoints_created'])}")

    @pytest.mark.asyncio
    async def test_record_failed_execution(self, l03_bridge):
        """Test recording failed tool execution with error details."""
        from src.L03_tool_execution.models.tool_result import (
            ToolInvokeRequest,
            ToolInvokeResponse,
            ToolStatus,
            ToolError,
            ExecutionMetadata
        )

        invocation_id = uuid4()

        # Create and record invocation
        request = ToolInvokeRequest(
            invocation_id=invocation_id,
            tool_id="failing_validation_tool",
            parameters={"input": "invalid_data"}
        )
        await l03_bridge.record_invocation_start(request)
        print(f"✓ Tool execution started: {invocation_id}")

        # Create error response
        response = ToolInvokeResponse(
            invocation_id=invocation_id,
            status=ToolStatus.ERROR,
            error=ToolError(
                code="E3001",
                message="Validation failed: input format incorrect",
                details={
                    "field": "input",
                    "reason": "format_error",
                    "expected": "json_object",
                    "received": "string"
                },
                retryable=True
            ),
            execution_metadata=ExecutionMetadata(
                duration_ms=500,
                cpu_used_millicore_seconds=200,
                memory_peak_mb=64
            ),
            completed_at=datetime.utcnow()
        )

        # Record error
        result = await l03_bridge.record_invocation_result(response)
        assert result is True
        print("✓ Error result recorded")

        # Verify error details
        execution = await l03_bridge.get_execution_history(invocation_id)
        assert execution["status"] == "error"
        assert execution["error_code"] == "E3001"
        assert "Validation failed" in execution["error_message"]
        assert execution["error_details"]["field"] == "input"
        assert execution["retryable"] is True
        assert execution["duration_ms"] == 500
        print("✓ Error details verified:")
        print(f"  - Code: {execution['error_code']}")
        print(f"  - Message: {execution['error_message']}")
        print(f"  - Retryable: {execution['retryable']}")

    @pytest.mark.asyncio
    async def test_full_execution_lifecycle(self, l03_bridge):
        """Test complete execution lifecycle: start → running → success."""
        from src.L03_tool_execution.models.tool_result import (
            ToolInvokeRequest,
            ToolInvokeResponse,
            ToolStatus,
            ToolResult,
            AgentContext,
            ExecutionOptions,
            ExecutionMetadata
        )

        invocation_id = uuid4()
        started_at = datetime.utcnow()

        print(f"\n=== Full Lifecycle Test for {invocation_id} ===")

        # Phase 1: Record invocation start
        request = ToolInvokeRequest(
            invocation_id=invocation_id,
            tool_id="lifecycle_integration_tool",
            tool_version="2.1.0",
            agent_context=AgentContext(
                agent_did="did:test:lifecycle_agent",
                tenant_id="tenant_lifecycle_test",
                session_id="session_lifecycle_001"
            ),
            parameters={"test": "full_lifecycle", "iterations": 5},
            execution_options=ExecutionOptions(priority=8)
        )
        assert await l03_bridge.record_invocation_start(request) is True
        print("✓ Phase 1: Invocation recorded (PENDING)")

        execution = await l03_bridge.get_execution_history(invocation_id)
        assert execution["status"] == "pending"

        # Phase 2: Update to RUNNING
        assert await l03_bridge.update_invocation_status(invocation_id, ToolStatus.RUNNING) is True
        print("✓ Phase 2: Status updated (RUNNING)")

        execution = await l03_bridge.get_execution_history(invocation_id)
        assert execution["status"] == "running"

        # Phase 3: Complete with SUCCESS
        response = ToolInvokeResponse(
            invocation_id=invocation_id,
            status=ToolStatus.SUCCESS,
            result=ToolResult(
                result={"final_output": "lifecycle_complete", "iterations_completed": 5},
                result_type="object"
            ),
            execution_metadata=ExecutionMetadata(
                duration_ms=2000,
                cpu_used_millicore_seconds=1500,
                memory_peak_mb=256
            ),
            completed_at=datetime.utcnow()
        )
        assert await l03_bridge.record_invocation_result(response, started_at) is True
        print("✓ Phase 3: Result recorded (SUCCESS)")

        # Final verification
        execution = await l03_bridge.get_execution_history(invocation_id)
        assert execution["status"] == "success"
        assert execution["output_result"]["result"]["final_output"] == "lifecycle_complete"
        assert execution["duration_ms"] == 2000
        assert execution["started_at"] is not None
        assert execution["completed_at"] is not None

        print("✓ LIFECYCLE COMPLETE:")
        print(f"  - Tool: {execution['tool_name']} v{execution['tool_version']}")
        print(f"  - Duration: {execution['duration_ms']}ms")
        print(f"  - Result: {execution['output_result']['result']['final_output']}")
        print("=== Test Passed ===\n")

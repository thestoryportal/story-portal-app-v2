"""
L05 Planning Pipeline - Fail-Fast Gate Tests (Phase 3).

These tests MUST pass before proceeding to Phase 4.
Gate 3 validates:
1. Missing L02 executor raises PlanningError (not mock result)
2. Missing L03 tool executor raises PlanningError (not mock result)
3. L04Bridge with strict_mode raises when not connected
4. validate_dependencies() reports missing dependencies

Run: pytest test_failfast_gates.py -v
Expected: 4/4 pass
"""

import pytest
import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from ..models import (
    Goal,
    GoalType,
    GoalConstraints,
    ExecutionPlan,
    Task,
    TaskStatus,
    PlanningError,
    ErrorCode,
)
from ..services.task_orchestrator import TaskOrchestrator
from ..services.planning_service import PlanningService
from ..integration.l04_bridge import L04Bridge


class TestFailFastGates:
    """
    Gate 3: Fail-Fast Tests

    These tests verify that missing dependencies raise errors
    instead of silently returning mock results.
    """

    @pytest.fixture
    def sample_plan(self) -> ExecutionPlan:
        """Create a sample plan with various task types."""
        plan = ExecutionPlan.create(goal_id=str(uuid4()))

        # LLM call task (requires L02)
        llm_task = Task.create(
            plan_id=plan.plan_id,
            name="LLM Analysis",
            description="Analyze requirements using LLM",
        )
        llm_task.task_type = "llm_call"
        llm_task.llm_prompt = "Analyze this requirement"

        # Tool call task (requires L03)
        tool_task = Task.create(
            plan_id=plan.plan_id,
            name="Execute Tool",
            description="Execute a specific tool",
        )
        tool_task.task_type = "tool_call"
        tool_task.tool_name = "file_writer"

        # Atomic task (requires L02)
        atomic_task = Task.create(
            plan_id=plan.plan_id,
            name="Atomic Operation",
            description="Perform atomic operation",
        )
        atomic_task.task_type = "atomic"

        plan.add_task(llm_task)
        plan.add_task(tool_task)
        plan.add_task(atomic_task)
        plan.mark_validated()

        return plan

    @pytest.mark.asyncio
    async def test_missing_l02_raises_error(self, sample_plan: ExecutionPlan):
        """
        GATE 3.1: Missing L02 executor raises PlanningError.

        Verifies that:
        1. TaskOrchestrator with executor_client=None
        2. Executing an llm_call task raises PlanningError
        3. Error is NOT silently replaced with mock result
        """
        # Create orchestrator WITHOUT L02 executor
        orchestrator = TaskOrchestrator(
            executor_client=None,  # No L02!
            tool_executor_client=None,
            max_parallel_tasks=5,
            strict_mode=True,  # Enable strict mode
        )

        # Get just the LLM task
        llm_task = sample_plan.get_task_by_name("LLM Analysis")
        assert llm_task is not None, "LLM task not found"

        # Create a single-task plan
        single_plan = ExecutionPlan.create(goal_id=str(uuid4()))
        single_plan.add_task(llm_task)
        single_plan.mark_validated()

        # Executing should raise PlanningError, NOT return mock
        with pytest.raises(PlanningError) as exc_info:
            await orchestrator.execute_plan(single_plan)

        # Verify it's the right error
        assert exc_info.value.code in ["E5200", "E5204", "E5306"], (
            f"GATE 3.1 FAILED: Expected PlanningError for missing L02.\\n"
            f"Got error code: {exc_info.value.code}\\n"
            f"Message: {exc_info.value.message}"
        )

    @pytest.mark.asyncio
    async def test_missing_l03_raises_error(self, sample_plan: ExecutionPlan):
        """
        GATE 3.2: Missing L03 tool executor raises PlanningError.

        Verifies that:
        1. TaskOrchestrator with tool_executor_client=None
        2. Executing a tool_call task raises PlanningError
        3. Error is NOT silently replaced with mock result
        """
        # Create orchestrator WITHOUT L03 tool executor
        orchestrator = TaskOrchestrator(
            executor_client=None,
            tool_executor_client=None,  # No L03!
            max_parallel_tasks=5,
            strict_mode=True,  # Enable strict mode
        )

        # Get just the tool task
        tool_task = sample_plan.get_task_by_name("Execute Tool")
        assert tool_task is not None, "Tool task not found"

        # Create a single-task plan
        single_plan = ExecutionPlan.create(goal_id=str(uuid4()))
        single_plan.add_task(tool_task)
        single_plan.mark_validated()

        # Executing should raise PlanningError, NOT return mock
        with pytest.raises(PlanningError) as exc_info:
            await orchestrator.execute_plan(single_plan)

        # Verify it's the right error
        assert exc_info.value.code in ["E5200", "E5204", "E5307"], (
            f"GATE 3.2 FAILED: Expected PlanningError for missing L03.\\n"
            f"Got error code: {exc_info.value.code}\\n"
            f"Message: {exc_info.value.message}"
        )

    @pytest.mark.asyncio
    async def test_l04_strict_mode_raises_when_not_connected(self):
        """
        GATE 3.3: L04Bridge with strict_mode raises when not connected.

        Verifies that:
        1. L04Bridge with strict_mode=True
        2. generate_plan_async raises when not connected to L04 service
        3. Does NOT silently fall back to mock generation
        """
        # Create L04Bridge with strict mode
        bridge = L04Bridge(
            base_url="http://localhost:9999",  # Non-existent service
            strict_mode=True,  # Enable strict mode
        )

        # Initialize (will fail to connect)
        await bridge.initialize()
        assert not bridge.is_connected(), "Bridge should not be connected to fake URL"

        # Attempting generation should raise, NOT return mock
        with pytest.raises(PlanningError) as exc_info:
            await bridge.generate_plan_async(
                task_description="Test task",
                context={"test": True},
            )

        # Verify it's a dependency error
        assert exc_info.value.code in ["E5308", "E5300"], (
            f"GATE 3.3 FAILED: Expected PlanningError for L04 not connected.\\n"
            f"Got error code: {exc_info.value.code}\\n"
            f"Message: {exc_info.value.message}"
        )

        await bridge.close()

    @pytest.mark.asyncio
    async def test_validate_dependencies_reports_issues(self, monkeypatch):
        """
        GATE 3.4: validate_dependencies() reports missing dependencies.

        Verifies that:
        1. PlanningService has validate_dependencies() method
        2. Method returns dict with status for each dependency
        3. Missing dependencies are clearly reported
        """
        # Set MOCK_MODE to prevent auto-creation of L02/L04
        monkeypatch.setenv("PLANNING_MOCK_MODE", "true")

        # Need to reimport to pick up the env var
        import importlib
        from ..services import planning_service
        importlib.reload(planning_service)

        # Create service without any clients configured
        service = planning_service.PlanningService(
            executor_client=None,
            tool_executor_client=None,
            gateway_client=None,
        )

        await service.initialize()

        try:
            # Call validate_dependencies
            result = await service.validate_dependencies()

            # Must return a dict with dependency status
            assert isinstance(result, dict), (
                f"GATE 3.4 FAILED: validate_dependencies() should return dict.\\n"
                f"Got: {type(result)}"
            )

            # Must report status for key dependencies
            expected_keys = ["l01_data", "l02_executor", "l03_tools", "l04_gateway"]
            for key in expected_keys:
                assert key in result, (
                    f"GATE 3.4 FAILED: validate_dependencies() missing '{key}'.\\n"
                    f"Keys found: {list(result.keys())}"
                )

            # L02, L03, L04 should be reported as unavailable
            assert result.get("l02_executor", {}).get("available") == False, (
                "L02 executor should be reported as unavailable"
            )
            assert result.get("l03_tools", {}).get("available") == False, (
                "L03 tools should be reported as unavailable"
            )
            assert result.get("l04_gateway", {}).get("available") == False, (
                "L04 gateway should be reported as unavailable"
            )

        finally:
            await service.cleanup()
            # Reset the env var
            monkeypatch.delenv("PLANNING_MOCK_MODE", raising=False)
            importlib.reload(planning_service)


class TestStrictModeConfiguration:
    """
    Additional tests for strict mode configuration.
    These help diagnose issues but are not blocking gates.
    """

    def test_task_orchestrator_strict_mode_default(self):
        """Test that strict_mode can be enabled on TaskOrchestrator."""
        orchestrator = TaskOrchestrator(strict_mode=True)
        assert hasattr(orchestrator, 'strict_mode'), "TaskOrchestrator should have strict_mode attribute"
        assert orchestrator.strict_mode == True, "strict_mode should be True when set"

    def test_task_orchestrator_strict_mode_off_allows_mock(self):
        """Test that strict_mode=False still allows mock fallback (for testing)."""
        orchestrator = TaskOrchestrator(strict_mode=False)
        assert orchestrator.strict_mode == False, "strict_mode should be False when disabled"

    def test_l04_bridge_strict_mode_default(self):
        """Test that strict_mode can be enabled on L04Bridge."""
        bridge = L04Bridge(strict_mode=True)
        assert hasattr(bridge, 'strict_mode'), "L04Bridge should have strict_mode attribute"
        assert bridge.strict_mode == True, "strict_mode should be True when set"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

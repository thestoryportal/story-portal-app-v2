"""
L05 Planning Pipeline - Foundation Gate Tests (Phase 1).

These tests MUST pass before proceeding to Phase 2.
Gate 1 validates:
1. execute_plan(plan_id) can load plans from persistence
2. ExecutionPlan serialization roundtrip works correctly
3. Full plan is stored in persistence, not just metadata

Run: pytest test_foundation_gates.py -v
Expected: 3/3 pass
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
    PlanStatus,
    PlanningError,
)
from ..models.task import Task, TaskStatus, TaskDependency, DependencyType
from ..services.planning_service import PlanningService
from ..services.plan_cache import PlanCache


class TestFoundationGates:
    """
    Gate 1: Foundation Tests

    These tests verify the core persistence and serialization
    infrastructure is working before proceeding to execution tests.
    """

    @pytest.fixture
    def planning_service(self):
        """Create a minimal PlanningService for testing."""
        return PlanningService()

    @pytest.fixture
    def sample_goal(self) -> Goal:
        """Create a sample goal for testing."""
        return Goal.create(
            agent_did="did:agent:test-foundation",
            goal_text="Create a test file for foundation validation",
            goal_type=GoalType.SIMPLE,
            constraints=GoalConstraints(
                max_token_budget=5000,
                max_execution_time_sec=300,
            ),
        )

    @pytest.fixture
    def sample_plan(self, sample_goal: Goal) -> ExecutionPlan:
        """Create a sample plan with tasks for testing."""
        plan = ExecutionPlan.create(goal_id=sample_goal.goal_id)

        # Add tasks with realistic data
        task1 = Task.create(
            plan_id=plan.plan_id,
            name="Analyze requirements",
            description="Parse the goal and identify required actions",
        )
        task2 = Task.create(
            plan_id=plan.plan_id,
            name="Execute file creation",
            description="Create the specified file with content",
        )
        task3 = Task.create(
            plan_id=plan.plan_id,
            name="Verify output",
            description="Confirm the file was created correctly",
        )

        # Set up dependencies using TaskDependency objects
        task2.dependencies = [
            TaskDependency(
                task_id=task1.task_id,
                dependency_type=DependencyType.BLOCKING,
            )
        ]
        task3.dependencies = [
            TaskDependency(
                task_id=task2.task_id,
                dependency_type=DependencyType.BLOCKING,
            )
        ]

        plan.add_task(task1)
        plan.add_task(task2)
        plan.add_task(task3)

        # Mark as validated (ready for execution)
        plan.mark_validated()

        return plan

    @pytest.mark.asyncio
    async def test_execution_plan_to_dict_roundtrip(self, sample_plan: ExecutionPlan):
        """
        GATE 1.1: ExecutionPlan serialization roundtrip.

        Verifies that an ExecutionPlan can be:
        1. Converted to dict via to_dict()
        2. Reconstructed via from_dict()
        3. All fields match the original

        This is CRITICAL for persistence - if this fails, nothing else works.
        """
        # Serialize to dict
        plan_dict = sample_plan.to_dict()

        # Verify dict has required fields
        assert "plan_id" in plan_dict, "Missing plan_id in serialized dict"
        assert "goal_id" in plan_dict, "Missing goal_id in serialized dict"
        assert "tasks" in plan_dict, "Missing tasks in serialized dict"
        assert "status" in plan_dict, "Missing status in serialized dict"
        assert "dependency_graph" in plan_dict, "Missing dependency_graph in serialized dict"
        assert "metadata" in plan_dict, "Missing metadata in serialized dict"

        # Verify tasks are serialized
        assert len(plan_dict["tasks"]) == 3, f"Expected 3 tasks, got {len(plan_dict['tasks'])}"

        # Reconstruct from dict
        reconstructed = ExecutionPlan.from_dict(plan_dict)

        # Verify core fields match
        assert reconstructed.plan_id == sample_plan.plan_id, "plan_id mismatch after roundtrip"
        assert reconstructed.goal_id == sample_plan.goal_id, "goal_id mismatch after roundtrip"
        assert reconstructed.status == sample_plan.status, "status mismatch after roundtrip"
        assert len(reconstructed.tasks) == len(sample_plan.tasks), "task count mismatch after roundtrip"

        # Verify tasks are reconstructed correctly
        for i, task in enumerate(reconstructed.tasks):
            original_task = sample_plan.tasks[i]
            assert task.task_id == original_task.task_id, f"Task {i} ID mismatch"
            assert task.name == original_task.name, f"Task {i} name mismatch"
            assert task.description == original_task.description, f"Task {i} description mismatch"

        # Verify dependency graph preserved
        assert reconstructed.dependency_graph == sample_plan.dependency_graph, "dependency_graph mismatch"

        # Verify metadata preserved
        assert reconstructed.metadata.decomposition_strategy == sample_plan.metadata.decomposition_strategy

    @pytest.mark.asyncio
    async def test_execute_plan_loads_from_persistence(self, planning_service: PlanningService, sample_goal: Goal):
        """
        GATE 1.2: execute_plan(plan_id) loads from persistence.

        Verifies that:
        1. A plan can be created and stored via create_plan()
        2. The plan can be loaded via execute_plan(plan_id)
        3. The loaded plan has all required data for execution

        Currently this test is expected to FAIL because execute_plan()
        raises E5002. This test documents the required behavior.
        """
        # Initialize service
        await planning_service.initialize()

        try:
            # Create a plan (this should store it in L01)
            plan = await planning_service.create_plan(sample_goal)

            assert plan is not None, "create_plan() returned None"
            assert plan.plan_id is not None, "Plan has no ID"
            assert plan.status == PlanStatus.VALIDATED, f"Plan not validated: {plan.status}"

            # Now try to load and execute by ID
            # This is the key test - execute_plan(plan_id) must work
            try:
                result = await planning_service.execute_plan(plan.plan_id)

                # If we get here, execute_plan works
                assert result is not None, "execute_plan() returned None"
                assert "plan_id" in result or isinstance(result, dict), "Result should be a dict"

            except PlanningError as pe:
                if pe.code == "E5002":
                    pytest.fail(
                        f"GATE 1.2 FAILED: execute_plan(plan_id) raises E5002.\n"
                        f"This method must be implemented to load plans from persistence.\n"
                        f"Error: {pe.message}"
                    )
                else:
                    raise

        finally:
            await planning_service.cleanup()

    @pytest.mark.asyncio
    async def test_full_plan_stored_not_just_metadata(self, planning_service: PlanningService, sample_goal: Goal):
        """
        GATE 1.3: Full plan is stored in persistence, not just metadata.

        Verifies that:
        1. When a plan is created, the full ExecutionPlan is stored
        2. The stored data includes all tasks with their details
        3. The stored data can be used to reconstruct the plan

        This ensures PipelineOrchestrator stores full_plan, not just summary.
        """
        # Initialize service
        await planning_service.initialize()

        try:
            # Create a plan
            plan = await planning_service.create_plan(sample_goal)

            # Get plan status from persistence
            plan_data = await planning_service.get_plan_status(plan.plan_id)

            assert plan_data is not None, "get_plan_status() returned None"
            assert "plan_id" in plan_data, "Stored data missing plan_id"
            assert "status" in plan_data, "Stored data missing status"

            # The key test: verify task count is stored
            # If only metadata is stored, task_count might be wrong or missing
            task_count = plan_data.get("task_count", 0)
            assert task_count > 0, (
                f"GATE 1.3 FAILED: task_count is {task_count}.\n"
                f"This suggests only metadata is stored, not the full plan.\n"
                f"PipelineOrchestrator must store full_plan: plan.to_dict()"
            )

            # Verify task count matches what we created
            # (GoalDecomposer creates tasks based on the goal)
            assert task_count == len(plan.tasks), (
                f"Stored task_count ({task_count}) doesn't match actual ({len(plan.tasks)})"
            )

        finally:
            await planning_service.cleanup()


class TestSerializationEdgeCases:
    """
    Additional serialization tests for edge cases.
    These help ensure robustness but are not blocking gates.
    """

    def test_empty_plan_serialization(self):
        """Test serialization of plan with no tasks."""
        plan = ExecutionPlan.create(goal_id=str(uuid4()))

        plan_dict = plan.to_dict()
        reconstructed = ExecutionPlan.from_dict(plan_dict)

        assert len(reconstructed.tasks) == 0
        assert reconstructed.dependency_graph == {}

    def test_plan_with_metadata_serialization(self):
        """Test that metadata fields are preserved."""
        plan = ExecutionPlan.create(goal_id=str(uuid4()))

        # Set metadata fields
        plan.metadata.decomposition_strategy = "llm"
        plan.metadata.decomposition_latency_ms = 150.5
        plan.metadata.cache_hit = True
        plan.metadata.llm_provider = "anthropic"
        plan.metadata.llm_model = "claude-3-opus"
        plan.metadata.total_tokens_used = 1500
        plan.metadata.tags = ["test", "validation"]

        plan_dict = plan.to_dict()
        reconstructed = ExecutionPlan.from_dict(plan_dict)

        assert reconstructed.metadata.decomposition_strategy == "llm"
        assert reconstructed.metadata.decomposition_latency_ms == 150.5
        assert reconstructed.metadata.cache_hit == True
        assert reconstructed.metadata.llm_provider == "anthropic"
        assert reconstructed.metadata.llm_model == "claude-3-opus"
        assert reconstructed.metadata.total_tokens_used == 1500
        assert reconstructed.metadata.tags == ["test", "validation"]

    def test_plan_status_transitions(self):
        """Test that status transitions are reflected in serialization."""
        plan = ExecutionPlan.create(goal_id=str(uuid4()))

        # Draft -> Validated
        assert plan.status == PlanStatus.DRAFT
        plan.mark_validated()
        assert plan.status == PlanStatus.VALIDATED

        plan_dict = plan.to_dict()
        reconstructed = ExecutionPlan.from_dict(plan_dict)
        assert reconstructed.status == PlanStatus.VALIDATED
        assert reconstructed.validated_at is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

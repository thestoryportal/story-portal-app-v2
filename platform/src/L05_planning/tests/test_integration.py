"""
L05 Planning Layer - Integration Tests.

End-to-end integration tests for L05 components.
"""

import pytest
from ..services import PlanningService
from ..models import Goal, GoalType


@pytest.mark.asyncio
async def test_simple_goal_integration(simple_goal: Goal):
    """Test end-to-end simple goal processing."""
    service = PlanningService()
    await service.initialize()

    try:
        # Create plan
        plan = await service.create_plan(simple_goal)

        assert plan is not None
        assert plan.plan_id is not None
        assert len(plan.tasks) > 0
        assert plan.status.value == "validated"

        # Get stats
        stats = service.get_stats()
        assert stats["service"]["plans_created"] == 1

    finally:
        await service.cleanup()


@pytest.mark.asyncio
async def test_template_decomposition(simple_goal: Goal):
    """Test template-based decomposition."""
    service = PlanningService()
    await service.initialize()

    try:
        # Force template strategy
        simple_goal.decomposition_strategy = "template"

        # Create plan
        plan = await service.create_plan(simple_goal)

        assert plan is not None
        assert plan.metadata.decomposition_strategy == "template"

    finally:
        await service.cleanup()


@pytest.mark.asyncio
async def test_plan_validation():
    """Test plan validation."""
    service = PlanningService()
    await service.initialize()

    try:
        # Create goal with very short timeout
        goal = Goal.create(
            agent_did="did:agent:test",
            goal_text="Test validation",
        )

        # Should still create valid plan
        plan = await service.create_plan(goal)
        assert plan.status.value == "validated"

    finally:
        await service.cleanup()


@pytest.mark.asyncio
async def test_plan_execution_mock(mock_goal: Goal):
    """Test plan execution with mock tasks."""
    service = PlanningService()
    await service.initialize()

    try:
        # Create plan
        plan = await service.create_plan(mock_goal)

        # Execute plan (with mock execution)
        result = await service.execute_plan_direct(plan)

        assert result is not None
        assert "plan_id" in result
        assert "status" in result

    finally:
        await service.cleanup()

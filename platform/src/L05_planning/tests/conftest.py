"""
L05 Planning Layer - Test Configuration.

Pytest fixtures for testing L05 components.
"""

import pytest
import asyncio
from typing import AsyncGenerator
from uuid import uuid4

from ..models import Goal, GoalType, GoalConstraints, Task, ExecutionPlan
from ..services import (
    GoalDecomposer,
    DependencyResolver,
    PlanValidator,
    ResourceEstimator,
    TaskOrchestrator,
    ContextInjector,
    AgentAssigner,
    ExecutionMonitor,
    PlanCache,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_goal() -> Goal:
    """Create a mock goal for testing."""
    return Goal.create(
        agent_did="did:agent:test",
        goal_text="Create a test plan with multiple tasks",
        goal_type=GoalType.COMPOUND,
        constraints=GoalConstraints(
            max_token_budget=10000,
            max_execution_time_sec=600,
        ),
    )


@pytest.fixture
def simple_goal() -> Goal:
    """Create a simple goal for testing."""
    return Goal.create(
        agent_did="did:agent:test",
        goal_text="What is the current date",
        goal_type=GoalType.SIMPLE,
    )


@pytest.fixture
def mock_plan(mock_goal: Goal) -> ExecutionPlan:
    """Create a mock execution plan."""
    plan = ExecutionPlan.create(goal_id=mock_goal.goal_id)

    # Add tasks
    task1 = Task.create(
        plan_id=plan.plan_id,
        name="Task 1",
        description="First task",
    )
    task2 = Task.create(
        plan_id=plan.plan_id,
        name="Task 2",
        description="Second task",
    )
    task3 = Task.create(
        plan_id=plan.plan_id,
        name="Task 3",
        description="Third task",
    )

    plan.add_task(task1)
    plan.add_task(task2)
    plan.add_task(task3)

    return plan


@pytest.fixture
def plan_cache() -> PlanCache:
    """Create a plan cache for testing."""
    return PlanCache(
        l1_max_size=10,
        l2_ttl_seconds=60,
        enable_l2=False,  # Disable Redis for tests
    )


@pytest.fixture
def goal_decomposer(plan_cache: PlanCache) -> GoalDecomposer:
    """Create a goal decomposer for testing."""
    return GoalDecomposer(
        cache=plan_cache,
        gateway_client=None,  # Mock gateway
        default_strategy="template",  # Use template for faster tests
    )


@pytest.fixture
def dependency_resolver() -> DependencyResolver:
    """Create a dependency resolver for testing."""
    return DependencyResolver()


@pytest.fixture
def resource_estimator() -> ResourceEstimator:
    """Create a resource estimator for testing."""
    return ResourceEstimator()


@pytest.fixture
def plan_validator(
    resource_estimator: ResourceEstimator,
    dependency_resolver: DependencyResolver,
) -> PlanValidator:
    """Create a plan validator for testing."""
    return PlanValidator(
        resource_estimator=resource_estimator,
        dependency_resolver=dependency_resolver,
    )


@pytest.fixture
def task_orchestrator(dependency_resolver: DependencyResolver) -> TaskOrchestrator:
    """Create a task orchestrator for testing."""
    return TaskOrchestrator(
        dependency_resolver=dependency_resolver,
        max_parallel_tasks=5,
    )


@pytest.fixture
def context_injector() -> ContextInjector:
    """Create a context injector for testing."""
    return ContextInjector(enable_secrets=False)


@pytest.fixture
def agent_assigner() -> AgentAssigner:
    """Create an agent assigner for testing."""
    return AgentAssigner()


@pytest.fixture
def execution_monitor() -> ExecutionMonitor:
    """Create an execution monitor for testing."""
    return ExecutionMonitor(enable_events=False)


@pytest.fixture
async def cleanup_timeout():
    """Fixture to ensure test cleanup happens within timeout."""
    yield
    # Allow 2 seconds for cleanup
    await asyncio.sleep(0.1)

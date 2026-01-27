"""
L05 Planning Layer - Test Configuration.

Pytest fixtures for testing L05 components.
Uses direct imports to avoid triggering cross-layer import chains.
"""

import pytest
import asyncio
from typing import AsyncGenerator
from uuid import uuid4

# Import models directly
from ..models import Goal, GoalType, GoalConstraints, Task, ExecutionPlan

# Import services directly from their modules to avoid cross-layer import chains
from ..services.goal_decomposer import GoalDecomposer
from ..services.dependency_resolver import DependencyResolver
from ..services.plan_validator import PlanValidator
from ..services.resource_estimator import ResourceEstimator
from ..services.task_orchestrator import TaskOrchestrator
from ..services.context_injector import ContextInjector
from ..services.agent_assigner import AgentAssigner
from ..services.execution_monitor import ExecutionMonitor
from ..services.plan_cache import PlanCache
from ..services.unit_executor import UnitExecutor
from ..services.pipeline_orchestrator import PipelineOrchestrator
from ..services.model_router import ModelRouter
from ..services.execution_replay import ExecutionReplay
from ..services.resume_manager import ResumeManager
from ..services.error_handler import ErrorHandler


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_goal() -> Goal:
    """Create a mock goal for testing that matches Simple Query template."""
    return Goal.create(
        agent_did="did:agent:test",
        goal_text="What is the status of the test system",
        goal_type=GoalType.SIMPLE,  # Simple for template matching
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


@pytest.fixture
def unit_executor(tmp_path) -> UnitExecutor:
    """Create a unit executor for testing."""
    return UnitExecutor(
        working_dir=tmp_path,
        sandbox=True,
        dry_run=True,
        default_timeout=30,
    )


@pytest.fixture
def execution_replay(tmp_path) -> ExecutionReplay:
    """Create an execution replay for testing."""
    return ExecutionReplay(
        storage_path=tmp_path / ".l05_replay",
        max_frames_per_execution=100,
        persist_frames=True,
    )


@pytest.fixture
def resume_manager(tmp_path) -> ResumeManager:
    """Create a resume manager for testing."""
    return ResumeManager(
        storage_path=tmp_path / ".l05_resume",
        stale_threshold_hours=24,
        max_stored_executions=100,
    )


@pytest.fixture
def error_handler() -> ErrorHandler:
    """Create an error handler for testing."""
    return ErrorHandler(
        recovery_protocol=None,
        compensation_engine=None,
        auto_recover=False,
        max_retries=3,
    )


@pytest.fixture
def model_router() -> ModelRouter:
    """Create a model router for testing."""
    return ModelRouter(
        l04_bridge=None,
        quality_threshold=0.7,
        prefer_local=True,
    )

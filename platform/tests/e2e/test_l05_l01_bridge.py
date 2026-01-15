"""
E2E tests for L05 Planning Layer - L01 Data Layer bridge integration.

Tests the complete flow of recording goals, plans, and tasks in L01.
"""

import pytest
import asyncio
import httpx
import json
from datetime import datetime
from uuid import uuid4

from src.L05_planning.services.l01_bridge import L05Bridge
from src.L05_planning.models import (
    Goal,
    GoalType,
    GoalStatus,
    GoalConstraints,
    ExecutionPlan,
    PlanStatus,
    PlanMetadata,
    Task,
    TaskType,
    TaskStatus,
    ResourceConstraints
)
from src.L01_data_layer.client import L01Client


@pytest.mark.asyncio
class TestL05L01Integration:
    """Test L05-L01 integration end-to-end."""

    @pytest.fixture
    async def bridge(self):
        """Create L05Bridge instance."""
        bridge = L05Bridge(l01_base_url="http://localhost:8002")
        await bridge.initialize()
        yield bridge
        await bridge.cleanup()

    @pytest.fixture
    async def l01_client(self):
        """Create L01Client instance for verification."""
        client = L01Client(base_url="http://localhost:8002")
        yield client
        await client.close()

    async def test_bridge_initialization(self, bridge):
        """Test that L05Bridge initializes correctly."""
        assert bridge is not None
        assert bridge.l01_client is not None
        assert bridge.enabled is True

    async def test_record_simple_goal(self, bridge, l01_client):
        """Test recording a simple goal."""
        # Create goal
        goal = Goal(
            goal_id=f"goal-{uuid4()}",
            agent_did="did:example:test-agent-123",
            goal_text="Complete the user registration workflow",
            goal_type=GoalType.SIMPLE,
            status=GoalStatus.PENDING,
            constraints=GoalConstraints(
                max_token_budget=5000,
                max_execution_time_sec=300,
                max_parallelism=5,
                priority=7,
                require_approval=False
            ),
            metadata={"context": "e2e-test"}
        )

        # Record in L01
        result = await bridge.record_goal(goal)
        assert result is True

        # Verify record was created in L01
        await asyncio.sleep(0.1)  # Allow async write to complete

        # Query L01 to verify
        async with httpx.AsyncClient() as client:
            http_response = await client.get(f"http://localhost:8002/goals/{goal.goal_id}")
            http_response.raise_for_status()
            record = http_response.json()

        assert record["goal_id"] == goal.goal_id
        assert record["agent_did"] == "did:example:test-agent-123"
        assert record["goal_text"] == "Complete the user registration workflow"
        assert record["goal_type"] == "simple"
        assert record["status"] == "pending"
        assert record["constraints_max_token_budget"] == 5000
        assert record["constraints_max_execution_time_sec"] == 300
        assert record["constraints_max_parallelism"] == 5
        assert record["constraints_priority"] == 7
        assert record["constraints_require_approval"] is False

    async def test_record_compound_goal_with_parent(self, bridge, l01_client):
        """Test recording a compound goal with parent relationship."""
        # Create parent goal
        parent_goal = Goal(
            goal_id=f"parent-goal-{uuid4()}",
            agent_did="did:example:test-agent-456",
            goal_text="Build complete e-commerce platform",
            goal_type=GoalType.COMPOUND,
            status=GoalStatus.DECOMPOSING,
            constraints=GoalConstraints(
                max_token_budget=50000,
                cost_limit_usd=10.0
            )
        )

        # Record parent goal
        await bridge.record_goal(parent_goal)

        # Create child goal
        child_goal = Goal(
            goal_id=f"child-goal-{uuid4()}",
            agent_did="did:example:test-agent-456",
            goal_text="Implement payment processing",
            goal_type=GoalType.SIMPLE,
            status=GoalStatus.PENDING,
            parent_goal_id=parent_goal.goal_id,
            decomposition_strategy="sequential",
            constraints=GoalConstraints(max_token_budget=10000)
        )

        # Record child goal
        result = await bridge.record_goal(child_goal)
        assert result is True

        # Verify child goal
        await asyncio.sleep(0.1)
        async with httpx.AsyncClient() as client:
            http_response = await client.get(f"http://localhost:8002/goals/{child_goal.goal_id}")
            http_response.raise_for_status()
            record = http_response.json()

        assert record["goal_id"] == child_goal.goal_id
        assert record["parent_goal_id"] == parent_goal.goal_id
        assert record["decomposition_strategy"] == "sequential"

    async def test_update_goal_status(self, bridge, l01_client):
        """Test updating goal status."""
        # Create and record goal
        goal = Goal(
            goal_id=f"goal-status-{uuid4()}",
            agent_did="did:example:test-agent-789",
            goal_text="Test goal status updates",
            goal_type=GoalType.SIMPLE,
            status=GoalStatus.PENDING
        )
        await bridge.record_goal(goal)
        await asyncio.sleep(0.1)

        # Update status to DECOMPOSING
        result = await bridge.update_goal_status(
            goal_id=goal.goal_id,
            status=GoalStatus.DECOMPOSING.value,
            decomposition_strategy="hybrid"
        )
        assert result is True

        # Verify update
        await asyncio.sleep(0.1)
        async with httpx.AsyncClient() as client:
            http_response = await client.get(f"http://localhost:8002/goals/{goal.goal_id}")
            http_response.raise_for_status()
            record = http_response.json()

        assert record["status"] == "decomposing"
        assert record["decomposition_strategy"] == "hybrid"

    async def test_record_execution_plan(self, bridge, l01_client):
        """Test recording an execution plan with tasks."""
        # Create goal first
        goal = Goal(
            goal_id=f"goal-plan-{uuid4()}",
            agent_did="did:example:test-agent-999",
            goal_text="Create API endpoint",
            goal_type=GoalType.COMPOUND,
            status=GoalStatus.READY
        )
        await bridge.record_goal(goal)

        # Create plan ID
        plan_id = f"plan-{uuid4()}"

        # Create tasks
        task1 = Task(
            task_id=f"task-{uuid4()}",
            plan_id=plan_id,
            name="Design API schema",
            description="Design the API endpoint schema",
            task_type=TaskType.LLM_CALL,
            status=TaskStatus.PENDING,
            timeout_seconds=120,
            metadata={"priority": "high"}
        )

        task2 = Task(
            task_id=f"task-{uuid4()}",
            plan_id=plan_id,
            name="Implement endpoint",
            description="Write the API endpoint code",
            task_type=TaskType.TOOL_CALL,
            status=TaskStatus.PENDING,
            dependencies=[task1],
            tool_name="code_writer",
            timeout_seconds=300
        )

        # Create execution plan
        plan = ExecutionPlan(
            plan_id=plan_id,
            goal_id=goal.goal_id,
            tasks=[task1, task2],
            dependency_graph={
                task2.task_id: [task1.task_id]
            },
            status=PlanStatus.VALIDATED,
            resource_budget=ResourceConstraints(
                max_token_count=8000,
                max_execution_time_sec=600,
                max_parallel_tasks=2
            ),
            validated_at=datetime.utcnow(),
            metadata=PlanMetadata(
                decomposition_strategy="hybrid",
                decomposition_latency_ms=245.5,
                cache_hit=False,
                llm_provider="ollama",
                llm_model="qwen2.5:latest",
                total_tokens_used=1234,
                validation_time_ms=89.3,
                tags=["api", "backend"]
            )
        )

        # Record plan in L01
        result = await bridge.record_plan(plan)
        assert result is True

        # Verify plan was created
        await asyncio.sleep(0.1)
        async with httpx.AsyncClient() as client:
            http_response = await client.get(f"http://localhost:8002/plans/{plan.plan_id}")
            http_response.raise_for_status()
            record = http_response.json()

        assert record["plan_id"] == plan.plan_id
        assert record["goal_id"] == goal.goal_id
        assert record["status"] == "validated"
        assert record["decomposition_strategy"] == "hybrid"
        assert float(record["decomposition_latency_ms"]) == 245.5
        assert record["cache_hit"] is False
        assert record["llm_provider"] == "ollama"
        assert record["llm_model"] == "qwen2.5:latest"
        assert record["total_tokens_used"] == 1234
        assert float(record["validation_time_ms"]) == 89.3
        assert "api" in record["tags"]
        assert "backend" in record["tags"]

        # Verify tasks are in the tasks JSONB field (parse if string)
        tasks_data = record["tasks"]
        if isinstance(tasks_data, str):
            tasks_data = json.loads(tasks_data)
        assert len(tasks_data) == 2
        assert tasks_data[0]["task_id"] == task1.task_id
        assert tasks_data[0]["name"] == "Design API schema"
        assert tasks_data[0]["task_type"] == "llm_call"
        assert tasks_data[1]["task_id"] == task2.task_id
        assert tasks_data[1]["name"] == "Implement endpoint"
        assert tasks_data[1]["task_type"] == "tool_call"
        assert tasks_data[1]["tool_name"] == "code_writer"
        assert task1.task_id in tasks_data[1]["dependencies"]

        # Verify dependency graph (parse if string)
        dep_graph = record["dependency_graph"]
        if isinstance(dep_graph, str):
            dep_graph = json.loads(dep_graph)
        assert task2.task_id in dep_graph
        assert task1.task_id in dep_graph[task2.task_id]

    async def test_update_plan_execution_lifecycle(self, bridge, l01_client):
        """Test updating plan status through execution lifecycle."""
        # Create goal and plan
        goal = Goal(
            goal_id=f"goal-lifecycle-{uuid4()}",
            agent_did="did:example:lifecycle-agent",
            goal_text="Test plan execution lifecycle",
            goal_type=GoalType.SIMPLE,
            status=GoalStatus.READY
        )
        await bridge.record_goal(goal)

        # Create plan ID
        plan_id = f"plan-lifecycle-{uuid4()}"

        task = Task(
            task_id=f"task-{uuid4()}",
            plan_id=plan_id,
            name="Execute test",
            description="Run test execution",
            task_type=TaskType.ATOMIC,
            status=TaskStatus.PENDING
        )

        plan = ExecutionPlan(
            plan_id=plan_id,
            goal_id=goal.goal_id,
            tasks=[task],
            status=PlanStatus.VALIDATED,
            validated_at=datetime.utcnow(),
            metadata=PlanMetadata(decomposition_strategy="simple")
        )

        await bridge.record_plan(plan)
        await asyncio.sleep(0.1)

        # Update 1: Start execution
        execution_start = datetime.utcnow()
        result = await bridge.update_plan_status(
            plan_id=plan.plan_id,
            status=PlanStatus.EXECUTING.value,
            execution_started_at=execution_start
        )
        assert result is True

        await asyncio.sleep(0.1)
        async with httpx.AsyncClient() as client:
            http_response = await client.get(f"http://localhost:8002/plans/{plan.plan_id}")
            http_response.raise_for_status()
            record = http_response.json()

        assert record["status"] == "executing"
        assert record["execution_started_at"] is not None

        # Update 2: Complete execution
        execution_end = datetime.utcnow()
        execution_time_ms = (execution_end - execution_start).total_seconds() * 1000

        result = await bridge.update_plan_status(
            plan_id=plan.plan_id,
            status=PlanStatus.COMPLETED.value,
            execution_completed_at=execution_end,
            execution_time_ms=execution_time_ms,
            parallelism_achieved=1,
            completed_task_count=1,
            failed_task_count=0
        )
        assert result is True

        await asyncio.sleep(0.1)
        async with httpx.AsyncClient() as client:
            http_response = await client.get(f"http://localhost:8002/plans/{plan.plan_id}")
            http_response.raise_for_status()
            record = http_response.json()

        assert record["status"] == "completed"
        assert record["execution_completed_at"] is not None
        assert float(record["execution_time_ms"]) > 0
        assert record["parallelism_achieved"] == 1
        assert record["completed_task_count"] == 1
        assert record["failed_task_count"] == 0

    async def test_update_plan_with_error(self, bridge, l01_client):
        """Test updating plan status to failed with error."""
        # Create minimal plan
        goal = Goal(
            goal_id=f"goal-error-{uuid4()}",
            agent_did="did:example:error-agent",
            goal_text="Test error handling",
            goal_type=GoalType.SIMPLE,
            status=GoalStatus.READY
        )
        await bridge.record_goal(goal)

        # Create plan ID
        plan_id = f"plan-error-{uuid4()}"

        task = Task(
            task_id=f"task-{uuid4()}",
            plan_id=plan_id,
            name="Failing task",
            description="This task will fail",
            task_type=TaskType.ATOMIC,
            status=TaskStatus.PENDING
        )

        plan = ExecutionPlan(
            plan_id=plan_id,
            goal_id=goal.goal_id,
            tasks=[task],
            status=PlanStatus.VALIDATED,
            validated_at=datetime.utcnow(),
            metadata=PlanMetadata(decomposition_strategy="simple")
        )

        await bridge.record_plan(plan)
        await asyncio.sleep(0.1)

        # Update to failed with error
        result = await bridge.update_plan_status(
            plan_id=plan.plan_id,
            status=PlanStatus.FAILED.value,
            error="Simulated execution failure: resource timeout",
            failed_task_count=1
        )
        assert result is True

        # Verify error is recorded
        await asyncio.sleep(0.1)
        async with httpx.AsyncClient() as client:
            http_response = await client.get(f"http://localhost:8002/plans/{plan.plan_id}")
            http_response.raise_for_status()
            record = http_response.json()

        assert record["status"] == "failed"
        assert record["error"] == "Simulated execution failure: resource timeout"
        assert record["failed_task_count"] == 1

    async def test_get_plan_from_l01(self, bridge, l01_client):
        """Test retrieving a plan from L01."""
        # Create and record plan
        goal = Goal(
            goal_id=f"goal-retrieve-{uuid4()}",
            agent_did="did:example:retrieve-agent",
            goal_text="Test plan retrieval",
            goal_type=GoalType.SIMPLE,
            status=GoalStatus.READY
        )
        await bridge.record_goal(goal)

        # Create plan ID
        plan_id = f"plan-retrieve-{uuid4()}"

        task = Task(
            task_id=f"task-{uuid4()}",
            plan_id=plan_id,
            name="Test task",
            description="Task for retrieval test",
            task_type=TaskType.ATOMIC,
            status=TaskStatus.PENDING
        )

        plan = ExecutionPlan(
            plan_id=plan_id,
            goal_id=goal.goal_id,
            tasks=[task],
            status=PlanStatus.DRAFT,
            metadata=PlanMetadata(decomposition_strategy="simple")
        )

        await bridge.record_plan(plan)
        await asyncio.sleep(0.1)

        # Retrieve plan via bridge
        retrieved_plan = await bridge.get_plan(plan.plan_id)
        assert retrieved_plan is not None
        assert retrieved_plan["plan_id"] == plan.plan_id
        assert retrieved_plan["goal_id"] == goal.goal_id
        assert retrieved_plan["status"] == "draft"

    async def test_bridge_disabled(self):
        """Test that disabled bridge doesn't record."""
        bridge = L05Bridge()
        bridge.enabled = False

        goal = Goal(
            goal_id=f"goal-disabled-{uuid4()}",
            agent_did="did:example:test",
            goal_text="test",
            goal_type=GoalType.SIMPLE,
            status=GoalStatus.PENDING
        )

        result = await bridge.record_goal(goal)
        assert result is False

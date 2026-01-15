"""
L05 Planning Layer - Model Tests.

Tests for core data models.
"""

import pytest
from ..models import (
    Goal,
    GoalType,
    GoalStatus,
    GoalConstraints,
    Task,
    TaskType,
    TaskStatus,
    ExecutionPlan,
    PlanStatus,
    ResourceEstimate,
    ResourceConstraints,
)


class TestGoal:
    """Test Goal model."""

    def test_goal_creation(self):
        """Test goal can be created."""
        goal = Goal.create(
            agent_did="did:agent:test",
            goal_text="Test goal",
        )

        assert goal.goal_id is not None
        assert goal.agent_did == "did:agent:test"
        assert goal.goal_text == "Test goal"
        assert goal.status == GoalStatus.PENDING

    def test_goal_validation_valid(self):
        """Test goal validation accepts valid input."""
        goal = Goal.create(
            agent_did="did:agent:test",
            goal_text="Process the user data safely",
        )

        is_valid, error_msg = goal.validate()
        assert is_valid
        assert error_msg is None

    def test_goal_validation_shell_metacharacters(self):
        """Test goal validation rejects shell metacharacters."""
        goal = Goal.create(
            agent_did="did:agent:test",
            goal_text="Process data | cat /etc/passwd",
        )

        is_valid, error_msg = goal.validate()
        assert not is_valid
        assert "shell metacharacters" in error_msg

    def test_goal_validation_sql_keywords(self):
        """Test goal validation rejects SQL keywords."""
        goal = Goal.create(
            agent_did="did:agent:test",
            goal_text="DROP TABLE users",
        )

        is_valid, error_msg = goal.validate()
        assert not is_valid
        assert "SQL keyword" in error_msg

    def test_goal_serialization(self):
        """Test goal can be serialized and deserialized."""
        goal = Goal.create(
            agent_did="did:agent:test",
            goal_text="Test goal",
        )

        # Serialize
        goal_dict = goal.to_dict()
        assert goal_dict["goal_id"] == goal.goal_id

        # Deserialize
        restored_goal = Goal.from_dict(goal_dict)
        assert restored_goal.goal_id == goal.goal_id
        assert restored_goal.goal_text == goal.goal_text


class TestTask:
    """Test Task model."""

    def test_task_creation(self):
        """Test task can be created."""
        task = Task.create(
            plan_id="plan-123",
            name="Test task",
            description="Test description",
        )

        assert task.task_id is not None
        assert task.name == "Test task"
        assert task.status == TaskStatus.PENDING

    def test_task_state_transitions(self):
        """Test task state transitions."""
        task = Task.create(
            plan_id="plan-123",
            name="Test task",
            description="Test description",
        )

        # PENDING -> READY
        task.mark_ready()
        assert task.status == TaskStatus.READY

        # READY -> EXECUTING
        task.mark_executing()
        assert task.status == TaskStatus.EXECUTING
        assert task.started_at is not None

        # EXECUTING -> COMPLETED
        task.mark_completed({"result": "success"})
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None
        assert task.outputs["result"] == "success"

    def test_task_can_execute(self):
        """Test task dependency checking."""
        task = Task.create(
            plan_id="plan-123",
            name="Test task",
            description="Test description",
        )

        # No dependencies - can execute
        completed = set()
        assert task.can_execute(completed)

        # Add dependency
        from ..models import TaskDependency, DependencyType

        task.dependencies.append(
            TaskDependency(task_id="task-1", dependency_type=DependencyType.BLOCKING)
        )

        # Dependency not completed - cannot execute
        assert not task.can_execute(completed)

        # Dependency completed - can execute
        completed.add("task-1")
        assert task.can_execute(completed)


class TestExecutionPlan:
    """Test ExecutionPlan model."""

    def test_plan_creation(self):
        """Test execution plan can be created."""
        plan = ExecutionPlan.create(goal_id="goal-123")

        assert plan.plan_id is not None
        assert plan.goal_id == "goal-123"
        assert plan.status == PlanStatus.DRAFT

    def test_plan_state_transitions(self):
        """Test plan state transitions."""
        plan = ExecutionPlan.create(goal_id="goal-123")

        # DRAFT -> VALIDATED
        plan.mark_validated()
        assert plan.status == PlanStatus.VALIDATED
        assert plan.validated_at is not None

        # VALIDATED -> EXECUTING
        plan.mark_executing()
        assert plan.status == PlanStatus.EXECUTING
        assert plan.execution_started_at is not None

        # EXECUTING -> COMPLETED
        plan.mark_completed()
        assert plan.status == PlanStatus.COMPLETED
        assert plan.execution_completed_at is not None

    def test_plan_task_management(self):
        """Test plan task management."""
        plan = ExecutionPlan.create(goal_id="goal-123")

        task1 = Task.create(
            plan_id=plan.plan_id, name="Task 1", description="First task"
        )
        task2 = Task.create(
            plan_id=plan.plan_id, name="Task 2", description="Second task"
        )

        plan.add_task(task1)
        plan.add_task(task2)

        assert len(plan.tasks) == 2
        assert plan.get_task(task1.task_id) == task1
        assert plan.get_task(task2.task_id) == task2


class TestResourceModels:
    """Test resource models."""

    def test_resource_estimate(self):
        """Test resource estimate model."""
        estimate = ResourceEstimate(
            cpu_cores=2.0,
            memory_mb=1024,
            execution_time_sec=120,
            token_count=1000,
            cost_usd=0.01,
        )

        assert estimate.cpu_cores == 2.0
        assert estimate.memory_mb == 1024
        assert estimate.token_count == 1000

    def test_resource_constraints_validation(self):
        """Test resource constraints validation."""
        constraints = ResourceConstraints(
            max_cpu_cores=4.0,
            max_memory_mb=2048,
            max_token_count=10000,
        )

        # Within budget
        estimate1 = ResourceEstimate(cpu_cores=2.0, memory_mb=1024, token_count=5000)
        is_valid, error = constraints.is_within_budget(estimate1)
        assert is_valid

        # Exceeds budget
        estimate2 = ResourceEstimate(cpu_cores=8.0, memory_mb=1024, token_count=5000)
        is_valid, error = constraints.is_within_budget(estimate2)
        assert not is_valid
        assert "CPU" in error

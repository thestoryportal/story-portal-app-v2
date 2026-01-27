"""
L05 Planning Layer - Task Data Model.

Represents atomic or compound units of work within an execution plan.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List
from uuid import uuid4


class TaskType(str, Enum):
    """Type of task indicating execution method."""

    ATOMIC = "atomic"  # Single indivisible operation
    COMPOUND = "compound"  # Task composed of subtasks
    TOOL_CALL = "tool_call"  # Invokes a specific tool (via L03)
    LLM_CALL = "llm_call"  # Requires LLM inference (via L04)


class TaskStatus(str, Enum):
    """Status of task in execution lifecycle."""

    PENDING = "pending"  # Task created, dependencies not satisfied
    READY = "ready"  # Dependencies satisfied, ready to execute
    EXECUTING = "executing"  # Currently being executed
    COMPLETED = "completed"  # Successfully completed
    FAILED = "failed"  # Execution failed
    BLOCKED = "blocked"  # Cannot proceed due to failed dependency


class DependencyType(str, Enum):
    """Type of dependency between tasks."""

    BLOCKING = "blocking"  # Task B cannot start until Task A completes
    CONDITIONAL = "conditional"  # Task B starts only if Task A succeeds with condition
    DATA = "data"  # Task B needs output data from Task A


@dataclass
class TaskDependency:
    """Represents a dependency relationship between tasks."""

    task_id: str  # ID of the task being depended upon
    dependency_type: DependencyType = DependencyType.BLOCKING
    condition: Optional[str] = None  # For CONDITIONAL dependencies
    output_key: Optional[str] = None  # For DATA dependencies, which output to use


@dataclass
class RetryPolicy:
    """Retry configuration for task execution."""

    max_retries: int = 3  # Maximum retry attempts
    initial_delay_sec: float = 1.0  # Initial delay before first retry
    backoff_multiplier: float = 2.0  # Exponential backoff multiplier
    max_delay_sec: float = 60.0  # Maximum delay between retries
    retry_on_timeout: bool = True  # Retry on timeout errors
    retry_on_agent_unavailable: bool = True  # Retry when agent unavailable


@dataclass
class Task:
    """
    Represents a unit of work within an execution plan.

    Tasks are the atomic or compound operations that result from goal decomposition.
    Each task has inputs, outputs, dependencies, and execution metadata.
    """

    task_id: str  # Unique identifier (UUID)
    plan_id: str  # Parent execution plan ID
    name: str  # Human-readable task name
    description: str  # Detailed task description
    task_type: TaskType = TaskType.ATOMIC  # Type of task
    status: TaskStatus = TaskStatus.PENDING  # Current status
    dependencies: List[TaskDependency] = field(default_factory=list)  # Task dependencies
    inputs: Dict[str, Any] = field(default_factory=dict)  # Input parameters
    outputs: Dict[str, Any] = field(default_factory=dict)  # Output results
    assigned_agent: Optional[str] = None  # DID of assigned agent
    timeout_seconds: int = 300  # Execution timeout (default 5 minutes)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)  # Retry configuration
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))  # Creation timestamp
    started_at: Optional[datetime] = None  # Execution start time
    completed_at: Optional[datetime] = None  # Execution completion time
    error: Optional[str] = None  # Error message if failed
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata
    tool_name: Optional[str] = None  # For TOOL_CALL tasks
    llm_prompt: Optional[str] = None  # For LLM_CALL tasks
    retry_count: int = 0  # Current retry attempt

    @classmethod
    def create(
        cls,
        plan_id: str,
        name: str,
        description: str,
        task_type: TaskType = TaskType.ATOMIC,
        inputs: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[TaskDependency]] = None,
        timeout_seconds: int = 300,
        tool_name: Optional[str] = None,
        llm_prompt: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "Task":
        """Factory method to create a new Task with generated UUID."""
        return cls(
            task_id=str(uuid4()),
            plan_id=plan_id,
            name=name,
            description=description,
            task_type=task_type,
            status=TaskStatus.PENDING,
            dependencies=dependencies or [],
            inputs=inputs or {},
            outputs={},
            timeout_seconds=timeout_seconds,
            retry_policy=RetryPolicy(),
            created_at=datetime.now(timezone.utc),
            metadata=metadata or {},
            tool_name=tool_name,
            llm_prompt=llm_prompt,
        )

    def can_execute(self, completed_tasks: set[str]) -> bool:
        """
        Check if task can be executed based on dependency satisfaction.

        Args:
            completed_tasks: Set of task IDs that have completed successfully

        Returns:
            True if all dependencies are satisfied, False otherwise
        """
        if self.status != TaskStatus.PENDING:
            return False

        for dep in self.dependencies:
            if dep.task_id not in completed_tasks:
                return False

        return True

    def mark_ready(self) -> None:
        """Mark task as ready for execution."""
        if self.status == TaskStatus.PENDING:
            self.status = TaskStatus.READY

    def mark_executing(self) -> None:
        """Mark task as currently executing."""
        if self.status == TaskStatus.READY:
            self.status = TaskStatus.EXECUTING
            self.started_at = datetime.now(timezone.utc)

    def mark_completed(self, outputs: Optional[Dict[str, Any]] = None) -> None:
        """Mark task as successfully completed."""
        if self.status == TaskStatus.EXECUTING:
            self.status = TaskStatus.COMPLETED
            self.completed_at = datetime.now(timezone.utc)
            if outputs:
                self.outputs = outputs

    def mark_failed(self, error: str) -> None:
        """Mark task as failed with error message."""
        if self.status in (TaskStatus.EXECUTING, TaskStatus.READY):
            self.status = TaskStatus.FAILED
            self.completed_at = datetime.now(timezone.utc)
            self.error = error

    def mark_blocked(self) -> None:
        """Mark task as blocked due to failed dependency."""
        if self.status in (TaskStatus.PENDING, TaskStatus.READY):
            self.status = TaskStatus.BLOCKED

    def should_retry(self) -> bool:
        """Check if task should be retried after failure."""
        if self.status != TaskStatus.FAILED:
            return False
        return self.retry_count < self.retry_policy.max_retries

    def get_retry_delay(self) -> float:
        """Calculate retry delay based on backoff policy."""
        delay = self.retry_policy.initial_delay_sec * (
            self.retry_policy.backoff_multiplier ** self.retry_count
        )
        return min(delay, self.retry_policy.max_delay_sec)

    def to_dict(self) -> Dict[str, Any]:
        """Convert Task to dictionary representation."""
        return {
            "task_id": self.task_id,
            "plan_id": self.plan_id,
            "name": self.name,
            "description": self.description,
            "task_type": self.task_type.value,
            "status": self.status.value,
            "dependencies": [
                {
                    "task_id": dep.task_id,
                    "dependency_type": dep.dependency_type.value,
                    "condition": dep.condition,
                    "output_key": dep.output_key,
                }
                for dep in self.dependencies
            ],
            "inputs": self.inputs,
            "outputs": self.outputs,
            "assigned_agent": self.assigned_agent,
            "timeout_seconds": self.timeout_seconds,
            "retry_policy": {
                "max_retries": self.retry_policy.max_retries,
                "initial_delay_sec": self.retry_policy.initial_delay_sec,
                "backoff_multiplier": self.retry_policy.backoff_multiplier,
                "max_delay_sec": self.retry_policy.max_delay_sec,
                "retry_on_timeout": self.retry_policy.retry_on_timeout,
                "retry_on_agent_unavailable": self.retry_policy.retry_on_agent_unavailable,
            },
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "metadata": self.metadata,
            "tool_name": self.tool_name,
            "llm_prompt": self.llm_prompt,
            "retry_count": self.retry_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create Task from dictionary representation."""
        dependencies = [
            TaskDependency(
                task_id=dep["task_id"],
                dependency_type=DependencyType(dep.get("dependency_type", "blocking")),
                condition=dep.get("condition"),
                output_key=dep.get("output_key"),
            )
            for dep in data.get("dependencies", [])
        ]

        retry_policy_data = data.get("retry_policy", {})
        retry_policy = RetryPolicy(
            max_retries=retry_policy_data.get("max_retries", 3),
            initial_delay_sec=retry_policy_data.get("initial_delay_sec", 1.0),
            backoff_multiplier=retry_policy_data.get("backoff_multiplier", 2.0),
            max_delay_sec=retry_policy_data.get("max_delay_sec", 60.0),
            retry_on_timeout=retry_policy_data.get("retry_on_timeout", True),
            retry_on_agent_unavailable=retry_policy_data.get("retry_on_agent_unavailable", True),
        )

        return cls(
            task_id=data["task_id"],
            plan_id=data["plan_id"],
            name=data["name"],
            description=data["description"],
            task_type=TaskType(data.get("task_type", "atomic")),
            status=TaskStatus(data.get("status", "pending")),
            dependencies=dependencies,
            inputs=data.get("inputs", {}),
            outputs=data.get("outputs", {}),
            assigned_agent=data.get("assigned_agent"),
            timeout_seconds=data.get("timeout_seconds", 300),
            retry_policy=retry_policy,
            created_at=datetime.fromisoformat(data["created_at"]),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            error=data.get("error"),
            metadata=data.get("metadata", {}),
            tool_name=data.get("tool_name"),
            llm_prompt=data.get("llm_prompt"),
            retry_count=data.get("retry_count", 0),
        )

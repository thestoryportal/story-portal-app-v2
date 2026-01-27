"""
L05 Planning Layer - Execution Plan Data Model.

Represents a complete plan with tasks, dependencies, and execution metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List
from uuid import uuid4

from .task import Task
from .resource import ResourceConstraints


class PlanStatus(str, Enum):
    """Status of execution plan in its lifecycle."""

    DRAFT = "draft"  # Plan created, not yet validated
    VALIDATED = "validated"  # Plan passed validation, ready for execution
    EXECUTING = "executing"  # Plan is currently executing
    COMPLETED = "completed"  # All tasks completed successfully
    FAILED = "failed"  # Plan execution failed
    CANCELLED = "cancelled"  # Plan execution cancelled


@dataclass
class PlanMetadata:
    """Metadata about plan creation and execution."""

    decomposition_strategy: str = "hybrid"  # "llm", "template", "hybrid"
    decomposition_latency_ms: Optional[float] = None  # Time to decompose
    cache_hit: bool = False  # Whether plan came from cache
    llm_provider: Optional[str] = None  # LLM provider used (if any)
    llm_model: Optional[str] = None  # LLM model used (if any)
    total_tokens_used: int = 0  # Total tokens consumed
    validation_time_ms: Optional[float] = None  # Time to validate
    execution_time_ms: Optional[float] = None  # Total execution time
    parallelism_achieved: int = 1  # Max concurrent tasks executed
    tags: List[str] = field(default_factory=list)  # Custom tags


@dataclass
class ExecutionPlan:
    """
    Represents a complete execution plan with tasks and dependencies.

    An ExecutionPlan is the output of goal decomposition. It contains all tasks
    needed to accomplish a goal, their dependencies, resource requirements, and
    execution metadata.
    """

    plan_id: str  # Unique identifier (UUID)
    goal_id: str  # Source goal that generated this plan
    tasks: List[Task] = field(default_factory=list)  # List of all tasks
    dependency_graph: Dict[str, List[str]] = field(default_factory=dict)  # Adjacency list
    status: PlanStatus = PlanStatus.DRAFT  # Current status
    resource_budget: Optional[ResourceConstraints] = None  # Resource limits
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))  # Creation time
    validated_at: Optional[datetime] = None  # Validation time
    execution_started_at: Optional[datetime] = None  # Execution start time
    execution_completed_at: Optional[datetime] = None  # Execution completion time
    signature: Optional[str] = None  # HMAC-SHA256 signature for integrity
    metadata: PlanMetadata = field(default_factory=PlanMetadata)  # Additional metadata
    error: Optional[str] = None  # Error message if failed
    completed_task_count: int = 0  # Number of completed tasks
    failed_task_count: int = 0  # Number of failed tasks

    @classmethod
    def create(
        cls,
        goal_id: str,
        tasks: Optional[List[Task]] = None,
        dependency_graph: Optional[Dict[str, List[str]]] = None,
        resource_budget: Optional[ResourceConstraints] = None,
        metadata: Optional[PlanMetadata] = None,
    ) -> "ExecutionPlan":
        """Factory method to create a new ExecutionPlan with generated UUID."""
        return cls(
            plan_id=str(uuid4()),
            goal_id=goal_id,
            tasks=tasks or [],
            dependency_graph=dependency_graph or {},
            status=PlanStatus.DRAFT,
            resource_budget=resource_budget,
            created_at=datetime.now(timezone.utc),
            metadata=metadata or PlanMetadata(),
        )

    def add_task(self, task: Task) -> None:
        """Add a task to the plan."""
        self.tasks.append(task)
        # Initialize dependency graph entry
        if task.task_id not in self.dependency_graph:
            self.dependency_graph[task.task_id] = [dep.task_id for dep in task.dependencies]

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None

    def get_ready_tasks(self) -> List[Task]:
        """Get all tasks that are ready to execute."""
        return [task for task in self.tasks if task.status == "ready"]

    def get_executing_tasks(self) -> List[Task]:
        """Get all tasks currently executing."""
        return [task for task in self.tasks if task.status == "executing"]

    def get_completed_tasks(self) -> List[Task]:
        """Get all completed tasks."""
        return [task for task in self.tasks if task.status == "completed"]

    def get_failed_tasks(self) -> List[Task]:
        """Get all failed tasks."""
        return [task for task in self.tasks if task.status == "failed"]

    def mark_validated(self) -> None:
        """Mark plan as validated."""
        if self.status == PlanStatus.DRAFT:
            self.status = PlanStatus.VALIDATED
            self.validated_at = datetime.now(timezone.utc)

    def mark_executing(self) -> None:
        """Mark plan as executing."""
        if self.status == PlanStatus.VALIDATED:
            self.status = PlanStatus.EXECUTING
            self.execution_started_at = datetime.now(timezone.utc)

    def mark_completed(self) -> None:
        """Mark plan as completed."""
        if self.status == PlanStatus.EXECUTING:
            self.status = PlanStatus.COMPLETED
            self.execution_completed_at = datetime.now(timezone.utc)
            self.completed_task_count = len(self.get_completed_tasks())

    def mark_failed(self, error: str) -> None:
        """Mark plan as failed."""
        if self.status in (PlanStatus.EXECUTING, PlanStatus.VALIDATED):
            self.status = PlanStatus.FAILED
            self.execution_completed_at = datetime.now(timezone.utc)
            self.error = error
            self.completed_task_count = len(self.get_completed_tasks())
            self.failed_task_count = len(self.get_failed_tasks())

    def is_complete(self) -> bool:
        """Check if all tasks are completed or plan is done."""
        if self.status in (PlanStatus.COMPLETED, PlanStatus.FAILED, PlanStatus.CANCELLED):
            return True
        # Check if all tasks are in terminal state
        for task in self.tasks:
            if task.status not in ("completed", "failed", "blocked"):
                return False
        return True

    def get_progress(self) -> float:
        """Get execution progress as percentage (0.0 to 1.0)."""
        if not self.tasks:
            return 0.0
        completed = len(self.get_completed_tasks())
        return completed / len(self.tasks)

    def to_dict(self) -> Dict[str, Any]:
        """Convert ExecutionPlan to dictionary representation."""
        return {
            "plan_id": self.plan_id,
            "goal_id": self.goal_id,
            "tasks": [task.to_dict() for task in self.tasks],
            "dependency_graph": self.dependency_graph,
            "status": self.status.value,
            "resource_budget": self.resource_budget.to_dict() if self.resource_budget else None,
            "created_at": self.created_at.isoformat(),
            "validated_at": self.validated_at.isoformat() if self.validated_at else None,
            "execution_started_at": self.execution_started_at.isoformat() if self.execution_started_at else None,
            "execution_completed_at": self.execution_completed_at.isoformat() if self.execution_completed_at else None,
            "signature": self.signature,
            "metadata": {
                "decomposition_strategy": self.metadata.decomposition_strategy,
                "decomposition_latency_ms": self.metadata.decomposition_latency_ms,
                "cache_hit": self.metadata.cache_hit,
                "llm_provider": self.metadata.llm_provider,
                "llm_model": self.metadata.llm_model,
                "total_tokens_used": self.metadata.total_tokens_used,
                "validation_time_ms": self.metadata.validation_time_ms,
                "execution_time_ms": self.metadata.execution_time_ms,
                "parallelism_achieved": self.metadata.parallelism_achieved,
                "tags": self.metadata.tags,
            },
            "error": self.error,
            "completed_task_count": self.completed_task_count,
            "failed_task_count": self.failed_task_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionPlan":
        """Create ExecutionPlan from dictionary representation."""
        from .task import Task

        tasks = [Task.from_dict(task_data) for task_data in data.get("tasks", [])]

        metadata_data = data.get("metadata", {})
        metadata = PlanMetadata(
            decomposition_strategy=metadata_data.get("decomposition_strategy", "hybrid"),
            decomposition_latency_ms=metadata_data.get("decomposition_latency_ms"),
            cache_hit=metadata_data.get("cache_hit", False),
            llm_provider=metadata_data.get("llm_provider"),
            llm_model=metadata_data.get("llm_model"),
            total_tokens_used=metadata_data.get("total_tokens_used", 0),
            validation_time_ms=metadata_data.get("validation_time_ms"),
            execution_time_ms=metadata_data.get("execution_time_ms"),
            parallelism_achieved=metadata_data.get("parallelism_achieved", 1),
            tags=metadata_data.get("tags", []),
        )

        resource_budget = None
        if data.get("resource_budget"):
            from .resource import ResourceConstraints
            resource_budget = ResourceConstraints.from_dict(data["resource_budget"])

        return cls(
            plan_id=data["plan_id"],
            goal_id=data["goal_id"],
            tasks=tasks,
            dependency_graph=data.get("dependency_graph", {}),
            status=PlanStatus(data.get("status", "draft")),
            resource_budget=resource_budget,
            created_at=datetime.fromisoformat(data["created_at"]),
            validated_at=datetime.fromisoformat(data["validated_at"]) if data.get("validated_at") else None,
            execution_started_at=datetime.fromisoformat(data["execution_started_at"]) if data.get("execution_started_at") else None,
            execution_completed_at=datetime.fromisoformat(data["execution_completed_at"]) if data.get("execution_completed_at") else None,
            signature=data.get("signature"),
            metadata=metadata,
            error=data.get("error"),
            completed_task_count=data.get("completed_task_count", 0),
            failed_task_count=data.get("failed_task_count", 0),
        )

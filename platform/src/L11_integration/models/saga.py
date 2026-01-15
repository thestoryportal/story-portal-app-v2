"""
L11 Integration Layer - Saga Orchestration Models.

Models for multi-step workflow orchestration with compensation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, Callable, Awaitable
from uuid import uuid4


class SagaStatus(str, Enum):
    """Status of a saga execution."""

    PENDING = "pending"  # Saga created, not started
    RUNNING = "running"  # Saga is executing
    COMPENSATING = "compensating"  # Saga is rolling back
    COMPLETED = "completed"  # Saga completed successfully
    FAILED = "failed"  # Saga failed and compensation complete
    TIMEOUT = "timeout"  # Saga exceeded timeout


class StepStatus(str, Enum):
    """Status of a saga step."""

    PENDING = "pending"  # Step not started
    RUNNING = "running"  # Step is executing
    COMPLETED = "completed"  # Step completed successfully
    FAILED = "failed"  # Step failed
    COMPENSATED = "compensated"  # Step was compensated (rolled back)
    SKIPPED = "skipped"  # Step was skipped


# Type aliases for step functions
StepAction = Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]
CompensationAction = Callable[[Dict[str, Any]], Awaitable[None]]


@dataclass
class SagaStep:
    """
    Single step in a saga workflow.

    Each step has an action and optional compensation action for rollback.
    """

    step_id: str  # Unique identifier for this step
    step_name: str  # Human-readable step name
    action: Optional[StepAction] = None  # Forward action (async function)
    compensation: Optional[CompensationAction] = None  # Rollback action (async function)
    service_name: Optional[str] = None  # Target service for this step
    endpoint: Optional[str] = None  # API endpoint to call
    timeout_sec: int = 30  # Step timeout in seconds
    retry_on_failure: bool = True  # Whether to retry on failure
    max_retries: int = 3  # Maximum retry attempts
    required: bool = True  # Whether step failure fails entire saga
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional step config

    # Runtime state
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    error: Optional[str] = None
    output: Optional[Dict[str, Any]] = None  # Step output data

    def start(self) -> None:
        """Mark step as started."""
        self.status = StepStatus.RUNNING
        self.started_at = datetime.utcnow()

    def complete(self, output: Optional[Dict[str, Any]] = None) -> None:
        """Mark step as completed."""
        self.status = StepStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.output = output or {}

    def fail(self, error: str) -> None:
        """Mark step as failed."""
        self.status = StepStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error = error

    def compensate(self) -> None:
        """Mark step as compensated."""
        self.status = StepStatus.COMPENSATED

    def can_retry(self) -> bool:
        """Check if step can be retried."""
        return self.retry_on_failure and self.retry_count < self.max_retries


@dataclass
class SagaDefinition:
    """
    Definition of a saga workflow.

    Sagas coordinate multi-step operations across layers with automatic
    rollback on failure.
    """

    saga_id: str  # Unique identifier
    saga_name: str  # Human-readable name
    steps: list[SagaStep] = field(default_factory=list)  # Ordered list of steps
    timeout_sec: int = 300  # Overall saga timeout (5 minutes default)
    auto_compensate: bool = True  # Automatically compensate on failure
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional saga config

    @classmethod
    def create(
        cls,
        saga_name: str,
        steps: Optional[list[SagaStep]] = None,
        timeout_sec: int = 300,
        auto_compensate: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "SagaDefinition":
        """Factory method to create a new saga definition."""
        return cls(
            saga_id=str(uuid4()),
            saga_name=saga_name,
            steps=steps or [],
            timeout_sec=timeout_sec,
            auto_compensate=auto_compensate,
            metadata=metadata or {},
        )

    def add_step(self, step: SagaStep) -> None:
        """Add a step to the saga."""
        self.steps.append(step)


@dataclass
class SagaExecution:
    """
    Runtime state of a saga execution.

    Tracks the progress and state of an executing saga.
    """

    execution_id: str  # Unique execution ID
    saga_definition: SagaDefinition  # The saga being executed
    status: SagaStatus = SagaStatus.PENDING
    current_step_index: int = 0  # Index of currently executing step
    context: Dict[str, Any] = field(default_factory=dict)  # Saga execution context
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None  # Error message if failed
    trace_id: Optional[str] = None  # Distributed tracing ID
    correlation_id: Optional[str] = None  # Request correlation ID

    @classmethod
    def create(
        cls,
        saga_definition: SagaDefinition,
        context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> "SagaExecution":
        """Factory method to create a new saga execution."""
        return cls(
            execution_id=str(uuid4()),
            saga_definition=saga_definition,
            status=SagaStatus.PENDING,
            context=context or {},
            trace_id=trace_id,
            correlation_id=correlation_id,
        )

    def start(self) -> None:
        """Start saga execution."""
        self.status = SagaStatus.RUNNING
        self.started_at = datetime.utcnow()

    def complete(self) -> None:
        """Complete saga execution."""
        self.status = SagaStatus.COMPLETED
        self.completed_at = datetime.utcnow()

    def fail(self, error: str) -> None:
        """Fail saga execution."""
        self.status = SagaStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error = error

    def start_compensation(self) -> None:
        """Start compensation (rollback) process."""
        self.status = SagaStatus.COMPENSATING

    def get_current_step(self) -> Optional[SagaStep]:
        """Get the currently executing step."""
        if 0 <= self.current_step_index < len(self.saga_definition.steps):
            return self.saga_definition.steps[self.current_step_index]
        return None

    def get_completed_steps(self) -> list[SagaStep]:
        """Get all completed steps (for compensation)."""
        return [
            step for step in self.saga_definition.steps
            if step.status == StepStatus.COMPLETED
        ]

    def is_timeout(self) -> bool:
        """Check if saga has exceeded timeout."""
        if self.started_at:
            elapsed = (datetime.utcnow() - self.started_at).total_seconds()
            return elapsed > self.saga_definition.timeout_sec
        return False

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "execution_id": self.execution_id,
            "saga_id": self.saga_definition.saga_id,
            "saga_name": self.saga_definition.saga_name,
            "status": self.status.value,
            "current_step_index": self.current_step_index,
            "total_steps": len(self.saga_definition.steps),
            "context": self.context,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "trace_id": self.trace_id,
            "correlation_id": self.correlation_id,
            "steps": [
                {
                    "step_id": step.step_id,
                    "step_name": step.step_name,
                    "status": step.status.value,
                    "error": step.error,
                }
                for step in self.saga_definition.steps
            ],
        }

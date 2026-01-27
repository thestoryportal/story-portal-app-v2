"""
L05 Planning Layer - Agent Models.

Represents agent capabilities and task assignments.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List


class CapabilityType(str, Enum):
    """Type of agent capability."""

    TOOL_EXECUTION = "tool_execution"  # Can execute tools
    LLM_INFERENCE = "llm_inference"  # Can perform LLM inference
    CODE_EXECUTION = "code_execution"  # Can execute code
    FILE_OPERATIONS = "file_operations"  # Can perform file operations
    NETWORK_ACCESS = "network_access"  # Has network access
    DATA_PROCESSING = "data_processing"  # Can process data
    REASONING = "reasoning"  # Has reasoning capabilities


@dataclass
class AgentCapability:
    """
    Represents a capability that an agent possesses.

    Used for task-agent matching and assignment.
    """

    capability_type: CapabilityType  # Type of capability
    version: str = "1.0"  # Capability version
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata

    def matches(self, required_capability: "AgentCapability") -> bool:
        """Check if this capability matches a required capability."""
        return self.capability_type == required_capability.capability_type

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "capability_type": self.capability_type.value,
            "version": self.version,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentCapability":
        """Create from dictionary representation."""
        return cls(
            capability_type=CapabilityType(data["capability_type"]),
            version=data.get("version", "1.0"),
            metadata=data.get("metadata", {}),
        )


class AssignmentStatus(str, Enum):
    """Status of agent assignment."""

    PENDING = "pending"  # Assignment pending
    ASSIGNED = "assigned"  # Agent assigned
    EXECUTING = "executing"  # Agent executing task
    COMPLETED = "completed"  # Task completed
    FAILED = "failed"  # Task failed


@dataclass
class AgentAssignment:
    """
    Represents assignment of a task to an agent.

    Tracks which agent is executing which task and the assignment status.
    """

    assignment_id: str  # Unique assignment ID
    task_id: str  # Task being executed
    agent_did: str  # Agent DID
    plan_id: str  # Parent plan
    status: AssignmentStatus = AssignmentStatus.PENDING  # Assignment status
    assigned_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))  # Assignment time
    started_at: Optional[datetime] = None  # Execution start time
    completed_at: Optional[datetime] = None  # Execution completion time
    affinity_score: float = 0.0  # Affinity score (0.0-1.0)
    load_score: float = 0.0  # Agent load at assignment (0.0-1.0)
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata

    def mark_executing(self) -> None:
        """Mark assignment as executing."""
        if self.status == AssignmentStatus.ASSIGNED:
            self.status = AssignmentStatus.EXECUTING
            self.started_at = datetime.now(timezone.utc)

    def mark_completed(self) -> None:
        """Mark assignment as completed."""
        if self.status == AssignmentStatus.EXECUTING:
            self.status = AssignmentStatus.COMPLETED
            self.completed_at = datetime.now(timezone.utc)

    def mark_failed(self) -> None:
        """Mark assignment as failed."""
        if self.status in (AssignmentStatus.EXECUTING, AssignmentStatus.ASSIGNED):
            self.status = AssignmentStatus.FAILED
            self.completed_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "assignment_id": self.assignment_id,
            "task_id": self.task_id,
            "agent_did": self.agent_did,
            "plan_id": self.plan_id,
            "status": self.status.value,
            "assigned_at": self.assigned_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "affinity_score": self.affinity_score,
            "load_score": self.load_score,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentAssignment":
        """Create from dictionary representation."""
        return cls(
            assignment_id=data["assignment_id"],
            task_id=data["task_id"],
            agent_did=data["agent_did"],
            plan_id=data["plan_id"],
            status=AssignmentStatus(data.get("status", "pending")),
            assigned_at=datetime.fromisoformat(data["assigned_at"]),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            affinity_score=data.get("affinity_score", 0.0),
            load_score=data.get("load_score", 0.0),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Agent:
    """
    Represents an agent available for task execution.

    Used by agent assigner for capability matching and load balancing.
    """

    agent_did: str  # Agent DID
    capabilities: List[AgentCapability] = field(default_factory=list)  # Agent capabilities
    current_load: int = 0  # Current number of assigned tasks
    max_concurrent_tasks: int = 5  # Maximum concurrent tasks
    is_available: bool = True  # Availability status
    last_health_check: Optional[datetime] = None  # Last health check time
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata

    def has_capability(self, required_capability: AgentCapability) -> bool:
        """Check if agent has required capability."""
        for cap in self.capabilities:
            if cap.matches(required_capability):
                return True
        return False

    def can_accept_task(self) -> bool:
        """Check if agent can accept more tasks."""
        return self.is_available and self.current_load < self.max_concurrent_tasks

    def get_load_ratio(self) -> float:
        """Get current load ratio (0.0-1.0)."""
        if self.max_concurrent_tasks == 0:
            return 1.0
        return self.current_load / self.max_concurrent_tasks

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "agent_did": self.agent_did,
            "capabilities": [cap.to_dict() for cap in self.capabilities],
            "current_load": self.current_load,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "is_available": self.is_available,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Agent":
        """Create from dictionary representation."""
        capabilities = [
            AgentCapability.from_dict(cap_data)
            for cap_data in data.get("capabilities", [])
        ]

        return cls(
            agent_did=data["agent_did"],
            capabilities=capabilities,
            current_load=data.get("current_load", 0),
            max_concurrent_tasks=data.get("max_concurrent_tasks", 5),
            is_available=data.get("is_available", True),
            last_health_check=datetime.fromisoformat(data["last_health_check"]) if data.get("last_health_check") else None,
            metadata=data.get("metadata", {}),
        )

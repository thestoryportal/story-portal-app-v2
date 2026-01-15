"""
L10 Human Interface Layer - Control Models

Models for agent control operations (pause, resume, emergency stop).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class ControlOperation(str, Enum):
    """Control operation types."""
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"
    EMERGENCY_STOP = "emergency_stop"
    UPDATE_QUOTA = "update_quota"
    REDIRECT_WORKFLOW = "redirect_workflow"


class ControlStatus(str, Enum):
    """Control operation status."""
    SUCCESS = "success"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"
    IDEMPOTENT = "idempotent"  # Operation was idempotent (no-op)


@dataclass
class PauseRequest:
    """Request to pause agent."""
    agent_id: str
    reason: Optional[str] = None
    user_id: Optional[str] = None
    idempotency_key: Optional[str] = None


@dataclass
class ResumeRequest:
    """Request to resume agent."""
    agent_id: str
    user_id: Optional[str] = None
    idempotency_key: Optional[str] = None


@dataclass
class EmergencyStopRequest:
    """Request to emergency stop agent."""
    agent_id: str
    reason: str
    user_id: str
    idempotency_key: Optional[str] = None


@dataclass
class UpdateQuotaRequest:
    """Request to update resource quota."""
    agent_id: str
    tokens_per_hour: Optional[int] = None
    cpu_millicores: Optional[int] = None
    memory_mb: Optional[int] = None
    user_id: Optional[str] = None


@dataclass
class ControlResponse:
    """Response from control operation."""
    operation: ControlOperation
    status: ControlStatus
    agent_id: str
    message: str
    previous_state: Optional[str] = None
    new_state: Optional[str] = None
    idempotent: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "operation": self.operation.value if isinstance(self.operation, ControlOperation) else self.operation,
            "status": self.status.value if isinstance(self.status, ControlStatus) else self.status,
            "agent_id": self.agent_id,
            "message": self.message,
            "previous_state": self.previous_state,
            "new_state": self.new_state,
            "idempotent": self.idempotent,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class ControlAuditEntry:
    """Audit entry for control operation."""
    operation: ControlOperation
    agent_id: str
    user_id: str
    user_ip: Optional[str] = None
    reason: Optional[str] = None
    status: ControlStatus = ControlStatus.SUCCESS
    error_message: Optional[str] = None
    change_delta: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    idempotency_key: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "operation": self.operation.value if isinstance(self.operation, ControlOperation) else self.operation,
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "user_ip": self.user_ip,
            "reason": self.reason,
            "status": self.status.value if isinstance(self.status, ControlStatus) else self.status,
            "error_message": self.error_message,
            "change_delta": self.change_delta,
            "timestamp": self.timestamp.isoformat(),
            "idempotency_key": self.idempotency_key,
        }

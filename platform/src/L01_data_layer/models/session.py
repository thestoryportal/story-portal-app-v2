"""Session models."""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum


class SessionStatus(str, Enum):
    """Session status enum."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CRASHED = "crashed"


class RuntimeBackend(str, Enum):
    """Runtime backend type."""
    LOCAL = "local"
    KUBERNETES = "kubernetes"
    UNKNOWN = "unknown"


class SessionCreate(BaseModel):
    """Session creation request."""
    agent_id: UUID = Field(..., description="Agent ID")
    session_type: str = Field(default="conversation", description="Session type")
    context: Dict[str, Any] = Field(default_factory=dict, description="Session context")
    runtime_backend: Optional[RuntimeBackend] = Field(None, description="Runtime backend")
    runtime_metadata: Dict[str, Any] = Field(default_factory=dict, description="Runtime-specific metadata")


class SessionUpdate(BaseModel):
    """Session update request."""
    status: Optional[SessionStatus] = None
    context: Optional[Dict[str, Any]] = None
    checkpoint: Optional[Dict[str, Any]] = None
    runtime_metadata: Optional[Dict[str, Any]] = None


class Session(BaseModel):
    """Session model."""
    id: UUID = Field(default_factory=uuid4)
    agent_id: UUID
    session_type: str = "conversation"
    status: SessionStatus = SessionStatus.ACTIVE
    context: Dict[str, Any] = Field(default_factory=dict)
    checkpoint: Optional[Dict[str, Any]] = None
    runtime_backend: Optional[RuntimeBackend] = None
    runtime_metadata: Dict[str, Any] = Field(default_factory=dict, description="Runtime-specific data (container_id, pod_name, l02_session_id, etc.)")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True

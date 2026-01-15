"""Agent models."""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum


class AgentStatus(str, Enum):
    """Agent status enum."""
    CREATED = "created"
    ACTIVE = "active"
    IDLE = "idle"
    BUSY = "busy"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    ERROR = "error"


class AgentCreate(BaseModel):
    """Agent creation request."""
    name: str = Field(..., description="Agent name")
    agent_type: str = Field(default="general", description="Agent type")
    configuration: Dict[str, Any] = Field(default_factory=dict, description="Agent configuration")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Agent metadata")
    resource_limits: Dict[str, Any] = Field(default_factory=dict, description="Resource limits")


class AgentUpdate(BaseModel):
    """Agent update request."""
    name: Optional[str] = None
    agent_type: Optional[str] = None
    status: Optional[AgentStatus] = None
    configuration: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    resource_limits: Optional[Dict[str, Any]] = None


class Agent(BaseModel):
    """Agent model."""
    id: UUID = Field(default_factory=uuid4, description="Agent ID")
    did: str = Field(..., description="Decentralized identifier")
    name: str
    agent_type: str = "general"
    status: AgentStatus = AgentStatus.CREATED
    configuration: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    resource_limits: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True

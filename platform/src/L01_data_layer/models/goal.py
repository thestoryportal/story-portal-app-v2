"""Goal models."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum


class GoalStatus(str, Enum):
    """Goal status enum."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GoalCreate(BaseModel):
    """Goal creation request."""
    agent_id: UUID = Field(..., description="Agent ID")
    description: str = Field(..., description="Goal description")
    success_criteria: List[Dict[str, Any]] = Field(default_factory=list, description="Success criteria")
    priority: int = Field(default=5, ge=1, le=10, description="Priority (1-10)")
    parent_goal_id: Optional[UUID] = Field(None, description="Parent goal ID for hierarchical goals")


class GoalUpdate(BaseModel):
    """Goal update request."""
    description: Optional[str] = None
    success_criteria: Optional[List[Dict[str, Any]]] = None
    status: Optional[GoalStatus] = None
    priority: Optional[int] = Field(None, ge=1, le=10)
    completed_at: Optional[datetime] = None


class Goal(BaseModel):
    """Goal model."""
    id: UUID = Field(default_factory=uuid4)
    agent_id: UUID
    description: str
    success_criteria: List[Dict[str, Any]] = Field(default_factory=list)
    status: GoalStatus = GoalStatus.PENDING
    priority: int = 5
    parent_goal_id: Optional[UUID] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

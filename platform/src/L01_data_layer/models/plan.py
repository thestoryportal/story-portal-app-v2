"""Plan and Task models."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum


class PlanStatus(str, Enum):
    """Plan status enum."""
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(str, Enum):
    """Task status enum."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class PlanCreate(BaseModel):
    """Plan creation request."""
    goal_id: UUID = Field(..., description="Goal ID")
    agent_id: UUID = Field(..., description="Agent ID")
    plan_type: str = Field(default="sequential", description="Plan type")
    steps: List[Dict[str, Any]] = Field(..., description="Plan steps")


class PlanUpdate(BaseModel):
    """Plan update request."""
    status: Optional[PlanStatus] = None
    current_step: Optional[int] = None
    steps: Optional[List[Dict[str, Any]]] = None


class Plan(BaseModel):
    """Plan model."""
    id: UUID = Field(default_factory=uuid4)
    goal_id: UUID
    agent_id: UUID
    plan_type: str = "sequential"
    steps: List[Dict[str, Any]]
    status: PlanStatus = PlanStatus.DRAFT
    current_step: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class TaskCreate(BaseModel):
    """Task creation request."""
    plan_id: UUID = Field(..., description="Plan ID")
    agent_id: UUID = Field(..., description="Agent ID")
    description: str = Field(..., description="Task description")
    task_type: Optional[str] = Field(None, description="Task type")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Task input data")
    sequence_order: int = Field(default=0, description="Task sequence order")


class TaskUpdate(BaseModel):
    """Task update request."""
    status: Optional[TaskStatus] = None
    output_data: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class Task(BaseModel):
    """Task model."""
    id: UUID = Field(default_factory=uuid4)
    plan_id: UUID
    agent_id: UUID
    description: str
    task_type: Optional[str] = None
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = None
    status: TaskStatus = TaskStatus.PENDING
    sequence_order: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

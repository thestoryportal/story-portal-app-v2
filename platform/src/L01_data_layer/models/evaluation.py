"""Evaluation models."""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID, uuid4
from decimal import Decimal


class EvaluationCreate(BaseModel):
    """Evaluation creation request."""
    agent_id: UUID = Field(..., description="Agent ID")
    task_id: Optional[UUID] = Field(None, description="Task ID")
    evaluation_type: str = Field(..., description="Evaluation type (e.g., 'quality', 'performance')")
    score: Optional[Decimal] = Field(None, ge=0.0, le=1.0, description="Score between 0 and 1")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Detailed metrics")
    feedback: Optional[str] = Field(None, description="Evaluation feedback")


class Evaluation(BaseModel):
    """Evaluation model."""
    id: UUID = Field(default_factory=uuid4)
    agent_id: UUID
    task_id: Optional[UUID] = None
    evaluation_type: str
    score: Optional[Decimal] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    feedback: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True

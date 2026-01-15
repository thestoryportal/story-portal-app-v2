"""Feedback models."""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID, uuid4


class FeedbackCreate(BaseModel):
    """Feedback creation request."""
    agent_id: UUID = Field(..., description="Agent ID")
    task_id: Optional[UUID] = Field(None, description="Task ID")
    feedback_type: str = Field(..., description="Feedback type (e.g., 'human', 'automated')")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating 1-5")
    content: str = Field(..., description="Feedback content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Feedback metadata")


class FeedbackUpdate(BaseModel):
    """Feedback update request."""
    processed: bool = Field(..., description="Mark feedback as processed")


class FeedbackEntry(BaseModel):
    """Feedback entry model."""
    id: UUID = Field(default_factory=uuid4)
    agent_id: UUID
    task_id: Optional[UUID] = None
    feedback_type: str
    rating: Optional[int] = None
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    processed: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True

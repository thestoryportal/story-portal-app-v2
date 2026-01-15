"""Event models for event sourcing."""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID, uuid4


class EventCreate(BaseModel):
    """Event creation request."""
    event_type: str = Field(..., description="Event type (e.g., 'agent.spawned')")
    aggregate_type: str = Field(..., description="Aggregate type (e.g., 'agent')")
    aggregate_id: UUID = Field(..., description="Aggregate ID")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event payload")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Event metadata")
    version: int = Field(default=1, description="Event version")


class Event(BaseModel):
    """Event model."""
    id: UUID = Field(default_factory=uuid4, description="Event ID")
    event_type: str
    aggregate_type: str
    aggregate_id: UUID
    payload: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = Field(default=1)

    class Config:
        from_attributes = True

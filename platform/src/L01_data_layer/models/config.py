"""Configuration models."""

from pydantic import BaseModel, Field
from typing import Dict, Any
from datetime import datetime
from uuid import UUID, uuid4


class ConfigCreate(BaseModel):
    """Configuration create request."""
    namespace: str = Field(..., description="Config namespace")
    key: str = Field(..., description="Config key")
    value: Dict[str, Any] = Field(..., description="Config value as JSON")


class ConfigUpdate(BaseModel):
    """Configuration update request."""
    value: Dict[str, Any] = Field(..., description="Config value as JSON")


class Configuration(BaseModel):
    """Configuration model."""
    id: UUID = Field(default_factory=uuid4)
    namespace: str
    key: str
    value: Dict[str, Any]
    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True

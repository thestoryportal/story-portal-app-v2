"""Model usage tracking models."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4
from decimal import Decimal


class ModelUsageCreate(BaseModel):
    """Model usage logging request."""
    agent_id: UUID = Field(..., description="Agent ID")
    model_provider: str = Field(..., description="Model provider (e.g., 'anthropic', 'openai')")
    model_name: str = Field(..., description="Model name (e.g., 'claude-3-sonnet', 'gpt-4')")
    input_tokens: int = Field(default=0, ge=0, description="Input tokens")
    output_tokens: int = Field(default=0, ge=0, description="Output tokens")
    latency_ms: Optional[int] = Field(None, ge=0, description="Latency in milliseconds")
    cost_estimate: Optional[Decimal] = Field(None, ge=0, description="Cost estimate in USD")


class ModelUsage(BaseModel):
    """Model usage model."""
    id: UUID = Field(default_factory=uuid4)
    agent_id: UUID
    model_provider: str
    model_name: str
    input_tokens: int
    output_tokens: int
    latency_ms: Optional[int] = None
    cost_estimate: Optional[Decimal] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True

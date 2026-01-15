"""Document models."""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID, uuid4


class DocumentCreate(BaseModel):
    """Document creation request."""
    title: str = Field(..., description="Document title", max_length=500)
    content: Optional[str] = Field(None, description="Document content")
    content_type: str = Field(default="text/plain", description="Content MIME type")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    tags: List[str] = Field(default_factory=list, description="Document tags")


class DocumentUpdate(BaseModel):
    """Document update request."""
    title: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = None
    content_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class Document(BaseModel):
    """Document model."""
    id: UUID = Field(default_factory=uuid4)
    title: str
    content: Optional[str] = None
    content_type: str = "text/plain"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True

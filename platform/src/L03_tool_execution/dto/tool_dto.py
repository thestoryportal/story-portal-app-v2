"""
Tool DTOs

Pydantic models for tool registry operations:
- Tool listing and retrieval
- Tool registration
- Semantic search
- Deprecation workflow
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator

from ..models import ToolCategory, SourceType, DeprecationState


class ToolDTO(BaseModel):
    """Tool definition response DTO."""

    tool_id: str = Field(..., description="Unique tool identifier")
    tool_name: str = Field(..., description="Human-readable tool name")
    description: str = Field(..., description="Tool description for semantic search")
    category: str = Field(..., description="Tool category (utility, data, integration, etc.)")
    tags: List[str] = Field(default_factory=list, description="Searchable tags")
    latest_version: str = Field(..., description="Latest available version")
    source_type: str = Field(..., description="Tool source (native, mcp, openapi, langchain)")
    source_metadata: Dict[str, Any] = Field(default_factory=dict, description="Source-specific metadata")
    deprecation_state: str = Field(default="active", description="Deprecation state")
    deprecation_date: Optional[datetime] = Field(None, description="Scheduled deprecation date")
    created_at: Optional[datetime] = Field(None, description="Tool registration timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    requires_approval: bool = Field(False, description="Requires human approval before execution")
    default_timeout_seconds: int = Field(30, description="Default execution timeout")
    default_cpu_millicore_limit: int = Field(500, description="Default CPU limit")
    default_memory_mb_limit: int = Field(1024, description="Default memory limit")

    model_config = {"extra": "ignore", "from_attributes": True}

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(cls, v: Any) -> str:
        if isinstance(v, ToolCategory):
            return v.value
        return str(v)

    @field_validator("source_type", mode="before")
    @classmethod
    def validate_source_type(cls, v: Any) -> str:
        if isinstance(v, SourceType):
            return v.value
        return str(v)

    @field_validator("deprecation_state", mode="before")
    @classmethod
    def validate_deprecation_state(cls, v: Any) -> str:
        if isinstance(v, DeprecationState):
            return v.value
        return str(v)


class ToolListResponseDTO(BaseModel):
    """Response for tool listing endpoint."""

    tools: List[ToolDTO] = Field(..., description="List of tools")
    total: int = Field(..., description="Total count")
    page: int = Field(1, description="Current page")
    page_size: int = Field(50, description="Items per page")

    model_config = {"extra": "ignore"}


class ToolSearchRequestDTO(BaseModel):
    """Request for semantic tool search."""

    query: str = Field(..., min_length=1, max_length=500, description="Natural language search query")
    limit: int = Field(10, ge=1, le=100, description="Maximum results to return")
    category: Optional[str] = Field(None, description="Filter by category")
    include_deprecated: bool = Field(False, description="Include deprecated tools")

    model_config = {"extra": "ignore"}


class ToolSearchResultDTO(BaseModel):
    """Individual search result with similarity score."""

    tool: ToolDTO = Field(..., description="Matched tool")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Cosine similarity score")

    model_config = {"extra": "ignore"}


class ToolRegisterRequestDTO(BaseModel):
    """Request for tool registration."""

    tool_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        pattern=r"^[a-z0-9][a-z0-9\-_]*[a-z0-9]$",
        description="Unique tool identifier (lowercase, alphanumeric with hyphens/underscores)",
    )
    tool_name: str = Field(..., min_length=1, max_length=255, description="Human-readable name")
    description: str = Field(..., min_length=10, max_length=5000, description="Tool description")
    category: str = Field(..., description="Tool category")
    tags: List[str] = Field(default_factory=list, max_length=20, description="Searchable tags")
    version: str = Field(
        ...,
        pattern=r"^\d+\.\d+\.\d+$",
        description="Semantic version (e.g., 1.0.0)",
    )
    source_type: str = Field(..., description="Tool source type")
    source_metadata: Dict[str, Any] = Field(default_factory=dict, description="Source configuration")
    requires_approval: bool = Field(False, description="Require human approval")
    default_timeout_seconds: int = Field(30, ge=1, le=3600, description="Default timeout")
    default_cpu_millicore_limit: int = Field(500, ge=100, le=4000, description="CPU limit")
    default_memory_mb_limit: int = Field(1024, ge=128, le=8192, description="Memory limit")
    required_permissions: Dict[str, Any] = Field(default_factory=dict, description="Required permissions")
    result_schema: Optional[Dict[str, Any]] = Field(None, description="JSON Schema for result validation")
    input_schema: Optional[Dict[str, Any]] = Field(None, description="JSON Schema for input validation")

    model_config = {"extra": "ignore"}

    @field_validator("category")
    @classmethod
    def validate_category_value(cls, v: str) -> str:
        valid_categories = [c.value for c in ToolCategory]
        if v not in valid_categories:
            raise ValueError(f"Invalid category: {v}. Must be one of: {valid_categories}")
        return v

    @field_validator("source_type")
    @classmethod
    def validate_source_type_value(cls, v: str) -> str:
        valid_sources = [s.value for s in SourceType]
        if v not in valid_sources:
            raise ValueError(f"Invalid source_type: {v}. Must be one of: {valid_sources}")
        return v


class ToolDeprecateRequestDTO(BaseModel):
    """Request for tool deprecation."""

    reason: str = Field(..., min_length=10, max_length=1000, description="Deprecation reason")
    replacement_tool_id: Optional[str] = Field(None, description="Recommended replacement tool")
    deprecation_date: Optional[datetime] = Field(None, description="Effective deprecation date")
    sunset_date: Optional[datetime] = Field(None, description="Final removal date")

    model_config = {"extra": "ignore"}

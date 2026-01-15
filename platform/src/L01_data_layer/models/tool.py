"""Tool models."""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum


class ToolType(str, Enum):
    """Tool type enum."""
    FUNCTION = "function"
    API = "api"
    EXTERNAL = "external"


class ToolExecutionStatus(str, Enum):
    """Tool execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    PERMISSION_DENIED = "permission_denied"
    PENDING_APPROVAL = "pending_approval"


class ToolCreate(BaseModel):
    """Tool registration request."""
    name: str = Field(..., description="Tool name")
    description: Optional[str] = Field(None, description="Tool description")
    tool_type: ToolType = Field(default=ToolType.FUNCTION, description="Tool type")
    schema_def: Dict[str, Any] = Field(..., description="Tool schema definition")
    permissions: Dict[str, Any] = Field(default_factory=dict, description="Tool permissions")
    enabled: bool = Field(default=True, description="Tool enabled flag")


class ToolUpdate(BaseModel):
    """Tool update request."""
    description: Optional[str] = None
    schema_def: Optional[Dict[str, Any]] = None
    permissions: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None


class Tool(BaseModel):
    """Tool model."""
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: Optional[str] = None
    tool_type: ToolType = ToolType.FUNCTION
    schema_def: Dict[str, Any]
    permissions: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class ToolExecutionCreate(BaseModel):
    """Tool execution logging request with rich metadata."""

    invocation_id: UUID
    tool_id: Optional[UUID] = None
    tool_name: str = Field(..., min_length=1)
    tool_version: Optional[str] = None

    # Agent context
    agent_id: Optional[UUID] = None
    agent_did: Optional[str] = None
    tenant_id: Optional[str] = None
    session_id: Optional[str] = None
    parent_sandbox_id: Optional[str] = None

    # Execution details
    input_params: Dict[str, Any] = Field(default_factory=dict)
    status: ToolExecutionStatus = ToolExecutionStatus.PENDING

    # Execution options
    async_mode: bool = False
    priority: int = Field(default=5, ge=1, le=10)
    idempotency_key: Optional[str] = None
    require_approval: bool = False

    # Resource limits
    cpu_millicore_limit: Optional[int] = None
    memory_mb_limit: Optional[int] = None
    timeout_seconds: Optional[int] = None


class ToolExecutionUpdate(BaseModel):
    """Tool execution update request."""

    status: Optional[ToolExecutionStatus] = None
    output_result: Optional[Dict[str, Any]] = None

    # Error information
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    retryable: Optional[bool] = None

    # Execution metadata
    duration_ms: Optional[int] = None
    cpu_used_millicore_seconds: Optional[int] = None
    memory_peak_mb: Optional[int] = None
    network_bytes_sent: Optional[int] = None
    network_bytes_received: Optional[int] = None

    # Phase 15/16 integration
    documents_accessed: Optional[list] = None
    checkpoints_created: Optional[list] = None
    checkpoint_ref: Optional[str] = None

    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ToolExecution(BaseModel):
    """Tool execution model with full execution history."""

    id: UUID = Field(default_factory=uuid4)
    invocation_id: UUID
    tool_id: Optional[UUID] = None
    tool_name: str
    tool_version: Optional[str] = None

    # Agent context
    agent_id: Optional[UUID] = None
    agent_did: Optional[str] = None
    tenant_id: Optional[str] = None
    session_id: Optional[str] = None
    parent_sandbox_id: Optional[str] = None

    # Execution details
    input_params: Dict[str, Any] = Field(default_factory=dict)
    output_result: Optional[Dict[str, Any]] = None
    status: ToolExecutionStatus = ToolExecutionStatus.PENDING

    # Error information
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    retryable: bool = False

    # Execution metadata
    duration_ms: Optional[int] = None
    cpu_used_millicore_seconds: Optional[int] = None
    memory_peak_mb: Optional[int] = None
    network_bytes_sent: Optional[int] = None
    network_bytes_received: Optional[int] = None

    # Phase 15/16 integration
    documents_accessed: list = Field(default_factory=list)
    checkpoints_created: list = Field(default_factory=list)
    checkpoint_ref: Optional[str] = None

    # Execution options
    async_mode: bool = False
    priority: int = 5
    idempotency_key: Optional[str] = None
    require_approval: bool = False

    # Resource limits
    cpu_millicore_limit: Optional[int] = None
    memory_mb_limit: Optional[int] = None
    timeout_seconds: Optional[int] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }

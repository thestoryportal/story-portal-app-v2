"""
Execution DTOs

Pydantic models for tool execution operations:
- Tool invocation requests/responses
- Async task management
- Error responses
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from ..models import ToolStatus


class AgentContextDTO(BaseModel):
    """Agent context for tool invocation (BC-1 nested sandbox)."""

    agent_did: str = Field(..., description="Agent decentralized identifier")
    tenant_id: str = Field(..., description="Tenant identifier for multi-tenancy")
    session_id: str = Field(..., description="Agent session identifier")
    capability_token: Optional[str] = Field(None, description="JWT capability token")
    parent_sandbox_id: Optional[str] = Field(None, description="L02 parent sandbox reference")

    model_config = {"extra": "ignore"}


class ResourceLimitsDTO(BaseModel):
    """Resource limits for tool execution (sub-allocated from agent)."""

    cpu_millicore_limit: Optional[int] = Field(None, ge=100, le=4000, description="CPU limit in millicores")
    memory_mb_limit: Optional[int] = Field(None, ge=128, le=8192, description="Memory limit in MB")
    timeout_seconds: Optional[int] = Field(None, ge=1, le=3600, description="Execution timeout")

    model_config = {"extra": "ignore"}


class DocumentContextDTO(BaseModel):
    """Document context for tool execution (Phase 15 integration)."""

    document_refs: List[str] = Field(default_factory=list, description="Document IDs to access")
    version_pinning: bool = Field(True, description="Pin document versions during execution")
    query: Optional[str] = Field(None, max_length=500, description="Semantic search query for documents")

    model_config = {"extra": "ignore"}


class CheckpointConfigDTO(BaseModel):
    """Checkpoint configuration for resumable operations (Phase 16 integration)."""

    enable_checkpointing: bool = Field(False, description="Enable checkpoint creation")
    interval_seconds: int = Field(30, ge=5, le=300, description="Micro-checkpoint interval")
    resume_from: Optional[str] = Field(None, description="Checkpoint ID to resume from")

    model_config = {"extra": "ignore"}


class ExecutionOptionsDTO(BaseModel):
    """Tool execution options."""

    async_mode: bool = Field(False, description="Enable async execution for long-running tools")
    priority: int = Field(5, ge=1, le=10, description="Execution priority (1-10, higher = more important)")
    idempotency_key: Optional[str] = Field(None, max_length=255, description="Key for duplicate detection")
    require_approval: Optional[bool] = Field(None, description="Override tool approval requirement")

    model_config = {"extra": "ignore"}


class ToolInvokeRequestDTO(BaseModel):
    """Tool invocation request (BC-2 interface)."""

    tool_id: str = Field(..., description="Tool identifier to invoke")
    tool_version: Optional[str] = Field(None, description="Specific version (default: latest)")
    agent_did: str = Field(..., description="Calling agent DID")
    tenant_id: str = Field(..., description="Tenant identifier")
    session_id: str = Field(..., description="Session identifier")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool input parameters")
    resource_limits: Optional[ResourceLimitsDTO] = Field(None, description="Resource constraints")
    document_context: Optional[DocumentContextDTO] = Field(None, description="Document access context")
    checkpoint_config: Optional[CheckpointConfigDTO] = Field(None, description="Checkpoint settings")
    async_mode: bool = Field(False, description="Enable async execution")
    priority: int = Field(5, ge=1, le=10, description="Execution priority")
    timeout_seconds: Optional[int] = Field(None, ge=1, le=3600, description="Execution timeout override")
    idempotency_key: Optional[str] = Field(None, max_length=255, description="Idempotency key")

    model_config = {"extra": "ignore"}


class ErrorResponseDTO(BaseModel):
    """Structured error response."""

    code: str = Field(..., description="Error code (E3xxx)")
    message: str = Field(..., description="Human-readable error message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional error context")
    retryable: bool = Field(False, description="Whether the operation can be retried")

    model_config = {"extra": "ignore"}


class ExecutionMetadataDTO(BaseModel):
    """Tool execution metadata for observability."""

    duration_ms: Optional[int] = Field(None, ge=0, description="Execution duration in milliseconds")
    cpu_used_millicore_seconds: Optional[int] = Field(None, ge=0, description="CPU usage")
    memory_peak_mb: Optional[int] = Field(None, ge=0, description="Peak memory usage")
    network_bytes_sent: Optional[int] = Field(None, ge=0, description="Network bytes sent")
    network_bytes_received: Optional[int] = Field(None, ge=0, description="Network bytes received")
    documents_accessed: List[Dict[str, Any]] = Field(default_factory=list, description="Documents accessed")
    checkpoints_created: List[Dict[str, Any]] = Field(default_factory=list, description="Checkpoints created")

    model_config = {"extra": "ignore"}


class PollingInfoDTO(BaseModel):
    """Polling information for async tool execution."""

    task_id: str = Field(..., description="Task identifier for polling")
    poll_url: str = Field(..., description="URL to poll for status")
    poll_interval_ms: int = Field(1000, ge=100, le=30000, description="Recommended poll interval")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")

    model_config = {"extra": "ignore"}


class ToolInvokeResponseDTO(BaseModel):
    """Tool invocation response (BC-2 interface)."""

    invocation_id: str = Field(..., description="Unique invocation identifier")
    status: str = Field(..., description="Execution status")
    result: Optional[Dict[str, Any]] = Field(None, description="Tool execution result")
    error: Optional[ErrorResponseDTO] = Field(None, description="Error details if failed")
    execution_metadata: Optional[ExecutionMetadataDTO] = Field(None, description="Execution metrics")
    checkpoint_ref: Optional[str] = Field(None, description="Final checkpoint ID")
    polling_info: Optional[PollingInfoDTO] = Field(None, description="Async polling info")
    task_id: Optional[str] = Field(None, description="Task ID for async execution")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")

    model_config = {"extra": "ignore"}

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: Any) -> str:
        if isinstance(v, ToolStatus):
            return v.value
        return str(v)


class TaskStatusDTO(BaseModel):
    """Async task status response."""

    task_id: str = Field(..., description="Task identifier")
    tool_id: str = Field(..., description="Tool being executed")
    invocation_id: str = Field(..., description="Original invocation ID")
    status: str = Field(..., description="Task status (pending, running, success, error, cancelled)")
    progress_percent: Optional[int] = Field(None, ge=0, le=100, description="Execution progress")
    result: Optional[Dict[str, Any]] = Field(None, description="Result if completed")
    error: Optional[ErrorResponseDTO] = Field(None, description="Error if failed")
    created_at: datetime = Field(..., description="Task creation time")
    updated_at: datetime = Field(..., description="Last status update")
    completed_at: Optional[datetime] = Field(None, description="Completion time")

    model_config = {"extra": "ignore"}


class TaskCancelResponseDTO(BaseModel):
    """Response for task cancellation."""

    task_id: str = Field(..., description="Cancelled task ID")
    cancelled: bool = Field(..., description="Whether cancellation succeeded")
    message: str = Field(..., description="Cancellation result message")

    model_config = {"extra": "ignore"}

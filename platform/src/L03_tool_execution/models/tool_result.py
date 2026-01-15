"""
Tool Result Models

Defines tool invocation request, response, and result structures.
Based on Section 4 (Interfaces) and BC-2 boundary condition.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4


class ToolStatus(Enum):
    """Tool invocation status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    PERMISSION_DENIED = "permission_denied"
    PENDING_APPROVAL = "pending_approval"


@dataclass
class ToolError:
    """Structured error information for tool failures"""
    code: str  # Error code (E3xxx)
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    retryable: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "retryable": self.retryable,
        }


@dataclass
class DocumentContext:
    """
    Document context for tool execution (Phase 15 integration).

    Provides tools with access to authoritative documents.
    """
    document_refs: List[str] = field(default_factory=list)  # Document IDs to access
    version_pinning: bool = True  # Pin document versions during execution
    query: Optional[str] = None  # Semantic search query for documents

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_refs": self.document_refs,
            "version_pinning": self.version_pinning,
            "query": self.query,
        }


@dataclass
class CheckpointConfig:
    """
    Checkpoint configuration for resumable operations (Phase 16 integration).

    Controls hybrid checkpointing strategy (micro/macro/named).
    """
    enable_checkpointing: bool = False
    interval_seconds: int = 30  # Micro-checkpoint interval
    resume_from: Optional[str] = None  # Checkpoint ID to resume from

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enable_checkpointing": self.enable_checkpointing,
            "interval_seconds": self.interval_seconds,
            "resume_from": self.resume_from,
        }


@dataclass
class ExecutionOptions:
    """
    Tool execution options (Gap G-004, Gap G-005).

    Controls async execution, priority, idempotency, and approval requirements.
    """
    async_mode: bool = False  # Long-running tool (>30s) with async pattern
    priority: int = 5  # 1-10, higher = more important (Gap G-005)
    idempotency_key: Optional[str] = None  # For duplicate request detection
    require_approval: Optional[bool] = None  # Override tool manifest setting

    def to_dict(self) -> Dict[str, Any]:
        return {
            "async_mode": self.async_mode,
            "priority": self.priority,
            "idempotency_key": self.idempotency_key,
            "require_approval": self.require_approval,
        }


@dataclass
class AgentContext:
    """
    Agent context for tool invocation (BC-1 nested sandbox).

    Provides parent sandbox context and identity information.
    """
    agent_did: str  # Agent decentralized identifier
    tenant_id: str  # Multi-tenant isolation
    session_id: str  # Agent session identifier
    capability_token: Optional[str] = None  # JWT capability token (Gap G-006)
    parent_sandbox_id: Optional[str] = None  # L02 parent sandbox reference

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_did": self.agent_did,
            "tenant_id": self.tenant_id,
            "session_id": self.session_id,
            "capability_token": self.capability_token,
            "parent_sandbox_id": self.parent_sandbox_id,
        }


@dataclass
class ResourceLimits:
    """
    Resource allocation limits for tool execution.

    Sub-allocated from agent limits (BC-1 constraint).
    """
    cpu_millicore_limit: Optional[int] = None  # CPU limit in millicores
    memory_mb_limit: Optional[int] = None  # Memory limit in MB
    timeout_seconds: Optional[int] = None  # Execution timeout

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_millicore_limit": self.cpu_millicore_limit,
            "memory_mb_limit": self.memory_mb_limit,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass
class ToolInvokeRequest:
    """
    Tool invocation request (BC-2 interface from L11).

    Complete request structure for tool.invoke() method.
    """
    invocation_id: UUID = field(default_factory=uuid4)
    tool_id: str = ""
    tool_version: Optional[str] = None  # If None, use latest compatible version
    agent_context: Optional[AgentContext] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    resource_limits: Optional[ResourceLimits] = None
    document_context: Optional[DocumentContext] = None
    checkpoint_config: Optional[CheckpointConfig] = None
    execution_options: Optional[ExecutionOptions] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "invocation_id": str(self.invocation_id),
            "tool_id": self.tool_id,
            "tool_version": self.tool_version,
            "agent_context": self.agent_context.to_dict() if self.agent_context else None,
            "parameters": self.parameters,
            "resource_limits": self.resource_limits.to_dict() if self.resource_limits else None,
            "document_context": self.document_context.to_dict() if self.document_context else None,
            "checkpoint_config": self.checkpoint_config.to_dict() if self.checkpoint_config else None,
            "execution_options": self.execution_options.to_dict() if self.execution_options else None,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ExecutionMetadata:
    """
    Tool execution metadata for observability and analytics.

    Includes resource usage, documents accessed, and checkpoints created.
    """
    duration_ms: Optional[int] = None
    cpu_used_millicore_seconds: Optional[int] = None
    memory_peak_mb: Optional[int] = None
    network_bytes_sent: Optional[int] = None
    network_bytes_received: Optional[int] = None
    documents_accessed: List[Dict[str, Any]] = field(default_factory=list)  # Phase 15
    checkpoints_created: List[Dict[str, Any]] = field(default_factory=list)  # Phase 16

    def to_dict(self) -> Dict[str, Any]:
        return {
            "duration_ms": self.duration_ms,
            "cpu_used_millicore_seconds": self.cpu_used_millicore_seconds,
            "memory_peak_mb": self.memory_peak_mb,
            "network_bytes_sent": self.network_bytes_sent,
            "network_bytes_received": self.network_bytes_received,
            "documents_accessed": self.documents_accessed,
            "checkpoints_created": self.checkpoints_created,
        }


@dataclass
class PollingInfo:
    """
    Polling information for async tool execution (MCP Tasks).

    Provides polling endpoint and estimated completion time.
    """
    task_id: str
    poll_url: str
    poll_interval_seconds: int = 5
    estimated_completion: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "poll_url": self.poll_url,
            "poll_interval_seconds": self.poll_interval_seconds,
            "estimated_completion": self.estimated_completion.isoformat() if self.estimated_completion else None,
        }


@dataclass
class ToolResult:
    """
    Tool execution result with validated output.

    Result is validated against tool manifest result_schema (Gap G-010).
    """
    result: Any  # Tool-specific result (validated against manifest schema)
    result_type: str = "object"  # Type hint for deserialization

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result": self.result,
            "result_type": self.result_type,
        }


@dataclass
class ToolInvokeResponse:
    """
    Tool invocation response (BC-2 interface to L11).

    Complete response structure for tool.invoke() method.
    """
    invocation_id: UUID
    status: ToolStatus
    result: Optional[ToolResult] = None
    error: Optional[ToolError] = None
    execution_metadata: Optional[ExecutionMetadata] = None
    checkpoint_ref: Optional[str] = None  # Final checkpoint ID for resumable operations
    polling_info: Optional[PollingInfo] = None  # For async mode
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "invocation_id": str(self.invocation_id),
            "status": self.status.value,
            "result": self.result.to_dict() if self.result else None,
            "error": self.error.to_dict() if self.error else None,
            "execution_metadata": self.execution_metadata.to_dict() if self.execution_metadata else None,
            "checkpoint_ref": self.checkpoint_ref,
            "polling_info": self.polling_info.to_dict() if self.polling_info else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

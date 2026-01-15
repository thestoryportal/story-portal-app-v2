"""
Checkpoint Models

Defines checkpoint state for resumable tool operations (Phase 16 integration).
Based on Section 5.1.4 and MCP Tasks abstraction (Section 3.3.1a).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4


class CheckpointType(Enum):
    """Checkpoint type for hybrid checkpointing strategy"""
    MICRO = "micro"  # Redis, 30s intervals, 1-hour TTL
    MACRO = "macro"  # PostgreSQL, event milestones, 90-day retention
    NAMED = "named"  # PostgreSQL, manual recovery points, indefinite retention


class TaskStatus(Enum):
    """MCP Task status states (MCP 2025-11-25 specification)"""
    PENDING = "pending"  # Task queued but not started
    RUNNING = "running"  # Task actively executing
    COMPLETED = "completed"  # Task finished successfully
    FAILED = "failed"  # Task encountered error
    CANCELLED = "cancelled"  # Task cancelled by client


@dataclass
class TaskProgress:
    """
    Task progress information (MCP-aligned).

    Provides real-time progress updates for long-running tools.
    """
    current: int  # Current progress value (0-100)
    total: int = 100  # Total progress value (default 100 for percentage)
    message: Optional[str] = None  # Human-readable status message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current": self.current,
            "total": self.total,
            "message": self.message,
        }


@dataclass
class Task:
    """
    MCP Task representation for async tool execution.

    Implements MCP Tasks abstraction from Section 3.3.1a.
    """
    id: str  # Unique task identifier (format: "task:{tool_id}:{invocation_id}")
    status: TaskStatus  # Current task status
    progress: Optional[TaskProgress] = None  # Progress information
    result: Optional[Any] = None  # Task result (when completed)
    error: Optional[str] = None  # Error message (when failed)
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None  # Execution start timestamp
    completed_at: Optional[datetime] = None  # Completion timestamp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status.value,
            "progress": self.progress.to_dict() if self.progress else None,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class CheckpointConfig:
    """
    Checkpoint configuration for resumable operations.

    Controls hybrid checkpointing strategy (micro/macro/named).
    """
    enable_checkpointing: bool = False
    interval_seconds: int = 30  # Micro-checkpoint interval
    resume_from: Optional[str] = None  # Checkpoint ID to resume from
    enable_compression: bool = True  # Compress checkpoints > 10 KB (Gap G-016)
    enable_delta_encoding: bool = True  # Delta encoding for large states > 100 KB (Gap G-015)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enable_checkpointing": self.enable_checkpointing,
            "interval_seconds": self.interval_seconds,
            "resume_from": self.resume_from,
            "enable_compression": self.enable_compression,
            "enable_delta_encoding": self.enable_delta_encoding,
        }


@dataclass
class Checkpoint:
    """
    Checkpoint state for resumable tool operations.

    Corresponds to tool_checkpoints table in PostgreSQL (Section 5.1.4).
    """
    checkpoint_id: UUID = field(default_factory=uuid4)
    invocation_id: UUID = field(default_factory=uuid4)
    checkpoint_type: CheckpointType = CheckpointType.MICRO
    checkpoint_label: Optional[str] = None  # For named checkpoints

    # Delta encoding (Gap G-015)
    parent_checkpoint_id: Optional[UUID] = None  # For delta encoding
    is_delta: bool = False

    # State storage
    state: Dict[str, Any] = field(default_factory=dict)  # Tool execution state
    state_compressed: Optional[bytes] = None  # gzip/zstd compressed state (if > 10 KB)
    state_size_bytes: int = 0

    # Progress tracking
    progress_percent: int = 0
    current_phase: Optional[str] = None

    # Phase 15 integration: document version pinning
    document_versions: Dict[str, str] = field(default_factory=dict)  # {document_id: version}

    # Lifecycle
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None  # TTL for micro-checkpoints
    archived_at: Optional[datetime] = None  # When moved to S3 Glacier

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": str(self.checkpoint_id),
            "invocation_id": str(self.invocation_id),
            "checkpoint_type": self.checkpoint_type.value,
            "checkpoint_label": self.checkpoint_label,
            "parent_checkpoint_id": str(self.parent_checkpoint_id) if self.parent_checkpoint_id else None,
            "is_delta": self.is_delta,
            "state": self.state if not self.state_compressed else None,  # Don't serialize if compressed
            "state_size_bytes": self.state_size_bytes,
            "progress_percent": self.progress_percent,
            "current_phase": self.current_phase,
            "document_versions": self.document_versions,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
        }


@dataclass
class ToolInvocation:
    """
    Tool invocation record for audit trail and analytics.

    Corresponds to tool_invocations table in PostgreSQL (Section 5.1.3).
    """
    invocation_id: UUID
    tool_id: str
    tool_version: str
    agent_did: str
    tenant_id: str
    session_id: str

    # PII-sanitized parameters and result
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None

    # Status and error
    status: str = "pending"  # "success", "error", "timeout", etc.
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    # Execution metadata
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    cpu_used_millicore_seconds: Optional[int] = None
    memory_peak_mb: Optional[int] = None
    network_bytes_sent: Optional[int] = None
    network_bytes_received: Optional[int] = None

    # Phase 15 integration
    documents_accessed: List[Dict[str, Any]] = field(default_factory=list)  # [{document_id, version, access_count}]

    # Phase 16 integration
    checkpoints_created: List[Dict[str, Any]] = field(default_factory=list)  # [{checkpoint_id, type, timestamp}]
    checkpoint_ref: Optional[str] = None  # Final checkpoint ID for resumable operations

    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "invocation_id": str(self.invocation_id),
            "tool_id": self.tool_id,
            "tool_version": self.tool_version,
            "agent_did": self.agent_did,
            "tenant_id": self.tenant_id,
            "session_id": self.session_id,
            "parameters": self.parameters,
            "result": self.result,
            "status": self.status,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "cpu_used_millicore_seconds": self.cpu_used_millicore_seconds,
            "memory_peak_mb": self.memory_peak_mb,
            "network_bytes_sent": self.network_bytes_sent,
            "network_bytes_received": self.network_bytes_received,
            "documents_accessed": self.documents_accessed,
            "checkpoints_created": self.checkpoints_created,
            "checkpoint_ref": self.checkpoint_ref,
            "created_at": self.created_at.isoformat(),
        }

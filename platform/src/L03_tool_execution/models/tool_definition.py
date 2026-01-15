"""
Tool Definition Models

Defines tool registry entities including definitions, versions, and manifests.
Based on Section 5.1.1 and 5.1.2 of tool-execution-layer-specification-v1.2-ASCII.md
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4


class ToolCategory(Enum):
    """Tool category classification"""
    DATA_ACCESS = "data_access"
    COMPUTATION = "computation"
    EXTERNAL_API = "external_api"
    FILE_SYSTEM = "file_system"
    LLM_INTERACTION = "llm_interaction"


class DeprecationState(Enum):
    """Tool deprecation lifecycle state"""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    SUNSET = "sunset"
    REMOVED = "removed"


class SourceType(Enum):
    """Tool source type"""
    MCP = "mcp"
    OPENAPI = "openapi"
    LANGCHAIN = "langchain"
    NATIVE = "native"


class ExecutionMode(Enum):
    """Tool execution mode (MCP Tasks abstraction)"""
    SYNC = "sync"
    ASYNC = "async"
    BOTH = "both"


@dataclass
class RetryPolicy:
    """Retry policy configuration for tool execution"""
    max_attempts: int = 3
    base_delay_ms: int = 1000
    max_delay_ms: int = 60000
    retryable_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_attempts": self.max_attempts,
            "base_delay_ms": self.base_delay_ms,
            "max_delay_ms": self.max_delay_ms,
            "retryable_errors": self.retryable_errors,
        }


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration for external API resilience"""
    failure_rate_threshold: float = 50.0  # Percentage
    sliding_window_size: int = 100  # Number of calls
    wait_duration_seconds: int = 60  # Wait time in open state

    def to_dict(self) -> Dict[str, Any]:
        return {
            "failure_rate_threshold": self.failure_rate_threshold,
            "sliding_window_size": self.sliding_window_size,
            "wait_duration_seconds": self.wait_duration_seconds,
        }


@dataclass
class ToolPermissions:
    """Tool permission requirements"""
    filesystem: List[Dict[str, str]] = field(default_factory=list)  # [{path, mode}]
    network: List[Dict[str, Any]] = field(default_factory=list)  # [{host, port}]
    credentials: List[str] = field(default_factory=list)  # [credential_names]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filesystem": self.filesystem,
            "network": self.network,
            "credentials": self.credentials,
        }


@dataclass
class ExecutionConfig:
    """Tool execution configuration"""
    default_timeout_seconds: int = 30
    default_cpu_millicore_limit: int = 500
    default_memory_mb_limit: int = 1024
    requires_approval: bool = False
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    circuit_breaker_config: Optional[CircuitBreakerConfig] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "default_timeout_seconds": self.default_timeout_seconds,
            "default_cpu_millicore_limit": self.default_cpu_millicore_limit,
            "default_memory_mb_limit": self.default_memory_mb_limit,
            "requires_approval": self.requires_approval,
            "retry_policy": self.retry_policy.to_dict(),
            "circuit_breaker_config": self.circuit_breaker_config.to_dict() if self.circuit_breaker_config else None,
        }


@dataclass
class ToolManifest:
    """
    Complete tool manifest with parameters, result schema, and configuration.

    Follows the JSON Schema 2020-12 specification defined in Section 5.2.1.
    """
    tool_id: str
    tool_name: str
    version: str
    description: str
    category: ToolCategory
    parameters_schema: Dict[str, Any]  # JSON Schema for parameters
    result_schema: Optional[Dict[str, Any]] = None  # JSON Schema for result validation (Gap G-010)
    permissions: ToolPermissions = field(default_factory=ToolPermissions)
    execution_config: ExecutionConfig = field(default_factory=ExecutionConfig)
    execution_mode: ExecutionMode = ExecutionMode.SYNC
    estimated_duration_seconds: Optional[int] = None
    progress_updates: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "tool_name": self.tool_name,
            "version": self.version,
            "description": self.description,
            "category": self.category.value,
            "parameters_schema": self.parameters_schema,
            "result_schema": self.result_schema,
            "permissions": self.permissions.to_dict(),
            "execution_config": self.execution_config.to_dict(),
            "execution_mode": self.execution_mode.value,
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "progress_updates": self.progress_updates,
        }


@dataclass
class ToolDefinition:
    """
    Tool registry entry with capability manifest and semantic embedding.

    Corresponds to tool_definitions table in PostgreSQL (Section 5.1.1).
    """
    tool_id: str
    tool_name: str
    description: str
    category: ToolCategory
    latest_version: str
    source_type: SourceType
    tags: List[str] = field(default_factory=list)
    source_metadata: Dict[str, Any] = field(default_factory=dict)
    deprecation_state: DeprecationState = DeprecationState.ACTIVE
    deprecation_date: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # Capability manifest fields (Gap G-001)
    requires_approval: bool = False
    default_timeout_seconds: int = 30
    default_cpu_millicore_limit: int = 500
    default_memory_mb_limit: int = 1024
    required_permissions: Dict[str, Any] = field(default_factory=dict)
    result_schema: Optional[Dict[str, Any]] = None
    retry_policy: Optional[Dict[str, Any]] = None
    circuit_breaker_config: Optional[Dict[str, Any]] = None

    # Semantic search (pgvector)
    description_embedding: Optional[List[float]] = None  # 768-dim vector

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "tool_name": self.tool_name,
            "description": self.description,
            "category": self.category.value,
            "tags": self.tags,
            "latest_version": self.latest_version,
            "source_type": self.source_type.value,
            "source_metadata": self.source_metadata,
            "deprecation_state": self.deprecation_state.value,
            "deprecation_date": self.deprecation_date.isoformat() if self.deprecation_date else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "requires_approval": self.requires_approval,
            "default_timeout_seconds": self.default_timeout_seconds,
            "default_cpu_millicore_limit": self.default_cpu_millicore_limit,
            "default_memory_mb_limit": self.default_memory_mb_limit,
            "required_permissions": self.required_permissions,
            "result_schema": self.result_schema,
            "retry_policy": self.retry_policy,
            "circuit_breaker_config": self.circuit_breaker_config,
        }


@dataclass
class ToolVersion:
    """
    Tool version history entry supporting multiple concurrent versions.

    Corresponds to tool_versions table in PostgreSQL (Section 5.1.2).
    """
    version_id: UUID
    tool_id: str
    version: str  # Semantic version (e.g., "2.1.0")
    manifest: ToolManifest
    compatibility_range: Optional[str] = None  # Compatible agent versions (e.g., "^1.0.0")
    release_notes: Optional[str] = None
    deprecated_in_favor_of: Optional[str] = None  # Version to migrate to (Gap G-003)
    created_at: datetime = field(default_factory=datetime.utcnow)
    removed_at: Optional[datetime] = None  # Set when version removed (Gap G-003)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_id": str(self.version_id),
            "tool_id": self.tool_id,
            "version": self.version,
            "manifest": self.manifest.to_dict(),
            "compatibility_range": self.compatibility_range,
            "release_notes": self.release_notes,
            "deprecated_in_favor_of": self.deprecated_in_favor_of,
            "created_at": self.created_at.isoformat(),
            "removed_at": self.removed_at.isoformat() if self.removed_at else None,
        }

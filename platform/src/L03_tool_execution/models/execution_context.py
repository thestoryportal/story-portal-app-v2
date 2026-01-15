"""
Execution Context Models

Defines sandbox configuration and resource limits for tool execution.
Based on BC-1 nested sandbox interface and Section 3.3.2.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List


class IsolationTechnology(Enum):
    """Sandbox isolation technology"""
    GVISOR = "gvisor"  # Cloud deployments (user-space kernel)
    FIRECRACKER = "firecracker"  # On-prem deployments (microVMs)
    RUNC = "runc"  # Minimal isolation (trusted tools only)


class NetworkPolicy(Enum):
    """Network isolation level (BC-1 constraint)"""
    ISOLATED = "isolated"  # No network access
    RESTRICTED = "restricted"  # Limited egress to approved hosts
    ALLOW_EGRESS = "allow_egress"  # Full egress allowed


@dataclass
class ResourceLimits:
    """
    Resource allocation limits for tool execution.

    Sub-allocated from agent limits (BC-1 constraint).
    Tool limits must be <= agent limits.
    """
    cpu_millicore_limit: int = 500  # CPU limit in millicores
    memory_mb_limit: int = 1024  # Memory limit in MB
    timeout_seconds: int = 30  # Execution timeout
    disk_mb_limit: Optional[int] = None  # Ephemeral disk limit

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_millicore_limit": self.cpu_millicore_limit,
            "memory_mb_limit": self.memory_mb_limit,
            "timeout_seconds": self.timeout_seconds,
            "disk_mb_limit": self.disk_mb_limit,
        }

    def validate_against_parent(self, parent_limits: "ResourceLimits") -> bool:
        """
        Validate that tool limits are within parent agent limits (BC-1).

        Returns:
            True if valid, False if tool exceeds agent limits
        """
        if self.cpu_millicore_limit > parent_limits.cpu_millicore_limit:
            return False
        if self.memory_mb_limit > parent_limits.memory_mb_limit:
            return False
        if self.timeout_seconds > parent_limits.timeout_seconds:
            return False
        return True


@dataclass
class FilesystemPolicy:
    """
    Filesystem access policy for tool sandbox.

    Subset of agent filesystem mounts (BC-1 constraint).
    """
    mount_paths: List[Dict[str, str]] = field(default_factory=list)  # [{path, mode}]
    read_only_root: bool = True
    temp_dir_size_mb: int = 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mount_paths": self.mount_paths,
            "read_only_root": self.read_only_root,
            "temp_dir_size_mb": self.temp_dir_size_mb,
        }


@dataclass
class NetworkPolicyConfig:
    """
    Network access policy for tool sandbox.

    Subset of agent network access (BC-1 constraint).
    """
    policy: NetworkPolicy = NetworkPolicy.RESTRICTED
    allowed_hosts: List[str] = field(default_factory=list)  # Hostnames or IP ranges
    allowed_ports: List[int] = field(default_factory=list)
    dns_servers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy": self.policy.value,
            "allowed_hosts": self.allowed_hosts,
            "allowed_ports": self.allowed_ports,
            "dns_servers": self.dns_servers,
        }


@dataclass
class SecurityContext:
    """
    Security context for sandbox execution.

    Follows Kubernetes security context model.
    """
    run_as_non_root: bool = True
    run_as_user: int = 65534  # nobody user
    run_as_group: int = 65534  # nobody group
    fs_group: int = 65534
    read_only_root_filesystem: bool = True
    allow_privilege_escalation: bool = False
    capabilities_drop: List[str] = field(default_factory=lambda: ["ALL"])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_as_non_root": self.run_as_non_root,
            "run_as_user": self.run_as_user,
            "run_as_group": self.run_as_group,
            "fs_group": self.fs_group,
            "read_only_root_filesystem": self.read_only_root_filesystem,
            "allow_privilege_escalation": self.allow_privilege_escalation,
            "capabilities_drop": self.capabilities_drop,
        }


@dataclass
class SandboxConfig:
    """
    Complete sandbox configuration for tool execution.

    Combines resource limits, isolation, and security policies.
    Implements BC-1 nested sandbox interface.
    """
    isolation_technology: IsolationTechnology = IsolationTechnology.GVISOR
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)
    filesystem_policy: FilesystemPolicy = field(default_factory=FilesystemPolicy)
    network_policy: NetworkPolicyConfig = field(default_factory=NetworkPolicyConfig)
    security_context: SecurityContext = field(default_factory=SecurityContext)
    environment_variables: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "isolation_technology": self.isolation_technology.value,
            "resource_limits": self.resource_limits.to_dict(),
            "filesystem_policy": self.filesystem_policy.to_dict(),
            "network_policy": self.network_policy.to_dict(),
            "security_context": self.security_context.to_dict(),
            "environment_variables": self.environment_variables,
        }


@dataclass
class ExecutionContext:
    """
    Complete execution context for tool invocation.

    Includes agent context, sandbox config, and runtime state.
    Implements BC-1 nested sandbox context from L02.
    """
    agent_did: str  # Agent decentralized identifier
    tenant_id: str  # Multi-tenant isolation
    session_id: str  # Agent session identifier
    parent_sandbox_id: Optional[str] = None  # L02 parent sandbox reference (BC-1)
    sandbox_config: SandboxConfig = field(default_factory=SandboxConfig)
    tool_sandbox_id: Optional[str] = None  # Created sandbox ID
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_did": self.agent_did,
            "tenant_id": self.tenant_id,
            "session_id": self.session_id,
            "parent_sandbox_id": self.parent_sandbox_id,
            "sandbox_config": self.sandbox_config.to_dict(),
            "tool_sandbox_id": self.tool_sandbox_id,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

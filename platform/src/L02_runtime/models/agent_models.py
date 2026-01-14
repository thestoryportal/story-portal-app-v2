"""
Agent Runtime Data Models

Defines core data structures for agent instances, configurations, and lifecycle management.
Based on Section 5 of agent-runtime-layer-specification-v1.2-final-ASCII.md
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4


class AgentState(Enum):
    """Agent lifecycle state"""
    PENDING = "pending"
    RUNNING = "running"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    FAILED = "failed"


class TrustLevel(Enum):
    """Code trust classification for sandbox selection"""
    TRUSTED = "trusted"
    STANDARD = "standard"
    UNTRUSTED = "untrusted"
    CONFIDENTIAL = "confidential"


class NetworkPolicy(Enum):
    """Network isolation level"""
    ISOLATED = "isolated"           # No network access
    RESTRICTED = "restricted"       # Limited egress to approved services
    ALLOW_EGRESS = "allow_egress"  # Full egress allowed


class RuntimeClass(Enum):
    """Container runtime types"""
    RUNC = "runc"          # Standard OCI runtime (minimal isolation)
    GVISOR = "gvisor"      # User-space kernel (application kernel sandbox)
    KATA = "kata"          # Lightweight VM (strong isolation)
    KATA_CC = "kata-cc"    # Kata with confidential computing


@dataclass
class ResourceLimits:
    """Resource allocation limits"""
    cpu: str = "2"                    # CPU cores (e.g., "2", "500m")
    memory: str = "2Gi"               # Memory limit (e.g., "2Gi", "512Mi")
    tokens_per_hour: int = 100000     # Token budget per hour

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu": self.cpu,
            "memory": self.memory,
            "tokens_per_hour": self.tokens_per_hour,
        }


@dataclass
class ToolDefinition:
    """Tool available to the agent"""
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


@dataclass
class AgentConfig:
    """
    Agent configuration for spawning.

    This is the primary configuration object passed to spawn() operations.
    """
    agent_id: str
    trust_level: TrustLevel
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)
    tools: List[ToolDefinition] = field(default_factory=list)
    environment: Dict[str, str] = field(default_factory=dict)
    initial_context: Optional[Dict[str, Any]] = None
    recovery_checkpoint_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "trust_level": self.trust_level.value,
            "resource_limits": self.resource_limits.to_dict(),
            "tools": [tool.to_dict() for tool in self.tools],
            "environment": self.environment,
            "initial_context": self.initial_context,
            "recovery_checkpoint_id": self.recovery_checkpoint_id,
        }


@dataclass
class SandboxConfiguration:
    """
    Sandbox isolation settings for an agent.

    Maps trust levels to runtime classes and security contexts.
    """
    runtime_class: RuntimeClass
    trust_level: TrustLevel
    security_context: Dict[str, Any]
    network_policy: NetworkPolicy
    resource_limits: ResourceLimits

    @classmethod
    def from_trust_level(
        cls,
        trust_level: TrustLevel,
        resource_limits: ResourceLimits,
        runtime_class: Optional[RuntimeClass] = None
    ) -> "SandboxConfiguration":
        """Create sandbox config from trust level with sensible defaults"""

        # Default runtime class mapping
        if runtime_class is None:
            runtime_class_map = {
                TrustLevel.TRUSTED: RuntimeClass.RUNC,
                TrustLevel.STANDARD: RuntimeClass.GVISOR,
                TrustLevel.UNTRUSTED: RuntimeClass.KATA,
                TrustLevel.CONFIDENTIAL: RuntimeClass.KATA_CC,
            }
            runtime_class = runtime_class_map[trust_level]

        # Default security context
        security_context = {
            "run_as_non_root": True,
            "run_as_user": 65534,  # nobody
            "run_as_group": 65534,
            "fs_group": 65534,
            "read_only_root_filesystem": True,
            "allow_privilege_escalation": False,
            "seccomp_profile": {"type": "RuntimeDefault"},
            "capabilities": {"drop": ["ALL"]},
        }

        # Relaxed settings for trusted code
        if trust_level == TrustLevel.TRUSTED:
            security_context["read_only_root_filesystem"] = False

        # Network policy based on trust
        network_policy_map = {
            TrustLevel.TRUSTED: NetworkPolicy.ALLOW_EGRESS,
            TrustLevel.STANDARD: NetworkPolicy.RESTRICTED,
            TrustLevel.UNTRUSTED: NetworkPolicy.ISOLATED,
            TrustLevel.CONFIDENTIAL: NetworkPolicy.ISOLATED,
        }
        network_policy = network_policy_map[trust_level]

        return cls(
            runtime_class=runtime_class,
            trust_level=trust_level,
            security_context=security_context,
            network_policy=network_policy,
            resource_limits=resource_limits,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "runtime_class": self.runtime_class.value,
            "trust_level": self.trust_level.value,
            "security_context": self.security_context,
            "network_policy": self.network_policy.value,
            "resource_limits": self.resource_limits.to_dict(),
        }


@dataclass
class ResourceUsage:
    """Current resource consumption for an agent"""
    cpu_seconds: float = 0.0
    memory_peak_mb: float = 0.0
    tokens_consumed: int = 0
    network_bytes_sent: int = 0
    network_bytes_received: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_seconds": self.cpu_seconds,
            "memory_peak_mb": self.memory_peak_mb,
            "tokens_consumed": self.tokens_consumed,
            "network_bytes_sent": self.network_bytes_sent,
            "network_bytes_received": self.network_bytes_received,
        }


@dataclass
class SpawnResult:
    """
    Result of spawning an agent instance.

    Returned by RuntimeBackend.spawn() and AgentRuntime.spawn().
    """
    agent_id: str
    session_id: str
    state: AgentState
    sandbox_type: str
    container_id: Optional[str] = None
    pod_name: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "state": self.state.value,
            "sandbox_type": self.sandbox_type,
            "container_id": self.container_id,
            "pod_name": self.pod_name,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class AgentInstance:
    """
    Complete representation of a running or suspended agent instance.

    This is the primary entity stored in the runtime's state tracking.
    """
    agent_id: str
    session_id: str
    state: AgentState
    config: AgentConfig
    sandbox: SandboxConfiguration
    resource_usage: ResourceUsage = field(default_factory=ResourceUsage)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    terminated_at: Optional[datetime] = None

    # Backend-specific fields
    container_id: Optional[str] = None
    pod_name: Optional[str] = None
    backend_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "state": self.state.value,
            "config": self.config.to_dict(),
            "sandbox": self.sandbox.to_dict(),
            "resource_usage": self.resource_usage.to_dict(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "terminated_at": self.terminated_at.isoformat() if self.terminated_at else None,
            "container_id": self.container_id,
            "pod_name": self.pod_name,
            "backend_metadata": self.backend_metadata,
        }

    @classmethod
    def from_spawn_result(
        cls,
        result: SpawnResult,
        config: AgentConfig,
        sandbox: SandboxConfiguration
    ) -> "AgentInstance":
        """Create AgentInstance from spawn result"""
        return cls(
            agent_id=result.agent_id,
            session_id=result.session_id,
            state=result.state,
            config=config,
            sandbox=sandbox,
            container_id=result.container_id,
            pod_name=result.pod_name,
            created_at=result.created_at,
        )

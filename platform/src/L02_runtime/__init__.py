"""
L02 Agent Runtime Layer

Provides agent lifecycle management, execution, and orchestration.

Phase 1 Foundation (implemented):
- Data models
- RuntimeBackend abstraction (LocalRuntime, KubernetesRuntime stub)
- Sandbox Manager
- Lifecycle Manager

Future phases:
- Agent Executor (Phase 2)
- Resource Manager (Phase 2)
- State Manager (Phase 3)
- SessionBridge enhancement (Phase 3)
- DocumentBridge (Phase 4)
- Fleet Manager (Phase 5)
- Health Monitor (Phase 6)
- Workflow Engine (Phase 7)
"""

from .models import (
    AgentState,
    TrustLevel,
    AgentConfig,
    ResourceLimits,
    SandboxConfiguration,
    SpawnResult,
    AgentInstance,
)

from .backends import (
    RuntimeBackend,
    LocalRuntime,
    KubernetesRuntime,
)

from .services import (
    SandboxManager,
    LifecycleManager,
)

from .runtime import AgentRuntime

__version__ = "0.1.0"

__all__ = [
    # Models
    "AgentState",
    "TrustLevel",
    "AgentConfig",
    "ResourceLimits",
    "SandboxConfiguration",
    "SpawnResult",
    "AgentInstance",
    # Backends
    "RuntimeBackend",
    "LocalRuntime",
    "KubernetesRuntime",
    # Services
    "SandboxManager",
    "LifecycleManager",
    # Main Runtime
    "AgentRuntime",
]

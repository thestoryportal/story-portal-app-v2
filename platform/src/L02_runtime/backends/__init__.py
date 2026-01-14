"""
Runtime Backend Abstraction

Provides pluggable runtime backends for agent execution:
- LocalRuntime: Docker containers or process isolation for local dev
- KubernetesRuntime: Full K8s integration for production

The RuntimeBackend protocol defines the interface that all backends must implement.
"""

from .protocol import RuntimeBackend, ContainerInfo, ContainerState
from .local_runtime import LocalRuntime
from .kubernetes_runtime import KubernetesRuntime

__all__ = [
    "RuntimeBackend",
    "ContainerInfo",
    "ContainerState",
    "LocalRuntime",
    "KubernetesRuntime",
]

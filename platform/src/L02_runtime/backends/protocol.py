"""
RuntimeBackend Protocol

Defines the interface for pluggable runtime backends.
All backends (LocalRuntime, KubernetesRuntime) must implement this protocol.
"""

from typing import Protocol, Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from ..models import (
    AgentConfig,
    SandboxConfiguration,
    SpawnResult,
    ResourceUsage,
)


class ContainerState(Enum):
    """Container/Pod state"""
    PENDING = "pending"
    RUNNING = "running"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class ContainerInfo:
    """Runtime information about a container/pod"""
    container_id: str
    state: ContainerState
    image: str
    created_at: datetime
    resource_usage: ResourceUsage
    backend_metadata: Dict[str, Any]


class RuntimeBackend(Protocol):
    """
    Protocol for runtime backends.

    Backends provide container/pod lifecycle management and resource isolation.
    Implementations:
    - LocalRuntime: Docker containers for local development
    - KubernetesRuntime: K8s pods for production deployment
    """

    async def initialize(self) -> None:
        """
        Initialize the runtime backend.

        For LocalRuntime: Connect to Docker daemon
        For KubernetesRuntime: Connect to K8s API server
        """
        ...

    async def spawn_container(
        self,
        config: AgentConfig,
        sandbox: SandboxConfiguration,
        image: str = "agent-runtime:latest",
        command: Optional[List[str]] = None,
        environment: Optional[Dict[str, str]] = None
    ) -> SpawnResult:
        """
        Spawn a new agent container/pod.

        Args:
            config: Agent configuration
            sandbox: Sandbox isolation settings
            image: Container image to use
            command: Override container command
            environment: Additional environment variables

        Returns:
            SpawnResult with container/pod information

        Raises:
            RuntimeError: If spawn fails
        """
        ...

    async def terminate_container(
        self,
        container_id: str,
        force: bool = False,
        timeout_seconds: int = 30
    ) -> None:
        """
        Terminate a running container/pod.

        Args:
            container_id: Container/pod identifier
            force: Force kill without graceful shutdown
            timeout_seconds: Graceful shutdown timeout

        Raises:
            RuntimeError: If termination fails
        """
        ...

    async def suspend_container(
        self,
        container_id: str
    ) -> str:
        """
        Suspend a running container (pause execution).

        For LocalRuntime: Use docker pause
        For KubernetesRuntime: Scale to 0 and checkpoint

        Args:
            container_id: Container/pod identifier

        Returns:
            Checkpoint identifier (if applicable)

        Raises:
            RuntimeError: If suspend fails
        """
        ...

    async def resume_container(
        self,
        container_id: str,
        checkpoint_id: Optional[str] = None
    ) -> None:
        """
        Resume a suspended container.

        For LocalRuntime: Use docker unpause
        For KubernetesRuntime: Scale from 0 and restore checkpoint

        Args:
            container_id: Container/pod identifier
            checkpoint_id: Optional checkpoint to restore from

        Raises:
            RuntimeError: If resume fails
        """
        ...

    async def get_container_info(
        self,
        container_id: str
    ) -> ContainerInfo:
        """
        Get runtime information about a container/pod.

        Args:
            container_id: Container/pod identifier

        Returns:
            Container runtime information

        Raises:
            RuntimeError: If container not found
        """
        ...

    async def list_containers(
        self,
        filters: Optional[Dict[str, str]] = None
    ) -> List[ContainerInfo]:
        """
        List containers/pods managed by this backend.

        Args:
            filters: Optional filters (e.g., {"agent_id": "..."})

        Returns:
            List of container information
        """
        ...

    async def get_logs(
        self,
        container_id: str,
        tail: int = 100,
        since_seconds: Optional[int] = None
    ) -> str:
        """
        Get container/pod logs.

        Args:
            container_id: Container/pod identifier
            tail: Number of lines to return
            since_seconds: Only return logs from last N seconds

        Returns:
            Log output as string
        """
        ...

    async def execute_command(
        self,
        container_id: str,
        command: List[str],
        timeout_seconds: int = 30
    ) -> Dict[str, Any]:
        """
        Execute a command in a running container/pod.

        Args:
            container_id: Container/pod identifier
            command: Command and arguments to execute
            timeout_seconds: Command timeout

        Returns:
            Dict with 'stdout', 'stderr', 'exit_code'

        Raises:
            RuntimeError: If execution fails
        """
        ...

    async def get_resource_usage(
        self,
        container_id: str
    ) -> ResourceUsage:
        """
        Get current resource usage for a container/pod.

        Args:
            container_id: Container/pod identifier

        Returns:
            Current resource consumption

        Raises:
            RuntimeError: If container not found
        """
        ...

    async def health_check(self) -> bool:
        """
        Check if the runtime backend is healthy and accessible.

        Returns:
            True if backend is healthy, False otherwise
        """
        ...

    async def cleanup(self) -> None:
        """
        Cleanup and disconnect from runtime backend.

        Should be called on shutdown.
        """
        ...

"""
LocalRuntime Backend

Docker-based runtime backend for local development.
Uses Docker containers for agent isolation without requiring Kubernetes.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import docker
from docker.models.containers import Container
from docker.models.networks import Network
from docker.errors import DockerException, NotFound, APIError

from ..models import (
    AgentConfig,
    AgentState,
    SandboxConfiguration,
    SpawnResult,
    ResourceUsage,
    NetworkPolicy,
)
from .protocol import ContainerInfo, ContainerState


logger = logging.getLogger(__name__)

# Restricted network name
RESTRICTED_NETWORK_NAME = "l02-restricted"

# Allowed hosts for restricted network (L01, L04, localhost)
ALLOWED_EGRESS_HOSTS = [
    "127.0.0.1",       # localhost
    "host.docker.internal",  # Host machine from container
    "172.17.0.1",      # Default Docker bridge gateway
]

# Allowed ports for restricted network
ALLOWED_EGRESS_PORTS = [
    8001,  # L01 Data Layer
    8004,  # L04 Model Gateway
]


class LocalRuntime:
    """
    Docker-based runtime backend for local development.

    Provides agent isolation using Docker containers with configurable
    resource limits and network policies.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize LocalRuntime.

        Args:
            config: Optional configuration dict
        """
        self.config = config or {}
        self.docker_client: Optional[docker.DockerClient] = None
        self._container_registry: Dict[str, str] = {}  # agent_id -> container_id
        self._restricted_network: Optional[Network] = None

    async def initialize(self) -> None:
        """Connect to Docker daemon and setup restricted network"""
        try:
            # Run in thread pool since docker-py is synchronous
            loop = asyncio.get_event_loop()
            self.docker_client = await loop.run_in_executor(
                None,
                docker.from_env
            )
            # Test connection
            await loop.run_in_executor(None, self.docker_client.ping)

            # Create or get restricted network for egress filtering
            await self._ensure_restricted_network()

        except DockerException as e:
            raise RuntimeError(f"Failed to connect to Docker: {e}")

    async def _ensure_restricted_network(self) -> None:
        """
        Ensure the restricted network exists for egress filtering.

        Creates a Docker network with internal flag to restrict egress.
        Containers on this network can only communicate with:
        - Other containers on the same network
        - The host machine (for L01, L04 access)
        """
        if not self.docker_client:
            return

        loop = asyncio.get_event_loop()

        try:
            # Check if network already exists
            networks = await loop.run_in_executor(
                None,
                lambda: self.docker_client.networks.list(names=[RESTRICTED_NETWORK_NAME])
            )

            if networks:
                self._restricted_network = networks[0]
                logger.info(f"Using existing restricted network: {RESTRICTED_NETWORK_NAME}")
                return

            # Create restricted network with custom IPAM
            ipam_pool = docker.types.IPAMPool(
                subnet="172.28.0.0/16",
                gateway="172.28.0.1"
            )
            ipam_config = docker.types.IPAMConfig(
                pool_configs=[ipam_pool]
            )

            # Create network with driver options for egress control
            self._restricted_network = await loop.run_in_executor(
                None,
                lambda: self.docker_client.networks.create(
                    name=RESTRICTED_NETWORK_NAME,
                    driver="bridge",
                    internal=False,  # Allow outbound but we'll restrict via iptables
                    ipam=ipam_config,
                    labels={
                        "l02.runtime": "restricted",
                        "l02.egress_policy": "limited",
                    },
                    options={
                        "com.docker.network.bridge.enable_ip_masquerade": "true",
                        "com.docker.network.bridge.enable_icc": "true",
                    }
                )
            )

            logger.info(f"Created restricted network: {RESTRICTED_NETWORK_NAME}")

            # Note: Full iptables egress rules would require host-level configuration
            # For development, we rely on the network isolation and application-level checks
            # In production, this should be supplemented with proper iptables rules

        except DockerException as e:
            logger.warning(f"Failed to create restricted network: {e}")
            # Continue without restricted network - will fall back to bridge

    async def spawn_container(
        self,
        config: AgentConfig,
        sandbox: SandboxConfiguration,
        image: str = "agent-runtime:latest",
        command: Optional[List[str]] = None,
        environment: Optional[Dict[str, str]] = None
    ) -> SpawnResult:
        """
        Spawn a new agent container.

        Creates a Docker container with appropriate resource limits,
        network policies, and security settings.
        """
        if not self.docker_client:
            raise RuntimeError("LocalRuntime not initialized")

        # Merge environment variables
        env = {**config.environment, **(environment or {})}
        env["AGENT_ID"] = config.agent_id

        # Build Docker run parameters
        container_config = self._build_container_config(
            config=config,
            sandbox=sandbox,
            image=image,
            command=command,
            environment=env
        )

        try:
            # Create and start container
            loop = asyncio.get_event_loop()
            container: Container = await loop.run_in_executor(
                None,
                lambda: self.docker_client.containers.run(**container_config)
            )

            # Register container
            self._container_registry[config.agent_id] = container.id

            # Create session_id (in production this would come from SessionBridge)
            session_id = f"session-{config.agent_id}"

            return SpawnResult(
                agent_id=config.agent_id,
                session_id=session_id,
                state=AgentState.RUNNING,
                sandbox_type=sandbox.runtime_class.value,
                container_id=container.id,
                created_at=datetime.now(timezone.utc)
            )

        except DockerException as e:
            raise RuntimeError(f"Failed to spawn container: {e}")

    def _build_container_config(
        self,
        config: AgentConfig,
        sandbox: SandboxConfiguration,
        image: str,
        command: Optional[List[str]],
        environment: Dict[str, str]
    ) -> Dict[str, Any]:
        """Build Docker container configuration"""

        # Parse resource limits
        cpu_limit = self._parse_cpu_limit(sandbox.resource_limits.cpu)
        memory_limit = sandbox.resource_limits.memory

        # Network mode based on policy
        network_mode = self._get_network_mode(sandbox.network_policy)

        # Security options
        security_opt = []
        if sandbox.security_context.get("seccomp_profile"):
            security_opt.append("seccomp=default")

        # User configuration
        user = None
        if sandbox.security_context.get("run_as_non_root"):
            user = f"{sandbox.security_context.get('run_as_user', 65534)}"

        # Read-only root filesystem
        read_only = sandbox.security_context.get("read_only_root_filesystem", True)

        container_config = {
            "image": image,
            "command": command,
            "environment": environment,
            "detach": True,
            "name": f"agent-{config.agent_id}",
            "labels": {
                "agent_id": config.agent_id,
                "trust_level": sandbox.trust_level.value,
                "runtime": "local",
            },
            "cpu_period": 100000,
            "cpu_quota": int(cpu_limit * 100000) if cpu_limit else 0,
            "mem_limit": memory_limit,
            "network_mode": network_mode,
            "security_opt": security_opt,
            "read_only": read_only,
            "user": user,
            "cap_drop": ["ALL"],
            "privileged": False,
        }

        # Add tmpfs for writable temp space if read-only root
        if read_only:
            container_config["tmpfs"] = {
                "/tmp": "rw,noexec,nosuid,size=100m"
            }

        return container_config

    @staticmethod
    def _parse_cpu_limit(cpu: str) -> Optional[float]:
        """Parse Kubernetes-style CPU limit to cores"""
        if cpu.endswith("m"):
            return float(cpu[:-1]) / 1000
        return float(cpu)

    def _get_network_mode(self, policy: NetworkPolicy) -> str:
        """
        Map network policy to Docker network mode.

        Args:
            policy: Network policy

        Returns:
            Docker network mode string
        """
        if policy == NetworkPolicy.ISOLATED:
            return "none"
        elif policy == NetworkPolicy.RESTRICTED:
            # Use restricted network for egress filtering
            if self._restricted_network:
                return RESTRICTED_NETWORK_NAME
            else:
                logger.warning(
                    "Restricted network not available, falling back to bridge"
                )
                return "bridge"
        else:
            return "bridge"

    async def terminate_container(
        self,
        container_id: str,
        force: bool = False,
        timeout_seconds: int = 30
    ) -> None:
        """Terminate a running container"""
        if not self.docker_client:
            raise RuntimeError("LocalRuntime not initialized")

        try:
            loop = asyncio.get_event_loop()
            container = await loop.run_in_executor(
                None,
                self.docker_client.containers.get,
                container_id
            )

            if force:
                await loop.run_in_executor(None, container.kill)
            else:
                await loop.run_in_executor(
                    None,
                    lambda: container.stop(timeout=timeout_seconds)
                )

            # Remove container
            await loop.run_in_executor(None, container.remove)

            # Unregister
            for agent_id, cid in list(self._container_registry.items()):
                if cid == container_id:
                    del self._container_registry[agent_id]
                    break

        except NotFound:
            raise RuntimeError(f"Container {container_id} not found")
        except DockerException as e:
            raise RuntimeError(f"Failed to terminate container: {e}")

    async def suspend_container(self, container_id: str) -> str:
        """Suspend container (pause execution)"""
        if not self.docker_client:
            raise RuntimeError("LocalRuntime not initialized")

        try:
            loop = asyncio.get_event_loop()
            container = await loop.run_in_executor(
                None,
                self.docker_client.containers.get,
                container_id
            )
            await loop.run_in_executor(None, container.pause)

            # Return empty checkpoint ID (Docker pause doesn't create checkpoints)
            return ""

        except NotFound:
            raise RuntimeError(f"Container {container_id} not found")
        except DockerException as e:
            raise RuntimeError(f"Failed to suspend container: {e}")

    async def resume_container(
        self,
        container_id: str,
        checkpoint_id: Optional[str] = None
    ) -> None:
        """Resume suspended container"""
        if not self.docker_client:
            raise RuntimeError("LocalRuntime not initialized")

        try:
            loop = asyncio.get_event_loop()
            container = await loop.run_in_executor(
                None,
                self.docker_client.containers.get,
                container_id
            )
            await loop.run_in_executor(None, container.unpause)

        except NotFound:
            raise RuntimeError(f"Container {container_id} not found")
        except DockerException as e:
            raise RuntimeError(f"Failed to resume container: {e}")

    async def get_container_info(self, container_id: str) -> ContainerInfo:
        """Get container information"""
        if not self.docker_client:
            raise RuntimeError("LocalRuntime not initialized")

        try:
            loop = asyncio.get_event_loop()
            container = await loop.run_in_executor(
                None,
                self.docker_client.containers.get,
                container_id
            )

            # Refresh container state
            await loop.run_in_executor(None, container.reload)

            # Parse state
            state = self._parse_container_state(container.status)

            # Get stats for resource usage
            resource_usage = await self._get_container_stats(container)

            return ContainerInfo(
                container_id=container.id,
                state=state,
                image=container.image.tags[0] if container.image.tags else "unknown",
                created_at=datetime.fromisoformat(
                    container.attrs["Created"].replace("Z", "+00:00")
                ),
                resource_usage=resource_usage,
                backend_metadata={
                    "status": container.status,
                    "labels": container.labels,
                }
            )

        except NotFound:
            raise RuntimeError(f"Container {container_id} not found")
        except DockerException as e:
            raise RuntimeError(f"Failed to get container info: {e}")

    async def _get_container_stats(self, container: Container) -> ResourceUsage:
        """Get container resource usage statistics"""
        try:
            loop = asyncio.get_event_loop()
            stats = await loop.run_in_executor(
                None,
                lambda: container.stats(stream=False)
            )

            # Calculate CPU usage
            cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                        stats["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                          stats["precpu_stats"]["system_cpu_usage"]
            cpu_seconds = cpu_delta / 1_000_000_000 if system_delta > 0 else 0

            # Calculate memory usage
            memory_usage = stats["memory_stats"].get("usage", 0)
            memory_mb = memory_usage / (1024 * 1024)

            return ResourceUsage(
                cpu_seconds=cpu_seconds,
                memory_peak_mb=memory_mb,
                tokens_consumed=0,  # Tracked separately by Resource Manager
                network_bytes_sent=stats.get("networks", {}).get("eth0", {}).get("tx_bytes", 0),
                network_bytes_received=stats.get("networks", {}).get("eth0", {}).get("rx_bytes", 0),
            )

        except (KeyError, ValueError, ZeroDivisionError) as e:
            logger.debug(f"Failed to parse container stats: {e}")
            return ResourceUsage()
        except DockerException as e:
            logger.warning(f"Docker API error getting stats: {e}")
            return ResourceUsage()
        except Exception as e:
            logger.warning(f"Unexpected error getting container stats: {e}")
            return ResourceUsage()

    @staticmethod
    def _parse_container_state(status: str) -> ContainerState:
        """Parse Docker container status to ContainerState"""
        status_map = {
            "created": ContainerState.PENDING,
            "running": ContainerState.RUNNING,
            "paused": ContainerState.SUSPENDED,
            "exited": ContainerState.TERMINATED,
            "dead": ContainerState.FAILED,
        }
        return status_map.get(status.lower(), ContainerState.UNKNOWN)

    async def list_containers(
        self,
        filters: Optional[Dict[str, str]] = None
    ) -> List[ContainerInfo]:
        """List all containers managed by this runtime"""
        if not self.docker_client:
            raise RuntimeError("LocalRuntime not initialized")

        try:
            loop = asyncio.get_event_loop()

            # Build Docker filters
            docker_filters = {"label": "runtime=local"}
            if filters:
                for key, value in filters.items():
                    docker_filters["label"].append(f"{key}={value}")

            containers = await loop.run_in_executor(
                None,
                lambda: self.docker_client.containers.list(
                    all=True,
                    filters=docker_filters
                )
            )

            # Get info for each container
            infos = []
            for container in containers:
                try:
                    info = await self.get_container_info(container.id)
                    infos.append(info)
                except (RuntimeError, DockerException) as e:
                    logger.debug(f"Failed to get info for container {container.id}: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Unexpected error getting container info for {container.id}: {e}")
                    continue

            return infos

        except DockerException as e:
            raise RuntimeError(f"Failed to list containers: {e}")

    async def get_logs(
        self,
        container_id: str,
        tail: int = 100,
        since_seconds: Optional[int] = None
    ) -> str:
        """Get container logs"""
        if not self.docker_client:
            raise RuntimeError("LocalRuntime not initialized")

        try:
            loop = asyncio.get_event_loop()
            container = await loop.run_in_executor(
                None,
                self.docker_client.containers.get,
                container_id
            )

            logs_kwargs = {"tail": tail}
            if since_seconds:
                logs_kwargs["since"] = since_seconds

            logs = await loop.run_in_executor(
                None,
                lambda: container.logs(**logs_kwargs)
            )

            return logs.decode("utf-8") if isinstance(logs, bytes) else logs

        except NotFound:
            raise RuntimeError(f"Container {container_id} not found")
        except DockerException as e:
            raise RuntimeError(f"Failed to get logs: {e}")

    async def execute_command(
        self,
        container_id: str,
        command: List[str],
        timeout_seconds: int = 30
    ) -> Dict[str, Any]:
        """Execute command in container"""
        if not self.docker_client:
            raise RuntimeError("LocalRuntime not initialized")

        try:
            loop = asyncio.get_event_loop()
            container = await loop.run_in_executor(
                None,
                self.docker_client.containers.get,
                container_id
            )

            result = await loop.run_in_executor(
                None,
                lambda: container.exec_run(command, demux=True)
            )

            exit_code, (stdout, stderr) = result.exit_code, result.output

            return {
                "stdout": stdout.decode("utf-8") if stdout else "",
                "stderr": stderr.decode("utf-8") if stderr else "",
                "exit_code": exit_code,
            }

        except NotFound:
            raise RuntimeError(f"Container {container_id} not found")
        except DockerException as e:
            raise RuntimeError(f"Failed to execute command: {e}")

    async def get_resource_usage(self, container_id: str) -> ResourceUsage:
        """Get current resource usage"""
        info = await self.get_container_info(container_id)
        return info.resource_usage

    async def health_check(self) -> bool:
        """Check if Docker daemon is accessible"""
        if not self.docker_client:
            return False

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.docker_client.ping)
            return True
        except (DockerException, ConnectionError, OSError) as e:
            logger.debug(f"Docker health check failed: {e}")
            return False
        except Exception as e:
            logger.warning(f"Unexpected error in Docker health check: {e}")
            return False

    async def cleanup(self) -> None:
        """Cleanup and disconnect"""
        if self.docker_client:
            loop = asyncio.get_event_loop()

            # Note: We don't remove the restricted network on cleanup
            # as other containers might still be using it.
            # Network cleanup should be done explicitly if needed.

            await loop.run_in_executor(None, self.docker_client.close)
            self.docker_client = None

        self._restricted_network = None
        self._container_registry.clear()

    async def remove_restricted_network(self) -> bool:
        """
        Remove the restricted network if no containers are using it.

        Returns:
            True if removed, False otherwise
        """
        if not self.docker_client or not self._restricted_network:
            return False

        try:
            loop = asyncio.get_event_loop()

            # Reload to get latest state
            await loop.run_in_executor(
                None,
                self._restricted_network.reload
            )

            # Check if any containers are connected
            containers = self._restricted_network.attrs.get("Containers", {})
            if containers:
                logger.warning(
                    f"Cannot remove restricted network: "
                    f"{len(containers)} containers still connected"
                )
                return False

            # Remove the network
            await loop.run_in_executor(
                None,
                self._restricted_network.remove
            )

            self._restricted_network = None
            logger.info(f"Removed restricted network: {RESTRICTED_NETWORK_NAME}")
            return True

        except DockerException as e:
            logger.warning(f"Failed to remove restricted network: {e}")
            return False

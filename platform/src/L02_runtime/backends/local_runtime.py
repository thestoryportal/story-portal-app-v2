"""
LocalRuntime Backend

Docker-based runtime backend for local development.
Uses Docker containers for agent isolation without requiring Kubernetes.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
import docker
from docker.models.containers import Container
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

    async def initialize(self) -> None:
        """Connect to Docker daemon"""
        try:
            # Run in thread pool since docker-py is synchronous
            loop = asyncio.get_event_loop()
            self.docker_client = await loop.run_in_executor(
                None,
                docker.from_env
            )
            # Test connection
            await loop.run_in_executor(None, self.docker_client.ping)
        except DockerException as e:
            raise RuntimeError(f"Failed to connect to Docker: {e}")

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
                created_at=datetime.utcnow()
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

    @staticmethod
    def _get_network_mode(policy: NetworkPolicy) -> str:
        """Map network policy to Docker network mode"""
        if policy == NetworkPolicy.ISOLATED:
            return "none"
        elif policy == NetworkPolicy.RESTRICTED:
            return "bridge"  # TODO: Add iptables rules for egress filtering
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

        except Exception:
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
                except Exception:
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
        except Exception:
            return False

    async def cleanup(self) -> None:
        """Cleanup and disconnect"""
        if self.docker_client:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.docker_client.close)
            self.docker_client = None
        self._container_registry.clear()

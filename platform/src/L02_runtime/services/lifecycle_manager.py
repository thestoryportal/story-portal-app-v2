"""
Lifecycle Manager

Manages the complete lifecycle of agent instances from spawn to termination.
Orchestrates RuntimeBackend operations with state tracking and error handling.

Based on Section 3.3.3 and 11.3 of agent-runtime-layer-specification-v1.2-final-ASCII.md
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import logging

from ..models import (
    AgentConfig,
    AgentState,
    AgentInstance,
    SpawnResult,
    SandboxConfiguration,
)
from ..backends.protocol import RuntimeBackend
from .sandbox_manager import SandboxManager, SandboxError


logger = logging.getLogger(__name__)


class LifecycleError(Exception):
    """Lifecycle operation error"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class LifecycleManager:
    """
    Manages agent lifecycle operations.

    Responsibilities:
    - Spawn agent instances with proper sandbox configuration
    - Terminate agents gracefully or forcefully
    - Suspend and resume agents
    - Track agent state
    - Handle restart policies
    """

    def __init__(
        self,
        backend: RuntimeBackend,
        sandbox_manager: SandboxManager,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize LifecycleManager.

        Args:
            backend: Runtime backend (LocalRuntime or KubernetesRuntime)
            sandbox_manager: Sandbox configuration manager
            config: Configuration dict with:
                - spawn_timeout_seconds: Timeout for spawn operations
                - graceful_shutdown_seconds: Graceful shutdown timeout
                - max_restart_count: Maximum automatic restarts
                - enable_suspend: Enable suspend/resume operations
        """
        self.backend = backend
        self.sandbox_manager = sandbox_manager
        self.config = config or {}

        # Configuration
        self.spawn_timeout = self.config.get("spawn_timeout_seconds", 60)
        self.shutdown_timeout = self.config.get("graceful_shutdown_seconds", 30)
        self.max_restart_count = self.config.get("max_restart_count", 5)
        self.enable_suspend = self.config.get("enable_suspend", True)

        # State tracking
        self._instances: Dict[str, AgentInstance] = {}
        self._restart_counts: Dict[str, int] = {}

        logger.info(
            f"LifecycleManager initialized with backend: "
            f"{backend.__class__.__name__}"
        )

    async def initialize(self) -> None:
        """Initialize lifecycle manager and backend"""
        await self.backend.initialize()
        logger.info("LifecycleManager initialization complete")

    async def spawn(
        self,
        config: AgentConfig,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> SpawnResult:
        """
        Spawn a new agent instance.

        Args:
            config: Agent configuration
            initial_context: Optional initial execution context

        Returns:
            SpawnResult with agent information

        Raises:
            LifecycleError: If spawn fails
        """
        logger.info(f"Spawning agent {config.agent_id}")

        try:
            # Generate sandbox configuration
            sandbox = self.sandbox_manager.get_sandbox_config(
                trust_level=config.trust_level,
                custom_limits=config.resource_limits
            )

            # Validate configuration
            self.sandbox_manager.validate_sandbox_config(sandbox)

            # Merge initial context into environment
            environment = config.environment.copy()
            if initial_context:
                environment["INITIAL_CONTEXT"] = str(initial_context)

            # Spawn container with timeout
            result = await asyncio.wait_for(
                self.backend.spawn_container(
                    config=config,
                    sandbox=sandbox,
                    image=self.config.get("agent_image", "agent-runtime:latest"),
                    environment=environment
                ),
                timeout=self.spawn_timeout
            )

            # Create agent instance record
            instance = AgentInstance.from_spawn_result(
                result=result,
                config=config,
                sandbox=sandbox
            )

            # Store instance
            self._instances[config.agent_id] = instance
            self._restart_counts[config.agent_id] = 0

            logger.info(
                f"Agent {config.agent_id} spawned successfully "
                f"with container {result.container_id}"
            )

            return result

        except asyncio.TimeoutError:
            raise LifecycleError(
                code="E2021",
                message=f"Spawn timeout exceeded ({self.spawn_timeout}s)"
            )
        except SandboxError as e:
            raise LifecycleError(
                code="E2020",
                message=f"Spawn failed due to sandbox error: {e.message}"
            )
        except Exception as e:
            logger.error(f"Spawn failed for agent {config.agent_id}: {e}")
            raise LifecycleError(
                code="E2020",
                message=f"Spawn failed: {str(e)}"
            )

    async def terminate(
        self,
        agent_id: str,
        reason: str,
        force: bool = False
    ) -> None:
        """
        Terminate an agent instance.

        Args:
            agent_id: Agent to terminate
            reason: Termination reason
            force: Force kill without graceful shutdown

        Raises:
            LifecycleError: If termination fails
        """
        logger.info(f"Terminating agent {agent_id} (reason: {reason}, force: {force})")

        # Get instance
        instance = self._instances.get(agent_id)
        if not instance:
            raise LifecycleError(
                code="E2022",
                message=f"Agent {agent_id} not found"
            )

        # Already terminated?
        if instance.state == AgentState.TERMINATED:
            logger.warning(f"Agent {agent_id} already terminated")
            return

        try:
            # Terminate container
            await self.backend.terminate_container(
                container_id=instance.container_id or agent_id,
                force=force,
                timeout_seconds=self.shutdown_timeout
            )

            # Update instance state
            instance.state = AgentState.TERMINATED
            instance.terminated_at = datetime.now(timezone.utc)
            instance.updated_at = datetime.now(timezone.utc)

            logger.info(f"Agent {agent_id} terminated successfully")

        except Exception as e:
            logger.error(f"Termination failed for agent {agent_id}: {e}")
            instance.state = AgentState.FAILED
            instance.updated_at = datetime.now(timezone.utc)
            raise LifecycleError(
                code="E2022",
                message=f"Terminate failed: {str(e)}"
            )

    async def suspend(
        self,
        agent_id: str,
        checkpoint: bool = True
    ) -> str:
        """
        Suspend agent and optionally checkpoint.

        Args:
            agent_id: Agent to suspend
            checkpoint: Whether to create checkpoint

        Returns:
            Checkpoint ID (if checkpoint=True)

        Raises:
            LifecycleError: If suspend fails
        """
        if not self.enable_suspend:
            raise LifecycleError(
                code="E2023",
                message="Suspend operations are disabled"
            )

        logger.info(f"Suspending agent {agent_id} (checkpoint: {checkpoint})")

        # Get instance
        instance = self._instances.get(agent_id)
        if not instance:
            raise LifecycleError(
                code="E2023",
                message=f"Agent {agent_id} not found"
            )

        # Must be running
        if instance.state != AgentState.RUNNING:
            raise LifecycleError(
                code="E2023",
                message=f"Agent {agent_id} not in RUNNING state (current: {instance.state.value})"
            )

        try:
            # Suspend container
            checkpoint_id = await self.backend.suspend_container(
                container_id=instance.container_id or agent_id
            )

            # Update instance state
            instance.state = AgentState.SUSPENDED
            instance.updated_at = datetime.now(timezone.utc)

            logger.info(f"Agent {agent_id} suspended successfully")

            return checkpoint_id

        except Exception as e:
            logger.error(f"Suspend failed for agent {agent_id}: {e}")
            raise LifecycleError(
                code="E2023",
                message=f"Suspend failed: {str(e)}"
            )

    async def resume(
        self,
        agent_id: str,
        checkpoint_id: Optional[str] = None
    ) -> AgentState:
        """
        Resume a suspended agent.

        Args:
            agent_id: Agent to resume
            checkpoint_id: Optional checkpoint to restore from

        Returns:
            Current agent state after resume

        Raises:
            LifecycleError: If resume fails
        """
        if not self.enable_suspend:
            raise LifecycleError(
                code="E2024",
                message="Resume operations are disabled"
            )

        logger.info(f"Resuming agent {agent_id}")

        # Get instance
        instance = self._instances.get(agent_id)
        if not instance:
            raise LifecycleError(
                code="E2024",
                message=f"Agent {agent_id} not found"
            )

        # Must be suspended
        if instance.state != AgentState.SUSPENDED:
            raise LifecycleError(
                code="E2024",
                message=f"Agent {agent_id} not in SUSPENDED state (current: {instance.state.value})"
            )

        try:
            # Resume container
            await self.backend.resume_container(
                container_id=instance.container_id or agent_id,
                checkpoint_id=checkpoint_id
            )

            # Update instance state
            instance.state = AgentState.RUNNING
            instance.updated_at = datetime.now(timezone.utc)

            logger.info(f"Agent {agent_id} resumed successfully")

            return instance.state

        except Exception as e:
            logger.error(f"Resume failed for agent {agent_id}: {e}")
            raise LifecycleError(
                code="E2024",
                message=f"Resume failed: {str(e)}"
            )

    async def get_state(self, agent_id: str) -> AgentState:
        """
        Get current agent state.

        Args:
            agent_id: Agent identifier

        Returns:
            Current agent state

        Raises:
            LifecycleError: If agent not found
        """
        instance = self._instances.get(agent_id)
        if not instance:
            raise LifecycleError(
                code="E2000",
                message=f"Agent {agent_id} not found"
            )
        return instance.state

    async def get_instance(self, agent_id: str) -> AgentInstance:
        """
        Get complete agent instance information.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent instance

        Raises:
            LifecycleError: If agent not found
        """
        instance = self._instances.get(agent_id)
        if not instance:
            raise LifecycleError(
                code="E2000",
                message=f"Agent {agent_id} not found"
            )

        # Update resource usage from backend
        try:
            if instance.container_id:
                usage = await self.backend.get_resource_usage(instance.container_id)
                instance.resource_usage = usage
                instance.updated_at = datetime.now(timezone.utc)
        except Exception as e:
            logger.warning(f"Failed to update resource usage: {e}")

        return instance

    async def list_instances(self) -> Dict[str, AgentInstance]:
        """
        List all tracked agent instances.

        Returns:
            Dict mapping agent_id to AgentInstance
        """
        return self._instances.copy()

    async def restart(
        self,
        agent_id: str,
        reason: str = "manual_restart"
    ) -> SpawnResult:
        """
        Restart an agent (terminate + spawn).

        Args:
            agent_id: Agent to restart
            reason: Restart reason

        Returns:
            SpawnResult for new instance

        Raises:
            LifecycleError: If restart fails or limit exceeded
        """
        logger.info(f"Restarting agent {agent_id}")

        # Check restart limit
        restart_count = self._restart_counts.get(agent_id, 0)
        if restart_count >= self.max_restart_count:
            raise LifecycleError(
                code="E2025",
                message=f"Max restart count ({self.max_restart_count}) exceeded"
            )

        # Get original config
        instance = self._instances.get(agent_id)
        if not instance:
            raise LifecycleError(
                code="E2000",
                message=f"Agent {agent_id} not found"
            )

        original_config = instance.config

        try:
            # Terminate existing instance
            await self.terminate(agent_id, reason=reason, force=True)

            # Spawn new instance with same config
            result = await self.spawn(original_config)

            # Increment restart count
            self._restart_counts[agent_id] = restart_count + 1

            logger.info(f"Agent {agent_id} restarted successfully")

            return result

        except Exception as e:
            logger.error(f"Restart failed for agent {agent_id}: {e}")
            raise LifecycleError(
                code="E2000",
                message=f"Restart failed: {str(e)}"
            )

    async def cleanup(self) -> None:
        """Cleanup and terminate all agents"""
        logger.info("Cleaning up lifecycle manager")

        # Terminate all running agents
        for agent_id in list(self._instances.keys()):
            try:
                await self.terminate(agent_id, reason="cleanup", force=True)
            except Exception as e:
                logger.error(f"Failed to terminate {agent_id} during cleanup: {e}")

        # Cleanup backend
        await self.backend.cleanup()

        self._instances.clear()
        self._restart_counts.clear()

        logger.info("Lifecycle manager cleanup complete")

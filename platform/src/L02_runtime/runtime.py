"""
Agent Runtime

Main entry point for the L02 Agent Runtime Layer.
Provides the AgentRuntime interface for agent lifecycle management.
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, AsyncIterator

from .models import AgentConfig, AgentState, SpawnResult
from .backends import LocalRuntime, KubernetesRuntime
from .services import SandboxManager, LifecycleManager


logger = logging.getLogger(__name__)


class AgentRuntime:
    """
    Primary interface for agent lifecycle management.

    Implements the AgentRuntime Protocol from specification Section 4.1.1.
    Orchestrates backend, sandbox manager, and lifecycle manager.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize AgentRuntime.

        Args:
            config_path: Path to configuration YAML file
                        (defaults to config/default_config.yaml)
        """
        # Load configuration
        if config_path:
            self.config = self._load_config(config_path)
        else:
            default_config_path = Path(__file__).parent / "config" / "default_config.yaml"
            self.config = self._load_config(str(default_config_path))

        # Initialize components (will be set in initialize())
        self.backend = None
        self.sandbox_manager = None
        self.lifecycle_manager = None

        logger.info("AgentRuntime created")

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            logger.info(f"Configuration loaded from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise RuntimeError(f"Configuration load failed: {e}")

    async def initialize(self) -> None:
        """
        Initialize the runtime and all components.

        Must be called before using any other methods.
        """
        logger.info("Initializing AgentRuntime")

        # Create backend based on configuration
        backend_type = self.config.get("runtime", {}).get("backend", "local")

        if backend_type == "local":
            self.backend = LocalRuntime(
                config=self.config.get("local_runtime", {})
            )
        elif backend_type == "kubernetes":
            self.backend = KubernetesRuntime(
                config=self.config.get("kubernetes_runtime", {})
            )
        else:
            raise ValueError(f"Unknown backend type: {backend_type}")

        # Create sandbox manager
        self.sandbox_manager = SandboxManager(
            config=self.config.get("sandbox", {})
        )

        # Create lifecycle manager
        self.lifecycle_manager = LifecycleManager(
            backend=self.backend,
            sandbox_manager=self.sandbox_manager,
            config=self.config.get("lifecycle", {})
        )

        # Initialize all components
        await self.backend.initialize()
        await self.sandbox_manager.initialize()
        await self.lifecycle_manager.initialize()

        logger.info(f"AgentRuntime initialized with {backend_type} backend")

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
            RuntimeError: If not initialized or spawn fails
        """
        if not self.lifecycle_manager:
            raise RuntimeError("AgentRuntime not initialized")

        return await self.lifecycle_manager.spawn(config, initial_context)

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
            RuntimeError: If not initialized or terminate fails
        """
        if not self.lifecycle_manager:
            raise RuntimeError("AgentRuntime not initialized")

        await self.lifecycle_manager.terminate(agent_id, reason, force)

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
            RuntimeError: If not initialized or suspend fails
        """
        if not self.lifecycle_manager:
            raise RuntimeError("AgentRuntime not initialized")

        return await self.lifecycle_manager.suspend(agent_id, checkpoint)

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
            RuntimeError: If not initialized or resume fails
        """
        if not self.lifecycle_manager:
            raise RuntimeError("AgentRuntime not initialized")

        return await self.lifecycle_manager.resume(agent_id, checkpoint_id)

    async def get_state(self, agent_id: str) -> AgentState:
        """
        Get current agent state.

        Args:
            agent_id: Agent identifier

        Returns:
            Current agent state

        Raises:
            RuntimeError: If not initialized or agent not found
        """
        if not self.lifecycle_manager:
            raise RuntimeError("AgentRuntime not initialized")

        return await self.lifecycle_manager.get_state(agent_id)

    async def execute(
        self,
        agent_id: str,
        input_message: str
    ) -> AsyncIterator[str]:
        """
        Execute agent with input, streaming response.

        NOTE: This is a placeholder for Phase 2 (Agent Executor).
        Currently not implemented.

        Args:
            agent_id: Agent to execute
            input_message: Input message

        Yields:
            Response chunks

        Raises:
            NotImplementedError: Phase 2 not yet implemented
        """
        raise NotImplementedError(
            "Agent execution is part of Phase 2 (Agent Executor). "
            "Use spawn/terminate/suspend/resume for Phase 1 operations."
        )

    async def cleanup(self) -> None:
        """Cleanup and shutdown runtime"""
        logger.info("Cleaning up AgentRuntime")

        if self.lifecycle_manager:
            await self.lifecycle_manager.cleanup()

        logger.info("AgentRuntime cleanup complete")

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        return self.config.copy()

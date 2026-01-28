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
from .services import (
    SandboxManager,
    LifecycleManager,
    L01Bridge,
    ModelGatewayBridge,
    AgentExecutor,
    ResourceManager,
)


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
        self.l01_bridge = None
        self.model_bridge = None
        self.agent_executor = None
        self.resource_manager = None

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

        # Create L01 bridge if enabled
        l01_config = self.config.get("l01_bridge", {})
        if l01_config.get("enabled", True):  # Enabled by default
            l01_base_url = l01_config.get("base_url", "http://localhost:8002")
            self.l01_bridge = L01Bridge(l01_base_url=l01_base_url)
            logger.info(f"L01 bridge created with base_url={l01_base_url}")
        else:
            self.l01_bridge = None
            logger.info("L01 bridge disabled")

        # Create lifecycle manager
        self.lifecycle_manager = LifecycleManager(
            backend=self.backend,
            sandbox_manager=self.sandbox_manager,
            config=self.config.get("lifecycle", {}),
            l01_bridge=self.l01_bridge
        )

        # Create model gateway bridge for LLM inference
        l04_config = self.config.get("l04_gateway", {})
        l04_base_url = l04_config.get("base_url", "http://localhost:8004")
        l04_timeout = l04_config.get("timeout", 300)
        self.model_bridge = ModelGatewayBridge(
            base_url=l04_base_url,
            timeout=l04_timeout
        )
        logger.info(f"ModelGatewayBridge created with base_url={l04_base_url}")

        # Create agent executor with model bridge
        executor_config = self.config.get("executor", {})
        self.agent_executor = AgentExecutor(
            config=executor_config,
            model_bridge=self.model_bridge
        )

        # Create resource manager with lifecycle manager for enforcement
        resource_config = self.config.get("resources", {})
        self.resource_manager = ResourceManager(
            config=resource_config,
            lifecycle_manager=self.lifecycle_manager
        )

        # Initialize all components
        await self.backend.initialize()
        await self.sandbox_manager.initialize()
        await self.lifecycle_manager.initialize()
        await self.agent_executor.initialize()
        await self.resource_manager.initialize()

        logger.info(
            f"AgentRuntime initialized with {backend_type} backend, "
            f"model_bridge={l04_base_url}"
        )

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
        input_message: str,
        stream: bool = False,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Execute agent with input, optionally streaming response.

        Args:
            agent_id: Agent to execute
            input_message: Input message
            stream: Whether to stream response (default: False)
            **kwargs: Additional parameters (system_prompt, temperature, etc.)

        Yields:
            Response chunks (if streaming) or full response dict

        Raises:
            RuntimeError: If not initialized or execution fails
        """
        if not self.agent_executor:
            raise RuntimeError("AgentRuntime not initialized")

        # Build input data
        input_data = {
            "content": input_message,
            **kwargs
        }

        # Execute via agent executor
        result = await self.agent_executor.execute(
            agent_id=agent_id,
            input_data=input_data,
            stream=stream
        )

        if stream:
            # Yield streaming chunks
            async for chunk in result:
                if chunk.get("type") == "content":
                    yield chunk.get("delta", "")
                elif chunk.get("type") == "end":
                    break
                elif chunk.get("type") == "error":
                    raise RuntimeError(chunk.get("message", "Execution error"))
        else:
            # Yield full response content
            yield result.get("response", "")

    async def cleanup(self) -> None:
        """Cleanup and shutdown runtime"""
        logger.info("Cleaning up AgentRuntime")

        if self.agent_executor:
            await self.agent_executor.cleanup()

        if self.resource_manager:
            await self.resource_manager.cleanup()

        if self.model_bridge:
            await self.model_bridge.close()

        if self.lifecycle_manager:
            await self.lifecycle_manager.cleanup()

        logger.info("AgentRuntime cleanup complete")

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        return self.config.copy()

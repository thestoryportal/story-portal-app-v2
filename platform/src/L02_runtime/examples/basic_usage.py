"""
Basic Usage Example for L02 Agent Runtime

Demonstrates spawning, managing, and terminating agents using the LocalRuntime backend.

Requirements:
- Docker daemon running
- alpine:latest image available
"""

import asyncio
import logging
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from L02_runtime import (
    AgentRuntime,
    AgentConfig,
    TrustLevel,
    ResourceLimits,
    AgentState,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def example_spawn_and_terminate():
    """Example: Spawn and terminate an agent"""
    logger.info("=== Example 1: Spawn and Terminate ===")

    # Create runtime
    runtime = AgentRuntime()
    await runtime.initialize()

    try:
        # Configure agent
        config = AgentConfig(
            agent_id="example-agent-1",
            trust_level=TrustLevel.STANDARD,
            environment={
                "ENV": "development",
                "LOG_LEVEL": "INFO"
            }
        )

        # Spawn agent
        logger.info(f"Spawning agent: {config.agent_id}")
        result = await runtime.spawn(config)

        logger.info(f"Agent spawned successfully!")
        logger.info(f"  - Agent ID: {result.agent_id}")
        logger.info(f"  - Session ID: {result.session_id}")
        logger.info(f"  - State: {result.state.value}")
        logger.info(f"  - Sandbox: {result.sandbox_type}")
        logger.info(f"  - Container ID: {result.container_id}")

        # Get agent state
        state = await runtime.get_state(config.agent_id)
        logger.info(f"Current state: {state.value}")

        # Wait a bit
        await asyncio.sleep(2)

        # Terminate agent
        logger.info(f"Terminating agent: {config.agent_id}")
        await runtime.terminate(config.agent_id, reason="example_complete")

        logger.info("Agent terminated successfully!")

    finally:
        await runtime.cleanup()


async def example_suspend_and_resume():
    """Example: Suspend and resume an agent"""
    logger.info("\n=== Example 2: Suspend and Resume ===")

    runtime = AgentRuntime()
    await runtime.initialize()

    try:
        config = AgentConfig(
            agent_id="example-agent-2",
            trust_level=TrustLevel.TRUSTED
        )

        # Spawn
        logger.info(f"Spawning agent: {config.agent_id}")
        result = await runtime.spawn(config)
        logger.info(f"Agent spawned: {result.state.value}")

        # Suspend
        logger.info(f"Suspending agent: {config.agent_id}")
        checkpoint_id = await runtime.suspend(config.agent_id)
        logger.info(f"Agent suspended (checkpoint: {checkpoint_id})")

        state = await runtime.get_state(config.agent_id)
        logger.info(f"Current state: {state.value}")

        # Resume
        logger.info(f"Resuming agent: {config.agent_id}")
        state = await runtime.resume(config.agent_id, checkpoint_id)
        logger.info(f"Agent resumed: {state.value}")

        # Cleanup
        await runtime.terminate(config.agent_id, reason="example_complete")

    finally:
        await runtime.cleanup()


async def example_custom_resources():
    """Example: Agent with custom resource limits"""
    logger.info("\n=== Example 3: Custom Resource Limits ===")

    runtime = AgentRuntime()
    await runtime.initialize()

    try:
        # Custom resource limits
        custom_limits = ResourceLimits(
            cpu="1",              # 1 CPU core
            memory="512Mi",       # 512 MB RAM
            tokens_per_hour=50000 # 50K tokens/hour
        )

        config = AgentConfig(
            agent_id="example-agent-3",
            trust_level=TrustLevel.UNTRUSTED,
            resource_limits=custom_limits
        )

        logger.info(f"Spawning agent with custom limits:")
        logger.info(f"  - CPU: {custom_limits.cpu}")
        logger.info(f"  - Memory: {custom_limits.memory}")
        logger.info(f"  - Tokens/hour: {custom_limits.tokens_per_hour}")

        result = await runtime.spawn(config)
        logger.info(f"Agent spawned: {result.agent_id}")

        # Get instance details
        instance = await runtime.lifecycle_manager.get_instance(config.agent_id)
        logger.info(f"Sandbox configuration:")
        logger.info(f"  - Runtime class: {instance.sandbox.runtime_class.value}")
        logger.info(f"  - Network policy: {instance.sandbox.network_policy.value}")
        logger.info(f"  - Trust level: {instance.sandbox.trust_level.value}")

        # Cleanup
        await runtime.terminate(config.agent_id, reason="example_complete")

    finally:
        await runtime.cleanup()


async def example_multiple_agents():
    """Example: Manage multiple agents concurrently"""
    logger.info("\n=== Example 4: Multiple Agents ===")

    runtime = AgentRuntime()
    await runtime.initialize()

    try:
        # Spawn multiple agents
        agent_ids = []
        for i in range(3):
            config = AgentConfig(
                agent_id=f"example-agent-multi-{i}",
                trust_level=TrustLevel.STANDARD
            )

            logger.info(f"Spawning agent {i+1}/3: {config.agent_id}")
            result = await runtime.spawn(config)
            agent_ids.append(result.agent_id)

        # List all instances
        instances = await runtime.lifecycle_manager.list_instances()
        logger.info(f"\nTotal active agents: {len(instances)}")

        for agent_id, instance in instances.items():
            logger.info(f"  - {agent_id}: {instance.state.value}")

        # Terminate all
        logger.info("\nTerminating all agents...")
        for agent_id in agent_ids:
            await runtime.terminate(agent_id, reason="example_complete")

        logger.info("All agents terminated")

    finally:
        await runtime.cleanup()


async def main():
    """Run all examples"""
    try:
        # Check if Docker is available
        from L02_runtime.backends import LocalRuntime

        backend = LocalRuntime()
        await backend.initialize()

        if not await backend.health_check():
            logger.error("Docker daemon not available!")
            logger.error("Please start Docker Desktop and try again.")
            await backend.cleanup()
            return

        await backend.cleanup()

        # Run examples
        await example_spawn_and_terminate()
        await example_suspend_and_resume()
        await example_custom_resources()
        await example_multiple_agents()

        logger.info("\n✓ All examples completed successfully!")

    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())

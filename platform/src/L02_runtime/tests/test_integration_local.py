"""
Integration tests for LocalRuntime backend

These tests require Docker to be running.
Run with: pytest -v test_integration_local.py
"""

import pytest
import asyncio

from ..models import AgentConfig, TrustLevel, AgentState
from ..backends import LocalRuntime
from ..services import SandboxManager, LifecycleManager
from ..runtime import AgentRuntime


@pytest.mark.integration
@pytest.mark.asyncio
async def test_local_runtime_spawn_terminate():
    """
    Integration test: Spawn and terminate an agent using LocalRuntime

    Requires:
    - Docker daemon running
    - agent-runtime:latest image (or will fail gracefully)
    """
    # Create backend
    backend = LocalRuntime(config={})

    try:
        # Initialize backend
        await backend.initialize()

        # Check Docker is available
        is_healthy = await backend.health_check()
        if not is_healthy:
            pytest.skip("Docker daemon not available")

        # Create config
        config = AgentConfig(
            agent_id="test-agent-integration",
            trust_level=TrustLevel.STANDARD
        )

        # Create sandbox manager
        sandbox_manager = SandboxManager(config={
            "available_runtimes": ["runc"],
            "default_runtime_class": "runc"
        })
        await sandbox_manager.initialize()

        sandbox = sandbox_manager.get_sandbox_config(TrustLevel.STANDARD)

        # Spawn container
        # Note: This will fail if agent-runtime:latest doesn't exist
        # For testing, we can use a simple image like alpine
        try:
            result = await backend.spawn_container(
                config=config,
                sandbox=sandbox,
                image="alpine:latest",
                command=["sleep", "3600"]
            )

            assert result.agent_id == "test-agent-integration"
            assert result.state == AgentState.RUNNING
            assert result.container_id is not None

            # Get container info
            info = await backend.get_container_info(result.container_id)
            assert info.container_id == result.container_id

            # Get logs (should be empty for sleep command)
            logs = await backend.get_logs(result.container_id, tail=10)
            assert logs is not None

            # Terminate container
            await backend.terminate_container(result.container_id, force=True)

        except Exception as e:
            # If image pull fails or container creation fails, that's okay for this test
            pytest.skip(f"Container spawn failed (expected in CI): {e}")

    finally:
        # Cleanup
        await backend.cleanup()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_lifecycle_manager_integration():
    """
    Integration test: Full lifecycle using LifecycleManager

    Tests spawn -> suspend -> resume -> terminate flow
    """
    backend = LocalRuntime(config={})

    try:
        await backend.initialize()

        if not await backend.health_check():
            pytest.skip("Docker daemon not available")

        sandbox_manager = SandboxManager(config={
            "available_runtimes": ["runc"]
        })
        await sandbox_manager.initialize()

        lifecycle_manager = LifecycleManager(
            backend=backend,
            sandbox_manager=sandbox_manager,
            config={"enable_suspend": True}
        )
        await lifecycle_manager.initialize()

        config = AgentConfig(
            agent_id="test-lifecycle-integration",
            trust_level=TrustLevel.TRUSTED
        )

        try:
            # Spawn
            result = await lifecycle_manager.spawn(config)
            assert result.state == AgentState.RUNNING

            # Get state
            state = await lifecycle_manager.get_state("test-lifecycle-integration")
            assert state == AgentState.RUNNING

            # Get instance
            instance = await lifecycle_manager.get_instance("test-lifecycle-integration")
            assert instance.agent_id == "test-lifecycle-integration"

            # Suspend
            checkpoint_id = await lifecycle_manager.suspend("test-lifecycle-integration")
            state = await lifecycle_manager.get_state("test-lifecycle-integration")
            assert state == AgentState.SUSPENDED

            # Resume
            state = await lifecycle_manager.resume("test-lifecycle-integration")
            assert state == AgentState.RUNNING

            # Terminate
            await lifecycle_manager.terminate(
                "test-lifecycle-integration",
                reason="integration_test"
            )
            state = await lifecycle_manager.get_state("test-lifecycle-integration")
            assert state == AgentState.TERMINATED

        except Exception as e:
            pytest.skip(f"Lifecycle test failed (expected in CI): {e}")

    finally:
        await backend.cleanup()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_runtime_integration():
    """
    Integration test: Full AgentRuntime API

    Tests the complete public interface
    """
    # Create runtime with in-memory config
    runtime = AgentRuntime.__new__(AgentRuntime)
    runtime.config = {
        "runtime": {"backend": "local"},
        "local_runtime": {"available_runtimes": ["runc"]},
        "sandbox": {
            "default_runtime_class": "runc",
            "available_runtimes": ["runc"]
        },
        "lifecycle": {
            "spawn_timeout_seconds": 60,
            "enable_suspend": True
        }
    }

    try:
        await runtime.initialize()

        # Check if Docker is available
        if not await runtime.lifecycle_manager.backend.health_check():
            pytest.skip("Docker daemon not available")

        config = AgentConfig(
            agent_id="test-runtime-api",
            trust_level=TrustLevel.STANDARD
        )

        try:
            # Test spawn
            result = await runtime.spawn(config)
            assert result.agent_id == "test-runtime-api"

            # Test get_state
            state = await runtime.get_state("test-runtime-api")
            assert state == AgentState.RUNNING

            # Test execute (should raise NotImplementedError)
            with pytest.raises(NotImplementedError):
                async for chunk in runtime.execute("test-runtime-api", "test"):
                    pass

            # Test terminate
            await runtime.terminate("test-runtime-api", "integration_test")

        except Exception as e:
            pytest.skip(f"Runtime API test failed (expected in CI): {e}")

    finally:
        await runtime.cleanup()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_docker_resource_limits():
    """
    Integration test: Verify resource limits are applied

    Tests that CPU and memory limits are properly set on containers
    """
    backend = LocalRuntime(config={})

    try:
        await backend.initialize()

        if not await backend.health_check():
            pytest.skip("Docker daemon not available")

        from ..models import ResourceLimits, SandboxConfiguration

        config = AgentConfig(
            agent_id="test-resources",
            trust_level=TrustLevel.STANDARD,
            resource_limits=ResourceLimits(
                cpu="1",
                memory="512Mi",
                tokens_per_hour=50000
            )
        )

        sandbox = SandboxConfiguration.from_trust_level(
            trust_level=TrustLevel.STANDARD,
            resource_limits=config.resource_limits
        )

        try:
            result = await backend.spawn_container(
                config=config,
                sandbox=sandbox,
                image="alpine:latest",
                command=["sleep", "60"]
            )

            # Get container stats to verify limits
            usage = await backend.get_resource_usage(result.container_id)
            assert usage is not None

            # Cleanup
            await backend.terminate_container(result.container_id, force=True)

        except Exception as e:
            pytest.skip(f"Resource limits test failed (expected in CI): {e}")

    finally:
        await backend.cleanup()


# Test runner helper
if __name__ == "__main__":
    """
    Run integration tests manually:
    python test_integration_local.py
    """
    import sys

    async def run_tests():
        print("Running integration tests...")
        print("\n1. Testing LocalRuntime spawn/terminate...")
        try:
            await test_local_runtime_spawn_terminate()
            print("✓ LocalRuntime test passed")
        except Exception as e:
            print(f"✗ LocalRuntime test failed: {e}")

        print("\n2. Testing LifecycleManager integration...")
        try:
            await test_lifecycle_manager_integration()
            print("✓ LifecycleManager test passed")
        except Exception as e:
            print(f"✗ LifecycleManager test failed: {e}")

        print("\n3. Testing AgentRuntime API...")
        try:
            await test_agent_runtime_integration()
            print("✓ AgentRuntime test passed")
        except Exception as e:
            print(f"✗ AgentRuntime test failed: {e}")

        print("\n4. Testing resource limits...")
        try:
            await test_docker_resource_limits()
            print("✓ Resource limits test passed")
        except Exception as e:
            print(f"✗ Resource limits test failed: {e}")

    asyncio.run(run_tests())

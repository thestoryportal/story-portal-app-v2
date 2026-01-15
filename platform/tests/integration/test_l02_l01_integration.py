"""
Integration test for L02 Runtime -> L01 Data Layer

Tests that L02 agent lifecycle events are properly published to L01.
"""

import asyncio
import pytest
from uuid import UUID

# L02 imports
from src.L02_runtime.runtime import AgentRuntime
from src.L02_runtime.models import (
    AgentConfig,
    TrustLevel,
    ResourceLimits,
)

# L01 imports
from src.L01_data_layer.client import L01Client


@pytest.mark.asyncio
async def test_l02_agent_spawn_creates_l01_session():
    """
    Test that spawning an agent in L02 creates a session in L01.

    Flow:
    1. Initialize L02 AgentRuntime with L01Bridge
    2. Spawn an agent
    3. Verify session created in L01
    4. Verify session has correct metadata
    """
    # Initialize L01 client
    l01_client = L01Client(base_url="http://localhost:8002")

    # Initialize L02 runtime with L01 bridge enabled
    runtime_config = {
        "runtime": {"backend": "local"},
        "local_runtime": {},
        "sandbox": {},
        "lifecycle": {},
        "l01_bridge": {
            "enabled": True,
            "base_url": "http://localhost:8002"
        }
    }

    runtime = AgentRuntime()
    runtime.config = runtime_config

    try:
        await runtime.initialize()

        # Create agent config
        agent_id = "test-l02-l01-agent"
        agent_config = AgentConfig(
            agent_id=agent_id,
            trust_level=TrustLevel.TRUSTED,
            resource_limits=ResourceLimits(
                cpu="1",
                memory="512Mi",
                tokens_per_hour=10000
            ),
            environment={"TEST": "true"}
        )

        # Spawn agent (this should create L01 session)
        spawn_result = await runtime.spawn(agent_config)

        assert spawn_result.agent_id == agent_id
        assert spawn_result.state.value == "running"

        # Wait a moment for L01 event to be published
        await asyncio.sleep(1)

        # Query L01 for sessions
        sessions = await l01_client.list_sessions(limit=100)

        # Find session for our agent
        agent_sessions = [
            s for s in sessions
            if s.get("runtime_metadata", {}).get("l02_session_id") == spawn_result.session_id
        ]

        assert len(agent_sessions) > 0, f"No L01 session found for L02 session {spawn_result.session_id}"

        session = agent_sessions[0]

        # Verify session metadata
        assert session["session_type"] == "runtime"
        assert session["status"] == "active"
        assert session["runtime_backend"] in ["local", "kubernetes"]

        runtime_metadata = session.get("runtime_metadata", {})
        assert runtime_metadata.get("l02_session_id") == spawn_result.session_id
        assert runtime_metadata.get("l02_agent_state") == "running"
        assert runtime_metadata.get("container_id") is not None

        print(f"✅ L02 agent {agent_id} created L01 session {session['id']}")
        print(f"   L02 session: {spawn_result.session_id}")
        print(f"   L01 session: {session['id']}")
        print(f"   Container: {runtime_metadata.get('container_id')}")

        # Terminate agent
        await runtime.terminate(agent_id, reason="test_complete")

        # Wait for termination event
        await asyncio.sleep(1)

        # Verify session updated to completed
        updated_session = await l01_client.get_session(UUID(session["id"]))
        assert updated_session["status"] in ["completed", "crashed"]

        print(f"✅ L01 session updated to {updated_session['status']} after termination")

    finally:
        # Cleanup
        await l01_client.close()


@pytest.mark.asyncio
async def test_l02_agent_lifecycle_events():
    """
    Test that L02 agent state transitions are reflected in L01.

    Flow:
    1. Spawn agent (creates L01 session with status=active)
    2. Suspend agent (updates L01 session to status=paused)
    3. Resume agent (updates L01 session to status=active)
    4. Terminate agent (updates L01 session to status=completed)
    """
    l01_client = L01Client(base_url="http://localhost:8002")

    runtime_config = {
        "runtime": {"backend": "local"},
        "local_runtime": {},
        "sandbox": {},
        "lifecycle": {"enable_suspend": True},
        "l01_bridge": {
            "enabled": True,
            "base_url": "http://localhost:8002"
        }
    }

    runtime = AgentRuntime()
    runtime.config = runtime_config

    try:
        await runtime.initialize()

        agent_id = "test-lifecycle-agent"
        agent_config = AgentConfig(
            agent_id=agent_id,
            trust_level=TrustLevel.TRUSTED,
            resource_limits=ResourceLimits(cpu="1", memory="512Mi")
        )

        # 1. Spawn
        spawn_result = await runtime.spawn(agent_config)
        await asyncio.sleep(1)

        sessions = await l01_client.list_sessions(limit=100)
        session = next(
            (s for s in sessions
             if s.get("runtime_metadata", {}).get("l02_session_id") == spawn_result.session_id),
            None
        )

        assert session is not None
        assert session["status"] == "active"
        print(f"✅ 1. Spawned: L01 session status = {session['status']}")

        # 2. Suspend
        await runtime.suspend(agent_id, checkpoint=False)
        await asyncio.sleep(1)

        updated_session = await l01_client.get_session(UUID(session["id"]))
        assert updated_session["status"] == "paused"
        assert updated_session["runtime_metadata"]["l02_agent_state"] == "suspended"
        print(f"✅ 2. Suspended: L01 session status = {updated_session['status']}")

        # 3. Resume
        await runtime.resume(agent_id)
        await asyncio.sleep(1)

        updated_session = await l01_client.get_session(UUID(session["id"]))
        assert updated_session["status"] == "active"
        assert updated_session["runtime_metadata"]["l02_agent_state"] == "running"
        print(f"✅ 3. Resumed: L01 session status = {updated_session['status']}")

        # 4. Terminate
        await runtime.terminate(agent_id, reason="test_complete")
        await asyncio.sleep(1)

        updated_session = await l01_client.get_session(UUID(session["id"]))
        assert updated_session["status"] in ["completed", "crashed"]
        print(f"✅ 4. Terminated: L01 session status = {updated_session['status']}")

    finally:
        await l01_client.close()


if __name__ == "__main__":
    # Run tests
    print("=" * 70)
    print("L02 -> L01 Integration Test")
    print("=" * 70)

    print("\nTest 1: Agent spawn creates L01 session")
    asyncio.run(test_l02_agent_spawn_creates_l01_session())

    print("\n" + "=" * 70)
    print("\nTest 2: Agent lifecycle events update L01")
    asyncio.run(test_l02_agent_lifecycle_events())

    print("\n" + "=" * 70)
    print("✅ All tests passed!")
    print("=" * 70)

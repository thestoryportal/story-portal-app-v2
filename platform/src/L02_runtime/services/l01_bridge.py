"""
L01 Data Layer Bridge for L02 Runtime

Publishes agent lifecycle events to L01 Data Layer for centralized tracking.
"""

import logging
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timezone

from shared.clients import L01Client
from ..models import AgentState, SpawnResult, AgentInstance

logger = logging.getLogger(__name__)


class L01Bridge:
    """
    Bridge between L02 Runtime and L01 Data Layer.

    Responsibilities:
    - Create session records in L01 when agents spawn
    - Update session status when agents change state
    - Publish lifecycle events to L01 EventStore via Redis
    - Link L02 runtime metadata with L01 sessions
    """

    def __init__(self, l01_base_url: str = "http://localhost:8002"):
        """
        Initialize L01 Bridge.

        Args:
            l01_base_url: Base URL for L01 Data Layer API
        """
        self.l01_client = L01Client(base_url=l01_base_url)
        self.enabled = True  # Can be disabled for testing

        logger.info(f"L01Bridge initialized with base_url={l01_base_url}")

    async def initialize(self) -> None:
        """Initialize bridge connection."""
        try:
            # Test L01 connection
            # L01Client doesn't require explicit initialization
            logger.info("L01Bridge initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize L01Bridge: {e}, continuing in degraded mode")
            self.enabled = False

    async def on_agent_spawned(
        self,
        spawn_result: SpawnResult,
        agent_instance: AgentInstance
    ) -> Optional[UUID]:
        """
        Called when an agent is spawned.

        Creates session record in L01 and publishes spawn event.

        Args:
            spawn_result: Result from spawn operation
            agent_instance: Complete agent instance data

        Returns:
            L01 session ID or None if failed
        """
        if not self.enabled:
            return None

        try:
            # Prepare runtime metadata
            runtime_metadata = {
                "l02_session_id": spawn_result.session_id,
                "l02_agent_state": spawn_result.state.value,
                "sandbox_type": spawn_result.sandbox_type,
                "container_id": spawn_result.container_id,
                "pod_name": spawn_result.pod_name,
                "backend_metadata": agent_instance.backend_metadata,
                "trust_level": agent_instance.sandbox.trust_level.value,
                "runtime_class": agent_instance.sandbox.runtime_class.value,
                "spawned_at": spawn_result.created_at.isoformat(),
            }

            # Create session in L01
            session = await self.l01_client.create_session(
                agent_id=UUID(spawn_result.agent_id),
                session_type="runtime",
                context={
                    "agent_config": agent_instance.config.to_dict(),
                    "sandbox_config": agent_instance.sandbox.to_dict(),
                },
                runtime_backend="local" if spawn_result.container_id else "kubernetes",
                runtime_metadata=runtime_metadata,
            )

            l01_session_id = UUID(session["id"])

            logger.info(
                f"Created L01 session {l01_session_id} for agent {spawn_result.agent_id}, "
                f"L02 session {spawn_result.session_id}"
            )

            # Events are automatically published by L01's SessionService
            return l01_session_id

        except Exception as e:
            logger.error(f"Failed to create L01 session for agent {spawn_result.agent_id}: {e}")
            return None

    async def on_agent_state_changed(
        self,
        l01_session_id: UUID,
        agent_id: str,
        old_state: AgentState,
        new_state: AgentState,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Called when agent state changes.

        Updates session status in L01 and publishes state change event.

        Args:
            l01_session_id: L01 session ID
            agent_id: Agent identifier
            old_state: Previous agent state
            new_state: New agent state
            metadata: Optional state change metadata
        """
        if not self.enabled:
            return

        try:
            # Map L02 AgentState to L01 SessionStatus
            status_map = {
                AgentState.PENDING: "active",
                AgentState.RUNNING: "active",
                AgentState.SUSPENDED: "paused",
                AgentState.TERMINATED: "completed",
                AgentState.FAILED: "crashed",
            }

            l01_status = status_map.get(new_state, "active")

            # Update session in L01
            await self.l01_client.update_session(
                session_id=l01_session_id,
                status=l01_status,
                runtime_metadata={
                    "l02_agent_state": new_state.value,
                    "state_changed_at": datetime.now(timezone.utc).isoformat(),
                    "previous_state": old_state.value,
                    **(metadata or {}),
                },
            )

            logger.info(
                f"Updated L01 session {l01_session_id} for agent {agent_id}: "
                f"{old_state.value} -> {new_state.value}"
            )

            # Events are automatically published by L01's SessionService

        except Exception as e:
            logger.error(
                f"Failed to update L01 session {l01_session_id} for agent {agent_id}: {e}"
            )

    async def on_agent_checkpoint_created(
        self,
        l01_session_id: UUID,
        agent_id: str,
        checkpoint_id: str,
        checkpoint_size_bytes: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Called when a checkpoint is created.

        Updates session with checkpoint reference.

        Args:
            l01_session_id: L01 session ID
            agent_id: Agent identifier
            checkpoint_id: L02 checkpoint ID
            checkpoint_size_bytes: Size of checkpoint
            metadata: Optional checkpoint metadata
        """
        if not self.enabled:
            return

        try:
            # Update session with checkpoint reference
            await self.l01_client.update_session(
                session_id=l01_session_id,
                checkpoint={
                    "l02_checkpoint_id": checkpoint_id,
                    "size_bytes": checkpoint_size_bytes,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    **(metadata or {}),
                },
            )

            logger.info(
                f"Updated L01 session {l01_session_id} with checkpoint {checkpoint_id} "
                f"for agent {agent_id}"
            )

        except Exception as e:
            logger.error(
                f"Failed to update L01 session {l01_session_id} with checkpoint: {e}"
            )

    async def on_agent_terminated(
        self,
        l01_session_id: UUID,
        agent_id: str,
        termination_reason: str,
        resource_usage: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Called when agent is terminated.

        Finalizes session in L01 with termination details.

        Args:
            l01_session_id: L01 session ID
            agent_id: Agent identifier
            termination_reason: Reason for termination
            resource_usage: Final resource usage statistics
        """
        if not self.enabled:
            return

        try:
            # Update session to completed/crashed
            status = "completed" if termination_reason == "normal" else "crashed"

            await self.l01_client.update_session(
                session_id=l01_session_id,
                status=status,
                runtime_metadata={
                    "l02_agent_state": "terminated",
                    "termination_reason": termination_reason,
                    "terminated_at": datetime.now(timezone.utc).isoformat(),
                    "resource_usage": resource_usage or {},
                },
            )

            logger.info(
                f"Finalized L01 session {l01_session_id} for agent {agent_id}: "
                f"status={status}, reason={termination_reason}"
            )

        except Exception as e:
            logger.error(
                f"Failed to finalize L01 session {l01_session_id} for agent {agent_id}: {e}"
            )

    async def get_session_by_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get L01 session for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Session data or None if not found
        """
        if not self.enabled:
            return None

        try:
            sessions = await self.l01_client.list_sessions(
                agent_id=UUID(agent_id),
                limit=1
            )

            return sessions[0] if sessions else None

        except Exception as e:
            logger.error(f"Failed to get L01 session for agent {agent_id}: {e}")
            return None

    async def cleanup(self) -> None:
        """Cleanup bridge and close connections."""
        if self.l01_client:
            await self.l01_client.close()

        logger.info("L01Bridge cleanup complete")

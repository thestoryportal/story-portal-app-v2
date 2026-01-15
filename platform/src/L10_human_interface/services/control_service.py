"""
L10 Human Interface Layer - Control Service

Handles agent control operations with distributed locking and idempotency.
"""

import json
import logging
import uuid
from datetime import datetime, UTC
from typing import Optional
import redis.asyncio as redis

from ..models import (
    ControlOperation,
    ControlStatus,
    ControlResponse,
    AgentState,
    ErrorCode,
    InterfaceError,
)
from ..config import get_settings

logger = logging.getLogger(__name__)


class ControlService:
    """
    Control service for agent operations.

    Features:
    - State validation before transitions
    - Distributed locking via Redis (SET NX EX)
    - Idempotency via Redis (24h TTL)
    - Audit logging for all operations
    """

    def __init__(
        self,
        state_manager=None,
        event_bus=None,
        audit_logger=None,
        redis_client: Optional[redis.Redis] = None,
    ):
        self.state_manager = state_manager
        self.event_bus = event_bus
        self.audit_logger = audit_logger
        self.redis = redis_client
        self.settings = get_settings()

    async def pause_agent(
        self,
        agent_id: str,
        tenant_id: str,
        user_id: str,
        reason: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> ControlResponse:
        """
        Pause agent execution.

        Args:
            agent_id: Agent ID
            tenant_id: Tenant ID
            user_id: User performing the action
            reason: Optional reason for pausing
            idempotency_key: Optional idempotency key

        Returns:
            ControlResponse
        """
        if not idempotency_key:
            idempotency_key = str(uuid.uuid4())

        # Check idempotency
        idem_result = await self._check_idempotency(idempotency_key, agent_id, "pause")
        if idem_result:
            logger.info(f"Idempotent pause request: {idempotency_key}")
            return ControlResponse(**idem_result)

        # Acquire distributed lock
        lock_acquired = await self._acquire_lock(agent_id)
        if not lock_acquired:
            raise InterfaceError.from_code(
                ErrorCode.E10305,
                details={"agent_id": agent_id},
                recovery_suggestion="Another operation is in progress, retry in a few seconds",
            )

        try:
            # Get current agent state
            if not self.state_manager:
                raise InterfaceError.from_code(
                    ErrorCode.E10303,
                    details={"agent_id": agent_id, "reason": "StateManager not available"},
                )

            agent_state = await self._get_agent_state(agent_id)
            if not agent_state:
                raise InterfaceError.from_code(
                    ErrorCode.E10302,
                    details={"agent_id": agent_id},
                )

            # Check if already paused (idempotent)
            if agent_state == AgentState.PAUSED:
                response = ControlResponse(
                    operation=ControlOperation.PAUSE,
                    status=ControlStatus.IDEMPOTENT,
                    agent_id=agent_id,
                    message="Agent already paused",
                    previous_state=agent_state.value,
                    new_state=agent_state.value,
                    idempotent=True,
                    timestamp=datetime.now(UTC),
                )
                await self._store_idempotency(idempotency_key, agent_id, "pause", response.to_dict())
                return response

            # Validate transition
            if agent_state not in [AgentState.RUNNING, AgentState.IDLE]:
                raise InterfaceError.from_code(
                    ErrorCode.E10301,
                    details={
                        "agent_id": agent_id,
                        "current_state": agent_state.value,
                        "requested_state": "paused",
                    },
                    recovery_suggestion="Can only pause agents in 'running' or 'idle' state",
                )

            # Perform state transition
            await self._update_agent_state(agent_id, AgentState.PAUSED)

            # Audit log
            if self.audit_logger:
                try:
                    await self.audit_logger.log(
                        event_type="agent.paused",
                        data={
                            "agent_id": agent_id,
                            "tenant_id": tenant_id,
                            "user_id": user_id,
                            "previous_state": agent_state.value,
                            "new_state": "paused",
                            "reason": reason,
                            "timestamp": datetime.now(UTC).isoformat(),
                        },
                    )
                except Exception as e:
                    logger.warning(f"Audit log failed: {e}")

            # Publish event
            if self.event_bus:
                try:
                    await self._publish_control_event(
                        agent_id, tenant_id, user_id, "agent.paused", "paused"
                    )
                except Exception as e:
                    logger.warning(f"Event publish failed: {e}")

            response = ControlResponse(
                operation=ControlOperation.PAUSE,
                status=ControlStatus.SUCCESS,
                agent_id=agent_id,
                message="Agent paused successfully",
                previous_state=agent_state.value,
                new_state="paused",
                timestamp=datetime.now(UTC),
            )

            # Store idempotency
            await self._store_idempotency(idempotency_key, agent_id, "pause", response.to_dict())

            return response

        finally:
            await self._release_lock(agent_id)

    async def resume_agent(
        self,
        agent_id: str,
        tenant_id: str,
        user_id: str,
        idempotency_key: Optional[str] = None,
    ) -> ControlResponse:
        """Resume paused agent (similar pattern to pause_agent)."""
        if not idempotency_key:
            idempotency_key = str(uuid.uuid4())

        idem_result = await self._check_idempotency(idempotency_key, agent_id, "resume")
        if idem_result:
            return ControlResponse(**idem_result)

        lock_acquired = await self._acquire_lock(agent_id)
        if not lock_acquired:
            raise InterfaceError.from_code(ErrorCode.E10305, details={"agent_id": agent_id})

        try:
            agent_state = await self._get_agent_state(agent_id)
            if not agent_state:
                raise InterfaceError.from_code(ErrorCode.E10302, details={"agent_id": agent_id})

            # Check if already running (idempotent)
            if agent_state == AgentState.RUNNING:
                response = ControlResponse(
                    operation=ControlOperation.RESUME,
                    status=ControlStatus.IDEMPOTENT,
                    agent_id=agent_id,
                    message="Agent already running",
                    previous_state=agent_state.value,
                    new_state=agent_state.value,
                    idempotent=True,
                )
                await self._store_idempotency(idempotency_key, agent_id, "resume", response.to_dict())
                return response

            # Validate transition
            if agent_state != AgentState.PAUSED:
                raise InterfaceError.from_code(
                    ErrorCode.E10301,
                    details={
                        "agent_id": agent_id,
                        "current_state": agent_state.value,
                        "requested_state": "running",
                    },
                )

            await self._update_agent_state(agent_id, AgentState.RUNNING)

            if self.event_bus:
                await self._publish_control_event(agent_id, tenant_id, user_id, "agent.resumed", "running")

            response = ControlResponse(
                operation=ControlOperation.RESUME,
                status=ControlStatus.SUCCESS,
                agent_id=agent_id,
                message="Agent resumed successfully",
                previous_state=agent_state.value,
                new_state="running",
            )

            await self._store_idempotency(idempotency_key, agent_id, "resume", response.to_dict())
            return response

        finally:
            await self._release_lock(agent_id)

    async def _get_agent_state(self, agent_id: str) -> Optional[AgentState]:
        """Get current agent state from StateManager."""
        if not self.state_manager or not hasattr(self.state_manager, "get_agent_state"):
            return None

        try:
            state_data = await self.state_manager.get_agent_state(agent_id)
            if state_data:
                state_str = state_data.get("state") if isinstance(state_data, dict) else getattr(state_data, "state", None)
                return AgentState(state_str) if state_str else None
        except Exception as e:
            logger.error(f"Failed to get agent state: {e}")
        return None

    async def _update_agent_state(self, agent_id: str, new_state: AgentState):
        """Update agent state in StateManager."""
        if not self.state_manager or not hasattr(self.state_manager, "update_agent_state"):
            raise InterfaceError.from_code(ErrorCode.E10303, details={"agent_id": agent_id})

        try:
            await self.state_manager.update_agent_state(agent_id, new_state.value)
        except Exception as e:
            logger.error(f"Failed to update agent state: {e}")
            raise InterfaceError.from_code(ErrorCode.E10303, details={"agent_id": agent_id, "error": str(e)})

    async def _acquire_lock(self, agent_id: str, timeout: Optional[int] = None) -> bool:
        """Acquire distributed lock using Redis SET NX EX."""
        if not self.redis:
            return True  # No Redis, skip locking

        timeout = timeout or self.settings.control_lock_ttl
        lock_key = f"control:lock:{agent_id}"

        try:
            acquired = await self.redis.set(lock_key, "locked", ex=timeout, nx=True)
            return bool(acquired)
        except Exception as e:
            logger.error(f"Lock acquisition failed: {e}")
            return False

    async def _release_lock(self, agent_id: str):
        """Release distributed lock."""
        if not self.redis:
            return

        lock_key = f"control:lock:{agent_id}"
        try:
            await self.redis.delete(lock_key)
        except Exception as e:
            logger.warning(f"Lock release failed: {e}")

    async def _check_idempotency(self, idempotency_key: str, agent_id: str, operation: str) -> Optional[dict]:
        """Check if operation was already processed."""
        if not self.redis:
            return None

        idem_key = f"control:idem:{idempotency_key}"
        try:
            cached = await self.redis.get(idem_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Idempotency check failed: {e}")
        return None

    async def _store_idempotency(self, idempotency_key: str, agent_id: str, operation: str, result: dict):
        """Store operation result for idempotency."""
        if not self.redis:
            return

        idem_key = f"control:idem:{idempotency_key}"
        try:
            await self.redis.setex(idem_key, self.settings.control_idempotency_ttl, json.dumps(result))
        except Exception as e:
            logger.warning(f"Idempotency store failed: {e}")

    async def _publish_control_event(self, agent_id: str, tenant_id: str, user_id: str, event_type: str, new_state: str):
        """Publish control event to event bus."""
        # Placeholder - actual implementation depends on L11 EventBus API
        pass

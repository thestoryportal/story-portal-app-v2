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
    UpdateQuotaRequest,
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

    async def emergency_stop_agent(
        self,
        agent_id: str,
        tenant_id: str,
        user_id: str,
        reason: str,
        idempotency_key: Optional[str] = None,
    ) -> ControlResponse:
        """
        Emergency stop agent - works from any state.

        Unlike pause, emergency stop bypasses normal state validation and
        priority locks. Used for critical situations requiring immediate shutdown.

        Args:
            agent_id: Agent ID
            tenant_id: Tenant ID
            user_id: User performing the action
            reason: Required reason for emergency stop
            idempotency_key: Optional idempotency key

        Returns:
            ControlResponse
        """
        if not idempotency_key:
            idempotency_key = str(uuid.uuid4())

        # Check idempotency
        idem_result = await self._check_idempotency(idempotency_key, agent_id, "emergency_stop")
        if idem_result:
            logger.info(f"Idempotent emergency stop request: {idempotency_key}")
            return ControlResponse(**idem_result)

        # Acquire priority lock with shorter timeout
        lock_acquired = await self._acquire_lock(agent_id, timeout=5)
        if not lock_acquired:
            # For emergency stop, we force acquire by deleting existing lock
            logger.warning(f"Force acquiring lock for emergency stop: {agent_id}")
            await self._release_lock(agent_id)
            lock_acquired = await self._acquire_lock(agent_id, timeout=5)
            if not lock_acquired:
                raise InterfaceError.from_code(
                    ErrorCode.E10303,
                    details={"agent_id": agent_id, "reason": "Failed to acquire emergency lock"},
                )

        try:
            # Get current agent state (but don't validate - emergency stop works from any state)
            previous_state = "unknown"
            if self.state_manager:
                try:
                    agent_state = await self._get_agent_state(agent_id)
                    if agent_state:
                        previous_state = agent_state.value
                        # Check if already stopped (idempotent)
                        if agent_state == AgentState.STOPPED:
                            response = ControlResponse(
                                operation=ControlOperation.EMERGENCY_STOP,
                                status=ControlStatus.IDEMPOTENT,
                                agent_id=agent_id,
                                message="Agent already stopped",
                                previous_state=previous_state,
                                new_state=previous_state,
                                idempotent=True,
                                timestamp=datetime.now(UTC),
                            )
                            await self._store_idempotency(
                                idempotency_key, agent_id, "emergency_stop", response.to_dict()
                            )
                            return response
                except Exception as e:
                    logger.warning(f"Could not get agent state (continuing with stop): {e}")

            # Perform emergency stop - force state to STOPPED
            if self.state_manager and hasattr(self.state_manager, "update_agent_state"):
                try:
                    await self.state_manager.update_agent_state(agent_id, AgentState.STOPPED.value)
                except Exception as e:
                    logger.error(f"State update failed during emergency stop: {e}")
                    # Continue anyway - log the failure but don't block emergency stop

            # Audit log (critical - always log)
            if self.audit_logger:
                try:
                    await self.audit_logger.log(
                        event_type="agent.emergency_stopped",
                        data={
                            "agent_id": agent_id,
                            "tenant_id": tenant_id,
                            "user_id": user_id,
                            "previous_state": previous_state,
                            "new_state": "stopped",
                            "reason": reason,
                            "timestamp": datetime.now(UTC).isoformat(),
                            "emergency": True,
                        },
                    )
                except Exception as e:
                    logger.error(f"Audit log failed for emergency stop: {e}")

            # Publish event
            try:
                await self._publish_control_event(
                    agent_id, tenant_id, user_id, "agent.emergency_stopped", "stopped"
                )
            except Exception as e:
                logger.warning(f"Event publish failed: {e}")

            response = ControlResponse(
                operation=ControlOperation.EMERGENCY_STOP,
                status=ControlStatus.SUCCESS,
                agent_id=agent_id,
                message=f"Agent emergency stopped: {reason}",
                previous_state=previous_state,
                new_state="stopped",
                timestamp=datetime.now(UTC),
                metadata={"reason": reason, "emergency": True},
            )

            # Store idempotency
            await self._store_idempotency(
                idempotency_key, agent_id, "emergency_stop", response.to_dict()
            )

            logger.warning(f"EMERGENCY STOP: Agent {agent_id} stopped by {user_id}: {reason}")
            return response

        finally:
            await self._release_lock(agent_id)

    async def update_quota(
        self,
        request: UpdateQuotaRequest,
        tenant_id: str,
        user_id: str,
    ) -> ControlResponse:
        """
        Update agent resource quotas.

        Updates token, CPU, and memory limits for an agent.

        Args:
            request: UpdateQuotaRequest with agent_id and quota values
            tenant_id: Tenant ID
            user_id: User performing the action

        Returns:
            ControlResponse
        """
        agent_id = request.agent_id

        # Validate quota values (must be positive if specified)
        if request.tokens_per_hour is not None and request.tokens_per_hour < 0:
            raise InterfaceError.from_code(
                ErrorCode.E10306,
                details={"tokens_per_hour": request.tokens_per_hour, "reason": "Must be non-negative"},
            )
        if request.cpu_millicores is not None and request.cpu_millicores < 0:
            raise InterfaceError.from_code(
                ErrorCode.E10306,
                details={"cpu_millicores": request.cpu_millicores, "reason": "Must be non-negative"},
            )
        if request.memory_mb is not None and request.memory_mb < 0:
            raise InterfaceError.from_code(
                ErrorCode.E10306,
                details={"memory_mb": request.memory_mb, "reason": "Must be non-negative"},
            )

        # Acquire lock
        lock_acquired = await self._acquire_lock(agent_id)
        if not lock_acquired:
            raise InterfaceError.from_code(
                ErrorCode.E10305,
                details={"agent_id": agent_id},
                recovery_suggestion="Another operation is in progress, retry in a few seconds",
            )

        try:
            # Verify agent exists
            if self.state_manager:
                agent_state = await self._get_agent_state(agent_id)
                if not agent_state:
                    raise InterfaceError.from_code(
                        ErrorCode.E10302,
                        details={"agent_id": agent_id},
                    )

            # Build quota update
            quota_updates = {}
            if request.tokens_per_hour is not None:
                quota_updates["tokens_per_hour"] = request.tokens_per_hour
            if request.cpu_millicores is not None:
                quota_updates["cpu_millicores"] = request.cpu_millicores
            if request.memory_mb is not None:
                quota_updates["memory_mb"] = request.memory_mb

            if not quota_updates:
                raise InterfaceError.from_code(
                    ErrorCode.E10306,
                    details={"agent_id": agent_id, "reason": "No quota values provided"},
                )

            # Update quotas via StateManager if available
            if self.state_manager and hasattr(self.state_manager, "update_agent_quotas"):
                try:
                    await self.state_manager.update_agent_quotas(agent_id, quota_updates)
                except Exception as e:
                    logger.error(f"Failed to update quotas: {e}")
                    raise InterfaceError.from_code(
                        ErrorCode.E10303,
                        details={"agent_id": agent_id, "error": str(e)},
                    )
            else:
                # Log that quota update was requested but StateManager doesn't support it
                logger.warning(f"StateManager doesn't support quota updates, logging only")

            # Audit log
            if self.audit_logger:
                try:
                    await self.audit_logger.log(
                        event_type="agent.quota_updated",
                        data={
                            "agent_id": agent_id,
                            "tenant_id": tenant_id,
                            "user_id": user_id,
                            "quota_updates": quota_updates,
                            "timestamp": datetime.now(UTC).isoformat(),
                        },
                    )
                except Exception as e:
                    logger.warning(f"Audit log failed: {e}")

            # Publish event
            try:
                await self._publish_control_event(
                    agent_id, tenant_id, user_id, "agent.quota_updated", None
                )
            except Exception as e:
                logger.warning(f"Event publish failed: {e}")

            response = ControlResponse(
                operation=ControlOperation.UPDATE_QUOTA,
                status=ControlStatus.SUCCESS,
                agent_id=agent_id,
                message="Agent quotas updated successfully",
                timestamp=datetime.now(UTC),
                metadata={"quota_updates": quota_updates},
            )

            logger.info(f"Updated quotas for agent {agent_id}: {quota_updates}")
            return response

        finally:
            await self._release_lock(agent_id)

    async def _publish_control_event(
        self,
        agent_id: str,
        tenant_id: str,
        user_id: str,
        event_type: str,
        new_state: Optional[str],
    ):
        """Publish control event to event bus (L11).

        Args:
            agent_id: Agent ID
            tenant_id: Tenant ID
            user_id: User who triggered the operation
            event_type: Type of control event
            new_state: New agent state (if applicable)
        """
        if not self.event_bus:
            return

        try:
            event_data = {
                "event_type": event_type,
                "agent_id": agent_id,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            if new_state:
                event_data["new_state"] = new_state

            # Publish to L11 event bus topic
            # The event_bus is expected to have a publish method
            if hasattr(self.event_bus, "publish"):
                await self.event_bus.publish(
                    topic="l10.control.operations",
                    message=event_data,
                )
            elif hasattr(self.event_bus, "send"):
                await self.event_bus.send(
                    topic="l10.control.operations",
                    message=event_data,
                )
            else:
                # Fallback: try to use Redis pub/sub directly
                if self.redis:
                    await self.redis.publish(
                        "l10.control.operations",
                        json.dumps(event_data),
                    )

            logger.debug(f"Published control event: {event_type} for agent {agent_id}")

        except Exception as e:
            # Don't fail the operation if event publish fails
            logger.warning(f"Failed to publish control event: {e}")

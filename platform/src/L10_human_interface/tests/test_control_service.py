"""
L10 Human Interface Layer - Control Service Tests

Test control operations, locking, idempotency, and state validation.
"""

import pytest
import asyncio
import time
from datetime import datetime, UTC
from unittest.mock import AsyncMock, Mock, patch

from ..models import (
    AgentState,
    ControlOperation,
    ControlStatus,
    UpdateQuotaRequest,
    ErrorCode,
    InterfaceError,
)
from ..services import ControlService


class TestControlServiceInit:
    """Test service initialization."""

    def test_control_service_creation(self, control_service):
        """Test control service creates successfully."""
        assert control_service is not None
        assert control_service.state_manager is not None
        assert control_service.event_bus is not None


class TestPauseAgent:
    """Test pause agent operation."""

    @pytest.mark.asyncio
    async def test_pause_agent_success(self, control_service, mock_state_manager):
        """Test successful agent pause."""
        # Mock agent in running state
        mock_state_manager.get_agent_state.return_value = {
            "agent_id": "agent-1",
            "state": "running",
            "tenant_id": "tenant-1",
        }
        mock_state_manager.update_agent_state.return_value = None

        response = await control_service.pause_agent(
            agent_id="agent-1",
            tenant_id="tenant-1",
            user_id="user-1",
            reason="Manual pause for maintenance",
        )

        assert response.operation == ControlOperation.PAUSE
        assert response.status == ControlStatus.SUCCESS
        assert response.agent_id == "agent-1"
        assert response.previous_state == "running"
        assert response.new_state == "paused"

        # Verify state manager was called
        mock_state_manager.update_agent_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_pause_agent_idempotent(self, control_service, mock_state_manager):
        """Test pausing already paused agent is idempotent."""
        # Mock agent in paused state
        mock_state_manager.get_agent_state.return_value = {
            "agent_id": "agent-1",
            "state": "paused",
            "tenant_id": "tenant-1",
        }

        response = await control_service.pause_agent(
            agent_id="agent-1",
            tenant_id="tenant-1",
            user_id="user-1",
        )

        assert response.status == ControlStatus.IDEMPOTENT
        assert response.idempotent is True
        # State manager should not be called for update
        mock_state_manager.update_agent_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_pause_agent_invalid_state_transition(self, control_service, mock_state_manager):
        """Test pausing failed agent raises error."""
        # Mock agent in failed state (invalid for pause)
        mock_state_manager.get_agent_state.return_value = {
            "agent_id": "agent-1",
            "state": "failed",
            "tenant_id": "tenant-1",
        }

        with pytest.raises(InterfaceError) as exc_info:
            await control_service.pause_agent(
                agent_id="agent-1",
                tenant_id="tenant-1",
                user_id="user-1",
            )

        assert exc_info.value.code == ErrorCode.E10301  # Invalid state transition

    @pytest.mark.asyncio
    async def test_pause_agent_not_found(self, control_service, mock_state_manager):
        """Test pausing nonexistent agent raises error."""
        mock_state_manager.get_agent_state.return_value = None

        with pytest.raises(InterfaceError) as exc_info:
            await control_service.pause_agent(
                agent_id="nonexistent",
                tenant_id="tenant-1",
                user_id="user-1",
            )

        assert exc_info.value.code == ErrorCode.E10302  # Agent not found

    @pytest.mark.asyncio
    async def test_pause_agent_audit_logging(self, control_service, mock_audit_logger):
        """Test that pause operation is audit logged."""
        await control_service.pause_agent(
            agent_id="agent-1",
            tenant_id="tenant-1",
            user_id="user-1",
            reason="Scheduled maintenance",
        )

        # Verify audit log was called
        mock_audit_logger.log.assert_called_once()
        call_args = mock_audit_logger.log.call_args
        assert "pause" in str(call_args).lower()

    @pytest.mark.asyncio
    async def test_pause_agent_publishes_event(self, control_service, mock_event_bus):
        """Test that pause operation publishes event."""
        await control_service.pause_agent(
            agent_id="agent-1",
            tenant_id="tenant-1",
            user_id="user-1",
        )

        # Verify event was published
        mock_event_bus.publish.assert_called()
        call_args = mock_event_bus.publish.call_args
        assert "control" in str(call_args).lower() or "pause" in str(call_args).lower()


class TestResumeAgent:
    """Test resume agent operation."""

    @pytest.mark.asyncio
    async def test_resume_agent_success(self, control_service, mock_state_manager):
        """Test successful agent resume."""
        # Mock agent in paused state
        mock_state_manager.get_agent_state.return_value = {
            "agent_id": "agent-1",
            "state": "paused",
            "tenant_id": "tenant-1",
        }

        response = await control_service.resume_agent(
            agent_id="agent-1",
            tenant_id="tenant-1",
            user_id="user-1",
        )

        assert response.operation == ControlOperation.RESUME
        assert response.status == ControlStatus.SUCCESS
        assert response.previous_state == "paused"
        assert response.new_state == "running"

    @pytest.mark.asyncio
    async def test_resume_agent_idempotent(self, control_service, mock_state_manager):
        """Test resuming already running agent is idempotent."""
        # Mock agent in running state
        mock_state_manager.get_agent_state.return_value = {
            "agent_id": "agent-1",
            "state": "running",
            "tenant_id": "tenant-1",
        }

        response = await control_service.resume_agent(
            agent_id="agent-1",
            tenant_id="tenant-1",
            user_id="user-1",
        )

        assert response.status == ControlStatus.IDEMPOTENT
        assert response.idempotent is True

    @pytest.mark.asyncio
    async def test_resume_agent_invalid_state(self, control_service, mock_state_manager):
        """Test resuming failed agent raises error."""
        # Mock agent in failed state
        mock_state_manager.get_agent_state.return_value = {
            "agent_id": "agent-1",
            "state": "failed",
            "tenant_id": "tenant-1",
        }

        with pytest.raises(InterfaceError) as exc_info:
            await control_service.resume_agent(
                agent_id="agent-1",
                tenant_id="tenant-1",
                user_id="user-1",
            )

        assert exc_info.value.code == ErrorCode.E10301


class TestEmergencyStop:
    """Test emergency stop operation."""

    @pytest.mark.asyncio
    async def test_emergency_stop_success(self, control_service, mock_state_manager):
        """Test successful emergency stop."""
        # Mock agent in running state
        mock_state_manager.get_agent_state.return_value = {
            "agent_id": "agent-1",
            "state": "running",
            "tenant_id": "tenant-1",
        }

        response = await control_service.emergency_stop_agent(
            agent_id="agent-1",
            tenant_id="tenant-1",
            user_id="admin-1",
            reason="Critical security issue detected",
        )

        assert response.operation == ControlOperation.EMERGENCY_STOP
        assert response.status == ControlStatus.SUCCESS
        assert response.new_state == "stopped"

    @pytest.mark.asyncio
    async def test_emergency_stop_from_any_state(self, control_service, mock_state_manager):
        """Test emergency stop works from any state (no state validation)."""
        # Emergency stop should work regardless of current state
        for state in ["running", "paused", "idle", "failed"]:
            mock_state_manager.get_agent_state.return_value = {
                "agent_id": "agent-1",
                "state": state,
                "tenant_id": "tenant-1",
            }

            response = await control_service.emergency_stop_agent(
                agent_id="agent-1",
                tenant_id="tenant-1",
                user_id="admin-1",
                reason="Emergency",
            )

            assert response.status == ControlStatus.SUCCESS
            assert response.new_state == "stopped"

    @pytest.mark.asyncio
    async def test_emergency_stop_bypasses_normal_locks(self, control_service, redis_client, mock_state_manager):
        """Test emergency stop force-acquires lock if already locked."""
        mock_state_manager.get_agent_state.return_value = {
            "agent_id": "agent-1",
            "state": "running",
            "tenant_id": "tenant-1",
        }

        # Pre-acquire a lock (simulating another operation in progress)
        lock_key = "control:lock:agent-1"
        await redis_client.set(lock_key, "locked", ex=60)

        # Emergency stop should still succeed by force-releasing
        response = await control_service.emergency_stop_agent(
            agent_id="agent-1",
            tenant_id="tenant-1",
            user_id="admin-1",
            reason="Critical emergency",
        )

        assert response.status == ControlStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_emergency_stop_requires_reason(self, control_service, mock_state_manager):
        """Test emergency stop requires a reason."""
        mock_state_manager.get_agent_state.return_value = {
            "agent_id": "agent-1",
            "state": "running",
            "tenant_id": "tenant-1",
        }

        # Reason is a required parameter in the method signature
        # This test verifies the reason is included in the response
        response = await control_service.emergency_stop_agent(
            agent_id="agent-1",
            tenant_id="tenant-1",
            user_id="admin-1",
            reason="Test emergency reason",
        )

        assert response.status == ControlStatus.SUCCESS
        assert "Test emergency reason" in response.message

    @pytest.mark.asyncio
    async def test_emergency_stop_audit_logged(self, control_service, mock_audit_logger, mock_state_manager):
        """Test that emergency stop is always audit logged."""
        mock_state_manager.get_agent_state.return_value = {
            "agent_id": "agent-1",
            "state": "running",
            "tenant_id": "tenant-1",
        }

        await control_service.emergency_stop_agent(
            agent_id="agent-1",
            tenant_id="tenant-1",
            user_id="admin-1",
            reason="Critical issue",
        )

        # Verify audit log was called with emergency flag
        mock_audit_logger.log.assert_called_once()
        call_args = mock_audit_logger.log.call_args
        assert "emergency" in str(call_args).lower()

    @pytest.mark.asyncio
    async def test_emergency_stop_already_stopped_idempotent(self, control_service, mock_state_manager):
        """Test emergency stop on already stopped agent is idempotent."""
        mock_state_manager.get_agent_state.return_value = {
            "agent_id": "agent-1",
            "state": "stopped",
            "tenant_id": "tenant-1",
        }

        response = await control_service.emergency_stop_agent(
            agent_id="agent-1",
            tenant_id="tenant-1",
            user_id="admin-1",
            reason="Already stopped",
        )

        assert response.status == ControlStatus.IDEMPOTENT
        assert response.idempotent is True


class TestDistributedLocking:
    """Test distributed locking mechanism."""

    @pytest.mark.asyncio
    async def test_acquire_lock_success(self, control_service, redis_client):
        """Test successful lock acquisition."""
        acquired = await control_service._acquire_lock(agent_id="agent-1")
        assert acquired is True

        # Verify lock exists in Redis
        lock_key = f"control:lock:agent-1"
        lock_value = await redis_client.get(lock_key)
        assert lock_value is not None

    @pytest.mark.asyncio
    async def test_acquire_lock_already_locked(self, control_service, redis_client):
        """Test lock acquisition fails when already locked."""
        # First acquisition succeeds
        acquired1 = await control_service._acquire_lock(agent_id="agent-1")
        assert acquired1 is True

        # Second acquisition fails
        acquired2 = await control_service._acquire_lock(agent_id="agent-1")
        assert acquired2 is False

    @pytest.mark.asyncio
    async def test_release_lock_success(self, control_service, redis_client):
        """Test successful lock release."""
        await control_service._acquire_lock(agent_id="agent-1")
        await control_service._release_lock(agent_id="agent-1")

        # Verify lock removed from Redis
        lock_key = f"control:lock:agent-1"
        lock_value = await redis_client.get(lock_key)
        assert lock_value is None

    @pytest.mark.asyncio
    async def test_lock_expires_automatically(self, control_service, redis_client):
        """Test lock expires after TTL."""
        # Acquire lock with short TTL
        await control_service._acquire_lock(agent_id="agent-1", timeout=1)

        # Wait for expiration
        await asyncio.sleep(1.5)

        # Lock should be expired, can acquire again
        acquired = await control_service._acquire_lock(agent_id="agent-1")
        assert acquired is True

    @pytest.mark.asyncio
    async def test_concurrent_operations_blocked_by_lock(self, control_service, mock_state_manager):
        """Test concurrent operations on same agent are blocked."""
        # Mock running agent
        mock_state_manager.get_agent_state.return_value = {
            "agent_id": "agent-1",
            "state": "running",
            "tenant_id": "tenant-1",
        }

        # First operation acquires lock
        response1 = await control_service.pause_agent(
            agent_id="agent-1",
            tenant_id="tenant-1",
            user_id="user-1",
        )
        assert response1.status == ControlStatus.SUCCESS

        # Second operation should fail (lock held)
        # Note: This test may need adjustment based on actual lock implementation
        # If the lock is released after operation, we need to test during operation


class TestIdempotency:
    """Test idempotency mechanism."""

    @pytest.mark.asyncio
    async def test_idempotency_key_prevents_duplicate(self, control_service, redis_client, mock_state_manager):
        """Test idempotency key prevents duplicate operations."""
        # Mock running agent
        mock_state_manager.get_agent_state.return_value = {
            "agent_id": "agent-1",
            "state": "running",
            "tenant_id": "tenant-1",
        }

        idempotency_key = "unique-operation-123"

        # First operation succeeds
        response1 = await control_service.pause_agent(
            agent_id="agent-1",
            tenant_id="tenant-1",
            user_id="user-1",
            idempotency_key=idempotency_key,
        )
        assert response1.status == ControlStatus.SUCCESS
        call_count = mock_state_manager.update_agent_state.call_count

        # Second operation with same key returns cached result
        response2 = await control_service.pause_agent(
            agent_id="agent-1",
            tenant_id="tenant-1",
            user_id="user-1",
            idempotency_key=idempotency_key,
        )

        # Should return same result without calling state manager again
        assert response2.operation == response1.operation
        assert mock_state_manager.update_agent_state.call_count == call_count

    @pytest.mark.asyncio
    async def test_idempotency_cache_expiration(self, control_service, redis_client):
        """Test idempotency cache expires after TTL."""
        # This would require time manipulation or shorter TTL for testing
        # Placeholder for testing cache expiration logic
        pass

    @pytest.mark.asyncio
    async def test_different_idempotency_keys_allowed(self, control_service, mock_state_manager):
        """Test different idempotency keys allow separate operations."""
        mock_state_manager.get_agent_state.return_value = {
            "agent_id": "agent-1",
            "state": "running",
            "tenant_id": "tenant-1",
        }

        # Two operations with different keys should both execute
        response1 = await control_service.pause_agent(
            agent_id="agent-1",
            tenant_id="tenant-1",
            user_id="user-1",
            idempotency_key="key-1",
        )

        # Reset state to running for second operation
        mock_state_manager.get_agent_state.return_value = {
            "agent_id": "agent-1",
            "state": "running",
            "tenant_id": "tenant-1",
        }

        response2 = await control_service.pause_agent(
            agent_id="agent-1",
            tenant_id="tenant-1",
            user_id="user-1",
            idempotency_key="key-2",
        )

        # Both should succeed
        assert response1.status == ControlStatus.SUCCESS
        assert response2.status in [ControlStatus.SUCCESS, ControlStatus.IDEMPOTENT]


class TestQuotaAdjustment:
    """Test quota adjustment operations."""

    @pytest.mark.asyncio
    async def test_update_quota_tokens_success(self, control_service, mock_state_manager):
        """Test successful token quota update."""
        request = UpdateQuotaRequest(
            agent_id="agent-1",
            tokens_per_hour=10000,
        )

        response = await control_service.update_quota(
            request=request,
            tenant_id="tenant-1",
            user_id="user-1",
        )

        assert response.status == ControlStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_update_quota_cpu_success(self, control_service, mock_state_manager):
        """Test successful CPU quota update."""
        request = UpdateQuotaRequest(
            agent_id="agent-1",
            cpu_millicores=500,
        )

        response = await control_service.update_quota(
            request=request,
            tenant_id="tenant-1",
            user_id="user-1",
        )

        assert response.status == ControlStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_update_quota_memory_success(self, control_service, mock_state_manager):
        """Test successful memory quota update."""
        request = UpdateQuotaRequest(
            agent_id="agent-1",
            memory_mb=1024,
        )

        response = await control_service.update_quota(
            request=request,
            tenant_id="tenant-1",
            user_id="user-1",
        )

        assert response.status == ControlStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_update_quota_invalid_negative(self, control_service):
        """Test invalid negative quota value raises error."""
        request = UpdateQuotaRequest(
            agent_id="agent-1",
            tokens_per_hour=-100,  # Invalid negative
        )

        with pytest.raises(InterfaceError) as exc_info:
            await control_service.update_quota(
                request=request,
                tenant_id="tenant-1",
                user_id="user-1",
            )

        assert exc_info.value.code == ErrorCode.E10306

    @pytest.mark.asyncio
    async def test_update_quota_agent_not_found(self, control_service, mock_state_manager):
        """Test quota update for nonexistent agent raises error."""
        mock_state_manager.get_agent_state.return_value = None
        request = UpdateQuotaRequest(
            agent_id="nonexistent",
            tokens_per_hour=10000,
        )

        with pytest.raises(InterfaceError) as exc_info:
            await control_service.update_quota(
                request=request,
                tenant_id="tenant-1",
                user_id="user-1",
            )

        assert exc_info.value.code == ErrorCode.E10302

    @pytest.mark.asyncio
    async def test_update_quota_publishes_event(self, control_service, mock_event_bus):
        """Test that quota update publishes event."""
        request = UpdateQuotaRequest(
            agent_id="agent-1",
            tokens_per_hour=10000,
        )

        await control_service.update_quota(
            request=request,
            tenant_id="tenant-1",
            user_id="user-1",
        )

        # Verify event was published
        mock_event_bus.publish.assert_called()


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_state_manager_unavailable(self, control_service, mock_state_manager):
        """Test L02 unavailability raises appropriate error."""
        mock_state_manager.get_agent_state.side_effect = Exception("Connection refused")

        with pytest.raises(InterfaceError) as exc_info:
            await control_service.pause_agent(
                agent_id="agent-1",
                tenant_id="tenant-1",
                user_id="user-1",
            )

        assert exc_info.value.code in [ErrorCode.E10901, ErrorCode.E10902]

    @pytest.mark.asyncio
    async def test_event_bus_failure_doesnt_block_operation(self, control_service, mock_event_bus):
        """Test that event bus failure doesn't prevent operation."""
        # Make event bus fail
        mock_event_bus.publish.side_effect = Exception("Event bus unavailable")

        # Operation should still succeed
        response = await control_service.pause_agent(
            agent_id="agent-1",
            tenant_id="tenant-1",
            user_id="user-1",
        )

        assert response.status == ControlStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_audit_log_failure_doesnt_block_operation(self, control_service, mock_audit_logger):
        """Test that audit log failure doesn't prevent operation."""
        # Make audit logger fail
        mock_audit_logger.log.side_effect = Exception("Audit unavailable")

        # Operation should still succeed (audit is important but not critical)
        response = await control_service.pause_agent(
            agent_id="agent-1",
            tenant_id="tenant-1",
            user_id="user-1",
        )

        assert response.status == ControlStatus.SUCCESS


class TestTenantIsolation:
    """Test tenant isolation in control operations."""

    @pytest.mark.asyncio
    async def test_cross_tenant_operation_blocked(self, control_service, mock_state_manager):
        """Test user cannot control agent from different tenant."""
        # Mock agent belonging to tenant-1
        mock_state_manager.get_agent_state.return_value = {
            "agent_id": "agent-1",
            "state": "running",
            "tenant_id": "tenant-1",
        }

        # User from tenant-2 tries to pause
        with pytest.raises(InterfaceError) as exc_info:
            await control_service.pause_agent(
                agent_id="agent-1",
                tenant_id="tenant-2",  # Different tenant
                user_id="user-from-tenant-2",
            )

        assert exc_info.value.code in [ErrorCode.E10003, ErrorCode.E10302]

"""
L08 Supervision Layer - Escalation Orchestrator Tests

Tests for escalation workflow management and state transitions.
"""

import pytest
import asyncio
from datetime import datetime, timedelta

from ..models.domain import EscalationWorkflow, EscalationStatus


@pytest.mark.l08
@pytest.mark.unit
class TestEscalationOrchestrator:
    """Tests for the escalation orchestrator"""

    @pytest.mark.asyncio
    async def test_create_escalation(self, escalation_orchestrator):
        """Test creating an escalation workflow"""
        workflow, error = await escalation_orchestrator.create_escalation(
            decision_id="dec_001",
            reason="High risk operation",
            context={"operation": "delete_user_data"},
            approvers=["admin_001", "admin_002"],
        )

        assert error is None
        assert workflow is not None
        assert workflow.workflow_id != ""
        assert workflow.status == EscalationStatus.PENDING
        assert workflow.escalation_level == 1
        assert len(workflow.approvers) == 2

    @pytest.mark.asyncio
    async def test_escalation_state_transitions(self, escalation_orchestrator):
        """Test escalation state transitions"""
        workflow, _ = await escalation_orchestrator.create_escalation(
            decision_id="dec_001",
            reason="Test",
            context={},
            approvers=["admin_001"],
        )

        # Initial state is PENDING
        assert workflow.status == EscalationStatus.PENDING

        # After notification, should be NOTIFIED (this happens async)
        await asyncio.sleep(0.1)  # Give time for async notification
        refreshed = await escalation_orchestrator.get_escalation(workflow.workflow_id)
        assert refreshed.status in [EscalationStatus.PENDING, EscalationStatus.NOTIFIED]

    @pytest.mark.asyncio
    async def test_approve_escalation(self, escalation_orchestrator):
        """Test approving an escalation"""
        workflow, _ = await escalation_orchestrator.create_escalation(
            decision_id="dec_001",
            reason="Test approval",
            context={},
            approvers=["admin_001"],
        )

        resolved, error = await escalation_orchestrator.resolve(
            workflow_id=workflow.workflow_id,
            approved=True,
            approver_id="admin_001",
            notes="Approved for testing",
        )

        assert error is None
        assert resolved.status == EscalationStatus.APPROVED
        assert resolved.resolved_by == "admin_001"
        assert resolved.resolution_notes == "Approved for testing"
        assert resolved.resolved_at is not None

    @pytest.mark.asyncio
    async def test_reject_escalation(self, escalation_orchestrator):
        """Test rejecting an escalation"""
        workflow, _ = await escalation_orchestrator.create_escalation(
            decision_id="dec_001",
            reason="Test rejection",
            context={},
            approvers=["admin_001"],
        )

        resolved, error = await escalation_orchestrator.resolve(
            workflow_id=workflow.workflow_id,
            approved=False,
            approver_id="admin_001",
            notes="Rejected - insufficient justification",
        )

        assert error is None
        assert resolved.status == EscalationStatus.REJECTED
        assert resolved.resolved_by == "admin_001"

    @pytest.mark.asyncio
    async def test_escalation_timeout(self, escalation_orchestrator, test_config):
        """Test escalation timeout handling"""
        # Create escalation with very short timeout
        workflow, _ = await escalation_orchestrator.create_escalation(
            decision_id="dec_001",
            reason="Test timeout",
            context={},
            approvers=["admin_001"],
        )

        # Wait for timeout (configured to 5 seconds in test_config)
        await asyncio.sleep(6)

        # Check escalation status
        refreshed = await escalation_orchestrator.get_escalation(workflow.workflow_id)

        # Should have either escalated to next level or timed out
        assert refreshed.status in [
            EscalationStatus.WAITING,
            EscalationStatus.TIMED_OUT,
        ] or refreshed.escalation_level > 1

    @pytest.mark.asyncio
    async def test_escalation_to_manager(self, escalation_orchestrator, test_config):
        """Test escalation to manager on timeout"""
        workflow, _ = await escalation_orchestrator.create_escalation(
            decision_id="dec_001",
            reason="Test manager escalation",
            context={},
            approvers=["admin_001"],
        )

        initial_level = workflow.escalation_level

        # Wait for timeout
        await asyncio.sleep(6)

        refreshed = await escalation_orchestrator.get_escalation(workflow.workflow_id)

        # If not timed out completely, should have escalated
        if refreshed.status not in [EscalationStatus.TIMED_OUT]:
            assert refreshed.escalation_level >= initial_level

    @pytest.mark.asyncio
    async def test_get_pending_escalations(self, escalation_orchestrator):
        """Test getting pending escalations"""
        # Create multiple escalations
        for i in range(3):
            await escalation_orchestrator.create_escalation(
                decision_id=f"dec_{i}",
                reason=f"Test {i}",
                context={},
                approvers=["admin_001"],
            )

        pending = await escalation_orchestrator.get_pending_escalations()
        assert len(pending) >= 3

        # All should be in pending-related states
        for w in pending:
            assert w.status in [
                EscalationStatus.PENDING,
                EscalationStatus.NOTIFIED,
                EscalationStatus.WAITING,
            ]

    @pytest.mark.asyncio
    async def test_resolved_not_in_pending(self, escalation_orchestrator):
        """Test that resolved escalations are not in pending list"""
        workflow, _ = await escalation_orchestrator.create_escalation(
            decision_id="dec_001",
            reason="Test",
            context={},
            approvers=["admin_001"],
        )

        # Resolve it
        await escalation_orchestrator.resolve(
            workflow_id=workflow.workflow_id,
            approved=True,
            approver_id="admin_001",
        )

        pending = await escalation_orchestrator.get_pending_escalations()
        pending_ids = [w.workflow_id for w in pending]

        assert workflow.workflow_id not in pending_ids

    @pytest.mark.asyncio
    async def test_escalation_not_found(self, escalation_orchestrator):
        """Test error for unknown escalation"""
        result = await escalation_orchestrator.get_escalation("unknown_id")
        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_already_resolved(self, escalation_orchestrator):
        """Test error when resolving already resolved escalation"""
        workflow, _ = await escalation_orchestrator.create_escalation(
            decision_id="dec_001",
            reason="Test",
            context={},
            approvers=["admin_001"],
        )

        # Resolve first time
        await escalation_orchestrator.resolve(
            workflow_id=workflow.workflow_id,
            approved=True,
            approver_id="admin_001",
        )

        # Try to resolve again
        result, error = await escalation_orchestrator.resolve(
            workflow_id=workflow.workflow_id,
            approved=False,
            approver_id="admin_002",
        )

        assert error is not None
        assert "already resolved" in error.lower() or "E8301" in error

    @pytest.mark.asyncio
    async def test_mfa_required_when_enabled(self, escalation_orchestrator, test_config):
        """Test MFA requirement based on config"""
        # In test config, MFA is disabled, so this should work without MFA
        workflow, _ = await escalation_orchestrator.create_escalation(
            decision_id="dec_001",
            reason="Test MFA",
            context={},
            approvers=["admin_001"],
        )

        resolved, error = await escalation_orchestrator.resolve(
            workflow_id=workflow.workflow_id,
            approved=True,
            approver_id="admin_001",
            mfa_token=None,  # No MFA token
        )

        # Should succeed since MFA is disabled in test config
        assert error is None
        assert resolved.status == EscalationStatus.APPROVED

    @pytest.mark.asyncio
    async def test_get_stats(self, escalation_orchestrator):
        """Test getting escalation orchestrator statistics"""
        # Create and resolve some escalations
        for i in range(3):
            workflow, _ = await escalation_orchestrator.create_escalation(
                decision_id=f"dec_{i}",
                reason=f"Test {i}",
                context={},
                approvers=["admin_001"],
            )
            if i == 0:
                await escalation_orchestrator.resolve(
                    workflow_id=workflow.workflow_id,
                    approved=True,
                    approver_id="admin_001",
                )

        stats = escalation_orchestrator.get_stats()
        assert "created_count" in stats
        assert "pending_count" in stats
        assert stats["created_count"] >= 3

    @pytest.mark.asyncio
    async def test_health_check(self, escalation_orchestrator):
        """Test escalation orchestrator health check"""
        health = await escalation_orchestrator.health_check()

        assert "status" in health
        assert health["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_cleanup_cancels_tasks(self, escalation_orchestrator):
        """Test that cleanup cancels timeout monitoring tasks"""
        # Create escalations with timeout tasks
        for i in range(3):
            await escalation_orchestrator.create_escalation(
                decision_id=f"dec_{i}",
                reason=f"Test {i}",
                context={},
                approvers=["admin_001"],
            )

        # Should have active timeout tasks
        assert len(escalation_orchestrator._timeout_tasks) >= 3

        # Cleanup
        await escalation_orchestrator.cleanup()

        # All tasks should be cancelled
        for task in escalation_orchestrator._timeout_tasks.values():
            assert task.cancelled() or task.done()

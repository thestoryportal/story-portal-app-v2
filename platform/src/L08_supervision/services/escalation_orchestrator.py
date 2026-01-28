"""
L08 Supervision Layer - Escalation Orchestrator

Human-in-the-loop escalation workflow management with timeout handling,
notification delivery, and MFA verification.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta

from ..models.domain import (
    EscalationWorkflow,
    EscalationStatus,
)
from ..models.config import SupervisionConfiguration
from ..models.error_codes import ErrorCodes, EscalationError
from ..integration.l01_bridge import L08Bridge
from ..integration.l10_bridge import L10Bridge
from .audit_manager import AuditManager

logger = logging.getLogger(__name__)


class EscalationOrchestrator:
    """
    Escalation workflow orchestrator with state machine and timeout handling.

    State machine:
    PENDING → NOTIFIED → WAITING → APPROVED/REJECTED/TIMED_OUT

    Features:
    - Automatic notification delivery to approvers
    - Timeout monitoring with auto-escalation
    - MFA verification for approvals
    - Retry logic with exponential backoff
    """

    VALID_TRANSITIONS = {
        EscalationStatus.PENDING: [EscalationStatus.NOTIFIED, EscalationStatus.TIMED_OUT],
        EscalationStatus.NOTIFIED: [EscalationStatus.WAITING, EscalationStatus.ASSIGNED, EscalationStatus.TIMED_OUT],
        EscalationStatus.WAITING: [EscalationStatus.APPROVED, EscalationStatus.REJECTED, EscalationStatus.TIMED_OUT],
        EscalationStatus.ASSIGNED: [EscalationStatus.IN_REVIEW, EscalationStatus.TIMED_OUT],
        EscalationStatus.IN_REVIEW: [EscalationStatus.APPROVED, EscalationStatus.REJECTED, EscalationStatus.TIMED_OUT],
        EscalationStatus.APPROVED: [],
        EscalationStatus.REJECTED: [],
        EscalationStatus.TIMED_OUT: [],
    }

    def __init__(
        self,
        l01_bridge: L08Bridge,
        l10_bridge: L10Bridge,
        audit_manager: AuditManager,
        config: SupervisionConfiguration
    ):
        """
        Initialize Escalation Orchestrator.

        Args:
            l01_bridge: L01 bridge for persistence
            l10_bridge: L10 bridge for notifications
            audit_manager: Audit manager for logging
            config: Supervision configuration
        """
        self.l01 = l01_bridge
        self.l10 = l10_bridge
        self.audit = audit_manager
        self.config = config

        # In-memory workflow cache
        self._workflows: Dict[str, EscalationWorkflow] = {}

        # Timeout monitoring tasks
        self._timeout_tasks: Dict[str, asyncio.Task] = {}

        # Metrics
        self._created_count: int = 0
        self._approved_count: int = 0
        self._rejected_count: int = 0
        self._timeout_count: int = 0

        logger.info("EscalationOrchestrator initialized")

    async def initialize(self) -> None:
        """Initialize escalation orchestrator"""
        await self.l10.initialize()
        logger.info("EscalationOrchestrator ready")

    async def create_escalation(
        self,
        decision_id: str,
        reason: str,
        context: Dict[str, Any],
        approvers: List[str],
        priority: int = 1
    ) -> Tuple[Optional[EscalationWorkflow], Optional[str]]:
        """
        Create a new escalation workflow.

        Args:
            decision_id: Policy decision ID that triggered escalation
            reason: Reason for escalation
            context: Additional context for approvers
            approvers: List of approver user IDs
            priority: Priority level (1=normal, 2=high, 3=urgent)

        Returns:
            Tuple of (workflow, error message)
        """
        try:
            # Create workflow
            workflow = EscalationWorkflow(
                decision_id=decision_id,
                reason=reason,
                context=context,
                status=EscalationStatus.PENDING,
                escalation_level=1,
                approvers=approvers,
                created_at=datetime.utcnow(),
                timeout_at=datetime.utcnow() + timedelta(seconds=self.config.escalation_timeout_seconds),
            )

            # Persist to L01
            success = await self.l01.create_escalation(workflow.to_dict())
            if not success:
                return None, f"{ErrorCodes.ESCALATION_WORKFLOW_FAILED.value}: Failed to create escalation"

            # Store in cache
            self._workflows[workflow.workflow_id] = workflow
            self._created_count += 1

            # Start timeout monitoring
            self._timeout_tasks[workflow.workflow_id] = asyncio.create_task(
                self._monitor_timeout(workflow.workflow_id)
            )

            # Send notifications (async, don't block)
            asyncio.create_task(self._notify_approvers(workflow, priority))

            # Log to audit
            await self.audit.log_escalation_created(
                workflow_id=workflow.workflow_id,
                decision_id=decision_id,
                reason=reason,
                approvers=approvers,
            )

            logger.info(
                f"Created escalation {workflow.workflow_id} "
                f"(decision={decision_id}, approvers={len(approvers)})"
            )

            return workflow, None

        except Exception as e:
            logger.error(f"Failed to create escalation: {e}")
            return None, str(e)

    async def resolve(
        self,
        workflow_id: str,
        approved: bool,
        approver_id: str,
        notes: str = "",
        mfa_token: Optional[str] = None
    ) -> Tuple[Optional[EscalationWorkflow], Optional[str]]:
        """
        Resolve an escalation with approval or rejection.

        Args:
            workflow_id: Workflow ID to resolve
            approved: Whether to approve or reject
            approver_id: ID of the approving user
            notes: Resolution notes
            mfa_token: MFA token for verification (if required)

        Returns:
            Tuple of (resolved workflow, error message)
        """
        try:
            # Get workflow
            workflow = await self._get_workflow(workflow_id)
            if not workflow:
                return None, f"{ErrorCodes.ESCALATION_NOT_FOUND.value}: Workflow {workflow_id} not found"

            # Check if already resolved
            if workflow.status in [EscalationStatus.APPROVED, EscalationStatus.REJECTED, EscalationStatus.TIMED_OUT]:
                return None, f"{ErrorCodes.ESCALATION_ALREADY_RESOLVED.value}: Workflow already resolved"

            # Verify MFA if required
            if self.config.require_mfa_for_approval:
                if not mfa_token:
                    return None, f"{ErrorCodes.ESCALATION_MFA_REQUIRED.value}: MFA verification required"

                mfa_valid = await self.l10.verify_mfa(
                    user_id=approver_id,
                    mfa_token=mfa_token,
                    escalation_id=workflow_id
                )
                if not mfa_valid:
                    return None, f"{ErrorCodes.ESCALATION_MFA_FAILED.value}: MFA verification failed"

                workflow.mfa_verified = True

            # Cancel timeout task
            if workflow_id in self._timeout_tasks:
                self._timeout_tasks[workflow_id].cancel()
                del self._timeout_tasks[workflow_id]

            # Update workflow
            workflow.status = EscalationStatus.APPROVED if approved else EscalationStatus.REJECTED
            workflow.resolved_at = datetime.utcnow()
            workflow.resolved_by = approver_id
            workflow.resolution_notes = notes

            # Persist update
            await self.l01.update_escalation(workflow_id, {
                "status": workflow.status.value,
                "resolved_at": workflow.resolved_at.isoformat(),
                "resolved_by": approver_id,
                "resolution_notes": notes,
                "mfa_verified": workflow.mfa_verified,
            })

            # Update metrics
            if approved:
                self._approved_count += 1
            else:
                self._rejected_count += 1

            # Log to audit
            await self.audit.log_escalation_resolved(
                workflow_id=workflow_id,
                approved=approved,
                resolved_by=approver_id,
                mfa_verified=workflow.mfa_verified,
            )

            # Notify resolution
            await self.l10.send_escalation_resolved(
                escalation_id=workflow_id,
                approved=approved,
                resolved_by=approver_id,
                notes=notes,
            )

            logger.info(
                f"Escalation {workflow_id} resolved: "
                f"{'approved' if approved else 'rejected'} by {approver_id}"
            )

            return workflow, None

        except Exception as e:
            logger.error(f"Failed to resolve escalation: {e}")
            return None, str(e)

    async def assign(
        self,
        workflow_id: str,
        assignee_id: str
    ) -> Tuple[Optional[EscalationWorkflow], Optional[str]]:
        """
        Assign an escalation to a specific approver.

        Args:
            workflow_id: Workflow ID to assign
            assignee_id: User ID to assign to

        Returns:
            Tuple of (updated workflow, error message)
        """
        try:
            workflow = await self._get_workflow(workflow_id)
            if not workflow:
                return None, f"{ErrorCodes.ESCALATION_NOT_FOUND.value}: Workflow {workflow_id} not found"

            # Validate state transition
            if not self._is_valid_transition(workflow.status, EscalationStatus.ASSIGNED):
                return None, f"{ErrorCodes.ESCALATION_INVALID_STATE.value}: Cannot assign from state {workflow.status.value}"

            workflow.assigned_to = assignee_id
            workflow.status = EscalationStatus.ASSIGNED

            await self.l01.update_escalation(workflow_id, {
                "assigned_to": assignee_id,
                "status": workflow.status.value,
            })

            logger.info(f"Escalation {workflow_id} assigned to {assignee_id}")
            return workflow, None

        except Exception as e:
            logger.error(f"Failed to assign escalation: {e}")
            return None, str(e)

    async def _monitor_timeout(self, workflow_id: str) -> None:
        """
        Background task to monitor escalation timeout.

        Handles:
        - Auto-escalation to manager level
        - Timeout notification
        - Final timeout (auto-reject)
        """
        try:
            workflow = await self._get_workflow(workflow_id)
            if not workflow:
                return

            # Calculate sleep time
            timeout_seconds = (workflow.timeout_at - datetime.utcnow()).total_seconds()

            if timeout_seconds > 0:
                # Send reminder at 50% and 80% of timeout
                reminder_50 = timeout_seconds * 0.5
                reminder_80 = timeout_seconds * 0.8

                await asyncio.sleep(reminder_50)

                # Check if still pending
                workflow = await self._get_workflow(workflow_id)
                if workflow and workflow.status in [EscalationStatus.PENDING, EscalationStatus.NOTIFIED, EscalationStatus.WAITING]:
                    await self.l10.send_escalation_reminder(
                        escalation_id=workflow_id,
                        approvers=workflow.approvers,
                        time_remaining_seconds=int(timeout_seconds * 0.5),
                    )

                await asyncio.sleep(reminder_80 - reminder_50)

                # Check again
                workflow = await self._get_workflow(workflow_id)
                if workflow and workflow.status in [EscalationStatus.PENDING, EscalationStatus.NOTIFIED, EscalationStatus.WAITING]:
                    await self.l10.send_escalation_reminder(
                        escalation_id=workflow_id,
                        approvers=workflow.approvers,
                        time_remaining_seconds=int(timeout_seconds * 0.2),
                    )

                await asyncio.sleep(timeout_seconds * 0.2)

            # Final timeout check
            workflow = await self._get_workflow(workflow_id)
            if workflow and workflow.status in [EscalationStatus.PENDING, EscalationStatus.NOTIFIED, EscalationStatus.WAITING]:
                if workflow.escalation_level < self.config.max_escalation_level:
                    # Escalate to next level
                    await self._escalate_to_manager(workflow)
                else:
                    # Max level reached - auto-timeout
                    await self._auto_timeout(workflow)

        except asyncio.CancelledError:
            logger.debug(f"Timeout monitoring cancelled for {workflow_id}")
        except Exception as e:
            logger.error(f"Timeout monitoring error for {workflow_id}: {e}")

    async def _escalate_to_manager(self, workflow: EscalationWorkflow) -> None:
        """Escalate to next management level"""
        logger.warning(
            f"Escalating {workflow.workflow_id} to level {workflow.escalation_level + 1}"
        )

        workflow.escalation_level += 1
        workflow.timeout_at = datetime.utcnow() + timedelta(seconds=self.config.escalation_timeout_seconds)

        await self.l01.update_escalation(workflow.workflow_id, {
            "escalation_level": workflow.escalation_level,
            "timeout_at": workflow.timeout_at.isoformat(),
        })

        # Send escalation notification
        await self.l10.send_escalation_notification(
            escalation_id=workflow.workflow_id,
            approvers=workflow.approvers,  # In production, would get manager list
            reason=f"Escalated to level {workflow.escalation_level}: {workflow.reason}",
            context={**workflow.context, "escalation_level": workflow.escalation_level},
            priority=min(3, workflow.escalation_level + 1),  # Increase priority
        )

        # Restart timeout monitoring
        self._timeout_tasks[workflow.workflow_id] = asyncio.create_task(
            self._monitor_timeout(workflow.workflow_id)
        )

    async def _auto_timeout(self, workflow: EscalationWorkflow) -> None:
        """Handle final timeout (auto-reject)"""
        logger.warning(f"Escalation {workflow.workflow_id} timed out")

        workflow.status = EscalationStatus.TIMED_OUT
        workflow.resolved_at = datetime.utcnow()
        workflow.resolution_notes = "Automatically timed out after maximum escalation level"

        await self.l01.update_escalation(workflow.workflow_id, {
            "status": workflow.status.value,
            "resolved_at": workflow.resolved_at.isoformat(),
            "resolution_notes": workflow.resolution_notes,
        })

        self._timeout_count += 1

        # Log to audit
        await self.audit.log_action(
            action="escalation_timeout",
            actor_id="system",
            actor_type="system",
            resource_type="escalation",
            resource_id=workflow.workflow_id,
            details={
                "escalation_level": workflow.escalation_level,
                "max_level": self.config.max_escalation_level,
            }
        )

    async def _notify_approvers(self, workflow: EscalationWorkflow, priority: int) -> None:
        """Send notifications to approvers with retry"""
        for attempt in range(self.config.escalation_retry_count):
            try:
                success = await self.l10.send_escalation_notification(
                    escalation_id=workflow.workflow_id,
                    approvers=workflow.approvers,
                    reason=workflow.reason,
                    context=workflow.context,
                    priority=priority,
                )

                if success:
                    workflow.status = EscalationStatus.NOTIFIED
                    workflow.notified_at = datetime.utcnow()

                    await self.l01.update_escalation(workflow.workflow_id, {
                        "status": workflow.status.value,
                        "notified_at": workflow.notified_at.isoformat(),
                    })

                    logger.info(f"Notified approvers for escalation {workflow.workflow_id}")
                    return

            except Exception as e:
                logger.warning(
                    f"Notification attempt {attempt + 1} failed for {workflow.workflow_id}: {e}"
                )
                await asyncio.sleep(self.config.escalation_retry_delay_seconds * (2 ** attempt))

        logger.error(f"Failed to notify approvers for {workflow.workflow_id} after all retries")

    async def _get_workflow(self, workflow_id: str) -> Optional[EscalationWorkflow]:
        """Get workflow from cache or L01"""
        if workflow_id in self._workflows:
            return self._workflows[workflow_id]

        data = await self.l01.get_escalation(workflow_id)
        if not data:
            return None

        workflow = self._dict_to_workflow(data)
        self._workflows[workflow_id] = workflow
        return workflow

    def _dict_to_workflow(self, data: Dict[str, Any]) -> EscalationWorkflow:
        """Convert dictionary to EscalationWorkflow"""
        return EscalationWorkflow(
            workflow_id=data.get("workflow_id", ""),
            decision_id=data.get("decision_id", ""),
            status=EscalationStatus(data.get("status", "PENDING")),
            escalation_level=data.get("escalation_level", 1),
            reason=data.get("reason", ""),
            context=data.get("context", {}),
            approvers=data.get("approvers", []),
            assigned_to=data.get("assigned_to"),
            resolution_notes=data.get("resolution_notes", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            notified_at=datetime.fromisoformat(data["notified_at"]) if data.get("notified_at") else None,
            timeout_at=datetime.fromisoformat(data["timeout_at"]) if data.get("timeout_at") else None,
            resolved_at=datetime.fromisoformat(data["resolved_at"]) if data.get("resolved_at") else None,
            resolved_by=data.get("resolved_by"),
            mfa_verified=data.get("mfa_verified", False),
        )

    def _is_valid_transition(
        self,
        current: EscalationStatus,
        target: EscalationStatus
    ) -> bool:
        """Check if state transition is valid"""
        return target in self.VALID_TRANSITIONS.get(current, [])

    async def get_pending_escalations(self) -> List[EscalationWorkflow]:
        """Get all pending escalations"""
        data_list = await self.l01.get_pending_escalations()
        return [self._dict_to_workflow(d) for d in data_list]

    async def get_escalation(self, workflow_id: str) -> Optional[EscalationWorkflow]:
        """Get a specific escalation"""
        return await self._get_workflow(workflow_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get escalation statistics"""
        return {
            "created_count": self._created_count,
            "approved_count": self._approved_count,
            "rejected_count": self._rejected_count,
            "timeout_count": self._timeout_count,
            "pending_count": len([w for w in self._workflows.values()
                                  if w.status in [EscalationStatus.PENDING, EscalationStatus.NOTIFIED, EscalationStatus.WAITING]]),
            "active_timeout_tasks": len(self._timeout_tasks),
        }

    async def health_check(self) -> Dict[str, Any]:
        """Health check for escalation orchestrator"""
        l10_health = await self.l10.health_check()
        return {
            "status": "healthy" if l10_health.get("status") == "healthy" else "degraded",
            "l10": l10_health,
            "stats": self.get_stats(),
        }

    async def cleanup(self) -> None:
        """Cleanup resources"""
        # Cancel all timeout tasks
        for task in self._timeout_tasks.values():
            task.cancel()
        self._timeout_tasks.clear()
        logger.info("EscalationOrchestrator cleanup complete")

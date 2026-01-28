"""
L08 Supervision Layer - Escalation Routes

REST API for managing escalation workflows.
"""

import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel, Field

from ..models.domain import EscalationStatus
from ..models.error_codes import ErrorCodes

logger = logging.getLogger(__name__)

router = APIRouter()


class CreateEscalationRequest(BaseModel):
    """Request to create an escalation"""
    decision_id: str = Field(..., description="Associated policy decision ID")
    reason: str = Field(..., description="Reason for escalation")
    context: Dict[str, Any] = Field(default_factory=dict, description="Context for approvers")
    approvers: List[str] = Field(default_factory=list, description="List of approver IDs")


class EscalationResponse(BaseModel):
    """Escalation workflow response"""
    workflow_id: str
    decision_id: str
    status: str
    reason: str
    escalation_level: int
    approvers: List[str]
    assigned_to: Optional[str] = None
    created_at: str
    timeout_at: Optional[str] = None
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None


class ResolveEscalationRequest(BaseModel):
    """Request to resolve an escalation"""
    approver_id: str = Field(..., description="ID of the approver")
    notes: str = Field(default="", description="Resolution notes")
    mfa_token: Optional[str] = Field(None, description="MFA token for verification")


@router.post("/escalations", response_model=EscalationResponse)
async def create_escalation(
    request: Request,
    escalation: CreateEscalationRequest
):
    """
    Create a new escalation workflow.

    This manually triggers an escalation for human review.
    Escalations are also created automatically when a policy
    returns an ESCALATE verdict.
    """
    service = request.app.state.supervision_service

    try:
        workflow, error = await service.create_escalation(
            decision_id=escalation.decision_id,
            reason=escalation.reason,
            context=escalation.context,
            approvers=escalation.approvers,
        )

        if error:
            logger.error(f"Failed to create escalation: {error}")
            raise HTTPException(status_code=400, detail=error)

        logger.info(f"Created escalation: {workflow.workflow_id}")

        return EscalationResponse(
            workflow_id=workflow.workflow_id,
            decision_id=workflow.decision_id,
            status=workflow.status.value,
            reason=workflow.reason,
            escalation_level=workflow.escalation_level,
            approvers=workflow.approvers,
            assigned_to=workflow.assigned_to,
            created_at=workflow.created_at.isoformat(),
            timeout_at=workflow.timeout_at.isoformat() if workflow.timeout_at else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Create escalation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"{ErrorCodes.ESCALATION_WORKFLOW_FAILED.value}: {str(e)}"
        )


@router.get("/escalations", response_model=List[EscalationResponse])
async def list_escalations(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by status"),
    approver_id: Optional[str] = Query(None, description="Filter by approver"),
    limit: int = Query(100, ge=1, le=1000),
):
    """
    List escalation workflows with optional filtering.
    """
    service = request.app.state.supervision_service

    try:
        # Get pending escalations (could be extended to support more filters)
        workflows = await service.get_pending_escalations()

        # Apply status filter
        if status:
            try:
                status_enum = EscalationStatus(status)
                workflows = [w for w in workflows if w.status == status_enum]
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {status}"
                )

        # Apply approver filter
        if approver_id:
            workflows = [w for w in workflows if approver_id in w.approvers]

        # Apply limit
        workflows = workflows[:limit]

        return [
            EscalationResponse(
                workflow_id=w.workflow_id,
                decision_id=w.decision_id,
                status=w.status.value,
                reason=w.reason,
                escalation_level=w.escalation_level,
                approvers=w.approvers,
                assigned_to=w.assigned_to,
                created_at=w.created_at.isoformat(),
                timeout_at=w.timeout_at.isoformat() if w.timeout_at else None,
                resolved_at=w.resolved_at.isoformat() if w.resolved_at else None,
                resolved_by=w.resolved_by,
                resolution_notes=w.resolution_notes,
            )
            for w in workflows
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"List escalations error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"{ErrorCodes.ESCALATION_WORKFLOW_FAILED.value}: {str(e)}"
        )


@router.get("/escalations/{workflow_id}", response_model=EscalationResponse)
async def get_escalation(
    request: Request,
    workflow_id: str
):
    """
    Get a specific escalation workflow by ID.
    """
    service = request.app.state.supervision_service

    try:
        workflow = await service.escalation_orchestrator.get_escalation(workflow_id)
        if not workflow:
            raise HTTPException(
                status_code=404,
                detail=f"{ErrorCodes.ESCALATION_NOT_FOUND.value}: Workflow {workflow_id} not found"
            )

        return EscalationResponse(
            workflow_id=workflow.workflow_id,
            decision_id=workflow.decision_id,
            status=workflow.status.value,
            reason=workflow.reason,
            escalation_level=workflow.escalation_level,
            approvers=workflow.approvers,
            assigned_to=workflow.assigned_to,
            created_at=workflow.created_at.isoformat(),
            timeout_at=workflow.timeout_at.isoformat() if workflow.timeout_at else None,
            resolved_at=workflow.resolved_at.isoformat() if workflow.resolved_at else None,
            resolved_by=workflow.resolved_by,
            resolution_notes=workflow.resolution_notes,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Get escalation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"{ErrorCodes.ESCALATION_WORKFLOW_FAILED.value}: {str(e)}"
        )


@router.post("/escalations/{workflow_id}/approve", response_model=EscalationResponse)
async def approve_escalation(
    request: Request,
    workflow_id: str,
    resolution: ResolveEscalationRequest
):
    """
    Approve an escalation workflow.

    MFA verification may be required based on configuration.
    """
    service = request.app.state.supervision_service

    try:
        workflow, error = await service.resolve_escalation(
            workflow_id=workflow_id,
            approved=True,
            approver_id=resolution.approver_id,
            notes=resolution.notes,
            mfa_token=resolution.mfa_token,
        )

        if error:
            logger.error(f"Failed to approve escalation: {error}")
            raise HTTPException(status_code=400, detail=error)

        logger.info(f"Approved escalation: {workflow_id} by {resolution.approver_id}")

        return EscalationResponse(
            workflow_id=workflow.workflow_id,
            decision_id=workflow.decision_id,
            status=workflow.status.value,
            reason=workflow.reason,
            escalation_level=workflow.escalation_level,
            approvers=workflow.approvers,
            assigned_to=workflow.assigned_to,
            created_at=workflow.created_at.isoformat(),
            timeout_at=workflow.timeout_at.isoformat() if workflow.timeout_at else None,
            resolved_at=workflow.resolved_at.isoformat() if workflow.resolved_at else None,
            resolved_by=workflow.resolved_by,
            resolution_notes=workflow.resolution_notes,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Approve escalation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"{ErrorCodes.ESCALATION_WORKFLOW_FAILED.value}: {str(e)}"
        )


@router.post("/escalations/{workflow_id}/reject", response_model=EscalationResponse)
async def reject_escalation(
    request: Request,
    workflow_id: str,
    resolution: ResolveEscalationRequest
):
    """
    Reject an escalation workflow.

    A rejection reason should be provided in the notes field.
    """
    service = request.app.state.supervision_service

    try:
        if not resolution.notes:
            raise HTTPException(
                status_code=400,
                detail=f"{ErrorCodes.ESCALATION_INVALID_STATE.value}: Rejection reason is required"
            )

        workflow, error = await service.resolve_escalation(
            workflow_id=workflow_id,
            approved=False,
            approver_id=resolution.approver_id,
            notes=resolution.notes,
            mfa_token=resolution.mfa_token,
        )

        if error:
            logger.error(f"Failed to reject escalation: {error}")
            raise HTTPException(status_code=400, detail=error)

        logger.info(f"Rejected escalation: {workflow_id} by {resolution.approver_id}")

        return EscalationResponse(
            workflow_id=workflow.workflow_id,
            decision_id=workflow.decision_id,
            status=workflow.status.value,
            reason=workflow.reason,
            escalation_level=workflow.escalation_level,
            approvers=workflow.approvers,
            assigned_to=workflow.assigned_to,
            created_at=workflow.created_at.isoformat(),
            timeout_at=workflow.timeout_at.isoformat() if workflow.timeout_at else None,
            resolved_at=workflow.resolved_at.isoformat() if workflow.resolved_at else None,
            resolved_by=workflow.resolved_by,
            resolution_notes=workflow.resolution_notes,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Reject escalation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"{ErrorCodes.ESCALATION_WORKFLOW_FAILED.value}: {str(e)}"
        )


@router.get("/escalations/pending/count")
async def get_pending_count(
    request: Request,
    approver_id: Optional[str] = Query(None, description="Filter by approver")
):
    """
    Get count of pending escalations.

    Useful for dashboard widgets and notifications.
    """
    service = request.app.state.supervision_service

    try:
        workflows = await service.get_pending_escalations()

        if approver_id:
            workflows = [w for w in workflows if approver_id in w.approvers]

        return {
            "pending_count": len(workflows),
            "approver_id": approver_id,
        }

    except Exception as e:
        logger.exception(f"Get pending count error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"{ErrorCodes.ESCALATION_WORKFLOW_FAILED.value}: {str(e)}"
        )

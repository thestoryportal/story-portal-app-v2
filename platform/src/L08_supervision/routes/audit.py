"""
L08 Supervision Layer - Audit Routes

REST API for querying and verifying the audit trail.
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel, Field

from ..models.error_codes import ErrorCodes

logger = logging.getLogger(__name__)

router = APIRouter()


class AuditEntryResponse(BaseModel):
    """Audit entry response"""
    entry_id: str
    timestamp: str
    action: str
    actor_id: str
    actor_type: str
    resource_type: str
    resource_id: str
    outcome: str
    details: dict
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    signature: str
    previous_hash: str


class AuditQueryResponse(BaseModel):
    """Response from audit query"""
    entries: List[AuditEntryResponse]
    total_count: int
    offset: int
    limit: int


class AuditVerifyResponse(BaseModel):
    """Response from audit chain verification"""
    valid: bool
    entries_verified: int
    errors: List[str]


@router.get("/audit/search", response_model=AuditQueryResponse)
async def search_audit_log(
    request: Request,
    actor_id: Optional[str] = Query(None, description="Filter by actor ID"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    correlation_id: Optional[str] = Query(None, description="Filter by correlation ID"),
    start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time (ISO format)"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """
    Search the audit log with filters.

    Returns audit entries matching the specified criteria.
    """
    service = request.app.state.supervision_service

    try:
        entries, error = await service.query_audit_log(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            limit=limit,
        )

        if error:
            logger.error(f"Audit query failed: {error}")
            raise HTTPException(status_code=400, detail=error)

        # Apply additional filters that aren't in the base query
        filtered = entries
        if resource_id:
            filtered = [e for e in filtered if e.resource_id == resource_id]
        if correlation_id:
            filtered = [e for e in filtered if e.correlation_id == correlation_id]

        # Apply pagination
        total_count = len(filtered)
        filtered = filtered[offset:offset + limit]

        response_entries = [
            AuditEntryResponse(
                entry_id=e.entry_id,
                timestamp=e.timestamp.isoformat(),
                action=e.action,
                actor_id=e.actor_id,
                actor_type=e.actor_type,
                resource_type=e.resource_type,
                resource_id=e.resource_id,
                outcome=e.outcome,
                details=e.details,
                correlation_id=e.correlation_id,
                session_id=e.session_id,
                ip_address=e.ip_address,
                signature=e.signature,
                previous_hash=e.previous_hash,
            )
            for e in filtered
        ]

        return AuditQueryResponse(
            entries=response_entries,
            total_count=total_count,
            offset=offset,
            limit=limit,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Audit search error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"{ErrorCodes.AUDIT_QUERY_FAILED.value}: {str(e)}"
        )


@router.get("/audit/stats")
async def get_audit_stats(
    request: Request,
    period_hours: int = Query(24, ge=1, le=720, description="Time period for stats")
):
    """
    Get audit trail statistics.

    Returns counts and summaries of audit activity.
    """
    service = request.app.state.supervision_service

    try:
        stats = service.audit_manager.get_stats()

        # Query recent entries for additional stats
        entries, _ = await service.query_audit_log(limit=1000)

        # Count by action type
        action_counts = {}
        for entry in entries:
            action_counts[entry.action] = action_counts.get(entry.action, 0) + 1

        # Count by actor
        actor_counts = {}
        for entry in entries:
            actor_counts[entry.actor_id] = actor_counts.get(entry.actor_id, 0) + 1

        # Count by outcome
        outcome_counts = {}
        for entry in entries:
            outcome_counts[entry.outcome] = outcome_counts.get(entry.outcome, 0) + 1

        return {
            "total_entries": stats.get("total_entries", 0),
            "signed_entries": stats.get("signed_entries", 0),
            "chain_length": stats.get("chain_length", 0),
            "period_hours": period_hours,
            "action_counts": action_counts,
            "actor_counts": actor_counts,
            "outcome_counts": outcome_counts,
        }

    except Exception as e:
        logger.exception(f"Audit stats error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"{ErrorCodes.AUDIT_QUERY_FAILED.value}: {str(e)}"
        )


@router.get("/audit/timeline")
async def get_audit_timeline(
    request: Request,
    correlation_id: str = Query(..., description="Correlation ID to trace"),
):
    """
    Get audit timeline for a correlation ID.

    Returns all audit entries related to a specific request or workflow.
    """
    service = request.app.state.supervision_service

    try:
        entries, error = await service.query_audit_log(limit=1000)
        if error:
            raise HTTPException(status_code=400, detail=error)

        # Filter by correlation ID
        timeline = [
            {
                "entry_id": e.entry_id,
                "timestamp": e.timestamp.isoformat(),
                "action": e.action,
                "actor_id": e.actor_id,
                "resource_type": e.resource_type,
                "resource_id": e.resource_id,
                "outcome": e.outcome,
            }
            for e in entries
            if e.correlation_id == correlation_id
        ]

        # Sort by timestamp
        timeline.sort(key=lambda x: x["timestamp"])

        return {
            "correlation_id": correlation_id,
            "entry_count": len(timeline),
            "timeline": timeline,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Audit timeline error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"{ErrorCodes.AUDIT_QUERY_FAILED.value}: {str(e)}"
        )


@router.post("/audit/verify", response_model=AuditVerifyResponse)
async def verify_audit_chain(
    request: Request,
    start_entry_id: Optional[str] = Query(None, description="Start verification from this entry"),
    end_entry_id: Optional[str] = Query(None, description="End verification at this entry"),
):
    """
    Verify the integrity of the audit trail.

    Validates the cryptographic chain of audit entries to detect
    any tampering or corruption.
    """
    service = request.app.state.supervision_service

    try:
        valid, entries_verified, error = await service.verify_audit_chain()

        errors = []
        if error:
            errors.append(error)

        return AuditVerifyResponse(
            valid=valid,
            entries_verified=entries_verified,
            errors=errors,
        )

    except Exception as e:
        logger.exception(f"Audit verify error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"{ErrorCodes.AUDIT_QUERY_FAILED.value}: {str(e)}"
        )


# NOTE: This route MUST come LAST because {entry_id} is a catch-all path parameter
# that would otherwise match "stats", "timeline", "verify", etc.
@router.get("/audit/{entry_id}", response_model=AuditEntryResponse)
async def get_audit_entry(
    request: Request,
    entry_id: str
):
    """
    Get a specific audit entry by ID.
    """
    service = request.app.state.supervision_service

    try:
        # Query for the specific entry
        entries, error = await service.query_audit_log(limit=1000)
        if error:
            raise HTTPException(status_code=400, detail=error)

        # Find the entry
        entry = next((e for e in entries if e.entry_id == entry_id), None)
        if not entry:
            raise HTTPException(
                status_code=404,
                detail=f"{ErrorCodes.AUDIT_ENTRY_NOT_FOUND.value}: Audit entry {entry_id} not found"
            )

        return AuditEntryResponse(
            entry_id=entry.entry_id,
            timestamp=entry.timestamp.isoformat(),
            action=entry.action,
            actor_id=entry.actor_id,
            actor_type=entry.actor_type,
            resource_type=entry.resource_type,
            resource_id=entry.resource_id,
            outcome=entry.outcome,
            details=entry.details,
            correlation_id=entry.correlation_id,
            session_id=entry.session_id,
            ip_address=entry.ip_address,
            signature=entry.signature,
            previous_hash=entry.previous_hash,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Get audit entry error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"{ErrorCodes.AUDIT_QUERY_FAILED.value}: {str(e)}"
        )

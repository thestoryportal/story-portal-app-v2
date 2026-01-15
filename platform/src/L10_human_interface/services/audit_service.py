"""
L10 Human Interface Layer - Audit Service

Log and query audit trail.
"""

import logging
import uuid
from datetime import datetime, UTC

from ..models import AuditEntry, AuditQuery, AuditResponse, AuditAction, AuditStatus, ErrorCode, InterfaceError

logger = logging.getLogger(__name__)


class AuditService:
    """Audit service for logging control actions."""

    def __init__(self, audit_logger=None):
        self.audit_logger = audit_logger

    async def log_action(
        self,
        actor: str,
        action: AuditAction,
        resource_type: str,
        resource_id: str,
        tenant_id: str,
        actor_ip: str = None,
        reason: str = None,
        change_delta: dict = None,
    ) -> AuditEntry:
        """Log audit action."""
        try:
            entry = AuditEntry(
                audit_id=str(uuid.uuid4()),
                actor=actor,
                actor_ip=actor_ip,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                change_delta=change_delta,
                reason=reason,
                timestamp=datetime.now(UTC),
                status=AuditStatus.SUCCESS,
                tenant_id=tenant_id,
            )

            # Log to L06 AuditLogger
            if self.audit_logger:
                await self.audit_logger.log(event_type=action.value, data=entry.to_dict())

            return entry

        except Exception as e:
            logger.error(f"Audit log failed: {e}")
            raise InterfaceError.from_code(ErrorCode.E10502, details={"error": str(e)})

    async def query_audit_trail(self, query: AuditQuery) -> AuditResponse:
        """Query audit trail."""
        try:
            # Placeholder: Query from L06
            return AuditResponse(entries=[], total=0, limit=query.limit, offset=query.offset, has_more=False)

        except Exception as e:
            logger.error(f"Audit query failed: {e}")
            raise InterfaceError.from_code(ErrorCode.E10501, details={"error": str(e)})

"""
L10 Human Interface Layer - Audit Models

Models for audit trail logging and querying.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any
from enum import Enum


class AuditAction(str, Enum):
    """Audit action types."""
    PAUSE_AGENT = "pause_agent"
    RESUME_AGENT = "resume_agent"
    STOP_AGENT = "stop_agent"
    EMERGENCY_STOP = "emergency_stop"
    UPDATE_QUOTA = "update_quota"
    ACKNOWLEDGE_ALERT = "acknowledge_alert"
    SNOOZE_ALERT = "snooze_alert"
    DASHBOARD_VIEW = "dashboard_view"
    EVENT_QUERY = "event_query"


class AuditStatus(str, Enum):
    """Audit entry status."""
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass
class AuditEntry:
    """Audit trail entry."""
    audit_id: str
    actor: str  # User ID or email
    actor_ip: Optional[str]
    action: AuditAction
    resource_type: str  # "agent", "workflow", "alert", etc.
    resource_id: str
    change_delta: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    status: AuditStatus = AuditStatus.SUCCESS
    error_message: Optional[str] = None
    tenant_id: Optional[str] = None
    request_id: Optional[str] = None
    mfa_required: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "audit_id": self.audit_id,
            "actor": self.actor,
            "actor_ip": self.actor_ip,
            "action": self.action.value if isinstance(self.action, AuditAction) else self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "change_delta": self.change_delta,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value if isinstance(self.status, AuditStatus) else self.status,
            "error_message": self.error_message,
            "tenant_id": self.tenant_id,
            "request_id": self.request_id,
            "mfa_required": self.mfa_required,
            "metadata": self.metadata,
        }


@dataclass
class AuditQuery:
    """Query for audit trail."""
    actor: Optional[str] = None
    action: Optional[AuditAction] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    tenant_id: Optional[str] = None
    limit: int = 100
    offset: int = 0


@dataclass
class AuditResponse:
    """Response with audit entries."""
    entries: List[AuditEntry]
    total: int
    limit: int
    offset: int
    has_more: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entries": [entry.to_dict() for entry in self.entries],
            "total": self.total,
            "limit": self.limit,
            "offset": self.offset,
            "has_more": self.has_more,
        }

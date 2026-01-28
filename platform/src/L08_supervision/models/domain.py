"""
L08 Supervision Layer - Domain Models

Core domain models for policy management, constraint enforcement,
anomaly detection, escalation workflows, and audit trails.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4
from collections import deque


class PolicyVerdict(str, Enum):
    """Policy evaluation verdict"""
    ALLOW = "ALLOW"
    DENY = "DENY"
    ESCALATE = "ESCALATE"


class AnomalySeverity(str, Enum):
    """Anomaly severity levels"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class EscalationStatus(str, Enum):
    """Escalation workflow status"""
    PENDING = "PENDING"
    NOTIFIED = "NOTIFIED"
    WAITING = "WAITING"
    ASSIGNED = "ASSIGNED"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    TIMED_OUT = "TIMED_OUT"


class ConstraintType(str, Enum):
    """Types of constraints"""
    RATE_LIMIT = "RATE_LIMIT"
    QUOTA = "QUOTA"
    RESOURCE_CAP = "RESOURCE_CAP"
    OPERATION_RESTRICTION = "OPERATION_RESTRICTION"
    TEMPORAL = "TEMPORAL"


# =============================================================================
# Policy Models
# =============================================================================

@dataclass
class PolicyRule:
    """Individual policy rule with condition and action"""
    rule_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    condition: str = ""  # Expression to evaluate (e.g., "agent.team == 'datascience'")
    action: PolicyVerdict = PolicyVerdict.ALLOW
    priority: int = 0  # Higher priority rules evaluated first
    enabled: bool = True
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "condition": self.condition,
            "action": self.action.value,
            "priority": self.priority,
            "enabled": self.enabled,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class PolicyDefinition:
    """Complete policy definition with versioning"""
    policy_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    rules: List[PolicyRule] = field(default_factory=list)
    scope: str = "global"  # global, department, team, agent
    scope_id: Optional[str] = None  # ID of department/team/agent if scoped
    active: bool = False  # Whether this policy is deployed
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "rules": [r.to_dict() for r in self.rules],
            "scope": self.scope,
            "scope_id": self.scope_id,
            "active": self.active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "metadata": self.metadata,
        }


@dataclass
class PolicyDecision:
    """Record of policy evaluation decision"""
    decision_id: str = field(default_factory=lambda: str(uuid4()))
    agent_id: str = ""
    request_context: Dict[str, Any] = field(default_factory=dict)
    verdict: PolicyVerdict = PolicyVerdict.ALLOW
    matched_rules: List[str] = field(default_factory=list)
    explanation: str = ""
    confidence: float = 1.0
    evaluation_latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    audit_event_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "agent_id": self.agent_id,
            "request_context": self.request_context,
            "verdict": self.verdict.value,
            "matched_rules": self.matched_rules,
            "explanation": self.explanation,
            "confidence": self.confidence,
            "evaluation_latency_ms": self.evaluation_latency_ms,
            "timestamp": self.timestamp.isoformat(),
            "audit_event_id": self.audit_event_id,
        }


# =============================================================================
# Constraint Models
# =============================================================================

@dataclass
class TemporalConstraintConfig:
    """Configuration for temporal constraints"""
    business_hours_only: bool = False
    start_hour: int = 9  # UTC
    end_hour: int = 17  # UTC
    allowed_days: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])  # Mon-Fri
    timezone: str = "UTC"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "business_hours_only": self.business_hours_only,
            "start_hour": self.start_hour,
            "end_hour": self.end_hour,
            "allowed_days": self.allowed_days,
            "timezone": self.timezone,
        }


@dataclass
class Constraint:
    """Operational constraint definition"""
    constraint_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    constraint_type: ConstraintType = ConstraintType.RATE_LIMIT
    limit: float = 0.0
    window_seconds: int = 3600
    agent_id: Optional[str] = None  # None = global constraint
    scope: str = "global"  # global, department, team, agent
    temporal_config: Optional[TemporalConstraintConfig] = None
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "constraint_id": self.constraint_id,
            "name": self.name,
            "description": self.description,
            "constraint_type": self.constraint_type.value,
            "limit": self.limit,
            "window_seconds": self.window_seconds,
            "agent_id": self.agent_id,
            "scope": self.scope,
            "temporal_config": self.temporal_config.to_dict() if self.temporal_config else None,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class ConstraintViolation:
    """Record of constraint violation"""
    violation_id: str = field(default_factory=lambda: str(uuid4()))
    constraint_id: str = ""
    constraint_name: str = ""
    agent_id: str = ""
    current_usage: float = 0.0
    limit: float = 0.0
    violation_type: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "violation_id": self.violation_id,
            "constraint_id": self.constraint_id,
            "constraint_name": self.constraint_name,
            "agent_id": self.agent_id,
            "current_usage": self.current_usage,
            "limit": self.limit,
            "violation_type": self.violation_type,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


# =============================================================================
# Anomaly Detection Models
# =============================================================================

@dataclass
class BaselineStats:
    """Statistical baseline for anomaly detection"""
    values: deque = field(default_factory=lambda: deque(maxlen=1000))
    mean: float = 0.0
    std: float = 0.0
    q1: float = 0.0
    q3: float = 0.0
    min_val: float = 0.0
    max_val: float = 0.0
    sample_count: int = 0
    last_updated: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mean": self.mean,
            "std": self.std,
            "q1": self.q1,
            "q3": self.q3,
            "min_val": self.min_val,
            "max_val": self.max_val,
            "sample_count": self.sample_count,
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class Anomaly:
    """Detected behavioral anomaly"""
    anomaly_id: str = field(default_factory=lambda: str(uuid4()))
    agent_id: str = ""
    metric_name: str = ""
    anomaly_type: str = ""
    severity: AnomalySeverity = AnomalySeverity.MEDIUM
    description: str = ""
    baseline_value: float = 0.0
    observed_value: float = 0.0
    z_score: float = 0.0
    iqr_score: float = 0.0
    detection_method: str = ""  # "z_score", "iqr", "ensemble"
    confidence: float = 0.0
    detected_at: datetime = field(default_factory=datetime.utcnow)
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "anomaly_id": self.anomaly_id,
            "agent_id": self.agent_id,
            "metric_name": self.metric_name,
            "anomaly_type": self.anomaly_type,
            "severity": self.severity.value,
            "description": self.description,
            "baseline_value": self.baseline_value,
            "observed_value": self.observed_value,
            "z_score": self.z_score,
            "iqr_score": self.iqr_score,
            "detection_method": self.detection_method,
            "confidence": self.confidence,
            "detected_at": self.detected_at.isoformat(),
            "acknowledged": self.acknowledged,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
        }


# =============================================================================
# Escalation Models
# =============================================================================

@dataclass
class EscalationWorkflow:
    """Human-in-the-loop escalation workflow"""
    workflow_id: str = field(default_factory=lambda: str(uuid4()))
    decision_id: str = ""
    status: EscalationStatus = EscalationStatus.PENDING
    escalation_level: int = 1
    reason: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    approvers: List[str] = field(default_factory=list)
    assigned_to: Optional[str] = None
    resolution_notes: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    notified_at: Optional[datetime] = None
    timeout_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    mfa_verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "decision_id": self.decision_id,
            "status": self.status.value,
            "escalation_level": self.escalation_level,
            "reason": self.reason,
            "context": self.context,
            "approvers": self.approvers,
            "assigned_to": self.assigned_to,
            "resolution_notes": self.resolution_notes,
            "created_at": self.created_at.isoformat(),
            "notified_at": self.notified_at.isoformat() if self.notified_at else None,
            "timeout_at": self.timeout_at.isoformat() if self.timeout_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "mfa_verified": self.mfa_verified,
        }


# =============================================================================
# Audit Trail Models
# =============================================================================

@dataclass
class AuditEntry:
    """Immutable audit log entry with cryptographic signing"""
    audit_id: str = field(default_factory=lambda: str(uuid4()))
    action: str = ""
    actor_id: str = ""
    actor_type: str = "agent"  # agent, user, system
    resource_type: str = ""
    resource_id: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    parent_audit_id: Optional[str] = None  # For audit trail linking
    signature: str = ""  # Cryptographic signature (Vault ECDSA or HMAC)
    signature_algorithm: str = "HMAC-SHA256"  # "ECDSA-P256" for production
    timestamp: datetime = field(default_factory=datetime.utcnow)
    integrity_hash: str = ""  # SHA-256 of canonical entry

    def to_dict(self) -> Dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "action": self.action,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "parent_audit_id": self.parent_audit_id,
            "signature": self.signature,
            "signature_algorithm": self.signature_algorithm,
            "timestamp": self.timestamp.isoformat(),
            "integrity_hash": self.integrity_hash,
        }

    def canonical_json(self) -> str:
        """Return canonical JSON for signing (sorted keys, no whitespace)"""
        import json
        data = {
            "audit_id": self.audit_id,
            "action": self.action,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "parent_audit_id": self.parent_audit_id,
            "timestamp": self.timestamp.isoformat(),
        }
        return json.dumps(data, sort_keys=True, separators=(',', ':'))

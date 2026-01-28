"""
L08 Supervision Layer - Data Transfer Objects (DTOs)

Pydantic v2 models for HTTP request/response serialization.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import uuid4

from .domain import PolicyVerdict, ConstraintType, AnomalySeverity, EscalationStatus


# =============================================================================
# Policy DTOs
# =============================================================================

class PolicyRuleDTO(BaseModel):
    """Policy rule for API requests/responses"""
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None
    name: Optional[str] = None  # Alias for rule_name
    description: str = ""
    condition: str
    action: str = "ALLOW"  # String for API compatibility
    priority: int = 0
    enabled: bool = True
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context):
        # Support both 'name' and 'rule_name' fields
        if self.rule_name is None and self.name is not None:
            object.__setattr__(self, 'rule_name', self.name)
        elif self.name is None and self.rule_name is not None:
            object.__setattr__(self, 'name', self.rule_name)


class PolicyCreateRequest(BaseModel):
    """Request to create a new policy"""
    name: str
    description: str = ""
    version: str = "1.0.0"
    rules: List[PolicyRuleDTO]
    scope: str = "global"
    scope_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PolicyUpdateRequest(BaseModel):
    """Request to update an existing policy"""
    name: Optional[str] = None
    description: Optional[str] = None
    rules: Optional[List[PolicyRuleDTO]] = None
    metadata: Optional[Dict[str, Any]] = None


class PolicyResponse(BaseModel):
    """Policy response"""
    policy_id: str
    name: str
    description: str
    version: str
    rules: List[PolicyRuleDTO]
    scope: str
    scope_id: Optional[str]
    active: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    metadata: Dict[str, Any]


class PolicyListResponse(BaseModel):
    """List of policies response"""
    policies: List[PolicyResponse]
    total: int
    page: int = 1
    page_size: int = 50


class PolicyDefinitionDTO(BaseModel):
    """Policy definition for API requests"""
    policy_id: Optional[str] = None
    name: str
    description: str = ""
    rules: List[PolicyRuleDTO]
    version: int = 1
    enabled: bool = True
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PolicyDefinitionResponse(BaseModel):
    """Policy definition response"""
    policy_id: str
    name: str
    description: str
    rules: List[PolicyRuleDTO]
    version: int
    enabled: bool
    tags: List[str]
    metadata: Dict[str, Any]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PolicyValidationRequest(BaseModel):
    """Request to validate a policy before deployment"""
    policy_id: str
    dry_run: bool = True


class PolicyValidationResponse(BaseModel):
    """Policy validation response"""
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    affected_agents: int = 0


# =============================================================================
# Evaluation DTOs
# =============================================================================

class EvaluationRequest(BaseModel):
    """Request to evaluate an agent action"""
    request_id: Optional[str] = Field(default_factory=lambda: str(uuid4()))
    agent_id: str
    operation: str
    resource: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)


class MatchedRuleInfo(BaseModel):
    """Information about a matched rule"""
    rule_id: str
    policy_id: str
    policy_name: str
    rule_name: str
    action: PolicyVerdict


class ExplanationDTO(BaseModel):
    """Explanation of policy decision"""
    matched_rules: List[MatchedRuleInfo]
    reason: str
    contributing_factors: List[str] = Field(default_factory=list)


class EvaluationResponse(BaseModel):
    """Response from policy evaluation"""
    request_id: str
    decision_id: str
    verdict: PolicyVerdict
    confidence: float
    explanation: ExplanationDTO
    audit_event_id: str
    evaluation_latency_ms: float
    escalation: Optional[Dict[str, Any]] = None


# =============================================================================
# Constraint DTOs
# =============================================================================

class TemporalConfigDTO(BaseModel):
    """Temporal constraint configuration"""
    business_hours_only: bool = False
    start_hour: int = 9
    end_hour: int = 17
    allowed_days: List[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4])
    timezone: str = "UTC"


class ConstraintCreateRequest(BaseModel):
    """Request to create a constraint"""
    name: str
    description: str = ""
    constraint_type: ConstraintType
    limit: float
    window_seconds: int = 3600
    agent_id: Optional[str] = None
    scope: str = "global"
    temporal_config: Optional[TemporalConfigDTO] = None


class ConstraintResponse(BaseModel):
    """Constraint response"""
    constraint_id: str
    name: str
    description: str
    constraint_type: ConstraintType
    limit: float
    window_seconds: int
    agent_id: Optional[str]
    scope: str
    temporal_config: Optional[TemporalConfigDTO]
    enabled: bool
    created_at: datetime
    updated_at: datetime


class ConstraintCheckRequest(BaseModel):
    """Request to check a constraint"""
    agent_id: str
    constraint_id: str
    requested_amount: int = 1


class ConstraintCheckResponse(BaseModel):
    """Response from constraint check"""
    allowed: bool
    remaining: Optional[float] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    reset_at: Optional[datetime] = None


class ConstraintViolationResponse(BaseModel):
    """Constraint violation response"""
    violation_id: str
    constraint_id: str
    constraint_name: str
    agent_id: str
    current_usage: float
    limit: float
    violation_type: str
    timestamp: datetime


# =============================================================================
# Escalation DTOs
# =============================================================================

class EscalationCreateRequest(BaseModel):
    """Request to create an escalation"""
    decision_id: str
    reason: str
    context: Dict[str, Any] = Field(default_factory=dict)
    approvers: List[str] = Field(default_factory=list)
    priority: int = 1


class EscalationResponse(BaseModel):
    """Escalation response"""
    workflow_id: str
    decision_id: str
    status: EscalationStatus
    escalation_level: int
    reason: str
    context: Dict[str, Any]
    approvers: List[str]
    assigned_to: Optional[str]
    created_at: datetime
    timeout_at: Optional[datetime]
    resolved_at: Optional[datetime]
    resolved_by: Optional[str]


class EscalationResolveRequest(BaseModel):
    """Request to resolve an escalation"""
    approver_id: str
    approved: bool
    notes: str = ""
    mfa_token: Optional[str] = None


class EscalationListResponse(BaseModel):
    """List of escalations response"""
    escalations: List[EscalationResponse]
    total: int
    pending_count: int


# =============================================================================
# Anomaly DTOs
# =============================================================================

class AnomalyResponse(BaseModel):
    """Anomaly detection response"""
    anomaly_id: str
    agent_id: str
    metric_name: str
    severity: AnomalySeverity
    description: str
    baseline_value: float
    observed_value: float
    z_score: float
    detection_method: str
    confidence: float
    detected_at: datetime
    acknowledged: bool


class AnomalyListResponse(BaseModel):
    """List of anomalies response"""
    anomalies: List[AnomalyResponse]
    total: int
    critical_count: int
    high_count: int


class AnomalyAcknowledgeRequest(BaseModel):
    """Request to acknowledge an anomaly"""
    acknowledged_by: str
    notes: str = ""


# =============================================================================
# Audit DTOs
# =============================================================================

class AuditQueryRequest(BaseModel):
    """Request to query audit log"""
    actor_id: Optional[str] = None
    actor_type: Optional[str] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = 100
    offset: int = 0


class AuditResponse(BaseModel):
    """Audit entry response"""
    audit_id: str
    action: str
    actor_id: str
    actor_type: str
    resource_type: str
    resource_id: str
    details: Dict[str, Any]
    timestamp: datetime
    signature_valid: bool = True


class AuditListResponse(BaseModel):
    """List of audit entries response"""
    entries: List[AuditResponse]
    total: int
    page: int
    page_size: int


class AuditVerifyRequest(BaseModel):
    """Request to verify audit trail integrity"""
    start_audit_id: Optional[str] = None
    end_audit_id: Optional[str] = None


class AuditVerifyResponse(BaseModel):
    """Audit verification response"""
    verified: bool
    entries_checked: int
    first_invalid_id: Optional[str] = None
    error_message: Optional[str] = None


# =============================================================================
# Health DTOs
# =============================================================================

class ComponentHealthDTO(BaseModel):
    """Health status of a component"""
    name: str
    status: str  # "healthy", "degraded", "unhealthy"
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Overall health response"""
    status: str
    service: str
    version: str
    components: Dict[str, ComponentHealthDTO] = Field(default_factory=dict)


class MetricsResponse(BaseModel):
    """Metrics summary response"""
    policy_evaluations_total: int
    policy_evaluation_latency_p99_ms: float
    constraint_violations_total: int
    escalations_pending: int
    anomalies_detected_total: int
    audit_entries_total: int

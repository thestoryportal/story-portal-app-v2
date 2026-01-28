"""
L08 Supervision Layer - Error Codes

Error code range: E8000-E8999

Categories:
- E8000-E8099: Policy errors
- E8100-E8199: Constraint errors
- E8200-E8299: Escalation errors
- E8300-E8399: Anomaly detection errors
- E8400-E8499: Audit trail errors
- E8500-E8599: Access control errors
- E8600-E8699: Integration errors
- E8700-E8799: Configuration errors
- E8800-E8899: Performance errors
- E8900-E8999: Internal errors
"""

from typing import Optional, Dict, Any
from enum import Enum


class ErrorCodes(str, Enum):
    """L08 error codes (E8000-E8999)"""

    # Policy errors (E8000-E8099)
    POLICY_NOT_FOUND = "E8001"
    POLICY_EVALUATION_FAILED = "E8002"
    POLICY_COMPILATION_FAILED = "E8003"
    POLICY_CONFLICT_DETECTED = "E8004"
    POLICY_INVALID_CONDITION = "E8005"
    POLICY_VERSION_CONFLICT = "E8006"
    POLICY_SCOPE_INVALID = "E8007"
    POLICY_RULE_INVALID = "E8008"
    POLICY_DEPLOY_FAILED = "E8009"
    POLICY_ROLLBACK_FAILED = "E8010"
    POLICY_CACHE_ERROR = "E8011"
    POLICY_CONTEXT_MISSING = "E8012"

    # Constraint errors (E8100-E8199)
    CONSTRAINT_VIOLATION = "E8101"
    RATE_LIMIT_EXCEEDED = "E8102"
    QUOTA_EXCEEDED = "E8103"
    RESOURCE_CAP_EXCEEDED = "E8104"
    CONSTRAINT_NOT_FOUND = "E8105"
    CONSTRAINT_INVALID = "E8106"
    CONSTRAINT_CONFLICT = "E8107"
    TEMPORAL_CONSTRAINT_VIOLATION = "E8108"
    BUSINESS_HOURS_VIOLATION = "E8109"

    # Escalation errors (E8200-E8299)
    ESCALATION_WORKFLOW_FAILED = "E8201"
    ESCALATION_TIMEOUT = "E8202"
    NO_APPROVER_AVAILABLE = "E8203"
    ESCALATION_NOT_FOUND = "E8204"
    ESCALATION_ALREADY_RESOLVED = "E8205"
    ESCALATION_INVALID_STATE = "E8206"
    ESCALATION_NOTIFICATION_FAILED = "E8207"
    ESCALATION_MFA_REQUIRED = "E8208"
    ESCALATION_MFA_FAILED = "E8209"
    ESCALATION_LEVEL_EXCEEDED = "E8210"

    # Anomaly detection errors (E8300-E8399)
    ANOMALY_DETECTION_FAILED = "E8301"
    INSUFFICIENT_BASELINE_DATA = "E8302"
    BASELINE_COMPUTATION_FAILED = "E8303"
    ANOMALY_NOT_FOUND = "E8304"
    METRIC_NOT_TRACKED = "E8305"
    DETECTION_THRESHOLD_INVALID = "E8306"

    # Audit trail errors (E8400-E8499)
    AUDIT_TRAIL_WRITE_FAILED = "E8401"
    AUDIT_SIGNATURE_INVALID = "E8402"
    AUDIT_ENTRY_NOT_FOUND = "E8403"
    AUDIT_INTEGRITY_VIOLATION = "E8404"
    AUDIT_QUERY_FAILED = "E8405"
    AUDIT_VERIFICATION_FAILED = "E8406"
    AUDIT_RETENTION_EXPIRED = "E8407"

    # Access control errors (E8500-E8599)
    ACCESS_DENIED = "E8501"
    MFA_REQUIRED = "E8502"
    INSUFFICIENT_PRIVILEGES = "E8503"
    SESSION_EXPIRED = "E8504"
    TOKEN_INVALID = "E8505"
    PERMISSION_NOT_FOUND = "E8506"
    ROLE_NOT_ASSIGNED = "E8507"

    # Integration errors (E8600-E8699)
    L01_CONNECTION_FAILED = "E8601"
    L10_CONNECTION_FAILED = "E8602"
    VAULT_CONNECTION_FAILED = "E8603"
    REDIS_CONNECTION_FAILED = "E8604"
    CONSENSUS_TIMEOUT = "E8605"
    BRIDGE_NOT_INITIALIZED = "E8606"

    # Configuration errors (E8700-E8799)
    CONFIG_INVALID = "E8701"
    CONFIG_MISSING = "E8702"
    CONFIG_LOAD_FAILED = "E8703"

    # Performance errors (E8800-E8899)
    EVALUATION_TIMEOUT = "E8801"
    CACHE_MISS = "E8802"
    SLA_VIOLATION = "E8803"

    # Internal errors (E8900-E8999)
    INTERNAL_ERROR = "E8901"
    NOT_IMPLEMENTED = "E8902"
    STATE_CORRUPTION = "E8903"


# Error code descriptions for documentation and logging
ERROR_DESCRIPTIONS: Dict[str, str] = {
    # Policy errors
    "E8001": "Policy not found in registry",
    "E8002": "Policy evaluation failed",
    "E8003": "Policy condition compilation failed",
    "E8004": "Conflicting policies detected",
    "E8005": "Invalid policy condition expression",
    "E8006": "Policy version conflict during update",
    "E8007": "Invalid policy scope",
    "E8008": "Invalid policy rule definition",
    "E8009": "Policy deployment failed",
    "E8010": "Policy rollback failed",
    "E8011": "Policy cache error",
    "E8012": "Required context missing for policy evaluation",

    # Constraint errors
    "E8101": "Constraint violation detected",
    "E8102": "Rate limit exceeded",
    "E8103": "Quota exceeded",
    "E8104": "Resource cap exceeded",
    "E8105": "Constraint not found",
    "E8106": "Invalid constraint definition",
    "E8107": "Conflicting constraints detected",
    "E8108": "Temporal constraint violation",
    "E8109": "Operation not allowed outside business hours",

    # Escalation errors
    "E8201": "Escalation workflow failed",
    "E8202": "Escalation timeout exceeded",
    "E8203": "No approver available for escalation",
    "E8204": "Escalation workflow not found",
    "E8205": "Escalation already resolved",
    "E8206": "Invalid escalation state transition",
    "E8207": "Failed to send escalation notification",
    "E8208": "MFA required for escalation resolution",
    "E8209": "MFA verification failed",
    "E8210": "Maximum escalation level exceeded",

    # Anomaly errors
    "E8301": "Anomaly detection failed",
    "E8302": "Insufficient baseline data for detection",
    "E8303": "Baseline computation failed",
    "E8304": "Anomaly record not found",
    "E8305": "Metric not being tracked",
    "E8306": "Invalid detection threshold",

    # Audit errors
    "E8401": "Failed to write audit entry",
    "E8402": "Audit signature verification failed",
    "E8403": "Audit entry not found",
    "E8404": "Audit trail integrity violation detected",
    "E8405": "Audit query failed",
    "E8406": "Audit verification failed",
    "E8407": "Audit entry beyond retention period",

    # Access control errors
    "E8501": "Access denied",
    "E8502": "MFA verification required",
    "E8503": "Insufficient privileges for operation",
    "E8504": "Session expired",
    "E8505": "Invalid authentication token",
    "E8506": "Permission not found",
    "E8507": "Required role not assigned",

    # Integration errors
    "E8601": "Failed to connect to L01 Data Layer",
    "E8602": "Failed to connect to L10 Human Interface",
    "E8603": "Failed to connect to Vault",
    "E8604": "Failed to connect to Redis",
    "E8605": "Consensus timeout in distributed operation",
    "E8606": "Bridge not initialized",

    # Configuration errors
    "E8701": "Invalid configuration value",
    "E8702": "Required configuration missing",
    "E8703": "Failed to load configuration",

    # Performance errors
    "E8801": "Evaluation timeout exceeded",
    "E8802": "Cache miss during high-load",
    "E8803": "SLA violation detected",

    # Internal errors
    "E8901": "Internal error",
    "E8902": "Feature not implemented",
    "E8903": "Internal state corruption detected",
}


class L08Error(Exception):
    """Base exception for L08 Supervision Layer"""

    def __init__(
        self,
        error_code: ErrorCodes,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.error_code = error_code
        self.message = message or ERROR_DESCRIPTIONS.get(error_code.value, "Unknown error")
        self.details = details or {}
        super().__init__(f"{error_code.value}: {self.message}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "error_code": self.error_code.value,
            "message": self.message,
            "details": self.details,
        }


class PolicyError(L08Error):
    """Policy-related errors"""
    pass


class ConstraintError(L08Error):
    """Constraint enforcement errors"""
    pass


class EscalationError(L08Error):
    """Escalation workflow errors"""
    pass


class AnomalyError(L08Error):
    """Anomaly detection errors"""
    pass


class AuditError(L08Error):
    """Audit trail errors"""
    pass


class AccessControlError(L08Error):
    """Access control errors"""
    pass


class IntegrationError(L08Error):
    """Integration/connectivity errors"""
    pass

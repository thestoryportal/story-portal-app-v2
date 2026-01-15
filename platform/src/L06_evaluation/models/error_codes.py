"""Error code registry for L06 Evaluation Layer (E6000-E6999)"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict


class ErrorCode(str, Enum):
    """L06 Error codes E6000-E6999"""

    # E6001-E6005: Authentication & Authorization
    E6001 = "E6001"  # Missing authentication token
    E6002 = "E6002"  # Invalid JWT signature
    E6003 = "E6003"  # Token expired
    E6004 = "E6004"  # Insufficient permissions
    E6005 = "E6005"  # Tenant access denied

    # E6101-E6105: Data Integrity & Validation
    E6101 = "E6101"  # CloudEvent validation failed
    E6102 = "E6102"  # Metric value out of range
    E6103 = "E6103"  # Duplicate event detected
    E6104 = "E6104"  # Timestamp invalid
    E6105 = "E6105"  # Label cardinality exceeded

    # E6201-E6205: Configuration & Policy
    E6201 = "E6201"  # Configuration validation failed
    E6202 = "E6202"  # Invalid threshold configuration
    E6203 = "E6203"  # Policy violation
    E6204 = "E6204"  # SLA violation
    E6205 = "E6205"  # Feature not enabled

    # E6301-E6305: Metric Collection & Storage
    E6301 = "E6301"  # TSDB write failed
    E6302 = "E6302"  # Event stream timeout
    E6303 = "E6303"  # Metric cardinality limit hit
    E6304 = "E6304"  # Storage quota exceeded
    E6305 = "E6305"  # Deduplication cache full

    # E6401-E6404: Quality Scoring
    E6401 = "E6401"  # Insufficient data for scoring
    E6402 = "E6402"  # Quality score calculation error
    E6403 = "E6403"  # Dimension data missing
    E6404 = "E6404"  # Quality score cache miss

    # E6501-E6504: Anomaly Detection
    E6501 = "E6501"  # Baseline not established
    E6502 = "E6502"  # Anomaly detection error
    E6503 = "E6503"  # Alert delivery failed
    E6504 = "E6504"  # False positive filter error

    # E6601-E6604: Compliance & Audit
    E6601 = "E6601"  # Audit log write failed
    E6602 = "E6602"  # Policy validation error
    E6603 = "E6603"  # Audit log quota exceeded
    E6604 = "E6604"  # Compliance violation detected

    # E6703, E6705: Integration Errors
    E6703 = "E6703"  # L01 integration failed
    E6705 = "E6705"  # Configuration store unavailable

    # E6801-E6803: Dashboard & Reporting
    E6801 = "E6801"  # Report generation failed
    E6802 = "E6802"  # Dashboard query timeout
    E6803 = "E6803"  # Visualization error

    # E6901, E6904-E6905: Operational Errors
    E6901 = "E6901"  # Component health check failed
    E6904 = "E6904"  # Configuration reload failed
    E6905 = "E6905"  # Out-of-memory error


@dataclass
class ErrorCodeMetadata:
    """Metadata for an error code"""
    code: ErrorCode
    message: str
    http_status: int
    root_cause: str
    recovery: str
    category: str


class ErrorCodeRegistry:
    """Registry of all L06 error codes with metadata"""

    _REGISTRY: Dict[ErrorCode, ErrorCodeMetadata] = {
        # Authentication & Authorization
        ErrorCode.E6001: ErrorCodeMetadata(
            code=ErrorCode.E6001,
            message="Missing authentication token",
            http_status=401,
            root_cause="API request without Authorization header",
            recovery="Provide valid OAuth 2.0 token in Authorization: Bearer <token> header",
            category="authentication",
        ),
        ErrorCode.E6002: ErrorCodeMetadata(
            code=ErrorCode.E6002,
            message="Invalid JWT signature",
            http_status=401,
            root_cause="Token signed with wrong key or corrupted",
            recovery="Reissue token from auth server or refresh token",
            category="authentication",
        ),
        ErrorCode.E6003: ErrorCodeMetadata(
            code=ErrorCode.E6003,
            message="Token expired",
            http_status=401,
            root_cause="JWT exp claim is in the past",
            recovery="Refresh token or re-authenticate with credentials",
            category="authentication",
        ),
        ErrorCode.E6004: ErrorCodeMetadata(
            code=ErrorCode.E6004,
            message="Insufficient permissions",
            http_status=403,
            root_cause="User role doesn't match endpoint requirements",
            recovery="Request role upgrade from admin or use different endpoint",
            category="authorization",
        ),
        ErrorCode.E6005: ErrorCodeMetadata(
            code=ErrorCode.E6005,
            message="Tenant access denied",
            http_status=403,
            root_cause="User not authorized to access tenant",
            recovery="Verify tenant_id matches authenticated user's tenant",
            category="authorization",
        ),

        # Data Integrity & Validation
        ErrorCode.E6101: ErrorCodeMetadata(
            code=ErrorCode.E6101,
            message="CloudEvent validation failed",
            http_status=400,
            root_cause="Missing required fields or invalid schema",
            recovery="Verify event includes source, type, subject, time, data",
            category="validation",
        ),
        ErrorCode.E6102: ErrorCodeMetadata(
            code=ErrorCode.E6102,
            message="Metric value out of range",
            http_status=400,
            root_cause="Value NaN, Inf, or outside expected bounds",
            recovery="Validate metric computation logic, check for division by zero",
            category="validation",
        ),
        ErrorCode.E6103: ErrorCodeMetadata(
            code=ErrorCode.E6103,
            message="Duplicate event detected",
            http_status=400,
            root_cause="Event with same idempotency key processed twice",
            recovery="This is idempotent - operation succeeds on retry",
            category="validation",
        ),
        ErrorCode.E6104: ErrorCodeMetadata(
            code=ErrorCode.E6104,
            message="Timestamp invalid",
            http_status=400,
            root_cause="Event timestamp unreasonable or out of order",
            recovery="Verify system clock on event source, check for negative durations",
            category="validation",
        ),
        ErrorCode.E6105: ErrorCodeMetadata(
            code=ErrorCode.E6105,
            message="Label cardinality exceeded",
            http_status=400,
            root_cause="Too many unique label combinations",
            recovery="Prune high-cardinality labels or aggregate dimensions",
            category="validation",
        ),

        # Configuration & Policy
        ErrorCode.E6201: ErrorCodeMetadata(
            code=ErrorCode.E6201,
            message="Configuration validation failed",
            http_status=400,
            root_cause="Quality weights don't sum to 1.0",
            recovery="Adjust weights: sum(all weights) must equal 1.0 ±0.001",
            category="configuration",
        ),
        ErrorCode.E6202: ErrorCodeMetadata(
            code=ErrorCode.E6202,
            message="Invalid threshold configuration",
            http_status=400,
            root_cause="Min/target/max thresholds out of order",
            recovery="Reorder: min < target < max, all positive",
            category="configuration",
        ),
        ErrorCode.E6203: ErrorCodeMetadata(
            code=ErrorCode.E6203,
            message="Policy violation",
            http_status=403,
            root_cause="Execution violated constraint (deadline, budget)",
            recovery="Adjust agent/plan parameters or relax policy limits",
            category="policy",
        ),
        ErrorCode.E6204: ErrorCodeMetadata(
            code=ErrorCode.E6204,
            message="SLA violation",
            http_status=400,
            root_cause="Metric outside SLA target range",
            recovery="Investigate performance degradation or adjust SLA target",
            category="policy",
        ),
        ErrorCode.E6205: ErrorCodeMetadata(
            code=ErrorCode.E6205,
            message="Feature not enabled",
            http_status=400,
            root_cause="Feature flag disabled in configuration",
            recovery="Enable feature via PUT /api/v1/config (Admin only)",
            category="configuration",
        ),

        # Metric Collection & Storage
        ErrorCode.E6301: ErrorCodeMetadata(
            code=ErrorCode.E6301,
            message="TSDB write failed",
            http_status=503,
            root_cause="VictoriaMetrics unavailable or quota exceeded",
            recovery="Wait for TSDB recovery or increase storage quota",
            category="storage",
        ),
        ErrorCode.E6302: ErrorCodeMetadata(
            code=ErrorCode.E6302,
            message="Event stream timeout",
            http_status=504,
            root_cause="Kafka/Pulsar not responding to requests",
            recovery="Check event stream broker connectivity, restart brokers if needed",
            category="integration",
        ),
        ErrorCode.E6303: ErrorCodeMetadata(
            code=ErrorCode.E6303,
            message="Metric cardinality limit hit",
            http_status=429,
            root_cause=">100K unique series per tenant",
            recovery="Auto-prune least-frequent labels automatically",
            category="storage",
        ),
        ErrorCode.E6304: ErrorCodeMetadata(
            code=ErrorCode.E6304,
            message="Storage quota exceeded",
            http_status=507,
            root_cause="TSDB storage full or quota exceeded",
            recovery="Delete old metrics or increase TSDB storage allocation",
            category="storage",
        ),
        ErrorCode.E6305: ErrorCodeMetadata(
            code=ErrorCode.E6305,
            message="Deduplication cache full",
            http_status=503,
            root_cause="Dedup buffer memory exhausted",
            recovery="Increase dedup cache size or reduce dedup window",
            category="storage",
        ),

        # Quality Scoring
        ErrorCode.E6401: ErrorCodeMetadata(
            code=ErrorCode.E6401,
            message="Insufficient data for scoring",
            http_status=202,
            root_cause="Not enough metrics collected in window",
            recovery="Retry later when more data available (wait for next window)",
            category="scoring",
        ),
        ErrorCode.E6402: ErrorCodeMetadata(
            code=ErrorCode.E6402,
            message="Quality score calculation error",
            http_status=500,
            root_cause="Exception in scorer (divide by zero, etc.)",
            recovery="Check dimension metrics availability, verify formula syntax",
            category="scoring",
        ),
        ErrorCode.E6403: ErrorCodeMetadata(
            code=ErrorCode.E6403,
            message="Dimension data missing",
            http_status=202,
            root_cause="One or more dimensions unavailable",
            recovery="Wait for dimension computation to complete",
            category="scoring",
        ),
        ErrorCode.E6404: ErrorCodeMetadata(
            code=ErrorCode.E6404,
            message="Quality score cache miss",
            http_status=202,
            root_cause="Cache evicted during computation",
            recovery="Score will be recomputed (may cause latency increase)",
            category="scoring",
        ),

        # Anomaly Detection
        ErrorCode.E6501: ErrorCodeMetadata(
            code=ErrorCode.E6501,
            message="Baseline not established",
            http_status=202,
            root_cause="Anomaly detector still in cold-start phase",
            recovery="Wait 1-2 hours for baseline training to complete",
            category="anomaly",
        ),
        ErrorCode.E6502: ErrorCodeMetadata(
            code=ErrorCode.E6502,
            message="Anomaly detection error",
            http_status=500,
            root_cause="Exception in detector algorithm",
            recovery="Check baseline data quality, verify metrics format",
            category="anomaly",
        ),
        ErrorCode.E6503: ErrorCodeMetadata(
            code=ErrorCode.E6503,
            message="Alert delivery failed",
            http_status=503,
            root_cause="Slack/PagerDuty webhook unreachable",
            recovery="Check webhook URL validity and endpoint availability",
            category="alerting",
        ),
        ErrorCode.E6504: ErrorCodeMetadata(
            code=ErrorCode.E6504,
            message="False positive filter error",
            http_status=500,
            root_cause="Exception in FP rate calculation",
            recovery="Review anomaly tuning parameters, adjust deviation threshold",
            category="anomaly",
        ),

        # Compliance & Audit
        ErrorCode.E6601: ErrorCodeMetadata(
            code=ErrorCode.E6601,
            message="Audit log write failed",
            http_status=500,
            root_cause="Cannot write to immutable audit trail",
            recovery="Check L01 audit storage availability and connectivity",
            category="audit",
        ),
        ErrorCode.E6602: ErrorCodeMetadata(
            code=ErrorCode.E6602,
            message="Policy validation error",
            http_status=400,
            root_cause="Execution doesn't meet policy requirements",
            recovery="Review policy configuration and constraints",
            category="compliance",
        ),
        ErrorCode.E6603: ErrorCodeMetadata(
            code=ErrorCode.E6603,
            message="Audit log quota exceeded",
            http_status=507,
            root_cause="Audit trail storage full",
            recovery="Archive old audit logs or increase quota",
            category="audit",
        ),
        ErrorCode.E6604: ErrorCodeMetadata(
            code=ErrorCode.E6604,
            message="Compliance violation detected",
            http_status=202,
            root_cause="Constraint breach detected",
            recovery="Manual review and remediation of execution required",
            category="compliance",
        ),

        # Integration Errors
        ErrorCode.E6703: ErrorCodeMetadata(
            code=ErrorCode.E6703,
            message="L01 integration failed",
            http_status=503,
            root_cause="Cannot connect to L01 APIs or event stream",
            recovery="Verify L01 service connectivity, restart if needed",
            category="integration",
        ),
        ErrorCode.E6705: ErrorCodeMetadata(
            code=ErrorCode.E6705,
            message="Configuration store unavailable",
            http_status=503,
            root_cause="Cannot load config from L01",
            recovery="Wait for config store recovery, use cached config",
            category="integration",
        ),

        # Dashboard & Reporting
        ErrorCode.E6801: ErrorCodeMetadata(
            code=ErrorCode.E6801,
            message="Report generation failed",
            http_status=500,
            root_cause="Exception during report compilation",
            recovery="Check data availability and retry report generation",
            category="reporting",
        ),
        ErrorCode.E6802: ErrorCodeMetadata(
            code=ErrorCode.E6802,
            message="Dashboard query timeout",
            http_status=504,
            root_cause="Grafana query exceeded timeout",
            recovery="Simplify query or increase timeout threshold",
            category="reporting",
        ),
        ErrorCode.E6803: ErrorCodeMetadata(
            code=ErrorCode.E6803,
            message="Visualization error",
            http_status=500,
            root_cause="Cannot render dashboard panel",
            recovery="Check metric availability and JSON format validity",
            category="reporting",
        ),

        # Operational Errors
        ErrorCode.E6901: ErrorCodeMetadata(
            code=ErrorCode.E6901,
            message="Component health check failed",
            http_status=500,
            root_cause="Component not responding to health probe",
            recovery="Check component logs and restart service pod",
            category="operational",
        ),
        ErrorCode.E6904: ErrorCodeMetadata(
            code=ErrorCode.E6904,
            message="Configuration reload failed",
            http_status=500,
            root_cause="Cannot reload configuration at runtime",
            recovery="Rollback to previous version via /api/v1/config/rollback",
            category="operational",
        ),
        ErrorCode.E6905: ErrorCodeMetadata(
            code=ErrorCode.E6905,
            message="Out-of-memory error",
            http_status=500,
            root_cause="Process heap memory exceeded",
            recovery="Increase pod memory allocation or reduce cardinality",
            category="operational",
        ),
    }

    @classmethod
    def get(cls, code: ErrorCode) -> ErrorCodeMetadata:
        """Get error code metadata"""
        return cls._REGISTRY.get(code)

    @classmethod
    def get_message(cls, code: ErrorCode) -> str:
        """Get error message for code"""
        metadata = cls.get(code)
        return metadata.message if metadata else f"Unknown error: {code}"

    @classmethod
    def get_http_status(cls, code: ErrorCode) -> int:
        """Get HTTP status for error code"""
        metadata = cls.get(code)
        return metadata.http_status if metadata else 500

    @classmethod
    def get_recovery(cls, code: ErrorCode) -> str:
        """Get recovery instructions for error code"""
        metadata = cls.get(code)
        return metadata.recovery if metadata else "Contact support"

    @classmethod
    def get_by_category(cls, category: str) -> list[ErrorCodeMetadata]:
        """Get all error codes in a category"""
        return [m for m in cls._REGISTRY.values() if m.category == category]

    @classmethod
    def format_error_response(cls, code: ErrorCode, details: str = "") -> dict:
        """Format error response for API"""
        metadata = cls.get(code)
        return {
            "error": code.value,
            "message": metadata.message if metadata else "Unknown error",
            "details": details,
            "recovery": metadata.recovery if metadata else "Contact support",
        }

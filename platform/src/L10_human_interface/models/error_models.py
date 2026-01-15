"""
L10 Human Interface Layer - Error Models

Error code range: E10000-E10999
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime, UTC


class ErrorCode(str, Enum):
    """L10 Human Interface Layer error codes (E10000-E10999)."""

    # E10000-E10099: Authentication & Authorization
    E10001 = "E10001"  # Missing API key
    E10002 = "E10002"  # Invalid API key
    E10003 = "E10003"  # API key expired
    E10004 = "E10004"  # Insufficient permissions
    E10005 = "E10005"  # Cross-tenant access denied
    E10006 = "E10006"  # MFA required
    E10007 = "E10007"  # Session expired

    # E10100-E10199: Dashboard Data
    E10101 = "E10101"  # Metric query failed
    E10102 = "E10102"  # Agent state unavailable
    E10103 = "E10103"  # Dashboard aggregation timeout
    E10104 = "E10104"  # Invalid time range
    E10105 = "E10105"  # Too many data points requested
    E10106 = "E10106"  # Agent not found
    E10107 = "E10107"  # Cache read failed

    # E10200-E10299: WebSocket
    E10201 = "E10201"  # WebSocket authentication failed
    E10202 = "E10202"  # Invalid subscription topic
    E10203 = "E10203"  # Connection limit exceeded
    E10204 = "E10204"  # Message rate limit exceeded
    E10205 = "E10205"  # WebSocket connection failed
    E10206 = "E10206"  # Invalid message format
    E10207 = "E10207"  # Subscription failed

    # E10300-E10399: Control Operations
    E10301 = "E10301"  # Invalid agent state transition
    E10302 = "E10302"  # Agent not found
    E10303 = "E10303"  # Control operation failed
    E10304 = "E10304"  # Operation already in progress
    E10305 = "E10305"  # Agent locked by another operation
    E10306 = "E10306"  # Invalid control request
    E10307 = "E10307"  # Control timeout

    # E10400-E10499: Event Viewer
    E10401 = "E10401"  # Event query failed
    E10402 = "E10402"  # Event not found
    E10403 = "E10403"  # Invalid event filter
    E10404 = "E10404"  # Event pagination error

    # E10500-E10599: Audit
    E10501 = "E10501"  # Audit log query failed
    E10502 = "E10502"  # Audit log write failed
    E10503 = "E10503"  # Audit trail unavailable

    # E10600-E10699: Cost API
    E10601 = "E10601"  # Cost calculation failed
    E10602 = "E10602"  # Budget exceeded alert
    E10603 = "E10603"  # Cost data unavailable

    # E10700-E10799: Alerts
    E10701 = "E10701"  # Alert configuration invalid
    E10702 = "E10702"  # Alert delivery failed
    E10703 = "E10703"  # Alert not found
    E10704 = "E10704"  # Alert acknowledge failed

    # E10900-E10999: Server Errors
    E10901 = "E10901"  # Internal server error
    E10902 = "E10902"  # Dependency unavailable (L02/L06/L11)
    E10903 = "E10903"  # Redis connection failed
    E10904 = "E10904"  # PostgreSQL connection failed
    E10905 = "E10905"  # Unexpected error


# Error messages for each code
ERROR_MESSAGES: Dict[ErrorCode, str] = {
    # Authentication & Authorization
    ErrorCode.E10001: "Missing API key",
    ErrorCode.E10002: "Invalid API key",
    ErrorCode.E10003: "API key expired",
    ErrorCode.E10004: "Insufficient permissions - Admin or Operator role required",
    ErrorCode.E10005: "Cross-tenant access denied",
    ErrorCode.E10006: "Multi-factor authentication required",
    ErrorCode.E10007: "Session expired - please re-authenticate",

    # Dashboard
    ErrorCode.E10101: "Metric query failed",
    ErrorCode.E10102: "Agent state unavailable",
    ErrorCode.E10103: "Dashboard aggregation timeout",
    ErrorCode.E10104: "Invalid time range - start must be before end",
    ErrorCode.E10105: "Too many data points requested - reduce time range",
    ErrorCode.E10106: "Agent not found",
    ErrorCode.E10107: "Cache read failed",

    # WebSocket
    ErrorCode.E10201: "WebSocket authentication failed",
    ErrorCode.E10202: "Invalid subscription topic",
    ErrorCode.E10203: "Connection limit exceeded",
    ErrorCode.E10204: "Message rate limit exceeded",
    ErrorCode.E10205: "WebSocket connection failed",
    ErrorCode.E10206: "Invalid message format",
    ErrorCode.E10207: "Subscription failed",

    # Control Operations
    ErrorCode.E10301: "Invalid agent state transition",
    ErrorCode.E10302: "Agent not found",
    ErrorCode.E10303: "Control operation failed",
    ErrorCode.E10304: "Operation already in progress",
    ErrorCode.E10305: "Agent locked by another operation",
    ErrorCode.E10306: "Invalid control request",
    ErrorCode.E10307: "Control operation timeout",

    # Event Viewer
    ErrorCode.E10401: "Event query failed",
    ErrorCode.E10402: "Event not found",
    ErrorCode.E10403: "Invalid event filter",
    ErrorCode.E10404: "Event pagination error",

    # Audit
    ErrorCode.E10501: "Audit log query failed",
    ErrorCode.E10502: "Audit log write failed",
    ErrorCode.E10503: "Audit trail unavailable",

    # Cost API
    ErrorCode.E10601: "Cost calculation failed",
    ErrorCode.E10602: "Budget exceeded alert",
    ErrorCode.E10603: "Cost data unavailable",

    # Alerts
    ErrorCode.E10701: "Alert configuration invalid",
    ErrorCode.E10702: "Alert delivery failed",
    ErrorCode.E10703: "Alert not found",
    ErrorCode.E10704: "Alert acknowledge failed",

    # Server
    ErrorCode.E10901: "Internal server error",
    ErrorCode.E10902: "Dependency layer unavailable",
    ErrorCode.E10903: "Redis connection failed",
    ErrorCode.E10904: "PostgreSQL connection failed",
    ErrorCode.E10905: "Unexpected error occurred",
}


# Recoverable errors (can retry)
RECOVERABLE_ERRORS = {
    ErrorCode.E10103,  # Timeout
    ErrorCode.E10303,  # Control operation failed
    ErrorCode.E10307,  # Control timeout
    ErrorCode.E10401,  # Event query failed
    ErrorCode.E10501,  # Audit query failed
    ErrorCode.E10601,  # Cost calculation failed
    ErrorCode.E10902,  # Dependency unavailable
    ErrorCode.E10903,  # Redis unavailable
    ErrorCode.E10904,  # PostgreSQL unavailable
}


@dataclass
class InterfaceError(Exception):
    """Base exception for L10 Human Interface Layer."""

    code: ErrorCode
    message: str
    details: Optional[Dict[str, Any]] = None
    recovery_suggestion: Optional[str] = None

    def __str__(self) -> str:
        """String representation of error."""
        base = f"{self.code.value}: {self.message}"
        if self.details:
            base += f" | Details: {self.details}"
        if self.recovery_suggestion:
            base += f" | Suggestion: {self.recovery_suggestion}"
        return base

    def __post_init__(self):
        """Call Exception.__init__ to properly initialize the exception."""
        super().__init__(str(self))

    @property
    def is_recoverable(self) -> bool:
        """Check if error is recoverable (can retry)."""
        return self.code in RECOVERABLE_ERRORS

    @property
    def http_status(self) -> int:
        """Map error code to HTTP status."""
        code_value = self.code.value

        # Authentication errors
        if code_value.startswith("E1000"):
            if code_value in ("E10001", "E10002", "E10003", "E10007"):
                return 401  # Unauthorized
            if code_value in ("E10004", "E10005"):
                return 403  # Forbidden
            return 401

        # Dashboard errors
        if code_value.startswith("E1010"):
            if code_value in ("E10106",):  # Not found
                return 404
            if code_value == "E10103":  # Timeout
                return 504
            return 400

        # WebSocket errors
        if code_value.startswith("E1020"):
            if code_value == "E10203":  # Rate limit
                return 429
            return 400

        # Control operation errors
        if code_value.startswith("E1030"):
            if code_value == "E10302":  # Not found
                return 404
            if code_value in ("E10304", "E10305"):  # Conflict
                return 409
            if code_value == "E10307":  # Timeout
                return 504
            return 400

        # Event viewer errors
        if code_value.startswith("E1040"):
            if code_value == "E10402":  # Not found
                return 404
            return 400

        # Audit errors
        if code_value.startswith("E1050"):
            return 500

        # Cost API errors
        if code_value.startswith("E1060"):
            return 400

        # Alert errors
        if code_value.startswith("E1070"):
            if code_value == "E10703":  # Not found
                return 404
            return 400

        # Server errors
        if code_value.startswith("E1090"):
            if code_value == "E10902":  # Dependency unavailable
                return 503
            return 500

        return 400  # Default to bad request

    def to_dict(self) -> Dict[str, Any]:
        """Convert to API response format."""
        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "details": self.details or {},
                "recovery": self.recovery_suggestion,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        }

    @classmethod
    def from_code(
        cls,
        code: ErrorCode,
        details: Optional[Dict[str, Any]] = None,
        recovery_suggestion: Optional[str] = None,
    ) -> "InterfaceError":
        """Create error from error code."""
        message = ERROR_MESSAGES.get(code, "Unknown error")
        return cls(
            code=code,
            message=message,
            details=details,
            recovery_suggestion=recovery_suggestion,
        )

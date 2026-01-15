"""
Tool Execution Layer Error Codes

Error code ranges E3000-E3999 for L03 Tool Execution Layer.
Based on Appendix B of tool-execution-layer-specification-v1.2-ASCII.md
"""

from enum import Enum
from typing import Dict, Any, Optional


class ErrorCode(Enum):
    """Error codes for L03 Tool Execution Layer (E3000-E3999)"""

    # Tool Registry Errors (E3000-E3099)
    E3001 = "E3001"  # Tool not found
    E3002 = "E3002"  # Tool version not found
    E3003 = "E3003"  # Tool deprecated
    E3004 = "E3004"  # Tool removed
    E3005 = "E3005"  # Semantic search failed
    E3006 = "E3006"  # Version conflict
    E3007 = "E3007"  # Duplicate tool registration
    E3008 = "E3008"  # Invalid tool manifest

    # Tool Executor Errors (E3100-E3199)
    E3101 = "E3101"  # Sandbox creation failed
    E3102 = "E3102"  # Resource limit exceeded
    E3103 = "E3103"  # Timeout exceeded
    E3104 = "E3104"  # Network policy violation
    E3105 = "E3105"  # Filesystem policy violation
    E3106 = "E3106"  # Concurrent tool limit exceeded
    E3107 = "E3107"  # Sandbox crashed
    E3108 = "E3108"  # Tool process exit non-zero

    # MCP Task Errors (E3150-E3199)
    E3150 = "E3150"  # Task not found
    E3151 = "E3151"  # Task already completed
    E3152 = "E3152"  # Task cancellation failed

    # Permission Checker Errors (E3200-E3299)
    E3201 = "E3201"  # Invalid capability token
    E3202 = "E3202"  # Expired capability token
    E3203 = "E3203"  # Permission denied - filesystem
    E3204 = "E3204"  # Permission denied - network
    E3205 = "E3205"  # Permission denied - credentials
    E3206 = "E3206"  # Permission denied - document access

    # External API Manager Errors (E3300-E3399)
    E3301 = "E3301"  # Circuit breaker open
    E3302 = "E3302"  # Rate limit exceeded
    E3303 = "E3303"  # External API timeout
    E3304 = "E3304"  # External API connection failed
    E3305 = "E3305"  # Credential injection failed
    E3306 = "E3306"  # Vault unavailable

    # Result Validator Errors (E3400-E3499)
    E3401 = "E3401"  # Schema validation failed
    E3402 = "E3402"  # Type coercion failed
    E3403 = "E3403"  # Sanitization failed
    E3404 = "E3404"  # Output too large

    # Document Bridge Errors (E3500-E3599)
    E3501 = "E3501"  # Document not found
    E3502 = "E3502"  # Document version pinning failed
    E3503 = "E3503"  # Document cache error
    E3504 = "E3504"  # MCP document server unavailable

    # State Bridge Errors (E3600-E3699)
    E3601 = "E3601"  # Checkpoint creation failed
    E3602 = "E3602"  # Checkpoint restoration failed
    E3603 = "E3603"  # Checkpoint not found
    E3604 = "E3604"  # MCP context server unavailable
    E3605 = "E3605"  # Delta encoding failed
    E3606 = "E3606"  # Checkpoint compression failed


# Error messages for each code
ERROR_MESSAGES: Dict[ErrorCode, str] = {
    # Tool Registry
    ErrorCode.E3001: "Tool not found in registry",
    ErrorCode.E3002: "Tool version not found",
    ErrorCode.E3003: "Tool is deprecated",
    ErrorCode.E3004: "Tool has been removed",
    ErrorCode.E3005: "Semantic search operation failed",
    ErrorCode.E3006: "Version conflict - no compatible version found",
    ErrorCode.E3007: "Tool already registered with this version",
    ErrorCode.E3008: "Invalid tool manifest schema",

    # Tool Executor
    ErrorCode.E3101: "Failed to create sandbox",
    ErrorCode.E3102: "Resource limit exceeded",
    ErrorCode.E3103: "Tool execution timeout",
    ErrorCode.E3104: "Network policy violation",
    ErrorCode.E3105: "Filesystem policy violation",
    ErrorCode.E3106: "Maximum concurrent tools exceeded",
    ErrorCode.E3107: "Sandbox crashed unexpectedly",
    ErrorCode.E3108: "Tool process exited with error",

    # MCP Tasks
    ErrorCode.E3150: "Task not found or expired",
    ErrorCode.E3151: "Task already completed",
    ErrorCode.E3152: "Task cancellation failed",

    # Permission Checker
    ErrorCode.E3201: "Invalid capability token",
    ErrorCode.E3202: "Capability token expired",
    ErrorCode.E3203: "Filesystem access denied",
    ErrorCode.E3204: "Network access denied",
    ErrorCode.E3205: "Credential access denied",
    ErrorCode.E3206: "Document access denied",

    # External API Manager
    ErrorCode.E3301: "Circuit breaker is open",
    ErrorCode.E3302: "Rate limit exceeded",
    ErrorCode.E3303: "External API request timeout",
    ErrorCode.E3304: "Failed to connect to external API",
    ErrorCode.E3305: "Credential injection failed",
    ErrorCode.E3306: "Vault service unavailable",

    # Result Validator
    ErrorCode.E3401: "Result schema validation failed",
    ErrorCode.E3402: "Type coercion failed",
    ErrorCode.E3403: "Output sanitization failed",
    ErrorCode.E3404: "Output exceeds size limit",

    # Document Bridge
    ErrorCode.E3501: "Document not found",
    ErrorCode.E3502: "Document version pinning failed",
    ErrorCode.E3503: "Document cache error",
    ErrorCode.E3504: "Document MCP server unavailable",

    # State Bridge
    ErrorCode.E3601: "Checkpoint creation failed",
    ErrorCode.E3602: "Checkpoint restoration failed",
    ErrorCode.E3603: "Checkpoint not found",
    ErrorCode.E3604: "Context MCP server unavailable",
    ErrorCode.E3605: "Delta encoding failed",
    ErrorCode.E3606: "Checkpoint compression failed",
}


# Retryable error codes
RETRYABLE_ERRORS = {
    ErrorCode.E3103,  # Timeout - can retry
    ErrorCode.E3301,  # Circuit breaker - can retry when closed
    ErrorCode.E3302,  # Rate limit - can retry after cooldown
    ErrorCode.E3303,  # External API timeout
    ErrorCode.E3304,  # Connection failed
    ErrorCode.E3503,  # Document cache error
    ErrorCode.E3504,  # MCP server unavailable
    ErrorCode.E3601,  # Checkpoint creation failed
    ErrorCode.E3604,  # MCP server unavailable
}


class ToolExecutionError(Exception):
    """
    Base exception for L03 Tool Execution Layer errors.

    All errors include a structured error code, message, and optional details.
    """

    def __init__(
        self,
        code: ErrorCode,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        retryable: Optional[bool] = None
    ):
        self.code = code
        self.message = message or ERROR_MESSAGES.get(code, "Unknown error")
        self.details = details or {}
        self.retryable = retryable if retryable is not None else (code in RETRYABLE_ERRORS)
        super().__init__(f"{code.value}: {self.message}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format for API responses"""
        return {
            "code": self.code.value,
            "message": self.message,
            "details": self.details,
            "retryable": self.retryable,
        }


# Error code range for documentation
E3000_RANGE = {
    "registry": (3000, 3099),
    "executor": (3100, 3199),
    "permissions": (3200, 3299),
    "external_api": (3300, 3399),
    "validation": (3400, 3499),
    "document_bridge": (3500, 3599),
    "state_bridge": (3600, 3699),
}

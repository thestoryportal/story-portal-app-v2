"""
L05 Planning Layer - Error Codes (E5000-E5999).

Error code ranges per specification:
- E5000-E5099: Plan cache and retrieval
- E5100-E5199: Goal decomposition
- E5200-E5299: Task orchestration
- E5300-E5399: Dependency resolution
- E5400-E5499: Context management
- E5500-E5599: Resource planning
- E5600-E5699: Plan validation
- E5700-E5799: Execution monitoring
- E5800-E5899: Plan persistence
- E5900-E5999: Multi-agent coordination
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class ErrorCode(str, Enum):
    """L05 Planning Layer error codes."""

    # E5000-E5099: Plan cache and retrieval
    E5000 = "E5000"  # PLAN_CACHE_ERROR
    E5001 = "E5001"  # GOAL_TEXT_TOO_LONG
    E5002 = "E5002"  # PLAN_NOT_FOUND
    E5003 = "E5003"  # CACHE_WRITE_FAILED
    E5004 = "E5004"  # INVALID_GOAL_INPUT (injection/security)
    E5005 = "E5005"  # CACHE_READ_FAILED

    # E5100-E5199: Goal decomposition
    E5100 = "E5100"  # DECOMPOSITION_FAILED
    E5101 = "E5101"  # LLM_DECOMPOSITION_ERROR
    E5102 = "E5102"  # TEMPLATE_MATCH_FAILED
    E5103 = "E5103"  # INVALID_GOAL_TYPE
    E5104 = "E5104"  # RECURSIVE_DEPTH_EXCEEDED
    E5105 = "E5105"  # DECOMPOSITION_TIMEOUT
    E5106 = "E5106"  # MALFORMED_LLM_RESPONSE
    E5107 = "E5107"  # GOAL_TOO_COMPLEX

    # E5200-E5299: Task orchestration
    E5200 = "E5200"  # ORCHESTRATION_FAILED
    E5201 = "E5201"  # INVALID_TASK_STATE_TRANSITION
    E5202 = "E5202"  # TASK_DISPATCH_FAILED
    E5203 = "E5203"  # TASK_TIMEOUT
    E5204 = "E5204"  # TASK_EXECUTION_FAILED
    E5205 = "E5205"  # MAX_RETRIES_EXCEEDED
    E5206 = "E5206"  # PARALLEL_EXECUTION_ERROR
    E5207 = "E5207"  # TASK_NOT_FOUND

    # E5300-E5399: Dependency resolution
    E5300 = "E5300"  # DEPENDENCY_RESOLUTION_FAILED
    E5301 = "E5301"  # CIRCULAR_DEPENDENCY_DETECTED
    E5302 = "E5302"  # MISSING_DEPENDENCY
    E5303 = "E5303"  # INVALID_DEPENDENCY_TYPE
    E5304 = "E5304"  # DEPENDENCY_GRAPH_INVALID
    E5305 = "E5305"  # TOPOLOGICAL_SORT_FAILED

    # E5400-E5499: Context management
    E5400 = "E5400"  # CONTEXT_INJECTION_FAILED
    E5401 = "E5401"  # SECRET_RESOLUTION_FAILED
    E5402 = "E5402"  # INPUT_BINDING_FAILED
    E5403 = "E5403"  # CONTEXT_VALIDATION_FAILED
    E5404 = "E5404"  # ACCESS_DENIED
    E5405 = "E5405"  # MISSING_REQUIRED_INPUT

    # E5500-E5599: Resource planning
    E5500 = "E5500"  # RESOURCE_ESTIMATION_FAILED
    E5501 = "E5501"  # TOKEN_BUDGET_EXCEEDED
    E5502 = "E5502"  # CPU_LIMIT_EXCEEDED
    E5503 = "E5503"  # MEMORY_LIMIT_EXCEEDED
    E5504 = "E5504"  # TIMEOUT_TOO_SHORT
    E5505 = "E5505"  # RESOURCE_UNAVAILABLE

    # E5600-E5699: Plan validation
    E5600 = "E5600"  # PLAN_VALIDATION_FAILED
    E5601 = "E5601"  # SYNTAX_VALIDATION_FAILED
    E5602 = "E5602"  # SEMANTIC_VALIDATION_FAILED
    E5603 = "E5603"  # FEASIBILITY_VALIDATION_FAILED
    E5604 = "E5604"  # SECURITY_VALIDATION_FAILED
    E5605 = "E5605"  # INVALID_TASK_FORMAT
    E5606 = "E5606"  # MISSING_REQUIRED_FIELD

    # E5700-E5799: Execution monitoring
    E5700 = "E5700"  # MONITORING_FAILED
    E5701 = "E5701"  # TASK_COMPLETION_TIMEOUT
    E5702 = "E5702"  # FAILURE_DETECTION_ERROR
    E5703 = "E5703"  # ESCALATION_FAILED
    E5704 = "E5704"  # RETRY_POLICY_INVALID

    # E5800-E5899: Plan persistence
    E5800 = "E5800"  # PERSISTENCE_FAILED
    E5801 = "E5801"  # PLAN_SAVE_FAILED
    E5802 = "E5802"  # PLAN_LOAD_FAILED
    E5803 = "E5803"  # PLAN_VERSION_CONFLICT
    E5804 = "E5804"  # AUDIT_LOG_FAILED

    # E5900-E5999: Multi-agent coordination
    E5900 = "E5900"  # AGENT_COORDINATION_FAILED
    E5901 = "E5901"  # AGENT_UNAVAILABLE
    E5902 = "E5902"  # CAPABILITY_MISMATCH
    E5903 = "E5903"  # AGENT_ASSIGNMENT_FAILED
    E5904 = "E5904"  # LOAD_BALANCING_FAILED
    E5905 = "E5905"  # AGENT_HEALTH_CHECK_FAILED


# Error code metadata
ERROR_MESSAGES = {
    # Plan cache and retrieval
    ErrorCode.E5000: "Plan cache operation failed",
    ErrorCode.E5001: "Goal text exceeds maximum length of 100,000 characters",
    ErrorCode.E5002: "Plan not found in cache or persistence layer",
    ErrorCode.E5003: "Failed to write plan to cache",
    ErrorCode.E5004: "Goal text contains invalid characters or injection patterns",
    ErrorCode.E5005: "Failed to read plan from cache",

    # Goal decomposition
    ErrorCode.E5100: "Goal decomposition failed",
    ErrorCode.E5101: "LLM-based decomposition encountered an error",
    ErrorCode.E5102: "No suitable template match found for goal",
    ErrorCode.E5103: "Invalid or unsupported goal type",
    ErrorCode.E5104: "Recursive decomposition exceeded maximum depth",
    ErrorCode.E5105: "Goal decomposition exceeded timeout threshold",
    ErrorCode.E5106: "LLM response could not be parsed",
    ErrorCode.E5107: "Goal complexity exceeds system capabilities",

    # Task orchestration
    ErrorCode.E5200: "Task orchestration failed",
    ErrorCode.E5201: "Invalid task state transition attempted",
    ErrorCode.E5202: "Failed to dispatch task to execution layer",
    ErrorCode.E5203: "Task execution exceeded timeout",
    ErrorCode.E5204: "Task execution failed",
    ErrorCode.E5205: "Maximum retry attempts exceeded",
    ErrorCode.E5206: "Parallel task execution encountered error",
    ErrorCode.E5207: "Task not found in execution plan",

    # Dependency resolution
    ErrorCode.E5300: "Dependency resolution failed",
    ErrorCode.E5301: "Circular dependency detected in task graph",
    ErrorCode.E5302: "Task dependency is missing or undefined",
    ErrorCode.E5303: "Invalid dependency type specified",
    ErrorCode.E5304: "Dependency graph structure is invalid",
    ErrorCode.E5305: "Topological sort of task graph failed",

    # Context management
    ErrorCode.E5400: "Context injection failed",
    ErrorCode.E5401: "Failed to resolve secret reference",
    ErrorCode.E5402: "Failed to bind input from prior task output",
    ErrorCode.E5403: "Execution context validation failed",
    ErrorCode.E5404: "Access denied for requested context scope",
    ErrorCode.E5405: "Required input is missing from context",

    # Resource planning
    ErrorCode.E5500: "Resource estimation failed",
    ErrorCode.E5501: "Token budget exceeded for plan",
    ErrorCode.E5502: "CPU limit exceeded for task",
    ErrorCode.E5503: "Memory limit exceeded for task",
    ErrorCode.E5504: "Task timeout is too short for estimated execution",
    ErrorCode.E5505: "Required resources are unavailable",

    # Plan validation
    ErrorCode.E5600: "Plan validation failed",
    ErrorCode.E5601: "Syntax validation failed",
    ErrorCode.E5602: "Semantic validation failed",
    ErrorCode.E5603: "Feasibility validation failed",
    ErrorCode.E5604: "Security validation failed",
    ErrorCode.E5605: "Invalid task format",
    ErrorCode.E5606: "Required field is missing",

    # Execution monitoring
    ErrorCode.E5700: "Execution monitoring failed",
    ErrorCode.E5701: "Task completion monitoring timed out",
    ErrorCode.E5702: "Failure detection encountered error",
    ErrorCode.E5703: "Task failure escalation failed",
    ErrorCode.E5704: "Retry policy configuration is invalid",

    # Plan persistence
    ErrorCode.E5800: "Plan persistence operation failed",
    ErrorCode.E5801: "Failed to save plan to persistence layer",
    ErrorCode.E5802: "Failed to load plan from persistence layer",
    ErrorCode.E5803: "Plan version conflict detected",
    ErrorCode.E5804: "Failed to write audit log entry",

    # Multi-agent coordination
    ErrorCode.E5900: "Agent coordination failed",
    ErrorCode.E5901: "Required agent is unavailable",
    ErrorCode.E5902: "Agent capability does not match task requirements",
    ErrorCode.E5903: "Failed to assign task to agent",
    ErrorCode.E5904: "Load balancing across agents failed",
    ErrorCode.E5905: "Agent health check failed",
}


# Recoverable vs non-recoverable errors
RECOVERABLE_ERRORS = {
    ErrorCode.E5105,  # DECOMPOSITION_TIMEOUT
    ErrorCode.E5203,  # TASK_TIMEOUT
    ErrorCode.E5901,  # AGENT_UNAVAILABLE
    ErrorCode.E5905,  # AGENT_HEALTH_CHECK_FAILED
    ErrorCode.E5003,  # CACHE_WRITE_FAILED
    ErrorCode.E5005,  # CACHE_READ_FAILED
}


@dataclass
class PlanningError(Exception):
    """Base exception for L05 Planning Layer errors."""

    code: ErrorCode
    message: str
    details: Optional[dict] = None
    recovery_suggestion: Optional[str] = None

    def __str__(self) -> str:
        """String representation of error."""
        base = f"{self.code}: {self.message}"
        if self.details:
            base += f" | Details: {self.details}"
        if self.recovery_suggestion:
            base += f" | Suggestion: {self.recovery_suggestion}"
        return base

    @property
    def is_recoverable(self) -> bool:
        """Check if error is recoverable (retry allowed)."""
        return self.code in RECOVERABLE_ERRORS

    @classmethod
    def from_code(cls, code: ErrorCode, details: Optional[dict] = None,
                  recovery_suggestion: Optional[str] = None) -> "PlanningError":
        """Create error from error code."""
        message = ERROR_MESSAGES.get(code, "Unknown planning error")
        return cls(code=code, message=message, details=details,
                   recovery_suggestion=recovery_suggestion)

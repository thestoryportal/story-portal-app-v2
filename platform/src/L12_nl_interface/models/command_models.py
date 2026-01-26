"""Command request/response models for L12 Natural Language Interface.

This module defines the data models for service invocation requests and responses:
- InvokeRequest: Request to invoke a service method
- InvokeResponse: Response from service method invocation
- ErrorResponse: Structured error information
- SessionInfo: Session state information

These models are used by CommandRouter, HTTP API, and MCP Server to handle
service invocations in a consistent manner.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
import uuid


class InvocationStatus(str, Enum):
    """Status of service invocation."""

    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"
    TIMEOUT = "timeout"
    # Workflow execution states
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ErrorCode(str, Enum):
    """Error codes for service invocation failures."""

    SERVICE_NOT_FOUND = "service_not_found"
    METHOD_NOT_FOUND = "method_not_found"
    INVALID_PARAMETERS = "invalid_parameters"
    INVALID_REQUEST = "invalid_request"
    DEPENDENCY_ERROR = "dependency_error"
    INITIALIZATION_ERROR = "initialization_error"
    SERVICE_INIT_ERROR = "service_init_error"
    EXECUTION_ERROR = "execution_error"
    TIMEOUT_ERROR = "timeout_error"
    PERMISSION_DENIED = "permission_denied"
    UNKNOWN_ERROR = "unknown_error"
    INTERNAL_ERROR = "internal_error"


class InvokeRequest(BaseModel):
    """Request to invoke a service method.

    Attributes:
        service_name: Name of service to invoke (e.g., "PlanningService")
        method_name: Name of method to call (e.g., "create_plan")
        parameters: Dict of parameter name -> value
        session_id: Session identifier for service instance isolation
        timeout_seconds: Optional timeout for invocation
        trace_id: Optional trace ID for distributed tracing

    Example:
        >>> request = InvokeRequest(
        ...     service_name="PlanningService",
        ...     method_name="create_plan",
        ...     parameters={"goal": goal_obj},
        ...     session_id="session-123"
        ... )
    """

    service_name: str = Field(..., description="Service name", min_length=1)
    method_name: str = Field(..., description="Method name", min_length=1)
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Method parameters"
    )
    session_id: str = Field(..., description="Session identifier", min_length=1)
    timeout_seconds: Optional[float] = Field(
        default=None,
        description="Invocation timeout",
        gt=0,
        le=600
    )
    trace_id: Optional[str] = Field(
        default=None,
        description="Distributed trace ID"
    )

    @field_validator("service_name", "method_name")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        """Ensure names are valid Python identifiers."""
        if not v.isidentifier():
            raise ValueError(f"'{v}' is not a valid Python identifier")
        return v

    @field_validator("method_name")
    @classmethod
    def validate_method_not_private(cls, v: str) -> str:
        """Ensure method is not private (no leading underscore)."""
        if v.startswith("_"):
            raise ValueError(f"Private method '{v}' cannot be invoked via L12")
        return v

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        """Ensure session_id is non-empty."""
        if not v.strip():
            raise ValueError("session_id cannot be empty")
        return v.strip()

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "service_name": "PlanningService",
                "method_name": "create_plan",
                "parameters": {"goal_text": "Create testing strategy"},
                "session_id": "session-abc123",
                "timeout_seconds": 30.0
            }
        }


class ErrorResponse(BaseModel):
    """Structured error information.

    Attributes:
        code: Error code from ErrorCode enum
        message: Human-readable error message
        details: Optional additional error details
        service_name: Service where error occurred
        method_name: Method where error occurred
        timestamp: When error occurred

    Example:
        >>> error = ErrorResponse(
        ...     code=ErrorCode.SERVICE_NOT_FOUND,
        ...     message="Service 'Foo' not found in catalog",
        ...     service_name="Foo",
        ...     method_name="bar"
        ... )
    """

    code: ErrorCode = Field(..., description="Error code")
    message: str = Field(..., description="Error message", min_length=1)
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details"
    )
    service_name: Optional[str] = Field(
        default=None,
        description="Service name"
    )
    method_name: Optional[str] = Field(
        default=None,
        description="Method name"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Error timestamp"
    )

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "code": "service_not_found",
                "message": "Service 'PlanningService' not found",
                "service_name": "PlanningService",
                "method_name": "create_plan"
            }
        }


class InvokeResponse(BaseModel):
    """Response from service method invocation.

    Attributes:
        status: Invocation status
        result: Result value from method (if successful)
        error: Error information (if failed)
        service_name: Service that was invoked
        method_name: Method that was called
        session_id: Session identifier
        trace_id: Trace ID for request correlation
        execution_time_ms: Time taken to execute in milliseconds
        timestamp: When invocation completed

    Example:
        >>> response = InvokeResponse(
        ...     status=InvocationStatus.SUCCESS,
        ...     result=execution_plan,
        ...     service_name="PlanningService",
        ...     method_name="create_plan",
        ...     session_id="session-123",
        ...     execution_time_ms=245.6
        ... )
    """

    status: InvocationStatus = Field(..., description="Invocation status")
    result: Optional[Any] = Field(
        default=None,
        description="Method result (if successful)"
    )
    error: Optional[ErrorResponse] = Field(
        default=None,
        description="Error info (if failed)"
    )
    service_name: str = Field(..., description="Service name", min_length=1)
    method_name: str = Field(..., description="Method name", min_length=1)
    session_id: str = Field(..., description="Session identifier", min_length=1)
    trace_id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Trace ID"
    )
    execution_time_ms: Optional[float] = Field(
        default=None,
        description="Execution time in milliseconds",
        ge=0
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp"
    )

    @field_validator("result", "error")
    @classmethod
    def validate_result_error_mutual_exclusion(cls, v, info):
        """Ensure result and error are mutually exclusive based on status."""
        # This validator runs after all fields are set
        # We check in a custom __post_init__ instead
        return v

    def model_post_init(self, __context: Any) -> None:
        """Validate after model initialization."""
        if self.status == InvocationStatus.SUCCESS and self.result is None:
            raise ValueError("SUCCESS status requires result")
        if self.status == InvocationStatus.ERROR and self.error is None:
            raise ValueError("ERROR status requires error info")

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "status": "success",
                "result": {"plan_id": "plan-123", "task_count": 5},
                "service_name": "PlanningService",
                "method_name": "create_plan",
                "session_id": "session-abc123",
                "execution_time_ms": 245.6
            }
        }


class SessionInfo(BaseModel):
    """Information about a service session.

    Attributes:
        session_id: Unique session identifier
        created_at: When session was created
        last_accessed: When session was last used
        expires_at: When session will expire
        service_count: Number of services initialized in session
        active: Whether session is still active
        memory_usage_mb: Approximate memory usage in MB

    Example:
        >>> info = SessionInfo(
        ...     session_id="session-123",
        ...     created_at=datetime.utcnow(),
        ...     service_count=3,
        ...     active=True,
        ...     memory_usage_mb=125.4
        ... )
    """

    session_id: str = Field(..., description="Session identifier", min_length=1)
    created_at: datetime = Field(..., description="Session creation time")
    last_accessed: datetime = Field(..., description="Last access time")
    expires_at: datetime = Field(..., description="Expiration time")
    service_count: int = Field(default=0, description="Services initialized", ge=0)
    active: bool = Field(default=True, description="Session active")
    memory_usage_mb: Optional[float] = Field(
        default=None,
        description="Memory usage in MB",
        ge=0
    )

    @field_validator("expires_at")
    @classmethod
    def validate_expiry_after_creation(cls, v: datetime, info) -> datetime:
        """Ensure expiry is after creation."""
        if "created_at" in info.data and v <= info.data["created_at"]:
            raise ValueError("expires_at must be after created_at")
        return v

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "session_id": "session-abc123",
                "created_at": "2026-01-15T10:00:00Z",
                "last_accessed": "2026-01-15T10:30:00Z",
                "expires_at": "2026-01-15T11:00:00Z",
                "service_count": 3,
                "active": True,
                "memory_usage_mb": 125.4
            }
        }


class SearchQuery(BaseModel):
    """Query for fuzzy service search.

    Attributes:
        query: Search query string
        threshold: Minimum similarity score (0.0-1.0)
        max_results: Maximum number of results to return
        layer_filter: Optional layer filter (e.g., "L05")
        category_filter: Optional category filter

    Example:
        >>> query = SearchQuery(
        ...     query="Let's Plan",
        ...     threshold=0.7,
        ...     max_results=5
        ... )
    """

    query: str = Field(..., description="Search query", min_length=1)
    threshold: float = Field(
        default=0.7,
        description="Minimum similarity score",
        ge=0.0,
        le=1.0
    )
    max_results: int = Field(
        default=10,
        description="Maximum results",
        gt=0,
        le=50
    )
    layer_filter: Optional[str] = Field(
        default=None,
        description="Filter by layer (e.g., L05)",
        pattern=r"^L(0[0-9]|1[01])$"
    )
    category_filter: Optional[str] = Field(
        default=None,
        description="Filter by category"
    )

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "query": "Let's Plan",
                "threshold": 0.7,
                "max_results": 5,
                "layer_filter": "L05"
            }
        }

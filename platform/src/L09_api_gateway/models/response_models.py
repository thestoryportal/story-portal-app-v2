"""
Response models
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    """Health check status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class GatewayResponse(BaseModel):
    """Standard gateway response"""

    status_code: int = Field(..., description="HTTP status code")
    headers: Dict[str, str] = Field(default_factory=dict)
    body: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Standard error response format"""

    error: Dict[str, Any] = Field(..., description="Error details")
    timestamp: int = Field(
        default_factory=lambda: int(datetime.utcnow().timestamp() * 1000)
    )
    trace_id: Optional[str] = None
    request_id: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Health check response"""

    status: HealthStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="1.2.0")
    dependencies: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    uptime_seconds: Optional[int] = None


class AsyncOperationResponse(BaseModel):
    """Response for async operation submission"""

    operation_id: str
    status: str
    message: str = "Operation accepted"
    poll_url: Optional[str] = None
    estimated_completion_seconds: Optional[int] = None


class RateLimitHeaders(BaseModel):
    """Rate limit response headers"""

    limit: int = Field(..., description="Rate limit")
    remaining: int = Field(..., description="Remaining tokens")
    reset: int = Field(..., description="Reset timestamp")
    retry_after: Optional[int] = None

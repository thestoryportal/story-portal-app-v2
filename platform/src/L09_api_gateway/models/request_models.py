"""
Request models for API Gateway
"""

from datetime import datetime
from typing import Dict, Optional, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, validator
import re


class IdempotencyKey(BaseModel):
    """Idempotency key for request deduplication"""

    key: UUID = Field(..., description="UUID v4 idempotency key")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    ttl_seconds: int = Field(default=86400, description="24 hour TTL")

    @validator("key", pre=True)
    def validate_uuid(cls, v):
        """Validate UUID format"""
        if isinstance(v, str):
            try:
                return UUID(v)
            except ValueError:
                raise ValueError("Idempotency key must be valid UUID v4")
        return v


class RequestMetadata(BaseModel):
    """Metadata about the incoming request"""

    method: str = Field(..., description="HTTP method (GET, POST, etc.)")
    path: str = Field(..., description="Request path")
    headers: Dict[str, str] = Field(default_factory=dict)
    query_params: Dict[str, str] = Field(default_factory=dict)
    client_ip: str = Field(..., description="Client IP address")
    user_agent: Optional[str] = None
    content_type: Optional[str] = None
    content_length: int = Field(default=0)
    api_version: Optional[str] = None


class RequestContext(BaseModel):
    """Complete request context flowing through gateway pipeline"""

    # Unique identifiers
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    trace_id: str = Field(..., description="W3C Trace Context trace ID")
    span_id: str = Field(..., description="W3C Trace Context span ID")

    # Request metadata
    metadata: RequestMetadata

    # Authentication & Authorization
    consumer_id: Optional[str] = None
    tenant_id: Optional[str] = None
    tenant_type: Optional[str] = None
    oauth_scopes: list[str] = Field(default_factory=list)
    auth_method: Optional[str] = None

    # Rate limiting
    rate_limit_tier: Optional[str] = None
    tokens_consumed: int = Field(default=1)

    # Idempotency
    idempotency_key: Optional[UUID] = None
    is_replayed: bool = Field(default=False)

    # Timing
    received_at: datetime = Field(default_factory=datetime.utcnow)

    # Additional context
    extra: Dict[str, Any] = Field(default_factory=dict)

    @validator("trace_id")
    def validate_trace_id(cls, v):
        """Validate W3C Trace Context format"""
        # W3C format: 32 hex characters
        if not re.match(r"^[0-9a-f]{32}$", v):
            raise ValueError("Invalid trace_id format (must be 32 hex chars)")
        return v

    @validator("span_id")
    def validate_span_id(cls, v):
        """Validate W3C span ID format"""
        # W3C format: 16 hex characters
        if not re.match(r"^[0-9a-f]{16}$", v):
            raise ValueError("Invalid span_id format (must be 16 hex chars)")
        return v

    def to_headers(self) -> Dict[str, str]:
        """Convert context to headers for backend injection"""
        headers = {
            "X-Request-ID": self.request_id,
            "X-Trace-ID": self.trace_id,
            "X-Span-ID": self.span_id,
        }

        if self.consumer_id:
            headers["X-Consumer-ID"] = self.consumer_id

        if self.tenant_id:
            headers["X-Tenant-ID"] = self.tenant_id

        if self.tenant_type:
            headers["X-Tenant-Type"] = self.tenant_type

        if self.idempotency_key:
            headers["X-Idempotency-Key"] = str(self.idempotency_key)

        return headers

"""
Async operation and webhook models
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field, validator
import re


class OperationStatus(str, Enum):
    """Async operation status"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class WebhookDeliveryStatus(str, Enum):
    """Webhook delivery status"""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"


class WebhookConfig(BaseModel):
    """Webhook configuration"""
    url: str = Field(..., description="Webhook delivery URL")
    secret: str = Field(..., description="HMAC signature secret")
    max_retries: int = Field(default=5)
    retry_backoff_base_ms: int = Field(default=1000)

    @validator("url")
    def validate_url(cls, v):
        """Validate webhook URL for SSRF prevention"""
        # Must be HTTPS
        if not v.startswith("https://"):
            raise ValueError("Webhook URL must use HTTPS")

        # Block private IP ranges
        private_patterns = [
            r"^https?://127\.",
            r"^https?://10\.",
            r"^https?://172\.(1[6-9]|2[0-9]|3[0-1])\.",
            r"^https?://192\.168\.",
            r"^https?://169\.254\.",
            r"^https?://\[::1\]",
            r"^https?://\[fc[0-9a-f]{2}:",
            r"^https?://localhost",
        ]

        for pattern in private_patterns:
            if re.match(pattern, v, re.IGNORECASE):
                raise ValueError(f"Webhook URL blocked (SSRF prevention): {v}")

        return v


class AsyncOperation(BaseModel):
    """Async operation tracking"""

    operation_id: str = Field(..., description="Unique operation ID")
    consumer_id: str = Field(..., description="Consumer who initiated")
    tenant_id: str = Field(..., description="Tenant context")

    # Status
    status: OperationStatus = OperationStatus.QUEUED
    progress_pct: int = Field(default=0, ge=0, le=100)

    # Request context
    request_id: str = Field(..., description="Original request ID")
    route_id: str = Field(..., description="Route that handled request")
    request_payload: Optional[Dict[str, Any]] = None

    # Results
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    # Webhook delivery
    webhook_config: Optional[WebhookConfig] = None
    webhook_delivery_status: Optional[WebhookDeliveryStatus] = None
    webhook_delivery_attempts: int = Field(default=0)
    webhook_last_attempt: Optional[datetime] = None

    def is_terminal(self) -> bool:
        """Check if operation is in terminal state"""
        return self.status in [
            OperationStatus.COMPLETED,
            OperationStatus.FAILED,
            OperationStatus.EXPIRED,
        ]

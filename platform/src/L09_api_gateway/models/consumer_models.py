"""
Consumer and authentication models
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class AuthMethod(str, Enum):
    """Authentication methods supported"""
    API_KEY = "api_key"
    OAUTH_JWT = "oauth_jwt"
    MTLS = "mtls"


class ConsumerStatus(str, Enum):
    """Consumer account status"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"
    DELETED = "deleted"


class RateLimitTier(str, Enum):
    """Rate limit tiers"""
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class RateLimitQuota(BaseModel):
    """Rate limit quota configuration"""
    rps_limit: int = Field(..., description="Requests per second limit")
    burst_capacity: int = Field(..., description="Burst token capacity")
    daily_quota: int = Field(..., description="Daily request quota")


class ConsumerProfile(BaseModel):
    """Consumer profile with authentication and authorization info"""

    consumer_id: str = Field(..., description="Unique consumer identifier")
    tenant_id: str = Field(..., description="Tenant identifier")
    tenant_type: str = Field(default="ORGANIZATION", description="Tenant type")

    # Authentication
    auth_method: AuthMethod
    api_key_hash: Optional[str] = None  # bcrypt hash
    oauth_client_id: Optional[str] = None
    mtls_cert_fingerprint: Optional[str] = None

    # Authorization
    roles: List[str] = Field(default_factory=list)
    oauth_scopes: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)

    # Status
    status: ConsumerStatus = ConsumerStatus.ACTIVE

    # Rate limiting
    rate_limit_tier: RateLimitTier = RateLimitTier.STANDARD
    quota: Optional[RateLimitQuota] = None

    # Webhooks
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_access: Optional[datetime] = None

    # Credential rotation
    credential_expires_at: Optional[datetime] = None
    credential_rotation_due: bool = Field(default=False)


# Rate limit tier configurations
RATE_LIMIT_CONFIGS = {
    RateLimitTier.STANDARD: RateLimitQuota(
        rps_limit=100,
        burst_capacity=1000,
        daily_quota=100_000,
    ),
    RateLimitTier.PREMIUM: RateLimitQuota(
        rps_limit=1000,
        burst_capacity=10_000,
        daily_quota=1_000_000,
    ),
    RateLimitTier.ENTERPRISE: RateLimitQuota(
        rps_limit=10_000,
        burst_capacity=100_000,
        daily_quota=100_000_000,
    ),
}

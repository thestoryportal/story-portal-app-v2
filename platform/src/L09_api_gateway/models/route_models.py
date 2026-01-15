"""
Route and backend models
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class LoadBalancingStrategy(str, Enum):
    """Load balancing strategies"""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    RANDOM = "random"
    CONSISTENT_HASH = "consistent_hash"


class BackendTarget(BaseModel):
    """Backend service target"""
    service_id: str = Field(..., description="Backend service identifier")
    host: str = Field(..., description="Backend host")
    port: int = Field(..., description="Backend port")
    protocol: str = Field(default="https", description="http or https")
    weight: int = Field(default=1, description="Load balancing weight")
    healthy: bool = Field(default=True, description="Health status")
    base_path: str = Field(default="", description="Base path prefix")


class RouteDefinition(BaseModel):
    """Route definition for request routing"""

    route_id: str = Field(..., description="Unique route identifier")
    path_pattern: str = Field(..., description="Path pattern (glob)")
    methods: List[str] = Field(..., description="Allowed HTTP methods")

    # Backend configuration
    backends: List[BackendTarget] = Field(..., description="Backend targets")
    load_balancing: LoadBalancingStrategy = Field(
        default=LoadBalancingStrategy.ROUND_ROBIN
    )

    # Authentication & Authorization
    auth_required: bool = Field(default=True)
    required_scopes: List[str] = Field(default_factory=list)
    required_roles: List[str] = Field(default_factory=list)

    # Rate limiting
    cost_tokens: int = Field(default=1, description="Token cost for this route")

    # Timeouts and retries
    timeout_ms: int = Field(default=60000, description="Request timeout")
    max_retries: int = Field(default=3, description="Max retry attempts")
    retryable_status_codes: List[int] = Field(
        default_factory=lambda: [503, 504]
    )

    # Async operations
    is_async_operation: bool = Field(default=False)
    async_timeout_ms: int = Field(default=300000, description="5 minute default")

    # API versioning
    api_version: Optional[str] = None
    deprecated: bool = Field(default=False)
    deprecation_date: Optional[str] = None

    # Additional config
    config: Dict[str, Any] = Field(default_factory=dict)


class RouteMatch(BaseModel):
    """Result of route matching"""
    route: RouteDefinition
    path_params: Dict[str, str] = Field(default_factory=dict)
    selected_backend: BackendTarget

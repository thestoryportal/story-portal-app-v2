"""
L11 Integration Layer - Service Registry Models.

Models for service discovery, registration, and health tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any
from uuid import uuid4


class ServiceStatus(str, Enum):
    """Status of a registered service."""

    HEALTHY = "healthy"  # Service is operational
    UNHEALTHY = "unhealthy"  # Service is failing health checks
    DEGRADED = "degraded"  # Service is operational but degraded
    UNKNOWN = "unknown"  # Health status unknown


class HealthCheckType(str, Enum):
    """Type of health check to perform."""

    HTTP = "http"  # HTTP GET endpoint check
    TCP = "tcp"  # TCP socket connection check
    GRPC = "grpc"  # gRPC health check
    REDIS = "redis"  # Redis PING check


@dataclass
class HealthCheck:
    """Configuration for service health checking."""

    check_type: HealthCheckType
    endpoint: str  # URL, host:port, or connection string
    interval_sec: int = 30  # Check interval in seconds
    timeout_sec: int = 5  # Check timeout in seconds
    failure_threshold: int = 3  # Consecutive failures before unhealthy
    success_threshold: int = 1  # Consecutive successes before healthy
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional check config


@dataclass
class ServiceInfo:
    """
    Information about a registered service in the integration layer.

    Services represent layer instances that can be discovered and communicated with.
    """

    service_id: str  # Unique identifier for this service instance
    service_name: str  # Layer name (e.g., "L02_runtime", "L03_tool_execution")
    service_version: str  # Service version (e.g., "0.1.0")
    endpoint: str  # Base URL or connection string (e.g., "http://localhost:8002")
    status: ServiceStatus = ServiceStatus.UNKNOWN
    health_check: Optional[HealthCheck] = None
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_health_check: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional service metadata
    capabilities: list[str] = field(default_factory=list)  # Service capabilities
    tags: list[str] = field(default_factory=list)  # Service tags for filtering

    @classmethod
    def create(
        cls,
        service_name: str,
        service_version: str,
        endpoint: str,
        health_check: Optional[HealthCheck] = None,
        metadata: Optional[Dict[str, Any]] = None,
        capabilities: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
    ) -> "ServiceInfo":
        """Factory method to create a new ServiceInfo with generated UUID."""
        return cls(
            service_id=str(uuid4()),
            service_name=service_name,
            service_version=service_version,
            endpoint=endpoint,
            status=ServiceStatus.UNKNOWN,
            health_check=health_check,
            registered_at=datetime.now(timezone.utc),
            metadata=metadata or {},
            capabilities=capabilities or [],
            tags=tags or [],
        )

    def update_health(self, status: ServiceStatus) -> None:
        """Update health status and timestamp."""
        self.status = status
        self.last_health_check = datetime.now(timezone.utc)

    def update_heartbeat(self) -> None:
        """Update heartbeat timestamp."""
        self.last_heartbeat = datetime.now(timezone.utc)

    def is_healthy(self) -> bool:
        """Check if service is healthy."""
        return self.status == ServiceStatus.HEALTHY

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "service_id": self.service_id,
            "service_name": self.service_name,
            "service_version": self.service_version,
            "endpoint": self.endpoint,
            "status": self.status.value,
            "health_check": {
                "check_type": self.health_check.check_type.value,
                "endpoint": self.health_check.endpoint,
                "interval_sec": self.health_check.interval_sec,
                "timeout_sec": self.health_check.timeout_sec,
                "failure_threshold": self.health_check.failure_threshold,
                "success_threshold": self.health_check.success_threshold,
                "metadata": self.health_check.metadata,
            } if self.health_check else None,
            "registered_at": self.registered_at.isoformat(),
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "metadata": self.metadata,
            "capabilities": self.capabilities,
            "tags": self.tags,
        }

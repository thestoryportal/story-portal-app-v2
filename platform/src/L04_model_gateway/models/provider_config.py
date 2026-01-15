"""
L04 Model Gateway Layer - Provider Configuration Models

Defines provider configurations and health status.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict
from datetime import datetime
from enum import Enum


class ProviderStatus(Enum):
    """Status of a provider"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class CircuitState(Enum):
    """Circuit breaker state"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class ProviderHealth:
    """Health status of a provider"""
    provider_id: str
    status: ProviderStatus
    circuit_state: CircuitState
    last_check: datetime
    consecutive_failures: int = 0
    last_failure_time: Optional[datetime] = None
    average_latency_ms: Optional[int] = None
    error_rate: float = 0.0
    metadata: Dict = field(default_factory=dict)

    def is_available(self) -> bool:
        """Check if provider is available for requests"""
        return (
            self.status in [ProviderStatus.HEALTHY, ProviderStatus.DEGRADED]
            and self.circuit_state != CircuitState.OPEN
        )

    def can_accept_request(self) -> bool:
        """Check if provider can accept new requests"""
        if self.circuit_state == CircuitState.OPEN:
            return False
        if self.circuit_state == CircuitState.HALF_OPEN:
            # In half-open state, allow limited requests to test recovery
            return True
        return self.status != ProviderStatus.UNAVAILABLE

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "provider_id": self.provider_id,
            "status": self.status.value,
            "circuit_state": self.circuit_state.value,
            "last_check": self.last_check.isoformat(),
            "consecutive_failures": self.consecutive_failures,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "average_latency_ms": self.average_latency_ms,
            "error_rate": self.error_rate,
            "metadata": self.metadata
        }


@dataclass
class ProviderConfig:
    """
    Provider configuration

    Defines how to connect to and interact with a provider.
    """
    provider_id: str
    display_name: str
    base_url: str
    api_key_env_var: Optional[str] = None
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay_seconds: int = 1
    supports_streaming: bool = True
    supports_batch: bool = False
    rate_limit_rpm: int = 60
    rate_limit_tpm: int = 100000
    circuit_breaker_enabled: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: int = 60
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "provider_id": self.provider_id,
            "display_name": self.display_name,
            "base_url": self.base_url,
            "api_key_env_var": self.api_key_env_var,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "retry_delay_seconds": self.retry_delay_seconds,
            "supports_streaming": self.supports_streaming,
            "supports_batch": self.supports_batch,
            "rate_limit_rpm": self.rate_limit_rpm,
            "rate_limit_tpm": self.rate_limit_tpm,
            "circuit_breaker_enabled": self.circuit_breaker_enabled,
            "circuit_breaker_failure_threshold": self.circuit_breaker_failure_threshold,
            "circuit_breaker_recovery_timeout": self.circuit_breaker_recovery_timeout,
            "metadata": self.metadata
        }

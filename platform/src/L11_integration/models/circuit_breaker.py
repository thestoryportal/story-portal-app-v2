"""
L11 Integration Layer - Circuit Breaker Models.

Models for circuit breaker pattern implementation for failure isolation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class CircuitState(str, Enum):
    """State of a circuit breaker."""

    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"  # Circuit broken, requests fail fast
    HALF_OPEN = "half_open"  # Testing recovery, limited requests allowed


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = 5  # Number of failures before opening circuit
    success_threshold: int = 2  # Number of successes to close from half-open
    timeout_sec: int = 60  # Seconds to wait before attempting recovery
    half_open_requests: int = 3  # Number of requests to allow in half-open state
    error_rate_threshold: float = 0.5  # Error rate (0.0-1.0) to trigger open
    window_size_sec: int = 60  # Time window for error rate calculation


@dataclass
class CircuitBreakerState:
    """
    State of a circuit breaker for a specific service.

    Circuit breakers protect against cascading failures by failing fast
    when a downstream service is experiencing issues.
    """

    service_name: str  # Name of the service this circuit protects
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0  # Consecutive failures in current state
    success_count: int = 0  # Consecutive successes in half-open state
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    opened_at: Optional[datetime] = None  # When circuit was opened
    half_opened_at: Optional[datetime] = None  # When circuit entered half-open
    closed_at: Optional[datetime] = None  # When circuit was closed
    total_requests: int = 0  # Total requests in current window
    failed_requests: int = 0  # Failed requests in current window
    window_start: datetime = field(default_factory=datetime.utcnow)
    config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)

    def record_success(self) -> None:
        """Record a successful request."""
        self.total_requests += 1
        self.success_count += 1
        self.failure_count = 0  # Reset failure count on success
        self.last_success_time = datetime.utcnow()

        # Transition from HALF_OPEN to CLOSED if threshold met
        if self.state == CircuitState.HALF_OPEN:
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.closed_at = datetime.utcnow()
                self.success_count = 0
                self.failed_requests = 0  # Reset error tracking

    def record_failure(self) -> None:
        """Record a failed request."""
        self.total_requests += 1
        self.failed_requests += 1
        self.failure_count += 1
        self.success_count = 0  # Reset success count on failure
        self.last_failure_time = datetime.utcnow()

        # Transition from CLOSED to OPEN if threshold exceeded
        if self.state == CircuitState.CLOSED:
            error_rate = self.get_error_rate()
            if (self.failure_count >= self.config.failure_threshold or
                error_rate >= self.config.error_rate_threshold):
                self.state = CircuitState.OPEN
                self.opened_at = datetime.utcnow()

        # Transition from HALF_OPEN back to OPEN on failure
        elif self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.opened_at = datetime.utcnow()

    def can_attempt_request(self) -> bool:
        """Check if a request can be attempted given current circuit state."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if timeout has elapsed to try half-open
            if self.opened_at:
                elapsed = (datetime.utcnow() - self.opened_at).total_seconds()
                if elapsed >= self.config.timeout_sec:
                    self.state = CircuitState.HALF_OPEN
                    self.half_opened_at = datetime.utcnow()
                    self.success_count = 0
                    self.failure_count = 0
                    return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            # Allow limited requests in half-open state
            return self.success_count + self.failure_count < self.config.half_open_requests

        return False

    def get_error_rate(self) -> float:
        """Calculate current error rate."""
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests

    def reset_window(self) -> None:
        """Reset the time window for error rate calculation."""
        elapsed = (datetime.utcnow() - self.window_start).total_seconds()
        if elapsed >= self.config.window_size_sec:
            self.total_requests = 0
            self.failed_requests = 0
            self.window_start = datetime.utcnow()

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "service_name": self.service_name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_success_time": self.last_success_time.isoformat() if self.last_success_time else None,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "half_opened_at": self.half_opened_at.isoformat() if self.half_opened_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "error_rate": self.get_error_rate(),
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "success_threshold": self.config.success_threshold,
                "timeout_sec": self.config.timeout_sec,
                "half_open_requests": self.config.half_open_requests,
                "error_rate_threshold": self.config.error_rate_threshold,
            },
        }

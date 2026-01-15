"""
Circuit breaker models
"""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class CircuitBreakerState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"          # Normal operation
    OPEN = "open"              # Fast-fail mode
    HALF_OPEN = "half_open"    # Testing recovery
    RECOVERING = "recovering"   # Ramping up traffic


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration"""

    # Failure detection
    error_rate_threshold: float = Field(
        default=0.5, description="50% error rate triggers opening"
    )
    error_sample_window_ms: int = Field(
        default=60000, description="1 minute window"
    )
    min_requests_threshold: int = Field(
        default=10, description="Minimum requests to measure"
    )

    # State transitions
    open_timeout_ms: int = Field(default=60000, description="1 minute timeout")
    half_open_success_threshold: int = Field(
        default=5, description="5 successes to close"
    )

    # Recovery
    ramp_up_duration_ms: int = Field(default=300000, description="5 minutes")
    ramp_up_initial_traffic_pct: int = Field(default=10, description="Start at 10%")
    max_open_duration_ms: int = Field(default=1800000, description="30 minutes max")


class CircuitBreakerStats(BaseModel):
    """Circuit breaker statistics"""

    current_state: CircuitBreakerState = CircuitBreakerState.CLOSED
    last_state_change: datetime = Field(default_factory=datetime.utcnow)

    # Request stats
    error_count: int = Field(default=0)
    request_count: int = Field(default=0)
    error_rate: float = Field(default=0.0)

    # Half-open state
    success_count_in_half_open: int = Field(default=0)

    # Recovery state
    traffic_ramp_pct: int = Field(default=100, description="0-100%")

    def should_allow_request(self) -> bool:
        """Check if request should be allowed based on state"""
        if self.current_state == CircuitBreakerState.CLOSED:
            return True
        elif self.current_state == CircuitBreakerState.OPEN:
            return False
        elif self.current_state == CircuitBreakerState.HALF_OPEN:
            return True  # Allow probe request
        elif self.current_state == CircuitBreakerState.RECOVERING:
            # Allow based on ramp-up percentage
            import random
            return random.random() * 100 < self.traffic_ramp_pct
        return False

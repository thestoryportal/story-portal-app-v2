"""
L07 Learning Layer - Circuit Breaker

Circuit breaker pattern implementation for fault tolerance and error handling.
Provides automatic failure detection, graceful degradation, and recovery.
"""

import asyncio
import logging
import functools
from typing import Dict, Any, Optional, Callable, TypeVar, Awaitable
from datetime import datetime, timezone
from enum import Enum
import time

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Failing, rejecting requests
    HALF_OPEN = "HALF_OPEN"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker for fault tolerance.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Circuit tripped, requests fail fast
    - HALF_OPEN: Testing recovery, allowing limited requests

    Transitions:
    - CLOSED -> OPEN: After failure_threshold consecutive failures
    - OPEN -> HALF_OPEN: After recovery_timeout seconds
    - HALF_OPEN -> CLOSED: On successful request
    - HALF_OPEN -> OPEN: On failed request
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        success_threshold: int = 1,
    ):
        """Initialize circuit breaker.

        Args:
            name: Name for identification
            failure_threshold: Failures before opening circuit
            recovery_timeout: Seconds before attempting recovery
            success_threshold: Successes needed to close from half-open
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._last_state_change: float = time.time()
        self._half_open_successes = 0

        logger.debug(f"CircuitBreaker '{name}' initialized (threshold={failure_threshold})")

    @property
    def state(self) -> str:
        """Get current state as string."""
        return self._state.value

    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._failure_count

    def allow_request(self) -> bool:
        """Check if request should be allowed.

        Returns:
            True if request can proceed, False if should fail fast
        """
        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self._last_failure_time is not None:
                elapsed = time.time() - self._last_failure_time
                if elapsed >= self.recovery_timeout:
                    # Transition to half-open
                    self._transition_to(CircuitState.HALF_OPEN)
                    return True
            return False

        if self._state == CircuitState.HALF_OPEN:
            # Allow limited requests in half-open state
            return True

        return False

    def record_success(self) -> None:
        """Record a successful operation."""
        self._success_count += 1

        if self._state == CircuitState.HALF_OPEN:
            self._half_open_successes += 1
            if self._half_open_successes >= self.success_threshold:
                # Service recovered, close circuit
                self._transition_to(CircuitState.CLOSED)
                logger.info(f"CircuitBreaker '{self.name}' closed after recovery")

    def record_failure(self, error: Optional[Exception] = None) -> None:
        """Record a failed operation.

        Args:
            error: Optional exception that caused the failure
        """
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.CLOSED:
            if self._failure_count >= self.failure_threshold:
                self._transition_to(CircuitState.OPEN)
                logger.warning(
                    f"CircuitBreaker '{self.name}' opened after "
                    f"{self._failure_count} failures"
                )

        elif self._state == CircuitState.HALF_OPEN:
            # Failed during recovery test, re-open
            self._transition_to(CircuitState.OPEN)
            logger.warning(
                f"CircuitBreaker '{self.name}' re-opened after "
                "failed recovery test"
            )

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state.

        Args:
            new_state: Target state
        """
        old_state = self._state
        self._state = new_state
        self._last_state_change = time.time()

        if new_state == CircuitState.CLOSED:
            # Reset counters on close
            self._failure_count = 0
            self._half_open_successes = 0

        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_successes = 0

        logger.debug(
            f"CircuitBreaker '{self.name}' transitioned: "
            f"{old_state.value} -> {new_state.value}"
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics.

        Returns:
            Dictionary of metrics
        """
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_failure_time": self._last_failure_time,
            "last_state_change": self._last_state_change,
        }

    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._half_open_successes = 0
        logger.info(f"CircuitBreaker '{self.name}' reset")


def with_circuit_breaker(
    circuit_breaker: CircuitBreaker,
    fallback: Optional[Callable[..., T]] = None
):
    """Decorator to wrap async function with circuit breaker.

    Args:
        circuit_breaker: Circuit breaker instance
        fallback: Optional fallback function if circuit is open

    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            if not circuit_breaker.allow_request():
                if fallback:
                    return await fallback(*args, **kwargs)
                raise CircuitOpenError(
                    f"Circuit '{circuit_breaker.name}' is open"
                )

            try:
                result = await func(*args, **kwargs)
                circuit_breaker.record_success()
                return result
            except Exception as e:
                circuit_breaker.record_failure(e)
                raise

        return wrapper
    return decorator


class CircuitOpenError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


async def retry_with_backoff(
    operation: Callable[..., Awaitable[T]],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
) -> T:
    """Execute operation with exponential backoff retry.

    Args:
        operation: Async function to retry
        max_retries: Maximum number of retries
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Add random jitter to delays

    Returns:
        Result of successful operation

    Raises:
        Last exception if all retries fail
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await operation()
        except Exception as e:
            last_exception = e

            if attempt == max_retries:
                # Final attempt failed
                logger.error(
                    f"Operation failed after {max_retries + 1} attempts: {e}"
                )
                raise

            # Calculate delay with exponential backoff
            delay = min(
                base_delay * (exponential_base ** attempt),
                max_delay
            )

            # Add jitter
            if jitter:
                import random
                delay = delay * (0.5 + random.random())

            logger.warning(
                f"Operation failed (attempt {attempt + 1}/{max_retries + 1}), "
                f"retrying in {delay:.2f}s: {e}"
            )

            await asyncio.sleep(delay)

    # Should not reach here, but just in case
    if last_exception:
        raise last_exception
    raise RuntimeError("Retry loop completed without result")


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""

    def __init__(self):
        """Initialize registry."""
        self._breakers: Dict[str, CircuitBreaker] = {}

    def get_or_create(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ) -> CircuitBreaker:
        """Get existing circuit breaker or create new one.

        Args:
            name: Circuit breaker name
            failure_threshold: Failures before opening
            recovery_timeout: Seconds before attempting recovery

        Returns:
            Circuit breaker instance
        """
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
            )
        return self._breakers[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name.

        Args:
            name: Circuit breaker name

        Returns:
            Circuit breaker or None if not found
        """
        return self._breakers.get(name)

    def list_all(self) -> Dict[str, CircuitBreaker]:
        """List all circuit breakers.

        Returns:
            Dictionary of name -> CircuitBreaker
        """
        return dict(self._breakers)

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all circuit breakers.

        Returns:
            Dictionary of name -> metrics
        """
        return {
            name: cb.get_metrics()
            for name, cb in self._breakers.items()
        }

    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for cb in self._breakers.values():
            cb.reset()


# Global registry for convenience
_global_registry = CircuitBreakerRegistry()


def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    """Get circuit breaker from global registry.

    Args:
        name: Circuit breaker name
        **kwargs: Arguments for circuit breaker creation

    Returns:
        Circuit breaker instance
    """
    return _global_registry.get_or_create(name, **kwargs)


def get_all_circuit_metrics() -> Dict[str, Dict[str, Any]]:
    """Get metrics for all circuit breakers in global registry.

    Returns:
        Dictionary of metrics
    """
    return _global_registry.get_all_metrics()

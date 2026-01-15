"""
L11 Integration Layer - Circuit Breaker.

Circuit breaker pattern for failure isolation and fast-fail behavior.
"""

import asyncio
import logging
from typing import Dict, Callable, TypeVar, Any, Optional
from datetime import datetime

from ..models import (
    CircuitBreakerState,
    CircuitState,
    CircuitBreakerConfig,
    IntegrationError,
    ErrorCode,
)


logger = logging.getLogger(__name__)


T = TypeVar('T')


class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures.

    Implements the circuit breaker pattern to fail fast when a service
    is experiencing issues.
    """

    def __init__(self):
        """Initialize circuit breaker manager."""
        self._circuits: Dict[str, CircuitBreakerState] = {}
        self._lock = asyncio.Lock()

    async def get_or_create_circuit(
        self,
        service_name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ) -> CircuitBreakerState:
        """
        Get or create a circuit breaker for a service.

        Args:
            service_name: Name of the service
            config: Circuit breaker configuration

        Returns:
            CircuitBreakerState
        """
        async with self._lock:
            if service_name not in self._circuits:
                self._circuits[service_name] = CircuitBreakerState(
                    service_name=service_name,
                    config=config or CircuitBreakerConfig(),
                )
                logger.info(f"Created circuit breaker for service: {service_name}")

            return self._circuits[service_name]

    async def execute(
        self,
        service_name: str,
        func: Callable[..., Any],
        *args: Any,
        config: Optional[CircuitBreakerConfig] = None,
        **kwargs: Any,
    ) -> Any:
        """
        Execute a function with circuit breaker protection.

        Args:
            service_name: Name of the service
            func: Function to execute (can be sync or async)
            *args: Function arguments
            config: Circuit breaker configuration
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            IntegrationError: If circuit is open or execution fails
        """
        # Get or create circuit
        circuit = await self.get_or_create_circuit(service_name, config)

        # Reset window if needed
        circuit.reset_window()

        # Check if request can be attempted
        if not circuit.can_attempt_request():
            raise IntegrationError.from_code(
                ErrorCode.E11201,
                details={
                    "service_name": service_name,
                    "state": circuit.state.value,
                    "opened_at": circuit.opened_at.isoformat() if circuit.opened_at else None,
                },
                recovery_suggestion=f"Wait {circuit.config.timeout_sec}s before retrying",
            )

        # Execute function
        try:
            # Handle both sync and async functions
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Record success
            await self.record_success(service_name)

            return result

        except Exception as e:
            # Record failure
            await self.record_failure(service_name)

            # Re-raise the exception
            raise

    async def record_success(self, service_name: str) -> None:
        """
        Record a successful request.

        Args:
            service_name: Name of the service
        """
        async with self._lock:
            if service_name in self._circuits:
                circuit = self._circuits[service_name]
                old_state = circuit.state
                circuit.record_success()

                if old_state != circuit.state:
                    logger.info(
                        f"Circuit breaker state changed for {service_name}: "
                        f"{old_state.value} -> {circuit.state.value}"
                    )

    async def record_failure(self, service_name: str) -> None:
        """
        Record a failed request.

        Args:
            service_name: Name of the service
        """
        async with self._lock:
            if service_name in self._circuits:
                circuit = self._circuits[service_name]
                old_state = circuit.state
                circuit.record_failure()

                if old_state != circuit.state:
                    logger.warning(
                        f"Circuit breaker state changed for {service_name}: "
                        f"{old_state.value} -> {circuit.state.value}"
                    )

    async def get_state(self, service_name: str) -> Optional[CircuitBreakerState]:
        """
        Get circuit breaker state for a service.

        Args:
            service_name: Name of the service

        Returns:
            CircuitBreakerState or None if not found
        """
        async with self._lock:
            return self._circuits.get(service_name)

    async def get_all_states(self) -> Dict[str, CircuitBreakerState]:
        """
        Get all circuit breaker states.

        Returns:
            Dictionary of service name to CircuitBreakerState
        """
        async with self._lock:
            return self._circuits.copy()

    async def reset_circuit(self, service_name: str) -> None:
        """
        Manually reset a circuit breaker to closed state.

        Args:
            service_name: Name of the service
        """
        async with self._lock:
            if service_name in self._circuits:
                circuit = self._circuits[service_name]
                circuit.state = CircuitState.CLOSED
                circuit.failure_count = 0
                circuit.success_count = 0
                circuit.failed_requests = 0
                circuit.closed_at = datetime.utcnow()
                logger.info(f"Manually reset circuit breaker for {service_name}")

    async def remove_circuit(self, service_name: str) -> None:
        """
        Remove a circuit breaker.

        Args:
            service_name: Name of the service
        """
        async with self._lock:
            if service_name in self._circuits:
                del self._circuits[service_name]
                logger.info(f"Removed circuit breaker for {service_name}")

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get circuit breaker metrics.

        Returns:
            Dictionary with metrics
        """
        metrics = {
            "total_circuits": len(self._circuits),
            "open": 0,
            "half_open": 0,
            "closed": 0,
            "circuits": {},
        }

        for service_name, circuit in self._circuits.items():
            if circuit.state == CircuitState.OPEN:
                metrics["open"] += 1
            elif circuit.state == CircuitState.HALF_OPEN:
                metrics["half_open"] += 1
            elif circuit.state == CircuitState.CLOSED:
                metrics["closed"] += 1

            metrics["circuits"][service_name] = {
                "state": circuit.state.value,
                "failure_count": circuit.failure_count,
                "error_rate": circuit.get_error_rate(),
                "total_requests": circuit.total_requests,
                "failed_requests": circuit.failed_requests,
            }

        return metrics


class CircuitBreakerMiddleware:
    """
    Middleware wrapper for circuit breaker functionality.

    Provides a decorator-style interface for circuit breaker protection.
    """

    def __init__(self, circuit_breaker: CircuitBreaker):
        """
        Initialize middleware.

        Args:
            circuit_breaker: CircuitBreaker instance
        """
        self.circuit_breaker = circuit_breaker

    def protect(
        self,
        service_name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ):
        """
        Decorator to protect a function with circuit breaker.

        Args:
            service_name: Name of the service
            config: Circuit breaker configuration

        Returns:
            Decorator function
        """
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                return await self.circuit_breaker.execute(
                    service_name,
                    func,
                    *args,
                    config=config,
                    **kwargs,
                )
            return wrapper
        return decorator

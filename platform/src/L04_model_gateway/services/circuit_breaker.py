"""
L04 Model Gateway Layer - Circuit Breaker Service

Circuit breaker pattern for provider failover and health management.
"""

import time
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging

from ..models import (
    CircuitState,
    ProviderHealth,
    ProviderStatus,
    CircuitBreakerError,
    L04ErrorCode
)

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """
    Circuit breaker for provider health management

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, reject requests
    - HALF_OPEN: Testing recovery, allow limited requests
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_requests: int = 3
    ):
        """
        Initialize circuit breaker

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds before attempting recovery
            half_open_max_requests: Max requests in half-open state
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_requests = half_open_max_requests

        # Circuit state per provider
        self._circuits: Dict[str, dict] = {}

        logger.info(
            f"CircuitBreaker initialized "
            f"(threshold={failure_threshold}, timeout={recovery_timeout}s)"
        )

    def get_state(self, provider: str) -> CircuitState:
        """
        Get current circuit state for provider

        Args:
            provider: Provider identifier

        Returns:
            Current CircuitState
        """
        circuit = self._get_or_create_circuit(provider)
        current_state = circuit["state"]

        # Check if OPEN circuit should transition to HALF_OPEN
        if current_state == CircuitState.OPEN:
            if self._should_attempt_reset(circuit):
                circuit["state"] = CircuitState.HALF_OPEN
                circuit["half_open_requests"] = 0
                logger.info(f"Circuit {provider}: OPEN -> HALF_OPEN")
                return CircuitState.HALF_OPEN

        return current_state

    async def call(self, provider: str, operation):
        """
        Execute operation through circuit breaker

        Args:
            provider: Provider identifier
            operation: Async callable to execute

        Returns:
            Result of operation

        Raises:
            CircuitBreakerError: If circuit is open
        """
        state = self.get_state(provider)

        # Check if circuit allows requests
        if state == CircuitState.OPEN:
            raise CircuitBreakerError(
                L04ErrorCode.E4701_PROVIDER_CIRCUIT_OPEN,
                f"Circuit breaker open for provider {provider}",
                {"provider": provider}
            )

        if state == CircuitState.HALF_OPEN:
            circuit = self._get_or_create_circuit(provider)
            if circuit["half_open_requests"] >= self.half_open_max_requests:
                raise CircuitBreakerError(
                    L04ErrorCode.E4701_PROVIDER_CIRCUIT_OPEN,
                    f"Circuit breaker half-open limit reached for {provider}",
                    {"provider": provider}
                )
            circuit["half_open_requests"] += 1

        # Execute operation
        try:
            result = await operation()
            self.record_success(provider)
            return result

        except Exception as e:
            self.record_failure(provider)
            raise

    def record_success(self, provider: str) -> None:
        """
        Record successful request

        Args:
            provider: Provider identifier
        """
        circuit = self._get_or_create_circuit(provider)
        circuit["consecutive_failures"] = 0
        circuit["last_success_time"] = time.time()

        # If in HALF_OPEN, check if we should close circuit
        if circuit["state"] == CircuitState.HALF_OPEN:
            if circuit["half_open_requests"] >= self.half_open_max_requests:
                circuit["state"] = CircuitState.CLOSED
                circuit["half_open_requests"] = 0
                logger.info(f"Circuit {provider}: HALF_OPEN -> CLOSED (recovered)")

    def record_failure(self, provider: str) -> None:
        """
        Record failed request

        Args:
            provider: Provider identifier
        """
        circuit = self._get_or_create_circuit(provider)
        circuit["consecutive_failures"] += 1
        circuit["last_failure_time"] = time.time()
        circuit["total_failures"] += 1

        # Check if we should open circuit
        if circuit["consecutive_failures"] >= self.failure_threshold:
            if circuit["state"] != CircuitState.OPEN:
                circuit["state"] = CircuitState.OPEN
                circuit["open_timestamp"] = time.time()
                logger.warning(
                    f"Circuit {provider}: {circuit['state'].value} -> OPEN "
                    f"({circuit['consecutive_failures']} failures)"
                )

        # If in HALF_OPEN and we get a failure, go back to OPEN
        elif circuit["state"] == CircuitState.HALF_OPEN:
            circuit["state"] = CircuitState.OPEN
            circuit["open_timestamp"] = time.time()
            logger.warning(f"Circuit {provider}: HALF_OPEN -> OPEN (recovery failed)")

    def get_health(self, provider: str) -> ProviderHealth:
        """
        Get provider health status

        Args:
            provider: Provider identifier

        Returns:
            ProviderHealth object
        """
        circuit = self._get_or_create_circuit(provider)
        state = self.get_state(provider)

        # Determine provider status based on circuit state
        if state == CircuitState.OPEN:
            status = ProviderStatus.UNAVAILABLE
        elif state == CircuitState.HALF_OPEN:
            status = ProviderStatus.DEGRADED
        else:
            status = ProviderStatus.HEALTHY

        # Calculate error rate
        total = circuit["total_requests"]
        failures = circuit["total_failures"]
        error_rate = (failures / total) if total > 0 else 0.0

        return ProviderHealth(
            provider_id=provider,
            status=status,
            circuit_state=state,
            last_check=datetime.utcnow(),
            consecutive_failures=circuit["consecutive_failures"],
            last_failure_time=(
                datetime.fromtimestamp(circuit["last_failure_time"])
                if circuit["last_failure_time"] else None
            ),
            error_rate=error_rate,
            metadata={
                "total_requests": total,
                "total_failures": failures,
                "last_success": circuit["last_success_time"]
            }
        )

    def reset(self, provider: str) -> None:
        """
        Reset circuit breaker for provider

        Args:
            provider: Provider identifier
        """
        if provider in self._circuits:
            circuit = self._circuits[provider]
            circuit["state"] = CircuitState.CLOSED
            circuit["consecutive_failures"] = 0
            circuit["half_open_requests"] = 0
            logger.info(f"Reset circuit breaker for {provider}")

    def _get_or_create_circuit(self, provider: str) -> dict:
        """Get or create circuit state for provider"""
        if provider not in self._circuits:
            self._circuits[provider] = {
                "state": CircuitState.CLOSED,
                "consecutive_failures": 0,
                "total_failures": 0,
                "total_requests": 0,
                "last_failure_time": None,
                "last_success_time": None,
                "open_timestamp": None,
                "half_open_requests": 0
            }

        # Increment request count
        self._circuits[provider]["total_requests"] += 1

        return self._circuits[provider]

    def _should_attempt_reset(self, circuit: dict) -> bool:
        """Check if circuit should attempt reset"""
        if circuit["open_timestamp"] is None:
            return False

        elapsed = time.time() - circuit["open_timestamp"]
        return elapsed >= self.recovery_timeout

    def get_stats(self) -> dict:
        """Get circuit breaker statistics"""
        stats = {
            "total_providers": len(self._circuits),
            "circuits_open": 0,
            "circuits_half_open": 0,
            "circuits_closed": 0,
            "providers": {}
        }

        for provider, circuit in self._circuits.items():
            state = circuit["state"]

            if state == CircuitState.OPEN:
                stats["circuits_open"] += 1
            elif state == CircuitState.HALF_OPEN:
                stats["circuits_half_open"] += 1
            else:
                stats["circuits_closed"] += 1

            stats["providers"][provider] = {
                "state": state.value,
                "consecutive_failures": circuit["consecutive_failures"],
                "total_failures": circuit["total_failures"],
                "total_requests": circuit["total_requests"]
            }

        return stats

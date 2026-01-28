"""
L11 Integration Layer - Circuit Breaker Tests.

Tests for the CircuitBreaker service.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock

from L11_integration.services import CircuitBreaker
from L11_integration.models import (
    CircuitBreakerConfig,
    CircuitState,
    IntegrationError,
)


@pytest.mark.l11
@pytest.mark.unit
class TestCircuitBreakerUnit:
    """Unit tests for CircuitBreaker."""

    @pytest.fixture
    def circuit_breaker(self):
        """Create circuit breaker for testing."""
        return CircuitBreaker(l11_bridge=None)

    @pytest.mark.asyncio
    async def test_create_circuit(self, circuit_breaker):
        """Test creating a circuit breaker."""
        circuit = await circuit_breaker.get_or_create_circuit("test_service")

        assert circuit is not None
        assert circuit.service_name == "test_service"
        assert circuit.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_execute_success(self, circuit_breaker):
        """Test successful execution through circuit breaker."""
        async def success_func():
            return "success"

        result = await circuit_breaker.execute("test_service", success_func)

        assert result == "success"
        circuit = await circuit_breaker.get_state("test_service")
        assert circuit.success_count >= 1

    @pytest.mark.asyncio
    async def test_execute_sync_function(self, circuit_breaker):
        """Test executing sync function through circuit breaker."""
        def sync_func():
            return "sync_result"

        result = await circuit_breaker.execute("test_service", sync_func)

        assert result == "sync_result"

    @pytest.mark.asyncio
    async def test_execute_failure_recorded(self, circuit_breaker):
        """Test that failures are recorded."""
        async def fail_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await circuit_breaker.execute("test_service", fail_func)

        circuit = await circuit_breaker.get_state("test_service")
        assert circuit.failure_count >= 1

    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold(self, circuit_breaker):
        """Test circuit opens after failure threshold."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            timeout_sec=60,
        )

        async def fail_func():
            raise ValueError("Test error")

        # Trigger failures to open circuit
        for i in range(3):
            try:
                await circuit_breaker.execute("test_service", fail_func, config=config)
            except (ValueError, IntegrationError):
                # After threshold, circuit opens and raises IntegrationError
                pass

        circuit = await circuit_breaker.get_state("test_service")
        assert circuit.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_circuit_rejects_requests(self, circuit_breaker):
        """Test that open circuit rejects requests."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            timeout_sec=60,
        )

        async def fail_func():
            raise ValueError("Test error")

        # Open the circuit - after 2 failures it opens
        for _ in range(2):
            try:
                await circuit_breaker.execute("test_service", fail_func, config=config)
            except (ValueError, IntegrationError):
                pass

        # Verify circuit is open
        circuit = await circuit_breaker.get_state("test_service")
        assert circuit.state == CircuitState.OPEN

        # Next call should reject immediately with IntegrationError
        with pytest.raises(IntegrationError) as exc_info:
            await circuit_breaker.execute("test_service", fail_func, config=config)

        assert "E11201" in str(exc_info.value.code) or "circuit" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_manual_reset(self, circuit_breaker):
        """Test manual circuit reset."""
        config = CircuitBreakerConfig(failure_threshold=1)

        async def fail_func():
            raise ValueError("Test error")

        # Open the circuit
        try:
            await circuit_breaker.execute("test_service", fail_func, config=config)
        except ValueError:
            pass

        circuit = await circuit_breaker.get_state("test_service")
        assert circuit.state == CircuitState.OPEN

        # Reset manually
        await circuit_breaker.reset_circuit("test_service")

        circuit = await circuit_breaker.get_state("test_service")
        assert circuit.state == CircuitState.CLOSED
        assert circuit.failure_count == 0

    @pytest.mark.asyncio
    async def test_get_all_states(self, circuit_breaker):
        """Test getting all circuit states."""
        await circuit_breaker.get_or_create_circuit("service_1")
        await circuit_breaker.get_or_create_circuit("service_2")
        await circuit_breaker.get_or_create_circuit("service_3")

        states = await circuit_breaker.get_all_states()

        assert len(states) == 3
        assert "service_1" in states
        assert "service_2" in states
        assert "service_3" in states

    @pytest.mark.asyncio
    async def test_remove_circuit(self, circuit_breaker):
        """Test removing a circuit."""
        await circuit_breaker.get_or_create_circuit("test_service")
        await circuit_breaker.remove_circuit("test_service")

        circuit = await circuit_breaker.get_state("test_service")
        assert circuit is None

    @pytest.mark.asyncio
    async def test_get_metrics(self, circuit_breaker):
        """Test getting circuit breaker metrics."""
        # Create circuits in different states
        await circuit_breaker.get_or_create_circuit("healthy_service")

        config = CircuitBreakerConfig(failure_threshold=1)

        async def fail_func():
            raise ValueError("Test error")

        try:
            await circuit_breaker.execute("failing_service", fail_func, config=config)
        except ValueError:
            pass

        metrics = circuit_breaker.get_metrics()

        assert metrics["total_circuits"] == 2
        assert metrics["closed"] >= 1  # healthy_service
        assert metrics["open"] >= 1    # failing_service
        assert "healthy_service" in metrics["circuits"]
        assert "failing_service" in metrics["circuits"]


@pytest.mark.l11
@pytest.mark.unit
class TestCircuitBreakerHalfOpen:
    """Tests for half-open state behavior."""

    @pytest.mark.asyncio
    async def test_half_open_success_closes_circuit(self):
        """Test that success in half-open state closes the circuit."""
        cb = CircuitBreaker(l11_bridge=None)
        config = CircuitBreakerConfig(
            failure_threshold=1,
            success_threshold=1,  # Single success closes circuit
            timeout_sec=0.1,  # Very short timeout for testing
        )

        async def fail_func():
            raise ValueError("error")

        async def success_func():
            return "ok"

        # Open the circuit
        try:
            await cb.execute("test", fail_func, config=config)
        except ValueError:
            pass

        circuit = await cb.get_state("test")
        assert circuit.state == CircuitState.OPEN

        # Wait for timeout to allow half-open transition
        await asyncio.sleep(0.15)

        # Execute should transition to HALF_OPEN and then success closes it
        result = await cb.execute("test", success_func, config=config)
        assert result == "ok"

        circuit = await cb.get_state("test")
        assert circuit.state == CircuitState.CLOSED

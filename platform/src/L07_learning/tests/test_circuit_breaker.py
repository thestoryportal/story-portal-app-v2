"""
L07 Learning Layer - Circuit Breaker Tests

Tests for circuit breaker pattern implementation.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta


@pytest.mark.l07
@pytest.mark.unit
class TestCircuitBreakerStates:
    """Tests for circuit breaker state transitions."""

    def test_initial_state_is_closed(self):
        """Test that circuit breaker starts in CLOSED state."""
        from L07_learning.services.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(name="test")
        assert cb.state == "CLOSED"

    def test_state_transitions_to_open_after_failures(self):
        """Test that circuit opens after threshold failures."""
        from L07_learning.services.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(name="test", failure_threshold=3)

        # Record failures
        for _ in range(3):
            cb.record_failure()

        assert cb.state == "OPEN"

    def test_state_transitions_to_half_open_after_timeout(self):
        """Test that circuit transitions to HALF_OPEN after timeout."""
        from L07_learning.services.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout=0.1)

        # Trip the circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"

        # Wait for recovery timeout
        import time
        time.sleep(0.15)

        # Should allow test request (transition to HALF_OPEN)
        assert cb.allow_request() is True
        assert cb.state == "HALF_OPEN"

    def test_state_returns_to_closed_on_success(self):
        """Test that circuit closes after success in HALF_OPEN state."""
        from L07_learning.services.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout=0.1)

        # Trip and wait
        cb.record_failure()
        cb.record_failure()
        import time
        time.sleep(0.15)

        # Allow request (enter HALF_OPEN)
        cb.allow_request()
        assert cb.state == "HALF_OPEN"

        # Record success
        cb.record_success()
        assert cb.state == "CLOSED"


@pytest.mark.l07
@pytest.mark.unit
class TestCircuitBreakerAllowRequest:
    """Tests for request allowing logic."""

    def test_allows_request_when_closed(self):
        """Test that requests are allowed when CLOSED."""
        from L07_learning.services.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(name="test")
        assert cb.allow_request() is True

    def test_denies_request_when_open(self):
        """Test that requests are denied when OPEN."""
        from L07_learning.services.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(name="test", failure_threshold=2)

        cb.record_failure()
        cb.record_failure()

        assert cb.allow_request() is False

    def test_allows_test_request_when_half_open(self):
        """Test that one request is allowed in HALF_OPEN state."""
        from L07_learning.services.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout=0.01)

        cb.record_failure()
        cb.record_failure()

        import time
        time.sleep(0.02)

        # First request should be allowed
        assert cb.allow_request() is True
        assert cb.state == "HALF_OPEN"


@pytest.mark.l07
@pytest.mark.unit
class TestCircuitBreakerRetry:
    """Tests for retry with exponential backoff."""

    @pytest.mark.asyncio
    async def test_retry_with_backoff_succeeds_eventually(self):
        """Test that retry eventually succeeds."""
        from L07_learning.services.circuit_breaker import retry_with_backoff

        call_count = 0

        async def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Transient error")
            return "success"

        result = await retry_with_backoff(
            flaky_operation,
            max_retries=5,
            base_delay=0.01
        )

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_raises_after_max_retries(self):
        """Test that retry raises after max retries exceeded."""
        from L07_learning.services.circuit_breaker import retry_with_backoff

        async def always_fails():
            raise Exception("Persistent error")

        with pytest.raises(Exception) as exc_info:
            await retry_with_backoff(
                always_fails,
                max_retries=3,
                base_delay=0.01
            )

        assert "Persistent error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_retry_respects_max_delay(self):
        """Test that backoff respects maximum delay."""
        from L07_learning.services.circuit_breaker import retry_with_backoff
        import time

        call_times = []

        async def failing_op():
            call_times.append(time.time())
            raise Exception("Error")

        try:
            await retry_with_backoff(
                failing_op,
                max_retries=5,
                base_delay=0.01,
                max_delay=0.05
            )
        except Exception:
            pass

        # Check that delays don't exceed max_delay
        for i in range(1, len(call_times)):
            delay = call_times[i] - call_times[i-1]
            assert delay < 0.1  # Allow some tolerance


@pytest.mark.l07
@pytest.mark.unit
class TestCircuitBreakerDecorator:
    """Tests for circuit breaker decorator."""

    @pytest.mark.asyncio
    async def test_decorator_tracks_failures(self):
        """Test that decorator tracks operation failures."""
        from L07_learning.services.circuit_breaker import (
            CircuitBreaker,
            with_circuit_breaker
        )

        cb = CircuitBreaker(name="test_op", failure_threshold=3)

        @with_circuit_breaker(cb)
        async def failing_operation():
            raise Exception("Operation failed")

        # Call and expect failures to be tracked
        for _ in range(3):
            try:
                await failing_operation()
            except Exception:
                pass

        assert cb.state == "OPEN"

    @pytest.mark.asyncio
    async def test_decorator_tracks_successes(self):
        """Test that decorator tracks operation successes."""
        from L07_learning.services.circuit_breaker import (
            CircuitBreaker,
            with_circuit_breaker
        )

        cb = CircuitBreaker(name="test_op", failure_threshold=3)

        @with_circuit_breaker(cb)
        async def successful_operation():
            return "success"

        result = await successful_operation()

        assert result == "success"
        assert cb.failure_count == 0


@pytest.mark.l07
@pytest.mark.unit
class TestCircuitBreakerMetrics:
    """Tests for circuit breaker metrics."""

    def test_get_metrics(self):
        """Test getting circuit breaker metrics."""
        from L07_learning.services.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(name="test")

        cb.record_failure()
        cb.record_failure()
        cb.record_success()

        metrics = cb.get_metrics()

        assert "state" in metrics
        assert "failure_count" in metrics
        assert "success_count" in metrics
        assert "last_failure_time" in metrics
        assert metrics["name"] == "test"

    def test_metrics_include_counts(self):
        """Test that metrics include correct counts."""
        from L07_learning.services.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(name="test", failure_threshold=5)

        for _ in range(3):
            cb.record_failure()
        for _ in range(5):
            cb.record_success()

        metrics = cb.get_metrics()

        assert metrics["failure_count"] == 3
        assert metrics["success_count"] == 5


@pytest.mark.l07
@pytest.mark.unit
class TestCircuitBreakerRegistry:
    """Tests for circuit breaker registry."""

    def test_get_or_create_circuit_breaker(self):
        """Test getting or creating circuit breakers."""
        from L07_learning.services.circuit_breaker import CircuitBreakerRegistry

        registry = CircuitBreakerRegistry()

        cb1 = registry.get_or_create("service_a")
        cb2 = registry.get_or_create("service_a")

        assert cb1 is cb2  # Same instance

    def test_list_circuit_breakers(self):
        """Test listing all circuit breakers."""
        from L07_learning.services.circuit_breaker import CircuitBreakerRegistry

        registry = CircuitBreakerRegistry()

        registry.get_or_create("service_a")
        registry.get_or_create("service_b")
        registry.get_or_create("service_c")

        breakers = registry.list_all()

        assert len(breakers) == 3
        assert "service_a" in breakers
        assert "service_b" in breakers
        assert "service_c" in breakers

    def test_get_all_metrics(self):
        """Test getting metrics for all circuit breakers."""
        from L07_learning.services.circuit_breaker import CircuitBreakerRegistry

        registry = CircuitBreakerRegistry()

        cb_a = registry.get_or_create("service_a")
        cb_b = registry.get_or_create("service_b")

        cb_a.record_failure()
        cb_b.record_success()

        all_metrics = registry.get_all_metrics()

        assert "service_a" in all_metrics
        assert "service_b" in all_metrics
        assert all_metrics["service_a"]["failure_count"] == 1
        assert all_metrics["service_b"]["success_count"] == 1

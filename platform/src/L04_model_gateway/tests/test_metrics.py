"""
L04 Model Gateway Layer - Metrics Tests

Tests for Prometheus metrics collection.
"""

import pytest
from unittest.mock import patch, MagicMock
from prometheus_client import REGISTRY

from L04_model_gateway.services.metrics import (
    MetricsManager,
    get_metrics_manager,
    metrics,
    INFERENCE_REQUESTS_TOTAL,
    CACHE_HITS_TOTAL,
    CACHE_MISSES_TOTAL,
    RATE_LIMIT_REJECTIONS_TOTAL,
    INFERENCE_LATENCY_SECONDS,
    CIRCUIT_BREAKER_STATE,
    ACTIVE_REQUESTS,
    TOKEN_USAGE_TOTAL,
    GATEWAY_INFO,
)


@pytest.mark.l04
@pytest.mark.unit
class TestMetricsManager:
    """Tests for MetricsManager class."""

    def test_initialize_sets_gateway_info(self):
        """Test that initialize sets gateway info metric."""
        manager = MetricsManager()
        manager.initialize(version="1.2.3")

        # Verify initialization flag
        assert manager._initialized is True

        # Second call should be no-op
        manager.initialize(version="different")
        # Should still be initialized from first call

    def test_get_metrics_manager_returns_singleton(self):
        """Test that get_metrics_manager returns the global instance."""
        manager1 = get_metrics_manager()
        manager2 = get_metrics_manager()

        assert manager1 is manager2
        assert manager1 is metrics


@pytest.mark.l04
@pytest.mark.unit
class TestInferenceMetrics:
    """Tests for inference request metrics."""

    def test_record_inference_request_increments_counter(self):
        """Test that record_inference_request increments the request counter."""
        manager = MetricsManager()

        # Get initial value
        initial = INFERENCE_REQUESTS_TOTAL.labels(
            provider="test_provider",
            model="test_model",
            status="success"
        )._value.get()

        # Record a request
        manager.record_inference_request(
            provider="test_provider",
            model="test_model",
            status="success",
            latency_seconds=0.5,
            input_tokens=100,
            output_tokens=50,
            cached=False
        )

        # Verify increment
        after = INFERENCE_REQUESTS_TOTAL.labels(
            provider="test_provider",
            model="test_model",
            status="success"
        )._value.get()

        assert after == initial + 1

    def test_record_inference_request_records_latency(self):
        """Test that record_inference_request records latency histogram."""
        manager = MetricsManager()

        # Get initial sum (histograms track sum of observations)
        histogram = INFERENCE_LATENCY_SECONDS.labels(
            provider="latency_test",
            model="latency_model"
        )
        initial_sum = histogram._sum.get()

        # Record a request
        manager.record_inference_request(
            provider="latency_test",
            model="latency_model",
            status="success",
            latency_seconds=1.5,
            input_tokens=100,
            output_tokens=50,
            cached=False
        )

        # Verify histogram observation added (sum should increase by latency value)
        after_sum = histogram._sum.get()
        assert after_sum >= initial_sum + 1.5

    def test_record_inference_request_records_token_usage(self):
        """Test that record_inference_request records token usage."""
        manager = MetricsManager()

        # Get initial values
        initial_input = TOKEN_USAGE_TOTAL.labels(
            direction="input",
            model="token_test"
        )._value.get()

        initial_output = TOKEN_USAGE_TOTAL.labels(
            direction="output",
            model="token_test"
        )._value.get()

        # Record a request
        manager.record_inference_request(
            provider="test",
            model="token_test",
            status="success",
            latency_seconds=0.5,
            input_tokens=100,
            output_tokens=50,
            cached=False
        )

        # Verify token increments
        after_input = TOKEN_USAGE_TOTAL.labels(
            direction="input",
            model="token_test"
        )._value.get()

        after_output = TOKEN_USAGE_TOTAL.labels(
            direction="output",
            model="token_test"
        )._value.get()

        assert after_input == initial_input + 100
        assert after_output == initial_output + 50


@pytest.mark.l04
@pytest.mark.unit
class TestCacheMetrics:
    """Tests for cache hit/miss metrics."""

    def test_record_cache_hit_increments_counter(self):
        """Test that record_cache_hit increments cache hits counter."""
        manager = MetricsManager()

        initial = CACHE_HITS_TOTAL._value.get()
        manager.record_cache_hit()
        after = CACHE_HITS_TOTAL._value.get()

        assert after == initial + 1

    def test_record_cache_miss_increments_counter(self):
        """Test that record_cache_miss increments cache misses counter."""
        manager = MetricsManager()

        initial = CACHE_MISSES_TOTAL._value.get()
        manager.record_cache_miss()
        after = CACHE_MISSES_TOTAL._value.get()

        assert after == initial + 1

    def test_record_inference_with_cached_true_increments_cache_hits(self):
        """Test that cached=True in record_inference increments cache hits."""
        manager = MetricsManager()

        initial = CACHE_HITS_TOTAL._value.get()

        manager.record_inference_request(
            provider="cache_test",
            model="cache_model",
            status="success",
            latency_seconds=0.1,
            input_tokens=10,
            output_tokens=5,
            cached=True
        )

        after = CACHE_HITS_TOTAL._value.get()
        assert after == initial + 1

    def test_record_inference_with_cached_false_increments_cache_misses(self):
        """Test that cached=False in record_inference increments cache misses."""
        manager = MetricsManager()

        initial = CACHE_MISSES_TOTAL._value.get()

        manager.record_inference_request(
            provider="cache_test2",
            model="cache_model2",
            status="success",
            latency_seconds=0.1,
            input_tokens=10,
            output_tokens=5,
            cached=False
        )

        after = CACHE_MISSES_TOTAL._value.get()
        assert after == initial + 1


@pytest.mark.l04
@pytest.mark.unit
class TestRateLimitMetrics:
    """Tests for rate limit metrics."""

    def test_record_rate_limit_rejection_increments_counter(self):
        """Test that record_rate_limit_rejection increments counter."""
        manager = MetricsManager()

        # Sanitized label
        safe_did = "did_key_test_agent"

        initial = RATE_LIMIT_REJECTIONS_TOTAL.labels(
            agent_did=safe_did
        )._value.get()

        manager.record_rate_limit_rejection("did:key:test-agent")

        after = RATE_LIMIT_REJECTIONS_TOTAL.labels(
            agent_did=safe_did
        )._value.get()

        assert after == initial + 1

    def test_record_rate_limit_sanitizes_did(self):
        """Test that agent DID is sanitized for metric labels."""
        manager = MetricsManager()

        # Should not raise with special characters
        manager.record_rate_limit_rejection("did:key:test-agent-with-special:chars")

        # Very long DIDs should be truncated
        long_did = "did:key:" + "a" * 100
        manager.record_rate_limit_rejection(long_did)


@pytest.mark.l04
@pytest.mark.unit
class TestCircuitBreakerMetrics:
    """Tests for circuit breaker state metrics."""

    def test_set_circuit_breaker_state_closed(self):
        """Test setting circuit breaker state to closed."""
        manager = MetricsManager()

        manager.set_circuit_breaker_state("test_provider", "closed")

        value = CIRCUIT_BREAKER_STATE.labels(
            provider="test_provider"
        )._value.get()

        assert value == 0

    def test_set_circuit_breaker_state_half_open(self):
        """Test setting circuit breaker state to half_open."""
        manager = MetricsManager()

        manager.set_circuit_breaker_state("test_provider2", "half_open")

        value = CIRCUIT_BREAKER_STATE.labels(
            provider="test_provider2"
        )._value.get()

        assert value == 1

    def test_set_circuit_breaker_state_open(self):
        """Test setting circuit breaker state to open."""
        manager = MetricsManager()

        manager.set_circuit_breaker_state("test_provider3", "open")

        value = CIRCUIT_BREAKER_STATE.labels(
            provider="test_provider3"
        )._value.get()

        assert value == 2

    def test_set_circuit_breaker_state_case_insensitive(self):
        """Test that state setting is case insensitive."""
        manager = MetricsManager()

        manager.set_circuit_breaker_state("case_test", "OPEN")

        value = CIRCUIT_BREAKER_STATE.labels(
            provider="case_test"
        )._value.get()

        assert value == 2


@pytest.mark.l04
@pytest.mark.unit
class TestActiveRequestMetrics:
    """Tests for active request tracking metrics."""

    def test_start_request_increments_gauge(self):
        """Test that start_request increments the active requests gauge."""
        manager = MetricsManager()

        initial = ACTIVE_REQUESTS.labels(
            provider="active_test"
        )._value.get()

        manager.start_request("active_test")

        after = ACTIVE_REQUESTS.labels(
            provider="active_test"
        )._value.get()

        assert after == initial + 1

    def test_end_request_decrements_gauge(self):
        """Test that end_request decrements the active requests gauge."""
        manager = MetricsManager()

        # First increment
        manager.start_request("active_test2")

        initial = ACTIVE_REQUESTS.labels(
            provider="active_test2"
        )._value.get()

        manager.end_request("active_test2")

        after = ACTIVE_REQUESTS.labels(
            provider="active_test2"
        )._value.get()

        assert after == initial - 1

    def test_request_lifecycle_tracking(self):
        """Test complete request lifecycle tracking."""
        manager = MetricsManager()
        provider = "lifecycle_test"

        initial = ACTIVE_REQUESTS.labels(provider=provider)._value.get()

        # Simulate multiple concurrent requests
        manager.start_request(provider)
        manager.start_request(provider)
        manager.start_request(provider)

        during = ACTIVE_REQUESTS.labels(provider=provider)._value.get()
        assert during == initial + 3

        # Complete requests
        manager.end_request(provider)
        manager.end_request(provider)

        after = ACTIVE_REQUESTS.labels(provider=provider)._value.get()
        assert after == initial + 1

        manager.end_request(provider)
        final = ACTIVE_REQUESTS.labels(provider=provider)._value.get()
        assert final == initial

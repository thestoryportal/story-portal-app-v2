"""
L04 Model Gateway Layer - Prometheus Metrics

Provides observability metrics for monitoring and alerting.
"""

from prometheus_client import Counter, Histogram, Gauge, Info
from typing import Optional
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Counters
# =============================================================================

# Inference request counter
INFERENCE_REQUESTS_TOTAL = Counter(
    "l04_inference_requests_total",
    "Total number of inference requests",
    ["provider", "model", "status"]
)

# Cache counters
CACHE_HITS_TOTAL = Counter(
    "l04_cache_hits_total",
    "Total number of cache hits"
)

CACHE_MISSES_TOTAL = Counter(
    "l04_cache_misses_total",
    "Total number of cache misses"
)

# Rate limit counter
RATE_LIMIT_REJECTIONS_TOTAL = Counter(
    "l04_rate_limit_rejections_total",
    "Total number of rate limit rejections",
    ["agent_did"]
)

# Token usage counters
TOKEN_USAGE_TOTAL = Counter(
    "l04_token_usage_total",
    "Total token usage",
    ["direction", "model"]  # direction: input/output
)


# =============================================================================
# Histograms
# =============================================================================

# Latency histogram with standard buckets
INFERENCE_LATENCY_SECONDS = Histogram(
    "l04_inference_latency_seconds",
    "Inference request latency in seconds",
    ["provider", "model"],
    buckets=[0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, 15.0, 30.0, 60.0]
)


# =============================================================================
# Gauges
# =============================================================================

# Circuit breaker state gauge (0=closed, 1=half_open, 2=open)
CIRCUIT_BREAKER_STATE = Gauge(
    "l04_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=half_open, 2=open)",
    ["provider"]
)

# Active requests gauge
ACTIVE_REQUESTS = Gauge(
    "l04_active_requests",
    "Number of currently active requests",
    ["provider"]
)


# =============================================================================
# Info
# =============================================================================

GATEWAY_INFO = Info(
    "l04_gateway",
    "L04 Model Gateway information"
)


# =============================================================================
# Metrics Manager
# =============================================================================

class MetricsManager:
    """
    Manager for L04 metrics collection and exposure.

    Provides convenience methods for recording metrics throughout
    the inference pipeline.
    """

    def __init__(self):
        self._initialized = False

    def initialize(self, version: str = "1.0.0"):
        """Initialize gateway info metric."""
        if not self._initialized:
            GATEWAY_INFO.info({
                "version": version,
                "layer": "L04",
                "component": "model_gateway"
            })
            self._initialized = True
            logger.info("L04 metrics initialized")

    # =========================================================================
    # Inference Metrics
    # =========================================================================

    def record_inference_request(
        self,
        provider: str,
        model: str,
        status: str,
        latency_seconds: float,
        input_tokens: int,
        output_tokens: int,
        cached: bool = False
    ):
        """
        Record a completed inference request.

        Args:
            provider: Provider name (e.g., "anthropic", "openai")
            model: Model ID
            status: Request status (e.g., "success", "error")
            latency_seconds: Request latency in seconds
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cached: Whether response was from cache
        """
        # Record request count
        INFERENCE_REQUESTS_TOTAL.labels(
            provider=provider,
            model=model,
            status=status
        ).inc()

        # Record latency
        INFERENCE_LATENCY_SECONDS.labels(
            provider=provider,
            model=model
        ).observe(latency_seconds)

        # Record token usage
        TOKEN_USAGE_TOTAL.labels(
            direction="input",
            model=model
        ).inc(input_tokens)

        TOKEN_USAGE_TOTAL.labels(
            direction="output",
            model=model
        ).inc(output_tokens)

        # Record cache hit/miss
        if cached:
            CACHE_HITS_TOTAL.inc()
        else:
            CACHE_MISSES_TOTAL.inc()

    def record_cache_hit(self):
        """Record a cache hit."""
        CACHE_HITS_TOTAL.inc()

    def record_cache_miss(self):
        """Record a cache miss."""
        CACHE_MISSES_TOTAL.inc()

    def record_rate_limit_rejection(self, agent_did: str):
        """
        Record a rate limit rejection.

        Args:
            agent_did: DID of the agent that was rate limited
        """
        # Sanitize agent_did for metric label (remove special chars)
        safe_did = agent_did.replace(":", "_").replace("-", "_")[:64]
        RATE_LIMIT_REJECTIONS_TOTAL.labels(agent_did=safe_did).inc()

    # =========================================================================
    # Circuit Breaker Metrics
    # =========================================================================

    def set_circuit_breaker_state(self, provider: str, state: str):
        """
        Update circuit breaker state gauge.

        Args:
            provider: Provider name
            state: Circuit state ("closed", "half_open", "open")
        """
        state_value = {
            "closed": 0,
            "half_open": 1,
            "open": 2
        }.get(state.lower(), 0)

        CIRCUIT_BREAKER_STATE.labels(provider=provider).set(state_value)

    # =========================================================================
    # Active Request Tracking
    # =========================================================================

    def start_request(self, provider: str):
        """
        Increment active requests counter.

        Args:
            provider: Provider handling the request
        """
        ACTIVE_REQUESTS.labels(provider=provider).inc()

    def end_request(self, provider: str):
        """
        Decrement active requests counter.

        Args:
            provider: Provider that handled the request
        """
        ACTIVE_REQUESTS.labels(provider=provider).dec()


# Global metrics manager instance
metrics = MetricsManager()


def get_metrics_manager() -> MetricsManager:
    """Get the global metrics manager instance."""
    return metrics

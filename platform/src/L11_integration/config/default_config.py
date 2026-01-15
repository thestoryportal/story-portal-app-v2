"""
L11 Integration Layer - Default Configuration.

Configuration for local development environment.
"""

from typing import Dict, Any


DEFAULT_CONFIG: Dict[str, Any] = {
    # Redis connection for event bus
    "redis": {
        "url": "redis://localhost:6379",
        "db": 0,
        "decode_responses": True,
    },

    # Service registry configuration
    "service_registry": {
        "health_check_interval_sec": 30,
        "health_check_timeout_sec": 5,
        "failure_threshold": 3,
        "success_threshold": 1,
    },

    # Circuit breaker configuration
    "circuit_breaker": {
        "failure_threshold": 5,
        "success_threshold": 2,
        "timeout_sec": 60,
        "half_open_requests": 3,
        "error_rate_threshold": 0.5,
        "window_size_sec": 60,
    },

    # Request orchestration configuration
    "request_orchestrator": {
        "default_timeout_sec": 30.0,
        "max_retries": 3,
        "backoff_factor": 2.0,
    },

    # Saga orchestration configuration
    "saga": {
        "default_timeout_sec": 300,
        "auto_compensate": True,
        "max_steps": 50,
    },

    # Observability configuration
    "observability": {
        "output_file": None,  # None = console only, or path to file
        "flush_interval_sec": 60,
        "max_spans_in_memory": 1000,
        "max_metrics_in_memory": 1000,
    },

    # Event bus configuration
    "event_bus": {
        "max_retries": 3,
        "retry_backoff_sec": 1.0,
        "dlq_enabled": True,
    },
}


# Layer service endpoints for local dev
LAYER_ENDPOINTS = {
    "L02_runtime": "http://localhost:8002",
    "L03_tool_execution": "http://localhost:8003",
    "L04_model_gateway": "http://localhost:8004",
    "L05_planning": "http://localhost:8005",
    "L06_evaluation": "http://localhost:8006",
    "L07_learning": "http://localhost:8007",
    "L08_supervision": "http://localhost:8008",
    "L09_api_gateway": "http://localhost:8009",
    "L10_ui": "http://localhost:8010",
}


def get_config() -> Dict[str, Any]:
    """
    Get default configuration.

    Returns:
        Configuration dictionary
    """
    return DEFAULT_CONFIG.copy()


def get_layer_endpoint(layer_name: str) -> str:
    """
    Get endpoint URL for a layer.

    Args:
        layer_name: Layer name (e.g., "L02_runtime")

    Returns:
        Endpoint URL

    Raises:
        ValueError: If layer not found
    """
    if layer_name not in LAYER_ENDPOINTS:
        raise ValueError(f"Unknown layer: {layer_name}")
    return LAYER_ENDPOINTS[layer_name]

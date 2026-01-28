"""
L07 Learning Layer - Observability

Prometheus metrics and monitoring infrastructure.
"""

from .metrics import (
    MetricsManager,
    get_metrics_manager,
    metrics,
    get_metrics,
    get_metrics_content_type,
    record_training_job_context,
    record_extraction_context,
    TRAINING_JOBS_TOTAL,
    EXAMPLES_EXTRACTED_TOTAL,
    VALIDATION_RESULTS_TOTAL,
    TRAINING_DURATION_SECONDS,
    EXTRACTION_LATENCY_SECONDS,
    ACTIVE_TRAINING_JOBS,
    DATASET_SIZE,
    LEARNING_INFO,
)

__all__ = [
    "MetricsManager",
    "get_metrics_manager",
    "metrics",
    "get_metrics",
    "get_metrics_content_type",
    "record_training_job_context",
    "record_extraction_context",
    "TRAINING_JOBS_TOTAL",
    "EXAMPLES_EXTRACTED_TOTAL",
    "VALIDATION_RESULTS_TOTAL",
    "TRAINING_DURATION_SECONDS",
    "EXTRACTION_LATENCY_SECONDS",
    "ACTIVE_TRAINING_JOBS",
    "DATASET_SIZE",
    "LEARNING_INFO",
]

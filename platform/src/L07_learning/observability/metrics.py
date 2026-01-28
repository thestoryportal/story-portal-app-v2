"""
L07 Learning Layer - Prometheus Metrics

Provides observability metrics for monitoring and alerting.
Follows the patterns established in L04 Model Gateway.
"""

import time
import logging
from contextlib import contextmanager
from typing import Optional

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST


logger = logging.getLogger(__name__)


# =============================================================================
# Counters
# =============================================================================

# Training job counter
TRAINING_JOBS_TOTAL = Counter(
    "l07_training_jobs_total",
    "Total number of training jobs",
    ["job_type", "status"]  # job_type: sft, rlhf, distillation, curriculum
)

# Examples extracted counter
EXAMPLES_EXTRACTED_TOTAL = Counter(
    "l07_examples_extracted_total",
    "Total number of training examples extracted",
    ["domain", "source"]  # source: execution_trace, planning_trace, human_annotated
)

# Validation results counter
VALIDATION_RESULTS_TOTAL = Counter(
    "l07_validation_results_total",
    "Total number of model validation results",
    ["result"]  # result: pass, fail
)


# =============================================================================
# Histograms
# =============================================================================

# Training duration histogram
TRAINING_DURATION_SECONDS = Histogram(
    "l07_training_duration_seconds",
    "Training job duration in seconds",
    ["job_type"],
    buckets=[60, 120, 300, 600, 1200, 1800, 3600, 7200, 14400, 28800, 86400]
)

# Extraction latency histogram
EXTRACTION_LATENCY_SECONDS = Histogram(
    "l07_extraction_latency_seconds",
    "Example extraction latency in seconds",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)


# =============================================================================
# Gauges
# =============================================================================

# Active training jobs gauge
ACTIVE_TRAINING_JOBS = Gauge(
    "l07_active_training_jobs",
    "Number of currently active training jobs"
)

# Dataset size gauge
DATASET_SIZE = Gauge(
    "l07_dataset_size",
    "Number of examples in a dataset",
    ["dataset_id", "split"]  # split: train, validation, test
)


# =============================================================================
# Info
# =============================================================================

LEARNING_INFO = Info(
    "l07_learning",
    "L07 Learning Layer information"
)


# =============================================================================
# Metrics Manager
# =============================================================================

class MetricsManager:
    """
    Manager for L07 metrics collection and exposure.

    Provides convenience methods for recording metrics throughout
    the learning pipeline.
    """

    def __init__(self):
        self._initialized = False

    def initialize(self, version: str = "1.0.0"):
        """Initialize learning layer info metric."""
        if not self._initialized:
            LEARNING_INFO.info({
                "version": version,
                "layer": "L07",
                "component": "learning"
            })
            self._initialized = True
            logger.info("L07 metrics initialized")

    # =========================================================================
    # Training Job Metrics
    # =========================================================================

    def record_training_job(
        self,
        job_type: str,
        status: str,
        duration_seconds: float
    ):
        """
        Record a completed training job.

        Args:
            job_type: Type of training job (sft, rlhf, distillation, curriculum)
            status: Job status (completed, failed, cancelled)
            duration_seconds: Job duration in seconds
        """
        # Record job count
        TRAINING_JOBS_TOTAL.labels(
            job_type=job_type,
            status=status
        ).inc()

        # Record duration
        TRAINING_DURATION_SECONDS.labels(
            job_type=job_type
        ).observe(duration_seconds)

    def start_training_job(self):
        """Increment active training jobs counter."""
        ACTIVE_TRAINING_JOBS.inc()

    def end_training_job(self):
        """Decrement active training jobs counter."""
        ACTIVE_TRAINING_JOBS.dec()

    # =========================================================================
    # Example Extraction Metrics
    # =========================================================================

    def record_examples_extracted(
        self,
        domain: str,
        source: str,
        count: int
    ):
        """
        Record extracted training examples.

        Args:
            domain: Domain of the examples (code_generation, planning, etc.)
            source: Source of extraction (execution_trace, planning_trace, etc.)
            count: Number of examples extracted
        """
        EXAMPLES_EXTRACTED_TOTAL.labels(
            domain=domain,
            source=source
        ).inc(count)

    def record_extraction_latency(self, latency_seconds: float):
        """
        Record extraction latency.

        Args:
            latency_seconds: Time taken for extraction in seconds
        """
        EXTRACTION_LATENCY_SECONDS.observe(latency_seconds)

    # =========================================================================
    # Dataset Metrics
    # =========================================================================

    def set_dataset_size(
        self,
        dataset_id: str,
        split: str,
        size: int
    ):
        """
        Set the size of a dataset split.

        Args:
            dataset_id: Dataset identifier
            split: Dataset split (train, validation, test)
            size: Number of examples in the split
        """
        DATASET_SIZE.labels(
            dataset_id=dataset_id,
            split=split
        ).set(size)

    # =========================================================================
    # Validation Metrics
    # =========================================================================

    def record_validation_result(self, passed: bool):
        """
        Record a model validation result.

        Args:
            passed: Whether the validation passed
        """
        result = "pass" if passed else "fail"
        VALIDATION_RESULTS_TOTAL.labels(result=result).inc()


# Global metrics manager instance
metrics = MetricsManager()


def get_metrics_manager() -> MetricsManager:
    """Get the global metrics manager instance."""
    return metrics


# =============================================================================
# Context Managers
# =============================================================================

@contextmanager
def record_training_job_context(job_type: str):
    """
    Context manager to record training job metrics.

    Args:
        job_type: Type of training job

    Usage:
        with record_training_job_context("sft") as record:
            await run_training()
            record.set_status("completed")
    """
    start_time = time.time()
    status = "error"  # Default to error if not set

    class RecordContext:
        def set_status(self, new_status: str):
            nonlocal status
            status = new_status

    record = RecordContext()

    # Track active jobs
    ACTIVE_TRAINING_JOBS.inc()

    try:
        yield record
    finally:
        duration = time.time() - start_time

        # Record metrics
        TRAINING_JOBS_TOTAL.labels(
            job_type=job_type,
            status=status
        ).inc()

        TRAINING_DURATION_SECONDS.labels(job_type=job_type).observe(duration)

        ACTIVE_TRAINING_JOBS.dec()


@contextmanager
def record_extraction_context():
    """
    Context manager to record extraction metrics.

    Usage:
        with record_extraction_context() as record:
            examples = await extract_examples()
            record.set_count(len(examples))
    """
    start_time = time.time()
    count = 0
    domain = "unknown"
    source = "unknown"

    class RecordContext:
        def set_count(self, new_count: int):
            nonlocal count
            count = new_count

        def set_domain(self, new_domain: str):
            nonlocal domain
            domain = new_domain

        def set_source(self, new_source: str):
            nonlocal source
            source = new_source

    record = RecordContext()

    try:
        yield record
    finally:
        duration = time.time() - start_time
        EXTRACTION_LATENCY_SECONDS.observe(duration)

        if count > 0:
            EXAMPLES_EXTRACTED_TOTAL.labels(
                domain=domain,
                source=source
            ).inc(count)


# =============================================================================
# Output Functions
# =============================================================================

def get_metrics() -> bytes:
    """
    Generate Prometheus metrics output.

    Returns:
        Metrics in Prometheus text format
    """
    return generate_latest()


def get_metrics_content_type() -> str:
    """
    Get content type for Prometheus metrics.

    Returns:
        Content type string
    """
    return CONTENT_TYPE_LATEST

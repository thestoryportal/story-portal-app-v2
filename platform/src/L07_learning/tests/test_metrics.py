"""
L07 Learning Layer - Metrics Tests

Tests for Prometheus metrics collection (TDD - tests written first).
"""

import pytest
import time
from unittest.mock import patch, MagicMock

# Note: Tests are written before implementation (TDD)
# Import will work once metrics module is created


@pytest.mark.l07
@pytest.mark.unit
class TestTrainingJobMetrics:
    """Tests for training job metrics."""

    def test_training_job_counter_increments(self):
        """Test that training job counter increments correctly."""
        from L07_learning.observability.metrics import (
            TRAINING_JOBS_TOTAL,
            MetricsManager,
        )

        manager = MetricsManager()

        # Get initial value
        initial = TRAINING_JOBS_TOTAL.labels(
            job_type="sft",
            status="completed"
        )._value.get()

        # Record a training job
        manager.record_training_job(
            job_type="sft",
            status="completed",
            duration_seconds=120.5
        )

        # Verify increment
        after = TRAINING_JOBS_TOTAL.labels(
            job_type="sft",
            status="completed"
        )._value.get()

        assert after == initial + 1

    def test_training_job_failed_status(self):
        """Test that failed training jobs are recorded."""
        from L07_learning.observability.metrics import (
            TRAINING_JOBS_TOTAL,
            MetricsManager,
        )

        manager = MetricsManager()

        initial = TRAINING_JOBS_TOTAL.labels(
            job_type="rlhf",
            status="failed"
        )._value.get()

        manager.record_training_job(
            job_type="rlhf",
            status="failed",
            duration_seconds=30.0
        )

        after = TRAINING_JOBS_TOTAL.labels(
            job_type="rlhf",
            status="failed"
        )._value.get()

        assert after == initial + 1

    def test_training_duration_histogram_records(self):
        """Test that training duration is recorded in histogram."""
        from L07_learning.observability.metrics import (
            TRAINING_DURATION_SECONDS,
            MetricsManager,
        )

        manager = MetricsManager()

        histogram = TRAINING_DURATION_SECONDS.labels(job_type="distillation")
        initial_sum = histogram._sum.get()

        manager.record_training_job(
            job_type="distillation",
            status="completed",
            duration_seconds=300.0
        )

        after_sum = histogram._sum.get()
        assert after_sum >= initial_sum + 300.0


@pytest.mark.l07
@pytest.mark.unit
class TestExampleExtractionMetrics:
    """Tests for example extraction metrics."""

    def test_examples_extracted_counter_increments(self):
        """Test that examples extracted counter increments."""
        from L07_learning.observability.metrics import (
            EXAMPLES_EXTRACTED_TOTAL,
            MetricsManager,
        )

        manager = MetricsManager()

        initial = EXAMPLES_EXTRACTED_TOTAL.labels(
            domain="code_generation",
            source="execution_trace"
        )._value.get()

        manager.record_examples_extracted(
            domain="code_generation",
            source="execution_trace",
            count=10
        )

        after = EXAMPLES_EXTRACTED_TOTAL.labels(
            domain="code_generation",
            source="execution_trace"
        )._value.get()

        assert after == initial + 10

    def test_extraction_latency_histogram_records(self):
        """Test that extraction latency is recorded."""
        from L07_learning.observability.metrics import (
            EXTRACTION_LATENCY_SECONDS,
            MetricsManager,
        )

        manager = MetricsManager()

        initial_sum = EXTRACTION_LATENCY_SECONDS._sum.get()

        manager.record_extraction_latency(latency_seconds=0.5)

        after_sum = EXTRACTION_LATENCY_SECONDS._sum.get()
        assert after_sum >= initial_sum + 0.5


@pytest.mark.l07
@pytest.mark.unit
class TestActiveJobsMetrics:
    """Tests for active training jobs gauge."""

    def test_active_jobs_gauge_increments(self):
        """Test that active jobs gauge increments when job starts."""
        from L07_learning.observability.metrics import (
            ACTIVE_TRAINING_JOBS,
            MetricsManager,
        )

        manager = MetricsManager()

        initial = ACTIVE_TRAINING_JOBS._value.get()

        manager.start_training_job()

        after = ACTIVE_TRAINING_JOBS._value.get()
        assert after == initial + 1

    def test_active_jobs_gauge_decrements(self):
        """Test that active jobs gauge decrements when job ends."""
        from L07_learning.observability.metrics import (
            ACTIVE_TRAINING_JOBS,
            MetricsManager,
        )

        manager = MetricsManager()

        # First increment
        manager.start_training_job()
        initial = ACTIVE_TRAINING_JOBS._value.get()

        manager.end_training_job()

        after = ACTIVE_TRAINING_JOBS._value.get()
        assert after == initial - 1

    def test_active_jobs_lifecycle(self):
        """Test complete active jobs lifecycle tracking."""
        from L07_learning.observability.metrics import (
            ACTIVE_TRAINING_JOBS,
            MetricsManager,
        )

        manager = MetricsManager()
        initial = ACTIVE_TRAINING_JOBS._value.get()

        # Simulate multiple concurrent jobs
        manager.start_training_job()
        manager.start_training_job()
        manager.start_training_job()

        during = ACTIVE_TRAINING_JOBS._value.get()
        assert during == initial + 3

        # Complete jobs
        manager.end_training_job()
        manager.end_training_job()

        after = ACTIVE_TRAINING_JOBS._value.get()
        assert after == initial + 1

        manager.end_training_job()
        final = ACTIVE_TRAINING_JOBS._value.get()
        assert final == initial


@pytest.mark.l07
@pytest.mark.unit
class TestDatasetMetrics:
    """Tests for dataset size gauge."""

    def test_dataset_size_gauge_set(self):
        """Test that dataset size gauge is set correctly."""
        from L07_learning.observability.metrics import (
            DATASET_SIZE,
            MetricsManager,
        )

        manager = MetricsManager()

        manager.set_dataset_size(
            dataset_id="ds-001",
            split="train",
            size=1000
        )

        value = DATASET_SIZE.labels(
            dataset_id="ds-001",
            split="train"
        )._value.get()

        assert value == 1000

    def test_dataset_size_updates(self):
        """Test that dataset size gauge can be updated."""
        from L07_learning.observability.metrics import (
            DATASET_SIZE,
            MetricsManager,
        )

        manager = MetricsManager()

        manager.set_dataset_size(
            dataset_id="ds-002",
            split="validation",
            size=100
        )

        # Update size
        manager.set_dataset_size(
            dataset_id="ds-002",
            split="validation",
            size=150
        )

        value = DATASET_SIZE.labels(
            dataset_id="ds-002",
            split="validation"
        )._value.get()

        assert value == 150


@pytest.mark.l07
@pytest.mark.unit
class TestValidationMetrics:
    """Tests for validation result metrics."""

    def test_validation_pass_counter(self):
        """Test that validation pass counter increments."""
        from L07_learning.observability.metrics import (
            VALIDATION_RESULTS_TOTAL,
            MetricsManager,
        )

        manager = MetricsManager()

        initial = VALIDATION_RESULTS_TOTAL.labels(result="pass")._value.get()

        manager.record_validation_result(passed=True)

        after = VALIDATION_RESULTS_TOTAL.labels(result="pass")._value.get()
        assert after == initial + 1

    def test_validation_fail_counter(self):
        """Test that validation fail counter increments."""
        from L07_learning.observability.metrics import (
            VALIDATION_RESULTS_TOTAL,
            MetricsManager,
        )

        manager = MetricsManager()

        initial = VALIDATION_RESULTS_TOTAL.labels(result="fail")._value.get()

        manager.record_validation_result(passed=False)

        after = VALIDATION_RESULTS_TOTAL.labels(result="fail")._value.get()
        assert after == initial + 1


@pytest.mark.l07
@pytest.mark.unit
class TestMetricsManager:
    """Tests for MetricsManager class."""

    def test_initialize_sets_learning_info(self):
        """Test that initialize sets learning layer info metric."""
        from L07_learning.observability.metrics import (
            MetricsManager,
        )

        manager = MetricsManager()
        manager.initialize(version="1.2.3")

        # Verify initialization flag
        assert manager._initialized is True

        # Second call should be no-op
        manager.initialize(version="different")
        # Should still be initialized from first call

    def test_get_metrics_manager_returns_singleton(self):
        """Test that get_metrics_manager returns the global instance."""
        from L07_learning.observability.metrics import (
            get_metrics_manager,
            metrics,
        )

        manager1 = get_metrics_manager()
        manager2 = get_metrics_manager()

        assert manager1 is manager2
        assert manager1 is metrics


@pytest.mark.l07
@pytest.mark.unit
class TestContextManagers:
    """Tests for context manager helpers."""

    def test_record_training_job_context(self):
        """Test training job context manager records metrics."""
        from L07_learning.observability.metrics import (
            record_training_job_context,
            TRAINING_JOBS_TOTAL,
            TRAINING_DURATION_SECONDS,
        )

        initial_count = TRAINING_JOBS_TOTAL.labels(
            job_type="sft",
            status="completed"
        )._value.get()

        with record_training_job_context("sft") as record:
            time.sleep(0.01)  # Small delay to ensure duration > 0
            record.set_status("completed")

        after_count = TRAINING_JOBS_TOTAL.labels(
            job_type="sft",
            status="completed"
        )._value.get()

        assert after_count == initial_count + 1

    def test_record_training_job_context_defaults_to_error(self):
        """Test that context manager defaults to error status on exception."""
        from L07_learning.observability.metrics import (
            record_training_job_context,
            TRAINING_JOBS_TOTAL,
        )

        initial_count = TRAINING_JOBS_TOTAL.labels(
            job_type="rlhf",
            status="error"
        )._value.get()

        try:
            with record_training_job_context("rlhf") as record:
                raise ValueError("Simulated error")
        except ValueError:
            pass

        after_count = TRAINING_JOBS_TOTAL.labels(
            job_type="rlhf",
            status="error"
        )._value.get()

        assert after_count == initial_count + 1

    def test_record_extraction_context(self):
        """Test extraction context manager records metrics."""
        from L07_learning.observability.metrics import (
            record_extraction_context,
            EXTRACTION_LATENCY_SECONDS,
        )

        initial_sum = EXTRACTION_LATENCY_SECONDS._sum.get()

        with record_extraction_context() as record:
            time.sleep(0.01)
            record.set_count(5)

        after_sum = EXTRACTION_LATENCY_SECONDS._sum.get()
        assert after_sum > initial_sum


@pytest.mark.l07
@pytest.mark.unit
class TestMetricsOutput:
    """Tests for metrics output generation."""

    def test_get_metrics_returns_bytes(self):
        """Test that get_metrics returns bytes."""
        from L07_learning.observability.metrics import get_metrics

        result = get_metrics()
        assert isinstance(result, bytes)

    def test_get_metrics_content_type(self):
        """Test that get_metrics_content_type returns correct type."""
        from L07_learning.observability.metrics import get_metrics_content_type

        content_type = get_metrics_content_type()
        assert "text/plain" in content_type or "text/openmetrics-text" in content_type

    def test_get_metrics_contains_l07_metrics(self):
        """Test that metrics output contains L07 metrics."""
        from L07_learning.observability.metrics import (
            get_metrics,
            MetricsManager,
        )

        # Record some metrics first
        manager = MetricsManager()
        manager.record_training_job(
            job_type="test_metrics_output",
            status="completed",
            duration_seconds=1.0
        )

        result = get_metrics().decode("utf-8")

        # Check for L07-specific metrics
        assert "l07_training_jobs_total" in result
        assert "l07_training_duration_seconds" in result

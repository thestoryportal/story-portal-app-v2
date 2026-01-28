"""
Observability Tests

Tests for Prometheus metrics and recording functions.
"""

import pytest
from unittest.mock import MagicMock, patch
import time

from ..observability.metrics import (
    TOOL_INVOCATIONS_TOTAL,
    TOOL_EXECUTION_DURATION,
    ACTIVE_EXECUTIONS,
    CACHE_HITS_TOTAL,
    CACHE_MISSES_TOTAL,
    SEMANTIC_SEARCH_DURATION,
    ASYNC_TASKS_TOTAL,
    ASYNC_TASKS_IN_PROGRESS,
    L02_REQUESTS_TOTAL,
    L02_REQUEST_DURATION,
    record_tool_invocation,
    record_cache_access,
    record_semantic_search,
    record_async_task,
    record_l02_request,
    record_error,
    get_metrics,
    get_metrics_content_type,
)


class TestMetricsRecording:
    """Tests for metrics recording functions."""

    def test_record_tool_invocation_success(self):
        """Test recording a successful tool invocation."""
        with record_tool_invocation("test-tool", "sync", "did:agent:test") as record:
            record.set_status("success")

        # Metric should have been recorded (we can't easily check the value
        # without resetting, but we can verify no exceptions)

    def test_record_tool_invocation_error(self):
        """Test recording a failed tool invocation."""
        with record_tool_invocation("test-tool", "async") as record:
            # Don't set status, defaults to error
            pass

    def test_record_tool_invocation_with_exception(self):
        """Test that metrics are still recorded when exception occurs."""
        try:
            with record_tool_invocation("test-tool", "sync", "did:agent:test"):
                raise ValueError("Test error")
        except ValueError:
            pass  # Expected

    def test_record_cache_hit(self):
        """Test recording a cache hit."""
        record_cache_access("test-tool", hit=True, cache_type="result")
        # No assertion needed - verifies no exception

    def test_record_cache_miss(self):
        """Test recording a cache miss."""
        record_cache_access("test-tool", hit=False, cache_type="idempotency")
        # No assertion needed - verifies no exception

    def test_record_semantic_search(self):
        """Test recording semantic search metrics."""
        with record_semantic_search() as record:
            record.set_results_count(5)

    def test_record_semantic_search_no_results(self):
        """Test recording semantic search with no results."""
        with record_semantic_search() as record:
            record.set_results_count(0)

    def test_record_async_task_created(self):
        """Test recording async task creation."""
        record_async_task("test-tool", "created")

    def test_record_async_task_completed_success(self):
        """Test recording async task completion with success."""
        record_async_task("test-tool", "completed", "success")

    def test_record_async_task_completed_error(self):
        """Test recording async task completion with error."""
        record_async_task("test-tool", "completed", "error")

    def test_record_async_task_completed_cancelled(self):
        """Test recording async task cancellation."""
        record_async_task("test-tool", "completed", "cancelled")

    def test_record_l02_request_success(self):
        """Test recording a successful L02 request."""
        with record_l02_request("get_document") as record:
            record.set_status("success")

    def test_record_l02_request_not_found(self):
        """Test recording an L02 request with not found."""
        with record_l02_request("get_document") as record:
            record.set_status("not_found")

    def test_record_l02_request_error(self):
        """Test recording an L02 request error (default)."""
        with record_l02_request("search_documents"):
            pass  # Status defaults to error

    def test_record_error(self):
        """Test recording an error."""
        record_error("E3001", "test-tool")


class TestMetricsOutput:
    """Tests for metrics output functions."""

    def test_get_metrics_returns_bytes(self):
        """Test that get_metrics returns bytes."""
        result = get_metrics()
        assert isinstance(result, bytes)

    def test_get_metrics_contains_metric_names(self):
        """Test that metrics output contains expected metric names."""
        result = get_metrics().decode("utf-8")

        # Check for some expected metric names
        assert "l03_tool_invocations_total" in result
        assert "l03_tool_execution_duration" in result
        assert "l03_cache_hits_total" in result
        assert "l03_semantic_search_duration" in result

    def test_get_metrics_content_type(self):
        """Test that content type is correct."""
        content_type = get_metrics_content_type()
        assert "text/plain" in content_type or "text/openmetrics" in content_type


class TestMetricsIntegration:
    """Integration tests for metrics with actual recording."""

    def test_full_tool_invocation_flow(self):
        """Test a complete tool invocation metrics flow."""
        # Record a tool invocation
        with record_tool_invocation("integration-tool", "sync", "did:agent:integration") as record:
            # Simulate some work
            time.sleep(0.01)
            record.set_status("success")

        # Record cache access
        record_cache_access("integration-tool", hit=True)

        # Get metrics and verify they're recorded
        metrics = get_metrics().decode("utf-8")
        assert "l03_tool_invocations_total" in metrics

    def test_async_task_lifecycle(self):
        """Test async task metrics through lifecycle."""
        # Create task
        record_async_task("lifecycle-tool", "created")

        # Complete task
        record_async_task("lifecycle-tool", "completed", "success")

        # Verify metrics
        metrics = get_metrics().decode("utf-8")
        assert "l03_async_tasks" in metrics

    def test_l02_request_with_timing(self):
        """Test L02 request metrics with timing."""
        with record_l02_request("test_operation") as record:
            time.sleep(0.01)  # Simulate network latency
            record.set_status("success")

        metrics = get_metrics().decode("utf-8")
        assert "l03_l02_request" in metrics

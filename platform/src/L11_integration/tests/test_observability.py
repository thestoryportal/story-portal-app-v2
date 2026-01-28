"""
L11 Integration Layer - Observability Collector Tests.

Tests for the ObservabilityCollector service.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone

from L11_integration.services import ObservabilityCollector, Counter, Gauge, Histogram
from L11_integration.models import TraceSpan, Metric, SpanKind, SpanStatus


@pytest.mark.l11
@pytest.mark.unit
class TestObservabilityCollectorUnit:
    """Unit tests for ObservabilityCollector."""

    @pytest_asyncio.fixture
    async def collector(self):
        """Create collector for testing."""
        c = ObservabilityCollector(output_file=None)
        await c.start()
        yield c
        await c.stop()

    @pytest.mark.asyncio
    async def test_record_span(self, collector):
        """Test recording a trace span."""
        span = TraceSpan(
            trace_id="trace-001",
            span_id="span-001",
            span_name="test_operation",
            span_kind=SpanKind.INTERNAL,
            service_name="L11_integration",
        )
        span.end(SpanStatus.OK)

        await collector.record_span(span)

        spans = await collector.get_spans()
        assert len(spans) == 1
        assert spans[0].span_name == "test_operation"

    @pytest.mark.asyncio
    async def test_record_metric(self, collector):
        """Test recording a metric."""
        metric = Metric(
            metric_name="test_counter",
            metric_type="counter",
            value=42.0,
            labels={"service": "test"},
        )

        await collector.record_metric(metric)

        metrics = await collector.get_metrics()
        assert len(metrics) == 1
        assert metrics[0].metric_name == "test_counter"
        assert metrics[0].value == 42.0

    @pytest.mark.asyncio
    async def test_get_spans_by_trace_id(self, collector):
        """Test filtering spans by trace ID."""
        span1 = TraceSpan(
            trace_id="trace-001",
            span_id="span-001",
            span_name="operation_1",
            span_kind=SpanKind.CLIENT,
            service_name="L11",
        )
        span2 = TraceSpan(
            trace_id="trace-002",
            span_id="span-002",
            span_name="operation_2",
            span_kind=SpanKind.SERVER,
            service_name="L11",
        )

        await collector.record_span(span1)
        await collector.record_span(span2)

        spans = await collector.get_spans(trace_id="trace-001")
        assert len(spans) == 1
        assert spans[0].trace_id == "trace-001"

    @pytest.mark.asyncio
    async def test_get_trace(self, collector):
        """Test getting all spans for a trace."""
        for i in range(3):
            span = TraceSpan(
                trace_id="trace-abc",
                span_id=f"span-{i}",
                span_name=f"operation_{i}",
                span_kind=SpanKind.INTERNAL,
                service_name="L11",
            )
            await collector.record_span(span)

        # Add span with different trace
        other_span = TraceSpan(
            trace_id="trace-other",
            span_id="span-other",
            span_name="other",
            span_kind=SpanKind.INTERNAL,
            service_name="L11",
        )
        await collector.record_span(other_span)

        trace = await collector.get_trace("trace-abc")
        assert len(trace) == 3
        assert all(s.trace_id == "trace-abc" for s in trace)

    @pytest.mark.asyncio
    async def test_get_metric_summary(self, collector):
        """Test getting metric summary statistics."""
        for i in range(5):
            metric = Metric(
                metric_name="latency",
                metric_type="histogram",
                value=float(i * 10),  # 0, 10, 20, 30, 40
                labels={"service": "test"},
            )
            await collector.record_metric(metric)

        summary = await collector.get_metric_summary("latency")
        assert summary["count"] == 5
        assert summary["min"] == 0.0
        assert summary["max"] == 40.0
        assert summary["avg"] == 20.0
        assert summary["sum"] == 100.0

    @pytest.mark.asyncio
    async def test_get_metric_summary_with_labels(self, collector):
        """Test filtering metric summary by labels."""
        # Add metrics with different labels
        await collector.record_metric(Metric(
            metric_name="requests",
            metric_type="counter",
            value=10.0,
            labels={"status": "200"},
        ))
        await collector.record_metric(Metric(
            metric_name="requests",
            metric_type="counter",
            value=5.0,
            labels={"status": "500"},
        ))

        summary = await collector.get_metric_summary("requests", labels={"status": "200"})
        assert summary["count"] == 1
        assert summary["sum"] == 10.0

    @pytest.mark.asyncio
    async def test_get_metric_summary_empty(self, collector):
        """Test metric summary for non-existent metric."""
        summary = await collector.get_metric_summary("nonexistent")
        assert summary["count"] == 0
        assert summary["avg"] == 0.0


@pytest.mark.l11
@pytest.mark.unit
class TestMetricHelpers:
    """Tests for Counter, Gauge, and Histogram helpers."""

    @pytest_asyncio.fixture
    async def collector(self):
        """Create collector for testing."""
        c = ObservabilityCollector(output_file=None)
        await c.start()
        yield c
        await c.stop()

    @pytest.mark.asyncio
    async def test_counter_increment(self, collector):
        """Test Counter increment."""
        counter = collector.create_counter("test_counter", {"env": "test"})

        await counter.inc()
        await counter.inc(5.0)

        metrics = await collector.get_metrics(metric_name="test_counter")
        assert len(metrics) == 2
        # Counter value should be cumulative in the Counter object
        assert counter._value == 6.0

    @pytest.mark.asyncio
    async def test_gauge_set(self, collector):
        """Test Gauge set."""
        gauge = collector.create_gauge("memory_usage", {"host": "local"})

        await gauge.set(1024.0)
        await gauge.set(2048.0)

        metrics = await collector.get_metrics(metric_name="memory_usage")
        assert len(metrics) == 2
        assert metrics[-1].value == 2048.0

    @pytest.mark.asyncio
    async def test_histogram_observe(self, collector):
        """Test Histogram observe."""
        histogram = collector.create_histogram("request_latency", {"endpoint": "/api"})

        await histogram.observe(0.1)
        await histogram.observe(0.5)
        await histogram.observe(1.2)

        metrics = await collector.get_metrics(metric_name="request_latency")
        assert len(metrics) == 3

        summary = await collector.get_metric_summary("request_latency")
        assert summary["count"] == 3
        assert summary["min"] == pytest.approx(0.1)
        assert summary["max"] == pytest.approx(1.2)


@pytest.mark.l11
@pytest.mark.unit
class TestObservabilityLifecycle:
    """Tests for ObservabilityCollector lifecycle."""

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test collector start and stop."""
        collector = ObservabilityCollector(output_file=None)
        assert collector._running is False

        await collector.start()
        assert collector._running is True
        assert collector._flush_task is not None

        await collector.stop()
        assert collector._running is False

    @pytest.mark.asyncio
    async def test_spans_limit(self):
        """Test that spans are limited to prevent memory issues."""
        collector = ObservabilityCollector(output_file=None)
        await collector.start()

        # Add more than 1000 spans (the internal limit)
        for i in range(1100):
            span = TraceSpan(
                trace_id=f"trace-{i}",
                span_id=f"span-{i}",
                span_name="test",
                span_kind=SpanKind.INTERNAL,
                service_name="test",
            )
            await collector.record_span(span)

        # Force flush
        await collector._flush_data()

        # Should be trimmed to last 1000
        spans = await collector.get_spans(limit=2000)
        assert len(spans) == 1000

        await collector.stop()

"""
L11 Integration Layer - Observability Collector.

Trace and metric aggregation for system-wide observability.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import json

from ..models import (
    TraceSpan,
    Metric,
    IntegrationError,
    ErrorCode,
)


logger = logging.getLogger(__name__)


class ObservabilityCollector:
    """
    Observability collector for traces and metrics.

    Collects and aggregates observability data for local dev environment.
    In production, this would export to Jaeger/Tempo and Prometheus.
    """

    def __init__(self, output_file: Optional[str] = None):
        """
        Initialize observability collector.

        Args:
            output_file: Optional file path to write observability data
        """
        self._spans: List[TraceSpan] = []
        self._metrics: List[Metric] = []
        self._output_file = output_file
        self._running = False
        self._flush_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the observability collector."""
        self._running = True

        # Start periodic flush task
        self._flush_task = asyncio.create_task(self._flush_loop())

        logger.info(
            f"Observability collector started "
            f"(output_file={self._output_file or 'console'})"
        )

    async def stop(self) -> None:
        """Stop the observability collector."""
        self._running = False
        logger.info("Stopping observability collector...")

        # Cancel flush task
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # Final flush
        await self._flush_data()

        logger.info("Observability collector stopped")

    async def record_span(self, span: TraceSpan) -> None:
        """
        Record a trace span.

        Args:
            span: TraceSpan to record
        """
        async with self._lock:
            self._spans.append(span)

        logger.debug(
            f"Recorded span: {span.span_name} "
            f"(trace_id={span.trace_id}, duration={span.duration_ms}ms)"
        )

    async def record_metric(self, metric: Metric) -> None:
        """
        Record a metric.

        Args:
            metric: Metric to record
        """
        async with self._lock:
            self._metrics.append(metric)

        logger.debug(
            f"Recorded metric: {metric.metric_name}={metric.value} "
            f"{metric.unit or ''}"
        )

    async def get_spans(
        self,
        trace_id: Optional[str] = None,
        service_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[TraceSpan]:
        """
        Get recorded spans with optional filtering.

        Args:
            trace_id: Filter by trace ID
            service_name: Filter by service name
            limit: Maximum number of spans to return

        Returns:
            List of TraceSpan
        """
        async with self._lock:
            filtered_spans = self._spans

            if trace_id:
                filtered_spans = [s for s in filtered_spans if s.trace_id == trace_id]

            if service_name:
                filtered_spans = [s for s in filtered_spans if s.service_name == service_name]

            return filtered_spans[-limit:]

    async def get_trace(self, trace_id: str) -> List[TraceSpan]:
        """
        Get all spans for a trace.

        Args:
            trace_id: Trace ID

        Returns:
            List of TraceSpan ordered by start time
        """
        async with self._lock:
            trace_spans = [s for s in self._spans if s.trace_id == trace_id]
            return sorted(trace_spans, key=lambda s: s.start_time)

    async def get_metrics(
        self,
        metric_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[Metric]:
        """
        Get recorded metrics with optional filtering.

        Args:
            metric_name: Filter by metric name
            limit: Maximum number of metrics to return

        Returns:
            List of Metric
        """
        async with self._lock:
            filtered_metrics = self._metrics

            if metric_name:
                filtered_metrics = [m for m in filtered_metrics if m.metric_name == metric_name]

            return filtered_metrics[-limit:]

    async def get_metric_summary(
        self,
        metric_name: str,
        labels: Optional[Dict[str, str]] = None,
    ) -> Dict[str, float]:
        """
        Get summary statistics for a metric.

        Args:
            metric_name: Metric name
            labels: Optional label filters

        Returns:
            Dictionary with min, max, avg, count
        """
        async with self._lock:
            # Filter metrics
            filtered = [m for m in self._metrics if m.metric_name == metric_name]

            if labels:
                filtered = [
                    m for m in filtered
                    if all(m.labels.get(k) == v for k, v in labels.items())
                ]

            if not filtered:
                return {
                    "min": 0.0,
                    "max": 0.0,
                    "avg": 0.0,
                    "count": 0,
                    "sum": 0.0,
                }

            values = [m.value for m in filtered]
            return {
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "count": len(values),
                "sum": sum(values),
            }

    async def _flush_loop(self) -> None:
        """Periodic flush loop."""
        while self._running:
            try:
                await asyncio.sleep(60)  # Flush every minute
                await self._flush_data()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in flush loop: {e}")

    async def _flush_data(self) -> None:
        """Flush observability data to output."""
        async with self._lock:
            if not self._spans and not self._metrics:
                return

            # Prepare data
            data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "spans": [s.to_dict() for s in self._spans],
                "metrics": [m.to_dict() for m in self._metrics],
            }

            # Write to file or log
            if self._output_file:
                try:
                    with open(self._output_file, 'a') as f:
                        f.write(json.dumps(data) + '\n')
                    logger.debug(
                        f"Flushed observability data to {self._output_file}: "
                        f"{len(self._spans)} spans, {len(self._metrics)} metrics"
                    )
                except Exception as e:
                    logger.error(f"Failed to write to {self._output_file}: {e}")
            else:
                # Log to console
                logger.info(
                    f"Observability data: "
                    f"{len(self._spans)} spans, {len(self._metrics)} metrics"
                )

            # Clear buffers (keep last 1000 for querying)
            if len(self._spans) > 1000:
                self._spans = self._spans[-1000:]
            if len(self._metrics) > 1000:
                self._metrics = self._metrics[-1000:]

    def create_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> "Counter":
        """
        Create a counter metric.

        Args:
            name: Metric name
            labels: Metric labels

        Returns:
            Counter instance
        """
        return Counter(self, name, labels or {})

    def create_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> "Gauge":
        """
        Create a gauge metric.

        Args:
            name: Metric name
            labels: Metric labels

        Returns:
            Gauge instance
        """
        return Gauge(self, name, labels or {})

    def create_histogram(self, name: str, labels: Optional[Dict[str, str]] = None) -> "Histogram":
        """
        Create a histogram metric.

        Args:
            name: Metric name
            labels: Metric labels

        Returns:
            Histogram instance
        """
        return Histogram(self, name, labels or {})


class Counter:
    """Counter metric."""

    def __init__(self, collector: ObservabilityCollector, name: str, labels: Dict[str, str]):
        self.collector = collector
        self.name = name
        self.labels = labels
        self._value = 0.0

    async def inc(self, value: float = 1.0) -> None:
        """Increment counter."""
        self._value += value
        metric = Metric(
            metric_name=self.name,
            metric_type="counter",
            value=self._value,
            labels=self.labels,
        )
        await self.collector.record_metric(metric)


class Gauge:
    """Gauge metric."""

    def __init__(self, collector: ObservabilityCollector, name: str, labels: Dict[str, str]):
        self.collector = collector
        self.name = name
        self.labels = labels

    async def set(self, value: float) -> None:
        """Set gauge value."""
        metric = Metric(
            metric_name=self.name,
            metric_type="gauge",
            value=value,
            labels=self.labels,
        )
        await self.collector.record_metric(metric)


class Histogram:
    """Histogram metric."""

    def __init__(self, collector: ObservabilityCollector, name: str, labels: Dict[str, str]):
        self.collector = collector
        self.name = name
        self.labels = labels

    async def observe(self, value: float) -> None:
        """Observe a value."""
        metric = Metric(
            metric_name=self.name,
            metric_type="histogram",
            value=value,
            labels=self.labels,
        )
        await self.collector.record_metric(metric)

"""Metrics aggregation engine for time-series data"""

import asyncio
import logging
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional
from collections import defaultdict
import statistics

from ..models.metric import MetricPoint, MetricType, MetricAggregation
from ..models.cloud_event import CloudEvent
from ..models.error_codes import ErrorCode

try:
    from .storage_manager import StorageManager
except ImportError:
    StorageManager = None

from .cache_manager import CacheManager

logger = logging.getLogger(__name__)


class StubStorageManager:
    """Stub storage manager for when actual storage is not available."""

    async def write_metric(self, metric: MetricPoint):
        """Stub method - does nothing."""
        pass

    async def query_metrics(self, *args, **kwargs):
        """Stub method - returns empty list."""
        return []

    async def cleanup(self):
        """Stub method - does nothing."""
        pass


class MetricsEngine:
    """
    Aggregates metrics into time windows and computes statistics.

    Per spec Section 3.2 (Component Responsibilities #3):
    - Aggregate metrics into time windows (60s default)
    - Compute avg, sum, min, max, percentiles (p50, p95, p99)
    - Label-based grouping
    - Cardinality limiting (max 100K series per tenant)
    """

    def __init__(
        self,
        storage_manager: Optional[StorageManager] = None,
        cache_manager: Optional[CacheManager] = None,
        window_seconds: int = 60,
        max_cardinality_per_tenant: int = 100000,
    ):
        """
        Initialize metrics engine.

        Args:
            storage_manager: Storage manager for persistence (optional, created in initialize())
            cache_manager: Cache manager for hot data (optional)
            window_seconds: Aggregation window size (default: 60s)
            max_cardinality_per_tenant: Max unique series per tenant
        """
        self.storage = storage_manager
        self.cache = cache_manager
        self.window_seconds = window_seconds
        self.max_cardinality = max_cardinality_per_tenant
        self._initialized = False

        # In-memory aggregation buffer (for current window)
        self._buffer: Dict[str, List[MetricPoint]] = defaultdict(list)
        self._last_flush = datetime.now(UTC)

        # Cardinality tracking per tenant
        self._cardinality: Dict[str, set] = defaultdict(set)

        # Statistics
        self.metrics_ingested = 0
        self.metrics_dropped_cardinality = 0

    async def initialize(self):
        """Initialize metrics engine and create dependencies if needed."""
        if self._initialized:
            return

        # Create storage manager if not provided
        if self.storage is None:
            if StorageManager is not None:
                self.storage = StorageManager()
                if hasattr(self.storage, 'initialize'):
                    await self.storage.initialize()
            else:
                # Storage module not available, create stub
                logger.warning("StorageManager not available, using stub")
                self.storage = StubStorageManager()

        self._initialized = True
        logger.info("MetricsEngine initialized")

    async def cleanup(self):
        """Cleanup metrics engine resources."""
        # Flush remaining metrics
        await self._flush_buffer()

        # Cleanup storage if we created it
        if self.storage and self._initialized:
            if hasattr(self.storage, 'cleanup'):
                await self.storage.cleanup()

        self._initialized = False
        logger.info("MetricsEngine cleaned up")

    async def ingest(self, metric: MetricPoint) -> bool:
        """
        Ingest a metric point.

        Args:
            metric: MetricPoint to ingest

        Returns:
            True if ingested successfully, False if dropped
        """
        try:
            # Check cardinality limit
            tenant_id = metric.labels.get("tenant_id", "default")
            series_key = metric.series_key()

            if not self._check_cardinality(tenant_id, series_key):
                self.metrics_dropped_cardinality += 1
                logger.warning(
                    f"Metric dropped due to cardinality limit: {tenant_id}/{series_key}"
                )
                return False

            # Add to buffer
            self._buffer[series_key].append(metric)
            self.metrics_ingested += 1

            # Write to storage
            await self.storage.write_metric(metric)

            # Flush if window has elapsed
            await self._check_and_flush()

            return True

        except Exception as e:
            logger.error(f"Metric ingestion failed: {e}")
            return False

    async def ingest_from_event(self, event: CloudEvent) -> List[MetricPoint]:
        """
        Extract and ingest metrics from CloudEvent.

        Args:
            event: CloudEvent containing metric data

        Returns:
            List of ingested MetricPoints
        """
        metrics = []

        try:
            # Extract metrics from event data
            data = event.data

            # Common metrics based on event type
            if event.type == "task.completed":
                # Duration metric
                if "duration_ms" in data:
                    metric = MetricPoint(
                        metric_name="task_duration_seconds",
                        value=data["duration_ms"] / 1000.0,
                        timestamp=event.time,
                        labels={
                            "task_id": event.subject,
                            "agent_id": data.get("agent_id", "unknown"),
                            "tenant_id": data.get("tenant_id", "default"),
                        },
                        metric_type=MetricType.GAUGE,
                    )
                    if await self.ingest(metric):
                        metrics.append(metric)

                # Success/failure counter
                success = data.get("success", True)
                metric = MetricPoint(
                    metric_name="task_completed_total",
                    value=1.0,
                    timestamp=event.time,
                    labels={
                        "agent_id": data.get("agent_id", "unknown"),
                        "tenant_id": data.get("tenant_id", "default"),
                        "status": "success" if success else "failure",
                    },
                    metric_type=MetricType.COUNTER,
                )
                if await self.ingest(metric):
                    metrics.append(metric)

            elif event.type == "model.inference.used":
                # Token usage metric
                if "tokens" in data:
                    metric = MetricPoint(
                        metric_name="model_tokens_used",
                        value=float(data["tokens"]),
                        timestamp=event.time,
                        labels={
                            "model": data.get("model", "unknown"),
                            "agent_id": data.get("agent_id", "unknown"),
                            "tenant_id": data.get("tenant_id", "default"),
                        },
                        metric_type=MetricType.COUNTER,
                    )
                    if await self.ingest(metric):
                        metrics.append(metric)

                # Cost metric
                if "cost" in data:
                    metric = MetricPoint(
                        metric_name="model_cost_dollars",
                        value=float(data["cost"]),
                        timestamp=event.time,
                        labels={
                            "model": data.get("model", "unknown"),
                            "agent_id": data.get("agent_id", "unknown"),
                            "tenant_id": data.get("tenant_id", "default"),
                        },
                        metric_type=MetricType.COUNTER,
                    )
                    if await self.ingest(metric):
                        metrics.append(metric)

            elif event.type == "error.occurred":
                # Error counter
                metric = MetricPoint(
                    metric_name="errors_total",
                    value=1.0,
                    timestamp=event.time,
                    labels={
                        "error_code": data.get("error_code", "unknown"),
                        "agent_id": data.get("agent_id", "unknown"),
                        "tenant_id": data.get("tenant_id", "default"),
                    },
                    metric_type=MetricType.COUNTER,
                )
                if await self.ingest(metric):
                    metrics.append(metric)

        except Exception as e:
            logger.error(f"Metric extraction from event failed: {e}")

        return metrics

    async def query(
        self,
        metric_name: str,
        start: datetime,
        end: datetime,
        labels: Optional[Dict[str, str]] = None,
        aggregation: MetricAggregation = MetricAggregation.AVG,
    ) -> List[MetricPoint]:
        """
        Query metrics with aggregation.

        Args:
            metric_name: Name of metric
            start: Start timestamp
            end: End timestamp
            labels: Label filters (optional)
            aggregation: Aggregation function

        Returns:
            List of aggregated MetricPoints
        """
        try:
            # Check cache first
            if self.cache:
                cache_key = self._get_query_cache_key(metric_name, start, end, labels, aggregation)
                cached = await self.cache.get_query_result(cache_key)
                if cached:
                    logger.debug(f"Query cache hit: {cache_key}")
                    return [MetricPoint.from_dict(m) for m in cached]

            # Read from storage
            raw_metrics = await self.storage.read_metrics(
                metric_name, start, end, labels
            )

            # Aggregate
            aggregated = self._aggregate_metrics(raw_metrics, aggregation)

            # Cache result
            if self.cache:
                await self.cache.set_query_result(
                    cache_key,
                    [m.to_dict() for m in aggregated],
                    ttl=60,
                )

            return aggregated

        except Exception as e:
            logger.error(f"Metric query failed: {e}")
            return []

    def _aggregate_metrics(
        self,
        metrics: List[MetricPoint],
        aggregation: MetricAggregation,
    ) -> List[MetricPoint]:
        """Aggregate metrics using specified function"""
        if not metrics:
            return []

        # Group by time window
        windowed = defaultdict(list)
        for metric in metrics:
            window_start = self._get_window_start(metric.timestamp)
            windowed[window_start].append(metric)

        # Aggregate each window
        aggregated = []
        for window_start, window_metrics in windowed.items():
            values = [m.value for m in window_metrics]

            if aggregation == MetricAggregation.AVG:
                agg_value = statistics.mean(values)
            elif aggregation == MetricAggregation.SUM:
                agg_value = sum(values)
            elif aggregation == MetricAggregation.MIN:
                agg_value = min(values)
            elif aggregation == MetricAggregation.MAX:
                agg_value = max(values)
            elif aggregation == MetricAggregation.STDDEV:
                agg_value = statistics.stdev(values) if len(values) > 1 else 0.0
            elif aggregation == MetricAggregation.P50:
                agg_value = statistics.median(values)
            elif aggregation == MetricAggregation.P95:
                agg_value = self._percentile(values, 0.95)
            elif aggregation == MetricAggregation.P99:
                agg_value = self._percentile(values, 0.99)
            elif aggregation == MetricAggregation.COUNT:
                agg_value = float(len(values))
            else:
                agg_value = statistics.mean(values)

            # Use first metric as template
            template = window_metrics[0]
            aggregated.append(
                MetricPoint(
                    metric_name=template.metric_name,
                    value=agg_value,
                    timestamp=window_start,
                    labels=template.labels,
                    metric_type=template.metric_type,
                )
            )

        return aggregated

    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile of values"""
        if not values:
            return 0.0

        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile)
        index = min(index, len(sorted_values) - 1)
        return sorted_values[index]

    def _get_window_start(self, timestamp: datetime) -> datetime:
        """Get start of time window for timestamp"""
        epoch = timestamp.timestamp()
        window_epoch = (epoch // self.window_seconds) * self.window_seconds
        return datetime.fromtimestamp(window_epoch)

    def _check_cardinality(self, tenant_id: str, series_key: str) -> bool:
        """Check if adding series would exceed cardinality limit"""
        tenant_series = self._cardinality[tenant_id]

        # If already tracking, it's OK
        if series_key in tenant_series:
            return True

        # Check if we can add a new series
        if len(tenant_series) >= self.max_cardinality:
            return False

        # Add to tracking
        tenant_series.add(series_key)
        return True

    async def _check_and_flush(self):
        """Check if window elapsed and flush buffer"""
        now = datetime.now(UTC)
        elapsed = (now - self._last_flush).total_seconds()

        if elapsed >= self.window_seconds:
            await self._flush_buffer()
            self._last_flush = now

    async def _flush_buffer(self):
        """Flush aggregation buffer to storage"""
        if not self._buffer:
            return

        logger.debug(f"Flushing {len(self._buffer)} metric series")

        # Clear buffer (already written to storage in ingest())
        self._buffer.clear()

    def _get_query_cache_key(
        self,
        metric_name: str,
        start: datetime,
        end: datetime,
        labels: Optional[Dict[str, str]],
        aggregation: MetricAggregation,
    ) -> str:
        """Generate cache key for query"""
        import hashlib
        import json

        query_data = {
            "metric": metric_name,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "labels": labels or {},
            "aggregation": aggregation.value,
        }
        query_str = json.dumps(query_data, sort_keys=True)
        query_hash = hashlib.md5(query_str.encode()).hexdigest()
        return query_hash

    def get_statistics(self) -> dict:
        """Get metrics engine statistics"""
        return {
            "metrics_ingested": self.metrics_ingested,
            "metrics_dropped_cardinality": self.metrics_dropped_cardinality,
            "buffer_size": len(self._buffer),
            "cardinality_by_tenant": {
                tenant: len(series) for tenant, series in self._cardinality.items()
            },
        }

    def reset_statistics(self):
        """Reset statistics counters"""
        self.metrics_ingested = 0
        self.metrics_dropped_cardinality = 0

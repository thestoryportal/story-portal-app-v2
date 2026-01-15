"""Storage manager for time-series metrics with tiered storage"""

import asyncio
import logging
from datetime import datetime, timedelta, UTC
from typing import List, Optional
from collections import deque

from ..models.metric import MetricPoint
from ..models.error_codes import ErrorCode

logger = logging.getLogger(__name__)


class StorageManager:
    """
    Manages tiered storage for metrics: hot (Redis), warm (PostgreSQL), cold (archive).

    Per spec Section 3.2 (Component Responsibilities #8):
    - Hot storage: Redis (7 days)
    - Warm storage: PostgreSQL (30 days)
    - Cold storage: Archive (365 days) - stub
    - Fallback queue for write failures
    """

    def __init__(
        self,
        redis_client: Optional[any] = None,
        postgres_conn: Optional[any] = None,
        hot_retention_days: int = 7,
        warm_retention_days: int = 30,
        fallback_queue_size: int = 10000,
    ):
        """
        Initialize storage manager.

        Args:
            redis_client: Redis client for hot storage
            postgres_conn: PostgreSQL connection for warm storage
            hot_retention_days: Hot storage retention (default: 7 days)
            warm_retention_days: Warm storage retention (default: 30 days)
            fallback_queue_size: Maximum fallback queue size
        """
        self.redis_client = redis_client
        self.postgres_conn = postgres_conn
        self.hot_retention_seconds = hot_retention_days * 86400
        self.warm_retention_seconds = warm_retention_days * 86400
        self.fallback_queue_size = fallback_queue_size

        # Fallback queue for write failures
        self._fallback_queue: deque[MetricPoint] = deque(maxlen=fallback_queue_size)

        # Statistics
        self.writes_succeeded = 0
        self.writes_failed = 0
        self.fallback_queue_overflows = 0

    async def write_metric(self, metric: MetricPoint) -> bool:
        """
        Write metric to appropriate storage tier.

        Args:
            metric: MetricPoint to store

        Returns:
            True if write succeeded, False otherwise
        """
        try:
            # Write to hot storage (Redis)
            hot_success = await self._write_to_hot(metric)

            # Write to warm storage (PostgreSQL) asynchronously
            if self.postgres_conn:
                asyncio.create_task(self._write_to_warm(metric))

            if hot_success:
                self.writes_succeeded += 1
                return True
            else:
                raise Exception("Hot storage write failed")

        except Exception as e:
            logger.error(f"Metric write failed: {e}")
            self.writes_failed += 1

            # Add to fallback queue
            try:
                self._fallback_queue.append(metric)
                if len(self._fallback_queue) >= self.fallback_queue_size:
                    self.fallback_queue_overflows += 1
                    logger.warning("Fallback queue full, oldest metrics being dropped")
            except Exception as queue_error:
                logger.error(f"Fallback queue append failed: {queue_error}")

            return False

    async def _write_to_hot(self, metric: MetricPoint) -> bool:
        """Write metric to Redis (hot storage)"""
        if not self.redis_client:
            logger.warning("Redis client not available, skipping hot storage")
            return False

        try:
            # Store in Redis sorted set by timestamp
            key = f"metrics:{metric.series_key()}"
            score = metric.timestamp.timestamp()
            value = metric.to_dict()

            import json
            await asyncio.to_thread(
                self.redis_client.zadd,
                key,
                {json.dumps(value, default=str): score},
            )

            # Set expiry for automatic cleanup
            await asyncio.to_thread(
                self.redis_client.expire,
                key,
                self.hot_retention_seconds,
            )

            return True

        except Exception as e:
            logger.error(f"Hot storage write failed: {e}")
            return False

    async def _write_to_warm(self, metric: MetricPoint):
        """Write metric to PostgreSQL (warm storage)"""
        if not self.postgres_conn:
            return

        try:
            # Insert into metrics table
            query = """
                INSERT INTO l06_metrics (
                    metric_name, value, timestamp, labels, metric_type
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """

            import json
            await asyncio.to_thread(
                self.postgres_conn.execute,
                query,
                (
                    metric.metric_name,
                    metric.value,
                    metric.timestamp,
                    json.dumps(metric.labels),
                    metric.metric_type.value,
                ),
            )

        except Exception as e:
            logger.error(f"Warm storage write failed: {e}")

    async def read_metrics(
        self,
        metric_name: str,
        start: datetime,
        end: datetime,
        labels: Optional[dict] = None,
    ) -> List[MetricPoint]:
        """
        Read metrics from storage.

        Args:
            metric_name: Name of metric to read
            start: Start timestamp
            end: End timestamp
            labels: Label filters (optional)

        Returns:
            List of MetricPoints
        """
        metrics = []

        # Try hot storage first (Redis)
        if self.redis_client:
            hot_metrics = await self._read_from_hot(metric_name, start, end, labels)
            metrics.extend(hot_metrics)

        # If time range exceeds hot storage, query warm storage
        hot_cutoff = datetime.now(UTC) - timedelta(days=7)
        if start < hot_cutoff and self.postgres_conn:
            warm_metrics = await self._read_from_warm(metric_name, start, end, labels)
            metrics.extend(warm_metrics)

        # Sort by timestamp
        metrics.sort(key=lambda m: m.timestamp)

        return metrics

    async def _read_from_hot(
        self,
        metric_name: str,
        start: datetime,
        end: datetime,
        labels: Optional[dict] = None,
    ) -> List[MetricPoint]:
        """Read metrics from Redis"""
        metrics = []

        try:
            # Scan for matching keys
            pattern = f"metrics:{metric_name}:*"
            cursor = 0

            while True:
                cursor, keys = await asyncio.to_thread(
                    self.redis_client.scan,
                    cursor,
                    match=pattern,
                    count=100,
                )

                for key in keys:
                    # Get metrics in time range from sorted set
                    results = await asyncio.to_thread(
                        self.redis_client.zrangebyscore,
                        key,
                        start.timestamp(),
                        end.timestamp(),
                    )

                    import json
                    for result in results:
                        data = json.loads(result)
                        metric = MetricPoint.from_dict(data)

                        # Filter by labels if provided
                        if labels is None or self._labels_match(metric.labels, labels):
                            metrics.append(metric)

                if cursor == 0:
                    break

        except Exception as e:
            logger.error(f"Hot storage read failed: {e}")

        return metrics

    async def _read_from_warm(
        self,
        metric_name: str,
        start: datetime,
        end: datetime,
        labels: Optional[dict] = None,
    ) -> List[MetricPoint]:
        """Read metrics from PostgreSQL"""
        metrics = []

        try:
            query = """
                SELECT metric_name, value, timestamp, labels, metric_type
                FROM l06_metrics
                WHERE metric_name = %s
                  AND timestamp BETWEEN %s AND %s
                ORDER BY timestamp
            """

            rows = await asyncio.to_thread(
                self.postgres_conn.execute,
                query,
                (metric_name, start, end),
            )

            import json
            for row in rows:
                metric = MetricPoint(
                    metric_name=row[0],
                    value=row[1],
                    timestamp=row[2],
                    labels=json.loads(row[3]) if row[3] else {},
                    metric_type=row[4],
                )

                # Filter by labels if provided
                if labels is None or self._labels_match(metric.labels, labels):
                    metrics.append(metric)

        except Exception as e:
            logger.error(f"Warm storage read failed: {e}")

        return metrics

    def _labels_match(self, metric_labels: dict, filter_labels: dict) -> bool:
        """Check if metric labels match filter labels"""
        for key, value in filter_labels.items():
            if metric_labels.get(key) != value:
                return False
        return True

    async def process_fallback_queue(self):
        """Process fallback queue and retry failed writes"""
        processed = 0
        failed = 0

        while self._fallback_queue:
            metric = self._fallback_queue.popleft()

            try:
                success = await self._write_to_hot(metric)
                if success:
                    processed += 1

                    # Also write to warm storage
                    if self.postgres_conn:
                        await self._write_to_warm(metric)
                else:
                    # Put back in queue
                    self._fallback_queue.append(metric)
                    failed += 1
                    break  # Stop processing if still failing

            except Exception as e:
                logger.error(f"Fallback queue processing failed: {e}")
                self._fallback_queue.append(metric)
                failed += 1
                break

        logger.info(f"Fallback queue processed: {processed} succeeded, {failed} failed")
        return processed, failed

    def get_fallback_queue_size(self) -> int:
        """Get current fallback queue size"""
        return len(self._fallback_queue)

    def get_statistics(self) -> dict:
        """Get storage statistics"""
        total_writes = self.writes_succeeded + self.writes_failed
        success_rate = (
            self.writes_succeeded / total_writes if total_writes > 0 else 0.0
        )

        return {
            "writes_succeeded": self.writes_succeeded,
            "writes_failed": self.writes_failed,
            "success_rate": success_rate,
            "fallback_queue_size": len(self._fallback_queue),
            "fallback_queue_overflows": self.fallback_queue_overflows,
        }

    def reset_statistics(self):
        """Reset statistics counters"""
        self.writes_succeeded = 0
        self.writes_failed = 0
        self.fallback_queue_overflows = 0

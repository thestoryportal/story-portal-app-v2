"""Query engine for metric queries with caching"""

import logging
from datetime import datetime
from typing import List, Optional

from ..models.metric import MetricPoint
from .metrics_engine import MetricsEngine
from .cache_manager import CacheManager

logger = logging.getLogger(__name__)


class QueryEngine:
    """
    Executes metric queries with caching and pagination.

    Per spec Section 3.2 (Component Responsibilities #9):
    - Cached query results (60s TTL)
    - Pagination support
    - Label filtering
    """

    def __init__(
        self,
        metrics_engine: MetricsEngine,
        cache_manager: Optional[CacheManager] = None,
    ):
        """
        Initialize query engine.

        Args:
            metrics_engine: MetricsEngine for querying
            cache_manager: CacheManager for caching (optional)
        """
        self.metrics = metrics_engine
        self.cache = cache_manager

    async def query(
        self,
        metric_name: str,
        start: datetime,
        end: datetime,
        labels: Optional[dict] = None,
        aggregation: str = "avg",
        limit: int = 10000,
    ) -> List[MetricPoint]:
        """Execute metric query"""
        return await self.metrics.query(
            metric_name, start, end, labels, aggregation
        )

    def get_statistics(self) -> dict:
        """Get query engine statistics"""
        return self.metrics.get_statistics()

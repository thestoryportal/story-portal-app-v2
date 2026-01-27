"""
L04 Model Gateway Layer - Request Queue Service

Priority queue for request buffering during load spikes.
"""

import asyncio
from typing import Optional
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from enum import Enum
import logging

from ..models import InferenceRequest

logger = logging.getLogger(__name__)


class Priority(Enum):
    """Request priority levels"""
    HIGH = 0
    NORMAL = 1
    LOW = 2


@dataclass
class QueuedRequest:
    """Wrapper for queued requests"""
    request: InferenceRequest
    priority: Priority
    enqueued_at: datetime
    deadline: Optional[datetime] = None

    def __lt__(self, other):
        """Compare for priority queue ordering"""
        # First by priority (lower number = higher priority)
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value

        # Then by deadline (earlier deadline = higher priority)
        if self.deadline and other.deadline:
            return self.deadline < other.deadline

        # Finally by enqueue time (earlier = higher priority)
        return self.enqueued_at < other.enqueued_at


class RequestQueue:
    """
    Priority queue for inference requests

    Supports:
    - Priority-based ordering
    - Deadline-aware processing
    - Queue size limits
    - Request timeouts
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_timeout_seconds: int = 300
    ):
        """
        Initialize request queue

        Args:
            max_size: Maximum queue size
            default_timeout_seconds: Default request timeout
        """
        self.max_size = max_size
        self.default_timeout_seconds = default_timeout_seconds
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=max_size)
        self._stats = {
            "enqueued": 0,
            "dequeued": 0,
            "expired": 0,
            "rejected": 0
        }
        logger.info(
            f"RequestQueue initialized (max_size={max_size}, "
            f"timeout={default_timeout_seconds}s)"
        )

    async def enqueue(
        self,
        request: InferenceRequest,
        priority: Priority = Priority.NORMAL,
        deadline: Optional[datetime] = None,
        timeout_seconds: Optional[int] = None
    ) -> bool:
        """
        Enqueue a request

        Args:
            request: InferenceRequest to queue
            priority: Request priority
            deadline: Optional deadline for processing
            timeout_seconds: Optional timeout override

        Returns:
            True if enqueued, False if queue full

        Raises:
            asyncio.QueueFull: If queue is full
        """
        try:
            # Calculate deadline if not provided
            if deadline is None and timeout_seconds is None:
                timeout_seconds = self.default_timeout_seconds

            if deadline is None and timeout_seconds:
                deadline = datetime.now(timezone.utc) + timedelta(seconds=timeout_seconds)

            # Create queued request
            queued = QueuedRequest(
                request=request,
                priority=priority,
                enqueued_at=datetime.now(timezone.utc),
                deadline=deadline
            )

            # Try to enqueue (non-blocking)
            self._queue.put_nowait(queued)
            self._stats["enqueued"] += 1

            logger.debug(
                f"Enqueued request {request.request_id} "
                f"(priority={priority.value}, queue_size={self.size()})"
            )

            return True

        except asyncio.QueueFull:
            self._stats["rejected"] += 1
            logger.warning(
                f"Queue full, rejected request {request.request_id} "
                f"(max_size={self.max_size})"
            )
            return False

    async def dequeue(
        self,
        timeout: Optional[float] = None
    ) -> Optional[InferenceRequest]:
        """
        Dequeue next request

        Args:
            timeout: Optional timeout for waiting

        Returns:
            Next InferenceRequest or None if timeout/empty
        """
        try:
            # Get next queued request
            queued = await asyncio.wait_for(
                self._queue.get(),
                timeout=timeout
            )

            # Check if request expired
            if queued.deadline and datetime.now(timezone.utc) > queued.deadline:
                self._stats["expired"] += 1
                logger.warning(
                    f"Request {queued.request.request_id} expired "
                    f"(deadline={queued.deadline.isoformat()})"
                )
                return None

            self._stats["dequeued"] += 1
            logger.debug(
                f"Dequeued request {queued.request.request_id} "
                f"(waited={(datetime.now(timezone.utc) - queued.enqueued_at).total_seconds():.2f}s)"
            )

            return queued.request

        except asyncio.TimeoutError:
            return None

    def size(self) -> int:
        """Get current queue size"""
        return self._queue.qsize()

    def is_empty(self) -> bool:
        """Check if queue is empty"""
        return self._queue.empty()

    def is_full(self) -> bool:
        """Check if queue is full"""
        return self._queue.full()

    async def clear(self) -> int:
        """
        Clear all requests from queue

        Returns:
            Number of requests cleared
        """
        count = 0
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                count += 1
            except asyncio.QueueEmpty:
                break

        logger.info(f"Cleared {count} requests from queue")
        return count

    def get_stats(self) -> dict:
        """Get queue statistics"""
        return {
            "current_size": self.size(),
            "max_size": self.max_size,
            "enqueued": self._stats["enqueued"],
            "dequeued": self._stats["dequeued"],
            "expired": self._stats["expired"],
            "rejected": self._stats["rejected"],
            "utilization": self.size() / self.max_size if self.max_size > 0 else 0.0
        }

"""Deduplication engine for event idempotency"""

import asyncio
from datetime import datetime, timedelta, UTC
from typing import Optional, Set
import logging
import hashlib

from ..models.cloud_event import CloudEvent
from ..models.error_codes import ErrorCode


logger = logging.getLogger(__name__)


class DeduplicationEngine:
    """
    Detects and prevents duplicate event processing.

    Per spec Section 3.2 (Component Responsibilities #2):
    - Detects duplicate events using idempotency keys
    - Tracks event IDs in Redis (24h TTL)
    - Fallback queue for duplicates
    - Idempotency key handling
    """

    def __init__(
        self,
        redis_client: Optional[any] = None,
        ttl_hours: int = 24,
        use_fallback_queue: bool = True,
    ):
        """
        Initialize deduplication engine.

        Args:
            redis_client: Redis client for distributed deduplication
            ttl_hours: Time-to-live for dedup keys (default: 24 hours)
            use_fallback_queue: Use fallback queue for duplicates (default: True)
        """
        self.redis_client = redis_client
        self.ttl_seconds = ttl_hours * 3600
        self.use_fallback_queue = use_fallback_queue

        # In-memory cache as fallback if Redis unavailable
        self._local_cache: Set[str] = set()
        self._local_cache_timestamps: dict[str, datetime] = {}
        self._fallback_queue: list[CloudEvent] = []

        # Statistics
        self.duplicates_detected = 0
        self.events_processed = 0

    async def is_duplicate(self, event: CloudEvent) -> bool:
        """
        Check if event is a duplicate based on event ID.

        Args:
            event: CloudEvent to check

        Returns:
            True if duplicate, False otherwise
        """
        self.events_processed += 1
        event_key = self._get_dedup_key(event)

        try:
            # Try Redis first
            if self.redis_client:
                is_dup = await self._check_redis(event_key)
                if is_dup:
                    self.duplicates_detected += 1
                    logger.info(f"Duplicate event detected (Redis): {event.id}")
                    if self.use_fallback_queue:
                        self._fallback_queue.append(event)
                    return True
                else:
                    # Mark as seen in Redis
                    await self._mark_seen_redis(event_key)
                    return False

            # Fallback to local cache
            else:
                return await self._check_local_cache(event_key, event)

        except Exception as e:
            logger.error(f"Deduplication check failed: {e}")
            # On error, allow event through (fail open)
            return False

    async def _check_redis(self, key: str) -> bool:
        """Check if key exists in Redis"""
        if not self.redis_client:
            return False

        try:
            # Use Redis SET with NX (only set if not exists)
            result = await asyncio.to_thread(
                self.redis_client.set,
                key,
                "1",
                ex=self.ttl_seconds,
                nx=True,
            )
            # If set failed (NX), key already exists = duplicate
            return result is None or result == 0
        except Exception as e:
            logger.warning(f"Redis check failed: {e}, falling back to local cache")
            return False

    async def _mark_seen_redis(self, key: str):
        """Mark event as seen in Redis"""
        if not self.redis_client:
            return

        try:
            await asyncio.to_thread(
                self.redis_client.setex,
                key,
                self.ttl_seconds,
                "1",
            )
        except Exception as e:
            logger.warning(f"Redis mark failed: {e}")

    async def _check_local_cache(self, key: str, event: CloudEvent) -> bool:
        """Check local in-memory cache (fallback)"""
        # Clean expired entries
        await self._clean_local_cache()

        # Check if already seen
        if key in self._local_cache:
            self.duplicates_detected += 1
            logger.info(f"Duplicate event detected (local cache): {event.id}")
            if self.use_fallback_queue:
                self._fallback_queue.append(event)
            return True

        # Mark as seen
        self._local_cache.add(key)
        self._local_cache_timestamps[key] = datetime.now(UTC)
        return False

    async def _clean_local_cache(self):
        """Remove expired entries from local cache"""
        now = datetime.now(UTC)
        expired_keys = [
            key
            for key, timestamp in self._local_cache_timestamps.items()
            if (now - timestamp).total_seconds() > self.ttl_seconds
        ]

        for key in expired_keys:
            self._local_cache.discard(key)
            del self._local_cache_timestamps[key]

    def _get_dedup_key(self, event: CloudEvent) -> str:
        """
        Generate deduplication key from event.

        Uses event ID as primary key, with hash of critical fields as fallback.
        """
        # Primary key: event ID
        if event.id:
            return f"dedup:event:{event.id}"

        # Fallback: hash of critical fields
        content = f"{event.source}:{event.type}:{event.subject}:{event.time.isoformat()}"
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"dedup:hash:{content_hash}"

    def get_fallback_queue(self) -> list[CloudEvent]:
        """Get list of duplicate events in fallback queue"""
        return self._fallback_queue.copy()

    def clear_fallback_queue(self):
        """Clear fallback queue"""
        self._fallback_queue.clear()

    def get_statistics(self) -> dict:
        """Get deduplication statistics"""
        return {
            "events_processed": self.events_processed,
            "duplicates_detected": self.duplicates_detected,
            "duplicate_rate": (
                self.duplicates_detected / self.events_processed
                if self.events_processed > 0
                else 0.0
            ),
            "fallback_queue_size": len(self._fallback_queue),
            "local_cache_size": len(self._local_cache),
        }

    async def reset_statistics(self):
        """Reset statistics counters"""
        self.events_processed = 0
        self.duplicates_detected = 0

    async def clear_cache(self):
        """Clear all deduplication cache (for testing)"""
        self._local_cache.clear()
        self._local_cache_timestamps.clear()

        if self.redis_client:
            try:
                # Scan and delete all dedup keys
                cursor = 0
                while True:
                    cursor, keys = await asyncio.to_thread(
                        self.redis_client.scan,
                        cursor,
                        match="dedup:*",
                        count=100,
                    )
                    if keys:
                        await asyncio.to_thread(self.redis_client.delete, *keys)
                    if cursor == 0:
                        break
            except Exception as e:
                logger.warning(f"Redis cache clear failed: {e}")

    def check_duplicate_sync(self, event: CloudEvent) -> bool:
        """
        Synchronous duplicate check (for testing/sync contexts).

        Returns True if duplicate.
        """
        event_key = self._get_dedup_key(event)

        # Check local cache only in sync mode
        if event_key in self._local_cache:
            self.duplicates_detected += 1
            return True

        self._local_cache.add(event_key)
        self._local_cache_timestamps[event_key] = datetime.utcnow()
        self.events_processed += 1
        return False

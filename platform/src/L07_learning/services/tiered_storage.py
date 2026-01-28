"""
L07 Learning Layer - Tiered Storage

Multi-tier storage system with hot/warm/cold tiers and fallback support.
Hot tier: Fast in-memory storage for frequently accessed data
Warm tier: Medium-speed storage for semi-frequent access
Cold tier: Persistent storage for infrequent access
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field
from collections import OrderedDict
from enum import Enum

logger = logging.getLogger(__name__)


class StorageTier(Enum):
    """Storage tier levels."""
    HOT = "hot"      # Fast, in-memory
    WARM = "warm"    # Medium speed
    COLD = "cold"    # Persistent, slower


@dataclass
class StorageItem:
    """Item stored in tiered storage."""
    key: str
    value: Any
    tier: StorageTier
    created_at: float
    expires_at: Optional[float] = None
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        """Check if item has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def touch(self, extend_ttl: Optional[float] = None) -> None:
        """Update access time and optionally extend TTL."""
        self.access_count += 1
        self.last_accessed = time.time()
        if extend_ttl and self.expires_at:
            self.expires_at = time.time() + extend_ttl


class TieredStorage:
    """Multi-tier storage with automatic promotion/demotion.

    Features:
    - Hot/warm/cold tiers with different access speeds
    - Automatic promotion of frequently accessed items
    - Fallback queue for when primary storage fails
    - TTL support with automatic expiration
    - LRU eviction for hot tier capacity limits
    """

    def __init__(
        self,
        hot_capacity: int = 1000,
        warm_capacity: int = 10000,
        promotion_threshold: int = 3,
        default_ttl: Optional[float] = None,
    ):
        """Initialize tiered storage.

        Args:
            hot_capacity: Maximum items in hot tier
            warm_capacity: Maximum items in warm tier
            promotion_threshold: Access count to promote to hot
            default_ttl: Default time-to-live in seconds
        """
        self.hot_capacity = hot_capacity
        self.warm_capacity = warm_capacity
        self.promotion_threshold = promotion_threshold
        self.default_ttl = default_ttl

        # Storage tiers (using OrderedDict for LRU)
        self._hot: OrderedDict[str, StorageItem] = OrderedDict()
        self._warm: OrderedDict[str, StorageItem] = OrderedDict()
        self._cold: Dict[str, StorageItem] = {}

        # Fallback queue for failed writes
        self._fallback_queue: List[Tuple[str, Any, dict]] = []

        # State flags
        self._primary_available = True

        # Metrics
        self._total_writes = 0
        self._total_reads = 0
        self._cache_hits = 0
        self._cache_misses = 0

        logger.info(
            f"TieredStorage initialized (hot={hot_capacity}, "
            f"warm={warm_capacity}, promotion_threshold={promotion_threshold})"
        )

    async def write(
        self,
        key: str,
        value: Any,
        tier: str = "warm",
        ttl: Optional[float] = None,
    ) -> bool:
        """Write data to storage.

        Args:
            key: Storage key
            value: Data to store
            tier: Target tier (hot, warm, cold)
            ttl: Time-to-live in seconds

        Returns:
            True if successful, False if queued for fallback
        """
        self._total_writes += 1

        if not self._primary_available:
            # Queue for later
            self._fallback_queue.append((key, value, {"tier": tier, "ttl": ttl}))
            logger.warning(f"Primary storage unavailable, queued key '{key}'")
            return False

        # Calculate expiration
        expires_at = None
        if ttl is not None:
            expires_at = time.time() + ttl
        elif self.default_ttl is not None:
            expires_at = time.time() + self.default_ttl

        # Create item
        item = StorageItem(
            key=key,
            value=value,
            tier=StorageTier(tier),
            created_at=time.time(),
            expires_at=expires_at,
        )

        # Store in appropriate tier
        self._store_in_tier(item, tier)

        logger.debug(f"Wrote key '{key}' to {tier} tier")
        return True

    def _store_in_tier(self, item: StorageItem, tier: str) -> None:
        """Store item in specified tier with eviction if needed."""
        # Remove from all tiers first
        self._remove_from_all_tiers(item.key)

        if tier == "hot":
            # Evict if over capacity
            while len(self._hot) >= self.hot_capacity:
                evicted_key, evicted_item = self._hot.popitem(last=False)
                # Demote to warm
                evicted_item.tier = StorageTier.WARM
                self._warm[evicted_key] = evicted_item
                logger.debug(f"Evicted '{evicted_key}' from hot to warm")

            self._hot[item.key] = item

        elif tier == "warm":
            # Evict if over capacity
            while len(self._warm) >= self.warm_capacity:
                evicted_key, evicted_item = self._warm.popitem(last=False)
                # Demote to cold
                evicted_item.tier = StorageTier.COLD
                self._cold[evicted_key] = evicted_item
                logger.debug(f"Evicted '{evicted_key}' from warm to cold")

            self._warm[item.key] = item

        else:  # cold
            self._cold[item.key] = item

    def _remove_from_all_tiers(self, key: str) -> None:
        """Remove key from all tiers."""
        self._hot.pop(key, None)
        self._warm.pop(key, None)
        self._cold.pop(key, None)

    async def read(self, key: str) -> Optional[Any]:
        """Read data from storage.

        Args:
            key: Storage key

        Returns:
            Stored value or None if not found/expired
        """
        self._total_reads += 1

        item = self._find_item(key)

        if item is None:
            self._cache_misses += 1
            return None

        # Check expiration
        if item.is_expired():
            self._remove_from_all_tiers(key)
            self._cache_misses += 1
            return None

        self._cache_hits += 1

        # Update access stats
        item.touch()

        # Check for promotion
        if item.tier != StorageTier.HOT:
            if item.access_count >= self.promotion_threshold:
                self._promote_to_hot(item)

        # Move to end for LRU
        if item.tier == StorageTier.HOT:
            self._hot.move_to_end(key)
        elif item.tier == StorageTier.WARM:
            self._warm.move_to_end(key)

        return item.value

    def _find_item(self, key: str) -> Optional[StorageItem]:
        """Find item in any tier."""
        if key in self._hot:
            return self._hot[key]
        if key in self._warm:
            return self._warm[key]
        if key in self._cold:
            return self._cold[key]
        return None

    def _promote_to_hot(self, item: StorageItem) -> None:
        """Promote item to hot tier."""
        old_tier = item.tier
        self._store_in_tier(item, "hot")
        item.tier = StorageTier.HOT
        logger.debug(f"Promoted '{item.key}' from {old_tier.value} to hot")

    async def delete(self, key: str) -> bool:
        """Delete item from storage.

        Args:
            key: Storage key

        Returns:
            True if deleted, False if not found
        """
        if self._find_item(key) is None:
            return False

        self._remove_from_all_tiers(key)
        logger.debug(f"Deleted key '{key}'")
        return True

    async def touch(self, key: str, extend_by: Optional[float] = None) -> bool:
        """Touch item to update access time and optionally extend TTL.

        Args:
            key: Storage key
            extend_by: Seconds to extend TTL by

        Returns:
            True if found and touched, False otherwise
        """
        item = self._find_item(key)
        if item is None:
            return False

        if extend_by:
            item.touch(extend_ttl=extend_by)
        else:
            # Default: extend by original TTL amount
            original_ttl = item.expires_at - item.created_at if item.expires_at else None
            item.touch(extend_ttl=original_ttl)

        return True

    def get_tier_items(self, tier: str) -> Dict[str, Any]:
        """Get all items in a tier.

        Args:
            tier: Tier name (hot, warm, cold)

        Returns:
            Dictionary of key -> value
        """
        if tier == "hot":
            return {k: v.value for k, v in self._hot.items() if not v.is_expired()}
        elif tier == "warm":
            return {k: v.value for k, v in self._warm.items() if not v.is_expired()}
        else:
            return {k: v.value for k, v in self._cold.items() if not v.is_expired()}

    def get_item_tier(self, key: str) -> Optional[str]:
        """Get tier for an item.

        Args:
            key: Storage key

        Returns:
            Tier name or None if not found
        """
        if key in self._hot:
            return "hot"
        if key in self._warm:
            return "warm"
        if key in self._cold:
            return "cold"
        return None

    def fallback_queue_size(self) -> int:
        """Get size of fallback queue."""
        return len(self._fallback_queue)

    async def drain_fallback_queue(self) -> int:
        """Drain fallback queue when primary storage recovers.

        Returns:
            Number of items drained
        """
        if not self._primary_available:
            return 0

        drained = 0
        while self._fallback_queue:
            key, value, options = self._fallback_queue.pop(0)
            await self.write(key, value, **options)
            drained += 1

        if drained > 0:
            logger.info(f"Drained {drained} items from fallback queue")

        return drained

    def get_metrics(self) -> Dict[str, Any]:
        """Get storage metrics.

        Returns:
            Dictionary of metrics
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total_requests if total_requests > 0 else 0.0

        return {
            "total_writes": self._total_writes,
            "total_reads": self._total_reads,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": hit_rate,
            "hot_items": len(self._hot),
            "warm_items": len(self._warm),
            "cold_items": len(self._cold),
            "fallback_queue_size": len(self._fallback_queue),
            "primary_available": self._primary_available,
        }

    async def cleanup_expired(self) -> int:
        """Remove expired items from all tiers.

        Returns:
            Number of items removed
        """
        removed = 0

        for tier_dict in [self._hot, self._warm, self._cold]:
            expired_keys = [
                k for k, v in tier_dict.items() if v.is_expired()
            ]
            for key in expired_keys:
                tier_dict.pop(key, None)
                removed += 1

        if removed > 0:
            logger.info(f"Cleaned up {removed} expired items")

        return removed

    def clear(self) -> None:
        """Clear all storage."""
        self._hot.clear()
        self._warm.clear()
        self._cold.clear()
        self._fallback_queue.clear()
        logger.info("Cleared all storage")

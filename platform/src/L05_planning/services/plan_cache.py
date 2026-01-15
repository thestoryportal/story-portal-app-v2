"""
L05 Planning Layer - Plan Cache Service.

Two-level cache (L1 in-memory + L2 Redis) for plan caching.
"""

import hashlib
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from ..models import ExecutionPlan, PlanningError, ErrorCode

logger = logging.getLogger(__name__)


class PlanCache:
    """
    Two-level plan cache with L1 (in-memory) and L2 (Redis) backing.

    Cache key is derived from normalized goal text using SHA-256 hash.
    """

    def __init__(
        self,
        l1_max_size: int = 100,
        l2_ttl_seconds: int = 3600,
        enable_l2: bool = True,
    ):
        """
        Initialize plan cache.

        Args:
            l1_max_size: Maximum L1 cache entries (LRU eviction)
            l2_ttl_seconds: TTL for L2 Redis cache (default 1 hour)
            enable_l2: Enable Redis L2 cache (default True)
        """
        self.l1_max_size = l1_max_size
        self.l2_ttl_seconds = l2_ttl_seconds
        self.enable_l2 = enable_l2

        # L1 cache: in-memory LRU
        self._l1_cache: Dict[str, tuple[ExecutionPlan, datetime]] = {}
        self._l1_access_order: list[str] = []

        # L2 cache: Redis connection (lazily initialized)
        self._redis_client = None
        self._redis_connected = False

        # Metrics
        self.l1_hits = 0
        self.l1_misses = 0
        self.l2_hits = 0
        self.l2_misses = 0

        logger.info(f"PlanCache initialized: L1 size={l1_max_size}, L2 TTL={l2_ttl_seconds}s")

    def _compute_cache_key(self, goal_text: str) -> str:
        """
        Compute cache key from goal text.

        Normalizes whitespace and takes first 1000 characters, then SHA-256 hash.
        """
        normalized = " ".join(goal_text[:1000].split())
        return hashlib.sha256(normalized.encode()).hexdigest()

    async def get(self, goal_text: str) -> Optional[ExecutionPlan]:
        """
        Get plan from cache (L1 first, then L2).

        Args:
            goal_text: Goal text to look up

        Returns:
            Cached ExecutionPlan or None if not found
        """
        cache_key = self._compute_cache_key(goal_text)

        # Try L1 cache
        plan = self._get_l1(cache_key)
        if plan:
            self.l1_hits += 1
            logger.debug(f"L1 cache hit for key {cache_key[:16]}...")
            return plan

        self.l1_misses += 1

        # Try L2 cache (Redis)
        if self.enable_l2:
            plan = await self._get_l2(cache_key)
            if plan:
                self.l2_hits += 1
                logger.debug(f"L2 cache hit for key {cache_key[:16]}...")
                # Promote to L1
                self._set_l1(cache_key, plan)
                return plan

            self.l2_misses += 1

        return None

    async def set(self, goal_text: str, plan: ExecutionPlan, ttl_seconds: Optional[int] = None) -> None:
        """
        Store plan in cache (both L1 and L2).

        Args:
            goal_text: Goal text used as cache key
            plan: ExecutionPlan to cache
            ttl_seconds: Optional TTL override for L2 cache
        """
        cache_key = self._compute_cache_key(goal_text)
        ttl = ttl_seconds or self.l2_ttl_seconds

        # Store in L1
        self._set_l1(cache_key, plan)

        # Store in L2 (Redis)
        if self.enable_l2:
            await self._set_l2(cache_key, plan, ttl)

        logger.debug(f"Cached plan {plan.plan_id} with key {cache_key[:16]}...")

    def _get_l1(self, cache_key: str) -> Optional[ExecutionPlan]:
        """Get plan from L1 (in-memory) cache."""
        if cache_key in self._l1_cache:
            plan, timestamp = self._l1_cache[cache_key]
            # Update access order (LRU)
            self._l1_access_order.remove(cache_key)
            self._l1_access_order.append(cache_key)
            return plan
        return None

    def _set_l1(self, cache_key: str, plan: ExecutionPlan) -> None:
        """Set plan in L1 (in-memory) cache with LRU eviction."""
        # Evict if at max size
        if len(self._l1_cache) >= self.l1_max_size and cache_key not in self._l1_cache:
            # Evict least recently used
            lru_key = self._l1_access_order.pop(0)
            del self._l1_cache[lru_key]
            logger.debug(f"Evicted L1 cache key {lru_key[:16]}... (LRU)")

        # Store plan with timestamp
        self._l1_cache[cache_key] = (plan, datetime.utcnow())

        # Update access order
        if cache_key in self._l1_access_order:
            self._l1_access_order.remove(cache_key)
        self._l1_access_order.append(cache_key)

    async def _get_l2(self, cache_key: str) -> Optional[ExecutionPlan]:
        """Get plan from L2 (Redis) cache."""
        if not self._ensure_redis_connection():
            return None

        try:
            # Get from Redis
            data = self._redis_client.get(f"plan:{cache_key}")
            if data:
                # Deserialize
                plan_dict = json.loads(data)
                return ExecutionPlan.from_dict(plan_dict)
        except Exception as e:
            logger.warning(f"L2 cache get failed: {e}")
            return None

        return None

    async def _set_l2(self, cache_key: str, plan: ExecutionPlan, ttl_seconds: int) -> None:
        """Set plan in L2 (Redis) cache."""
        if not self._ensure_redis_connection():
            return

        try:
            # Serialize plan
            plan_dict = plan.to_dict()
            data = json.dumps(plan_dict)

            # Store in Redis with TTL
            self._redis_client.setex(f"plan:{cache_key}", ttl_seconds, data)
        except Exception as e:
            logger.warning(f"L2 cache set failed: {e}")

    def _ensure_redis_connection(self) -> bool:
        """Ensure Redis connection is established."""
        if self._redis_connected:
            return True

        if not self.enable_l2:
            return False

        # Try to connect to Redis
        try:
            import redis

            self._redis_client = redis.Redis(
                host="localhost",
                port=6379,
                db=0,
                decode_responses=True,
                socket_timeout=1,
                socket_connect_timeout=1,
            )
            # Test connection
            self._redis_client.ping()
            self._redis_connected = True
            logger.info("Connected to Redis L2 cache")
            return True
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. L2 cache disabled.")
            self.enable_l2 = False
            return False

    async def invalidate(self, goal_text: str) -> None:
        """
        Invalidate cached plan for goal.

        Args:
            goal_text: Goal text to invalidate
        """
        cache_key = self._compute_cache_key(goal_text)

        # Remove from L1
        if cache_key in self._l1_cache:
            del self._l1_cache[cache_key]
            self._l1_access_order.remove(cache_key)

        # Remove from L2
        if self.enable_l2 and self._ensure_redis_connection():
            try:
                self._redis_client.delete(f"plan:{cache_key}")
            except Exception as e:
                logger.warning(f"L2 cache invalidation failed: {e}")

        logger.debug(f"Invalidated cache for key {cache_key[:16]}...")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        l1_hit_rate = self.l1_hits / max(1, self.l1_hits + self.l1_misses)
        l2_hit_rate = self.l2_hits / max(1, self.l2_hits + self.l2_misses) if self.enable_l2 else 0.0

        return {
            "l1_size": len(self._l1_cache),
            "l1_max_size": self.l1_max_size,
            "l1_hits": self.l1_hits,
            "l1_misses": self.l1_misses,
            "l1_hit_rate": l1_hit_rate,
            "l2_enabled": self.enable_l2,
            "l2_connected": self._redis_connected,
            "l2_hits": self.l2_hits,
            "l2_misses": self.l2_misses,
            "l2_hit_rate": l2_hit_rate,
        }

    async def clear(self) -> None:
        """Clear all caches."""
        self._l1_cache.clear()
        self._l1_access_order.clear()

        if self.enable_l2 and self._ensure_redis_connection():
            try:
                # Clear all plan keys
                keys = self._redis_client.keys("plan:*")
                if keys:
                    self._redis_client.delete(*keys)
            except Exception as e:
                logger.warning(f"L2 cache clear failed: {e}")

        logger.info("Cleared all caches")

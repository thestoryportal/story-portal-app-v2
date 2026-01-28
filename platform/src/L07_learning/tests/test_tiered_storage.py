"""
L07 Learning Layer - Tiered Storage Tests

Tests for tiered storage with hot/warm/cold tiers.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta


@pytest.mark.l07
@pytest.mark.unit
class TestTieredStorageBasics:
    """Tests for basic tiered storage functionality."""

    @pytest.mark.asyncio
    async def test_write_to_storage(self):
        """Test writing data to storage."""
        from L07_learning.services.tiered_storage import TieredStorage

        storage = TieredStorage()

        await storage.write("key1", {"data": "value1"})

        result = await storage.read("key1")
        assert result is not None
        assert result["data"] == "value1"

    @pytest.mark.asyncio
    async def test_read_nonexistent_key_returns_none(self):
        """Test reading non-existent key returns None."""
        from L07_learning.services.tiered_storage import TieredStorage

        storage = TieredStorage()

        result = await storage.read("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_from_storage(self):
        """Test deleting from storage."""
        from L07_learning.services.tiered_storage import TieredStorage

        storage = TieredStorage()

        await storage.write("key1", {"data": "value"})
        deleted = await storage.delete("key1")

        assert deleted is True
        assert await storage.read("key1") is None


@pytest.mark.l07
@pytest.mark.unit
class TestHotStorage:
    """Tests for hot (fast) storage tier."""

    @pytest.mark.asyncio
    async def test_hot_storage_read_is_fast(self):
        """Test that hot storage reads are fast."""
        from L07_learning.services.tiered_storage import TieredStorage
        import time

        storage = TieredStorage()

        await storage.write("hot_key", {"data": "fast_data"}, tier="hot")

        start = time.time()
        result = await storage.read("hot_key")
        elapsed = time.time() - start

        assert result is not None
        assert elapsed < 0.1  # Should be very fast for in-memory

    @pytest.mark.asyncio
    async def test_hot_storage_has_capacity_limit(self):
        """Test that hot storage has capacity limits."""
        from L07_learning.services.tiered_storage import TieredStorage

        storage = TieredStorage(hot_capacity=5)

        # Write more than capacity
        for i in range(10):
            await storage.write(f"key_{i}", {"data": i}, tier="hot")

        # Hot storage should have evicted some items
        hot_count = len(storage.get_tier_items("hot"))
        assert hot_count <= 5


@pytest.mark.l07
@pytest.mark.unit
class TestStorageTierPromotion:
    """Tests for tier promotion (frequently accessed items moved to hot)."""

    @pytest.mark.asyncio
    async def test_frequent_access_promotes_to_hot(self):
        """Test that frequently accessed items are promoted to hot."""
        from L07_learning.services.tiered_storage import TieredStorage

        storage = TieredStorage(promotion_threshold=3)

        # Write to cold tier
        await storage.write("key1", {"data": "value"}, tier="cold")

        # Access multiple times
        for _ in range(5):
            await storage.read("key1")

        # Should be promoted to hot
        tier = storage.get_item_tier("key1")
        assert tier == "hot"


@pytest.mark.l07
@pytest.mark.unit
class TestFallbackQueue:
    """Tests for fallback queue when primary storage unavailable."""

    @pytest.mark.asyncio
    async def test_write_to_fallback_when_primary_fails(self):
        """Test writing to fallback when primary storage fails."""
        from L07_learning.services.tiered_storage import TieredStorage

        storage = TieredStorage()

        # Simulate primary failure
        storage._primary_available = False

        await storage.write("fallback_key", {"data": "fallback_data"})

        # Should be in fallback queue
        assert storage.fallback_queue_size() > 0

    @pytest.mark.asyncio
    async def test_fallback_queue_drains_on_recovery(self):
        """Test that fallback queue drains when primary recovers."""
        from L07_learning.services.tiered_storage import TieredStorage

        storage = TieredStorage()

        # Simulate failure and write
        storage._primary_available = False
        await storage.write("key1", {"data": "value1"})
        await storage.write("key2", {"data": "value2"})

        # Simulate recovery
        storage._primary_available = True
        await storage.drain_fallback_queue()

        assert storage.fallback_queue_size() == 0
        assert await storage.read("key1") is not None


@pytest.mark.l07
@pytest.mark.unit
class TestStorageMetrics:
    """Tests for storage metrics."""

    @pytest.mark.asyncio
    async def test_get_storage_metrics(self):
        """Test getting storage metrics."""
        from L07_learning.services.tiered_storage import TieredStorage

        storage = TieredStorage()

        await storage.write("key1", {"data": "value1"})
        await storage.write("key2", {"data": "value2"})
        await storage.read("key1")

        metrics = storage.get_metrics()

        assert "total_writes" in metrics
        assert "total_reads" in metrics
        assert "hot_items" in metrics
        assert "warm_items" in metrics
        assert "cold_items" in metrics
        assert metrics["total_writes"] >= 2
        assert metrics["total_reads"] >= 1

    @pytest.mark.asyncio
    async def test_metrics_include_hit_rate(self):
        """Test that metrics include cache hit rate."""
        from L07_learning.services.tiered_storage import TieredStorage

        storage = TieredStorage()

        await storage.write("key1", {"data": "value"})
        await storage.read("key1")  # Hit
        await storage.read("key2")  # Miss

        metrics = storage.get_metrics()

        assert "hit_rate" in metrics
        assert 0 <= metrics["hit_rate"] <= 1


@pytest.mark.l07
@pytest.mark.unit
class TestStorageTTL:
    """Tests for time-to-live (TTL) functionality."""

    @pytest.mark.asyncio
    async def test_item_expires_after_ttl(self):
        """Test that items expire after TTL."""
        from L07_learning.services.tiered_storage import TieredStorage
        import asyncio

        storage = TieredStorage()

        await storage.write("ttl_key", {"data": "expiring"}, ttl=0.1)

        # Should exist immediately
        assert await storage.read("ttl_key") is not None

        # Wait for expiration
        await asyncio.sleep(0.15)

        # Should be expired
        assert await storage.read("ttl_key") is None

    @pytest.mark.asyncio
    async def test_touch_extends_ttl(self):
        """Test that touching an item extends its TTL."""
        from L07_learning.services.tiered_storage import TieredStorage
        import asyncio

        storage = TieredStorage()

        await storage.write("touch_key", {"data": "value"}, ttl=0.2)

        await asyncio.sleep(0.1)
        await storage.touch("touch_key")  # Extend TTL

        await asyncio.sleep(0.15)  # Past original TTL

        # Should still exist due to touch
        assert await storage.read("touch_key") is not None

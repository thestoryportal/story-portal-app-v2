"""
Test Result Cache

Tests for result caching with Redis.
"""

import pytest
from ..services import ResultCache
from ..models import ToolResult


@pytest.mark.asyncio
class TestResultCache:
    """Test ResultCache service"""

    @pytest.fixture
    async def cache(self, mock_redis_url):
        """Create cache instance"""
        cache = ResultCache(redis_url=mock_redis_url)
        try:
            await cache.initialize()
            yield cache
        finally:
            await cache.clear_all()
            await cache.close()

    async def test_cache_miss(self, cache, sample_tool_invoke_request):
        """Test cache miss"""
        result = await cache.get(sample_tool_invoke_request)
        assert result is None

    async def test_cache_set_and_get(self, cache, sample_tool_invoke_request):
        """Test caching and retrieval"""
        tool_result = ToolResult(result={"output": "test"})

        await cache.set(sample_tool_invoke_request, tool_result, ttl_seconds=60)

        cached = await cache.get(sample_tool_invoke_request)
        assert cached is not None
        assert cached.result == {"output": "test"}

    async def test_cache_invalidation(self, cache, sample_tool_invoke_request):
        """Test cache invalidation"""
        tool_result = ToolResult(result={"output": "test"})

        await cache.set(sample_tool_invoke_request, tool_result)

        # Verify cached
        cached = await cache.get(sample_tool_invoke_request)
        assert cached is not None

        # Invalidate
        await cache.invalidate(sample_tool_invoke_request)

        # Verify cache miss
        cached = await cache.get(sample_tool_invoke_request)
        assert cached is None

    async def test_idempotency_key(self, cache, sample_tool_invoke_request):
        """Test caching with idempotency key"""
        from ..models import ExecutionOptions

        sample_tool_invoke_request.execution_options = ExecutionOptions(
            idempotency_key="test_idempotency_123"
        )

        tool_result = ToolResult(result={"output": "idempotent"})

        await cache.set(sample_tool_invoke_request, tool_result)

        cached = await cache.get(sample_tool_invoke_request)
        assert cached is not None
        assert cached.result == {"output": "idempotent"}

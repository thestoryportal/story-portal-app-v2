"""
Tests for Document Bridge

Basic tests for document querying and claim verification.
"""

import pytest
import asyncio

from ..services.document_bridge import DocumentBridge, DocumentError


@pytest.fixture
def document_bridge():
    """Create DocumentBridge instance"""
    return DocumentBridge(config={
        "default_confidence_threshold": 0.7,
        "max_sources": 5,
        "cache_ttl_seconds": 60,
        "verify_claims": True,
    })


@pytest.mark.asyncio
async def test_document_bridge_initialization(document_bridge):
    """Test document bridge initialization"""
    await document_bridge.initialize()
    assert document_bridge.confidence_threshold == 0.7
    assert document_bridge.max_sources == 5
    assert document_bridge.verify_claims is True


@pytest.mark.asyncio
async def test_cache_key_generation(document_bridge):
    """Test cache key generation"""
    key1 = document_bridge._get_cache_key("test query", {"type": "spec"})
    key2 = document_bridge._get_cache_key("test query", {"type": "spec"})
    key3 = document_bridge._get_cache_key("test query", {"type": "doc"})

    assert key1 == key2
    assert key1 != key3


@pytest.mark.asyncio
async def test_cache_operations(document_bridge):
    """Test cache add/get operations"""
    await document_bridge.initialize()

    cache_key = "test_query"
    result = [{"id": "doc1", "title": "Test Doc"}]

    # Add to cache
    document_bridge._add_to_cache(cache_key, result)

    # Get from cache
    cached = document_bridge._get_from_cache(cache_key)
    assert cached == result

    # Clear cache
    await document_bridge.clear_cache()
    cached = document_bridge._get_from_cache(cache_key)
    assert cached is None


@pytest.mark.asyncio
async def test_query_documents_stub(document_bridge):
    """Test document query (stub implementation)"""
    await document_bridge.initialize()

    # Note: This uses stub MCP implementation
    results = await document_bridge.query_documents(
        query="test query",
        use_cache=False,
    )

    # Stub returns empty list
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_verify_claim_disabled(document_bridge):
    """Test claim verification when disabled"""
    document_bridge.verify_claims = False

    result = await document_bridge.verify_claim("test claim")

    assert result["verified"] is False
    assert result["confidence"] == 0.0
    assert "disabled" in result["explanation"].lower()


@pytest.mark.asyncio
async def test_cleanup(document_bridge):
    """Test document bridge cleanup"""
    await document_bridge.initialize()

    # Add some cache data
    document_bridge._add_to_cache("key1", [{"id": "doc1"}])

    await document_bridge.cleanup()

    assert len(document_bridge._cache) == 0

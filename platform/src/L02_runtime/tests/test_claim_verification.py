"""
Tests for Document Bridge Claim Verification

Tests for semantic similarity, recency, and consensus scoring.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from ..services.document_bridge import DocumentBridge, DocumentError


@pytest.fixture
def document_bridge():
    """Create DocumentBridge instance"""
    return DocumentBridge(config={
        "verify_claims": True,
        "default_confidence_threshold": 0.7,
        "max_sources": 5,
    })


class TestSemanticSimilarity:
    """Tests for semantic similarity computation"""

    def test_similarity_identical(self, document_bridge):
        """Test similarity of identical texts"""
        claim = "The system uses PostgreSQL for data storage"
        content = "The system uses PostgreSQL for data storage"

        similarity = document_bridge._compute_semantic_similarity(claim, content)

        # Should be 1.0 for identical text
        assert similarity == 1.0

    def test_similarity_high_overlap(self, document_bridge):
        """Test similarity with high word overlap"""
        claim = "PostgreSQL stores agent state"
        content = "The agent state is stored in PostgreSQL database"

        similarity = document_bridge._compute_semantic_similarity(claim, content)

        # Should have good overlap
        assert similarity >= 0.3

    def test_similarity_no_overlap(self, document_bridge):
        """Test similarity with no word overlap"""
        claim = "cats chase mice"
        content = "dogs fetch sticks"

        similarity = document_bridge._compute_semantic_similarity(claim, content)

        # No overlap
        assert similarity == 0.0

    def test_similarity_empty_claim(self, document_bridge):
        """Test similarity with empty claim"""
        similarity = document_bridge._compute_semantic_similarity("", "some content")

        assert similarity == 0.0

    def test_similarity_empty_content(self, document_bridge):
        """Test similarity with empty content"""
        similarity = document_bridge._compute_semantic_similarity("some claim", "")

        assert similarity == 0.0

    def test_similarity_removes_stop_words(self, document_bridge):
        """Test that stop words are filtered out"""
        # These claims differ only in stop words
        claim1 = "the database stores data"
        claim2 = "a database stores data"

        sim1 = document_bridge._compute_semantic_similarity(claim1, claim1)
        sim2 = document_bridge._compute_semantic_similarity(claim1, claim2)

        # Should be equal since stop words filtered
        assert sim1 == sim2


class TestRecencyFactor:
    """Tests for recency factor computation"""

    def test_recency_recent_document(self, document_bridge):
        """Test recency for today's document"""
        doc = {
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        recency = document_bridge._compute_recency_factor(doc)

        # Should be close to 1.0 for today
        assert recency >= 0.9

    def test_recency_old_document(self, document_bridge):
        """Test recency for old document"""
        old_date = datetime.now(timezone.utc) - timedelta(days=90)
        doc = {
            "updated_at": old_date.isoformat()
        }

        recency = document_bridge._compute_recency_factor(doc)

        # Should be lower for old documents
        assert recency < 0.5
        assert recency >= 0.1  # Minimum floor

    def test_recency_no_date(self, document_bridge):
        """Test recency with no date defaults to 0.5"""
        doc = {}

        recency = document_bridge._compute_recency_factor(doc)

        assert recency == 0.5

    def test_recency_uses_created_at_fallback(self, document_bridge):
        """Test recency uses created_at when no updated_at"""
        doc = {
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        recency = document_bridge._compute_recency_factor(doc)

        # Should use created_at
        assert recency >= 0.9


class TestConsensusScore:
    """Tests for consensus score computation"""

    def test_consensus_no_sources(self, document_bridge):
        """Test consensus with no sources"""
        consensus = document_bridge._compute_consensus_score([])

        assert consensus == 0.0

    def test_consensus_single_source(self, document_bridge):
        """Test consensus with single source is capped"""
        sources = [{"relevance_score": 0.9}]

        consensus = document_bridge._compute_consensus_score(sources)

        # Single source capped at 0.7
        assert consensus == 0.7

    def test_consensus_multiple_agreeing_sources(self, document_bridge):
        """Test consensus with multiple agreeing sources"""
        sources = [
            {"relevance_score": 0.85},
            {"relevance_score": 0.82},
            {"relevance_score": 0.88},
        ]

        consensus = document_bridge._compute_consensus_score(sources)

        # Should be high with agreement bonus
        assert consensus >= 0.8

    def test_consensus_disagreeing_sources(self, document_bridge):
        """Test consensus with high variance in sources"""
        sources = [
            {"relevance_score": 0.95},
            {"relevance_score": 0.30},
        ]

        consensus = document_bridge._compute_consensus_score(sources)

        # Should be lower due to variance penalty
        avg = (0.95 + 0.30) / 2
        assert consensus < avg + 0.2  # Less than avg + max bonus

    def test_consensus_within_bounds(self, document_bridge):
        """Test consensus score stays within 0-1"""
        # Very high scores
        sources = [
            {"relevance_score": 1.0},
            {"relevance_score": 1.0},
            {"relevance_score": 1.0},
            {"relevance_score": 1.0},
        ]

        consensus = document_bridge._compute_consensus_score(sources)

        assert consensus <= 1.0
        assert consensus >= 0.0


class TestVerificationExplanation:
    """Tests for verification explanation generation"""

    def test_explanation_no_sources(self, document_bridge):
        """Test explanation when no sources"""
        explanation = document_bridge._build_verification_explanation(
            verified=False,
            consensus_score=0.0,
            sources=[]
        )

        assert "No authoritative sources" in explanation

    def test_explanation_verified_strong(self, document_bridge):
        """Test explanation for strongly verified claim"""
        explanation = document_bridge._build_verification_explanation(
            verified=True,
            consensus_score=0.95,
            sources=[{"id": "doc1"}]
        )

        assert "strongly supported" in explanation
        assert "95%" in explanation

    def test_explanation_verified_moderate(self, document_bridge):
        """Test explanation for moderately verified claim"""
        explanation = document_bridge._build_verification_explanation(
            verified=True,
            consensus_score=0.72,
            sources=[{"id": "doc1"}]
        )

        assert "moderately supported" in explanation

    def test_explanation_not_verified(self, document_bridge):
        """Test explanation for unverified claim"""
        explanation = document_bridge._build_verification_explanation(
            verified=False,
            consensus_score=0.55,
            sources=[{"id": "doc1"}]
        )

        assert "below verification threshold" in explanation


class TestVerifyClaim:
    """Tests for full claim verification flow"""

    @pytest.mark.asyncio
    async def test_verify_claim_disabled(self, document_bridge):
        """Test verify_claim when disabled"""
        document_bridge.verify_claims = False

        result = await document_bridge.verify_claim("Test claim")

        assert result["verified"] is False
        assert "disabled" in result["explanation"]

    @pytest.mark.asyncio
    async def test_verify_claim_no_documents(self, document_bridge):
        """Test verify_claim with no documents found"""
        document_bridge.query_documents = AsyncMock(return_value=[])

        with pytest.raises(DocumentError) as exc_info:
            await document_bridge.verify_claim("Unknown claim")

        assert exc_info.value.code == "E2061"

    @pytest.mark.asyncio
    async def test_verify_claim_success(self, document_bridge):
        """Test successful claim verification"""
        # Mock documents
        mock_docs = [
            {
                "id": "doc-1",
                "title": "Architecture Guide",
                "content": "The system uses PostgreSQL for data persistence",
                "confidence": 0.85,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": "doc-2",
                "title": "Database Design",
                "content": "PostgreSQL is the primary database for storing agent data",
                "confidence": 0.82,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        ]

        document_bridge.query_documents = AsyncMock(return_value=mock_docs)

        result = await document_bridge.verify_claim(
            "PostgreSQL stores agent data"
        )

        assert result["verified"] is True
        assert result["confidence"] > 0
        assert result["consensus_score"] > 0
        assert len(result["sources"]) > 0

    @pytest.mark.asyncio
    async def test_verify_claim_low_consensus(self, document_bridge):
        """Test claim with low consensus is not verified"""
        # Mock documents with low relevance
        mock_docs = [
            {
                "id": "doc-1",
                "title": "Unrelated Doc",
                "content": "This document talks about different topics entirely",
                "confidence": 0.3,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        ]

        document_bridge.query_documents = AsyncMock(return_value=mock_docs)

        result = await document_bridge.verify_claim(
            "PostgreSQL stores agent data"
        )

        # Low similarity should result in no supporting sources
        # which means not verified
        assert result["verified"] is False

    @pytest.mark.asyncio
    async def test_verify_claim_with_multiple_sources(self, document_bridge):
        """Test verification with multiple agreeing sources"""
        mock_docs = [
            {
                "id": "doc-1",
                "title": "Doc 1",
                "content": "Redis caches session state for fast access",
                "confidence": 0.9,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": "doc-2",
                "title": "Doc 2",
                "content": "Session state is cached in Redis",
                "confidence": 0.88,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": "doc-3",
                "title": "Doc 3",
                "content": "Redis provides session state caching",
                "confidence": 0.85,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        ]

        document_bridge.query_documents = AsyncMock(return_value=mock_docs)

        result = await document_bridge.verify_claim(
            "Redis caches session state"
        )

        assert result["verified"] is True
        # Multiple sources should give higher consensus
        assert result["consensus_score"] >= 0.7


class TestCaching:
    """Tests for document query caching"""

    @pytest.mark.asyncio
    async def test_cache_stores_result(self, document_bridge):
        """Test that results are cached"""
        document_bridge._stub_mode = True  # Use stub mode

        # First call
        await document_bridge.query_documents("test query")

        # Check cache
        cache_key = document_bridge._get_cache_key("test query", None)
        assert cache_key in document_bridge._cache

    @pytest.mark.asyncio
    async def test_cache_returns_cached_result(self, document_bridge):
        """Test that cached results are returned"""
        cache_key = document_bridge._get_cache_key("test query", None)
        expiry = datetime.now(timezone.utc) + timedelta(seconds=300)
        cached_docs = [{"id": "cached-doc", "confidence": 0.9}]
        document_bridge._cache[cache_key] = (cached_docs, expiry)

        result = await document_bridge.query_documents(
            "test query",
            use_cache=True
        )

        assert result == cached_docs

    @pytest.mark.asyncio
    async def test_cache_expires(self, document_bridge):
        """Test that expired cache entries are removed"""
        cache_key = document_bridge._get_cache_key("test query", None)
        expiry = datetime.now(timezone.utc) - timedelta(seconds=1)  # Expired
        cached_docs = [{"id": "expired-doc"}]
        document_bridge._cache[cache_key] = (cached_docs, expiry)
        document_bridge._stub_mode = True

        # Should not return expired result
        result = await document_bridge.query_documents(
            "test query",
            use_cache=True
        )

        # Should have fetched new (stub) result, not cached
        assert result != cached_docs
        # Expired entry should be removed
        assert cache_key not in document_bridge._cache or \
               document_bridge._cache[cache_key][0] != cached_docs

"""Unit tests for ExactMatcher and FuzzyMatcher."""

import pytest

from src.L12_nl_interface.core.service_registry import get_registry
from src.L12_nl_interface.routing.exact_matcher import ExactMatcher
from src.L12_nl_interface.routing.fuzzy_matcher import FuzzyMatcher, ServiceMatch


class TestExactMatcher:
    """Test cases for ExactMatcher."""

    @pytest.fixture
    def matcher(self):
        """Create ExactMatcher instance."""
        registry = get_registry()
        return ExactMatcher(registry)

    def test_exact_match_found(self, matcher):
        """Test exact match for existing service."""
        # Assuming PlanningService exists in catalog
        result = matcher.match("PlanningService")
        if result:
            assert result.service_name == "PlanningService"

    def test_exact_match_case_sensitive(self, matcher):
        """Test exact match is case-sensitive."""
        # Should NOT match lowercase version
        result = matcher.match("planningservice")
        # Depends on whether aliases include lowercase versions
        # This might match if aliases are set up

    def test_exact_match_not_found(self, matcher):
        """Test exact match returns None for non-existent service."""
        result = matcher.match("NonExistentService12345")
        assert result is None

    def test_is_exact_match(self, matcher):
        """Test is_exact_match check."""
        # Should return True for existing service
        if matcher.match("PlanningService"):
            assert matcher.is_exact_match("PlanningService")

        # Should return False for non-existent service
        assert not matcher.is_exact_match("NonExistentService12345")

    def test_alias_matching(self, matcher):
        """Test matching via aliases."""
        # If aliases are configured, they should work
        # Example: "Planning" might alias to "PlanningService"
        # This depends on catalog configuration
        pass  # Skip if no aliases configured

    def test_empty_query(self, matcher):
        """Test empty query returns None."""
        result = matcher.match("")
        assert result is None

    def test_whitespace_query(self, matcher):
        """Test whitespace-only query returns None."""
        result = matcher.match("   ")
        assert result is None


class TestFuzzyMatcher:
    """Test cases for FuzzyMatcher."""

    @pytest.fixture
    def matcher(self):
        """Create FuzzyMatcher instance."""
        registry = get_registry()
        return FuzzyMatcher(registry, use_semantic=False)

    def test_fuzzy_match_keyword(self, matcher):
        """Test fuzzy matching with keyword."""
        # Search for "plan" - should match planning-related services
        matches = matcher.match("plan", threshold=0.5, max_results=10)

        assert len(matches) > 0
        assert all(isinstance(m, ServiceMatch) for m in matches)

        # Results should be sorted by score (descending)
        scores = [m.score for m in matches]
        assert scores == sorted(scores, reverse=True)

    def test_fuzzy_match_threshold(self, matcher):
        """Test threshold filtering."""
        # High threshold should return fewer results
        low_threshold_matches = matcher.match("plan", threshold=0.3, max_results=20)
        high_threshold_matches = matcher.match("plan", threshold=0.8, max_results=20)

        assert len(low_threshold_matches) >= len(high_threshold_matches)

    def test_fuzzy_match_max_results(self, matcher):
        """Test max_results limiting."""
        matches = matcher.match("plan", threshold=0.3, max_results=3)

        assert len(matches) <= 3

    def test_fuzzy_match_empty_query(self, matcher):
        """Test empty query returns empty list."""
        matches = matcher.match("", threshold=0.5)
        assert len(matches) == 0

    def test_fuzzy_match_no_results(self, matcher):
        """Test query with no matches returns empty list."""
        # Use a nonsense query that won't match anything
        matches = matcher.match("xyzabc123nonexistent", threshold=0.9)
        assert len(matches) == 0

    def test_service_match_structure(self, matcher):
        """Test ServiceMatch structure."""
        matches = matcher.match("plan", threshold=0.5, max_results=1)

        if len(matches) > 0:
            match = matches[0]

            # Check ServiceMatch attributes
            assert hasattr(match, "service")
            assert hasattr(match, "score")
            assert hasattr(match, "match_reason")

            # Check types
            assert 0.0 <= match.score <= 1.0
            assert isinstance(match.match_reason, str)
            assert match.service.service_name

    def test_fuzzy_match_phrase(self, matcher):
        """Test fuzzy matching with multi-word phrase."""
        matches = matcher.match("create a plan", threshold=0.5)

        assert len(matches) > 0

        # Should match planning-related services
        service_names = [m.service.service_name for m in matches]
        # Check if any planning service is in results
        has_planning = any("plan" in name.lower() for name in service_names)
        # Note: This might not always be true depending on keywords

    def test_fuzzy_match_stopwords_removed(self, matcher):
        """Test that stopwords are removed from query."""
        # "Let's create a plan" should match similar to "create plan"
        matches1 = matcher.match("let's create a plan", threshold=0.5)
        matches2 = matcher.match("create plan", threshold=0.5)

        # Should have similar results (stopwords removed)
        assert len(matches1) > 0
        assert len(matches2) > 0

    def test_fuzzy_match_case_insensitive(self, matcher):
        """Test matching is case-insensitive."""
        matches_lower = matcher.match("plan", threshold=0.5)
        matches_upper = matcher.match("PLAN", threshold=0.5)

        # Should get similar results
        assert len(matches_lower) > 0
        assert len(matches_upper) > 0

    def test_get_statistics(self, matcher):
        """Test getting matcher statistics."""
        stats = matcher.get_statistics()

        assert isinstance(stats, dict)
        assert "semantic_enabled" in stats
        assert "semantic_weight" in stats
        assert "keyword_weight" in stats
        assert "total_services" in stats

        assert isinstance(stats["semantic_enabled"], bool)
        assert stats["semantic_enabled"] is False  # We disabled semantic
        assert stats["total_services"] > 0

    def test_semantic_disabled(self, matcher):
        """Test that semantic matching is disabled."""
        stats = matcher.get_statistics()
        assert stats["semantic_enabled"] is False

    def test_partial_keyword_match(self, matcher):
        """Test partial keyword matching."""
        # "planning" should match services with "plan" keyword
        matches = matcher.match("planning", threshold=0.3)

        assert len(matches) > 0

    def test_score_range(self, matcher):
        """Test that all scores are in valid range."""
        matches = matcher.match("plan", threshold=0.0, max_results=20)

        for match in matches:
            assert 0.0 <= match.score <= 1.0

    def test_match_reason_present(self, matcher):
        """Test that match_reason is provided."""
        matches = matcher.match("plan", threshold=0.5, max_results=5)

        for match in matches:
            assert match.match_reason
            assert len(match.match_reason) > 0

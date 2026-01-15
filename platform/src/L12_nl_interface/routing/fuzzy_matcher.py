"""Fuzzy Matcher for L12 Natural Language Interface.

This module implements the FuzzyMatcher class for keyword-based and
semantic fuzzy matching with ranking. It enables natural language
queries like "Let's Plan" → PlanningService disambiguation.

Key features:
- Keyword-based similarity (Jaccard, overlap)
- Semantic similarity via L04 embeddings (optional)
- Ranked results with scores (0.0-1.0)
- Configurable threshold filtering
- Combined keyword + semantic scoring

Example:
    >>> matcher = FuzzyMatcher(registry)
    >>> matches = matcher.match("Let's Plan", threshold=0.7)
    >>> for match in matches:
    ...     print(f"{match.service.service_name}: {match.score:.2f}")
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Set

from ..core.service_registry import ServiceRegistry
from ..models.service_metadata import ServiceMetadata

logger = logging.getLogger(__name__)


@dataclass
class ServiceMatch:
    """Result of fuzzy matching with score.

    Attributes:
        service: Matched ServiceMetadata
        score: Match score (0.0-1.0, higher = better match)
        match_reason: Explanation of why this matched
    """

    service: ServiceMetadata
    score: float
    match_reason: str

    def __lt__(self, other: "ServiceMatch") -> bool:
        """Compare by score (for sorting, higher score first)."""
        return self.score > other.score  # Reverse for descending sort


class FuzzyMatcher:
    """Matcher for fuzzy service lookups using keywords and semantics.

    The FuzzyMatcher provides natural language service discovery using:
    1. Keyword-based similarity (Jaccard, overlap)
    2. Semantic similarity via embeddings (optional, requires L04)

    Results are ranked by combined score and filtered by threshold.

    Attributes:
        registry: ServiceRegistry for metadata access
        use_semantic: Whether to use semantic matching via L04
        semantic_weight: Weight for semantic score (0.0-1.0)
        keyword_weight: Weight for keyword score (0.0-1.0)

    Example:
        >>> from L12_nl_interface.core.service_registry import get_registry
        >>> from L12_nl_interface.routing.fuzzy_matcher import FuzzyMatcher
        >>> matcher = FuzzyMatcher(get_registry())
        >>> matches = matcher.match("create a plan", threshold=0.6)
        >>> for match in matches:
        ...     print(f"{match.service.service_name}: {match.score:.2f}")
    """

    def __init__(
        self,
        registry: ServiceRegistry,
        use_semantic: bool = False,
        semantic_weight: float = 0.5,
        keyword_weight: float = 0.5,
    ):
        """Initialize the fuzzy matcher.

        Args:
            registry: ServiceRegistry instance for metadata access
            use_semantic: Enable semantic matching via L04 embeddings
            semantic_weight: Weight for semantic score (default: 0.5)
            keyword_weight: Weight for keyword score (default: 0.5)
        """
        self.registry = registry
        self.use_semantic = use_semantic
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight

        # Validate weights
        if not (0.0 <= semantic_weight <= 1.0):
            raise ValueError("semantic_weight must be between 0.0 and 1.0")
        if not (0.0 <= keyword_weight <= 1.0):
            raise ValueError("keyword_weight must be between 0.0 and 1.0")

        # Normalize weights to sum to 1.0
        total_weight = semantic_weight + keyword_weight
        if total_weight > 0:
            self.semantic_weight = semantic_weight / total_weight
            self.keyword_weight = keyword_weight / total_weight
        else:
            self.semantic_weight = 0.5
            self.keyword_weight = 0.5

        logger.info(
            f"FuzzyMatcher initialized: semantic={use_semantic}, "
            f"weights=(keyword={self.keyword_weight:.2f}, semantic={self.semantic_weight:.2f})"
        )

    def match(
        self, query: str, threshold: float = 0.7, max_results: int = 10
    ) -> List[ServiceMatch]:
        """Match query to services using fuzzy matching.

        This method:
        1. Performs keyword-based matching
        2. Optionally performs semantic matching (if enabled)
        3. Combines scores with configured weights
        4. Filters by threshold
        5. Returns top max_results sorted by score

        Args:
            query: Natural language query (e.g., "Let's Plan")
            threshold: Minimum score threshold (0.0-1.0)
            max_results: Maximum number of results to return

        Returns:
            List of ServiceMatch objects sorted by score (descending)

        Example:
            >>> matches = matcher.match("create a plan", threshold=0.6)
            >>> if matches:
            ...     print(f"Best match: {matches[0].service.service_name}")
        """
        if not query or not query.strip():
            logger.debug("Empty query provided to fuzzy matcher")
            return []

        # Keyword matching (always performed)
        keyword_matches = self._keyword_match(query)

        # Semantic matching (optional)
        semantic_matches = []
        if self.use_semantic:
            try:
                semantic_matches = self._semantic_match(query)
            except Exception as e:
                logger.warning(f"Semantic matching failed: {e}, falling back to keyword-only")
                # Continue with keyword-only matching

        # Combine scores
        combined_matches = self._combine_scores(keyword_matches, semantic_matches)

        # Filter by threshold
        filtered_matches = [m for m in combined_matches if m.score >= threshold]

        # Sort by score (descending) and limit results
        filtered_matches.sort()  # Uses __lt__ for reverse sort
        result = filtered_matches[:max_results]

        logger.debug(
            f"Fuzzy match '{query}': {len(result)} results above threshold {threshold}"
        )

        return result

    def _keyword_match(self, query: str) -> List[ServiceMatch]:
        """Perform keyword-based fuzzy matching.

        Uses multiple similarity metrics:
        - Jaccard similarity on query words vs service keywords
        - Overlap coefficient (for substring matches)
        - Service name similarity (for direct name matches)

        Args:
            query: Query string

        Returns:
            List of ServiceMatch objects with keyword-based scores

        Example:
            >>> matches = matcher._keyword_match("create plan")
        """
        query_words = self._tokenize_query(query)
        matches = []

        all_services = self.registry.list_all_services()

        for service in all_services:
            # Calculate keyword similarity
            keyword_score = self._calculate_keyword_similarity(
                query_words, service.keywords
            )

            # Calculate service name similarity
            name_score = self._calculate_name_similarity(query, service.service_name)

            # Combine keyword and name scores (weighted average)
            # Keywords are more important (0.7) than name (0.3)
            combined_score = (0.7 * keyword_score) + (0.3 * name_score)

            if combined_score > 0.0:
                reason = f"Keyword match: {combined_score:.2f}"
                matches.append(
                    ServiceMatch(
                        service=service, score=combined_score, match_reason=reason
                    )
                )

        return matches

    def _semantic_match(self, query: str) -> List[ServiceMatch]:
        """Perform semantic matching using L04 embeddings.

        This method uses L04 ModelGateway to generate embeddings for
        the query and service descriptions, then calculates cosine
        similarity between them.

        Args:
            query: Query string

        Returns:
            List of ServiceMatch objects with semantic scores

        Raises:
            Exception: If L04 is unavailable or embedding fails

        Note:
            This is a placeholder. Actual implementation requires:
            1. L04 ModelGateway integration
            2. Embedding generation for query and service descriptions
            3. Cosine similarity calculation
            4. Caching for performance

        Example:
            >>> matches = matcher._semantic_match("create a strategic plan")
        """
        # Placeholder for semantic matching
        # TODO: Implement in Agent R3
        logger.debug("Semantic matching not yet implemented (Agent R3)")
        return []

    def _combine_scores(
        self, keyword_matches: List[ServiceMatch], semantic_matches: List[ServiceMatch]
    ) -> List[ServiceMatch]:
        """Combine keyword and semantic scores with configured weights.

        Args:
            keyword_matches: List of keyword-based matches
            semantic_matches: List of semantic-based matches

        Returns:
            List of ServiceMatch objects with combined scores

        Example:
            >>> combined = matcher._combine_scores(kw_matches, sem_matches)
        """
        # If no semantic matches, return keyword matches as-is
        if not semantic_matches:
            return keyword_matches

        # Build semantic score lookup
        semantic_scores = {
            match.service.service_name: match.score for match in semantic_matches
        }

        # Combine scores
        combined = []
        for kw_match in keyword_matches:
            service_name = kw_match.service.service_name
            kw_score = kw_match.score
            sem_score = semantic_scores.get(service_name, 0.0)

            # Weighted combination
            combined_score = (
                self.keyword_weight * kw_score + self.semantic_weight * sem_score
            )

            reason = f"Combined: keyword={kw_score:.2f}, semantic={sem_score:.2f}"
            combined.append(
                ServiceMatch(
                    service=kw_match.service, score=combined_score, match_reason=reason
                )
            )

        # Add semantic-only matches (not in keyword matches)
        keyword_names = {m.service.service_name for m in keyword_matches}
        for sem_match in semantic_matches:
            if sem_match.service.service_name not in keyword_names:
                # Only semantic score available
                combined_score = self.semantic_weight * sem_match.score
                reason = f"Semantic only: {sem_match.score:.2f}"
                combined.append(
                    ServiceMatch(
                        service=sem_match.service,
                        score=combined_score,
                        match_reason=reason,
                    )
                )

        return combined

    def _tokenize_query(self, query: str) -> Set[str]:
        """Tokenize query into normalized words.

        Tokenization:
        - Convert to lowercase
        - Remove punctuation
        - Split on whitespace
        - Remove stopwords (common words like "a", "the", "let's")

        Args:
            query: Query string

        Returns:
            Set of normalized query words

        Example:
            >>> matcher._tokenize_query("Let's create a plan")
            {'create', 'plan'}
        """
        # Stopwords to remove
        stopwords = {
            "a",
            "an",
            "the",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "can",
            "to",
            "of",
            "in",
            "for",
            "on",
            "with",
            "at",
            "by",
            "from",
            "as",
            "let",
            "lets",
            "let's",
            "i",
            "me",
            "my",
            "we",
            "our",
        }

        # Remove punctuation and convert to lowercase
        cleaned = "".join(c if c.isalnum() or c.isspace() else " " for c in query.lower())

        # Split and filter
        words = {
            word.strip()
            for word in cleaned.split()
            if word.strip() and word.strip() not in stopwords and len(word.strip()) > 2
        }

        return words

    def _calculate_keyword_similarity(
        self, query_words: Set[str], service_keywords: List[str]
    ) -> float:
        """Calculate keyword similarity using Jaccard and overlap.

        Uses:
        - Jaccard similarity: |intersection| / |union|
        - Overlap coefficient: |intersection| / min(|query|, |keywords|)
        - Takes maximum of both for best similarity

        Args:
            query_words: Set of normalized query words
            service_keywords: List of service keywords

        Returns:
            Similarity score (0.0-1.0)

        Example:
            >>> score = matcher._calculate_keyword_similarity(
            ...     {'create', 'plan'}, ['planning', 'plan', 'goal']
            ... )
        """
        if not query_words or not service_keywords:
            return 0.0

        # Normalize service keywords to lowercase
        keywords_lower = {kw.lower() for kw in service_keywords}

        # Calculate intersection
        intersection = query_words & keywords_lower

        if not intersection:
            # Check for partial matches (substring)
            partial_score = 0.0
            for query_word in query_words:
                for keyword in keywords_lower:
                    if query_word in keyword or keyword in query_word:
                        partial_score = max(partial_score, 0.5)
            return partial_score

        # Jaccard similarity
        union = query_words | keywords_lower
        jaccard = len(intersection) / len(union) if union else 0.0

        # Overlap coefficient
        min_size = min(len(query_words), len(keywords_lower))
        overlap = len(intersection) / min_size if min_size > 0 else 0.0

        # Return maximum (more generous matching)
        return max(jaccard, overlap)

    def _calculate_name_similarity(self, query: str, service_name: str) -> float:
        """Calculate similarity between query and service name.

        Uses simple substring and prefix matching.

        Args:
            query: Query string
            service_name: Service name

        Returns:
            Similarity score (0.0-1.0)

        Example:
            >>> score = matcher._calculate_name_similarity("Plan", "PlanningService")
        """
        query_lower = query.lower().replace(" ", "")
        name_lower = service_name.lower()

        # Exact match
        if query_lower == name_lower:
            return 1.0

        # Substring match
        if query_lower in name_lower or name_lower in query_lower:
            return 0.7

        # Prefix match
        if name_lower.startswith(query_lower) or query_lower.startswith(name_lower):
            return 0.6

        return 0.0

    def get_statistics(self) -> dict:
        """Get matcher statistics.

        Returns:
            Dict with statistics

        Example:
            >>> stats = matcher.get_statistics()
            >>> print(f"Semantic enabled: {stats['semantic_enabled']}")
        """
        return {
            "semantic_enabled": self.use_semantic,
            "semantic_weight": self.semantic_weight,
            "keyword_weight": self.keyword_weight,
            "total_services": len(self.registry.list_all_services()),
        }

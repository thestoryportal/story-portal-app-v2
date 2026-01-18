"""Exact Matcher for L12 Natural Language Interface.

This module implements the ExactMatcher class for O(1) hash-based
exact service name matching. It provides instant lookup for precise
service names like "PlanningService".

Key features:
- O(1) hash-based lookup (dict)
- Case-insensitive matching
- Alias support (e.g., "Planning" → "PlanningService")
- Query normalization (strip whitespace, lowercase)

Example:
    >>> matcher = ExactMatcher(registry)
    >>> service = matcher.match("PlanningService")
    >>> if service:
    ...     print(f"Found: {service.service_name}")
"""

import logging
from typing import Dict, List, Optional

from ..core.service_registry import ServiceRegistry
from ..models.service_metadata import ServiceMetadata

logger = logging.getLogger(__name__)


class ExactMatcher:
    """Matcher for exact service name lookups with O(1) complexity.

    The ExactMatcher provides instant service lookup using hash-based
    dictionary lookups. It supports case-insensitive matching and
    service name aliases for convenience.

    Attributes:
        registry: ServiceRegistry for metadata access
        exact_index: Dict mapping normalized names to ServiceMetadata
        alias_index: Dict mapping aliases to ServiceMetadata

    Example:
        >>> from L12_nl_interface.core.service_registry import get_registry
        >>> from L12_nl_interface.routing.exact_matcher import ExactMatcher
        >>> matcher = ExactMatcher(get_registry())
        >>> service = matcher.match("PlanningService")
        >>> print(service.service_name)
    """

    def __init__(self, registry: ServiceRegistry):
        """Initialize the exact matcher.

        Args:
            registry: ServiceRegistry instance for metadata access
        """
        self.registry = registry
        self.exact_index: Dict[str, ServiceMetadata] = {}
        self.alias_index: Dict[str, ServiceMetadata] = {}

        # Build indices
        self._build_indices()

        logger.info(
            f"ExactMatcher initialized: {len(self.exact_index)} services, "
            f"{len(self.alias_index)} aliases"
        )

    def _build_indices(self) -> None:
        """Build exact match and alias indices from registry.

        Creates:
        - exact_index: normalized_name -> ServiceMetadata
        - alias_index: alias -> ServiceMetadata (for common variations)
        """
        all_services = self.registry.list_all_services()

        for service in all_services:
            # Add exact match (normalized)
            normalized_name = self._normalize_query(service.service_name)
            self.exact_index[normalized_name] = service

            # Add common aliases
            aliases = self._generate_aliases(service.service_name)
            for alias in aliases:
                normalized_alias = self._normalize_query(alias)
                if normalized_alias not in self.alias_index:
                    self.alias_index[normalized_alias] = service

        logger.debug(
            f"Built indices: {len(self.exact_index)} exact, "
            f"{len(self.alias_index)} aliases"
        )

    def _normalize_query(self, query: str) -> str:
        """Normalize query for matching.

        Normalization:
        - Convert to lowercase
        - Strip leading/trailing whitespace
        - Remove extra internal whitespace

        Args:
            query: Query string to normalize

        Returns:
            Normalized query string

        Example:
            >>> matcher._normalize_query("  PlanningService  ")
            'planningservice'
        """
        return query.strip().lower().replace(" ", "")

    def _generate_aliases(self, service_name: str) -> List[str]:
        """Generate common aliases for a service name.

        Aliases include:
        - Without "Service" suffix (e.g., "Planning" for "PlanningService")
        - Without "Manager" suffix (e.g., "Lifecycle" for "LifecycleManager")
        - Without "Executor" suffix
        - Without "Engine" suffix
        - Without "Registry" suffix

        Args:
            service_name: Service name to generate aliases for

        Returns:
            List of alias strings

        Example:
            >>> matcher._generate_aliases("PlanningService")
            ['Planning', 'PlanningService']
        """
        aliases = []

        # Remove common suffixes
        suffixes = ["Service", "Manager", "Executor", "Engine", "Registry", "Handler"]

        for suffix in suffixes:
            if service_name.endswith(suffix) and len(service_name) > len(suffix):
                base_name = service_name[: -len(suffix)]
                if base_name:  # Ensure non-empty
                    aliases.append(base_name)

        return aliases

    def match(self, query: str) -> Optional[ServiceMetadata]:
        """Match query to a service using exact lookup.

        This method performs O(1) hash lookups. It tries:
        1. Exact match on normalized query
        2. Alias match if exact fails

        Args:
            query: Query string (e.g., "PlanningService" or "Planning")

        Returns:
            ServiceMetadata if exact match found, None otherwise

        Example:
            >>> service = matcher.match("PlanningService")
            >>> if service:
            ...     print(f"Matched: {service.service_name}")
            ... else:
            ...     print("No exact match")
        """
        if not query or not query.strip():
            logger.debug("Empty query provided to exact matcher")
            return None

        normalized_query = self._normalize_query(query)

        # Try exact match first
        if normalized_query in self.exact_index:
            service = self.exact_index[normalized_query]
            logger.debug(
                f"Exact match found for '{query}': {service.service_name}"
            )
            return service

        # Try alias match
        if normalized_query in self.alias_index:
            service = self.alias_index[normalized_query]
            logger.debug(
                f"Alias match found for '{query}': {service.service_name}"
            )
            return service

        # No match
        logger.debug(f"No exact match found for '{query}'")
        return None

    def is_exact_match(self, query: str) -> bool:
        """Check if query has an exact match.

        Args:
            query: Query string to check

        Returns:
            True if exact match exists, False otherwise

        Example:
            >>> if matcher.is_exact_match("PlanningService"):
            ...     print("Exact match available")
        """
        return self.match(query) is not None

    def list_exact_matches(self, queries: List[str]) -> Dict[str, Optional[ServiceMetadata]]:
        """Match multiple queries in batch.

        Args:
            queries: List of query strings

        Returns:
            Dict mapping query to ServiceMetadata (or None if no match)

        Example:
            >>> queries = ["PlanningService", "GoalDecomposer", "Unknown"]
            >>> matches = matcher.list_exact_matches(queries)
            >>> for query, service in matches.items():
            ...     if service:
            ...         print(f"{query} -> {service.service_name}")
        """
        return {query: self.match(query) for query in queries}

    def get_all_matchable_names(self) -> List[str]:
        """Get all matchable service names (exact + aliases).

        Returns:
            List of all names that can be matched

        Example:
            >>> names = matcher.get_all_matchable_names()
            >>> print(f"Can match {len(names)} names")
        """
        # Combine exact and alias keys, remove duplicates
        all_names = set(self.exact_index.keys()) | set(self.alias_index.keys())
        return sorted(list(all_names))

    def suggest_closest_exact(self, query: str, max_suggestions: int = 5) -> List[ServiceMetadata]:
        """Suggest closest exact matches based on string similarity.

        This is a fallback when no exact match is found. It uses
        simple string similarity (prefix matching) to suggest alternatives.

        Args:
            query: Query string
            max_suggestions: Maximum number of suggestions to return

        Returns:
            List of ServiceMetadata objects for closest matches

        Example:
            >>> suggestions = matcher.suggest_closest_exact("Plan")
            >>> for service in suggestions:
            ...     print(service.service_name)
        """
        if not query or not query.strip():
            return []

        normalized_query = self._normalize_query(query)
        suggestions = []

        # Find services with names starting with query
        for normalized_name, service in self.exact_index.items():
            if normalized_name.startswith(normalized_query):
                suggestions.append(service)

        # Sort by name length (shorter = more relevant)
        suggestions.sort(key=lambda s: len(s.service_name))

        return suggestions[:max_suggestions]

    def get_statistics(self) -> Dict[str, int]:
        """Get matcher statistics.

        Returns:
            Dict with statistics

        Example:
            >>> stats = matcher.get_statistics()
            >>> print(f"Exact matches: {stats['exact_count']}")
        """
        return {
            "exact_count": len(self.exact_index),
            "alias_count": len(self.alias_index),
            "total_matchable": len(set(self.exact_index.keys()) | set(self.alias_index.keys())),
        }

    def validate_indices(self) -> List[str]:
        """Validate matcher indices for inconsistencies.

        Returns:
            List of validation warnings (empty if all valid)

        Example:
            >>> warnings = matcher.validate_indices()
            >>> if warnings:
            ...     print("Warnings:", warnings)
        """
        warnings = []

        # Check for duplicate aliases pointing to different services
        alias_targets: Dict[str, List[str]] = {}
        for alias, service in self.alias_index.items():
            if alias not in alias_targets:
                alias_targets[alias] = []
            alias_targets[alias].append(service.service_name)

        for alias, targets in alias_targets.items():
            if len(targets) > 1:
                warnings.append(
                    f"Alias '{alias}' maps to multiple services: {targets}"
                )

        return warnings

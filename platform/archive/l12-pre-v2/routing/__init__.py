"""Routing components for L12 Natural Language Interface.

This package provides command routing and service matching:
- ExactMatcher: O(1) hash-based exact service name matching
- FuzzyMatcher: Keyword and semantic fuzzy matching with ranking
- CommandRouter: Routes commands to appropriate service methods
"""

from .exact_matcher import ExactMatcher
from .fuzzy_matcher import FuzzyMatcher, ServiceMatch
from .command_router import CommandRouter

__all__ = [
    "ExactMatcher",
    "FuzzyMatcher",
    "ServiceMatch",
    "CommandRouter",
]

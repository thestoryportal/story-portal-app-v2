"""Core components for L12 Natural Language Interface.

This package provides the foundational components:
- ServiceRegistry: Service catalog and metadata management
- ServiceFactory: Dynamic service instantiation with dependency resolution
- SessionManager: Conversation-scoped service lifecycle
"""

from .service_registry import ServiceRegistry, get_registry
from .service_factory import (
    ServiceFactory,
    DependencyError,
    CircularDependencyError,
)
from .session_manager import SessionManager, SessionInfo

__all__ = [
    "ServiceRegistry",
    "get_registry",
    "ServiceFactory",
    "DependencyError",
    "CircularDependencyError",
    "SessionManager",
    "SessionInfo",
]

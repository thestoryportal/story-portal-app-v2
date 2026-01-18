"""Service Factory for L12 Natural Language Interface.

This module implements the ServiceFactory class which handles dynamic
service instantiation with dependency resolution and two-phase initialization.

Key features:
- Dynamic import and instantiation from module paths
- Topological sort for dependency resolution
- Circular dependency detection
- Two-phase initialization (sync __init__ + async initialize())
- Per-session service caching
- Comprehensive error handling
"""

import importlib
import inspect
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from ..models import ErrorCode, ServiceMetadata
from .service_registry import ServiceRegistry

logger = logging.getLogger(__name__)


class DependencyError(Exception):
    """Error raised when dependency resolution fails."""

    pass


class CircularDependencyError(DependencyError):
    """Error raised when circular dependency is detected."""

    pass


class ServiceFactory:
    """Factory for dynamic service instantiation with dependency resolution.

    The ServiceFactory handles the complex process of creating service instances
    with proper dependency injection and initialization. It ensures:
    1. Dependencies are resolved in correct order (topological sort)
    2. Circular dependencies are detected and rejected
    3. Services are instantiated only once per session (cached)
    4. Two-phase initialization is handled (sync __init__ + async initialize())

    Attributes:
        registry: ServiceRegistry for metadata lookup
        session_cache: Dict mapping (session_id, service_name) -> instance

    Example:
        >>> factory = ServiceFactory(registry)
        >>> service = await factory.create_service("PlanningService", "session-123")
        >>> # Dependencies automatically resolved and initialized
    """

    def __init__(self, registry: ServiceRegistry):
        """Initialize the service factory.

        Args:
            registry: ServiceRegistry instance for metadata lookup
        """
        self.registry = registry
        # Cache: (session_id, service_name) -> service instance
        self.session_cache: Dict[Tuple[str, str], Any] = {}
        logger.info("ServiceFactory initialized")

    async def create_service(
        self,
        service_name: str,
        session_id: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Create and initialize a service instance with dependencies.

        This is the main entry point for service creation. It:
        1. Checks cache for existing instance
        2. Resolves dependency tree
        3. Creates instances in correct order
        4. Handles two-phase initialization
        5. Caches the result

        Args:
            service_name: Name of service to create
            session_id: Session identifier for isolation
            config: Optional configuration overrides

        Returns:
            Initialized service instance

        Raises:
            DependencyError: If dependency resolution fails
            CircularDependencyError: If circular dependency detected
            ImportError: If service module cannot be imported
            ValueError: If service not found in registry

        Example:
            >>> service = await factory.create_service(
            ...     "PlanningService",
            ...     "session-123",
            ...     config={"timeout": 30}
            ... )
        """
        # Check cache first
        cache_key = (session_id, service_name)
        if cache_key in self.session_cache:
            logger.debug(f"Returning cached instance: {service_name} (session {session_id})")
            return self.session_cache[cache_key]

        # Get service metadata
        metadata = self.registry.get_service(service_name)
        if not metadata:
            raise ValueError(f"Service '{service_name}' not found in registry")

        # Resolve dependency tree
        logger.info(f"Creating service '{service_name}' for session '{session_id}'")
        dependency_order = self._resolve_dependencies(service_name)
        logger.debug(f"Dependency order: {dependency_order}")

        # Create all services in dependency order
        created_services: Dict[str, Any] = {}
        for dep_name in dependency_order:
            dep_cache_key = (session_id, dep_name)

            # Use cached if available
            if dep_cache_key in self.session_cache:
                created_services[dep_name] = self.session_cache[dep_cache_key]
                continue

            # Create new instance
            dep_metadata = self.registry.get_service(dep_name)
            if not dep_metadata:
                raise DependencyError(
                    f"Dependency '{dep_name}' not found for service '{service_name}'"
                )

            # Instantiate with dependencies
            dep_instance = self._instantiate_service(
                dep_metadata, created_services, config
            )
            created_services[dep_name] = dep_instance

            # Cache it
            self.session_cache[dep_cache_key] = dep_instance

            # Initialize if async
            if dep_metadata.requires_async_init:
                await self._initialize_service(dep_instance, dep_name)

            logger.debug(f"Created and cached: {dep_name}")

        # Create the target service itself
        target_instance = self._instantiate_service(metadata, created_services, config)
        created_services[service_name] = target_instance
        self.session_cache[cache_key] = target_instance

        # Initialize if async
        if metadata.requires_async_init:
            await self._initialize_service(target_instance, service_name)

        logger.info(f"Successfully created service '{service_name}'")
        return target_instance

    def _resolve_dependencies(self, service_name: str) -> List[str]:
        """Resolve dependency tree using topological sort.

        Args:
            service_name: Root service to resolve dependencies for

        Returns:
            List of service names in dependency order (dependencies first)

        Raises:
            CircularDependencyError: If circular dependency detected
            DependencyError: If dependency cannot be resolved

        Example:
            >>> order = factory._resolve_dependencies("PlanningService")
            >>> # Returns: ["GoalDecomposer", "ModelGateway", "AgentExecutor", ...]
        """
        # Build dependency graph
        graph: Dict[str, Set[str]] = {}
        all_services: Set[str] = set()

        def build_graph(name: str) -> None:
            """Recursively build dependency graph."""
            if name in graph:
                return  # Already processed

            metadata = self.registry.get_service(name)
            if not metadata:
                raise DependencyError(f"Service '{name}' not found in registry")

            all_services.add(name)
            graph[name] = set(metadata.dependencies)

            for dep_name in metadata.dependencies:
                build_graph(dep_name)

        # Build graph starting from root
        build_graph(service_name)

        # Topological sort using DFS
        sorted_order: List[str] = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()  # For cycle detection

        def dfs(name: str) -> None:
            """DFS for topological sort with cycle detection."""
            if name in rec_stack:
                # Circular dependency detected!
                raise CircularDependencyError(
                    f"Circular dependency detected involving service '{name}'"
                )

            if name in visited:
                return

            rec_stack.add(name)
            visited.add(name)

            # Visit dependencies first
            for dep_name in graph.get(name, set()):
                dfs(dep_name)

            rec_stack.remove(name)
            sorted_order.append(name)

        # Perform DFS from all nodes
        for service in all_services:
            if service not in visited:
                dfs(service)

        # Remove the root service (we'll create it separately)
        if service_name in sorted_order:
            sorted_order.remove(service_name)

        return sorted_order

    def _instantiate_service(
        self,
        metadata: ServiceMetadata,
        available_services: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Instantiate a service class with dependency injection.

        Args:
            metadata: Service metadata
            available_services: Dict of already-created service instances
            config: Optional configuration overrides

        Returns:
            Service instance (not yet initialized if async)

        Raises:
            ImportError: If module cannot be imported
            TypeError: If class cannot be instantiated
            DependencyError: If required dependency not available

        Example:
            >>> instance = factory._instantiate_service(
            ...     metadata,
            ...     {"GoalDecomposer": decomposer_instance},
            ...     {"timeout": 30}
            ... )
        """
        # Import the module
        try:
            module = importlib.import_module(metadata.module_path)
        except ImportError as e:
            raise ImportError(
                f"Failed to import module '{metadata.module_path}' "
                f"for service '{metadata.service_name}': {e}"
            )

        # Get the class
        try:
            service_class = getattr(module, metadata.class_name)
        except AttributeError:
            raise ImportError(
                f"Class '{metadata.class_name}' not found in module "
                f"'{metadata.module_path}'"
            )

        # Inspect constructor to determine injection strategy
        init_signature = inspect.signature(service_class.__init__)
        init_params = {}

        # Try to inject dependencies by parameter name
        for param_name, param in init_signature.parameters.items():
            if param_name == "self":
                continue

            # Check if this parameter matches a dependency name
            if param_name in available_services:
                init_params[param_name] = available_services[param_name]
            # Check if parameter has dependency name in metadata.dependencies
            elif any(
                dep.lower() == param_name.lower() for dep in metadata.dependencies
            ):
                # Find the matching dependency (case-insensitive)
                for dep_name in metadata.dependencies:
                    if dep_name.lower() == param_name.lower():
                        if dep_name in available_services:
                            init_params[param_name] = available_services[dep_name]
                        break
            # Handle config parameters
            elif config and param_name in config:
                init_params[param_name] = config[param_name]
            # Handle optional parameters with defaults
            elif param.default != inspect.Parameter.empty:
                # Has default, skip injection
                continue
            # Required parameter but not available - log warning but continue
            else:
                logger.warning(
                    f"Parameter '{param_name}' for service "
                    f"'{metadata.service_name}' not available for injection"
                )

        # Instantiate
        try:
            instance = service_class(**init_params)
            logger.debug(
                f"Instantiated {metadata.service_name} with params: "
                f"{list(init_params.keys())}"
            )
            return instance
        except TypeError as e:
            raise TypeError(
                f"Failed to instantiate service '{metadata.service_name}': {e}"
            )

    async def _initialize_service(self, instance: Any, service_name: str) -> None:
        """Call async initialize() method on service if it exists.

        Args:
            instance: Service instance to initialize
            service_name: Service name (for logging)

        Raises:
            AttributeError: If initialize() method doesn't exist but is required
            Exception: Any exception raised by initialize()

        Example:
            >>> await factory._initialize_service(service_instance, "PlanningService")
        """
        if not hasattr(instance, "initialize"):
            logger.warning(
                f"Service '{service_name}' marked as requires_async_init "
                "but has no initialize() method"
            )
            return

        try:
            initialize_method = getattr(instance, "initialize")
            if inspect.iscoroutinefunction(initialize_method):
                await initialize_method()
                logger.debug(f"Async initialized: {service_name}")
            else:
                # Not async, call it anyway
                initialize_method()
                logger.debug(f"Sync initialized: {service_name}")
        except Exception as e:
            raise Exception(
                f"Failed to initialize service '{service_name}': {e}"
            ) from e

    def clear_session_cache(self, session_id: str) -> int:
        """Clear all cached services for a session.

        Args:
            session_id: Session to clear cache for

        Returns:
            Number of services cleared

        Example:
            >>> count = factory.clear_session_cache("session-123")
            >>> print(f"Cleared {count} services")
        """
        to_remove = [
            key for key in self.session_cache.keys() if key[0] == session_id
        ]

        for key in to_remove:
            del self.session_cache[key]

        logger.info(f"Cleared {len(to_remove)} services for session '{session_id}'")
        return len(to_remove)

    def clear_all_cache(self) -> int:
        """Clear all cached services across all sessions.

        Returns:
            Number of services cleared

        Example:
            >>> count = factory.clear_all_cache()
        """
        count = len(self.session_cache)
        self.session_cache.clear()
        logger.info(f"Cleared all {count} cached services")
        return count

    def get_cached_services(self, session_id: str) -> List[str]:
        """Get list of cached service names for a session.

        Args:
            session_id: Session to query

        Returns:
            List of service names cached for this session

        Example:
            >>> services = factory.get_cached_services("session-123")
            >>> print(f"Cached: {services}")
        """
        return [
            key[1] for key in self.session_cache.keys() if key[0] == session_id
        ]

    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with cache stats: total_cached, sessions_count, services_per_session

        Example:
            >>> stats = factory.get_cache_statistics()
            >>> print(f"Total cached: {stats['total_cached']}")
        """
        sessions = set(key[0] for key in self.session_cache.keys())
        services_per_session = {}

        for session_id in sessions:
            services_per_session[session_id] = len(
                [key for key in self.session_cache.keys() if key[0] == session_id]
            )

        return {
            "total_cached": len(self.session_cache),
            "sessions_count": len(sessions),
            "services_per_session": services_per_session,
        }

    def validate_service_dependencies(self, service_name: str) -> List[str]:
        """Validate that all dependencies for a service can be resolved.

        Args:
            service_name: Service to validate

        Returns:
            List of validation error messages (empty if valid)

        Example:
            >>> errors = factory.validate_service_dependencies("PlanningService")
            >>> if errors:
            ...     print("Validation failed:", errors)
        """
        errors = []

        try:
            # Try to resolve dependencies
            self._resolve_dependencies(service_name)
        except CircularDependencyError as e:
            errors.append(str(e))
        except DependencyError as e:
            errors.append(str(e))
        except Exception as e:
            errors.append(f"Unexpected error: {e}")

        return errors

"""
Request Router - Path-based Routing to Backend Services
"""

import re
import random
from typing import List, Dict, Optional
from ..models import (
    RequestContext,
    RouteDefinition,
    RouteMatch,
    BackendTarget,
    LoadBalancingStrategy,
)
from ..errors import ErrorCode, RoutingError


class RequestRouter:
    """
    Routes incoming requests to backend services

    Features:
    - Glob pattern matching for paths
    - Multiple backend targets with load balancing
    - API versioning support
    - Route-specific configuration
    """

    def __init__(self):
        self.routes: List[RouteDefinition] = []
        self._compiled_patterns: Dict[str, re.Pattern] = {}
        self._backend_connections: Dict[str, int] = {}  # Track connection counts

    def add_route(self, route: RouteDefinition) -> None:
        """Add route definition"""
        self.routes.append(route)
        # Compile glob pattern to regex
        pattern = self._glob_to_regex(route.path_pattern)
        self._compiled_patterns[route.route_id] = re.compile(pattern)

    def remove_route(self, route_id: str) -> None:
        """Remove route by ID"""
        self.routes = [r for r in self.routes if r.route_id != route_id]
        self._compiled_patterns.pop(route_id, None)

    async def match_route(self, context: RequestContext) -> RouteMatch:
        """
        Match request to route

        Args:
            context: Request context

        Returns:
            RouteMatch with selected backend

        Raises:
            RoutingError: If no route matches
        """
        method = context.metadata.method
        path = context.metadata.path
        api_version = context.metadata.api_version

        # Try to find matching route
        for route in self.routes:
            # Check method
            if method not in route.methods:
                continue

            # Check API version if specified
            if route.api_version and api_version != route.api_version:
                continue

            # Check path pattern
            pattern = self._compiled_patterns.get(route.route_id)
            if not pattern:
                continue

            match = pattern.match(path)
            if not match:
                continue

            # Extract path parameters
            path_params = match.groupdict()

            # Check if route is deprecated
            if route.deprecated:
                # Log warning but allow (with deprecation header)
                pass

            # Select backend using load balancing
            backend = await self._select_backend(route)

            if not backend:
                raise RoutingError(
                    ErrorCode.E9803,
                    "All backend replicas unavailable",
                    details={"route_id": route.route_id},
                )

            return RouteMatch(
                route=route,
                path_params=path_params,
                selected_backend=backend,
            )

        # No route found
        raise RoutingError(
            ErrorCode.E9001,
            "Route not found",
            details={"method": method, "path": path},
        )

    async def _select_backend(self, route: RouteDefinition) -> Optional[BackendTarget]:
        """
        Select backend using load balancing strategy

        Args:
            route: Route definition with backends

        Returns:
            Selected BackendTarget or None if all unhealthy
        """
        # Filter healthy backends
        healthy_backends = [b for b in route.backends if b.healthy]

        if not healthy_backends:
            return None

        # Apply load balancing strategy
        if route.load_balancing == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin_select(healthy_backends)

        elif route.load_balancing == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections_select(healthy_backends)

        elif route.load_balancing == LoadBalancingStrategy.RANDOM:
            return random.choice(healthy_backends)

        elif route.load_balancing == LoadBalancingStrategy.CONSISTENT_HASH:
            # Use first healthy backend for now
            return healthy_backends[0]

        else:
            return healthy_backends[0]

    def _round_robin_select(self, backends: List[BackendTarget]) -> BackendTarget:
        """Round-robin load balancing"""
        if not hasattr(self, "_round_robin_index"):
            self._round_robin_index = 0

        backend = backends[self._round_robin_index % len(backends)]
        self._round_robin_index += 1
        return backend

    def _least_connections_select(
        self, backends: List[BackendTarget]
    ) -> BackendTarget:
        """Least connections load balancing"""
        # Find backend with fewest connections
        min_connections = float("inf")
        selected = backends[0]

        for backend in backends:
            conn_count = self._backend_connections.get(backend.service_id, 0)
            if conn_count < min_connections:
                min_connections = conn_count
                selected = backend

        return selected

    def increment_connections(self, backend: BackendTarget) -> None:
        """Increment connection count for backend"""
        service_id = backend.service_id
        self._backend_connections[service_id] = (
            self._backend_connections.get(service_id, 0) + 1
        )

    def decrement_connections(self, backend: BackendTarget) -> None:
        """Decrement connection count for backend"""
        service_id = backend.service_id
        count = self._backend_connections.get(service_id, 0)
        self._backend_connections[service_id] = max(0, count - 1)

    def _glob_to_regex(self, pattern: str) -> str:
        """
        Convert glob pattern to regex

        Supports:
        - * for any characters within path segment
        - ** for any characters including /
        - {name} for named path parameters

        Examples:
        - /agents/{id} -> /agents/(?P<id>[^/]+)
        - /agents/{id}/* -> /agents/(?P<id>[^/]+)/.*
        - /agents/** -> /agents/.*
        """
        # Escape special regex characters except glob wildcards
        pattern = pattern.replace(".", r"\.")
        pattern = pattern.replace("?", r"\?")

        # Replace {name} with named capture groups
        pattern = re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", pattern)

        # Replace ** with .*
        pattern = pattern.replace("**", ".*")

        # Replace * with [^/]* (match within segment)
        pattern = re.sub(r"(?<!\.)(\*)(?!\.)", r"[^/]*", pattern)

        # Anchor pattern
        pattern = f"^{pattern}$"

        return pattern

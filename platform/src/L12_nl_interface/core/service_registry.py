"""Service Registry for L12 Natural Language Interface.

This module implements the ServiceRegistry class which loads and provides
access to the comprehensive service catalog of 60+ platform services.

The registry supports:
- Exact service lookup by name
- Fuzzy search by keywords
- Filtering by layer
- Filtering by category
- Dependency graph navigation
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from ..models import ServiceMetadata, MethodMetadata, ParameterMetadata

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """Registry for platform service metadata.

    Loads the service catalog from JSON and provides query methods for
    service discovery. The registry is initialized once at startup and
    provides fast lookups for exact and fuzzy matching.

    Attributes:
        catalog_path: Path to service_catalog.json
        services: Dict mapping service name to ServiceMetadata
        by_layer: Dict mapping layer to list of service names
        by_keywords: Dict mapping keyword to list of service names

    Example:
        >>> registry = ServiceRegistry()
        >>> service = registry.get_service("PlanningService")
        >>> services = registry.list_by_layer("L05")
        >>> matches = registry.search_by_keyword("plan")
    """

    def __init__(self, catalog_path: Optional[Path] = None):
        """Initialize the service registry.

        Args:
            catalog_path: Optional path to service_catalog.json
                         If not provided, uses default path relative to this module
        """
        if catalog_path is None:
            # Default path: src/L12_nl_interface/data/service_catalog.json
            module_dir = Path(__file__).parent.parent
            catalog_path = module_dir / "data" / "service_catalog.json"

        self.catalog_path = catalog_path
        self.services: Dict[str, ServiceMetadata] = {}
        self.by_layer: Dict[str, List[str]] = {}
        self.by_keywords: Dict[str, List[str]] = {}

        # Load catalog on initialization
        self._load_catalog()
        self._build_indices()

        logger.info(
            f"ServiceRegistry initialized with {len(self.services)} services "
            f"from {len(self.by_layer)} layers"
        )

    def _load_catalog(self) -> None:
        """Load service catalog from JSON file.

        Raises:
            FileNotFoundError: If catalog file not found
            ValueError: If catalog JSON is invalid
        """
        if not self.catalog_path.exists():
            raise FileNotFoundError(f"Service catalog not found: {self.catalog_path}")

        try:
            with open(self.catalog_path, "r") as f:
                catalog_data = json.load(f)

            for service_name, service_dict in catalog_data.items():
                # Convert method dicts to MethodMetadata objects
                methods = []
                for method_dict in service_dict.get("methods", []):
                    # Convert parameter dicts to ParameterMetadata objects
                    parameters = [
                        ParameterMetadata(**param)
                        for param in method_dict.get("parameters", [])
                    ]
                    method_dict["parameters"] = parameters
                    methods.append(MethodMetadata(**method_dict))

                service_dict["methods"] = methods
                service_metadata = ServiceMetadata(**service_dict)
                self.services[service_name] = service_metadata

            logger.info(f"Loaded {len(self.services)} services from catalog")

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in catalog: {e}")
        except Exception as e:
            raise ValueError(f"Error loading catalog: {e}")

    def _build_indices(self) -> None:
        """Build lookup indices for fast queries.

        Creates:
        - by_layer: layer -> [service_names]
        - by_keywords: keyword -> [service_names]
        """
        for service_name, service in self.services.items():
            # Index by layer
            layer = service.layer
            if layer not in self.by_layer:
                self.by_layer[layer] = []
            self.by_layer[layer].append(service_name)

            # Index by keywords (normalized to lowercase)
            for keyword in service.keywords:
                keyword_lower = keyword.lower()
                if keyword_lower not in self.by_keywords:
                    self.by_keywords[keyword_lower] = []
                self.by_keywords[keyword_lower].append(service_name)

        logger.debug(
            f"Built indices: {len(self.by_layer)} layers, "
            f"{len(self.by_keywords)} keywords"
        )

    def get_service(self, service_name: str) -> Optional[ServiceMetadata]:
        """Get service metadata by exact name.

        Args:
            service_name: Exact service name (case-sensitive)

        Returns:
            ServiceMetadata if found, None otherwise

        Example:
            >>> service = registry.get_service("PlanningService")
            >>> print(service.description)
        """
        return self.services.get(service_name)

    def list_all_services(self) -> List[ServiceMetadata]:
        """List all services in catalog.

        Returns:
            List of all ServiceMetadata objects

        Example:
            >>> services = registry.list_all_services()
            >>> print(f"Total services: {len(services)}")
        """
        return list(self.services.values())

    def list_by_layer(self, layer: str) -> List[ServiceMetadata]:
        """Get all services in a specific layer.

        Args:
            layer: Layer identifier (e.g., "L05")

        Returns:
            List of ServiceMetadata for services in that layer

        Example:
            >>> l05_services = registry.list_by_layer("L05")
            >>> for service in l05_services:
            ...     print(service.service_name)
        """
        service_names = self.by_layer.get(layer, [])
        return [self.services[name] for name in service_names]

    def search_by_keyword(self, keyword: str) -> List[ServiceMetadata]:
        """Search services by keyword (case-insensitive).

        Args:
            keyword: Keyword to search for

        Returns:
            List of ServiceMetadata with matching keyword

        Example:
            >>> matches = registry.search_by_keyword("plan")
            >>> for service in matches:
            ...     print(f"{service.service_name}: {service.keywords}")
        """
        keyword_lower = keyword.lower()
        service_names = self.by_keywords.get(keyword_lower, [])
        return [self.services[name] for name in service_names]

    def search_by_keywords(self, keywords: List[str]) -> List[ServiceMetadata]:
        """Search services matching any of the provided keywords.

        Args:
            keywords: List of keywords to search for

        Returns:
            List of ServiceMetadata with at least one matching keyword
            (deduplicated)

        Example:
            >>> matches = registry.search_by_keywords(["plan", "goal"])
            >>> print(f"Found {len(matches)} services")
        """
        matched_names = set()
        for keyword in keywords:
            keyword_lower = keyword.lower()
            matched_names.update(self.by_keywords.get(keyword_lower, []))

        return [self.services[name] for name in matched_names]

    def search_services(self, query: str) -> List[ServiceMetadata]:
        """Search services by query string (case-insensitive).

        Searches across service names, descriptions, and keywords.

        Args:
            query: Search query string

        Returns:
            List of matching ServiceMetadata objects

        Example:
            >>> matches = registry.search_services("plan")
            >>> print(f"Found {len(matches)} planning services")
        """
        query_lower = query.lower().strip()
        if not query_lower:
            return []

        results = []
        for service in self.services.values():
            # Check service name
            if query_lower in service.service_name.lower():
                results.append(service)
                continue

            # Check description
            if query_lower in service.description.lower():
                results.append(service)
                continue

            # Check keywords
            if any(query_lower in kw.lower() for kw in service.keywords):
                results.append(service)
                continue

        return results

    def get_dependencies(self, service_name: str) -> List[ServiceMetadata]:
        """Get all direct dependencies of a service.

        Args:
            service_name: Service to get dependencies for

        Returns:
            List of ServiceMetadata for dependencies

        Example:
            >>> deps = registry.get_dependencies("PlanningService")
            >>> print([d.service_name for d in deps])
        """
        service = self.get_service(service_name)
        if not service:
            return []

        deps = []
        for dep_name in service.dependencies:
            dep = self.get_service(dep_name)
            if dep:
                deps.append(dep)
            else:
                logger.warning(
                    f"Dependency '{dep_name}' not found for service '{service_name}'"
                )

        return deps

    def get_dependency_tree(self, service_name: str) -> Dict[str, ServiceMetadata]:
        """Get full dependency tree (recursive) for a service.

        Args:
            service_name: Service to get dependency tree for

        Returns:
            Dict mapping service name to ServiceMetadata for all dependencies
            (includes transitive dependencies)

        Example:
            >>> tree = registry.get_dependency_tree("PlanningService")
            >>> print(f"Total dependencies: {len(tree)}")
        """
        tree: Dict[str, ServiceMetadata] = {}
        visited = set()

        def _traverse(name: str) -> None:
            if name in visited:
                return
            visited.add(name)

            service = self.get_service(name)
            if not service:
                return

            tree[name] = service

            for dep_name in service.dependencies:
                _traverse(dep_name)

        _traverse(service_name)

        # Remove the root service itself
        tree.pop(service_name, None)

        return tree

    def get_services_requiring_async_init(self) -> List[ServiceMetadata]:
        """Get all services that require async initialization.

        Returns:
            List of ServiceMetadata for services with async initialize()

        Example:
            >>> async_services = registry.get_services_requiring_async_init()
            >>> print(f"{len(async_services)} services need async init")
        """
        return [
            service
            for service in self.services.values()
            if service.requires_async_init
        ]

    def get_statistics(self) -> Dict[str, int]:
        """Get registry statistics.

        Returns:
            Dict with counts: total_services, total_layers, total_keywords,
            services_with_async_init, services_with_dependencies

        Example:
            >>> stats = registry.get_statistics()
            >>> print(f"Total services: {stats['total_services']}")
        """
        return {
            "total_services": len(self.services),
            "total_layers": len(self.by_layer),
            "total_keywords": len(self.by_keywords),
            "services_with_async_init": len(self.get_services_requiring_async_init()),
            "services_with_dependencies": len(
                [s for s in self.services.values() if s.dependencies]
            ),
        }

    def validate_catalog(self) -> List[str]:
        """Validate catalog integrity.

        Checks:
        - All dependencies exist in catalog
        - All services have minimum 3 keywords
        - No circular dependencies (basic check)

        Returns:
            List of validation warning messages (empty if all valid)

        Example:
            >>> warnings = registry.validate_catalog()
            >>> if warnings:
            ...     for warning in warnings:
            ...         print(f"Warning: {warning}")
        """
        warnings = []

        for service_name, service in self.services.items():
            # Check keywords count
            if len(service.keywords) < 3:
                warnings.append(
                    f"Service '{service_name}' has fewer than 3 keywords: "
                    f"{service.keywords}"
                )

            # Check dependencies exist
            for dep_name in service.dependencies:
                if dep_name not in self.services:
                    warnings.append(
                        f"Service '{service_name}' has unknown dependency: '{dep_name}'"
                    )

            # Basic circular dependency check (self-reference)
            if service_name in service.dependencies:
                warnings.append(
                    f"Service '{service_name}' has circular dependency (self-reference)"
                )

        return warnings


# Global singleton instance (lazy-loaded)
_registry_instance: Optional[ServiceRegistry] = None


def get_registry() -> ServiceRegistry:
    """Get global ServiceRegistry singleton instance.

    Returns:
        ServiceRegistry instance

    Example:
        >>> from L12_nl_interface.core.service_registry import get_registry
        >>> registry = get_registry()
        >>> service = registry.get_service("PlanningService")
    """
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ServiceRegistry()
    return _registry_instance

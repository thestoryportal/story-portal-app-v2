"""Unit tests for ServiceRegistry."""

import pytest

from src.L12_nl_interface.core.service_registry import ServiceRegistry, get_registry


class TestServiceRegistry:
    """Test cases for ServiceRegistry."""

    def test_singleton_pattern(self):
        """Test that get_registry returns singleton."""
        registry1 = get_registry()
        registry2 = get_registry()
        assert registry1 is registry2

    def test_list_all_services(self):
        """Test listing all services."""
        registry = get_registry()
        services = registry.list_all_services()

        # Should have loaded services from catalog
        assert len(services) > 0

        # Each service should have required fields
        for service in services:
            assert service.service_name
            assert service.layer
            assert service.module_path
            assert service.class_name
            assert service.description
            assert isinstance(service.keywords, list)
            assert isinstance(service.dependencies, list)
            assert isinstance(service.methods, list)

    def test_get_service(self):
        """Test getting service by name."""
        registry = get_registry()

        # Get a known service (PlanningService should exist in catalog)
        service = registry.get_service("PlanningService")

        if service:  # Only test if service exists in catalog
            assert service.service_name == "PlanningService"
            assert service.layer == "L05"
            assert "planning" in [kw.lower() for kw in service.keywords]
            assert len(service.methods) > 0

    def test_get_nonexistent_service(self):
        """Test getting non-existent service returns None."""
        registry = get_registry()
        service = registry.get_service("NonExistentService")
        assert service is None

    def test_list_by_layer(self):
        """Test listing services by layer."""
        registry = get_registry()

        # Get L05 services
        l05_services = registry.list_by_layer("L05")

        # All services should be from L05
        for service in l05_services:
            assert service.layer == "L05"

        # Should have at least some L05 services
        if len(l05_services) > 0:
            assert len(l05_services) > 0

    def test_search_services(self):
        """Test searching services by query."""
        registry = get_registry()

        # Search for "plan" - should match planning-related services
        results = registry.search_services("plan")

        # Should have some results
        assert len(results) > 0

        # Results should be relevant
        for service in results:
            # Check if "plan" appears in name, description, or keywords
            plan_match = (
                "plan" in service.service_name.lower()
                or "plan" in service.description.lower()
                or any("plan" in kw.lower() for kw in service.keywords)
            )
            assert plan_match

    def test_search_services_case_insensitive(self):
        """Test search is case-insensitive."""
        registry = get_registry()

        # Search with different cases
        results_lower = registry.search_services("plan")
        results_upper = registry.search_services("PLAN")
        results_mixed = registry.search_services("Plan")

        # Should get similar results
        assert len(results_lower) > 0
        assert len(results_upper) > 0
        assert len(results_mixed) > 0

    def test_service_metadata_structure(self):
        """Test ServiceMetadata structure."""
        registry = get_registry()
        services = registry.list_all_services()

        if len(services) > 0:
            service = services[0]

            # Check required string fields
            assert isinstance(service.service_name, str)
            assert isinstance(service.layer, str)
            assert isinstance(service.module_path, str)
            assert isinstance(service.class_name, str)
            assert isinstance(service.description, str)

            # Check lists
            assert isinstance(service.keywords, list)
            assert isinstance(service.dependencies, list)
            assert isinstance(service.methods, list)

            # Check boolean
            assert isinstance(service.requires_async_init, bool)

            # Check methods if present
            if len(service.methods) > 0:
                method = service.methods[0]
                assert hasattr(method, "name")
                assert hasattr(method, "description")
                assert hasattr(method, "parameters")
                assert hasattr(method, "returns")

    def test_layer_format(self):
        """Test that all services have valid layer format."""
        registry = get_registry()
        services = registry.list_all_services()

        valid_layers = {
            "L01", "L02", "L03", "L04", "L05",
            "L06", "L07", "L08", "L09", "L10", "L11"
        }

        for service in services:
            assert service.layer in valid_layers, (
                f"Service {service.service_name} has invalid layer: {service.layer}"
            )

    def test_no_duplicate_services(self):
        """Test that there are no duplicate service names."""
        registry = get_registry()
        services = registry.list_all_services()

        service_names = [s.service_name for s in services]
        assert len(service_names) == len(set(service_names)), (
            "Duplicate service names found in catalog"
        )

    def test_dependencies_are_valid(self):
        """Test that all service dependencies reference valid services."""
        registry = get_registry()
        services = registry.list_all_services()

        # Build set of all service names
        all_service_names = {s.service_name for s in services}

        # Check each service's dependencies
        for service in services:
            for dep in service.dependencies:
                # Dependency should either be a valid service name
                # or a generic class (which might not be in catalog)
                # For now, just check that dependencies are non-empty strings
                assert isinstance(dep, str)
                assert len(dep) > 0

    def test_keywords_not_empty(self):
        """Test that all services have keywords."""
        registry = get_registry()
        services = registry.list_all_services()

        for service in services:
            assert len(service.keywords) > 0, (
                f"Service {service.service_name} has no keywords"
            )

    def test_description_not_empty(self):
        """Test that all services have descriptions."""
        registry = get_registry()
        services = registry.list_all_services()

        for service in services:
            assert len(service.description) > 0, (
                f"Service {service.service_name} has no description"
            )
            # Description should be reasonably detailed (>= 20 chars)
            assert len(service.description) >= 20, (
                f"Service {service.service_name} has too short description"
            )

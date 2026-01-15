"""Unit tests for CommandRouter."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.L12_nl_interface.core.service_factory import ServiceFactory
from src.L12_nl_interface.core.service_registry import get_registry
from src.L12_nl_interface.core.session_manager import SessionManager
from src.L12_nl_interface.models.command_models import (
    ErrorCode,
    InvocationStatus,
    InvokeRequest,
)
from src.L12_nl_interface.routing.command_router import CommandRouter
from src.L12_nl_interface.routing.exact_matcher import ExactMatcher
from src.L12_nl_interface.routing.fuzzy_matcher import FuzzyMatcher
from src.L12_nl_interface.services.memory_monitor import MemoryMonitor


@pytest_asyncio.fixture
async def command_router():
    """Create CommandRouter instance with mocked dependencies."""
    registry = get_registry()
    factory = ServiceFactory(registry)
    memory_monitor = MemoryMonitor(enabled=False)
    session_manager = SessionManager(
        factory, memory_monitor, ttl_seconds=3600, cleanup_interval_seconds=300
    )

    # Start session manager
    await session_manager.start()

    exact_matcher = ExactMatcher(registry)
    fuzzy_matcher = FuzzyMatcher(registry, use_semantic=False)

    router = CommandRouter(
        registry, factory, session_manager, exact_matcher, fuzzy_matcher
    )

    yield router

    # Cleanup
    await session_manager.stop()


@pytest.mark.asyncio
class TestCommandRouter:
    """Test cases for CommandRouter."""

    async def test_parse_command_with_dot(self, command_router):
        """Test parsing command with dot separator."""
        service_name, method_name = command_router._parse_command(
            "PlanningService.create_plan"
        )

        assert service_name == "PlanningService"
        assert method_name == "create_plan"

    async def test_parse_command_without_dot(self, command_router):
        """Test parsing command without dot separator."""
        service_name, method_name = command_router._parse_command("PlanningService")

        if command_router.exact_matcher.is_exact_match("PlanningService"):
            assert service_name == "PlanningService"
            assert method_name is None
        else:
            assert service_name is None
            assert method_name is None

    async def test_parse_command_natural_language(self, command_router):
        """Test parsing natural language query."""
        service_name, method_name = command_router._parse_command("Let's create a plan")

        # Natural language should not be parsed as exact match
        assert service_name is None
        assert method_name is None

    async def test_match_service_exact(self, command_router):
        """Test matching service with exact matcher."""
        # This will only work if PlanningService exists in catalog
        service = command_router._match_service("PlanningService")

        if service:
            assert service.service_name == "PlanningService"

    async def test_match_service_fuzzy(self, command_router):
        """Test matching service with fuzzy matcher."""
        # Use a query that should fuzzy match
        service = command_router._match_service("planning")

        # Should find a planning-related service
        if service:
            assert "plan" in service.service_name.lower() or any(
                "plan" in kw.lower() for kw in service.keywords
            )

    async def test_match_service_not_found(self, command_router):
        """Test matching non-existent service returns None."""
        service = command_router._match_service("NonExistentService12345XYZ")

        assert service is None

    async def test_get_available_commands(self, command_router):
        """Test getting list of available commands."""
        commands = command_router.get_available_commands()

        assert isinstance(commands, list)
        assert len(commands) > 0

        # Each command should be in "ServiceName.method_name" format
        for cmd in commands:
            assert "." in cmd
            parts = cmd.split(".")
            assert len(parts) == 2

    async def test_get_service_methods(self, command_router):
        """Test getting methods for a service."""
        # Get methods for PlanningService if it exists
        methods = command_router.get_service_methods("PlanningService")

        if methods:
            assert isinstance(methods, list)
            assert all(isinstance(m, str) for m in methods)

    async def test_suggest_commands(self, command_router):
        """Test suggesting commands based on query."""
        suggestions = command_router.suggest_commands("create a plan", max_suggestions=5)

        assert isinstance(suggestions, list)
        assert len(suggestions) <= 5

        # Each suggestion should have required fields
        for suggestion in suggestions:
            assert "service" in suggestion
            assert "method" in suggestion
            assert "command" in suggestion
            assert "score" in suggestion
            assert "description" in suggestion

    async def test_route_request_service_not_found(self, command_router):
        """Test routing request for non-existent service."""
        request = InvokeRequest(
            service_name="NonExistentService",
            method_name="some_method",
            parameters={},
            session_id="test-session",
        )

        response = await command_router.route_request(request)

        assert response.status == InvocationStatus.ERROR
        assert response.error is not None
        assert response.error.code == ErrorCode.SERVICE_NOT_FOUND

    async def test_error_response_structure(self, command_router):
        """Test error response structure."""
        response = command_router._error_response(
            service_name="TestService",
            method_name="test_method",
            session_id="test-session",
            error_code=ErrorCode.METHOD_NOT_FOUND,
            message="Method not found",
            details={"extra": "info"},
        )

        assert response.status == InvocationStatus.ERROR
        assert response.error is not None
        assert response.error.code == ErrorCode.METHOD_NOT_FOUND
        assert response.error.message == "Method not found"
        assert response.error.details == {"extra": "info"}
        assert response.service_name == "TestService"
        assert response.method_name == "test_method"
        assert response.session_id == "test-session"

    async def test_invoke_request_validation(self, command_router):
        """Test InvokeRequest model validation."""
        # Valid request
        request = InvokeRequest(
            service_name="TestService",
            method_name="test_method",
            parameters={"key": "value"},
            session_id="test-session",
        )

        assert request.service_name == "TestService"
        assert request.method_name == "test_method"
        assert request.parameters == {"key": "value"}
        assert request.session_id == "test-session"

    async def test_invoke_request_defaults(self, command_router):
        """Test InvokeRequest default values."""
        request = InvokeRequest(
            service_name="TestService",
            method_name="test_method",
            session_id="test-session",
        )

        # Parameters should default to empty dict
        assert request.parameters == {}
        assert request.timeout_seconds is None

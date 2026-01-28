"""
L11 Integration Layer - Request Orchestrator Tests.

Tests for the RequestOrchestrator service.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

from L11_integration.services import RequestOrchestrator, ServiceRegistry, CircuitBreaker
from L11_integration.models import ServiceInfo, ServiceStatus, RequestContext, IntegrationError
from .fixtures.mock_http import MockHTTPClient, MockHTTPStatusError


@pytest.mark.l11
@pytest.mark.unit
class TestRequestOrchestratorUnit:
    """Unit tests for RequestOrchestrator."""

    @pytest_asyncio.fixture
    async def setup_orchestrator(self, mock_http_client):
        """Set up orchestrator with mocks."""
        registry = ServiceRegistry(l11_bridge=None)
        await registry.start()

        # Register a test service
        service = ServiceInfo(
            service_id="test-service",
            service_name="L02_runtime",
            endpoint="http://localhost:8002",
            status=ServiceStatus.HEALTHY,
        )
        await registry.register_service(service)

        cb = CircuitBreaker(l11_bridge=None)
        orchestrator = RequestOrchestrator(
            service_registry=registry,
            circuit_breaker=cb,
        )
        await orchestrator.start()
        orchestrator._http_client = mock_http_client

        yield orchestrator, registry, cb, mock_http_client

        await orchestrator.stop()
        await registry.stop()

    @pytest.mark.asyncio
    async def test_route_request_success(self, setup_orchestrator):
        """Test successful request routing."""
        orchestrator, registry, cb, mock_http = setup_orchestrator
        mock_http.add_response("POST", "/api/test", {"result": "success"})

        result = await orchestrator.route_request(
            service_name="L02_runtime",
            method="POST",
            path="/api/test",
            data={"key": "value"},
        )

        assert result == {"result": "success"}
        assert mock_http.request_count() == 1

    @pytest.mark.asyncio
    async def test_route_request_with_context(self, setup_orchestrator):
        """Test request routing with trace context."""
        orchestrator, registry, cb, mock_http = setup_orchestrator
        mock_http.add_response("GET", "/health", {"status": "ok"})

        context = RequestContext.create()
        result = await orchestrator.route_request(
            service_name="L02_runtime",
            method="GET",
            path="/health",
            context=context,
        )

        assert result == {"status": "ok"}
        request = mock_http.get_requests()[0]
        assert "X-Trace-ID" in request["headers"] or "x-trace-id" in str(request["headers"]).lower()

    @pytest.mark.asyncio
    async def test_route_request_service_not_found(self, setup_orchestrator):
        """Test routing to non-existent service."""
        orchestrator, registry, cb, mock_http = setup_orchestrator

        with pytest.raises(IntegrationError) as exc_info:
            await orchestrator.route_request(
                service_name="nonexistent_service",
                method="GET",
                path="/test",
            )

        assert "E11001" in str(exc_info.value.code) or "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_route_request_http_error(self, setup_orchestrator):
        """Test handling of HTTP errors."""
        orchestrator, registry, cb, mock_http = setup_orchestrator
        mock_http.add_response("POST", "/error", {"error": "bad request"}, status_code=400)

        with pytest.raises(IntegrationError):
            await orchestrator.route_request(
                service_name="L02_runtime",
                method="POST",
                path="/error",
            )

    @pytest.mark.asyncio
    async def test_route_request_timeout(self, setup_orchestrator):
        """Test handling of request timeout."""
        orchestrator, registry, cb, mock_http = setup_orchestrator
        mock_http.set_timeout_for("GET", "/slow")

        with pytest.raises(IntegrationError) as exc_info:
            await orchestrator.route_request(
                service_name="L02_runtime",
                method="GET",
                path="/slow",
                timeout=1.0,
            )

        assert "E11302" in str(exc_info.value.code) or "timeout" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_broadcast_request(self, setup_orchestrator):
        """Test broadcasting request to multiple services."""
        orchestrator, registry, cb, mock_http = setup_orchestrator

        # Register additional service
        service2 = ServiceInfo(
            service_id="test-service-2",
            service_name="L03_tool_execution",
            endpoint="http://localhost:8003",
            status=ServiceStatus.HEALTHY,
        )
        await registry.register_service(service2)

        mock_http.add_response("GET", "8002", {"service": "L02"})
        mock_http.add_response("GET", "8003", {"service": "L03"})

        results = await orchestrator.broadcast_request(
            service_names=["L02_runtime", "L03_tool_execution"],
            method="GET",
            path="/health",
        )

        assert len(results) == 2
        assert "L02_runtime" in results
        assert "L03_tool_execution" in results

    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self, setup_orchestrator):
        """Test circuit breaker is used for requests."""
        orchestrator, registry, cb, mock_http = setup_orchestrator
        mock_http.add_response("GET", "/test", {"ok": True})

        # Make successful request
        await orchestrator.route_request(
            service_name="L02_runtime",
            method="GET",
            path="/test",
        )

        # Check circuit breaker recorded success
        circuit_state = await cb.get_state("L02_runtime")
        assert circuit_state is not None
        assert circuit_state.success_count >= 1


@pytest.mark.l11
@pytest.mark.unit
class TestRequestOrchestratorLifecycle:
    """Tests for RequestOrchestrator lifecycle."""

    @pytest.mark.asyncio
    async def test_start_creates_http_client(self):
        """Test that start creates HTTP client."""
        registry = ServiceRegistry(l11_bridge=None)
        cb = CircuitBreaker(l11_bridge=None)
        orchestrator = RequestOrchestrator(registry, cb)

        assert orchestrator._http_client is None

        await orchestrator.start()
        assert orchestrator._http_client is not None

        await orchestrator.stop()
        # Note: httpx client becomes closed but reference may remain

    @pytest.mark.asyncio
    async def test_route_without_start_fails(self):
        """Test routing without starting fails."""
        registry = ServiceRegistry(l11_bridge=None)
        cb = CircuitBreaker(l11_bridge=None)
        orchestrator = RequestOrchestrator(registry, cb)

        with pytest.raises(IntegrationError) as exc_info:
            await orchestrator.route_request(
                service_name="test",
                method="GET",
                path="/test",
            )

        assert "not started" in str(exc_info.value).lower()

"""
Tests for Request Router
"""

import pytest
from ..services.router import RequestRouter
from ..models import (
    RouteDefinition,
    BackendTarget,
    RequestContext,
    RequestMetadata,
)
from ..errors import RoutingError, ErrorCode


@pytest.mark.asyncio
async def test_route_matching():
    """Test basic route matching"""
    router = RequestRouter()

    # Add test route
    route = RouteDefinition(
        route_id="test_route",
        path_pattern="/api/agents/{id}",
        methods=["GET", "POST"],
        backends=[
            BackendTarget(
                service_id="backend1",
                host="localhost",
                port=8001,
            )
        ],
    )
    router.add_route(route)

    # Create request context
    context = RequestContext(
        trace_id="a" * 32,
        span_id="b" * 16,
        metadata=RequestMetadata(
            method="GET",
            path="/api/agents/123",
            client_ip="127.0.0.1",
        ),
    )

    # Match route
    match = await router.match_route(context)

    assert match.route.route_id == "test_route"
    assert match.path_params == {"id": "123"}
    assert match.selected_backend.service_id == "backend1"


@pytest.mark.asyncio
async def test_route_not_found():
    """Test route not found error"""
    router = RequestRouter()

    context = RequestContext(
        trace_id="a" * 32,
        span_id="b" * 16,
        metadata=RequestMetadata(
            method="GET",
            path="/api/unknown",
            client_ip="127.0.0.1",
        ),
    )

    with pytest.raises(RoutingError) as exc_info:
        await router.match_route(context)

    assert exc_info.value.code == ErrorCode.E9001


@pytest.mark.asyncio
async def test_glob_pattern_matching():
    """Test glob pattern matching"""
    router = RequestRouter()

    # Wildcard route
    route = RouteDefinition(
        route_id="wildcard_route",
        path_pattern="/api/agents/{id}/*",
        methods=["GET"],
        backends=[
            BackendTarget(
                service_id="backend1",
                host="localhost",
                port=8001,
            )
        ],
    )
    router.add_route(route)

    context = RequestContext(
        trace_id="a" * 32,
        span_id="b" * 16,
        metadata=RequestMetadata(
            method="GET",
            path="/api/agents/123/invoke",
            client_ip="127.0.0.1",
        ),
    )

    match = await router.match_route(context)
    assert match.route.route_id == "wildcard_route"


@pytest.mark.asyncio
async def test_method_mismatch():
    """Test HTTP method mismatch"""
    router = RequestRouter()

    route = RouteDefinition(
        route_id="post_only",
        path_pattern="/api/test",
        methods=["POST"],
        backends=[
            BackendTarget(
                service_id="backend1",
                host="localhost",
                port=8001,
            )
        ],
    )
    router.add_route(route)

    context = RequestContext(
        trace_id="a" * 32,
        span_id="b" * 16,
        metadata=RequestMetadata(
            method="GET",
            path="/api/test",
            client_ip="127.0.0.1",
        ),
    )

    with pytest.raises(RoutingError):
        await router.match_route(context)

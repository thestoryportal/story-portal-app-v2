"""HTTP API for L12 Natural Language Interface.

This module implements a FastAPI REST interface for L12 with the following endpoints:

POST /v1/services/invoke - Invoke a service method
GET /v1/services/search - Search services by query
GET /v1/services - List all services
GET /v1/services/{name} - Get service details
GET /v1/sessions/{id} - Get session metrics
GET /health - Health check

Example:
    >>> from L12_nl_interface.interfaces.http_api import create_app
    >>> app = create_app()
    >>> # Run with: uvicorn L12_nl_interface.interfaces.http_api:app --port 8005
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..config.settings import get_settings
from ..core.service_factory import ServiceFactory
from ..core.service_registry import ServiceRegistry, get_registry
from ..core.session_manager import SessionManager
from ..models.command_models import InvokeRequest, InvokeResponse, InvocationStatus
from ..models.service_metadata import ServiceMetadata
from ..routing.command_router import CommandRouter
from ..routing.exact_matcher import ExactMatcher
from ..routing.fuzzy_matcher import FuzzyMatcher, ServiceMatch
from ..services.memory_monitor import MemoryMonitor

logger = logging.getLogger(__name__)

# Global application state
_app_state: Dict[str, Any] = {}


class SearchRequest(BaseModel):
    """Request model for service search."""

    query: str = Field(..., description="Search query", min_length=1)
    threshold: float = Field(
        default=0.7, description="Minimum match score (0.0-1.0)", ge=0.0, le=1.0
    )
    max_results: int = Field(
        default=10, description="Maximum results to return", gt=0, le=50
    )


class SearchResult(BaseModel):
    """Result model for fuzzy search."""

    service_name: str = Field(..., description="Service name")
    description: str = Field(..., description="Service description")
    score: float = Field(..., description="Match score (0.0-1.0)")
    match_reason: str = Field(..., description="Why this service matched")
    layer: str = Field(..., description="Service layer")
    keywords: List[str] = Field(..., description="Service keywords")


class ServiceListItem(BaseModel):
    """Service list item for /v1/services."""

    service_name: str
    description: str
    layer: str
    keywords: List[str]
    dependencies_count: int
    methods_count: int


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    services_loaded: int
    active_sessions: int


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    logger.info("L12 HTTP API starting up...")

    # Initialize components
    settings = get_settings()
    settings.configure_logging()

    # Initialize core components
    registry = get_registry()
    factory = ServiceFactory(registry)
    memory_monitor = MemoryMonitor(
        enabled=settings.enable_memory_monitor,
        memory_limit_mb=settings.memory_limit_mb,
        snapshot_interval_seconds=settings.memory_snapshot_interval,
    )
    session_manager = SessionManager(
        factory,
        memory_monitor,
        ttl_seconds=settings.session_ttl_seconds,
        cleanup_interval_seconds=settings.cleanup_interval_seconds,
    )

    # Start session manager
    await session_manager.start()

    # Initialize routing
    exact_matcher = ExactMatcher(registry)
    fuzzy_matcher = FuzzyMatcher(
        registry,
        use_semantic=settings.use_semantic_matching,
    )
    command_router = CommandRouter(
        registry, factory, session_manager, exact_matcher, fuzzy_matcher
    )

    # Store in app state
    _app_state["settings"] = settings
    _app_state["registry"] = registry
    _app_state["factory"] = factory
    _app_state["session_manager"] = session_manager
    _app_state["memory_monitor"] = memory_monitor
    _app_state["exact_matcher"] = exact_matcher
    _app_state["fuzzy_matcher"] = fuzzy_matcher
    _app_state["command_router"] = command_router

    logger.info(
        f"L12 HTTP API started: {len(registry.list_all_services())} services loaded"
    )

    yield

    # Cleanup on shutdown
    logger.info("L12 HTTP API shutting down...")
    await session_manager.stop()
    logger.info("L12 HTTP API stopped")


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI application

    Example:
        >>> app = create_app()
        >>> # Run with: uvicorn module:app --port 8005
    """
    app = FastAPI(
        title="L12 Natural Language Interface API",
        description="REST API for accessing 60+ platform services via natural language",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check endpoint
    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    async def health_check():
        """Health check endpoint.

        Returns:
            Health status with basic metrics
        """
        registry = _app_state.get("registry")
        session_manager = _app_state.get("session_manager")

        services_count = len(registry.list_all_services()) if registry else 0
        active_sessions = (
            len(session_manager.list_sessions()) if session_manager else 0
        )

        return HealthResponse(
            status="healthy",
            version="1.0.0",
            services_loaded=services_count,
            active_sessions=active_sessions,
        )

    # Invoke service method endpoint
    @app.post("/v1/services/invoke", response_model=InvokeResponse, tags=["Services"])
    async def invoke_service(request: InvokeRequest):
        """Invoke a service method.

        Args:
            request: InvokeRequest with service_name, method_name, parameters

        Returns:
            InvokeResponse with result or error

        Example:
            POST /v1/services/invoke
            {
                "service_name": "PlanningService",
                "method_name": "create_plan",
                "parameters": {"goal": "test"},
                "session_id": "session-123"
            }
        """
        router = _app_state.get("command_router")
        if not router:
            raise HTTPException(status_code=500, detail="Router not initialized")

        try:
            response = await router.route_request(request)
            return response
        except Exception as e:
            logger.error(f"Error invoking service: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    # Search services endpoint
    @app.get("/v1/services/search", response_model=List[SearchResult], tags=["Services"])
    async def search_services(
        q: str = Query(..., description="Search query", min_length=1),
        threshold: float = Query(
            default=0.7, description="Minimum match score", ge=0.0, le=1.0
        ),
        max_results: int = Query(
            default=10, description="Maximum results", gt=0, le=50
        ),
    ):
        """Search services using fuzzy matching.

        Args:
            q: Search query (e.g., "create a plan")
            threshold: Minimum match score (0.0-1.0)
            max_results: Maximum number of results

        Returns:
            List of matching services with scores

        Example:
            GET /v1/services/search?q=create%20a%20plan&threshold=0.6
        """
        fuzzy_matcher = _app_state.get("fuzzy_matcher")
        if not fuzzy_matcher:
            raise HTTPException(status_code=500, detail="Fuzzy matcher not initialized")

        try:
            matches = fuzzy_matcher.match(q, threshold=threshold, max_results=max_results)

            return [
                SearchResult(
                    service_name=match.service.service_name,
                    description=match.service.description,
                    score=match.score,
                    match_reason=match.match_reason,
                    layer=match.service.layer,
                    keywords=match.service.keywords,
                )
                for match in matches
            ]
        except Exception as e:
            logger.error(f"Error searching services: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    # List all services endpoint
    @app.get("/v1/services", response_model=List[ServiceListItem], tags=["Services"])
    async def list_services(
        layer: Optional[str] = Query(
            default=None, description="Filter by layer (e.g., L05)"
        )
    ):
        """List all services or filter by layer.

        Args:
            layer: Optional layer filter (e.g., "L05")

        Returns:
            List of services

        Example:
            GET /v1/services?layer=L05
        """
        registry = _app_state.get("registry")
        if not registry:
            raise HTTPException(status_code=500, detail="Registry not initialized")

        try:
            if layer:
                services = registry.list_by_layer(layer)
            else:
                services = registry.list_all_services()

            return [
                ServiceListItem(
                    service_name=service.service_name,
                    description=service.description,
                    layer=service.layer,
                    keywords=service.keywords,
                    dependencies_count=len(service.dependencies),
                    methods_count=len(service.methods),
                )
                for service in services
            ]
        except Exception as e:
            logger.error(f"Error listing services: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    # Get service details endpoint
    @app.get("/v1/services/{service_name}", response_model=ServiceMetadata, tags=["Services"])
    async def get_service(service_name: str):
        """Get detailed information about a service.

        Args:
            service_name: Name of the service

        Returns:
            ServiceMetadata with full details

        Example:
            GET /v1/services/PlanningService
        """
        registry = _app_state.get("registry")
        if not registry:
            raise HTTPException(status_code=500, detail="Registry not initialized")

        service = registry.get_service(service_name)
        if not service:
            raise HTTPException(
                status_code=404, detail=f"Service '{service_name}' not found"
            )

        return service

    # Get session metrics endpoint
    @app.get("/v1/sessions/{session_id}", tags=["Sessions"])
    async def get_session(session_id: str):
        """Get metrics for a specific session.

        Args:
            session_id: Session identifier

        Returns:
            Session metrics

        Example:
            GET /v1/sessions/session-123
        """
        session_manager = _app_state.get("session_manager")
        if not session_manager:
            raise HTTPException(status_code=500, detail="Session manager not initialized")

        metrics = session_manager.get_session_metrics(session_id)
        if not metrics:
            raise HTTPException(
                status_code=404, detail=f"Session '{session_id}' not found"
            )

        return metrics

    # List all sessions endpoint
    @app.get("/v1/sessions", tags=["Sessions"])
    async def list_sessions():
        """List all active sessions with metrics.

        Returns:
            List of session metrics

        Example:
            GET /v1/sessions
        """
        session_manager = _app_state.get("session_manager")
        if not session_manager:
            raise HTTPException(status_code=500, detail="Session manager not initialized")

        return session_manager.get_all_session_metrics()

    # Global metrics endpoint
    @app.get("/v1/metrics", tags=["Metrics"])
    async def get_metrics():
        """Get global metrics across all sessions.

        Returns:
            Global metrics dictionary

        Example:
            GET /v1/metrics
        """
        session_manager = _app_state.get("session_manager")
        if not session_manager:
            raise HTTPException(status_code=500, detail="Session manager not initialized")

        return session_manager.get_global_metrics()

    return app


# Global app instance
app = create_app()


def get_app() -> FastAPI:
    """Get global FastAPI application instance.

    Returns:
        FastAPI application

    Example:
        >>> from L12_nl_interface.interfaces.http_api import get_app
        >>> app = get_app()
    """
    return app


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        app,
        host=settings.http_host,
        port=settings.http_port,
        log_level=settings.log_level.lower(),
    )

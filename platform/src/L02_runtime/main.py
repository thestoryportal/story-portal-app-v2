"""
L02 Agent Runtime Layer - FastAPI Application

Main HTTP server for the Agent Runtime service.
Provides agent lifecycle management API consumed by external clients.
"""

import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .runtime import AgentRuntime
from .routes import agents_router, execution_router

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("L02 Agent Runtime starting...")

    # Load configuration
    config_path = os.getenv("L02_CONFIG_PATH")
    if not config_path:
        default_config = Path(__file__).parent / "config" / "default_config.yaml"
        if default_config.exists():
            config_path = str(default_config)

    # Initialize AgentRuntime
    try:
        runtime = AgentRuntime(config_path=config_path)
        await runtime.initialize()
        app.state.runtime = runtime
        logger.info("AgentRuntime initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize AgentRuntime: {e}")
        # Create minimal runtime for health checks
        app.state.runtime = None
        app.state.startup_error = str(e)

    logger.info("L02 Agent Runtime started")

    yield

    # Shutdown
    logger.info("L02 Agent Runtime shutting down...")
    if hasattr(app.state, "runtime") and app.state.runtime:
        await app.state.runtime.cleanup()
    logger.info("L02 Agent Runtime shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="L02 Agent Runtime",
    description="Agent lifecycle management, execution, and sandbox orchestration",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(agents_router)
app.include_router(execution_router)


# ============================================================================
# Health Check Endpoints
# ============================================================================

@app.get("/health")
async def health():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "service": "l02-runtime",
        "version": "2.0.0"
    }


@app.get("/health/live")
async def health_live():
    """Liveness probe for Kubernetes"""
    return {"status": "alive"}


@app.get("/health/ready")
async def health_ready():
    """Readiness probe for Kubernetes"""
    runtime = getattr(app.state, "runtime", None)
    if runtime:
        return {"status": "ready"}

    startup_error = getattr(app.state, "startup_error", None)
    return {
        "status": "not_ready",
        "reason": startup_error or "AgentRuntime not initialized"
    }


@app.get("/")
async def root():
    """Root endpoint with service info"""
    runtime = getattr(app.state, "runtime", None)
    backend_type = "unknown"
    if runtime and runtime.backend:
        backend_type = type(runtime.backend).__name__

    return {
        "service": "L02 Agent Runtime",
        "version": "2.0.0",
        "status": "operational" if runtime else "degraded",
        "backend": backend_type,
        "endpoints": {
            "spawn": "/api/agents/spawn",
            "terminate": "/api/agents/{agent_id}/terminate",
            "suspend": "/api/agents/{agent_id}/suspend",
            "resume": "/api/agents/{agent_id}/resume",
            "state": "/api/agents/{agent_id}/state",
            "execute": "/api/agents/{agent_id}/execute",
            "stream": "/api/agents/{agent_id}/execute/stream",
            "health": "/health/ready"
        }
    }

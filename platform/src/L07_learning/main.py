"""
L07 Learning Layer - FastAPI Application

Main HTTP server for the Learning Layer service.
Provides training, model management, and learning pipeline APIs.
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .observability.metrics import (
    get_metrics,
    get_metrics_content_type,
    get_metrics_manager,
)
from .routes import datasets_router, jobs_router, models_router, examples_router

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("L07 Learning Layer starting...")

    # Initialize metrics
    metrics_manager = get_metrics_manager()
    metrics_manager.initialize(version="2.0.0")

    # Initialize learning service (optional, for advanced features)
    try:
        from .services import LearningService
        learning_service = LearningService()
        await learning_service.initialize()
        app.state.learning_service = learning_service
        logger.info("L07 Learning Service initialized")
    except Exception as e:
        logger.warning(f"Learning service not initialized (optional): {e}")
        app.state.learning_service = None

    logger.info("L07 Learning Layer started")

    yield

    # Shutdown
    logger.info("L07 Learning Layer shutting down...")
    if hasattr(app.state, "learning_service") and app.state.learning_service:
        await app.state.learning_service.cleanup()
    logger.info("L07 Learning Layer shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="L07 Learning Layer",
    description="Training, model management, and learning pipeline service",
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

# Register routers
app.include_router(datasets_router)
app.include_router(jobs_router)
app.include_router(models_router)
app.include_router(examples_router)


# =============================================================================
# Health Check Endpoints
# =============================================================================

@app.get("/health")
async def health():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "service": "l07-learning",
        "version": "2.0.0"
    }


@app.get("/health/live")
async def health_live():
    """Liveness probe for Kubernetes"""
    return {"status": "alive"}


@app.get("/health/ready")
async def health_ready():
    """Readiness probe for Kubernetes"""
    # Routes are always ready - learning_service is optional
    return {"status": "ready"}


# =============================================================================
# Metrics Endpoint
# =============================================================================

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=get_metrics(),
        media_type=get_metrics_content_type(),
    )


# =============================================================================
# Root Endpoint
# =============================================================================

@app.get("/")
async def root():
    """Root endpoint with service info"""
    learning_service = getattr(app.state, "learning_service", None)
    return {
        "service": "L07 Learning Layer",
        "version": "2.0.0",
        "status": "operational",
        "learning_service": "initialized" if learning_service else "disabled",
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "datasets": "/datasets",
            "jobs": "/jobs",
            "models": "/models",
            "examples": "/examples",
        }
    }

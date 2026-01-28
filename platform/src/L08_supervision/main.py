"""
L08 Supervision Layer - FastAPI Application

Main HTTP server for the Supervision service.
Provides policy evaluation, constraint enforcement, anomaly detection,
escalation management, and audit trail capabilities.
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models.config import SupervisionConfiguration
from .models.error_codes import L08Error
from .services.supervision_service import SupervisionService

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("L08 Supervision Layer starting...")

    # Load configuration
    config = SupervisionConfiguration.from_env()
    logger.info(f"Configuration loaded (dev_mode={config.dev_mode})")

    # Initialize supervision service
    supervision_service = SupervisionService(config=config)
    await supervision_service.initialize()

    # Store in app state
    app.state.supervision_service = supervision_service
    app.state.config = config

    logger.info("L08 Supervision Layer started")

    yield

    # Shutdown
    logger.info("L08 Supervision Layer shutting down...")
    if hasattr(app.state, "supervision_service") and app.state.supervision_service:
        await app.state.supervision_service.cleanup()
    logger.info("L08 Supervision Layer shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="L08 Supervision Layer",
    description="Policy evaluation, constraint enforcement, anomaly detection, and escalation management",
    version="1.0.0",
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


# Exception handlers
@app.exception_handler(L08Error)
async def l08_error_handler(request: Request, exc: L08Error):
    """Handle L08-specific errors"""
    return JSONResponse(
        status_code=400,
        content=exc.to_dict()
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    """Handle generic errors"""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "code": "E8900",
            "message": "Internal server error",
            "details": str(exc) if os.getenv("DEBUG", "false").lower() == "true" else None
        }
    )


# ============================================================================
# Import and register routes
# ============================================================================

from .routes import (
    policies_router,
    evaluations_router,
    escalations_router,
    audit_router,
    health_router,
)

app.include_router(policies_router, prefix="/api/v1", tags=["Policies"])
app.include_router(evaluations_router, prefix="/api/v1", tags=["Evaluations"])
app.include_router(escalations_router, prefix="/api/v1", tags=["Escalations"])
app.include_router(audit_router, prefix="/api/v1", tags=["Audit"])
app.include_router(health_router, tags=["Health"])


# ============================================================================
# Root endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint with service info"""
    service = getattr(app.state, "supervision_service", None)
    return {
        "service": "L08 Supervision Layer",
        "version": "1.0.0",
        "status": "operational" if service and service._initialized else "initializing",
        "endpoints": {
            "policies": "/api/v1/policies",
            "evaluate": "/api/v1/evaluate",
            "escalations": "/api/v1/escalations",
            "audit": "/api/v1/audit",
            "health": "/health"
        }
    }


@app.get("/health")
async def health():
    """Basic health check endpoint"""
    service = getattr(app.state, "supervision_service", None)
    if service:
        return await service.health_check()
    return {
        "status": "starting",
        "service": "l08-supervision",
        "version": "1.0.0"
    }


@app.get("/health/live")
async def health_live():
    """Liveness probe for Kubernetes"""
    return {"status": "alive"}


@app.get("/health/ready")
async def health_ready():
    """Readiness probe for Kubernetes"""
    service = getattr(app.state, "supervision_service", None)
    if service and service._initialized:
        return {"status": "ready"}
    return JSONResponse(
        status_code=503,
        content={"status": "not_ready", "reason": "SupervisionService not initialized"}
    )

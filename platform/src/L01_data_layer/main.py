"""
L01 Data Layer - FastAPI Application

Provides centralized data persistence and event sourcing for the agentic platform.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .database import db
from .redis_client import redis_client
from .middleware import AuthenticationMiddleware
from .routers import (
    health_router,
    events_router,
    agents_router,
    tools_router,
    config_router,
    goals_router,
    plans_router,
    evaluations_router,
    feedback_router,
    documents_router,
    sessions_router,
    training_examples_router,
    datasets_router,
    models_router,
    # L06 Evaluation
    quality_scores_router,
    metrics_router,
    anomalies_router,
    compliance_results_router,
    alerts_router,
    # L09 API Gateway
    api_requests_router,
    authentication_events_router,
    rate_limit_events_router,
    # L10 Human Interface
    user_interactions_router,
    control_operations_router,
    # L11 Integration Layer
    saga_executions_router,
    saga_steps_router,
    circuit_breaker_events_router,
    service_registry_events_router,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    logger.info("Starting L01 Data Layer...")

    try:
        # Connect to database
        await db.connect()
        logger.info("Database connected")

        # Initialize schema
        await db.initialize_schema()
        logger.info("Database schema initialized")

        # Connect to Redis
        await redis_client.connect()
        logger.info("Redis connected")

        logger.info("L01 Data Layer started successfully")

    except Exception as e:
        logger.error(f"Failed to start L01 Data Layer: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down L01 Data Layer...")
    await db.disconnect()
    await redis_client.disconnect()
    logger.info("L01 Data Layer shut down")


# Create FastAPI app
app = FastAPI(
    title="L01 Data Layer",
    description="Centralized data persistence and event sourcing layer",
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

# Add Authentication middleware
# Note: Authentication can be disabled by setting L01_AUTH_DISABLED=true
import os
if os.getenv("L01_AUTH_DISABLED", "false").lower() != "true":
    app.add_middleware(BaseHTTPMiddleware, dispatch=AuthenticationMiddleware(app))
    logger.info("L01 authentication middleware enabled")
else:
    logger.warning("L01 authentication middleware DISABLED - not recommended for production!")

# Register routers
app.include_router(health_router)
app.include_router(events_router)
app.include_router(agents_router)
app.include_router(tools_router)
app.include_router(config_router)
app.include_router(goals_router)
app.include_router(plans_router)
app.include_router(evaluations_router)
app.include_router(feedback_router)
app.include_router(documents_router)
app.include_router(sessions_router)
app.include_router(training_examples_router)
app.include_router(datasets_router)
app.include_router(models_router)
# L06 Evaluation
app.include_router(quality_scores_router)
app.include_router(metrics_router)
app.include_router(anomalies_router)
app.include_router(compliance_results_router)
app.include_router(alerts_router)
# L09 API Gateway
app.include_router(api_requests_router)
app.include_router(authentication_events_router)
app.include_router(rate_limit_events_router)
# L10 Human Interface
app.include_router(user_interactions_router)
app.include_router(control_operations_router)
# L11 Integration Layer
app.include_router(saga_executions_router)
app.include_router(saga_steps_router)
app.include_router(circuit_breaker_events_router)
app.include_router(service_registry_events_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "L01 Data Layer",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "health": "/health/live, /health/ready",
            "events": "/events",
            "agents": "/agents",
            "tools": "/tools",
            "config": "/config",
            "goals": "/goals (L05 Planning)",
            "plans": "/plans (L05 Planning)",
            "evaluations": "/evaluations (Legacy L06)",
            "feedback": "/feedback",
            "documents": "/documents",
            "sessions": "/sessions",
            "training_examples": "/training-examples (L07 Learning)",
            "datasets": "/datasets (L07 Learning)",
            "models": "/models (L04 Model Gateway)",
            "quality_scores": "/quality-scores (L06 Evaluation)",
            "metrics": "/metrics (L06 Evaluation)",
            "anomalies": "/anomalies (L06 Evaluation)",
            "compliance_results": "/compliance-results (L06 Evaluation)",
            "alerts": "/alerts (L06 Evaluation)",
            "api_requests": "/api-requests (L09 API Gateway)",
            "authentication_events": "/authentication-events (L09 API Gateway)",
            "rate_limit_events": "/rate-limit-events (L09 API Gateway)",
            "user_interactions": "/user-interactions (L10 Human Interface)",
            "control_operations": "/control-operations (L10 Human Interface)",
            "saga_executions": "/saga-executions (L11 Integration)",
            "saga_steps": "/saga-steps (L11 Integration)",
            "circuit_breaker_events": "/circuit-breaker-events (L11 Integration)",
            "service_registry_events": "/service-registry-events (L11 Integration)",
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)

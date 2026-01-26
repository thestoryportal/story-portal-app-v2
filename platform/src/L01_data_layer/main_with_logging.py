"""
L01 Data Layer - FastAPI Application with Structured Logging

Example implementation showing integration of structured logging and correlation IDs.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import shared logging and middleware
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared import (
    setup_logging,
    CorrelationIDMiddleware,
    RequestLoggingMiddleware,
    PerformanceMonitoringMiddleware,
)

from .database import db
from .redis_client import redis_client
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
    quality_scores_router,
    metrics_router,
    anomalies_router,
    compliance_results_router,
    alerts_router,
    api_requests_router,
    authentication_events_router,
    rate_limit_events_router,
    user_interactions_router,
    control_operations_router,
    saga_executions_router,
    saga_steps_router,
    circuit_breaker_events_router,
    service_registry_events_router,
)

# Configure structured logging
SERVICE_NAME = "L01-data-layer"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
JSON_LOGS = os.getenv("JSON_LOGS", "true").lower() == "true"

logger = setup_logging(
    service_name=SERVICE_NAME,
    log_level=LOG_LEVEL,
    json_logs=JSON_LOGS,
    include_debug_fields=False,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    logger.info(
        "Starting L01 Data Layer",
        extra={
            'event': 'service_startup',
            'log_level': LOG_LEVEL,
            'json_logs': JSON_LOGS,
        }
    )

    try:
        # Connect to database
        await db.connect()
        logger.info(
            "Database connected",
            extra={
                'event': 'database_connected',
                'component': 'postgresql'
            }
        )

        # Initialize schema
        await db.initialize_schema()
        logger.info(
            "Database schema initialized",
            extra={'event': 'schema_initialized'}
        )

        # Connect to Redis
        await redis_client.connect()
        logger.info(
            "Redis connected",
            extra={
                'event': 'redis_connected',
                'component': 'redis'
            }
        )

        logger.info(
            "L01 Data Layer started successfully",
            extra={'event': 'service_ready'}
        )

    except Exception as e:
        logger.error(
            f"Failed to start L01 Data Layer",
            extra={
                'event': 'service_startup_failed',
                'error': str(e),
                'error_type': type(e).__name__,
            },
            exc_info=True
        )
        raise

    yield

    # Shutdown
    logger.info(
        "Shutting down L01 Data Layer",
        extra={'event': 'service_shutdown'}
    )

    try:
        await db.disconnect()
        logger.info(
            "Database disconnected",
            extra={'event': 'database_disconnected'}
        )

        await redis_client.disconnect()
        logger.info(
            "Redis disconnected",
            extra={'event': 'redis_disconnected'}
        )

        logger.info(
            "L01 Data Layer shut down successfully",
            extra={'event': 'service_shutdown_complete'}
        )
    except Exception as e:
        logger.error(
            f"Error during shutdown",
            extra={
                'event': 'service_shutdown_error',
                'error': str(e),
            },
            exc_info=True
        )


# Create FastAPI app
app = FastAPI(
    title="L01 Data Layer",
    description="Centralized data persistence and event sourcing layer with structured logging",
    version="2.0.0",
    lifespan=lifespan,
)

# Add correlation ID middleware (first in chain)
app.add_middleware(
    CorrelationIDMiddleware,
    service_name=SERVICE_NAME,
    log_requests=True,
    log_responses=True,
)

# Add performance monitoring middleware
app.add_middleware(
    PerformanceMonitoringMiddleware,
    service_name=SERVICE_NAME,
    slow_request_threshold_ms=1000.0,
    very_slow_threshold_ms=5000.0,
)

# Add request logging middleware (detailed metrics)
app.add_middleware(
    RequestLoggingMiddleware,
    service_name=SERVICE_NAME,
    log_body_size=True,
    max_body_log_size=1000,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(events_router, prefix="/events", tags=["events"])
app.include_router(agents_router, prefix="/agents", tags=["agents"])
app.include_router(tools_router, prefix="/tools", tags=["tools"])
app.include_router(config_router, prefix="/config", tags=["config"])
app.include_router(goals_router, prefix="/goals", tags=["goals"])
app.include_router(plans_router, prefix="/plans", tags=["plans"])
app.include_router(evaluations_router, prefix="/evaluations", tags=["evaluations"])
app.include_router(feedback_router, prefix="/feedback", tags=["feedback"])
app.include_router(documents_router, prefix="/documents", tags=["documents"])
app.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
app.include_router(training_examples_router, prefix="/training-examples", tags=["training"])
app.include_router(datasets_router, prefix="/datasets", tags=["datasets"])
app.include_router(models_router, prefix="/models", tags=["models"])
app.include_router(quality_scores_router, prefix="/quality-scores", tags=["quality"])
app.include_router(metrics_router, prefix="/metrics", tags=["metrics"])
app.include_router(anomalies_router, prefix="/anomalies", tags=["anomalies"])
app.include_router(compliance_results_router, prefix="/compliance-results", tags=["compliance"])
app.include_router(alerts_router, prefix="/alerts", tags=["alerts"])
app.include_router(api_requests_router, prefix="/api-requests", tags=["api-gateway"])
app.include_router(authentication_events_router, prefix="/authentication-events", tags=["api-gateway"])
app.include_router(rate_limit_events_router, prefix="/rate-limit-events", tags=["api-gateway"])
app.include_router(user_interactions_router, prefix="/user-interactions", tags=["human-interface"])
app.include_router(control_operations_router, prefix="/control-operations", tags=["human-interface"])
app.include_router(saga_executions_router, prefix="/saga-executions", tags=["integration"])
app.include_router(saga_steps_router, prefix="/saga-steps", tags=["integration"])
app.include_router(circuit_breaker_events_router, prefix="/circuit-breaker-events", tags=["integration"])
app.include_router(service_registry_events_router, prefix="/service-registry-events", tags=["integration"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    logger.info(
        "Root endpoint accessed",
        extra={'event': 'root_access'}
    )
    return {
        "service": "L01 Data Layer",
        "version": "2.0.0",
        "status": "operational"
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8001"))

    logger.info(
        f"Starting server on port {port}",
        extra={
            'event': 'server_start',
            'port': port,
        }
    )

    uvicorn.run(
        "main_with_logging:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_config=None,  # Disable uvicorn's default logging
    )

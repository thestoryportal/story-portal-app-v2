"""
L03 Tool Execution - Production Implementation

Provides tool registry, execution, and sandbox management services.
Based on tool-execution-layer-specification-v1.2-ASCII.md
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from .routes import health_router, tools_router, execution_router, tasks_router
from .observability.metrics import get_metrics, get_metrics_content_type
from .services.tool_registry import ToolRegistry
from .services.tool_sandbox import ToolSandbox
from .services.tool_executor import ToolExecutor
from .services.result_cache import ResultCache
from .services.task_manager import TaskManager

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Environment configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/agentic_platform"
)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for service initialization and cleanup.

    Initializes:
    - ToolRegistry (PostgreSQL + Ollama embeddings)
    - ToolSandbox
    - ToolExecutor
    - ResultCache (Redis)
    """
    logger.info("L03 Tool Execution starting...")

    # Initialize services
    tool_registry = None
    result_cache = None
    tool_sandbox = None
    tool_executor = None
    task_manager = None

    try:
        # Initialize tool registry (PostgreSQL + pgvector)
        tool_registry = ToolRegistry(
            db_connection_string=DATABASE_URL,
            ollama_base_url=OLLAMA_URL,
        )
        try:
            await tool_registry.initialize()
            app.state.tool_registry = tool_registry
            logger.info("Tool Registry initialized")
        except Exception as e:
            logger.warning(f"Tool Registry initialization failed: {e}")
            app.state.tool_registry = None

        # Initialize result cache (Redis)
        result_cache = ResultCache(redis_url=REDIS_URL)
        try:
            await result_cache.initialize()
            app.state.result_cache = result_cache
            logger.info("Result Cache initialized")
        except Exception as e:
            logger.warning(f"Result Cache initialization failed: {e}")
            app.state.result_cache = None

        # Initialize sandbox and executor
        tool_sandbox = ToolSandbox()
        app.state.tool_sandbox = tool_sandbox

        if tool_registry:
            tool_executor = ToolExecutor(
                tool_registry=tool_registry,
                tool_sandbox=tool_sandbox,
            )
            app.state.tool_executor = tool_executor
            logger.info("Tool Executor initialized")
        else:
            app.state.tool_executor = None
            logger.warning("Tool Executor not initialized (registry unavailable)")

        # Initialize task manager for async execution
        task_manager = TaskManager(redis_url=REDIS_URL)
        try:
            await task_manager.initialize()
            app.state.task_manager = task_manager
            logger.info("Task Manager initialized")
        except Exception as e:
            logger.warning(f"Task Manager initialization failed: {e}")
            app.state.task_manager = None

        logger.info("L03 Tool Execution started")
        yield

    finally:
        # Graceful shutdown
        logger.info("L03 Tool Execution shutting down...")

        if tool_registry:
            try:
                await tool_registry.close()
                logger.info("Tool Registry closed")
            except Exception as e:
                logger.error(f"Error closing Tool Registry: {e}")

        if result_cache:
            try:
                await result_cache.close()
                logger.info("Result Cache closed")
            except Exception as e:
                logger.error(f"Error closing Result Cache: {e}")

        if task_manager:
            try:
                await task_manager.close()
                logger.info("Task Manager closed")
            except Exception as e:
                logger.error(f"Error closing Task Manager: {e}")

        logger.info("L03 Tool Execution stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="L03 Tool Execution",
        description="Tool registry, execution, and sandbox management for autonomous agents",
        version="2.0.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health_router, tags=["health"])
    app.include_router(tools_router, prefix="/tools", tags=["tools"])
    app.include_router(execution_router, tags=["execution"])
    app.include_router(tasks_router, prefix="/tasks", tags=["tasks"])

    @app.get("/")
    async def root():
        """Root endpoint with service information."""
        return {
            "service": "L03 Tool Execution",
            "version": "2.0.0",
            "description": "Tool registry, execution, and sandbox management",
            "endpoints": {
                "health": "/health",
                "tools": "/tools",
                "invoke": "/tools/{tool_id}/invoke",
                "tasks": "/tasks",
                "metrics": "/metrics",
            },
        }

    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint."""
        return Response(
            content=get_metrics(),
            media_type=get_metrics_content_type(),
        )

    return app


# Create the app instance for uvicorn
app = create_app()

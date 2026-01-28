"""
L04 Model Gateway Layer - FastAPI Application

Main HTTP server for the Model Gateway service.
Provides LLM inference API consumed by L02 Runtime.
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .services import ModelGateway
from .providers import ClaudeCodeAdapter, OllamaAdapter, MockAdapter
from .routes import inference_router, models_router

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("L04 Model Gateway starting...")

    # Initialize providers
    providers = {}

    # Claude Code CLI adapter (primary)
    claude_path = os.getenv("CLAUDE_CLI_PATH", "claude")
    claude_timeout = int(os.getenv("CLAUDE_CLI_TIMEOUT", "300"))
    try:
        claude_adapter = ClaudeCodeAdapter(
            claude_path=claude_path,
            timeout=claude_timeout
        )
        providers["claude_code"] = claude_adapter
        logger.info(f"Claude Code adapter initialized (path={claude_path})")
    except Exception as e:
        logger.warning(f"Failed to initialize Claude Code adapter: {e}")

    # Ollama adapter (fallback for local dev)
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    try:
        ollama_adapter = OllamaAdapter(base_url=ollama_url)
        providers["ollama"] = ollama_adapter
        logger.info(f"Ollama adapter initialized (url={ollama_url})")
    except Exception as e:
        logger.warning(f"Failed to initialize Ollama adapter: {e}")

    # Mock adapter (for testing)
    providers["mock"] = MockAdapter()
    logger.info("Mock adapter initialized")

    # Initialize ModelGateway with providers
    gateway = ModelGateway(providers=providers)
    app.state.model_gateway = gateway

    logger.info(f"L04 Model Gateway started with {len(providers)} providers")

    yield

    # Shutdown
    logger.info("L04 Model Gateway shutting down...")
    if hasattr(app.state, "model_gateway") and app.state.model_gateway:
        await app.state.model_gateway.close()
    logger.info("L04 Model Gateway shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="L04 Model Gateway",
    description="LLM routing, caching, and inference service",
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
app.include_router(inference_router)
app.include_router(models_router)


# ============================================================================
# Health Check Endpoints
# ============================================================================

@app.get("/health")
async def health():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "service": "l04-model-gateway",
        "version": "2.0.0"
    }


@app.get("/health/live")
async def health_live():
    """Liveness probe for Kubernetes"""
    return {"status": "alive"}


@app.get("/health/ready")
async def health_ready():
    """Readiness probe for Kubernetes"""
    gateway = getattr(app.state, "model_gateway", None)
    if gateway:
        return {"status": "ready"}
    return {"status": "not_ready", "reason": "ModelGateway not initialized"}


@app.get("/")
async def root():
    """Root endpoint with service info"""
    gateway = getattr(app.state, "model_gateway", None)
    provider_count = len(gateway.providers) if gateway else 0
    return {
        "service": "L04 Model Gateway",
        "version": "2.0.0",
        "status": "operational",
        "providers": provider_count,
        "endpoints": {
            "inference": "/api/inference",
            "stream": "/api/inference/stream",
            "health": "/api/inference/health"
        }
    }

"""
L14 Skill Library - FastAPI Application

Provides skill management, generation, validation, and optimization
for Claude Code agents.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .services import SkillStore, SkillGenerator, SkillValidator, SkillOptimizer
from .routers import skills_router, init_services

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Service instances
skill_store: SkillStore
skill_generator: SkillGenerator
skill_validator: SkillValidator
skill_optimizer: SkillOptimizer


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global skill_store, skill_generator, skill_validator, skill_optimizer

    # Startup
    logger.info("Starting L14 Skill Library...")

    try:
        # Initialize services
        skill_store = SkillStore()
        skill_validator = SkillValidator()
        skill_optimizer = SkillOptimizer(skill_store)

        # Initialize generator with L04 gateway URL
        l04_url = os.getenv("L04_MODEL_GATEWAY_URL", "http://localhost:8004")
        default_model = os.getenv("L14_DEFAULT_MODEL", "claude-3-sonnet")
        skill_generator = SkillGenerator(
            l04_base_url=l04_url,
            default_model=default_model,
        )

        # Initialize router services
        init_services(
            skill_store=skill_store,
            skill_generator=skill_generator,
            skill_validator=skill_validator,
            skill_optimizer=skill_optimizer,
        )

        logger.info("L14 Skill Library started successfully")
        logger.info(f"L04 Model Gateway URL: {l04_url}")
        logger.info(f"Default model: {default_model}")

    except Exception as e:
        logger.error(f"Failed to start L14 Skill Library: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down L14 Skill Library...")
    logger.info("L14 Skill Library shut down")


# Create FastAPI app
app = FastAPI(
    title="L14 Skill Library",
    description="Skill management, generation, validation, and optimization for Claude Code agents",
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


# =============================================================================
# Health Endpoints
# =============================================================================

@app.get("/health", tags=["Health"])
async def health():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "l14-skill-library",
        "version": "1.0.0",
    }


@app.get("/health/live", tags=["Health"])
async def health_live():
    """Liveness probe for container orchestration."""
    return {"status": "alive"}


@app.get("/health/ready", tags=["Health"])
async def health_ready():
    """
    Readiness probe.

    Checks if all required services are initialized.
    """
    try:
        # Check if services are initialized
        if skill_store is None:
            return {"status": "not_ready", "reason": "SkillStore not initialized"}

        return {"status": "ready"}
    except Exception as e:
        return {"status": "not_ready", "reason": str(e)}


# =============================================================================
# Root Endpoint
# =============================================================================

@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "L14 Skill Library",
        "version": "1.0.0",
        "status": "operational",
        "description": "Skill management for Claude Code agents",
        "endpoints": {
            "health": "/health, /health/live, /health/ready",
            "skills": "/skills",
            "skills_crud": "/skills (POST, GET, PATCH, DELETE)",
            "skills_by_name": "/skills/by-name/{name}",
            "skills_validate": "/skills/{skill_id}/validate, /skills/validate/yaml",
            "skills_generate": "/skills/generate, /skills/generate/template/{template_name}",
            "skills_optimize": "/skills/optimize, /skills/loading-order",
            "skills_agent": "/skills/agent/{agent_id}",
            "stats": "/skills/stats/summary",
        },
        "features": [
            "Skill CRUD operations",
            "LLM-powered skill generation",
            "Schema validation",
            "Token optimization",
            "Priority-based loading",
            "Context-aware skill selection",
            "Agent skill assignment",
        ],
    }


# =============================================================================
# Include Routers
# =============================================================================

app.include_router(skills_router)


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("L14_PORT", "8014"))
    host = os.getenv("L14_HOST", "0.0.0.0")

    uvicorn.run(
        "L14_skill_library.main:app",
        host=host,
        port=port,
        reload=os.getenv("L14_RELOAD", "false").lower() == "true",
    )

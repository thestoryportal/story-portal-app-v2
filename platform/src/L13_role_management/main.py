"""
L13 Role Management Layer - FastAPI Application

Provides role-based task routing, context assembly, and human/AI classification
for the agentic platform.

Features:
- Role registration and management
- Task-to-role dispatching
- Human/AI/Hybrid classification
- Context assembly within token budgets
- Skill and keyword matching
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import roles_router
from .services import (
    RoleRegistry,
    RoleDispatcher,
    RoleContextBuilder,
    ClassificationEngine,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Service instances
role_registry: RoleRegistry = None
role_dispatcher: RoleDispatcher = None
context_builder: RoleContextBuilder = None
classification_engine: ClassificationEngine = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global role_registry, role_dispatcher, context_builder, classification_engine

    # Startup
    logger.info("Starting L13 Role Management Layer...")

    try:
        # Initialize services
        # TODO: Add database pool when L01 bridge is configured
        role_registry = RoleRegistry(
            db_pool=None,  # Will be injected when database is available
            redis_client=None,  # Will be injected when Redis is available
            use_memory_fallback=True,
        )
        await role_registry.initialize()
        logger.info("RoleRegistry initialized")

        classification_engine = ClassificationEngine(
            human_threshold=0.6,
            ai_threshold=0.6,
            default_to_hybrid=True,
        )
        logger.info("ClassificationEngine initialized")

        context_builder = RoleContextBuilder(
            project_context_provider=None,  # Optional external provider
            example_provider=None,  # Optional external provider
            default_token_budget=4000,
        )
        logger.info("RoleContextBuilder initialized")

        role_dispatcher = RoleDispatcher(
            role_registry=role_registry,
            classification_engine=classification_engine,
            context_builder=context_builder,
        )
        logger.info("RoleDispatcher initialized")

        # Seed default roles for development
        if os.getenv("L13_SEED_DEFAULT_ROLES", "true").lower() == "true":
            await _seed_default_roles(role_registry)

        logger.info("L13 Role Management Layer started successfully")

    except Exception as e:
        logger.error(f"Failed to start L13 Role Management Layer: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down L13 Role Management Layer...")
    logger.info("L13 Role Management Layer shut down")


async def _seed_default_roles(registry: RoleRegistry) -> None:
    """Seed default roles for development and testing."""
    from .models import RoleCreate, RoleType, Skill, SkillLevel

    default_roles = [
        RoleCreate(
            name="Senior Python Developer",
            department="Engineering",
            description="Experienced Python developer for backend systems and automation.",
            role_type=RoleType.AI_PRIMARY,
            skills=[
                Skill(name="Python", level=SkillLevel.EXPERT, keywords=["python", "fastapi", "django"]),
                Skill(name="API Design", level=SkillLevel.ADVANCED, keywords=["rest", "graphql", "api"]),
                Skill(name="Testing", level=SkillLevel.ADVANCED, keywords=["pytest", "testing", "tdd"]),
            ],
            responsibilities=[
                "Design and implement backend services",
                "Write clean, maintainable code",
                "Review pull requests",
            ],
            token_budget=8000,
            priority=7,
            tags=["backend", "python", "api"],
        ),
        RoleCreate(
            name="Project Manager",
            department="Management",
            description="Coordinates project activities and stakeholder communication.",
            role_type=RoleType.HUMAN_PRIMARY,
            skills=[
                Skill(name="Project Management", level=SkillLevel.EXPERT, keywords=["planning", "coordination"]),
                Skill(name="Communication", level=SkillLevel.EXPERT, keywords=["stakeholder", "presentation"]),
                Skill(name="Risk Management", level=SkillLevel.ADVANCED, keywords=["risk", "mitigation"]),
            ],
            responsibilities=[
                "Plan and track project milestones",
                "Communicate with stakeholders",
                "Manage project risks",
            ],
            token_budget=4000,
            priority=8,
            tags=["management", "planning", "communication"],
        ),
        RoleCreate(
            name="Data Analyst",
            department="Analytics",
            description="Analyzes data to extract insights and create reports.",
            role_type=RoleType.HYBRID,
            skills=[
                Skill(name="Data Analysis", level=SkillLevel.ADVANCED, keywords=["analysis", "statistics"]),
                Skill(name="SQL", level=SkillLevel.ADVANCED, keywords=["sql", "database", "query"]),
                Skill(name="Visualization", level=SkillLevel.INTERMEDIATE, keywords=["charts", "dashboards"]),
            ],
            responsibilities=[
                "Analyze datasets and identify patterns",
                "Create data visualizations and reports",
                "Support data-driven decision making",
            ],
            token_budget=6000,
            priority=6,
            tags=["data", "analytics", "reporting"],
        ),
    ]

    for role_data in default_roles:
        existing = await registry.get_role_by_name(role_data.name)
        if not existing:
            await registry.register_role(role_data)
            logger.info(f"Seeded default role: {role_data.name}")


# Create FastAPI app
app = FastAPI(
    title="L13 Role Management Layer",
    description="Role-based task routing, classification, and context assembly",
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
async def health() -> Dict[str, str]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "l13-role-management",
        "version": "1.0.0",
    }


@app.get("/health/live", tags=["Health"])
async def health_live() -> Dict[str, str]:
    """Liveness probe for monitoring and load balancers."""
    return {"status": "alive"}


@app.get("/health/ready", tags=["Health"])
async def health_ready() -> Dict[str, Any]:
    """Readiness probe checking service dependencies."""
    ready = role_registry is not None and role_dispatcher is not None

    return {
        "status": "ready" if ready else "not_ready",
        "checks": {
            "role_registry": role_registry is not None,
            "role_dispatcher": role_dispatcher is not None,
            "classification_engine": classification_engine is not None,
            "context_builder": context_builder is not None,
        },
    }


# =============================================================================
# Root Endpoint
# =============================================================================

@app.get("/", tags=["Root"])
async def root() -> Dict[str, Any]:
    """Root endpoint with service information."""
    return {
        "service": "L13 Role Management Layer",
        "version": "1.0.0",
        "status": "operational",
        "description": "Role-based task routing and context assembly",
        "endpoints": {
            "health": "/health, /health/live, /health/ready",
            "roles": "/roles (CRUD, search, dispatch)",
            "dispatch": "/roles/dispatch",
            "classify": "/roles/classify",
            "context": "/roles/{role_id}/context",
            "statistics": "/roles/statistics, /roles/dispatch/statistics",
        },
        "features": [
            "Role registration and management",
            "Task-to-role dispatching",
            "Human/AI/Hybrid classification",
            "Token-budgeted context assembly",
            "Skill and keyword matching",
        ],
    }


# Register routers
app.include_router(roles_router)


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("L13_PORT", "8013"))
    host = os.getenv("L13_HOST", "0.0.0.0")

    uvicorn.run(app, host=host, port=port)

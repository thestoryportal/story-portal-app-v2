"""
L13 Role Management Layer - Role-based task routing and context assembly.

This layer provides intelligent role management for the agentic platform,
including:

- Role registration and lifecycle management
- Task-to-role dispatching with skill matching
- Human/AI/Hybrid classification for routing decisions
- Token-budgeted context assembly for prompts

Features:
- Skill-based role matching with weighted scoring
- Keyword analysis for classification
- Configurable human/AI thresholds
- Project context integration
- Example retrieval for behavioral guidance

Usage:
    from L13_role_management import (
        Role, RoleCreate, RoleRegistry,
        RoleDispatcher, ClassificationEngine,
        RoleContextBuilder, TaskRequirements,
    )

    # Create registry and dispatcher
    registry = RoleRegistry()
    await registry.initialize()

    dispatcher = RoleDispatcher(
        role_registry=registry,
        classification_engine=ClassificationEngine(),
        context_builder=RoleContextBuilder(),
    )

    # Dispatch a task
    result = await dispatcher.dispatch_task(
        task_id="task-123",
        requirements=TaskRequirements(
            task_description="Implement a REST API endpoint",
            required_skills=["Python", "FastAPI"],
            keywords=["api", "backend"],
        ),
    )
"""

__version__ = "1.0.0"

from .models import (
    # Enums
    RoleType,
    RoleStatus,
    SkillLevel,
    # Core Models
    Skill,
    RoleDefinition,
    RoleCreate,
    RoleUpdate,
    Role,
    # Matching & Dispatch
    RoleMatch,
    TaskRequirements,
    RoleContext,
    ClassificationResult,
    DispatchResult,
)

from .services import (
    RoleRegistry,
    RoleDispatcher,
    RoleContextBuilder,
    ClassificationEngine,
)

from .routers import roles_router

__all__ = [
    # Version
    "__version__",
    # Enums
    "RoleType",
    "RoleStatus",
    "SkillLevel",
    # Core Models
    "Skill",
    "RoleDefinition",
    "RoleCreate",
    "RoleUpdate",
    "Role",
    # Matching & Dispatch
    "RoleMatch",
    "TaskRequirements",
    "RoleContext",
    "ClassificationResult",
    "DispatchResult",
    # Services
    "RoleRegistry",
    "RoleDispatcher",
    "RoleContextBuilder",
    "ClassificationEngine",
    # Routers
    "roles_router",
]

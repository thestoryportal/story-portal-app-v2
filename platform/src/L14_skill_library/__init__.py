"""
L14 Skill Library - Skill management for Claude Code agents.

This layer provides:
- Skill file schema and templates
- CRUD operations for skills
- LLM-powered skill generation from role responsibilities
- Schema validation for skill files
- Token optimization and priority-based loading
- Context-aware skill selection

Features:
- In-memory skill storage with optional L01 persistence
- Integration with L04 Model Gateway for skill generation
- Comprehensive validation with detailed issue reporting
- Multiple optimization strategies for efficient context usage
"""

__version__ = "1.0.0"

from .models import (
    # Schema and Template
    SKILL_FILE_SCHEMA,
    SKILL_FILE_TEMPLATE,
    # Enums
    SkillStatus,
    SkillPriority,
    SkillCategory,
    ValidationSeverity,
    OptimizationStrategy,
    # Skill Definition Components
    SkillMetadata,
    SkillRole,
    SkillResponsibilities,
    SkillTools,
    SkillProcedure,
    SkillExample,
    SkillConstraints,
    SkillDependencies,
    SkillDefinition,
    # CRUD Models
    SkillCreate,
    SkillUpdate,
    Skill,
    # Validation Models
    ValidationIssue,
    SkillValidationResult,
    # Generation Models
    SkillGenerationRequest,
    SkillGenerationResponse,
    # Optimization Models
    SkillOptimizationRequest,
    SkillOptimizationResult,
)

from .services import (
    SkillStore,
    SkillGenerator,
    SkillValidator,
    SkillOptimizer,
)

from .routers import (
    skills_router,
    init_services,
)

__all__ = [
    # Version
    "__version__",
    # Schema and Template
    "SKILL_FILE_SCHEMA",
    "SKILL_FILE_TEMPLATE",
    # Enums
    "SkillStatus",
    "SkillPriority",
    "SkillCategory",
    "ValidationSeverity",
    "OptimizationStrategy",
    # Skill Definition Components
    "SkillMetadata",
    "SkillRole",
    "SkillResponsibilities",
    "SkillTools",
    "SkillProcedure",
    "SkillExample",
    "SkillConstraints",
    "SkillDependencies",
    "SkillDefinition",
    # CRUD Models
    "SkillCreate",
    "SkillUpdate",
    "Skill",
    # Validation Models
    "ValidationIssue",
    "SkillValidationResult",
    # Generation Models
    "SkillGenerationRequest",
    "SkillGenerationResponse",
    # Optimization Models
    "SkillOptimizationRequest",
    "SkillOptimizationResult",
    # Services
    "SkillStore",
    "SkillGenerator",
    "SkillValidator",
    "SkillOptimizer",
    # Routers
    "skills_router",
    "init_services",
]

"""
Role models for L13 Role Management Layer.

Defines the core data structures for role-based task routing and context building.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum


class RoleType(str, Enum):
    """Classification of role types based on human/AI involvement."""
    HUMAN_PRIMARY = "human_primary"  # Human does the work, AI assists
    HYBRID = "hybrid"  # Collaborative human-AI execution
    AI_PRIMARY = "ai_primary"  # AI does the work, human supervises


class RoleStatus(str, Enum):
    """Role status enum."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    PENDING_APPROVAL = "pending_approval"


class SkillLevel(str, Enum):
    """Skill proficiency levels."""
    NOVICE = "novice"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class Skill(BaseModel):
    """A skill that a role possesses."""
    name: str = Field(..., description="Skill name")
    level: SkillLevel = Field(default=SkillLevel.INTERMEDIATE, description="Proficiency level")
    description: Optional[str] = Field(None, description="Skill description")
    keywords: List[str] = Field(default_factory=list, description="Keywords for matching")
    weight: float = Field(default=1.0, ge=0.0, le=10.0, description="Importance weight for matching")


class RoleDefinition(BaseModel):
    """
    Definition of a role including its capabilities and constraints.

    This defines what a role can do, what skills it requires, and how it
    should be classified for human/AI routing decisions.
    """
    name: str = Field(..., description="Role name (e.g., 'Senior Python Developer')")
    department: str = Field(..., description="Department or team (e.g., 'Engineering')")
    description: str = Field(..., description="Full description of the role")
    role_type: RoleType = Field(default=RoleType.HYBRID, description="Human/AI classification")
    skills: List[Skill] = Field(default_factory=list, description="Required skills")
    responsibilities: List[str] = Field(default_factory=list, description="Key responsibilities")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Role constraints")
    token_budget: int = Field(default=4000, ge=100, le=128000, description="Token budget for context")
    priority: int = Field(default=5, ge=1, le=10, description="Role priority (1=lowest, 10=highest)")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class RoleCreate(BaseModel):
    """Role creation request."""
    name: str = Field(..., description="Role name")
    department: str = Field(..., description="Department or team")
    description: str = Field(..., description="Role description")
    role_type: RoleType = Field(default=RoleType.HYBRID, description="Human/AI classification")
    skills: List[Skill] = Field(default_factory=list, description="Required skills")
    responsibilities: List[str] = Field(default_factory=list, description="Key responsibilities")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Role constraints")
    token_budget: int = Field(default=4000, ge=100, le=128000, description="Token budget")
    priority: int = Field(default=5, ge=1, le=10, description="Role priority")
    tags: List[str] = Field(default_factory=list, description="Tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")


class RoleUpdate(BaseModel):
    """Role update request."""
    name: Optional[str] = None
    department: Optional[str] = None
    description: Optional[str] = None
    role_type: Optional[RoleType] = None
    status: Optional[RoleStatus] = None
    skills: Optional[List[Skill]] = None
    responsibilities: Optional[List[str]] = None
    constraints: Optional[Dict[str, Any]] = None
    token_budget: Optional[int] = Field(None, ge=100, le=128000)
    priority: Optional[int] = Field(None, ge=1, le=10)
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class Role(BaseModel):
    """
    Complete role model with all fields.

    Represents a registered role in the system with full tracking.
    """
    id: UUID = Field(default_factory=uuid4, description="Role ID")
    name: str = Field(..., description="Role name")
    department: str = Field(..., description="Department or team")
    description: str = Field(..., description="Role description")
    role_type: RoleType = Field(default=RoleType.HYBRID, description="Human/AI classification")
    status: RoleStatus = Field(default=RoleStatus.ACTIVE, description="Role status")
    skills: List[Skill] = Field(default_factory=list, description="Required skills")
    responsibilities: List[str] = Field(default_factory=list, description="Key responsibilities")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Role constraints")
    token_budget: int = Field(default=4000, ge=100, le=128000, description="Token budget")
    priority: int = Field(default=5, ge=1, le=10, description="Role priority")
    tags: List[str] = Field(default_factory=list, description="Tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class RoleMatch(BaseModel):
    """
    Result of matching a task to potential roles.

    Includes the matched role and scoring information for selection.
    """
    role: Role = Field(..., description="The matched role")
    score: float = Field(..., ge=0.0, le=1.0, description="Match score (0-1)")
    matching_skills: List[str] = Field(default_factory=list, description="Skills that matched")
    matching_keywords: List[str] = Field(default_factory=list, description="Keywords that matched")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence in match")
    reasoning: str = Field(default="", description="Explanation of match")


class TaskRequirements(BaseModel):
    """
    Requirements extracted from a task for role matching.
    """
    task_description: str = Field(..., description="Description of the task")
    required_skills: List[str] = Field(default_factory=list, description="Skills needed")
    keywords: List[str] = Field(default_factory=list, description="Task keywords")
    complexity: str = Field(default="medium", description="Task complexity")
    urgency: str = Field(default="normal", description="Task urgency")
    department_hint: Optional[str] = Field(None, description="Suggested department")
    role_type_preference: Optional[RoleType] = Field(None, description="Preferred role type")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class RoleContext(BaseModel):
    """
    Assembled context for a role including skills, project context, and constraints.

    This is the complete context package that gets injected into prompts
    or provided to agents for task execution.
    """
    role: Role = Field(..., description="The role this context is for")
    system_prompt: str = Field(default="", description="Assembled system prompt")
    skill_context: str = Field(default="", description="Context about role skills")
    project_context: str = Field(default="", description="Relevant project context")
    constraints_context: str = Field(default="", description="Role constraints as context")
    examples: List[str] = Field(default_factory=list, description="Example behaviors/outputs")
    token_count: int = Field(default=0, ge=0, description="Total tokens in context")
    token_budget: int = Field(default=4000, ge=100, le=128000, description="Token budget")
    budget_utilization: float = Field(default=0.0, ge=0.0, le=1.0, description="Budget utilization")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Context metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class ClassificationResult(BaseModel):
    """
    Result of classifying a task for human/AI routing.
    """
    task_id: Optional[str] = Field(None, description="Task identifier")
    classification: RoleType = Field(..., description="Recommended classification")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence")
    reasoning: str = Field(default="", description="Explanation of classification")
    factors: Dict[str, float] = Field(default_factory=dict, description="Contributing factors")
    recommended_roles: List[RoleMatch] = Field(default_factory=list, description="Recommended roles")
    human_oversight_required: bool = Field(default=False, description="Whether human oversight needed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Classification metadata")


class DispatchResult(BaseModel):
    """
    Result of dispatching a task to a role.
    """
    task_id: str = Field(..., description="Task identifier")
    assigned_role: Role = Field(..., description="Role assigned to task")
    classification: ClassificationResult = Field(..., description="Classification details")
    context: RoleContext = Field(..., description="Assembled context")
    dispatch_time: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Dispatch metadata")

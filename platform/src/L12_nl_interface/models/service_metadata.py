"""Service metadata models for L12 Natural Language Interface.

This module defines the core data models for service metadata, including:
- ServiceMetadata: Complete metadata for a platform service
- MethodMetadata: Metadata for a service method
- ParameterMetadata: Metadata for a method parameter

These models are used by the ServiceRegistry to catalog all 60+ platform services
and enable both exact and fuzzy matching for natural language queries.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class ParameterType(str, Enum):
    """Supported parameter types for service methods."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DICT = "dict"
    LIST = "list"
    OBJECT = "object"  # Custom object/class
    ANY = "any"  # Any type


class ParameterMetadata(BaseModel):
    """Metadata for a service method parameter.

    Attributes:
        name: Parameter name as it appears in method signature
        type: Parameter type (str, int, bool, custom object, etc.)
        required: Whether parameter is required or optional
        description: Human-readable description of parameter purpose
        default: Default value if parameter is optional
        constraints: Optional validation constraints (e.g., min/max for int)

    Example:
        >>> param = ParameterMetadata(
        ...     name="goal",
        ...     type="Goal",
        ...     required=True,
        ...     description="Goal object to decompose"
        ... )
    """

    name: str = Field(..., description="Parameter name", min_length=1)
    type: str = Field(..., description="Parameter type", min_length=1)
    required: bool = Field(default=True, description="Whether parameter is required")
    description: str = Field(..., description="Parameter description", min_length=1)
    default: Optional[Any] = Field(default=None, description="Default value if optional")
    constraints: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Validation constraints (min, max, pattern, etc.)"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure parameter name is valid Python identifier."""
        if not v.isidentifier():
            raise ValueError(f"Parameter name '{v}' is not a valid Python identifier")
        return v

    @field_validator("constraints")
    @classmethod
    def validate_constraints(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Ensure constraints dict has valid keys."""
        if v is not None:
            valid_keys = {"min", "max", "pattern", "min_length", "max_length", "choices"}
            invalid = set(v.keys()) - valid_keys
            if invalid:
                raise ValueError(f"Invalid constraint keys: {invalid}")
        return v

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "name": "goal",
                "type": "Goal",
                "required": True,
                "description": "Goal object to decompose into tasks"
            }
        }


class MethodMetadata(BaseModel):
    """Metadata for a service method.

    Attributes:
        name: Method name as it appears in service class
        description: Human-readable description of what method does
        parameters: List of parameter metadata
        returns: Return type description
        async_method: Whether method is async (awaitable)
        examples: Optional usage examples

    Example:
        >>> method = MethodMetadata(
        ...     name="create_plan",
        ...     description="Create execution plan from goal",
        ...     parameters=[param],
        ...     returns="ExecutionPlan",
        ...     async_method=True
        ... )
    """

    name: str = Field(..., description="Method name", min_length=1)
    description: str = Field(..., description="Method description", min_length=1)
    parameters: List[ParameterMetadata] = Field(
        default_factory=list,
        description="Method parameters"
    )
    returns: str = Field(..., description="Return type", min_length=1)
    async_method: bool = Field(default=False, description="Whether method is async")
    examples: Optional[List[str]] = Field(
        default=None,
        description="Usage examples"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure method name is valid Python identifier."""
        if not v.isidentifier():
            raise ValueError(f"Method name '{v}' is not a valid Python identifier")
        if v.startswith("_"):
            raise ValueError(f"Private method '{v}' cannot be exposed via L12")
        return v

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "name": "create_plan",
                "description": "Create execution plan from goal",
                "parameters": [],
                "returns": "ExecutionPlan",
                "async_method": True
            }
        }


class ServiceMetadata(BaseModel):
    """Complete metadata for a platform service.

    This class represents all information needed to discover, instantiate,
    and invoke a platform service via the L12 Natural Language Interface.

    Attributes:
        service_name: Unique service name (e.g., "PlanningService")
        layer: Platform layer (L01-L11)
        module_path: Python module path for import
        class_name: Class name within module
        description: Human-readable service description
        keywords: Keywords for fuzzy matching (minimum 3)
        dependencies: List of other services this service depends on
        requires_async_init: Whether service has async initialize() method
        methods: List of public methods exposed via L12
        aliases: Optional alternative names for this service
        category: Optional service category (orchestrator, manager, executor, etc.)

    Example:
        >>> service = ServiceMetadata(
        ...     service_name="PlanningService",
        ...     layer="L05",
        ...     module_path="L05_planning.services.planning_service",
        ...     class_name="PlanningService",
        ...     description="Strategic planning coordinator",
        ...     keywords=["plan", "planning", "goal", "decompose"],
        ...     dependencies=["GoalDecomposer", "ModelGateway"],
        ...     requires_async_init=True,
        ...     methods=[method]
        ... )
    """

    service_name: str = Field(..., description="Unique service name", min_length=1)
    layer: str = Field(..., description="Platform layer (L00-L14)", pattern=r"^L(0[0-9]|1[0-4])$")
    module_path: str = Field(..., description="Python module path", min_length=1)
    class_name: str = Field(..., description="Class name", min_length=1)
    description: str = Field(..., description="Service description", min_length=10)
    keywords: List[str] = Field(..., description="Keywords for fuzzy matching", min_length=3)
    dependencies: List[str] = Field(
        default_factory=list,
        description="Service dependencies"
    )
    requires_async_init: bool = Field(
        default=False,
        description="Has async initialize() method"
    )
    methods: List[MethodMetadata] = Field(
        default_factory=list,
        description="Public methods"
    )
    aliases: Optional[List[str]] = Field(
        default=None,
        description="Alternative service names"
    )
    category: Optional[str] = Field(
        default=None,
        description="Service category"
    )

    @field_validator("service_name", "class_name")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        """Ensure names are valid Python identifiers."""
        if not v.isidentifier():
            raise ValueError(f"'{v}' is not a valid Python identifier")
        return v

    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, v: List[str]) -> List[str]:
        """Ensure at least 3 keywords provided."""
        if len(v) < 3:
            raise ValueError("At least 3 keywords required for fuzzy matching")
        # Normalize to lowercase for case-insensitive matching
        return [keyword.lower() for keyword in v]

    @field_validator("layer")
    @classmethod
    def validate_layer(cls, v: str) -> str:
        """Ensure layer is valid (L00-L14)."""
        valid_layers = [f"L{str(i).zfill(2)}" for i in range(0, 15)]
        if v not in valid_layers:
            raise ValueError(f"Layer must be one of {valid_layers}")
        return v

    @field_validator("module_path")
    @classmethod
    def validate_module_path(cls, v: str) -> str:
        """Ensure module path looks reasonable."""
        if not all(part.isidentifier() for part in v.split(".")):
            raise ValueError(f"Invalid module path: {v}")
        return v

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "service_name": "PlanningService",
                "layer": "L05",
                "module_path": "L05_planning.services.planning_service",
                "class_name": "PlanningService",
                "description": "Strategic planning coordinator for goal decomposition",
                "keywords": ["plan", "planning", "goal", "decompose", "strategy"],
                "dependencies": ["GoalDecomposer", "ModelGateway"],
                "requires_async_init": True,
                "methods": []
            }
        }


class ServiceMatch(BaseModel):
    """Result of fuzzy service matching.

    Represents a potential service match with similarity score.
    Used by FuzzyMatcher to return ranked results.

    Attributes:
        service: The matched service metadata
        score: Similarity score (0.0-1.0, higher is better)
        match_reason: Explanation of why service matched

    Example:
        >>> match = ServiceMatch(
        ...     service=service_metadata,
        ...     score=0.95,
        ...     match_reason="Keyword 'plan' matched in service keywords"
        ... )
    """

    service: ServiceMetadata = Field(..., description="Matched service metadata")
    score: float = Field(..., description="Similarity score (0.0-1.0)", ge=0.0, le=1.0)
    match_reason: str = Field(..., description="Why service matched", min_length=1)

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "service": {
                    "service_name": "PlanningService",
                    "layer": "L05",
                    "score": 0.95,
                    "match_reason": "Keyword 'plan' matched"
                }
            }
        }

"""L01 Data Layer - Training Example Models

Models for storing training examples extracted from execution traces.
Supports L07 Learning Layer integration.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum


class ExampleSource(str, Enum):
    """Source type for training examples."""
    EXECUTION_TRACE = "execution_trace"
    PLANNING_TRACE = "planning_trace"
    QUALITY_FEEDBACK = "quality_feedback"
    SYNTHETIC = "synthetic"
    HUMAN_ANNOTATED = "human_annotated"


class TaskType(str, Enum):
    """Task complexity classification."""
    SINGLE_STEP = "single_step"
    MULTI_STEP = "multi_step"
    REASONING = "reasoning"
    PLANNING = "planning"
    CODE_GENERATION = "code_generation"


class TrainingExampleCreate(BaseModel):
    """Training example creation request."""

    # Identifiers
    execution_id: Optional[str] = None
    task_id: Optional[str] = None
    agent_id: Optional[UUID] = None

    # Source metadata
    source_type: ExampleSource = ExampleSource.EXECUTION_TRACE
    source_trace_hash: Optional[str] = None

    # Input portion
    input_text: str = Field(..., min_length=1, description="Input text for the model")
    input_structured: Dict[str, Any] = Field(default_factory=dict, description="Structured input data")

    # Output portion
    output_text: str = Field(default="", description="Expected output text")
    expected_actions: List[Dict[str, Any]] = Field(default_factory=list, description="Expected action sequence")
    final_answer: str = Field(default="", description="Final answer from execution")

    # Quality signals from L06
    quality_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Quality score 0-100")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score 0-1")

    # Classification
    labels: List[str] = Field(default_factory=list, description="Classification labels")
    domain: str = Field(default="general", description="Task domain")
    task_type: TaskType = TaskType.SINGLE_STEP

    # Computed metadata
    difficulty: float = Field(default=0.5, ge=0.0, le=1.0, description="Difficulty score 0-1")

    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    extracted_by: str = Field(default="L07 TrainingDataExtractor", description="Extraction source")


class TrainingExampleUpdate(BaseModel):
    """Training example update request."""

    quality_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    labels: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class TrainingExample(BaseModel):
    """Training example stored in L01."""

    # Primary key
    id: UUID = Field(default_factory=uuid4)

    # Identifiers
    execution_id: Optional[str] = None
    task_id: Optional[str] = None
    agent_id: Optional[UUID] = None

    # Source metadata
    source_type: ExampleSource = ExampleSource.EXECUTION_TRACE
    source_trace_hash: Optional[str] = None

    # Input portion
    input_text: str
    input_structured: Dict[str, Any] = Field(default_factory=dict)

    # Output portion
    output_text: str = ""
    expected_actions: List[Dict[str, Any]] = Field(default_factory=list)
    final_answer: str = ""

    # Quality signals
    quality_score: float = 0.0
    confidence: float = 0.0

    # Classification
    labels: List[str] = Field(default_factory=list)
    domain: str = "general"
    task_type: TaskType = TaskType.SINGLE_STEP

    # Computed metadata
    difficulty: float = 0.5

    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    extracted_by: str = "L07 TrainingDataExtractor"

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }

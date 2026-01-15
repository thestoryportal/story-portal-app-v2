"""L01 Data Layer - Dataset Models

Models for managing versioned training datasets with train/val/test splits.
Supports L07 Learning Layer integration.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum


class DatasetSplit(str, Enum):
    """Dataset split types."""
    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"


class DatasetCreate(BaseModel):
    """Dataset creation request."""

    name: str = Field(..., min_length=1, max_length=255, description="Dataset name")
    version: str = Field(default="1.0.0", description="Semantic version")
    description: str = Field(default="", description="Dataset description")
    tags: List[str] = Field(default_factory=list, description="Dataset tags")

    # Split configuration
    split_ratios: Dict[str, float] = Field(
        default_factory=lambda: {"train": 0.8, "validation": 0.1, "test": 0.1},
        description="Train/val/test split ratios"
    )

    # Lineage
    source_datasets: List[str] = Field(default_factory=list, description="Parent dataset IDs")
    extraction_jobs: List[str] = Field(default_factory=list, description="Extraction job IDs")
    filter_configs: List[Dict[str, Any]] = Field(default_factory=list, description="Filter configurations")
    transformations: List[str] = Field(default_factory=list, description="Applied transformations")

    # Statistics (computed)
    statistics: Dict[str, Any] = Field(default_factory=dict, description="Dataset statistics")

    # Creator
    created_by: str = Field(default="L07 DatasetCurator", description="Creator identifier")


class DatasetUpdate(BaseModel):
    """Dataset update request."""

    description: Optional[str] = None
    tags: Optional[List[str]] = None
    statistics: Optional[Dict[str, Any]] = None


class Dataset(BaseModel):
    """Training dataset with versioning and splits."""

    # Primary key
    id: UUID = Field(default_factory=uuid4)

    # Identifiers
    name: str
    version: str = "1.0.0"

    # Metadata
    description: str = ""
    tags: List[str] = Field(default_factory=list)

    # Split configuration
    split_ratios: Dict[str, float] = Field(
        default_factory=lambda: {"train": 0.8, "validation": 0.1, "test": 0.1}
    )

    # Lineage tracking (stored as JSONB)
    lineage: Dict[str, Any] = Field(
        default_factory=lambda: {
            "source_datasets": [],
            "extraction_jobs": [],
            "filter_configs": [],
            "transformations": []
        },
        description="Dataset lineage information"
    )

    # Statistics (stored as JSONB)
    statistics: Dict[str, Any] = Field(
        default_factory=lambda: {
            "total_examples": 0,
            "train_count": 0,
            "validation_count": 0,
            "test_count": 0,
            "quality_score_mean": 0.0,
            "quality_score_std": 0.0,
            "confidence_mean": 0.0,
            "difficulty_mean": 0.0,
            "domain_distribution": {},
            "task_type_distribution": {}
        },
        description="Dataset statistics"
    )

    # Creator
    created_by: str = "L07 DatasetCurator"

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }


class DatasetExampleLink(BaseModel):
    """Link between dataset and training example with split assignment."""

    id: UUID = Field(default_factory=uuid4)
    dataset_id: UUID
    example_id: UUID
    split: DatasetSplit = DatasetSplit.TRAIN
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }

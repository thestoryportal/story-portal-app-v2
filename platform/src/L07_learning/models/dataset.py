"""L07 Learning Layer - Dataset Models."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional
import uuid


class DatasetSplit(Enum):
    """Dataset split types."""
    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"


@dataclass
class DatasetVersion:
    """Version metadata for a dataset."""

    version: str  # Semantic version (e.g., "1.0.0")
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "DatasetCurator v1.0"
    change_summary: str = ""
    parent_version: Optional[str] = None
    example_count: int = 0
    quality_threshold: float = 70.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        return data


@dataclass
class DatasetLineage:
    """Lineage tracking for datasets."""

    source_datasets: List[str] = field(default_factory=list)
    extraction_jobs: List[str] = field(default_factory=list)
    filter_configs: List[Dict[str, Any]] = field(default_factory=list)
    transformations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class DatasetStatistics:
    """Statistics for a training dataset."""

    total_examples: int = 0
    train_count: int = 0
    validation_count: int = 0
    test_count: int = 0

    quality_score_mean: float = 0.0
    quality_score_std: float = 0.0
    quality_score_min: float = 0.0
    quality_score_max: float = 0.0

    confidence_mean: float = 0.0
    confidence_std: float = 0.0

    difficulty_mean: float = 0.0
    difficulty_std: float = 0.0
    difficulty_distribution: Dict[str, int] = field(default_factory=dict)

    domain_distribution: Dict[str, int] = field(default_factory=dict)
    task_type_distribution: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert statistics to dictionary."""
        return asdict(self)


@dataclass
class Dataset:
    """Training dataset with versioning and split management.

    A dataset is a versioned collection of training examples with train/val/test
    splits. Datasets are immutable - modifications create new versions.
    """

    # Identifiers
    dataset_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    version: str = "1.0.0"

    # Examples (stored as IDs to avoid duplication)
    example_ids: List[str] = field(default_factory=list)

    # Splits (example_id -> split mapping)
    splits: Dict[str, List[str]] = field(default_factory=dict)

    # Statistics
    statistics: DatasetStatistics = field(default_factory=DatasetStatistics)

    # Metadata
    description: str = ""
    tags: List[str] = field(default_factory=list)
    lineage: DatasetLineage = field(default_factory=DatasetLineage)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "DatasetCurator v1.0"

    # Configuration
    split_ratios: Dict[str, float] = field(default_factory=lambda: {
        "train": 0.8,
        "validation": 0.1,
        "test": 0.1
    })

    def to_dict(self) -> Dict[str, Any]:
        """Convert dataset to dictionary."""
        data = asdict(self)
        data['statistics'] = self.statistics.to_dict() if self.statistics else {}
        data['lineage'] = self.lineage.to_dict() if self.lineage else {}
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Dataset':
        """Create dataset from dictionary."""
        if 'statistics' in data and isinstance(data['statistics'], dict):
            data['statistics'] = DatasetStatistics(**data['statistics'])
        if 'lineage' in data and isinstance(data['lineage'], dict):
            data['lineage'] = DatasetLineage(**data['lineage'])
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)

    def get_split_size(self, split: DatasetSplit) -> int:
        """Get number of examples in a split.

        Args:
            split: Dataset split type

        Returns:
            Number of examples in split
        """
        return len(self.splits.get(split.value, []))

    def add_example(self, example_id: str, split: Optional[DatasetSplit] = None) -> None:
        """Add example to dataset.

        Args:
            example_id: Example identifier
            split: Optional split assignment
        """
        if example_id not in self.example_ids:
            self.example_ids.append(example_id)

        if split:
            if split.value not in self.splits:
                self.splits[split.value] = []
            if example_id not in self.splits[split.value]:
                self.splits[split.value].append(example_id)

        self.updated_at = datetime.utcnow()

    def validate(self) -> bool:
        """Validate dataset integrity.

        Returns:
            True if valid, False otherwise
        """
        # Check all split examples are in example_ids
        all_split_ids = set()
        for split_ids in self.splits.values():
            all_split_ids.update(split_ids)

        if not all_split_ids.issubset(set(self.example_ids)):
            return False

        # Check split ratios sum to 1.0 (with tolerance)
        ratio_sum = sum(self.split_ratios.values())
        if abs(ratio_sum - 1.0) > 0.01:
            return False

        return True

    def compute_statistics(self, examples: List[Any]) -> DatasetStatistics:
        """Compute statistics from example list.

        Args:
            examples: List of TrainingExample objects

        Returns:
            Computed statistics
        """
        import numpy as np

        if not examples:
            return DatasetStatistics()

        quality_scores = [ex.quality_score for ex in examples]
        confidences = [ex.confidence for ex in examples]
        difficulties = [ex.difficulty for ex in examples]

        # Difficulty distribution
        difficulty_dist = {'easy': 0, 'medium': 0, 'hard': 0}
        for d in difficulties:
            if d < 0.33:
                difficulty_dist['easy'] += 1
            elif d < 0.66:
                difficulty_dist['medium'] += 1
            else:
                difficulty_dist['hard'] += 1

        # Domain distribution
        domain_dist = {}
        for ex in examples:
            domain_dist[ex.domain] = domain_dist.get(ex.domain, 0) + 1

        # Task type distribution
        task_type_dist = {}
        for ex in examples:
            task_type_str = ex.task_type.value if hasattr(ex.task_type, 'value') else str(ex.task_type)
            task_type_dist[task_type_str] = task_type_dist.get(task_type_str, 0) + 1

        stats = DatasetStatistics(
            total_examples=len(examples),
            train_count=self.get_split_size(DatasetSplit.TRAIN),
            validation_count=self.get_split_size(DatasetSplit.VALIDATION),
            test_count=self.get_split_size(DatasetSplit.TEST),
            quality_score_mean=float(np.mean(quality_scores)),
            quality_score_std=float(np.std(quality_scores)),
            quality_score_min=float(np.min(quality_scores)),
            quality_score_max=float(np.max(quality_scores)),
            confidence_mean=float(np.mean(confidences)),
            confidence_std=float(np.std(confidences)),
            difficulty_mean=float(np.mean(difficulties)),
            difficulty_std=float(np.std(difficulties)),
            difficulty_distribution=difficulty_dist,
            domain_distribution=domain_dist,
            task_type_distribution=task_type_dist
        )

        self.statistics = stats
        return stats

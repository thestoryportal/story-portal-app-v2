"""L07 Learning Layer - Curriculum Learning Models."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional
import uuid


class DifficultyLevel(Enum):
    """Difficulty level for curriculum stages."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


@dataclass
class CurriculumStage:
    """Stage in curriculum learning progression.

    Represents a phase of training with specific difficulty level and
    example selection criteria.
    """

    # Identifiers
    stage_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    stage_number: int = 1
    name: str = ""

    # Difficulty
    difficulty_level: DifficultyLevel = DifficultyLevel.EASY
    difficulty_min: float = 0.0
    difficulty_max: float = 0.33

    # Example selection
    example_count: int = 0
    quality_threshold: float = 70.0
    confidence_threshold: float = 0.7

    # Training configuration
    epochs: int = 1
    learning_rate: float = 2e-5

    # Completion criteria
    target_accuracy: float = 0.90
    min_examples: int = 100

    # Status
    completed: bool = False
    completion_time: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['difficulty_level'] = self.difficulty_level.value
        if self.completion_time:
            data['completion_time'] = self.completion_time.isoformat()
        return data


@dataclass
class LearningPath:
    """Complete curriculum learning path.

    Defines a sequence of curriculum stages for progressive learning
    from easy to hard examples.
    """

    # Identifiers
    path_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "default_curriculum"
    description: str = ""

    # Stages
    stages: List[CurriculumStage] = field(default_factory=list)
    current_stage: int = 0

    # Dataset
    dataset_id: str = ""
    total_examples: int = 0

    # Progress
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress_percent: float = 0.0

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "CurriculumPlanner v1.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['stages'] = [s.to_dict() for s in self.stages]
        data['created_at'] = self.created_at.isoformat()
        if self.started_at:
            data['started_at'] = self.started_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
        return data

    def get_current_stage(self) -> Optional[CurriculumStage]:
        """Get current curriculum stage.

        Returns:
            Current stage or None if completed
        """
        if 0 <= self.current_stage < len(self.stages):
            return self.stages[self.current_stage]
        return None

    def advance_stage(self) -> bool:
        """Advance to next curriculum stage.

        Returns:
            True if advanced, False if already at last stage
        """
        if self.current_stage < len(self.stages) - 1:
            if self.stages[self.current_stage]:
                self.stages[self.current_stage].completed = True
                self.stages[self.current_stage].completion_time = datetime.utcnow()
            self.current_stage += 1
            self.progress_percent = (self.current_stage / len(self.stages)) * 100
            return True
        return False

    def is_completed(self) -> bool:
        """Check if curriculum is completed.

        Returns:
            True if all stages completed
        """
        return self.current_stage >= len(self.stages)

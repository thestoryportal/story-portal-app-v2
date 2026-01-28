"""
L07 Learning Layer - Curriculum Service

Service for managing curriculum learning with progressive difficulty stages.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
import uuid

from ..models.curriculum import (
    CurriculumStage,
    LearningPath,
    DifficultyLevel,
)
from ..models.training_example import TrainingExample
from ..models.training_job import TrainingJob, JobType, JobConfig


logger = logging.getLogger(__name__)


# Default difficulty ranges for each level
DIFFICULTY_RANGES = {
    DifficultyLevel.EASY: (0.0, 0.33),
    DifficultyLevel.MEDIUM: (0.33, 0.66),
    DifficultyLevel.HARD: (0.66, 0.85),
    DifficultyLevel.EXPERT: (0.85, 1.0),
}

# Default stage configurations
DEFAULT_STAGE_CONFIG = {
    DifficultyLevel.EASY: {"epochs": 2, "learning_rate": 2e-5, "target_accuracy": 0.85},
    DifficultyLevel.MEDIUM: {"epochs": 3, "learning_rate": 1e-5, "target_accuracy": 0.88},
    DifficultyLevel.HARD: {"epochs": 4, "learning_rate": 5e-6, "target_accuracy": 0.90},
    DifficultyLevel.EXPERT: {"epochs": 5, "learning_rate": 2e-6, "target_accuracy": 0.92},
}


class CurriculumService:
    """
    Service for managing curriculum learning.

    Curriculum learning progressively trains on increasingly difficult examples,
    which can improve model performance and training efficiency.
    """

    def __init__(
        self,
        storage_path: str = "/tmp/l07_learning/curriculum",
    ):
        """
        Initialize CurriculumService.

        Args:
            storage_path: Path for storing curriculum data
        """
        self.storage_path = storage_path
        self._examples: List[TrainingExample] = []
        self._learning_paths: Dict[str, LearningPath] = {}
        self._training_jobs: Dict[str, TrainingJob] = {}

        logger.info(f"Initialized CurriculumService (storage={storage_path})")

    def set_examples(self, examples: List[TrainingExample]) -> None:
        """
        Set the pool of training examples for curriculum selection.

        Args:
            examples: List of training examples
        """
        self._examples = examples
        logger.info(f"Set {len(examples)} examples for curriculum learning")

    async def create_learning_path(
        self,
        name: str,
        dataset_id: str,
        num_stages: int = 4,
        description: str = "",
    ) -> LearningPath:
        """
        Create a new learning path with progressive difficulty stages.

        Args:
            name: Name for the learning path
            dataset_id: ID of the dataset to use
            num_stages: Number of curriculum stages (default 4)
            description: Optional description

        Returns:
            Created LearningPath
        """
        logger.info(f"Creating learning path '{name}' with {num_stages} stages")

        # Create stages based on difficulty levels
        stages = []
        difficulty_levels = list(DifficultyLevel)[:num_stages]

        for i, level in enumerate(difficulty_levels):
            diff_range = DIFFICULTY_RANGES[level]
            config = DEFAULT_STAGE_CONFIG.get(level, DEFAULT_STAGE_CONFIG[DifficultyLevel.EASY])

            stage = CurriculumStage(
                stage_id=str(uuid.uuid4()),
                stage_number=i,
                name=f"Stage {i + 1}: {level.value.capitalize()}",
                difficulty_level=level,
                difficulty_min=diff_range[0],
                difficulty_max=diff_range[1],
                epochs=config["epochs"],
                learning_rate=config["learning_rate"],
                target_accuracy=config["target_accuracy"],
                quality_threshold=70.0,
                confidence_threshold=0.7,
            )
            stages.append(stage)

        # Create learning path
        path = LearningPath(
            path_id=str(uuid.uuid4()),
            name=name,
            description=description,
            stages=stages,
            dataset_id=dataset_id,
            total_examples=len(self._examples),
            current_stage=0,
            progress_percent=0.0,
            created_at=datetime.utcnow(),
        )

        # Store path
        self._learning_paths[path.path_id] = path

        logger.info(f"Created learning path {path.path_id} with {num_stages} stages")

        return path

    async def get_examples_for_stage(
        self,
        path: LearningPath,
        stage_number: int,
    ) -> List[TrainingExample]:
        """
        Get training examples filtered for a specific curriculum stage.

        Args:
            path: Learning path
            stage_number: Stage number (0-indexed)

        Returns:
            List of examples matching stage difficulty criteria
        """
        if stage_number < 0 or stage_number >= len(path.stages):
            logger.warning(f"Invalid stage number: {stage_number}")
            return []

        stage = path.stages[stage_number]

        # Filter examples by difficulty range
        filtered = [
            ex for ex in self._examples
            if stage.difficulty_min <= ex.difficulty <= stage.difficulty_max
            and ex.quality_score >= stage.quality_threshold
            and ex.confidence >= stage.confidence_threshold
        ]

        logger.info(
            f"Found {len(filtered)} examples for stage {stage_number} "
            f"(difficulty {stage.difficulty_min:.2f}-{stage.difficulty_max:.2f})"
        )

        return filtered

    async def advance_stage(self, path: LearningPath) -> bool:
        """
        Advance to the next curriculum stage.

        Args:
            path: Learning path to advance

        Returns:
            True if advanced, False if already at last stage
        """
        if path.is_completed():
            logger.info(f"Learning path {path.path_id} is already completed")
            return False

        # Mark current stage as completed
        if path.current_stage < len(path.stages):
            path.stages[path.current_stage].completed = True
            path.stages[path.current_stage].completion_time = datetime.utcnow()

        # Advance to next stage
        advanced = path.advance_stage()

        if advanced:
            logger.info(
                f"Advanced learning path {path.path_id} to stage {path.current_stage} "
                f"(progress: {path.progress_percent:.1f}%)"
            )
        else:
            path.completed_at = datetime.utcnow()
            path.progress_percent = 100.0
            logger.info(f"Learning path {path.path_id} completed")

        return advanced

    async def complete_stage(
        self,
        path: LearningPath,
        stage_number: int,
        metrics: Dict[str, Any],
    ) -> bool:
        """
        Mark a stage as completed with metrics.

        Args:
            path: Learning path
            stage_number: Stage number to complete
            metrics: Training metrics for the stage

        Returns:
            True if completed successfully
        """
        if stage_number < 0 or stage_number >= len(path.stages):
            logger.warning(f"Invalid stage number: {stage_number}")
            return False

        stage = path.stages[stage_number]

        # Mark completed
        stage.completed = True
        stage.completion_time = datetime.utcnow()

        # Check if accuracy meets target
        accuracy = metrics.get("accuracy", 0.0)
        if accuracy < stage.target_accuracy:
            logger.warning(
                f"Stage {stage_number} accuracy {accuracy:.3f} below target {stage.target_accuracy:.3f}"
            )

        logger.info(f"Completed stage {stage_number} of path {path.path_id}")

        return True

    async def run_stage(
        self,
        path: LearningPath,
        stage_number: int,
        base_model_id: str = "gpt2",
    ) -> TrainingJob:
        """
        Create and start a training job for a curriculum stage.

        Args:
            path: Learning path
            stage_number: Stage number to run
            base_model_id: Base model to fine-tune

        Returns:
            Created TrainingJob
        """
        if stage_number < 0 or stage_number >= len(path.stages):
            raise ValueError(f"Invalid stage number: {stage_number}")

        stage = path.stages[stage_number]

        # Create job configuration from stage
        config = JobConfig(
            base_model_id=base_model_id,
            num_epochs=stage.epochs,
            learning_rate=stage.learning_rate,
        )

        # Create training job
        job = TrainingJob(
            job_id=str(uuid.uuid4()),
            job_name=f"{path.name}-stage-{stage_number}",
            job_type=JobType.CURRICULUM,
            dataset_id=path.dataset_id,
            base_model_id=base_model_id,
            config=config,
        )

        # Store job
        self._training_jobs[job.job_id] = job

        # Mark path as started if not already
        if not path.started_at:
            path.started_at = datetime.utcnow()

        logger.info(
            f"Created training job {job.job_id} for stage {stage_number} "
            f"(epochs={stage.epochs}, lr={stage.learning_rate})"
        )

        return job

    async def get_curriculum_stats(self, path: LearningPath) -> Dict[str, Any]:
        """
        Get statistics for a curriculum learning path.

        Args:
            path: Learning path

        Returns:
            Dictionary of statistics
        """
        # Count examples per stage
        stage_stats = []
        for i, stage in enumerate(path.stages):
            examples = await self.get_examples_for_stage(path, i)
            stage_stats.append({
                "stage_number": i,
                "name": stage.name,
                "difficulty_level": stage.difficulty_level.value,
                "example_count": len(examples),
                "completed": stage.completed,
                "target_accuracy": stage.target_accuracy,
            })

        completed_count = sum(1 for s in path.stages if s.completed)

        return {
            "path_id": path.path_id,
            "name": path.name,
            "dataset_id": path.dataset_id,
            "total_examples": len(self._examples),
            "stages": stage_stats,
            "current_stage": path.current_stage,
            "completed_stages": completed_count,
            "total_stages": len(path.stages),
            "progress_percent": path.progress_percent,
            "is_completed": path.is_completed(),
        }

    async def list_learning_paths(self) -> List[LearningPath]:
        """
        List all learning paths.

        Returns:
            List of learning paths
        """
        return list(self._learning_paths.values())

    async def get_learning_path(self, path_id: str) -> Optional[LearningPath]:
        """
        Get a learning path by ID.

        Args:
            path_id: Path identifier

        Returns:
            LearningPath or None if not found
        """
        return self._learning_paths.get(path_id)

    async def delete_learning_path(self, path_id: str) -> bool:
        """
        Delete a learning path.

        Args:
            path_id: Path identifier

        Returns:
            True if deleted, False if not found
        """
        if path_id in self._learning_paths:
            del self._learning_paths[path_id]
            logger.info(f"Deleted learning path {path_id}")
            return True
        return False

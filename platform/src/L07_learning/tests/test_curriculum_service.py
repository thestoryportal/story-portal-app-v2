"""
L07 Learning Layer - Curriculum Service Tests

Tests for CurriculumService (TDD - tests written first).
"""

import pytest
from datetime import datetime
from typing import List
import uuid

from L07_learning.models.curriculum import (
    CurriculumStage,
    LearningPath,
    DifficultyLevel,
)
from L07_learning.models.training_example import TrainingExample, ExampleSource, TaskType


@pytest.fixture
def sample_examples() -> List[TrainingExample]:
    """Generate sample training examples with varying difficulty."""
    examples = []
    for i in range(100):
        # Distribute difficulty: 30 easy, 30 medium, 25 hard, 15 expert
        if i < 30:
            difficulty = 0.1 + (i % 10) * 0.02  # 0.1 - 0.28
            quality = 85 + (i % 10)
        elif i < 60:
            difficulty = 0.35 + ((i - 30) % 10) * 0.02  # 0.35 - 0.53
            quality = 80 + ((i - 30) % 10)
        elif i < 85:
            difficulty = 0.67 + ((i - 60) % 10) * 0.01  # 0.67 - 0.76
            quality = 75 + ((i - 60) % 10)
        else:
            difficulty = 0.85 + ((i - 85) % 10) * 0.01  # 0.85 - 0.94
            quality = 70 + ((i - 85) % 5)

        examples.append(
            TrainingExample(
                example_id=f"ex-{i:03d}",
                execution_id=f"exec-{i:03d}",
                task_id=f"task-{i:03d}",
                source_type=ExampleSource.EXECUTION_TRACE,
                input_text=f"Input text {i}",
                output_text=f"Output text {i}",
                quality_score=quality,
                confidence=0.8,
                difficulty=difficulty,
                domain="general",
                task_type=TaskType.SINGLE_STEP,
            )
        )
    return examples


@pytest.mark.l07
@pytest.mark.unit
class TestCurriculumServiceCreation:
    """Tests for curriculum creation."""

    @pytest.mark.asyncio
    async def test_create_learning_path_with_4_stages(self, sample_examples):
        """Test creating a learning path with 4 stages."""
        from L07_learning.services.curriculum_service import CurriculumService

        service = CurriculumService()

        path = await service.create_learning_path(
            name="test-curriculum",
            dataset_id="ds-001",
            num_stages=4,
        )

        assert path is not None
        assert path.name == "test-curriculum"
        assert len(path.stages) == 4
        assert path.current_stage == 0
        assert path.progress_percent == 0.0

    @pytest.mark.asyncio
    async def test_stages_have_increasing_difficulty(self, sample_examples):
        """Test that stages have increasing difficulty ranges."""
        from L07_learning.services.curriculum_service import CurriculumService

        service = CurriculumService()

        path = await service.create_learning_path(
            name="difficulty-test",
            dataset_id="ds-001",
            num_stages=4,
        )

        # Verify difficulty progression
        prev_max = 0.0
        for stage in path.stages:
            assert stage.difficulty_min >= prev_max
            assert stage.difficulty_max > stage.difficulty_min
            prev_max = stage.difficulty_max

    @pytest.mark.asyncio
    async def test_stages_have_correct_difficulty_levels(self, sample_examples):
        """Test that stages have correct DifficultyLevel enum values."""
        from L07_learning.services.curriculum_service import CurriculumService

        service = CurriculumService()

        path = await service.create_learning_path(
            name="level-test",
            dataset_id="ds-001",
            num_stages=4,
        )

        expected_levels = [
            DifficultyLevel.EASY,
            DifficultyLevel.MEDIUM,
            DifficultyLevel.HARD,
            DifficultyLevel.EXPERT,
        ]

        for i, stage in enumerate(path.stages):
            assert stage.difficulty_level == expected_levels[i]


@pytest.mark.l07
@pytest.mark.unit
class TestExampleFiltering:
    """Tests for example filtering by difficulty."""

    @pytest.mark.asyncio
    async def test_get_examples_filtered_by_difficulty(self, sample_examples):
        """Test getting examples for a specific stage."""
        from L07_learning.services.curriculum_service import CurriculumService

        service = CurriculumService()
        service.set_examples(sample_examples)

        path = await service.create_learning_path(
            name="filter-test",
            dataset_id="ds-001",
            num_stages=4,
        )

        # Get examples for first (easy) stage
        easy_examples = await service.get_examples_for_stage(path, stage_number=0)

        assert len(easy_examples) > 0
        # All examples should have difficulty within easy range
        for ex in easy_examples:
            assert ex.difficulty <= path.stages[0].difficulty_max

    @pytest.mark.asyncio
    async def test_get_examples_returns_empty_for_invalid_stage(self, sample_examples):
        """Test that invalid stage number returns empty list."""
        from L07_learning.services.curriculum_service import CurriculumService

        service = CurriculumService()
        service.set_examples(sample_examples)

        path = await service.create_learning_path(
            name="invalid-stage-test",
            dataset_id="ds-001",
            num_stages=4,
        )

        # Invalid stage number
        examples = await service.get_examples_for_stage(path, stage_number=10)
        assert examples == []


@pytest.mark.l07
@pytest.mark.unit
class TestStageProgression:
    """Tests for stage progression."""

    @pytest.mark.asyncio
    async def test_advance_stage_updates_progress(self, sample_examples):
        """Test that advancing stage updates progress percentage."""
        from L07_learning.services.curriculum_service import CurriculumService

        service = CurriculumService()
        service.set_examples(sample_examples)

        path = await service.create_learning_path(
            name="progress-test",
            dataset_id="ds-001",
            num_stages=4,
        )

        # Initial state
        assert path.current_stage == 0
        assert path.progress_percent == 0.0

        # Advance to stage 1
        advanced = await service.advance_stage(path)
        assert advanced is True
        assert path.current_stage == 1
        assert path.progress_percent == 25.0

        # Advance to stage 2
        advanced = await service.advance_stage(path)
        assert advanced is True
        assert path.current_stage == 2
        assert path.progress_percent == 50.0

    @pytest.mark.asyncio
    async def test_complete_stage_marks_completed(self, sample_examples):
        """Test that completing a stage marks it as completed."""
        from L07_learning.services.curriculum_service import CurriculumService

        service = CurriculumService()
        service.set_examples(sample_examples)

        path = await service.create_learning_path(
            name="complete-test",
            dataset_id="ds-001",
            num_stages=4,
        )

        # Complete first stage with metrics
        metrics = {
            "accuracy": 0.95,
            "loss": 0.1,
        }

        completed = await service.complete_stage(
            path=path,
            stage_number=0,
            metrics=metrics,
        )

        assert completed is True
        assert path.stages[0].completed is True
        assert path.stages[0].completion_time is not None

    @pytest.mark.asyncio
    async def test_cannot_advance_past_last_stage(self, sample_examples):
        """Test that cannot advance past the last stage."""
        from L07_learning.services.curriculum_service import CurriculumService

        service = CurriculumService()

        path = await service.create_learning_path(
            name="last-stage-test",
            dataset_id="ds-001",
            num_stages=2,
        )

        # Advance through all stages
        await service.advance_stage(path)  # To stage 1
        await service.advance_stage(path)  # Completes path

        # Try to advance past last stage
        advanced = await service.advance_stage(path)
        assert advanced is False
        # Path should be marked complete with 100% progress
        assert path.progress_percent == 100.0
        assert path.completed_at is not None


@pytest.mark.l07
@pytest.mark.unit
class TestTrainingJobCreation:
    """Tests for training job creation from curriculum."""

    @pytest.mark.asyncio
    async def test_run_stage_creates_training_job(self, sample_examples):
        """Test that running a stage creates a training job."""
        from L07_learning.services.curriculum_service import CurriculumService

        service = CurriculumService()
        service.set_examples(sample_examples)

        path = await service.create_learning_path(
            name="job-test",
            dataset_id="ds-001",
            num_stages=4,
        )

        # Run first stage
        job = await service.run_stage(
            path=path,
            stage_number=0,
            base_model_id="gpt2",
        )

        assert job is not None
        assert job.dataset_id == path.dataset_id
        assert job.config.num_epochs == path.stages[0].epochs
        assert job.config.learning_rate == path.stages[0].learning_rate

    @pytest.mark.asyncio
    async def test_run_stage_uses_stage_config(self, sample_examples):
        """Test that running a stage uses stage-specific configuration."""
        from L07_learning.services.curriculum_service import CurriculumService

        service = CurriculumService()
        service.set_examples(sample_examples)

        path = await service.create_learning_path(
            name="config-test",
            dataset_id="ds-001",
            num_stages=4,
        )

        # Customize stage config
        path.stages[1].epochs = 5
        path.stages[1].learning_rate = 1e-5

        # Run stage 1 (medium difficulty)
        job = await service.run_stage(
            path=path,
            stage_number=1,
            base_model_id="gpt2",
        )

        assert job.config.num_epochs == 5
        assert job.config.learning_rate == 1e-5


@pytest.mark.l07
@pytest.mark.unit
class TestCurriculumStatistics:
    """Tests for curriculum statistics."""

    @pytest.mark.asyncio
    async def test_get_curriculum_stats(self, sample_examples):
        """Test getting curriculum statistics."""
        from L07_learning.services.curriculum_service import CurriculumService

        service = CurriculumService()
        service.set_examples(sample_examples)

        path = await service.create_learning_path(
            name="stats-test",
            dataset_id="ds-001",
            num_stages=4,
        )

        stats = await service.get_curriculum_stats(path)

        assert "stages" in stats
        assert "total_examples" in stats
        assert "completed_stages" in stats
        assert len(stats["stages"]) == 4

    @pytest.mark.asyncio
    async def test_list_learning_paths(self, sample_examples):
        """Test listing all learning paths."""
        from L07_learning.services.curriculum_service import CurriculumService

        service = CurriculumService()

        # Create multiple paths
        await service.create_learning_path(name="path-1", dataset_id="ds-001")
        await service.create_learning_path(name="path-2", dataset_id="ds-002")

        paths = await service.list_learning_paths()

        assert len(paths) >= 2
        names = [p.name for p in paths]
        assert "path-1" in names
        assert "path-2" in names

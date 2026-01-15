"""L07 Learning Layer - Autonomous continuous improvement engine.

The Learning Layer extracts training data from execution traces, manages model
fine-tuning pipelines, implements RLHF feedback loops, and enables the system
to improve autonomously based on quality signals from L06.
"""

__version__ = "1.0.0"
__layer__ = "L07"

from .models.training_example import TrainingExample, ExampleSource, ExampleLabel
from .models.dataset import Dataset, DatasetVersion, DatasetSplit
from .models.training_job import TrainingJob, JobStatus, JobConfig
from .models.model_artifact import ModelArtifact, ModelVersion, ModelLineage
from .services.learning_service import LearningService

__all__ = [
    "TrainingExample",
    "ExampleSource",
    "ExampleLabel",
    "Dataset",
    "DatasetVersion",
    "DatasetSplit",
    "TrainingJob",
    "JobStatus",
    "JobConfig",
    "ModelArtifact",
    "ModelVersion",
    "ModelLineage",
    "LearningService",
]

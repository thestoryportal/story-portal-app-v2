"""L07 Learning Layer - Training Job Models."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional
import uuid


class JobStatus(Enum):
    """Training job status."""
    PENDING = "pending"
    INITIALIZING = "initializing"
    PREPARING_DATA = "preparing_data"
    TRAINING = "training"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    QUARANTINED = "quarantined"


class JobType(Enum):
    """Type of training job."""
    SFT = "supervised_fine_tuning"
    RLHF = "reinforcement_learning_human_feedback"
    DISTILLATION = "knowledge_distillation"
    CURRICULUM = "curriculum_learning"


@dataclass
class LoRAConfig:
    """LoRA (Low-Rank Adaptation) configuration."""

    rank: int = 16
    alpha: float = 32.0
    dropout: float = 0.05
    target_modules: List[str] = field(default_factory=lambda: ["q_proj", "v_proj"])
    bias: str = "none"
    task_type: str = "CAUSAL_LM"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class JobConfig:
    """Configuration for training job."""

    # Model configuration
    base_model_id: str = "gpt-4-turbo-2024-04"
    adapter_name: Optional[str] = None

    # Training hyperparameters
    learning_rate: float = 2e-5
    batch_size: int = 16
    gradient_accumulation_steps: int = 4
    num_epochs: int = 3
    max_steps: Optional[int] = None
    warmup_ratio: float = 0.1
    weight_decay: float = 0.01
    max_grad_norm: float = 1.0

    # LoRA configuration
    lora_config: LoRAConfig = field(default_factory=LoRAConfig)

    # Data configuration
    max_seq_length: int = 2048
    shuffle: bool = True

    # Validation
    eval_strategy: str = "epoch"
    eval_steps: Optional[int] = None
    save_strategy: str = "epoch"
    save_total_limit: int = 3

    # Early stopping
    early_stopping_patience: int = 2
    early_stopping_threshold: float = 0.001
    metric_for_best_model: str = "eval_loss"

    # Optimization
    gradient_checkpointing: bool = True
    fp16: bool = True
    use_curriculum: bool = False

    # Output
    output_dir: str = "/tmp/l07_training"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['lora_config'] = self.lora_config.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobConfig':
        """Create from dictionary."""
        if 'lora_config' in data and isinstance(data['lora_config'], dict):
            data['lora_config'] = LoRAConfig(**data['lora_config'])
        return cls(**data)


@dataclass
class TrainingMetrics:
    """Metrics collected during training."""

    epoch: int = 0
    step: int = 0
    train_loss: float = 0.0
    eval_loss: Optional[float] = None
    learning_rate: float = 0.0
    grad_norm: float = 0.0
    gpu_memory_mb: float = 0.0
    gpu_utilization_percent: float = 0.0
    throughput_samples_per_second: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class ValidationMetrics:
    """Validation metrics for trained model."""

    accuracy: float = 0.0
    eval_loss: float = 0.0
    bleu_score: Optional[float] = None
    perplexity: Optional[float] = None
    f1_score: Optional[float] = None

    # Performance metrics
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0

    # Regression tests
    regression_tests_passed: int = 0
    regression_tests_failed: int = 0
    regression_tests_total: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class TrainingJob:
    """Training job with lifecycle management.

    A training job represents a complete training run from data preparation
    through model validation. Jobs track status, metrics, and artifacts.
    """

    # Identifiers
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    job_name: str = ""
    job_type: JobType = JobType.SFT

    # Status
    status: JobStatus = JobStatus.PENDING
    status_message: str = ""

    # Configuration
    config: JobConfig = field(default_factory=JobConfig)

    # Data
    dataset_id: str = ""
    dataset_version: str = "1.0.0"

    # Models
    base_model_id: str = ""
    output_model_id: Optional[str] = None

    # Metrics
    training_metrics: List[TrainingMetrics] = field(default_factory=list)
    validation_metrics: Optional[ValidationMetrics] = None
    final_loss: Optional[float] = None

    # Error handling
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # Metadata
    created_by: str = "FineTuningEngine v1.0"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['job_type'] = self.job_type.value
        data['status'] = self.status.value
        data['config'] = self.config.to_dict()
        data['training_metrics'] = [m.to_dict() for m in self.training_metrics]
        if self.validation_metrics:
            data['validation_metrics'] = self.validation_metrics.to_dict()
        data['created_at'] = self.created_at.isoformat()
        if self.started_at:
            data['started_at'] = self.started_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrainingJob':
        """Create from dictionary."""
        if 'job_type' in data and isinstance(data['job_type'], str):
            data['job_type'] = JobType(data['job_type'])
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = JobStatus(data['status'])
        if 'config' in data and isinstance(data['config'], dict):
            data['config'] = JobConfig.from_dict(data['config'])
        if 'training_metrics' in data and isinstance(data['training_metrics'], list):
            data['training_metrics'] = [
                TrainingMetrics(**m) if isinstance(m, dict) else m
                for m in data['training_metrics']
            ]
        if 'validation_metrics' in data and isinstance(data['validation_metrics'], dict):
            data['validation_metrics'] = ValidationMetrics(**data['validation_metrics'])
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'started_at' in data and isinstance(data['started_at'], str):
            data['started_at'] = datetime.fromisoformat(data['started_at'])
        if 'completed_at' in data and isinstance(data['completed_at'], str):
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)

    def update_status(self, status: JobStatus, message: str = "") -> None:
        """Update job status.

        Args:
            status: New status
            message: Optional status message
        """
        self.status = status
        self.status_message = message
        self.updated_at = datetime.utcnow()

        if status == JobStatus.TRAINING and not self.started_at:
            self.started_at = datetime.utcnow()
        elif status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            self.completed_at = datetime.utcnow()

    def add_training_metric(self, metric: TrainingMetrics) -> None:
        """Add training metric.

        Args:
            metric: Training metric to add
        """
        self.training_metrics.append(metric)
        self.updated_at = datetime.utcnow()

    def get_duration_seconds(self) -> Optional[float]:
        """Get job duration in seconds.

        Returns:
            Duration in seconds, or None if not completed
        """
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            return (datetime.utcnow() - self.started_at).total_seconds()
        return None

    def is_terminal(self) -> bool:
        """Check if job is in terminal state.

        Returns:
            True if job is completed, failed, or cancelled
        """
        return self.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.QUARANTINED)

    def can_retry(self) -> bool:
        """Check if job can be retried.

        Returns:
            True if job failed and retry count < max retries
        """
        return self.status == JobStatus.FAILED and self.retry_count < self.max_retries

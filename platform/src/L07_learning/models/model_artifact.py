"""L07 Learning Layer - Model Artifact Models."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional
import uuid
import hashlib


class ModelType(Enum):
    """Type of model artifact."""
    BASE = "base"
    FINE_TUNED = "fine_tuned"
    LORA_ADAPTER = "lora_adapter"
    DISTILLED = "distilled"
    REWARD_MODEL = "reward_model"


class ModelStage(Enum):
    """Deployment stage for model."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"
    QUARANTINED = "quarantined"


@dataclass
class ModelVersion:
    """Version metadata for model artifact."""

    version: str  # Semantic version (e.g., "1.0.0")
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "FineTuningEngine v1.0"
    change_summary: str = ""
    parent_version: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        return data


@dataclass
class ModelLineage:
    """Lineage tracking for model artifacts."""

    base_model_id: Optional[str] = None
    parent_model_id: Optional[str] = None
    training_job_id: Optional[str] = None
    dataset_id: Optional[str] = None
    dataset_version: Optional[str] = None
    training_config: Dict[str, Any] = field(default_factory=dict)
    training_metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ModelMetrics:
    """Performance metrics for model."""

    # Training metrics
    final_train_loss: float = 0.0
    final_eval_loss: float = 0.0
    training_duration_seconds: float = 0.0

    # Validation metrics
    accuracy: float = 0.0
    bleu_score: Optional[float] = None
    perplexity: Optional[float] = None

    # Performance metrics
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    throughput_queries_per_second: float = 0.0

    # Resource metrics
    model_size_mb: float = 0.0
    gpu_memory_mb: float = 0.0

    # Quality metrics
    regression_test_pass_rate: float = 0.0
    safety_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ModelArtifact:
    """Model artifact with versioning and lifecycle management.

    A model artifact represents a trained or fine-tuned model with complete
    metadata, lineage tracking, and deployment lifecycle management.
    """

    # Identifiers
    model_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    version: str = "1.0.0"

    # Type and stage
    model_type: ModelType = ModelType.FINE_TUNED
    stage: ModelStage = ModelStage.DEVELOPMENT

    # Artifact location
    artifact_path: str = ""
    artifact_format: str = "safetensors"
    artifact_size_bytes: int = 0

    # Checksum and signature
    checksum_sha256: Optional[str] = None
    signature: Optional[str] = None
    signed: bool = False
    signing_key_version: Optional[str] = None

    # Lineage
    lineage: ModelLineage = field(default_factory=ModelLineage)

    # Metrics
    metrics: ModelMetrics = field(default_factory=ModelMetrics)

    # Metadata
    description: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Stage history
    stage_history: List[Dict[str, Any]] = field(default_factory=list)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    deployed_at: Optional[datetime] = None

    # Creator
    created_by: str = "FineTuningEngine v1.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['model_type'] = self.model_type.value
        data['stage'] = self.stage.value
        data['lineage'] = self.lineage.to_dict()
        data['metrics'] = self.metrics.to_dict()
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        if self.deployed_at:
            data['deployed_at'] = self.deployed_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelArtifact':
        """Create from dictionary."""
        if 'model_type' in data and isinstance(data['model_type'], str):
            data['model_type'] = ModelType(data['model_type'])
        if 'stage' in data and isinstance(data['stage'], str):
            data['stage'] = ModelStage(data['stage'])
        if 'lineage' in data and isinstance(data['lineage'], dict):
            data['lineage'] = ModelLineage(**data['lineage'])
        if 'metrics' in data and isinstance(data['metrics'], dict):
            data['metrics'] = ModelMetrics(**data['metrics'])
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        if 'deployed_at' in data and isinstance(data['deployed_at'], str):
            data['deployed_at'] = datetime.fromisoformat(data['deployed_at'])
        return cls(**data)

    def compute_checksum(self, file_path: str) -> str:
        """Compute SHA256 checksum of artifact file.

        Args:
            file_path: Path to artifact file

        Returns:
            SHA256 checksum
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        checksum = sha256_hash.hexdigest()
        self.checksum_sha256 = checksum
        return checksum

    def verify_checksum(self, file_path: str) -> bool:
        """Verify artifact checksum.

        Args:
            file_path: Path to artifact file

        Returns:
            True if checksum matches, False otherwise
        """
        if not self.checksum_sha256:
            return False
        computed = self.compute_checksum(file_path)
        return computed == self.checksum_sha256

    def transition_stage(
        self,
        new_stage: ModelStage,
        transitioned_by: str,
        notes: str = "",
        approval_required: bool = False,
        approver: Optional[str] = None
    ) -> None:
        """Transition model to new stage.

        Args:
            new_stage: Target stage
            transitioned_by: User/service performing transition
            notes: Optional transition notes
            approval_required: Whether approval was required
            approver: Approver if approval required
        """
        transition = {
            "from_stage": self.stage.value,
            "to_stage": new_stage.value,
            "transitioned_at": datetime.utcnow().isoformat(),
            "transitioned_by": transitioned_by,
            "notes": notes,
            "approval_required": approval_required,
            "approver": approver
        }
        self.stage_history.append(transition)
        self.stage = new_stage
        self.updated_at = datetime.utcnow()

        if new_stage == ModelStage.PRODUCTION:
            self.deployed_at = datetime.utcnow()

    def can_transition_to(self, target_stage: ModelStage) -> tuple[bool, str]:
        """Check if model can transition to target stage.

        Args:
            target_stage: Target stage

        Returns:
            Tuple of (can_transition, reason)
        """
        # Define allowed transitions
        allowed_transitions = {
            ModelStage.DEVELOPMENT: [ModelStage.STAGING, ModelStage.ARCHIVED],
            ModelStage.STAGING: [ModelStage.PRODUCTION, ModelStage.DEVELOPMENT, ModelStage.ARCHIVED],
            ModelStage.PRODUCTION: [ModelStage.ARCHIVED, ModelStage.QUARANTINED],
            ModelStage.ARCHIVED: [],
            ModelStage.QUARANTINED: [ModelStage.ARCHIVED]
        }

        if target_stage not in allowed_transitions.get(self.stage, []):
            return False, f"Cannot transition from {self.stage.value} to {target_stage.value}"

        # Additional validation for production
        if target_stage == ModelStage.PRODUCTION:
            if not self.metrics.regression_test_pass_rate or self.metrics.regression_test_pass_rate < 0.95:
                return False, "Regression test pass rate too low for production"
            if not self.signed:
                return False, "Model must be signed before production deployment"

        return True, "Transition allowed"

    def validate(self) -> bool:
        """Validate model artifact.

        Returns:
            True if valid, False otherwise
        """
        if not self.name:
            return False
        if not self.artifact_path:
            return False
        if self.stage == ModelStage.PRODUCTION and not self.signed:
            return False
        return True

"""L07 Learning Layer - Reward Signal Models for RLHF."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional
import uuid


class RewardSource(Enum):
    """Source of reward signal."""
    L06_QUALITY_SCORE = "l06_quality_score"
    HUMAN_FEEDBACK = "human_feedback"
    AUTOMATED_METRIC = "automated_metric"
    PREFERENCE_PAIR = "preference_pair"


@dataclass
class RewardSignal:
    """Reward signal for reinforcement learning.

    Represents a quality signal that can be used to train reward models
    or directly for policy optimization.
    """

    # Identifiers
    signal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    execution_id: str = ""
    task_id: str = ""

    # Reward value
    reward: float = 0.0  # Normalized reward [-1, 1]
    raw_score: float = 0.0  # Original score before normalization
    confidence: float = 0.0  # Confidence in reward [0, 1]

    # Source
    source: RewardSource = RewardSource.L06_QUALITY_SCORE
    source_metadata: Dict[str, Any] = field(default_factory=dict)

    # Context
    trajectory: List[Dict[str, Any]] = field(default_factory=list)
    outcome: str = ""
    outcome_type: str = "success"  # success, failure, timeout, error

    # Timestamp
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['source'] = self.source.value
        data['created_at'] = self.created_at.isoformat()
        return data

    @classmethod
    def from_quality_score(
        cls,
        execution_id: str,
        task_id: str,
        quality_score: float,
        confidence: float,
        outcome_type: str = "success"
    ) -> 'RewardSignal':
        """Create reward signal from L06 quality score.

        Args:
            execution_id: Execution identifier
            task_id: Task identifier
            quality_score: Quality score from L06 (0-100)
            confidence: Confidence in score (0-1)
            outcome_type: Type of outcome

        Returns:
            RewardSignal instance
        """
        # Normalize quality score to [-1, 1]
        normalized_reward = (quality_score - 50) / 50

        # Apply confidence weighting
        weighted_reward = normalized_reward * confidence

        # Apply failure penalties
        penalties = {
            "timeout": -0.5,
            "error": -0.3,
            "constraint_violation": -0.2
        }
        penalty = penalties.get(outcome_type, 0.0)

        final_reward = max(-1.0, min(1.0, weighted_reward + penalty))

        return cls(
            execution_id=execution_id,
            task_id=task_id,
            reward=final_reward,
            raw_score=quality_score,
            confidence=confidence,
            source=RewardSource.L06_QUALITY_SCORE,
            outcome_type=outcome_type
        )


@dataclass
class PreferencePair:
    """Preference pair for reward model training.

    Represents a comparison between two outputs where one is preferred
    over the other. Used for training reward models in RLHF.
    """

    # Identifiers
    pair_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""

    # Input (shared between both outputs)
    input_text: str = ""
    input_context: Dict[str, Any] = field(default_factory=dict)

    # Preferred output
    preferred_output: str = ""
    preferred_trajectory: List[Dict[str, Any]] = field(default_factory=list)
    preferred_score: float = 0.0

    # Rejected output
    rejected_output: str = ""
    rejected_trajectory: List[Dict[str, Any]] = field(default_factory=list)
    rejected_score: float = 0.0

    # Preference metadata
    preference_strength: float = 0.0  # How much better is preferred? [0, 1]
    source: str = "l06_quality_score"
    confidence: float = 0.0

    # Timestamp
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        return data


@dataclass
class RewardModel:
    """Trained reward model for RLHF.

    A reward model is a classifier trained to predict quality scores
    from execution trajectories. Used in PPO policy optimization.
    """

    # Identifiers
    model_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "reward_model"
    version: str = "1.0.0"

    # Model artifacts
    model_path: str = ""
    model_type: str = "classifier"

    # Training metadata
    training_dataset_size: int = 0
    training_pairs_count: int = 0
    training_accuracy: float = 0.0
    validation_accuracy: float = 0.0

    # Configuration
    config: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    trained_by: str = "RLHFEngine v1.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        return data

    def predict_reward(self, trajectory: List[Dict[str, Any]]) -> float:
        """Predict reward for trajectory (stub).

        Args:
            trajectory: Execution trajectory

        Returns:
            Predicted reward [-1, 1]
        """
        # Stub implementation - in production would use actual model
        return 0.0

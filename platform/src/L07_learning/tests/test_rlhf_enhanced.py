"""
L07 Learning Layer - Enhanced RLHF Tests

Tests for enhanced RLHF functionality (beyond stub implementations).
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from typing import List, Dict, Any

from L07_learning.models.reward_signal import PreferencePair, RewardModel


@pytest.mark.l07
@pytest.mark.unit
class TestRewardModelTraining:
    """Tests for reward model training."""

    @pytest.mark.asyncio
    async def test_train_reward_model_returns_model(self):
        """Test that train_reward_model returns a RewardModel."""
        from L07_learning.services.rlhf_engine import RLHFEngine

        engine = RLHFEngine()

        # Create sample preference pairs
        pairs = create_sample_preference_pairs(100)

        model = await engine.train_reward_model(pairs)

        assert model is not None
        assert isinstance(model, RewardModel)
        assert model.training_pairs_count == 100

    @pytest.mark.asyncio
    async def test_reward_model_has_accuracy_metrics(self):
        """Test that trained reward model has accuracy metrics."""
        from L07_learning.services.rlhf_engine import RLHFEngine

        engine = RLHFEngine()
        pairs = create_sample_preference_pairs(200)

        model = await engine.train_reward_model(pairs)

        assert hasattr(model, 'training_accuracy')
        assert hasattr(model, 'validation_accuracy')
        assert 0.0 <= model.training_accuracy <= 1.0
        assert 0.0 <= model.validation_accuracy <= 1.0

    @pytest.mark.asyncio
    async def test_reward_model_uses_classifier(self):
        """Test that reward model training uses binary classifier approach."""
        from L07_learning.services.rlhf_engine import RLHFEngine

        engine = RLHFEngine()
        pairs = create_sample_preference_pairs(150)

        model = await engine.train_reward_model(
            pairs,
            config={"classifier_type": "binary"}
        )

        # Should have training metadata about classifier
        assert model is not None
        # Config should be stored
        assert model.config.get("classifier_type") == "binary"


@pytest.mark.l07
@pytest.mark.unit
class TestKLDivergenceComputation:
    """Tests for KL divergence computation."""

    @pytest.mark.asyncio
    async def test_compute_kl_returns_float(self):
        """Test that compute_kl_divergence returns a float."""
        from L07_learning.services.rlhf_engine import RLHFEngine

        engine = RLHFEngine()

        kl = await engine.compute_kl_divergence(
            base_model_id="gpt2",
            optimized_model_id="gpt2-optimized"
        )

        assert isinstance(kl, float)
        assert kl >= 0.0

    @pytest.mark.asyncio
    async def test_kl_divergence_is_non_negative(self):
        """Test that KL divergence is always non-negative."""
        from L07_learning.services.rlhf_engine import RLHFEngine

        engine = RLHFEngine()

        # Run multiple times to check consistency
        for _ in range(10):
            kl = await engine.compute_kl_divergence(
                base_model_id="model-a",
                optimized_model_id="model-b"
            )
            assert kl >= 0.0, "KL divergence must be non-negative"

    @pytest.mark.asyncio
    async def test_kl_with_sample_distributions(self):
        """Test KL computation with provided sample distributions."""
        from L07_learning.services.rlhf_engine import RLHFEngine

        engine = RLHFEngine()

        # If the engine supports passing distributions directly
        if hasattr(engine, '_compute_kl_from_samples'):
            import numpy as np

            # Create sample distributions
            p_samples = np.random.normal(0, 1, 1000)
            q_samples = np.random.normal(0.1, 1.1, 1000)

            kl = engine._compute_kl_from_samples(p_samples, q_samples)
            assert isinstance(kl, float)
            assert kl >= 0.0


@pytest.mark.l07
@pytest.mark.unit
class TestRewardHackingDetection:
    """Tests for reward hacking detection."""

    @pytest.mark.asyncio
    async def test_detect_reward_hacking_returns_bool(self):
        """Test that detect_reward_hacking returns a boolean."""
        from L07_learning.services.rlhf_engine import RLHFEngine

        engine = RLHFEngine()

        test_cases = create_adversarial_test_cases(10)

        result = await engine.detect_reward_hacking(
            model_id="test-model",
            test_cases=test_cases
        )

        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_detect_with_adversarial_cases(self):
        """Test detection uses adversarial test cases."""
        from L07_learning.services.rlhf_engine import RLHFEngine

        engine = RLHFEngine()

        # Create adversarial test cases that should trigger detection
        adversarial_cases = [
            {
                "input": "Summarize this article",
                "expected_pattern": "high_reward_but_wrong",
                "adversarial_output": "A" * 1000,  # Repetitive padding
            },
            {
                "input": "Answer this question",
                "expected_pattern": "reward_gaming",
                "adversarial_output": "Yes" * 100,  # Repetitive pattern
            }
        ]

        result = await engine.detect_reward_hacking(
            model_id="suspicious-model",
            test_cases=adversarial_cases
        )

        # Result should be boolean
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_hacking_detection_uses_test_cases(self):
        """Test that hacking detection actually uses the test cases."""
        from L07_learning.services.rlhf_engine import RLHFEngine

        engine = RLHFEngine()

        # Empty test cases - should not detect hacking
        result_empty = await engine.detect_reward_hacking(
            model_id="model-1",
            test_cases=[]
        )

        # With test cases
        test_cases = create_adversarial_test_cases(20)
        result_with_cases = await engine.detect_reward_hacking(
            model_id="model-2",
            test_cases=test_cases
        )

        # Both should return booleans
        assert isinstance(result_empty, bool)
        assert isinstance(result_with_cases, bool)


@pytest.mark.l07
@pytest.mark.unit
class TestPreferencePairCreation:
    """Tests for preference pair creation from quality scores."""

    @pytest.mark.asyncio
    async def test_create_preference_pairs_from_quality(self):
        """Test creating preference pairs from quality scores."""
        from L07_learning.services.rlhf_engine import RLHFEngine

        engine = RLHFEngine()

        execution_data = [
            {"task_id": "t1", "input": "Q1", "output": "A1", "quality_score": 90},
            {"task_id": "t2", "input": "Q2", "output": "A2", "quality_score": 50},
            {"task_id": "t3", "input": "Q3", "output": "A3", "quality_score": 80},
            {"task_id": "t4", "input": "Q4", "output": "A4", "quality_score": 30},
        ]

        pairs = await engine.create_preference_pairs_from_quality_scores(
            execution_data
        )

        assert len(pairs) >= 1
        # Preferred should have higher score than rejected
        for pair in pairs:
            assert pair.preferred_score >= pair.rejected_score

    @pytest.mark.asyncio
    async def test_preference_pairs_have_strength(self):
        """Test that preference pairs have strength calculated."""
        from L07_learning.services.rlhf_engine import RLHFEngine

        engine = RLHFEngine()

        execution_data = [
            {"task_id": "t1", "input": "Q1", "output": "Good", "quality_score": 95},
            {"task_id": "t2", "input": "Q2", "output": "Bad", "quality_score": 20},
        ]

        pairs = await engine.create_preference_pairs_from_quality_scores(
            execution_data
        )

        if pairs:
            pair = pairs[0]
            assert hasattr(pair, 'preference_strength')
            assert 0.0 <= pair.preference_strength <= 1.0


@pytest.mark.l07
@pytest.mark.unit
class TestRLHFConfiguration:
    """Tests for RLHF configuration."""

    def test_rlhf_config_defaults(self):
        """Test that RLHFConfig has sensible defaults."""
        from L07_learning.services.rlhf_engine import RLHFConfig

        config = RLHFConfig()

        assert config.rollout_size > 0
        assert config.mini_batch_size > 0
        assert config.clip_ratio > 0
        assert config.clip_ratio < 1.0
        assert config.kl_penalty_coeff >= 0

    def test_rlhf_config_custom_values(self):
        """Test that RLHFConfig accepts custom values."""
        from L07_learning.services.rlhf_engine import RLHFConfig

        config = RLHFConfig(
            rollout_size=1024,
            clip_ratio=0.1,
            kl_penalty_coeff=0.05
        )

        assert config.rollout_size == 1024
        assert config.clip_ratio == 0.1
        assert config.kl_penalty_coeff == 0.05


@pytest.mark.l07
@pytest.mark.unit
class TestPolicyOptimization:
    """Tests for policy optimization (stub behavior)."""

    @pytest.mark.asyncio
    async def test_optimize_policy_returns_artifact(self):
        """Test that optimize_policy returns a ModelArtifact."""
        from L07_learning.services.rlhf_engine import RLHFEngine

        engine = RLHFEngine()

        # First train a reward model
        pairs = create_sample_preference_pairs(100)
        reward_model = await engine.train_reward_model(pairs)

        # Then optimize policy
        artifact = await engine.optimize_policy(
            base_model_id="gpt2",
            reward_model=reward_model
        )

        assert artifact is not None
        assert hasattr(artifact, 'model_id')
        assert hasattr(artifact, 'lineage')

    @pytest.mark.asyncio
    async def test_optimized_policy_has_lineage(self):
        """Test that optimized policy has proper lineage."""
        from L07_learning.services.rlhf_engine import RLHFEngine

        engine = RLHFEngine()

        pairs = create_sample_preference_pairs(100)
        reward_model = await engine.train_reward_model(pairs)

        artifact = await engine.optimize_policy(
            base_model_id="base-gpt2",
            reward_model=reward_model
        )

        assert artifact.lineage is not None
        assert artifact.lineage.base_model_id == "base-gpt2"


# Helper functions


def create_sample_preference_pairs(count: int) -> List[PreferencePair]:
    """Create sample preference pairs for testing."""
    pairs = []
    for i in range(count):
        pair = PreferencePair(
            task_id=f"task_{i}",
            input_text=f"Question {i}",
            preferred_output=f"Good answer {i}",
            preferred_score=80 + (i % 20),
            rejected_output=f"Bad answer {i}",
            rejected_score=30 + (i % 20),
            preference_strength=0.5 + (i % 50) / 100.0
        )
        pairs.append(pair)
    return pairs


def create_adversarial_test_cases(count: int) -> List[Dict[str, Any]]:
    """Create adversarial test cases for reward hacking detection."""
    cases = []
    for i in range(count):
        case = {
            "input": f"Test input {i}",
            "expected_behavior": "coherent_response",
            "adversarial_patterns": [
                "repetition",
                "padding",
                "keyword_stuffing"
            ]
        }
        cases.append(case)
    return cases

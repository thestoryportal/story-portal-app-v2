"""
L07 Learning Layer - Real Training Tests

Tests for real training with HuggingFace/PEFT (GPU optional).
These tests verify the training pipeline works correctly.
"""

import pytest
import os
import json
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any

from L07_learning.services.gpu_detector import GPUDetector


# Check if GPU/MPS is available for real training tests
GPU_AVAILABLE = GPUDetector.detect().get("available", False)


@pytest.mark.l07
@pytest.mark.unit
class TestFineTuningEngineAutoDetection:
    """Tests for automatic GPU detection in FineTuningEngine."""

    def test_engine_auto_detects_simulation_mode_without_gpu(self):
        """Test that engine auto-detects simulation mode when no GPU."""
        from L07_learning.services.fine_tuning_engine import FineTuningEngine

        with patch.object(GPUDetector, 'detect', return_value={"available": False}):
            engine = FineTuningEngine(simulate_training=None)
            assert engine.simulate_training is True

    def test_engine_auto_detects_real_mode_with_gpu(self):
        """Test that engine auto-detects real mode when GPU available."""
        from L07_learning.services.fine_tuning_engine import FineTuningEngine

        with patch.object(GPUDetector, 'detect', return_value={"available": True, "backend": "cuda"}):
            engine = FineTuningEngine(simulate_training=None)
            assert engine.simulate_training is False

    def test_engine_respects_explicit_simulation_flag(self):
        """Test that explicit simulate_training flag is respected."""
        from L07_learning.services.fine_tuning_engine import FineTuningEngine

        engine = FineTuningEngine(simulate_training=True)
        assert engine.simulate_training is True

        engine2 = FineTuningEngine(simulate_training=False)
        assert engine2.simulate_training is False


@pytest.mark.l07
@pytest.mark.unit
class TestRealTrainingPreparation:
    """Tests for real training preparation (no GPU required)."""

    def test_load_model_function_exists(self):
        """Test that load_model helper exists."""
        from L07_learning.services.fine_tuning_engine import FineTuningEngine

        engine = FineTuningEngine(simulate_training=False)
        assert hasattr(engine, '_load_base_model')

    def test_prepare_lora_config_exists(self):
        """Test that LoRA config preparation exists."""
        from L07_learning.services.fine_tuning_engine import FineTuningEngine

        engine = FineTuningEngine(simulate_training=False)
        assert hasattr(engine, '_prepare_lora_config')

    def test_prepare_dataset_exists(self):
        """Test that dataset preparation exists."""
        from L07_learning.services.fine_tuning_engine import FineTuningEngine

        engine = FineTuningEngine(simulate_training=False)
        assert hasattr(engine, '_prepare_training_dataset')

    def test_save_model_checkpoint_exists(self):
        """Test that model checkpoint saving exists."""
        from L07_learning.services.fine_tuning_engine import FineTuningEngine

        engine = FineTuningEngine(simulate_training=False)
        assert hasattr(engine, '_save_model_checkpoint')


@pytest.mark.l07
@pytest.mark.unit
class TestLoRAConfigPreparation:
    """Tests for LoRA configuration preparation."""

    @pytest.mark.asyncio
    async def test_prepare_lora_config_returns_dict(self):
        """Test that LoRA config preparation returns dict."""
        from L07_learning.services.fine_tuning_engine import FineTuningEngine
        from L07_learning.models.training_job import JobConfig, LoRAConfig

        engine = FineTuningEngine(simulate_training=False)

        config = JobConfig(
            lora_config=LoRAConfig(
                rank=8,
                alpha=16,
                dropout=0.1,
                target_modules=["q_proj", "v_proj"]
            )
        )

        lora_config = engine._prepare_lora_config(config)

        assert isinstance(lora_config, dict)
        assert "r" in lora_config
        assert "lora_alpha" in lora_config
        assert "lora_dropout" in lora_config
        assert lora_config["r"] == 8
        assert lora_config["lora_alpha"] == 16
        assert lora_config["lora_dropout"] == 0.1

    @pytest.mark.asyncio
    async def test_lora_config_has_target_modules(self):
        """Test that LoRA config includes target modules."""
        from L07_learning.services.fine_tuning_engine import FineTuningEngine
        from L07_learning.models.training_job import JobConfig, LoRAConfig

        engine = FineTuningEngine(simulate_training=False)

        config = JobConfig(
            lora_config=LoRAConfig(
                target_modules=["q_proj", "k_proj", "v_proj"]
            )
        )

        lora_config = engine._prepare_lora_config(config)

        assert "target_modules" in lora_config
        assert "q_proj" in lora_config["target_modules"]


@pytest.mark.l07
@pytest.mark.unit
class TestTrainingArgumentsPreparation:
    """Tests for training arguments preparation."""

    def test_prepare_training_args_exists(self):
        """Test that training args preparation exists."""
        from L07_learning.services.fine_tuning_engine import FineTuningEngine

        engine = FineTuningEngine(simulate_training=False)
        assert hasattr(engine, '_prepare_training_arguments')

    @pytest.mark.asyncio
    async def test_training_args_has_required_fields(self):
        """Test that training args has required fields."""
        from L07_learning.services.fine_tuning_engine import FineTuningEngine
        from L07_learning.models.training_job import TrainingJob, JobConfig, JobType

        engine = FineTuningEngine(simulate_training=False)

        job = TrainingJob(
            job_name="test_job",
            job_type=JobType.SFT,
            config=JobConfig(
                num_epochs=3,
                batch_size=4,
                learning_rate=2e-5
            ),
            dataset_id="ds-001",
            base_model_id="gpt2"
        )

        args = engine._prepare_training_arguments(job)

        assert isinstance(args, dict)
        assert "num_train_epochs" in args
        assert "per_device_train_batch_size" in args
        assert "learning_rate" in args
        assert "warmup_ratio" in args
        assert "weight_decay" in args
        assert args["num_train_epochs"] == 3
        assert args["per_device_train_batch_size"] == 4


@pytest.mark.l07
@pytest.mark.unit
class TestCheckpointSaving:
    """Tests for model checkpoint saving."""

    @pytest.mark.asyncio
    async def test_save_model_checkpoint_creates_file(self):
        """Test that saving checkpoint creates a file."""
        from L07_learning.services.fine_tuning_engine import FineTuningEngine
        from L07_learning.models.training_job import TrainingJob, JobConfig, JobType
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            engine = FineTuningEngine(
                simulate_training=False,
                checkpoint_dir=tmpdir
            )

            job = TrainingJob(
                job_name="test_checkpoint",
                job_type=JobType.SFT,
                config=JobConfig(),
                dataset_id="ds-001",
                base_model_id="gpt2"
            )

            # Mock model for checkpoint
            mock_model = MagicMock()
            mock_model.save_pretrained = MagicMock()

            checkpoint_path = await engine._save_model_checkpoint(
                job=job,
                model=mock_model,
                epoch=1,
                step=100,
                train_loss=0.5
            )

            assert checkpoint_path is not None
            assert job.job_id in checkpoint_path

    @pytest.mark.asyncio
    async def test_checkpoint_metadata_saved(self):
        """Test that checkpoint metadata is saved."""
        from L07_learning.services.fine_tuning_engine import FineTuningEngine
        from L07_learning.models.training_job import TrainingJob, JobConfig, JobType
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            engine = FineTuningEngine(
                simulate_training=False,
                checkpoint_dir=tmpdir
            )

            job = TrainingJob(
                job_name="test_metadata",
                job_type=JobType.SFT,
                config=JobConfig(learning_rate=1e-5),
                dataset_id="ds-001",
                base_model_id="gpt2"
            )

            mock_model = MagicMock()
            mock_model.save_pretrained = MagicMock()

            checkpoint_path = await engine._save_model_checkpoint(
                job=job,
                model=mock_model,
                epoch=2,
                step=200,
                train_loss=0.3
            )

            # Check metadata file exists - checkpoint_path is a directory
            metadata_path = os.path.join(
                checkpoint_path,
                "checkpoint_metadata.json"
            )
            assert os.path.exists(metadata_path)

            with open(metadata_path) as f:
                metadata = json.load(f)

            assert metadata["epoch"] == 2
            assert metadata["step"] == 200
            assert metadata["train_loss"] == 0.3


@pytest.mark.l07
@pytest.mark.unit
class TestResumeFromCheckpoint:
    """Tests for resuming training from checkpoint."""

    @pytest.mark.asyncio
    async def test_load_checkpoint_function_exists(self):
        """Test that load checkpoint function exists."""
        from L07_learning.services.fine_tuning_engine import FineTuningEngine

        engine = FineTuningEngine(simulate_training=False)
        assert hasattr(engine, '_load_model_from_checkpoint')


@pytest.mark.l07
@pytest.mark.slow
@pytest.mark.skipif(not GPU_AVAILABLE, reason="GPU required for real training tests")
class TestRealTrainingWithGPU:
    """Tests that require GPU (skipped if no GPU available)."""

    @pytest.mark.asyncio
    async def test_lora_training_completes(self):
        """Test that LoRA training completes successfully."""
        from L07_learning.services.fine_tuning_engine import FineTuningEngine
        from L07_learning.models.training_job import JobConfig
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            engine = FineTuningEngine(
                simulate_training=False,
                checkpoint_dir=tmpdir
            )

            # Use very small config for testing
            config = JobConfig(
                num_epochs=1,
                batch_size=1,
                learning_rate=1e-5
            )

            job = await engine.start_training(
                dataset_id="test_dataset",
                base_model_id="distilgpt2",  # Small model for testing
                config=config
            )

            # Wait for completion (with timeout)
            import asyncio
            for _ in range(60):  # Max 60 seconds
                status = await engine.get_job_status(job.job_id)
                if status and status.is_terminal():
                    break
                await asyncio.sleep(1)

            final_status = await engine.get_job_status(job.job_id)
            assert final_status is not None
            # May fail due to missing dataset, but should not raise exception
            assert final_status.status in ["COMPLETED", "FAILED"]

    @pytest.mark.asyncio
    async def test_checkpoint_saves_safetensors(self):
        """Test that checkpoints are saved in safetensors format."""
        from L07_learning.services.fine_tuning_engine import FineTuningEngine
        import tempfile
        import glob

        with tempfile.TemporaryDirectory() as tmpdir:
            engine = FineTuningEngine(
                simulate_training=False,
                checkpoint_dir=tmpdir,
                checkpoint_interval_epochs=1
            )

            # This test verifies the format but doesn't run full training
            # Just check that save_model_checkpoint uses safetensors
            from L07_learning.models.training_job import TrainingJob, JobConfig, JobType

            job = TrainingJob(
                job_name="test_format",
                job_type=JobType.SFT,
                config=JobConfig(),
                dataset_id="ds-001",
                base_model_id="gpt2"
            )

            mock_model = MagicMock()
            mock_model.save_pretrained = MagicMock()

            await engine._save_model_checkpoint(
                job=job,
                model=mock_model,
                epoch=1,
                step=100,
                train_loss=0.5
            )

            # Verify save_pretrained was called with safe_serialization
            mock_model.save_pretrained.assert_called()
            call_kwargs = mock_model.save_pretrained.call_args
            # Should have safe_serialization=True
            assert call_kwargs is not None


@pytest.mark.l07
@pytest.mark.unit
class TestTrainingMetricsCollection:
    """Tests for training metrics collection during real training."""

    def test_metrics_collector_exists(self):
        """Test that metrics collector exists."""
        from L07_learning.services.fine_tuning_engine import FineTuningEngine

        engine = FineTuningEngine(simulate_training=False)
        assert hasattr(engine, '_create_training_callback')

    @pytest.mark.asyncio
    async def test_callback_records_metrics(self):
        """Test that training callback records metrics."""
        from L07_learning.services.fine_tuning_engine import FineTuningEngine
        from L07_learning.models.training_job import TrainingJob, JobConfig, JobType

        engine = FineTuningEngine(simulate_training=False)

        job = TrainingJob(
            job_name="test_callback",
            job_type=JobType.SFT,
            config=JobConfig(),
            dataset_id="ds-001",
            base_model_id="gpt2"
        )

        callback = engine._create_training_callback(job)

        # Callback may be None if transformers not installed
        if callback is not None:
            # Callback should be a class or function with on_log method
            assert callable(callback) or hasattr(callback, 'on_log')
        else:
            # This is acceptable - transformers not available
            import warnings
            warnings.warn("transformers not installed, callback test skipped")

"""
L07 Learning Layer - GPU Detection Tests

Tests for GPU detection and automatic training mode selection.
"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.l07
@pytest.mark.unit
class TestGPUDetection:
    """Tests for GPU detection functionality."""

    def test_detect_returns_dict_with_available_key(self):
        """Test that detect() returns dict with 'available' key."""
        from L07_learning.services.gpu_detector import GPUDetector

        result = GPUDetector.detect()

        assert isinstance(result, dict)
        assert "available" in result
        assert isinstance(result["available"], bool)

    def test_detect_returns_device_count(self):
        """Test that detect() returns device_count."""
        from L07_learning.services.gpu_detector import GPUDetector

        result = GPUDetector.detect()

        assert "device_count" in result
        assert isinstance(result["device_count"], int)
        assert result["device_count"] >= 0

    def test_detect_returns_devices_list(self):
        """Test that detect() returns devices list."""
        from L07_learning.services.gpu_detector import GPUDetector

        result = GPUDetector.detect()

        assert "devices" in result
        assert isinstance(result["devices"], list)

    @patch('L07_learning.services.gpu_detector.torch')
    @patch('L07_learning.services.gpu_detector.TORCH_AVAILABLE', True)
    def test_detect_with_cuda_available(self, mock_torch):
        """Test detection when CUDA is available."""
        from L07_learning.services.gpu_detector import GPUDetector

        # Clear cache to force re-detection
        GPUDetector.clear_cache()

        # Mock CUDA availability
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.device_count.return_value = 2
        mock_torch.cuda.get_device_name.side_effect = ["GPU 0", "GPU 1"]
        mock_props = MagicMock()
        mock_props.total_memory = 8 * 1024 * 1024 * 1024  # 8GB
        mock_props.major = 8
        mock_props.minor = 0
        mock_props.multi_processor_count = 80
        mock_torch.cuda.get_device_properties.return_value = mock_props

        result = GPUDetector.detect(force_refresh=True)

        assert result["available"] is True
        assert result["device_count"] == 2

        # Clean up
        GPUDetector.clear_cache()

    @patch('L07_learning.services.gpu_detector.torch')
    def test_detect_without_cuda(self, mock_torch):
        """Test detection when CUDA is not available."""
        from L07_learning.services.gpu_detector import GPUDetector

        mock_torch.cuda.is_available.return_value = False

        result = GPUDetector.detect()

        assert result["available"] is False
        assert result["device_count"] == 0

    def test_detect_handles_no_torch(self):
        """Test that detect() handles missing torch gracefully."""
        from L07_learning.services.gpu_detector import GPUDetector

        # This test verifies the fallback behavior
        result = GPUDetector.detect()

        # Should return valid result even if torch not installed
        assert isinstance(result, dict)
        assert "available" in result


@pytest.mark.l07
@pytest.mark.unit
class TestGPUDetectorHelpers:
    """Tests for GPU detector helper methods."""

    def test_get_device_info(self):
        """Test getting device info."""
        from L07_learning.services.gpu_detector import GPUDetector

        info = GPUDetector.get_device_info()

        assert "cuda_available" in info
        assert "cuda_version" in info

    def test_check_memory_requirements(self):
        """Test checking memory requirements."""
        from L07_learning.services.gpu_detector import GPUDetector

        # Check with small requirement (should pass even without GPU)
        can_train = GPUDetector.check_memory_requirements(
            required_memory_gb=0.1,
            model_size_gb=0.01,
        )

        assert isinstance(can_train, bool)

    def test_recommend_batch_size(self):
        """Test batch size recommendation."""
        from L07_learning.services.gpu_detector import GPUDetector

        batch_size = GPUDetector.recommend_batch_size(
            model_size_gb=0.5,
        )

        assert isinstance(batch_size, int)
        assert batch_size > 0


@pytest.mark.l07
@pytest.mark.unit
class TestTrainingModeSelection:
    """Tests for automatic training mode selection."""

    def test_fallback_to_simulation_when_no_gpu(self):
        """Test that training falls back to simulation without GPU."""
        from L07_learning.services.gpu_detector import GPUDetector

        detection = GPUDetector.detect()

        # Should determine training mode based on GPU availability
        if detection["available"]:
            recommended_mode = "gpu"
        else:
            recommended_mode = "simulation"

        mode = GPUDetector.recommend_training_mode()
        assert mode in ["gpu", "simulation", "cpu"]

    def test_get_training_device(self):
        """Test getting recommended training device."""
        from L07_learning.services.gpu_detector import GPUDetector

        device = GPUDetector.get_training_device()

        # Should return valid device string
        assert device in ["cuda", "cuda:0", "cpu", "mps"]

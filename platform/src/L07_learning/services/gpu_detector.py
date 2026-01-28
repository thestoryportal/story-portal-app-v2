"""
L07 Learning Layer - GPU Detector

Utility for detecting GPU availability and configuring training modes.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Try to import torch for GPU detection
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available - GPU detection will report no GPUs")


class GPUDetector:
    """
    Utility class for GPU detection and training mode configuration.

    Provides methods to:
    - Detect available GPUs
    - Check memory requirements
    - Recommend training configurations
    """

    _cached_detection: Optional[Dict[str, Any]] = None

    @classmethod
    def detect(cls, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Detect available GPUs and their capabilities.

        Args:
            force_refresh: Force re-detection even if cached

        Returns:
            Dictionary with GPU information:
            - available: bool - whether GPU is available
            - device_count: int - number of GPUs
            - devices: list - list of device info dicts
            - cuda_version: str - CUDA version if available
            - backend: str - 'cuda', 'mps', or 'cpu'
        """
        if cls._cached_detection is not None and not force_refresh:
            return cls._cached_detection

        result = {
            "available": False,
            "device_count": 0,
            "devices": [],
            "cuda_version": None,
            "backend": "cpu",
            "torch_available": TORCH_AVAILABLE,
        }

        if not TORCH_AVAILABLE:
            cls._cached_detection = result
            return result

        try:
            # Check CUDA availability
            if torch.cuda.is_available():
                result["available"] = True
                result["device_count"] = torch.cuda.device_count()
                result["cuda_version"] = torch.version.cuda
                result["backend"] = "cuda"

                # Get device info
                for i in range(result["device_count"]):
                    try:
                        props = torch.cuda.get_device_properties(i)
                        device_info = {
                            "index": i,
                            "name": torch.cuda.get_device_name(i),
                            "total_memory_gb": props.total_memory / (1024**3),
                            "major": props.major,
                            "minor": props.minor,
                            "multi_processor_count": props.multi_processor_count,
                        }
                        result["devices"].append(device_info)
                    except Exception as e:
                        logger.warning(f"Error getting device {i} properties: {e}")

            # Check MPS (Apple Silicon) availability
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                result["available"] = True
                result["device_count"] = 1
                result["backend"] = "mps"
                result["devices"].append({
                    "index": 0,
                    "name": "Apple MPS",
                    "total_memory_gb": None,  # MPS doesn't expose memory info
                })

        except Exception as e:
            logger.error(f"Error during GPU detection: {e}")

        cls._cached_detection = result
        logger.info(
            f"GPU detection: available={result['available']}, "
            f"backend={result['backend']}, devices={result['device_count']}"
        )

        return result

    @classmethod
    def get_device_info(cls) -> Dict[str, Any]:
        """
        Get comprehensive device information.

        Returns:
            Dictionary with device info
        """
        detection = cls.detect()

        info = {
            "cuda_available": detection["backend"] == "cuda",
            "cuda_version": detection["cuda_version"],
            "mps_available": detection["backend"] == "mps",
            "torch_available": TORCH_AVAILABLE,
            "torch_version": torch.__version__ if TORCH_AVAILABLE else None,
            "device_count": detection["device_count"],
            "devices": detection["devices"],
        }

        return info

    @classmethod
    def check_memory_requirements(
        cls,
        required_memory_gb: float,
        model_size_gb: float,
    ) -> bool:
        """
        Check if available GPU memory meets requirements.

        Args:
            required_memory_gb: Required GPU memory in GB
            model_size_gb: Model size in GB

        Returns:
            True if requirements can be met
        """
        detection = cls.detect()

        if not detection["available"]:
            # No GPU, can't meet requirements
            return False

        if detection["backend"] == "mps":
            # MPS doesn't expose memory, assume it can handle it
            return True

        # Check if any device has enough memory
        total_required = required_memory_gb + model_size_gb
        for device in detection["devices"]:
            if device.get("total_memory_gb", 0) >= total_required:
                return True

        return False

    @classmethod
    def recommend_batch_size(
        cls,
        model_size_gb: float,
        sequence_length: int = 512,
        target_memory_utilization: float = 0.8,
    ) -> int:
        """
        Recommend batch size based on available memory.

        Args:
            model_size_gb: Model size in GB
            sequence_length: Sequence length for training
            target_memory_utilization: Target GPU memory utilization

        Returns:
            Recommended batch size
        """
        detection = cls.detect()

        if not detection["available"]:
            # CPU training - use small batch size
            return 4

        if detection["backend"] == "mps":
            # MPS - use moderate batch size
            return 8

        # CUDA - calculate based on memory
        max_memory_gb = max(
            (d.get("total_memory_gb", 0) for d in detection["devices"]),
            default=0
        )

        if max_memory_gb == 0:
            return 4

        # Rough estimation: each sample uses ~(model_size * seq_len / 512) MB
        available_memory = max_memory_gb * target_memory_utilization - model_size_gb
        memory_per_sample = model_size_gb * sequence_length / 512 / 10  # rough estimate

        if memory_per_sample <= 0:
            return 4

        batch_size = int(available_memory / memory_per_sample)
        batch_size = max(1, min(batch_size, 64))  # Clamp to [1, 64]

        return batch_size

    @classmethod
    def recommend_training_mode(cls) -> str:
        """
        Recommend training mode based on hardware.

        Returns:
            One of: 'gpu', 'cpu', 'simulation'
        """
        detection = cls.detect()

        if detection["available"]:
            return "gpu"
        elif TORCH_AVAILABLE:
            return "cpu"
        else:
            return "simulation"

    @classmethod
    def get_training_device(cls) -> str:
        """
        Get the recommended training device string.

        Returns:
            Device string: 'cuda', 'cuda:0', 'mps', or 'cpu'
        """
        detection = cls.detect()

        if detection["backend"] == "cuda":
            if detection["device_count"] > 0:
                return "cuda:0"
            return "cuda"
        elif detection["backend"] == "mps":
            return "mps"
        else:
            return "cpu"

    @classmethod
    def clear_cache(cls) -> None:
        """Clear cached detection results."""
        cls._cached_detection = None

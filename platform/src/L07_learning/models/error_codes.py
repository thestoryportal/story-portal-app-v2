"""L07 Learning Layer - Error Codes (E7000-E7999)."""

from enum import Enum
from typing import Dict


class LearningErrorCode(Enum):
    """Error codes for L07 Learning Layer."""

    # Training Data Extraction (E7000-E7099)
    E7000 = ("Training data extraction failed", "critical")
    E7001 = ("Malformed execution trace", "warning")
    E7002 = ("Quality score unavailable", "warning")
    E7003 = ("Trace parsing timeout", "warning")
    E7004 = ("Inconsistent trace version", "error")
    E7005 = ("Training data contamination detected", "critical")

    # Example Filtering (E7100-E7199)
    E7100 = ("All examples filtered", "warning")
    E7101 = ("Insufficient diversity", "warning")
    E7102 = ("Quality signal inconsistent", "warning")
    E7103 = ("Outlier detection failed", "error")
    E7104 = ("Dataset size explosion", "warning")

    # Model Registry and Deployment (E7200-E7299)
    E7200 = ("Model artifact not found", "critical")
    E7201 = ("Signature verification failed", "critical")
    E7202 = ("Stage transition validation failed", "error")
    E7203 = ("Model version conflict", "error")
    E7204 = ("Model registration failed", "error")

    # RLHF and Reward Modeling (E7300-E7399)
    E7300 = ("Reward model training failed", "error")
    E7301 = ("Insufficient reward signal variance", "warning")
    E7302 = ("PPO policy divergence exceeded", "error")
    E7303 = ("Reward hacking detected", "critical")
    E7304 = ("Rollout generation failed", "error")

    # Monitoring and Reliability (E7400-E7499)
    E7400 = ("Training metrics unavailable", "warning")
    E7401 = ("Negative feedback loop detected", "critical")
    E7402 = ("Circuit breaker opened", "warning")
    E7403 = ("Model quality degradation", "warning")

    # Configuration (E7500-E7599)
    E7500 = ("Invalid configuration", "error")
    E7501 = ("Missing required configuration", "error")
    E7502 = ("Configuration validation failed", "error")

    # Knowledge Distillation (E7600-E7699)
    E7600 = ("Distillation failed", "error")
    E7601 = ("Student model underperforming", "warning")
    E7602 = ("Teacher model unavailable", "error")

    # Cost and Resources (E7700-E7799)
    E7700 = ("GPU out of memory", "error")
    E7701 = ("Training cost exceeded budget", "warning")
    E7702 = ("Resource quota exceeded", "error")
    E7703 = ("Training timeout", "warning")

    # Observability (E7800-E7899)
    E7800 = ("Metrics export failed", "warning")
    E7801 = ("Logging system unavailable", "warning")
    E7802 = ("Alert delivery failed", "warning")

    # System and Integration (E7900-E7999)
    E7900 = ("L01 integration failed", "error")
    E7901 = ("L02 integration failed", "error")
    E7902 = ("L04 integration failed", "error")
    E7903 = ("L06 integration failed", "error")
    E7904 = ("Database connection failed", "critical")
    E7905 = ("Model loading failed", "error")
    E7906 = ("Training divergence", "error")
    E7907 = ("Validation failed", "warning")
    E7908 = ("Checkpoint save failed", "critical")

    def __init__(self, message: str, severity: str):
        self.message = message
        self.severity = severity

    def to_dict(self) -> Dict[str, str]:
        """Convert error code to dictionary."""
        return {
            "code": self.name,
            "message": self.message,
            "severity": self.severity
        }


class LearningLayerException(Exception):
    """Base exception for L07 Learning Layer."""

    def __init__(self, error_code: LearningErrorCode, details: str = ""):
        self.error_code = error_code
        self.details = details
        super().__init__(f"{error_code.name}: {error_code.message}. {details}")

    def to_dict(self) -> Dict:
        """Convert exception to dictionary."""
        return {
            "error_code": self.error_code.name,
            "message": self.error_code.message,
            "severity": self.error_code.severity,
            "details": self.details
        }


class TrainingDataExtractionError(LearningLayerException):
    """Error during training data extraction."""
    pass


class ExampleFilteringError(LearningLayerException):
    """Error during example filtering."""
    pass


class ModelRegistryError(LearningLayerException):
    """Error in model registry operations."""
    pass


class RLHFError(LearningLayerException):
    """Error in RLHF pipeline."""
    pass


class TrainingError(LearningLayerException):
    """Error during model training."""
    pass


class ValidationError(LearningLayerException):
    """Error during model validation."""
    pass


class IntegrationError(LearningLayerException):
    """Error in cross-layer integration."""
    pass

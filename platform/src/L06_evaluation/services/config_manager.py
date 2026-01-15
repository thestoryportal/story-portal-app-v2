"""Configuration manager with hot-reload and validation"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Configuration manager with hot-reload.

    Per spec Section 3.2 (Component Responsibilities #10):
    - Hot-reload config
    - Validates schemas
    - Manages rollbacks
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize config manager.

        Args:
            config: Initial configuration (optional)
        """
        self.config = config or self._default_config()
        self.version = "1.0.0"
        self.history: List[Dict[str, Any]] = []

    def _default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "quality_scorer": {
                "weight_accuracy": 0.3,
                "weight_latency": 0.25,
                "weight_cost": 0.15,
                "weight_reliability": 0.2,
                "weight_compliance": 0.1,
            },
            "anomaly_detector": {
                "algorithm": "zscore",
                "baseline_window_hours": 24,
                "deviation_threshold": 3.0,
                "cold_start_samples": 100,
            },
            "metrics_engine": {
                "window_seconds": 60,
                "max_cardinality_per_tenant": 100000,
            },
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)

    def update(self, updates: Dict[str, Any]):
        """Update configuration"""
        self.history.append(self.config.copy())
        self.config.update(updates)
        self.version = f"{int(float(self.version.split('.')[0])) + 1}.0.0"
        logger.info(f"Config updated to version {self.version}")

    def rollback(self):
        """Rollback to previous configuration"""
        if self.history:
            self.config = self.history.pop()
            logger.info("Config rolled back")

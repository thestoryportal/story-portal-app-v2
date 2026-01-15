"""Configuration module for L12 Natural Language Interface.

This package provides centralized configuration management:
- L12Settings: Main configuration class with environment variable support
- get_settings(): Global singleton accessor
- reset_settings(): Settings reset for testing
"""

from .settings import L12Settings, get_settings, reset_settings

__all__ = [
    "L12Settings",
    "get_settings",
    "reset_settings",
]

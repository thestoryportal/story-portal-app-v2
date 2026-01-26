"""L05 Planning Layer - Health Check Utility."""

from typing import Dict, Any


def get_health_status() -> Dict[str, Any]:
    """Return health status for the L05 Planning Layer."""
    return {
        "status": "ok",
        "layer": "L05"
    }

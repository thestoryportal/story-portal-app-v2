"""L05 Planning Layer - Health Check Tests."""

import pytest
from ..utils.health import get_health_status


class TestHealthCheck:
    """Test health check utility."""

    def test_get_health_status_returns_dict(self):
        result = get_health_status()
        assert isinstance(result, dict)

    def test_get_health_status_status_is_ok(self):
        result = get_health_status()
        assert result["status"] == "ok"

    def test_get_health_status_layer_is_l05(self):
        result = get_health_status()
        assert result["layer"] == "L05"

    def test_get_health_status_exact_return(self):
        result = get_health_status()
        assert result == {"status": "ok", "layer": "L05"}

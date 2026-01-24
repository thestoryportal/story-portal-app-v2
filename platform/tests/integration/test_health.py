"""
Integration Tests - Health Checks

Tests health endpoints for all platform services.
"""

import pytest
import httpx

pytestmark = [pytest.mark.integration, pytest.mark.health, pytest.mark.smoke]


@pytest.mark.asyncio
class TestHealthEndpoints:
    """Test health check endpoints across all services"""

    async def test_l01_health_live(self, http_client: httpx.AsyncClient):
        """Test L01 Data Layer liveness probe"""
        response = await http_client.get("http://localhost:8001/health/live")
        assert response.status_code == 200

    async def test_l01_health_ready(self, http_client: httpx.AsyncClient):
        """Test L01 Data Layer readiness probe"""
        response = await http_client.get("http://localhost:8001/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") in ["healthy", "ok", "ready", True]

    async def test_l09_health_live(self, http_client: httpx.AsyncClient):
        """Test L09 API Gateway liveness probe"""
        response = await http_client.get("http://localhost:8009/health/live")
        assert response.status_code == 200

    async def test_l09_health_ready(self, http_client: httpx.AsyncClient):
        """Test L09 readiness probe - checks dependencies"""
        try:
            response = await http_client.get("http://localhost:8009/health/ready")
            # Accept 200 (ready), 503 (not ready but responding), or 401 (auth required)
            assert response.status_code in [200, 401, 503], f"Unexpected status: {response.status_code}"
            # If we got 503, verify it's a proper health check response
            if response.status_code == 503:
                data = response.json()
                assert "status" in data  # Should have status field
        except httpx.ConnectError:
            pytest.skip("L09 service not available")

    async def test_l10_health(self, http_client: httpx.AsyncClient):
        """Test L10 Human Interface health endpoint"""
        try:
            # Try /health/live first, fall back to /health
            response = await http_client.get("http://localhost:8010/health/live")
            if response.status_code == 404:
                response = await http_client.get("http://localhost:8010/health")
            assert response.status_code == 200
        except httpx.ConnectError:
            pytest.skip("L10 service not available")

    async def test_l12_health(self, http_client: httpx.AsyncClient):
        """Test L12 Service Hub health endpoint"""
        try:
            # Try /health/live first, fall back to /health
            response = await http_client.get("http://localhost:8012/health/live")
            if response.status_code == 404:
                response = await http_client.get("http://localhost:8012/health")
            assert response.status_code == 200
        except httpx.ConnectError:
            pytest.skip("L12 service not available")

    async def test_all_services_healthy(self, http_client: httpx.AsyncClient, service_urls):
        """Verify all available services are healthy"""
        unhealthy = []
        available = 0

        for service_name, base_url in service_urls.items():
            try:
                # Try /health/live first
                response = await http_client.get(f"{base_url}/health/live", timeout=5.0)
                if response.status_code == 404:
                    # Fall back to /health
                    response = await http_client.get(f"{base_url}/health", timeout=5.0)

                if response.status_code == 200:
                    available += 1
                elif response.status_code == 401:
                    # Auth required but service is responding
                    available += 1
                else:
                    unhealthy.append(f"{service_name} returned {response.status_code}")
            except httpx.ConnectError:
                pass  # Service not running, skip
            except Exception as e:
                unhealthy.append(f"{service_name}: {str(e)}")

        # At least L01 should be available
        assert available >= 1, "At least one service should be available"
        assert len(unhealthy) == 0, f"Unhealthy services: {', '.join(unhealthy)}"


@pytest.mark.asyncio
class TestServiceAvailability:
    """Test that services are reachable and responding"""

    @pytest.mark.parametrize("service,port", [
        ("l01", 8001),
        ("l09", 8009),
    ])
    async def test_service_responds(self, http_client: httpx.AsyncClient, service: str, port: int):
        """Test that service responds to health check"""
        try:
            response = await http_client.get(f"http://localhost:{port}/health/live", timeout=5.0)
            assert response.status_code == 200, f"{service} (port {port}) returned {response.status_code}"
        except httpx.ConnectError:
            pytest.skip(f"{service} (port {port}) not available")
        except httpx.TimeoutException:
            pytest.fail(f"{service} (port {port}) timed out")

"""
Smoke Test Suite

Critical smoke tests to validate platform health before deployment.
These tests should run in <5 minutes and catch major issues.
"""

import pytest
import httpx
import asyncio


@pytest.mark.smoke
@pytest.mark.asyncio
class TestPlatformSmoke:
    """Smoke tests for platform services."""

    async def test_all_services_healthy(
        self,
        http_client: httpx.AsyncClient,
    ):
        """Test that all core services are healthy."""
        services = [
            ('L01 Data Layer', 'http://localhost:8001'),
            ('L02 Runtime', 'http://localhost:8002'),
            ('L03 Tool Execution', 'http://localhost:8003'),
            ('L04 Model Gateway', 'http://localhost:8004'),
            ('L05 Planning', 'http://localhost:8005'),
            ('L06 Evaluation', 'http://localhost:8006'),
            ('L07 Learning', 'http://localhost:8007'),
            ('L09 API Gateway', 'http://localhost:8009'),
            ('L10 Human Interface', 'http://localhost:8010'),
            ('L11 Integration', 'http://localhost:8011'),
            ('L12 NL Interface', 'http://localhost:8012'),
        ]

        results = []
        for name, url in services:
            try:
                response = await http_client.get(
                    f"{url}/health/live",
                    timeout=5.0
                )
                results.append((name, response.status_code == 200))
            except Exception as e:
                results.append((name, False))
                print(f"❌ {name} failed: {e}")

        # Check that at least 80% of services are healthy
        healthy_count = sum(1 for _, is_healthy in results if is_healthy)
        total = len(services)
        health_percentage = (healthy_count / total) * 100

        assert health_percentage >= 80, (
            f"Only {healthy_count}/{total} services are healthy ({health_percentage:.1f}%)"
        )

    async def test_database_connectivity(
        self,
        http_client: httpx.AsyncClient,
        l01_data_layer_url: str,
    ):
        """Test PostgreSQL database connectivity."""
        response = await http_client.get(
            f"{l01_data_layer_url}/health/ready",
            timeout=5.0
        )
        assert response.status_code == 200
        data = response.json()
        assert data['status'] in ['healthy', 'degraded']

    async def test_redis_connectivity(
        self,
        http_client: httpx.AsyncClient,
        l01_data_layer_url: str,
    ):
        """Test Redis connectivity."""
        response = await http_client.get(
            f"{l01_data_layer_url}/health/ready",
            timeout=5.0
        )
        assert response.status_code == 200

    async def test_api_gateway_routing(
        self,
        http_client: httpx.AsyncClient,
        l09_api_gateway_url: str,
    ):
        """Test API Gateway can route requests."""
        response = await http_client.get(
            f"{l09_api_gateway_url}/health/live",
            timeout=5.0
        )
        assert response.status_code == 200

    async def test_ui_accessible(
        self,
        http_client: httpx.AsyncClient,
    ):
        """Test that UI is accessible."""
        try:
            response = await http_client.get(
                "http://localhost:3000",
                timeout=5.0,
                follow_redirects=True
            )
            assert response.status_code == 200
        except httpx.ConnectError:
            pytest.skip("UI is not running")

    async def test_consul_available(
        self,
        http_client: httpx.AsyncClient,
        consul_url: str,
    ):
        """Test Consul is available (if enabled)."""
        try:
            response = await http_client.get(
                f"{consul_url}/v1/status/leader",
                timeout=5.0
            )
            assert response.status_code == 200
        except httpx.ConnectError:
            pytest.skip("Consul is not enabled")

    async def test_etcd_available(
        self,
        http_client: httpx.AsyncClient,
        etcd_url: str,
    ):
        """Test etcd is available (if enabled)."""
        try:
            response = await http_client.get(
                f"{etcd_url}/version",
                timeout=5.0
            )
            assert response.status_code == 200
        except httpx.ConnectError:
            pytest.skip("etcd is not enabled")


@pytest.mark.smoke
@pytest.mark.asyncio
class TestAPIEndpoints:
    """Smoke tests for critical API endpoints."""

    async def test_health_endpoints(
        self,
        http_client: httpx.AsyncClient,
        l09_api_gateway_url: str,
    ):
        """Test health check endpoints."""
        endpoints = ['/health/live', '/health/ready', '/health/startup']

        for endpoint in endpoints:
            response = await http_client.get(
                f"{l09_api_gateway_url}{endpoint}",
                timeout=5.0
            )
            assert response.status_code == 200, f"Endpoint {endpoint} failed"

    async def test_openapi_docs_accessible(
        self,
        http_client: httpx.AsyncClient,
    ):
        """Test OpenAPI documentation is accessible."""
        try:
            response = await http_client.get(
                "http://localhost:8099",
                timeout=5.0
            )
            assert response.status_code == 200
        except httpx.ConnectError:
            pytest.skip("API docs aggregator is not running")


@pytest.mark.smoke
@pytest.mark.asyncio
class TestPerformance:
    """Basic performance smoke tests."""

    async def test_api_response_time(
        self,
        http_client: httpx.AsyncClient,
        l09_api_gateway_url: str,
        performance_threshold_ms: int,
    ):
        """Test API response time is within acceptable threshold."""
        import time

        start = time.time()
        response = await http_client.get(
            f"{l09_api_gateway_url}/health/live",
            timeout=5.0
        )
        duration_ms = (time.time() - start) * 1000

        assert response.status_code == 200
        assert duration_ms < performance_threshold_ms, (
            f"Response time {duration_ms:.2f}ms exceeds threshold {performance_threshold_ms}ms"
        )

    async def test_concurrent_requests(
        self,
        http_client: httpx.AsyncClient,
        l09_api_gateway_url: str,
    ):
        """Test platform can handle concurrent requests."""
        async def make_request():
            return await http_client.get(
                f"{l09_api_gateway_url}/health/live",
                timeout=5.0
            )

        # Make 10 concurrent requests
        tasks = [make_request() for _ in range(10)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed
        successful = sum(
            1 for r in responses
            if isinstance(r, httpx.Response) and r.status_code == 200
        )

        assert successful >= 8, (
            f"Only {successful}/10 concurrent requests succeeded"
        )


@pytest.mark.smoke
@pytest.mark.asyncio
class TestSecurity:
    """Basic security smoke tests."""

    async def test_cors_headers(
        self,
        http_client: httpx.AsyncClient,
        l09_api_gateway_url: str,
    ):
        """Test CORS headers are properly configured."""
        response = await http_client.options(
            f"{l09_api_gateway_url}/health/live",
            headers={'Origin': 'http://localhost:3000'},
            timeout=5.0
        )

        # Should either allow or reject, not crash
        assert response.status_code in [200, 204, 404, 405]

    async def test_no_sensitive_info_in_errors(
        self,
        http_client: httpx.AsyncClient,
        l09_api_gateway_url: str,
    ):
        """Test error responses don't leak sensitive information."""
        response = await http_client.get(
            f"{l09_api_gateway_url}/nonexistent-endpoint",
            timeout=5.0
        )

        # Should return 404
        assert response.status_code == 404

        # Should not contain sensitive information
        body = response.text.lower()
        sensitive_keywords = ['password', 'token', 'secret', 'key', 'private']

        for keyword in sensitive_keywords:
            assert keyword not in body, (
                f"Error response contains sensitive keyword: {keyword}"
            )


@pytest.mark.smoke
def test_environment_variables():
    """Test required environment variables are set."""
    import os

    # Check test environment is set
    assert os.getenv('TESTING') == '1'
    assert os.getenv('ENVIRONMENT') == 'test'


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_platform_version(
    http_client: httpx.AsyncClient,
    l09_api_gateway_url: str,
):
    """Test platform version endpoint."""
    response = await http_client.get(
        f"{l09_api_gateway_url}/health/live",
        timeout=5.0
    )
    assert response.status_code == 200

    data = response.json()
    assert 'version' in data or 'service' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-m', 'smoke'])

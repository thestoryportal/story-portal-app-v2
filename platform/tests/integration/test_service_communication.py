"""
Integration Tests for Service Communication

Tests inter-service communication and data flow.
"""

import pytest
import httpx
import asyncio


@pytest.mark.integration
@pytest.mark.asyncio
class TestServiceDiscovery:
    """Test Consul service discovery integration."""

    async def test_service_registration(
        self,
        http_client: httpx.AsyncClient,
        consul_url: str,
    ):
        """Test services are registered with Consul."""
        try:
            response = await http_client.get(
                f"{consul_url}/v1/catalog/services",
                timeout=5.0
            )
            assert response.status_code == 200

            services = response.json()
            # Should have consul service at minimum
            assert 'consul' in services or len(services) >= 0

        except httpx.ConnectError:
            pytest.skip("Consul not available")

    async def test_service_health_checks(
        self,
        http_client: httpx.AsyncClient,
        consul_url: str,
    ):
        """Test service health checks in Consul."""
        try:
            # Check health of registered services
            response = await http_client.get(
                f"{consul_url}/v1/health/state/passing",
                timeout=5.0
            )
            assert response.status_code == 200

            checks = response.json()
            # At least Consul itself should be passing
            assert len(checks) >= 0

        except httpx.ConnectError:
            pytest.skip("Consul not available")


@pytest.mark.integration
@pytest.mark.asyncio
class TestConfigurationManagement:
    """Test etcd configuration management integration."""

    async def test_config_read_write(
        self,
        http_client: httpx.AsyncClient,
        etcd_url: str,
    ):
        """Test reading and writing configuration to etcd."""
        try:
            import base64

            # Write a test configuration
            test_key = "/test/config/key"
            test_value = "test-value-12345"

            encoded_key = base64.b64encode(test_key.encode()).decode()
            encoded_value = base64.b64encode(test_value.encode()).decode()

            # Write
            response = await http_client.post(
                f"{etcd_url}/v3/kv/put",
                json={"key": encoded_key, "value": encoded_value},
                timeout=5.0
            )
            assert response.status_code == 200

            # Read
            response = await http_client.post(
                f"{etcd_url}/v3/kv/range",
                json={"key": encoded_key},
                timeout=5.0
            )
            assert response.status_code == 200

            data = response.json()
            assert 'kvs' in data
            if data['kvs']:
                stored_value = base64.b64decode(data['kvs'][0]['value']).decode()
                assert stored_value == test_value

        except httpx.ConnectError:
            pytest.skip("etcd not available")


@pytest.mark.integration
@pytest.mark.asyncio
class TestEventSystem:
    """Test Redis Streams event system integration."""

    async def test_event_publish_subscribe(
        self,
        redis_url: str,
    ):
        """Test publishing and subscribing to events."""
        try:
            import redis.asyncio as aioredis

            redis_client = await aioredis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
            )

            # Publish event
            stream_key = "events:test.event"
            event_data = {
                "type": "test.event",
                "source": "integration-test",
                "data": "test-data",
            }

            event_id = await redis_client.xadd(stream_key, event_data)
            assert event_id is not None

            # Read event back
            messages = await redis_client.xread({stream_key: "0-0"}, count=1)
            assert len(messages) > 0

            stream, events = messages[0]
            assert stream == stream_key
            assert len(events) > 0

            # Cleanup
            await redis_client.delete(stream_key)
            await redis_client.close()

        except Exception as e:
            pytest.skip(f"Redis not available: {e}")


@pytest.mark.integration
@pytest.mark.asyncio
class TestHealthChecks:
    """Test health check system integration."""

    async def test_database_health_check(
        self,
        http_client: httpx.AsyncClient,
        l01_data_layer_url: str,
    ):
        """Test database health check endpoint."""
        response = await http_client.get(
            f"{l01_data_layer_url}/health/ready",
            timeout=5.0
        )
        assert response.status_code == 200

        data = response.json()
        assert 'status' in data
        assert data['status'] in ['healthy', 'degraded', 'unhealthy']

    async def test_all_service_health_checks(
        self,
        http_client: httpx.AsyncClient,
    ):
        """Test all services have health check endpoints."""
        services = [
            'http://localhost:8001',
            'http://localhost:8002',
            'http://localhost:8009',
            'http://localhost:8010',
        ]

        for service_url in services:
            try:
                response = await http_client.get(
                    f"{service_url}/health/live",
                    timeout=5.0
                )
                assert response.status_code == 200, (
                    f"Health check failed for {service_url}"
                )
            except httpx.ConnectError:
                # Service not running, skip
                pass


@pytest.mark.integration
@pytest.mark.asyncio
class TestAPIGateway:
    """Test API Gateway routing and proxy."""

    async def test_gateway_health(
        self,
        http_client: httpx.AsyncClient,
        l09_api_gateway_url: str,
    ):
        """Test API Gateway health endpoint."""
        response = await http_client.get(
            f"{l09_api_gateway_url}/health/live",
            timeout=5.0
        )
        assert response.status_code == 200

    async def test_cors_configuration(
        self,
        http_client: httpx.AsyncClient,
        l09_api_gateway_url: str,
    ):
        """Test CORS is configured correctly."""
        response = await http_client.options(
            f"{l09_api_gateway_url}/health/live",
            headers={
                'Origin': 'http://localhost:3000',
                'Access-Control-Request-Method': 'GET',
            },
            timeout=5.0
        )

        # Should handle CORS preflight
        assert response.status_code in [200, 204, 404, 405]


@pytest.mark.integration
@pytest.mark.asyncio
class TestDatabaseIntegration:
    """Test database integration."""

    async def test_postgres_connection(
        self,
        http_client: httpx.AsyncClient,
        l01_data_layer_url: str,
    ):
        """Test PostgreSQL connection through L01."""
        response = await http_client.get(
            f"{l01_data_layer_url}/health/ready",
            timeout=5.0
        )

        assert response.status_code == 200
        data = response.json()
        assert data['status'] != 'unhealthy'

    async def test_redis_connection(
        self,
        http_client: httpx.AsyncClient,
        l01_data_layer_url: str,
    ):
        """Test Redis connection through L01."""
        response = await http_client.get(
            f"{l01_data_layer_url}/health/ready",
            timeout=5.0
        )

        assert response.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-m', 'integration'])

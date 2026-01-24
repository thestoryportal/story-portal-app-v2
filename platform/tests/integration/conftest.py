"""
Integration Test Fixtures

Shared fixtures for integration tests that require running services.
"""

import pytest
import pytest_asyncio
import httpx
import asyncio
import os
from typing import AsyncGenerator, Dict, Any

# Service URLs (from docker-compose)
BASE_URLS = {
    "l01": "http://localhost:8001",
    "l02": "http://localhost:8002",
    "l03": "http://localhost:8003",
    "l04": "http://localhost:8004",
    "l05": "http://localhost:8005",
    "l06": "http://localhost:8006",
    "l07": "http://localhost:8007",
    "l09": "http://localhost:8009",
    "l10": "http://localhost:8010",
    "l11": "http://localhost:8011",
    "l12": "http://localhost:8012",
}

# Test API key for authentication (matches L01 container dev key)
TEST_API_KEY = os.getenv("TEST_API_KEY", "dev_key_local_ONLY")

# Default headers for authenticated requests
DEFAULT_HEADERS = {
    "X-API-Key": TEST_API_KEY,
    "Content-Type": "application/json",
}


@pytest_asyncio.fixture(scope="function")
async def http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide an async HTTP client for making requests to services"""
    async with httpx.AsyncClient(timeout=30.0, headers=DEFAULT_HEADERS) as client:
        yield client


@pytest.fixture(scope="session")
def service_urls() -> Dict[str, str]:
    """Provide service URLs for testing"""
    return BASE_URLS


@pytest.fixture(scope="function")
async def wait_for_services(http_client: httpx.AsyncClient, service_urls: Dict[str, str]):
    """Wait for all services to be healthy before running tests"""
    max_retries = 30
    retry_delay = 1.0

    for service_name, base_url in service_urls.items():
        health_url = f"{base_url}/health"

        for attempt in range(max_retries):
            try:
                response = await http_client.get(health_url)
                if response.status_code == 200:
                    print(f"✓ {service_name} is healthy")
                    break
            except (httpx.ConnectError, httpx.TimeoutException):
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    pytest.skip(f"Service {service_name} not available at {base_url}")


@pytest.fixture(scope="function")
def l01_client(http_client: httpx.AsyncClient, service_urls: Dict[str, str]):
    """Provide HTTP client configured for L01 Data Layer"""
    class L01Client:
        def __init__(self, client: httpx.AsyncClient, base_url: str):
            self.client = client
            self.base_url = base_url

        async def health(self):
            return await self.client.get(f"{self.base_url}/health")

        async def get_agents(self):
            return await self.client.get(f"{self.base_url}/api/v1/agents")

        async def create_agent(self, data: Dict[str, Any]):
            return await self.client.post(f"{self.base_url}/api/v1/agents", json=data)

    return L01Client(http_client, service_urls["l01"])


@pytest.fixture(scope="function")
def l09_client(http_client: httpx.AsyncClient, service_urls: Dict[str, str]):
    """Provide HTTP client configured for L09 API Gateway"""
    class L09Client:
        def __init__(self, client: httpx.AsyncClient, base_url: str):
            self.client = client
            self.base_url = base_url

        async def health(self):
            return await self.client.get(f"{self.base_url}/health")

        async def health_live(self):
            return await self.client.get(f"{self.base_url}/health/live")

        async def health_ready(self):
            return await self.client.get(f"{self.base_url}/health/ready")

        async def health_detailed(self):
            return await self.client.get(f"{self.base_url}/health/detailed")

    return L09Client(http_client, service_urls["l09"])


@pytest.fixture(scope="function")
def l10_client(http_client: httpx.AsyncClient, service_urls: Dict[str, str]):
    """Provide HTTP client configured for L10 Human Interface"""
    class L10Client:
        def __init__(self, client: httpx.AsyncClient, base_url: str):
            self.client = client
            self.base_url = base_url

        async def health(self):
            return await self.client.get(f"{self.base_url}/health")

        async def get_dashboard(self):
            return await self.client.get(f"{self.base_url}/api/dashboard")

    return L10Client(http_client, service_urls["l10"])


@pytest.fixture(scope="function")
def l12_client(http_client: httpx.AsyncClient, service_urls: Dict[str, str]):
    """Provide HTTP client configured for L12 Service Hub"""
    class L12Client:
        def __init__(self, client: httpx.AsyncClient, base_url: str):
            self.client = client
            self.base_url = base_url

        async def health(self):
            return await self.client.get(f"{self.base_url}/health")

        async def get_services(self):
            return await self.client.get(f"{self.base_url}/api/services")

    return L12Client(http_client, service_urls["l12"])


# Database fixtures
@pytest.fixture(scope="session")
def db_connection_string() -> str:
    """Provide database connection string for tests"""
    import os
    return os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/agentic_platform"
    )


# Redis fixtures
@pytest.fixture(scope="session")
def redis_url() -> str:
    """Provide Redis URL for tests"""
    import os
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")

"""
Pytest Configuration and Fixtures

Shared fixtures for all tests in the platform.
"""

import pytest
import asyncio
import httpx
from typing import AsyncGenerator, Generator
import os

# Set test environment
os.environ['TESTING'] = '1'
os.environ['ENVIRONMENT'] = 'test'


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide an async HTTP client for tests."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        yield client


@pytest.fixture
def api_base_url() -> str:
    """Get API Gateway base URL."""
    return os.getenv('API_GATEWAY_URL', 'http://localhost:8009')


@pytest.fixture
def mock_correlation_id() -> str:
    """Provide a mock correlation ID."""
    return "test-correlation-id-12345"


@pytest.fixture
def mock_headers(mock_correlation_id: str) -> dict:
    """Provide mock HTTP headers with correlation ID."""
    return {
        'X-Correlation-ID': mock_correlation_id,
        'Content-Type': 'application/json',
    }


@pytest.fixture
async def health_check(http_client: httpx.AsyncClient, api_base_url: str) -> dict:
    """
    Check if services are healthy before running tests.
    Skip tests if services are not available.
    """
    try:
        response = await http_client.get(f"{api_base_url}/health/live", timeout=5.0)
        if response.status_code == 200:
            return response.json()
        pytest.skip("API Gateway is not healthy")
    except Exception:
        pytest.skip("API Gateway is not available")


# Service-specific fixtures

@pytest.fixture
def l01_data_layer_url() -> str:
    """L01 Data Layer URL."""
    return os.getenv('L01_URL', 'http://localhost:8001')


@pytest.fixture
def l02_runtime_url() -> str:
    """L02 Runtime URL."""
    return os.getenv('L02_URL', 'http://localhost:8002')


@pytest.fixture
def l09_api_gateway_url() -> str:
    """L09 API Gateway URL."""
    return os.getenv('L09_URL', 'http://localhost:8009')


@pytest.fixture
def l10_human_interface_url() -> str:
    """L10 Human Interface URL."""
    return os.getenv('L10_URL', 'http://localhost:8010')


# Database fixtures

@pytest.fixture
def postgres_connection_string() -> str:
    """PostgreSQL connection string for tests."""
    return os.getenv(
        'TEST_DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/agentic_platform_test'
    )


@pytest.fixture
def redis_url() -> str:
    """Redis URL for tests."""
    return os.getenv('TEST_REDIS_URL', 'redis://localhost:6379/1')


# Consul and etcd fixtures

@pytest.fixture
def consul_url() -> str:
    """Consul URL for tests."""
    return os.getenv('TEST_CONSUL_URL', 'http://localhost:8500')


@pytest.fixture
def etcd_url() -> str:
    """etcd URL for tests."""
    return os.getenv('TEST_ETCD_URL', 'http://localhost:2379')


# Performance testing fixtures

@pytest.fixture
def performance_threshold_ms() -> int:
    """Maximum acceptable response time in milliseconds."""
    return 500


# Helper functions

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )
    config.addinivalue_line(
        "markers", "security: mark test as security test"
    )
    config.addinivalue_line(
        "markers", "smoke: mark test as smoke test"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location."""
    for item in items:
        # Add integration marker to integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Add unit marker to unit tests
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Add performance marker to performance tests
        if "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)

        # Add security marker to security tests
        if "security" in str(item.fspath):
            item.add_marker(pytest.mark.security)

        # Add smoke marker to smoke tests
        if "smoke" in str(item.fspath):
            item.add_marker(pytest.mark.smoke)

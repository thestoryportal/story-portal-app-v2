"""Configuration and fixtures for E2E tests."""
import pytest


@pytest.fixture
def api_base_url():
    """Base URL for API Gateway."""
    return "http://localhost:8000"


@pytest.fixture
def api_key():
    """Test API key for authentication."""
    return "test-key-12345678901234567890123456789012"


@pytest.fixture
def api_headers(api_key):
    """Common headers for API requests."""
    return {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }

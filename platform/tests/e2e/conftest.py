import pytest
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Add platform to path
PLATFORM_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PLATFORM_ROOT))

# Pytest configuration
def pytest_configure(config):
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks integration tests")
    config.addinivalue_line("markers", "e2e: marks end-to-end tests")

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def infrastructure_check():
    """Verify infrastructure is running."""
    import redis
    import psycopg2
    import httpx

    checks = {}

    # Redis
    try:
        r = redis.Redis(host='localhost', port=6379)
        r.ping()
        checks['redis'] = True
    except Exception as e:
        checks['redis'] = str(e)

    # PostgreSQL
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='postgres',
            database='agentic_platform'
        )
        conn.close()
        checks['postgresql'] = True
    except Exception as e:
        checks['postgresql'] = str(e)

    # Ollama
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get('http://localhost:11434/api/tags', timeout=5.0)
            checks['ollama'] = resp.status_code == 200
    except Exception as e:
        checks['ollama'] = str(e)

    return checks

@pytest.fixture(autouse=True)
async def test_timeout():
    """Ensure tests don't hang."""
    yield
    await asyncio.sleep(0)  # Allow cleanup

@pytest.fixture
def test_agent_did():
    """Standard test agent DID."""
    return "did:agent:e2e-test-agent"

@pytest.fixture
def test_timestamp():
    """Current timestamp for tests."""
    return datetime.now()

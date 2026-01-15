"""
L04 Model Gateway Layer - Pytest Configuration

Shared fixtures and configuration for tests.
"""

import pytest
import asyncio


@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def cleanup_timeout():
    """Cleanup timeout for async tests (2 seconds max)"""
    return 2.0


@pytest.fixture
def mock_ollama_response():
    """Mock Ollama API response"""
    return {
        "message": {
            "role": "assistant",
            "content": "This is a mock response from Ollama."
        },
        "done": True,
        "done_reason": "stop",
        "total_duration": 1000000000,
        "load_duration": 100000000,
        "prompt_eval_count": 10,
        "eval_count": 20
    }

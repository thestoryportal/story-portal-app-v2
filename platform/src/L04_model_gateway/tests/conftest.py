"""
L04 Model Gateway Layer - Pytest Configuration

Shared fixtures and configuration for tests.
"""

import pytest
import pytest_asyncio
import asyncio
from typing import AsyncIterator

from ..models import (
    InferenceRequest,
    Message,
    MessageRole,
    LogicalPrompt,
    ModelRequirements,
    RequestConstraints,
)

from .fixtures.mock_clients import (
    MockHTTPClient,
    MockHTTPResponse,
    MockStreamResponse,
    create_mock_anthropic_client,
    create_mock_openai_client,
)
from .fixtures.api_responses import (
    ANTHROPIC_RESPONSE_SUCCESS,
    ANTHROPIC_RESPONSE_STREAM,
    OPENAI_RESPONSE_SUCCESS,
    OPENAI_RESPONSE_STREAM,
)


# =============================================================================
# Event Loop Configuration
# =============================================================================

@pytest.fixture(scope="session")
def event_loop_policy():
    """Use the default event loop policy"""
    return asyncio.DefaultEventLoopPolicy()


# =============================================================================
# Mock HTTP Client Fixtures
# =============================================================================

@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic API client returning successful responses"""
    return create_mock_anthropic_client(success=True)


@pytest.fixture
def mock_anthropic_client_429():
    """Create a mock Anthropic API client returning rate limit errors"""
    return create_mock_anthropic_client(success=False, error_type="429")


@pytest.fixture
def mock_anthropic_client_401():
    """Create a mock Anthropic API client returning auth errors"""
    return create_mock_anthropic_client(success=False, error_type="401")


@pytest.fixture
def mock_anthropic_client_500():
    """Create a mock Anthropic API client returning server errors"""
    return create_mock_anthropic_client(success=False, error_type="500")


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI API client returning successful responses"""
    return create_mock_openai_client(success=True)


@pytest.fixture
def mock_openai_client_429():
    """Create a mock OpenAI API client returning rate limit errors"""
    return create_mock_openai_client(success=False, error_type="429")


@pytest.fixture
def mock_openai_client_401():
    """Create a mock OpenAI API client returning auth errors"""
    return create_mock_openai_client(success=False, error_type="401")


@pytest.fixture
def mock_openai_client_500():
    """Create a mock OpenAI API client returning server errors"""
    return create_mock_openai_client(success=False, error_type="500")


@pytest.fixture
def mock_httpx_client():
    """Create a generic mock httpx client"""
    return MockHTTPClient()


# =============================================================================
# Inference Request Fixtures
# =============================================================================

@pytest.fixture
def sample_message():
    """Create a sample user message"""
    return Message(role=MessageRole.USER, content="Hello, how are you?")


@pytest.fixture
def sample_messages():
    """Create a sample conversation"""
    return [
        Message(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
        Message(role=MessageRole.USER, content="Hello, how are you?"),
    ]


@pytest.fixture
def sample_inference_request(sample_messages):
    """Create a sample inference request"""
    return InferenceRequest.create(
        agent_did="did:key:test-agent-123",
        messages=sample_messages,
        system_prompt="You are a helpful assistant.",
        temperature=0.7,
        max_tokens=1000,
    )


@pytest.fixture
def sample_inference_request_streaming(sample_messages):
    """Create a sample inference request with streaming enabled"""
    return InferenceRequest.create(
        agent_did="did:key:test-agent-123",
        messages=sample_messages,
        system_prompt="You are a helpful assistant.",
        temperature=0.7,
        max_tokens=1000,
        enable_streaming=True,
    )


@pytest.fixture
def sample_inference_request_with_capabilities(sample_messages):
    """Create a sample inference request with specific capabilities"""
    return InferenceRequest.create(
        agent_did="did:key:test-agent-123",
        messages=sample_messages,
        system_prompt="You are a helpful assistant.",
        temperature=0.7,
        max_tokens=1000,
        capabilities=["vision", "tool_use"],
    )


# =============================================================================
# Test Utility Fixtures
# =============================================================================

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


@pytest.fixture
def mock_anthropic_response():
    """Mock Anthropic API response"""
    return ANTHROPIC_RESPONSE_SUCCESS


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response"""
    return OPENAI_RESPONSE_SUCCESS


@pytest.fixture
def mock_anthropic_stream_response():
    """Mock Anthropic streaming response"""
    return ANTHROPIC_RESPONSE_STREAM


@pytest.fixture
def mock_openai_stream_response():
    """Mock OpenAI streaming response"""
    return OPENAI_RESPONSE_STREAM


# =============================================================================
# Test Markers
# =============================================================================

def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "l04: mark test as L04 Model Gateway layer test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires running services)"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow (>30s execution)"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test (no external dependencies)"
    )

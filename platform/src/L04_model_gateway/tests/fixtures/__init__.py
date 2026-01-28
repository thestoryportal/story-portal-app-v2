"""
L04 Model Gateway Layer - Test Fixtures Package

Provides mock API responses and HTTP clients for provider testing.
"""

from .api_responses import (
    ANTHROPIC_RESPONSE_SUCCESS,
    ANTHROPIC_RESPONSE_STREAM,
    ANTHROPIC_RESPONSE_ERROR_429,
    ANTHROPIC_RESPONSE_ERROR_401,
    ANTHROPIC_RESPONSE_ERROR_500,
    OPENAI_RESPONSE_SUCCESS,
    OPENAI_RESPONSE_STREAM,
    OPENAI_RESPONSE_ERROR_429,
    OPENAI_RESPONSE_ERROR_401,
)

from .mock_clients import (
    MockHTTPResponse,
    MockHTTPClient,
    MockStreamResponse,
    create_mock_anthropic_client,
    create_mock_openai_client,
)

__all__ = [
    # Anthropic responses
    "ANTHROPIC_RESPONSE_SUCCESS",
    "ANTHROPIC_RESPONSE_STREAM",
    "ANTHROPIC_RESPONSE_ERROR_429",
    "ANTHROPIC_RESPONSE_ERROR_401",
    "ANTHROPIC_RESPONSE_ERROR_500",
    # OpenAI responses
    "OPENAI_RESPONSE_SUCCESS",
    "OPENAI_RESPONSE_STREAM",
    "OPENAI_RESPONSE_ERROR_429",
    "OPENAI_RESPONSE_ERROR_401",
    # Mock clients
    "MockHTTPResponse",
    "MockHTTPClient",
    "MockStreamResponse",
    "create_mock_anthropic_client",
    "create_mock_openai_client",
]

"""
L04 Model Gateway Layer - Mock HTTP Clients

Provides mock HTTP clients for testing provider adapters without
making actual API calls.
"""

import json
from typing import Any, Dict, List, Optional, AsyncIterator, Union
from dataclasses import dataclass, field
import asyncio

from . import api_responses


@dataclass
class MockHTTPResponse:
    """Mock HTTP response for testing"""
    status_code: int
    content: bytes = b""
    headers: Dict[str, str] = field(default_factory=dict)
    _json: Optional[dict] = None

    def json(self) -> dict:
        """Return JSON content"""
        if self._json is not None:
            return self._json
        return json.loads(self.content)

    def raise_for_status(self):
        """Raise exception for error status codes"""
        if self.status_code >= 400:
            import httpx
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=None,
                response=self
            )

    @property
    def text(self) -> str:
        """Return text content"""
        return self.content.decode("utf-8")


@dataclass
class MockStreamResponse:
    """Mock streaming HTTP response for SSE testing"""
    status_code: int = 200
    chunks: List[dict] = field(default_factory=list)
    headers: Dict[str, str] = field(default_factory=dict)

    async def aiter_lines(self) -> AsyncIterator[str]:
        """Iterate over SSE lines"""
        for chunk in self.chunks:
            yield f"data: {json.dumps(chunk)}"
            await asyncio.sleep(0.01)  # Small delay to simulate streaming

    async def aiter_bytes(self) -> AsyncIterator[bytes]:
        """Iterate over bytes"""
        for chunk in self.chunks:
            yield f"data: {json.dumps(chunk)}\n\n".encode()
            await asyncio.sleep(0.01)

    def raise_for_status(self):
        """Raise exception for error status codes"""
        if self.status_code >= 400:
            import httpx
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=None,
                response=self
            )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockHTTPClient:
    """Mock HTTP client for testing provider adapters"""

    def __init__(
        self,
        responses: Optional[Dict[str, MockHTTPResponse]] = None,
        stream_responses: Optional[Dict[str, MockStreamResponse]] = None,
        default_response: Optional[MockHTTPResponse] = None,
    ):
        """
        Initialize mock client.

        Args:
            responses: Dict mapping (method, path) tuples to responses
            stream_responses: Dict mapping (method, path) tuples to stream responses
            default_response: Default response if no matching path
        """
        self.responses = responses or {}
        self.stream_responses = stream_responses or {}
        self.default_response = default_response or MockHTTPResponse(
            status_code=200,
            content=b'{"status": "ok"}'
        )
        self.request_history: List[Dict[str, Any]] = []
        self.base_url = ""

    def _record_request(self, method: str, url: str, **kwargs):
        """Record request for later inspection"""
        self.request_history.append({
            "method": method,
            "url": url,
            "headers": kwargs.get("headers", {}),
            "json": kwargs.get("json"),
            "data": kwargs.get("data"),
        })

    def _get_response(self, method: str, url: str) -> MockHTTPResponse:
        """Get response for request"""
        key = (method.upper(), url)
        if key in self.responses:
            return self.responses[key]

        # Try path-only matching
        for (m, path), response in self.responses.items():
            if m == method.upper() and url.endswith(path):
                return response

        return self.default_response

    def _get_stream_response(self, method: str, url: str) -> MockStreamResponse:
        """Get streaming response for request"""
        key = (method.upper(), url)
        if key in self.stream_responses:
            return self.stream_responses[key]

        # Try path-only matching
        for (m, path), response in self.stream_responses.items():
            if m == method.upper() and url.endswith(path):
                return response

        return MockStreamResponse(status_code=200, chunks=[])

    async def post(
        self,
        url: str,
        json: Optional[dict] = None,
        data: Optional[bytes] = None,
        headers: Optional[dict] = None,
        timeout: Optional[int] = None,
    ) -> MockHTTPResponse:
        """Mock POST request"""
        self._record_request("POST", url, json=json, data=data, headers=headers)
        return self._get_response("POST", url)

    async def get(
        self,
        url: str,
        headers: Optional[dict] = None,
        timeout: Optional[int] = None,
    ) -> MockHTTPResponse:
        """Mock GET request"""
        self._record_request("GET", url, headers=headers)
        return self._get_response("GET", url)

    def stream(
        self,
        method: str,
        url: str,
        json: Optional[dict] = None,
        headers: Optional[dict] = None,
        timeout: Optional[int] = None,
    ) -> MockStreamResponse:
        """Mock streaming request"""
        self._record_request(method, url, json=json, headers=headers)
        return self._get_stream_response(method, url)

    async def aclose(self):
        """Close client (no-op for mock)"""
        pass

    def get_last_request(self) -> Optional[Dict[str, Any]]:
        """Get the most recent request"""
        return self.request_history[-1] if self.request_history else None

    def clear_history(self):
        """Clear request history"""
        self.request_history.clear()


def create_mock_anthropic_client(
    success: bool = True,
    error_type: Optional[str] = None,
    custom_response: Optional[dict] = None,
) -> MockHTTPClient:
    """
    Create a mock HTTP client configured for Anthropic API.

    Args:
        success: Whether requests should succeed
        error_type: Error type ("429", "401", "500", "400")
        custom_response: Custom response to return

    Returns:
        Configured MockHTTPClient
    """
    responses = {}
    stream_responses = {}

    if success and not error_type:
        # Success response
        response_data = custom_response or api_responses.ANTHROPIC_RESPONSE_SUCCESS
        responses[("POST", "/v1/messages")] = MockHTTPResponse(
            status_code=200,
            content=json.dumps(response_data).encode(),
            headers={"content-type": "application/json"}
        )

        # Streaming success
        stream_responses[("POST", "/v1/messages")] = MockStreamResponse(
            status_code=200,
            chunks=api_responses.ANTHROPIC_RESPONSE_STREAM,
            headers={"content-type": "text/event-stream"}
        )
    else:
        # Error responses
        error_map = {
            "429": (429, api_responses.ANTHROPIC_RESPONSE_ERROR_429),
            "401": (401, api_responses.ANTHROPIC_RESPONSE_ERROR_401),
            "500": (500, api_responses.ANTHROPIC_RESPONSE_ERROR_500),
            "400": (400, api_responses.ANTHROPIC_RESPONSE_ERROR_400),
        }

        status_code, error_data = error_map.get(error_type, (500, api_responses.ANTHROPIC_RESPONSE_ERROR_500))
        responses[("POST", "/v1/messages")] = MockHTTPResponse(
            status_code=status_code,
            content=json.dumps(error_data).encode(),
            headers={"content-type": "application/json"}
        )

    return MockHTTPClient(responses=responses, stream_responses=stream_responses)


def create_mock_openai_client(
    success: bool = True,
    error_type: Optional[str] = None,
    custom_response: Optional[dict] = None,
) -> MockHTTPClient:
    """
    Create a mock HTTP client configured for OpenAI API.

    Args:
        success: Whether requests should succeed
        error_type: Error type ("429", "401", "500", "400")
        custom_response: Custom response to return

    Returns:
        Configured MockHTTPClient
    """
    responses = {}
    stream_responses = {}

    if success and not error_type:
        # Success response
        response_data = custom_response or api_responses.OPENAI_RESPONSE_SUCCESS
        responses[("POST", "/chat/completions")] = MockHTTPResponse(
            status_code=200,
            content=json.dumps(response_data).encode(),
            headers={"content-type": "application/json"}
        )

        # Models endpoint for health check
        responses[("GET", "/models")] = MockHTTPResponse(
            status_code=200,
            content=json.dumps({"data": [{"id": "gpt-4o"}, {"id": "gpt-3.5-turbo"}]}).encode(),
            headers={"content-type": "application/json"}
        )

        # Streaming success
        stream_responses[("POST", "/chat/completions")] = MockStreamResponse(
            status_code=200,
            chunks=api_responses.OPENAI_RESPONSE_STREAM,
            headers={"content-type": "text/event-stream"}
        )
    else:
        # Error responses
        error_map = {
            "429": (429, api_responses.OPENAI_RESPONSE_ERROR_429),
            "401": (401, api_responses.OPENAI_RESPONSE_ERROR_401),
            "500": (500, api_responses.OPENAI_RESPONSE_ERROR_500),
            "400": (400, api_responses.OPENAI_RESPONSE_ERROR_400),
        }

        status_code, error_data = error_map.get(error_type, (500, api_responses.OPENAI_RESPONSE_ERROR_500))
        responses[("POST", "/chat/completions")] = MockHTTPResponse(
            status_code=status_code,
            content=json.dumps(error_data).encode(),
            headers={"content-type": "application/json"}
        )

    return MockHTTPClient(responses=responses, stream_responses=stream_responses)

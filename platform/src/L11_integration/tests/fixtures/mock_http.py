"""Mock HTTP client for testing."""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import json


@dataclass
class MockResponse:
    """Mock HTTP response."""

    status_code: int = 200
    content: bytes = b""
    headers: Dict[str, str] = field(default_factory=dict)
    _json: Optional[Dict[str, Any]] = None

    def json(self) -> Dict[str, Any]:
        """Return JSON response."""
        if self._json is not None:
            return self._json
        if self.content:
            return json.loads(self.content)
        return {}

    def raise_for_status(self) -> None:
        """Raise exception for error status codes."""
        if self.status_code >= 400:
            raise MockHTTPStatusError(self)


class MockHTTPStatusError(Exception):
    """Mock HTTP status error."""

    def __init__(self, response: MockResponse):
        self.response = response
        super().__init__(f"HTTP {response.status_code}")


class MockTimeoutException(Exception):
    """Mock timeout exception."""
    pass


class MockConnectError(Exception):
    """Mock connection error."""
    pass


class MockHTTPClient:
    """Mock HTTP client for testing."""

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self._responses: Dict[Tuple[str, str], MockResponse] = {}
        self._requests: List[Dict[str, Any]] = []
        self._default_response: Optional[MockResponse] = None
        self._closed = False

    def add_response(
        self,
        method: str,
        url_pattern: str,
        response: Optional[Dict[str, Any]] = None,
        status_code: int = 200,
    ) -> None:
        """Add a mock response for a method/URL pattern."""
        self._responses[(method.upper(), url_pattern)] = MockResponse(
            status_code=status_code,
            _json=response or {},
        )

    def set_default_response(
        self,
        response: Optional[Dict[str, Any]] = None,
        status_code: int = 200,
    ) -> None:
        """Set default response for unmatched requests."""
        self._default_response = MockResponse(
            status_code=status_code,
            _json=response or {},
        )

    def set_timeout_for(self, method: str, url_pattern: str) -> None:
        """Set a request to timeout."""
        self._responses[(method.upper(), url_pattern)] = "TIMEOUT"

    def set_connect_error_for(self, method: str, url_pattern: str) -> None:
        """Set a request to fail with connection error."""
        self._responses[(method.upper(), url_pattern)] = "CONNECT_ERROR"

    def _find_response(self, method: str, url: str) -> Any:
        """Find matching response for request."""
        # Exact match first
        key = (method.upper(), url)
        if key in self._responses:
            return self._responses[key]

        # Pattern match (check if URL contains pattern)
        for (m, pattern), response in self._responses.items():
            if m == method.upper() and pattern in url:
                return response

        return self._default_response

    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> MockResponse:
        """Mock GET request."""
        return await self._request("GET", url, headers=headers, timeout=timeout)

    async def post(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> MockResponse:
        """Mock POST request."""
        return await self._request("POST", url, json=json, headers=headers, timeout=timeout)

    async def put(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> MockResponse:
        """Mock PUT request."""
        return await self._request("PUT", url, json=json, headers=headers, timeout=timeout)

    async def delete(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> MockResponse:
        """Mock DELETE request."""
        return await self._request("DELETE", url, headers=headers, timeout=timeout)

    async def _request(
        self,
        method: str,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> MockResponse:
        """Internal request handler."""
        # Record request
        self._requests.append({
            "method": method,
            "url": url,
            "json": json,
            "headers": headers,
            "timeout": timeout,
        })

        # Find response
        response = self._find_response(method, url)

        if response == "TIMEOUT":
            raise MockTimeoutException(f"Timeout for {method} {url}")
        if response == "CONNECT_ERROR":
            raise MockConnectError(f"Connection error for {method} {url}")
        if response is None:
            return MockResponse(status_code=404, _json={"error": "Not found"})

        return response

    async def aclose(self) -> None:
        """Close the client."""
        self._closed = True

    def get_requests(self) -> List[Dict[str, Any]]:
        """Get recorded requests."""
        return self._requests

    def clear_requests(self) -> None:
        """Clear recorded requests."""
        self._requests.clear()

    def request_count(self) -> int:
        """Get number of requests made."""
        return len(self._requests)

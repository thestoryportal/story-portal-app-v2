"""
HTTP Client with Automatic Correlation ID Propagation

Provides HTTP client utilities that automatically inject correlation IDs
into outgoing requests for distributed tracing.
"""

import logging
from typing import Any, Dict, Optional
import httpx

from .logging_config import get_correlation_id, get_request_id, get_user_id, get_session_id
from .middleware import add_correlation_headers


logger = logging.getLogger(__name__)


class CorrelatedHTTPClient:
    """
    HTTP client that automatically propagates correlation IDs.

    Usage:
        client = CorrelatedHTTPClient()
        response = await client.get("http://service/endpoint")
    """

    def __init__(
        self,
        timeout: float = 30.0,
        follow_redirects: bool = True,
        verify_ssl: bool = True,
    ):
        """
        Initialize HTTP client.

        Args:
            timeout: Request timeout in seconds
            follow_redirects: Whether to follow redirects
            verify_ssl: Whether to verify SSL certificates
        """
        self.timeout = timeout
        self.follow_redirects = follow_redirects
        self.verify_ssl = verify_ssl
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=self.follow_redirects,
            verify=self.verify_ssl,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    def _prepare_headers(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Prepare headers with correlation tracking.

        Args:
            headers: Optional additional headers

        Returns:
            Headers with correlation tracking added
        """
        if headers is None:
            headers = {}

        # Add correlation headers from context
        headers = add_correlation_headers(headers.copy())

        return headers

    def _log_request(
        self,
        method: str,
        url: str,
        correlation_id: Optional[str],
        request_id: Optional[str],
    ):
        """Log outgoing request."""
        logger.info(
            f"Outgoing {method} request",
            extra={
                'event': 'outgoing_request',
                'method': method,
                'url': url,
                'correlation_id': correlation_id,
                'request_id': request_id,
            }
        )

    def _log_response(
        self,
        method: str,
        url: str,
        status_code: int,
        duration_ms: float,
    ):
        """Log response."""
        logger.info(
            f"Response received",
            extra={
                'event': 'response_received',
                'method': method,
                'url': url,
                'status_code': status_code,
                'duration_ms': duration_ms,
            }
        )

    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """
        Make GET request with correlation tracking.

        Args:
            url: Target URL
            params: Query parameters
            headers: Additional headers

        Returns:
            HTTP response
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        headers = self._prepare_headers(headers)
        correlation_id = get_correlation_id()
        request_id = get_request_id()

        self._log_request("GET", url, correlation_id, request_id)

        import time
        start_time = time.time()

        try:
            response = await self._client.get(url, params=params, headers=headers)
            duration_ms = (time.time() - start_time) * 1000

            self._log_response("GET", url, response.status_code, duration_ms)

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"GET request failed",
                extra={
                    'event': 'request_failed',
                    'method': 'GET',
                    'url': url,
                    'error': str(e),
                    'duration_ms': duration_ms,
                },
                exc_info=True,
            )
            raise

    async def post(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """
        Make POST request with correlation tracking.

        Args:
            url: Target URL
            json: JSON body
            data: Form data
            headers: Additional headers

        Returns:
            HTTP response
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        headers = self._prepare_headers(headers)
        correlation_id = get_correlation_id()
        request_id = get_request_id()

        self._log_request("POST", url, correlation_id, request_id)

        import time
        start_time = time.time()

        try:
            response = await self._client.post(
                url, json=json, data=data, headers=headers
            )
            duration_ms = (time.time() - start_time) * 1000

            self._log_response("POST", url, response.status_code, duration_ms)

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"POST request failed",
                extra={
                    'event': 'request_failed',
                    'method': 'POST',
                    'url': url,
                    'error': str(e),
                    'duration_ms': duration_ms,
                },
                exc_info=True,
            )
            raise

    async def put(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """Make PUT request with correlation tracking."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        headers = self._prepare_headers(headers)
        correlation_id = get_correlation_id()
        request_id = get_request_id()

        self._log_request("PUT", url, correlation_id, request_id)

        import time
        start_time = time.time()

        try:
            response = await self._client.put(
                url, json=json, data=data, headers=headers
            )
            duration_ms = (time.time() - start_time) * 1000

            self._log_response("PUT", url, response.status_code, duration_ms)

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"PUT request failed",
                extra={
                    'event': 'request_failed',
                    'method': 'PUT',
                    'url': url,
                    'error': str(e),
                    'duration_ms': duration_ms,
                },
                exc_info=True,
            )
            raise

    async def delete(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """Make DELETE request with correlation tracking."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        headers = self._prepare_headers(headers)
        correlation_id = get_correlation_id()
        request_id = get_request_id()

        self._log_request("DELETE", url, correlation_id, request_id)

        import time
        start_time = time.time()

        try:
            response = await self._client.delete(url, headers=headers)
            duration_ms = (time.time() - start_time) * 1000

            self._log_response("DELETE", url, response.status_code, duration_ms)

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"DELETE request failed",
                extra={
                    'event': 'request_failed',
                    'method': 'DELETE',
                    'url': url,
                    'error': str(e),
                    'duration_ms': duration_ms,
                },
                exc_info=True,
            )
            raise


# Convenience functions for one-off requests

async def get_with_correlation(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
) -> httpx.Response:
    """
    Make one-off GET request with correlation tracking.

    Args:
        url: Target URL
        params: Query parameters
        headers: Additional headers
        timeout: Request timeout

    Returns:
        HTTP response
    """
    async with CorrelatedHTTPClient(timeout=timeout) as client:
        return await client.get(url, params=params, headers=headers)


async def post_with_correlation(
    url: str,
    json: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
) -> httpx.Response:
    """
    Make one-off POST request with correlation tracking.

    Args:
        url: Target URL
        json: JSON body
        data: Form data
        headers: Additional headers
        timeout: Request timeout

    Returns:
        HTTP response
    """
    async with CorrelatedHTTPClient(timeout=timeout) as client:
        return await client.post(url, json=json, data=data, headers=headers)

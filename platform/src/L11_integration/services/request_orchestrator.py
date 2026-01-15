"""
L11 Integration Layer - Request Orchestrator.

Cross-layer request routing with correlation and tracing.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
import httpx

from .service_registry import ServiceRegistry
from .circuit_breaker import CircuitBreaker
from ..models import (
    RequestContext,
    TraceSpan,
    SpanKind,
    SpanStatus,
    IntegrationError,
    ErrorCode,
)


logger = logging.getLogger(__name__)


class RequestOrchestrator:
    """
    Request orchestrator for cross-layer communication.

    Handles routing, correlation, tracing, and timeout management.
    """

    def __init__(
        self,
        service_registry: ServiceRegistry,
        circuit_breaker: CircuitBreaker,
    ):
        """
        Initialize request orchestrator.

        Args:
            service_registry: ServiceRegistry instance
            circuit_breaker: CircuitBreaker instance
        """
        self.service_registry = service_registry
        self.circuit_breaker = circuit_breaker
        self._http_client: Optional[httpx.AsyncClient] = None

    async def start(self) -> None:
        """Start the request orchestrator."""
        self._http_client = httpx.AsyncClient(timeout=30.0)
        logger.info("Request orchestrator started")

    async def stop(self) -> None:
        """Stop the request orchestrator."""
        if self._http_client:
            await self._http_client.aclose()
        logger.info("Request orchestrator stopped")

    async def route_request(
        self,
        service_name: str,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        context: Optional[RequestContext] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Route a request to a service.

        Args:
            service_name: Target service name (e.g., "L02_runtime")
            method: HTTP method (GET, POST, etc.)
            path: Request path
            data: Request payload
            context: Request context for tracing
            timeout: Request timeout in seconds

        Returns:
            Response data as dictionary

        Raises:
            IntegrationError: If routing fails
        """
        if not self._http_client:
            raise IntegrationError.from_code(
                ErrorCode.E11300,
                details={"reason": "Request orchestrator not started"},
            )

        # Create context if not provided
        if context is None:
            context = RequestContext.create()

        # Create trace span
        span = TraceSpan(
            trace_id=context.trace_id,
            span_id=context.span_id,
            parent_span_id=context.parent_span_id,
            span_name=f"{service_name}.{method} {path}",
            span_kind=SpanKind.CLIENT,
            service_name="L11_integration",
        )
        span.set_attribute("target_service", service_name)
        span.set_attribute("http_method", method)
        span.set_attribute("http_path", path)

        try:
            # Discover service
            service = await self.service_registry.get_service_by_name(service_name)
            if not service:
                raise IntegrationError.from_code(
                    ErrorCode.E11001,
                    details={"service_name": service_name},
                )

            if not service.is_healthy():
                logger.warning(f"Routing request to unhealthy service: {service_name}")

            # Build URL
            url = f"{service.endpoint}{path}"
            span.set_attribute("http_url", url)

            # Prepare headers with context propagation
            headers = context.to_headers()

            # Execute with circuit breaker protection
            response_data = await self.circuit_breaker.execute(
                service_name,
                self._send_request,
                method=method,
                url=url,
                data=data,
                headers=headers,
                timeout=timeout or 30.0,
            )

            # Mark span as successful
            span.end(SpanStatus.OK)

            return response_data

        except IntegrationError as e:
            # Record error in span
            span.end(SpanStatus.ERROR, error=str(e))
            raise

        except Exception as e:
            # Wrap unexpected errors
            span.end(SpanStatus.ERROR, error=str(e))
            raise IntegrationError.from_code(
                ErrorCode.E11301,
                details={
                    "service_name": service_name,
                    "method": method,
                    "path": path,
                    "error": str(e),
                },
            )

    async def _send_request(
        self,
        method: str,
        url: str,
        data: Optional[Dict[str, Any]],
        headers: Dict[str, str],
        timeout: float,
    ) -> Dict[str, Any]:
        """
        Send HTTP request.

        Args:
            method: HTTP method
            url: Request URL
            data: Request data
            headers: Request headers
            timeout: Request timeout

        Returns:
            Response data

        Raises:
            Exception: If request fails
        """
        if not self._http_client:
            raise IntegrationError.from_code(
                ErrorCode.E11300,
                details={"reason": "HTTP client not initialized"},
            )

        try:
            # Send request
            if method.upper() == "GET":
                response = await self._http_client.get(
                    url,
                    headers=headers,
                    timeout=timeout,
                )
            elif method.upper() == "POST":
                response = await self._http_client.post(
                    url,
                    json=data,
                    headers=headers,
                    timeout=timeout,
                )
            elif method.upper() == "PUT":
                response = await self._http_client.put(
                    url,
                    json=data,
                    headers=headers,
                    timeout=timeout,
                )
            elif method.upper() == "DELETE":
                response = await self._http_client.delete(
                    url,
                    headers=headers,
                    timeout=timeout,
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # Check response
            response.raise_for_status()

            # Return JSON response
            return response.json()

        except httpx.TimeoutException:
            raise IntegrationError.from_code(
                ErrorCode.E11302,
                details={"url": url, "timeout": timeout},
            )
        except httpx.HTTPStatusError as e:
            raise IntegrationError.from_code(
                ErrorCode.E11301,
                details={
                    "url": url,
                    "status_code": e.response.status_code,
                    "error": str(e),
                },
            )
        except Exception as e:
            raise IntegrationError.from_code(
                ErrorCode.E11301,
                details={"url": url, "error": str(e)},
            )

    async def broadcast_request(
        self,
        service_names: list[str],
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        context: Optional[RequestContext] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Broadcast a request to multiple services in parallel.

        Args:
            service_names: List of target service names
            method: HTTP method
            path: Request path
            data: Request payload
            context: Request context
            timeout: Request timeout per service

        Returns:
            Dictionary mapping service name to response
        """
        # Create context if not provided
        if context is None:
            context = RequestContext.create()

        # Create tasks for parallel execution
        tasks = []
        for service_name in service_names:
            # Create child context for each request
            child_context = context.create_child_context()
            task = self.route_request(
                service_name=service_name,
                method=method,
                path=path,
                data=data,
                context=child_context,
                timeout=timeout,
            )
            tasks.append((service_name, task))

        # Execute in parallel
        results = {}
        responses = await asyncio.gather(*[t for _, t in tasks], return_exceptions=True)

        for (service_name, _), response in zip(tasks, responses):
            if isinstance(response, Exception):
                results[service_name] = {"error": str(response)}
            else:
                results[service_name] = response

        return results

    async def aggregate_responses(
        self,
        service_names: list[str],
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        context: Optional[RequestContext] = None,
        timeout: Optional[float] = None,
        aggregator: Optional[callable] = None,
    ) -> Any:
        """
        Aggregate responses from multiple services.

        Args:
            service_names: List of target service names
            method: HTTP method
            path: Request path
            data: Request payload
            context: Request context
            timeout: Request timeout per service
            aggregator: Function to aggregate responses (default: list)

        Returns:
            Aggregated result
        """
        # Broadcast request
        results = await self.broadcast_request(
            service_names=service_names,
            method=method,
            path=path,
            data=data,
            context=context,
            timeout=timeout,
        )

        # Apply aggregator
        if aggregator:
            return aggregator(results)
        else:
            # Default: return list of successful responses
            return [
                response for response in results.values()
                if not isinstance(response, dict) or "error" not in response
            ]

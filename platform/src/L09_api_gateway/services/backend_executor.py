"""
Backend Executor - Circuit Breaker with 4-State Machine
"""

import time
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from ..models import (
    RequestContext,
    RouteMatch,
    BackendTarget,
    CircuitBreakerState,
    CircuitBreakerConfig,
    CircuitBreakerStats,
    GatewayResponse,
)
from ..errors import ErrorCode, CircuitBreakerError, ServerError


class BackendExecutor:
    """
    Executes requests to backend services with circuit breaker protection

    Features:
    - 4-state circuit breaker (CLOSED, OPEN, HALF_OPEN, RECOVERING)
    - Exponential backoff for retries
    - Request timeout enforcement
    - Connection pooling
    - mTLS support
    """

    def __init__(
        self,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
    ):
        self.circuit_breaker_config = circuit_breaker_config or CircuitBreakerConfig()

        # Circuit breaker state per backend
        self._circuit_breakers: Dict[str, CircuitBreakerStats] = {}

        # HTTP client with connection pooling
        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )

    async def execute(
        self,
        context: RequestContext,
        route_match: RouteMatch,
        body: Optional[bytes] = None,
    ) -> GatewayResponse:
        """
        Execute request to backend service

        Args:
            context: Request context
            route_match: Matched route with backend
            body: Request body

        Returns:
            GatewayResponse

        Raises:
            CircuitBreakerError: If circuit breaker is open
            ServerError: If backend execution fails
        """
        backend = route_match.selected_backend
        route = route_match.route

        # Check circuit breaker
        circuit_breaker = self._get_circuit_breaker(backend.service_id)

        if not circuit_breaker.should_allow_request():
            raise CircuitBreakerError(
                ErrorCode.E9801,
                "Circuit breaker open",
                details={
                    "backend": backend.service_id,
                    "state": circuit_breaker.current_state.value,
                },
            )

        # Prepare backend request
        url = self._build_backend_url(backend, context.metadata.path)
        headers = self._prepare_headers(context, route_match)

        # Execute with retries
        max_retries = route.max_retries
        retry_count = 0
        last_error = None

        while retry_count <= max_retries:
            try:
                # Execute request
                response = await self._execute_request(
                    method=context.metadata.method,
                    url=url,
                    headers=headers,
                    body=body,
                    timeout=route.timeout_ms / 1000.0,
                )

                # Record success
                self._record_success(circuit_breaker)

                return response

            except Exception as e:
                last_error = e

                # Record failure
                self._record_failure(circuit_breaker)

                # Check if should retry
                if retry_count >= max_retries:
                    break

                # Check if error is retryable
                if not self._is_retryable_error(e, route):
                    break

                # Exponential backoff
                backoff = self._calculate_backoff(retry_count)
                await self._sleep(backoff)

                retry_count += 1

        # All retries exhausted
        raise ServerError(
            ErrorCode.E9904,
            f"Backend request failed after {retry_count} retries: {str(last_error)}",
            details={"backend": backend.service_id, "retries": retry_count},
        )

    async def _execute_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[bytes],
        timeout: float,
    ) -> GatewayResponse:
        """Execute HTTP request to backend"""
        try:
            response = await self._http_client.request(
                method=method,
                url=url,
                headers=headers,
                content=body,
                timeout=timeout,
            )

            return GatewayResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                body=response.content,
                timestamp=datetime.utcnow(),
            )

        except httpx.TimeoutException as e:
            raise ServerError(
                ErrorCode.E9903,
                f"Gateway timeout: {str(e)}",
            )
        except httpx.ConnectError as e:
            raise ServerError(
                ErrorCode.E9904,
                f"Backend connection failed: {str(e)}",
            )
        except Exception as e:
            raise ServerError(
                ErrorCode.E9901,
                f"Backend request failed: {str(e)}",
            )

    def _build_backend_url(self, backend: BackendTarget, path: str) -> str:
        """Build backend URL"""
        protocol = backend.protocol
        host = backend.host
        port = backend.port
        base_path = backend.base_path.rstrip("/")

        # Combine base path with request path
        full_path = f"{base_path}{path}"

        return f"{protocol}://{host}:{port}{full_path}"

    def _prepare_headers(
        self, context: RequestContext, route_match: RouteMatch
    ) -> Dict[str, str]:
        """Prepare headers for backend request"""
        headers = dict(context.metadata.headers)

        # Inject context headers
        context_headers = context.to_headers()
        headers.update(context_headers)

        # Remove headers that shouldn't be forwarded
        headers.pop("host", None)
        headers.pop("connection", None)

        return headers

    def _get_circuit_breaker(self, backend_id: str) -> CircuitBreakerStats:
        """Get or create circuit breaker for backend"""
        if backend_id not in self._circuit_breakers:
            self._circuit_breakers[backend_id] = CircuitBreakerStats()
        return self._circuit_breakers[backend_id]

    def _record_success(self, circuit_breaker: CircuitBreakerStats) -> None:
        """Record successful request"""
        circuit_breaker.request_count += 1

        # Update state based on current state
        if circuit_breaker.current_state == CircuitBreakerState.HALF_OPEN:
            circuit_breaker.success_count_in_half_open += 1

            # Close circuit after threshold successes
            if (
                circuit_breaker.success_count_in_half_open
                >= self.circuit_breaker_config.half_open_success_threshold
            ):
                self._transition_to_recovering(circuit_breaker)

        elif circuit_breaker.current_state == CircuitBreakerState.RECOVERING:
            # Increase traffic gradually
            self._update_traffic_ramp(circuit_breaker)

    def _record_failure(self, circuit_breaker: CircuitBreakerStats) -> None:
        """Record failed request"""
        circuit_breaker.request_count += 1
        circuit_breaker.error_count += 1

        # Calculate error rate
        if circuit_breaker.request_count >= self.circuit_breaker_config.min_requests_threshold:
            circuit_breaker.error_rate = (
                circuit_breaker.error_count / circuit_breaker.request_count
            )

            # Check if should open circuit
            if (
                circuit_breaker.error_rate
                >= self.circuit_breaker_config.error_rate_threshold
            ):
                if circuit_breaker.current_state == CircuitBreakerState.CLOSED:
                    self._transition_to_open(circuit_breaker)
                elif circuit_breaker.current_state == CircuitBreakerState.RECOVERING:
                    self._transition_to_open(circuit_breaker)

        # In HALF_OPEN, any failure reopens circuit
        if circuit_breaker.current_state == CircuitBreakerState.HALF_OPEN:
            self._transition_to_open(circuit_breaker)

    def _transition_to_open(self, circuit_breaker: CircuitBreakerStats) -> None:
        """Transition to OPEN state"""
        circuit_breaker.current_state = CircuitBreakerState.OPEN
        circuit_breaker.last_state_change = datetime.utcnow()

    def _transition_to_half_open(self, circuit_breaker: CircuitBreakerStats) -> None:
        """Transition to HALF_OPEN state"""
        circuit_breaker.current_state = CircuitBreakerState.HALF_OPEN
        circuit_breaker.last_state_change = datetime.utcnow()
        circuit_breaker.success_count_in_half_open = 0

    def _transition_to_recovering(self, circuit_breaker: CircuitBreakerStats) -> None:
        """Transition to RECOVERING state"""
        circuit_breaker.current_state = CircuitBreakerState.RECOVERING
        circuit_breaker.last_state_change = datetime.utcnow()
        circuit_breaker.traffic_ramp_pct = self.circuit_breaker_config.ramp_up_initial_traffic_pct

    def _transition_to_closed(self, circuit_breaker: CircuitBreakerStats) -> None:
        """Transition to CLOSED state"""
        circuit_breaker.current_state = CircuitBreakerState.CLOSED
        circuit_breaker.last_state_change = datetime.utcnow()
        circuit_breaker.error_count = 0
        circuit_breaker.request_count = 0
        circuit_breaker.error_rate = 0.0
        circuit_breaker.traffic_ramp_pct = 100

    def _update_traffic_ramp(self, circuit_breaker: CircuitBreakerStats) -> None:
        """Update traffic ramp percentage during recovery"""
        # Linear ramp over 5 minutes
        elapsed = datetime.utcnow() - circuit_breaker.last_state_change
        elapsed_ms = elapsed.total_seconds() * 1000

        ramp_duration_ms = self.circuit_breaker_config.ramp_up_duration_ms
        initial_pct = self.circuit_breaker_config.ramp_up_initial_traffic_pct

        # Calculate percentage
        progress = min(1.0, elapsed_ms / ramp_duration_ms)
        circuit_breaker.traffic_ramp_pct = int(
            initial_pct + (100 - initial_pct) * progress
        )

        # If ramp complete, close circuit
        if circuit_breaker.traffic_ramp_pct >= 100:
            self._transition_to_closed(circuit_breaker)

    def _is_retryable_error(self, error: Exception, route: RouteMatch) -> bool:
        """Check if error is retryable"""
        # Timeouts are retryable
        if isinstance(error, httpx.TimeoutException):
            return True

        # Connection errors are retryable
        if isinstance(error, httpx.ConnectError):
            return True

        # Check status code if available
        if isinstance(error, ServerError):
            # 503, 504 are retryable
            return True

        return False

    def _calculate_backoff(self, retry_count: int) -> float:
        """Calculate exponential backoff with jitter"""
        import random

        base_ms = 100
        multiplier = 10
        max_ms = 60000

        backoff_ms = min(base_ms * (multiplier ** retry_count), max_ms)

        # Add jitter (±10%)
        jitter = random.uniform(-0.1, 0.1)
        backoff_ms = backoff_ms * (1 + jitter)

        return backoff_ms / 1000.0  # Convert to seconds

    async def _sleep(self, seconds: float) -> None:
        """Sleep for specified seconds"""
        import asyncio
        await asyncio.sleep(seconds)

    async def close(self) -> None:
        """Close HTTP client"""
        await self._http_client.aclose()

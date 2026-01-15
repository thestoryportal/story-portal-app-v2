"""
Main API Gateway application with FastAPI
"""

import time
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
import redis.asyncio as aioredis

from .config import get_settings
from .models import (
    RequestContext,
    RequestMetadata,
    HealthStatus,
    HealthCheckResponse,
)
from .services import (
    AuthenticationHandler,
    AuthorizationEngine,
    RateLimiter,
    IdempotencyHandler,
    RequestRouter,
    RequestValidator,
    BackendExecutor,
    AsyncHandler,
    ResponseFormatter,
    EventPublisher,
)
from .errors import GatewayError, ErrorCode, ServerError


class APIGateway:
    """
    Main API Gateway application

    Coordinates all services in request processing pipeline:
    1. Authentication
    2. Authorization
    3. Request Validation
    4. Idempotency Check
    5. Rate Limiting
    6. Request Routing
    7. Backend Execution
    8. Response Formatting
    9. Event Publishing
    """

    def __init__(self):
        self.settings = get_settings()
        self.app = FastAPI(
            title="L09 API Gateway",
            version="1.2.0",
            description="API Gateway with authentication, authorization, and rate limiting",
        )

        # Initialize services
        self.redis_client: Optional[aioredis.Redis] = None
        self.auth_handler: Optional[AuthenticationHandler] = None
        self.authz_engine: Optional[AuthorizationEngine] = None
        self.rate_limiter: Optional[RateLimiter] = None
        self.idempotency_handler: Optional[IdempotencyHandler] = None
        self.request_router: Optional[RequestRouter] = None
        self.request_validator: Optional[RequestValidator] = None
        self.backend_executor: Optional[BackendExecutor] = None
        self.async_handler: Optional[AsyncHandler] = None
        self.response_formatter: Optional[ResponseFormatter] = None
        self.event_publisher: Optional[EventPublisher] = None

        # Health tracking
        self.start_time = datetime.utcnow()

        # Register routes
        self._register_health_endpoints()
        self._register_gateway_routes()

    async def startup(self):
        """Initialize gateway services on startup"""
        # Initialize Redis
        self.redis_client = await aioredis.from_url(
            f"redis://{self.settings.redis_host}:{self.settings.redis_port}/{self.settings.redis_db}",
            password=self.settings.redis_password,
            encoding="utf-8",
            decode_responses=True,
        )

        # Initialize services
        self.auth_handler = AuthenticationHandler(jwks_url=self.settings.jwks_url)
        self.authz_engine = AuthorizationEngine()
        self.rate_limiter = RateLimiter(self.redis_client)
        self.idempotency_handler = IdempotencyHandler(self.redis_client)
        self.request_router = RequestRouter()
        self.request_validator = RequestValidator(
            max_body_size=self.settings.max_body_size,
            max_header_count=self.settings.max_header_count,
            max_header_size=self.settings.max_header_size,
            max_query_length=self.settings.max_query_length,
        )
        self.backend_executor = BackendExecutor()
        self.response_formatter = ResponseFormatter()

        # Mock services (would connect to real L01 in production)
        self.async_handler = AsyncHandler(
            operation_store=None,  # Mock
            redis_client=self.redis_client,
        )
        self.event_publisher = EventPublisher(
            event_store=None,  # Mock
            log_sampling_rate=self.settings.log_sampling_rate,
        )

        # Load initial routes (would load from L01 in production)
        await self._load_routes()

    async def shutdown(self):
        """Cleanup on shutdown"""
        if self.redis_client:
            await self.redis_client.close()
        if self.backend_executor:
            await self.backend_executor.close()
        if self.async_handler:
            await self.async_handler.close()

    def _register_health_endpoints(self):
        """Register health check endpoints"""

        @self.app.get("/health/live")
        async def liveness():
            """Liveness probe - is service alive?"""
            return JSONResponse(
                content={"status": "ok", "timestamp": datetime.utcnow().isoformat()}
            )

        @self.app.get("/health/ready")
        async def readiness():
            """Readiness probe - is service ready for traffic?"""
            dependencies = {}

            # Check Redis
            try:
                await self.redis_client.ping()
                dependencies["redis"] = {
                    "status": "healthy",
                    "latency_ms": 0,
                }
            except Exception as e:
                dependencies["redis"] = {
                    "status": "unhealthy",
                    "error": str(e),
                }
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "status": "unhealthy",
                        "dependencies": dependencies,
                    },
                )

            return JSONResponse(
                content={
                    "status": "healthy",
                    "dependencies": dependencies,
                }
            )

        @self.app.get("/health/startup")
        async def startup():
            """Startup probe - has service completed initialization?"""
            if not self.redis_client or not self.request_router:
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={"status": "starting"},
                )

            return JSONResponse(content={"status": "ready"})

        @self.app.get("/health/detailed")
        async def detailed_health():
            """Detailed health check"""
            uptime = (datetime.utcnow() - self.start_time).total_seconds()

            dependencies = {
                "redis": await self._check_redis_health(),
            }

            overall_status = (
                HealthStatus.HEALTHY
                if all(d.get("status") == "healthy" for d in dependencies.values())
                else HealthStatus.DEGRADED
            )

            response = HealthCheckResponse(
                status=overall_status,
                version="1.2.0",
                dependencies=dependencies,
                uptime_seconds=int(uptime),
            )

            return JSONResponse(content=response.model_dump(mode='json'))

    def _register_gateway_routes(self):
        """Register main gateway route handler"""

        @self.app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
        async def gateway_handler(request: Request, path: str):
            """Main gateway request handler"""
            start_time = time.time()

            try:
                # Build request context
                context = await self._build_request_context(request)

                # Process through pipeline
                response = await self._process_request(context, request)

                # Calculate latency
                latency_ms = (time.time() - start_time) * 1000

                # Publish event
                if self.event_publisher:
                    await self.event_publisher.publish_request_event(
                        context=context,
                        response=response,
                        latency_ms=latency_ms,
                    )

                # Convert to FastAPI response
                return Response(
                    content=response.body if isinstance(response.body, bytes) else str(response.body).encode(),
                    status_code=response.status_code,
                    headers=response.headers,
                )

            except GatewayError as e:
                # Handle gateway errors
                latency_ms = (time.time() - start_time) * 1000

                # Build minimal context for error
                context = await self._build_request_context(request)

                # Format error response
                error_response = await self.response_formatter.format_error(e, context)

                # Publish error event
                if self.event_publisher:
                    await self.event_publisher.publish_request_event(
                        context=context,
                        response=error_response,
                        latency_ms=latency_ms,
                        error_code=e.code.value,
                    )

                return Response(
                    content=str(error_response.body).encode(),
                    status_code=error_response.status_code,
                    headers=error_response.headers,
                )

            except Exception as e:
                # Unexpected error
                context = await self._build_request_context(request)
                error = ServerError(ErrorCode.E9901, f"Internal server error: {str(e)}")
                error_response = await self.response_formatter.format_error(error, context)

                return Response(
                    content=str(error_response.body).encode(),
                    status_code=500,
                    headers=error_response.headers,
                )

    async def _build_request_context(self, request: Request) -> RequestContext:
        """Build request context from FastAPI request"""
        # Generate trace IDs
        trace_id = request.headers.get("traceparent", "").split("-")[1] if "traceparent" in request.headers else uuid.uuid4().hex
        span_id = uuid.uuid4().hex[:16]

        # Extract metadata
        metadata = RequestMetadata(
            method=request.method,
            path=request.url.path,
            headers=dict(request.headers),
            query_params=dict(request.query_params),
            client_ip=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent"),
            content_type=request.headers.get("content-type"),
            api_version=request.headers.get("accept-version"),
        )

        # Extract idempotency key
        idempotency_key = request.headers.get("idempotency-key")

        return RequestContext(
            trace_id=trace_id,
            span_id=span_id,
            metadata=metadata,
            idempotency_key=uuid.UUID(idempotency_key) if idempotency_key else None,
        )

    async def _process_request(self, context: RequestContext, request: Request):
        """Process request through gateway pipeline"""
        # Mock consumer lookup function
        async def consumer_lookup_fn(**kwargs):
            # In production, query L01 Consumer Registry
            from .models import ConsumerProfile, AuthMethod, RateLimitTier
            return ConsumerProfile(
                consumer_id="test_consumer",
                tenant_id="test_tenant",
                auth_method=AuthMethod.API_KEY,
                rate_limit_tier=RateLimitTier.STANDARD,
            )

        # 1. Authenticate
        consumer = await self.auth_handler.authenticate(context, consumer_lookup_fn)
        context.consumer_id = consumer.consumer_id
        context.tenant_id = consumer.tenant_id
        context.rate_limit_tier = consumer.rate_limit_tier.value
        context.oauth_scopes = consumer.oauth_scopes

        # 2. Check idempotency
        cached_response = await self.idempotency_handler.check_idempotency(context)
        if cached_response:
            return cached_response

        # 3. Rate limit
        await self.rate_limiter.check_rate_limit(consumer, tokens_required=1)

        # 4. Route request
        route_match = await self.request_router.match_route(context)

        # 5. Authorize
        await self.authz_engine.authorize(context, consumer, route_match.route)

        # 6. Validate request
        body = await request.body() if request.method in ["POST", "PUT", "PATCH"] else None
        await self.request_validator.validate_request(context, body)

        # 7. Execute backend (or mock response)
        # For now, return mock success response
        from .models import GatewayResponse
        response = GatewayResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body={"message": "Success", "route": route_match.route.route_id},
        )

        # 8. Store idempotency response
        await self.idempotency_handler.store_response(context, response)

        # 9. Format response
        rate_limit_info = await self.rate_limiter.get_rate_limit_info(consumer)
        response = await self.response_formatter.format_response(
            response, context, rate_limit_info
        )

        return response

    async def _load_routes(self):
        """Load route definitions"""
        # Mock route - in production, load from L01
        from .models import RouteDefinition, BackendTarget

        test_route = RouteDefinition(
            route_id="test_route",
            path_pattern="/api/test",
            methods=["GET", "POST"],
            backends=[
                BackendTarget(
                    service_id="test_backend",
                    host="localhost",
                    port=8001,
                    protocol="http",
                )
            ],
            auth_required=True,
        )

        self.request_router.add_route(test_route)

    async def _check_redis_health(self) -> Dict[str, Any]:
        """Check Redis health"""
        try:
            start = time.time()
            await self.redis_client.ping()
            latency_ms = (time.time() - start) * 1000

            return {
                "status": "healthy",
                "latency_ms": round(latency_ms, 2),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }

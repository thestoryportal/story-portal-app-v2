"""
Standardized Health Check Framework

Provides consistent health check endpoints across all service layers:
- /health/live - Liveness probe (is service running?)
- /health/ready - Readiness probe (can service handle requests?)
- /health/startup - Startup probe (has service initialized?)
- /health - Detailed health status with component checks

Based on Kubernetes health check best practices.
"""

import time
import logging
from typing import Dict, Any, List, Optional, Callable, Awaitable
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field
from fastapi import APIRouter, status, Response


logger = logging.getLogger(__name__)


# ============================================================================
# Health Status Models
# ============================================================================

class HealthStatus(str, Enum):
    """Health check status values."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class ComponentHealth(BaseModel):
    """Health status for a single component."""
    name: str = Field(..., description="Component name")
    status: HealthStatus = Field(..., description="Component health status")
    message: Optional[str] = Field(None, description="Status message or error")
    response_time_ms: Optional[float] = Field(None, description="Health check duration")
    last_check_at: Optional[datetime] = Field(None, description="Last check timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class HealthCheckResponse(BaseModel):
    """Detailed health check response."""
    status: HealthStatus = Field(..., description="Overall health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    uptime_seconds: float = Field(..., description="Service uptime")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    components: List[ComponentHealth] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Health Check Functions
# ============================================================================

class HealthCheck:
    """
    Base class for health checks.

    Subclass this to implement custom health checks for different components.
    """

    def __init__(self, name: str):
        """
        Initialize health check.

        Args:
            name: Component name
        """
        self.name = name
        self._last_status: Optional[HealthStatus] = None
        self._last_check_at: Optional[datetime] = None
        self._last_response_time_ms: Optional[float] = None

    async def check(self) -> ComponentHealth:
        """
        Execute health check.

        Returns:
            ComponentHealth with check results
        """
        start_time = time.time()

        try:
            # Execute the actual health check
            is_healthy, message, metadata = await self._check_health()

            response_time_ms = (time.time() - start_time) * 1000

            status_value = HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY

            self._last_status = status_value
            self._last_check_at = datetime.utcnow()
            self._last_response_time_ms = response_time_ms

            return ComponentHealth(
                name=self.name,
                status=status_value,
                message=message,
                response_time_ms=response_time_ms,
                last_check_at=self._last_check_at,
                metadata=metadata or {},
            )

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000

            logger.error(
                f"Health check failed for {self.name}",
                extra={
                    'event': 'health_check_failed',
                    'component': self.name,
                    'error': str(e),
                },
                exc_info=True,
            )

            self._last_status = HealthStatus.UNHEALTHY
            self._last_check_at = datetime.utcnow()
            self._last_response_time_ms = response_time_ms

            return ComponentHealth(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check error: {str(e)}",
                response_time_ms=response_time_ms,
                last_check_at=self._last_check_at,
                metadata={"error_type": type(e).__name__},
            )

    async def _check_health(self) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Implement health check logic.

        Returns:
            Tuple of (is_healthy, message, metadata)

        Subclasses should override this method.
        """
        raise NotImplementedError("Subclasses must implement _check_health()")


# ============================================================================
# Built-in Health Checks
# ============================================================================

class DatabaseHealthCheck(HealthCheck):
    """Health check for database connection."""

    def __init__(self, name: str, db_pool):
        """
        Initialize database health check.

        Args:
            name: Component name
            db_pool: Database connection pool (asyncpg)
        """
        super().__init__(name)
        self.db_pool = db_pool

    async def _check_health(self) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Check database connectivity."""
        try:
            # Execute simple query
            result = await self.db_pool.fetchval("SELECT 1")

            if result == 1:
                # Get pool stats
                pool_size = self.db_pool.get_size()
                pool_free = self.db_pool.get_idle_size()
                pool_used = pool_size - pool_free

                return (
                    True,
                    "Database connection healthy",
                    {
                        "pool_size": pool_size,
                        "pool_used": pool_used,
                        "pool_free": pool_free,
                    }
                )
            else:
                return (False, "Database query returned unexpected result", {})

        except Exception as e:
            return (False, f"Database connection failed: {str(e)}", {})


class RedisHealthCheck(HealthCheck):
    """Health check for Redis connection."""

    def __init__(self, name: str, redis_client):
        """
        Initialize Redis health check.

        Args:
            name: Component name
            redis_client: Redis client (aioredis)
        """
        super().__init__(name)
        self.redis_client = redis_client

    async def _check_health(self) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Check Redis connectivity."""
        try:
            # Execute PING command
            pong = await self.redis_client.ping()

            if pong:
                # Get Redis info
                info = await self.redis_client.info()

                return (
                    True,
                    "Redis connection healthy",
                    {
                        "redis_version": info.get("redis_version"),
                        "used_memory_human": info.get("used_memory_human"),
                        "connected_clients": info.get("connected_clients"),
                    }
                )
            else:
                return (False, "Redis PING failed", {})

        except Exception as e:
            return (False, f"Redis connection failed: {str(e)}", {})


class HTTPServiceHealthCheck(HealthCheck):
    """Health check for downstream HTTP service."""

    def __init__(self, name: str, service_url: str, timeout: float = 5.0):
        """
        Initialize HTTP service health check.

        Args:
            name: Component name
            service_url: Service health endpoint URL
            timeout: Request timeout in seconds
        """
        super().__init__(name)
        self.service_url = service_url
        self.timeout = timeout

    async def _check_health(self) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Check HTTP service availability."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.service_url)

                if response.status_code == 200:
                    return (
                        True,
                        f"Service {self.service_url} is healthy",
                        {
                            "status_code": response.status_code,
                            "response_time_ms": response.elapsed.total_seconds() * 1000,
                        }
                    )
                else:
                    return (
                        False,
                        f"Service returned status {response.status_code}",
                        {"status_code": response.status_code}
                    )

        except httpx.TimeoutException:
            return (False, f"Service timeout after {self.timeout}s", {})
        except Exception as e:
            return (False, f"Service check failed: {str(e)}", {})


class CustomHealthCheck(HealthCheck):
    """Health check with custom function."""

    def __init__(self, name: str, check_func: Callable[[], Awaitable[bool]]):
        """
        Initialize custom health check.

        Args:
            name: Component name
            check_func: Async function that returns True if healthy

        Example:
            async def check_my_service():
                return await my_service.is_operational()

            health_checker.add_check(CustomHealthCheck("my-service", check_my_service))
        """
        super().__init__(name)
        self.check_func = check_func

    async def _check_health(self) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Execute custom health check function."""
        try:
            is_healthy = await self.check_func()
            message = "Component is healthy" if is_healthy else "Component is unhealthy"
            return (is_healthy, message, {})
        except Exception as e:
            return (False, f"Custom check failed: {str(e)}", {})


# ============================================================================
# Health Check Manager
# ============================================================================

class HealthCheckManager:
    """
    Manages health checks for a service.

    Example:
        manager = HealthCheckManager(
            service_name="L01 Data Layer",
            version="1.0.0",
        )

        # Add checks
        manager.add_check(DatabaseHealthCheck("postgres", db_pool))
        manager.add_check(RedisHealthCheck("redis", redis_client))

        # Get health status
        health = await manager.check_health()
    """

    def __init__(self, service_name: str, version: str = "1.0.0"):
        """
        Initialize health check manager.

        Args:
            service_name: Service name
            version: Service version
        """
        self.service_name = service_name
        self.version = version
        self.checks: List[HealthCheck] = []
        self.start_time = time.time()

    def add_check(self, health_check: HealthCheck):
        """
        Add a health check.

        Args:
            health_check: HealthCheck instance
        """
        self.checks.append(health_check)
        logger.info(
            f"Added health check: {health_check.name}",
            extra={
                'event': 'health_check_added',
                'service': self.service_name,
                'component': health_check.name,
            }
        )

    async def check_health(self, include_components: bool = True) -> HealthCheckResponse:
        """
        Execute all health checks.

        Args:
            include_components: Include component-level checks

        Returns:
            HealthCheckResponse with overall and component statuses
        """
        uptime = time.time() - self.start_time

        components = []
        if include_components:
            # Execute all component checks in parallel
            import asyncio
            component_results = await asyncio.gather(
                *[check.check() for check in self.checks],
                return_exceptions=True
            )

            for result in component_results:
                if isinstance(result, Exception):
                    logger.error(
                        "Component health check raised exception",
                        extra={'error': str(result)},
                        exc_info=result,
                    )
                    components.append(ComponentHealth(
                        name="unknown",
                        status=HealthStatus.UNHEALTHY,
                        message=f"Check failed: {str(result)}",
                    ))
                else:
                    components.append(result)

        # Determine overall status
        if not components:
            overall_status = HealthStatus.HEALTHY
        elif all(c.status == HealthStatus.HEALTHY for c in components):
            overall_status = HealthStatus.HEALTHY
        elif any(c.status == HealthStatus.UNHEALTHY for c in components):
            overall_status = HealthStatus.UNHEALTHY
        else:
            overall_status = HealthStatus.DEGRADED

        return HealthCheckResponse(
            status=overall_status,
            service=self.service_name,
            version=self.version,
            uptime_seconds=uptime,
            components=components,
        )

    async def is_live(self) -> bool:
        """
        Liveness check - is the service running?

        Returns:
            True if service is alive (always returns True if reached)
        """
        return True

    async def is_ready(self) -> bool:
        """
        Readiness check - can the service handle requests?

        Checks all critical components. Service is ready only if all are healthy.

        Returns:
            True if service is ready to handle requests
        """
        health = await self.check_health(include_components=True)
        return health.status == HealthStatus.HEALTHY

    async def is_started(self) -> bool:
        """
        Startup check - has the service completed initialization?

        Returns:
            True if service startup is complete
        """
        # Default implementation: check if service has been running for at least 5 seconds
        uptime = time.time() - self.start_time
        return uptime > 5.0


# ============================================================================
# FastAPI Router Factory
# ============================================================================

def create_health_router(manager: HealthCheckManager) -> APIRouter:
    """
    Create FastAPI router with standardized health endpoints.

    Args:
        manager: HealthCheckManager instance

    Returns:
        APIRouter with health endpoints

    Example:
        from fastapi import FastAPI

        app = FastAPI()
        health_manager = HealthCheckManager("My Service", "1.0.0")
        health_manager.add_check(DatabaseHealthCheck("postgres", db_pool))

        app.include_router(create_health_router(health_manager))
    """
    router = APIRouter(prefix="/health", tags=["health"])

    @router.get("/live", status_code=status.HTTP_200_OK)
    async def liveness(response: Response):
        """
        Liveness probe endpoint.

        Returns 200 if service is alive (running).
        Used by Kubernetes to restart unhealthy pods.

        Should be lightweight and always succeed if process is running.
        """
        is_live = await manager.is_live()

        if not is_live:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"status": "unhealthy", "message": "Service is not alive"}

        return {"status": "healthy"}

    @router.get("/ready", status_code=status.HTTP_200_OK)
    async def readiness(response: Response):
        """
        Readiness probe endpoint.

        Returns 200 if service can handle requests.
        Used by Kubernetes to route traffic to healthy pods.

        Checks all critical dependencies (database, cache, etc.).
        """
        is_ready = await manager.is_ready()

        if not is_ready:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            health = await manager.check_health()
            return {
                "status": "unhealthy",
                "message": "Service is not ready",
                "components": [
                    {"name": c.name, "status": c.status, "message": c.message}
                    for c in health.components
                    if c.status != HealthStatus.HEALTHY
                ]
            }

        return {"status": "healthy"}

    @router.get("/startup", status_code=status.HTTP_200_OK)
    async def startup_probe(response: Response):
        """
        Startup probe endpoint.

        Returns 200 if service initialization is complete.
        Used by Kubernetes during pod startup.

        Allows slow-starting applications time to initialize.
        """
        is_started = await manager.is_started()

        if not is_started:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {
                "status": "starting",
                "message": "Service initialization in progress",
                "uptime_seconds": time.time() - manager.start_time,
            }

        return {"status": "healthy"}

    @router.get("/", response_model=HealthCheckResponse)
    async def detailed_health(response: Response):
        """
        Detailed health check endpoint.

        Returns comprehensive health status including all components.
        Used for monitoring and debugging.
        """
        health = await manager.check_health(include_components=True)

        if health.status == HealthStatus.UNHEALTHY:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif health.status == HealthStatus.DEGRADED:
            response.status_code = status.HTTP_200_OK  # Still accepting requests

        return health

    return router


# ============================================================================
# Convenience Functions
# ============================================================================

def setup_health_checks(
    app,
    service_name: str,
    version: str = "1.0.0",
    db_pool=None,
    redis_client=None,
) -> HealthCheckManager:
    """
    Convenience function to setup health checks for a service.

    Args:
        app: FastAPI application
        service_name: Service name
        version: Service version
        db_pool: Database connection pool (optional)
        redis_client: Redis client (optional)

    Returns:
        HealthCheckManager instance

    Example:
        from fastapi import FastAPI

        app = FastAPI()
        health_manager = setup_health_checks(
            app,
            service_name="L01 Data Layer",
            version="1.0.0",
            db_pool=db_pool,
            redis_client=redis_client,
        )

        # Add custom checks
        health_manager.add_check(CustomHealthCheck("custom", my_check_func))
    """
    manager = HealthCheckManager(service_name, version)

    # Add database check if provided
    if db_pool:
        manager.add_check(DatabaseHealthCheck("database", db_pool))

    # Add Redis check if provided
    if redis_client:
        manager.add_check(RedisHealthCheck("cache", redis_client))

    # Create and include router
    health_router = create_health_router(manager)
    app.include_router(health_router)

    logger.info(
        f"Health checks configured for {service_name}",
        extra={
            'event': 'health_checks_configured',
            'service': service_name,
            'version': version,
            'checks': len(manager.checks),
        }
    )

    return manager

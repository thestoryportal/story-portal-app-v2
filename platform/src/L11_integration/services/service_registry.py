"""
L11 Integration Layer - Service Registry.

Service discovery and health tracking for all layers.
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import httpx

from ..models import (
    ServiceInfo,
    ServiceStatus,
    HealthCheckType,
    IntegrationError,
    ErrorCode,
)


logger = logging.getLogger(__name__)


class ServiceRegistry:
    """
    Service registry for layer discovery and health tracking.

    Maintains a registry of all layer services with health monitoring.
    """

    def __init__(self, l11_bridge=None):
        """Initialize service registry.

        Args:
            l11_bridge: L11Bridge instance for recording to L01
        """
        self.l11_bridge = l11_bridge
        self._services: Dict[str, ServiceInfo] = {}
        self._health_check_tasks: Dict[str, asyncio.Task] = {}
        self._running = False
        self._lock = asyncio.Lock()

    async def register_service(self, service: ServiceInfo) -> None:
        """
        Register a new service.

        Args:
            service: ServiceInfo to register

        Raises:
            IntegrationError: If service already registered
        """
        async with self._lock:
            if service.service_id in self._services:
                raise IntegrationError.from_code(
                    ErrorCode.E11007,
                    details={"service_id": service.service_id, "service_name": service.service_name},
                )

            self._services[service.service_id] = service
            logger.info(f"Registered service: {service.service_name} ({service.service_id})")

            # Record service registration in L01
            if self.l11_bridge:
                await self.l11_bridge.record_service_registry_event(
                    timestamp=datetime.now(),
                    service_id=service.service_id,
                    event_type="registered",
                    layer=service.layer,
                    host=service.host,
                    port=service.port,
                    health_status=service.status.value,
                    capabilities=service.capabilities,
                    metadata=service.metadata,
                )

            # Start health checking if configured
            if service.health_check and self._running:
                await self._start_health_check(service)

    async def deregister_service(self, service_id: str) -> None:
        """
        Deregister a service.

        Args:
            service_id: ID of service to deregister

        Raises:
            IntegrationError: If service not found
        """
        async with self._lock:
            if service_id not in self._services:
                raise IntegrationError.from_code(
                    ErrorCode.E11001,
                    details={"service_id": service_id},
                )

            # Stop health check task
            if service_id in self._health_check_tasks:
                self._health_check_tasks[service_id].cancel()
                del self._health_check_tasks[service_id]

            service = self._services[service_id]
            del self._services[service_id]
            logger.info(f"Deregistered service: {service.service_name} ({service_id})")

            # Record service deregistration in L01
            if self.l11_bridge:
                await self.l11_bridge.record_service_registry_event(
                    timestamp=datetime.now(),
                    service_id=service_id,
                    event_type="deregistered",
                    layer=service.layer,
                    health_status="offline",
                )

    async def get_service(self, service_id: str) -> ServiceInfo:
        """
        Get service by ID.

        Args:
            service_id: Service ID

        Returns:
            ServiceInfo

        Raises:
            IntegrationError: If service not found
        """
        async with self._lock:
            if service_id not in self._services:
                raise IntegrationError.from_code(
                    ErrorCode.E11001,
                    details={"service_id": service_id},
                )
            return self._services[service_id]

    async def get_service_by_name(self, service_name: str) -> Optional[ServiceInfo]:
        """
        Get service by name (returns first healthy instance).

        Args:
            service_name: Service name (e.g., "L02_runtime")

        Returns:
            ServiceInfo or None if not found
        """
        async with self._lock:
            # First try to find a healthy service
            for service in self._services.values():
                if service.service_name == service_name and service.is_healthy():
                    return service

            # Fall back to any service with this name
            for service in self._services.values():
                if service.service_name == service_name:
                    return service

            return None

    async def get_all_services(self) -> List[ServiceInfo]:
        """
        Get all registered services.

        Returns:
            List of ServiceInfo
        """
        async with self._lock:
            return list(self._services.values())

    async def get_healthy_services(self) -> List[ServiceInfo]:
        """
        Get all healthy services.

        Returns:
            List of healthy ServiceInfo
        """
        async with self._lock:
            return [s for s in self._services.values() if s.is_healthy()]

    async def update_service_health(self, service_id: str, status: ServiceStatus) -> None:
        """
        Update service health status.

        Args:
            service_id: Service ID
            status: New health status
        """
        async with self._lock:
            if service_id in self._services:
                service = self._services[service_id]
                old_status = service.status
                service.update_health(status)
                logger.debug(f"Updated health for {service.service_name}: {status.value}")

                # Record health change in L01 if status changed
                if old_status != status and self.l11_bridge:
                    await self.l11_bridge.record_service_registry_event(
                        timestamp=datetime.now(),
                        service_id=service_id,
                        event_type="health_change",
                        layer=service.layer,
                        health_status=status.value,
                        metadata={"previous_status": old_status.value},
                    )

    async def heartbeat(self, service_id: str) -> None:
        """
        Record a heartbeat from a service.

        Args:
            service_id: Service ID
        """
        async with self._lock:
            if service_id in self._services:
                self._services[service_id].update_heartbeat()

    async def start(self) -> None:
        """Start the service registry and begin health checking."""
        self._running = True
        logger.info("Service registry started")

        # Start health checks for all registered services
        async with self._lock:
            for service in self._services.values():
                if service.health_check:
                    await self._start_health_check(service)

    async def stop(self) -> None:
        """Stop the service registry and cancel all health checks."""
        self._running = False
        logger.info("Stopping service registry...")

        # Cancel all health check tasks
        for task in self._health_check_tasks.values():
            task.cancel()

        # Wait for tasks to complete
        if self._health_check_tasks:
            await asyncio.gather(*self._health_check_tasks.values(), return_exceptions=True)

        self._health_check_tasks.clear()
        logger.info("Service registry stopped")

    async def _start_health_check(self, service: ServiceInfo) -> None:
        """Start health check task for a service."""
        if service.service_id in self._health_check_tasks:
            return

        task = asyncio.create_task(self._health_check_loop(service))
        self._health_check_tasks[service.service_id] = task

    async def _health_check_loop(self, service: ServiceInfo) -> None:
        """Continuous health check loop for a service."""
        if not service.health_check:
            return

        consecutive_failures = 0
        consecutive_successes = 0

        logger.info(f"Starting health checks for {service.service_name}")

        while self._running:
            try:
                # Perform health check
                is_healthy = await self._perform_health_check(service)

                if is_healthy:
                    consecutive_successes += 1
                    consecutive_failures = 0

                    # Transition to healthy if threshold met
                    if consecutive_successes >= service.health_check.success_threshold:
                        if service.status != ServiceStatus.HEALTHY:
                            await self.update_service_health(service.service_id, ServiceStatus.HEALTHY)
                            logger.info(f"Service {service.service_name} is now HEALTHY")
                else:
                    consecutive_failures += 1
                    consecutive_successes = 0

                    # Transition to unhealthy if threshold met
                    if consecutive_failures >= service.health_check.failure_threshold:
                        if service.status != ServiceStatus.UNHEALTHY:
                            await self.update_service_health(service.service_id, ServiceStatus.UNHEALTHY)
                            logger.warning(f"Service {service.service_name} is now UNHEALTHY")

            except Exception as e:
                logger.error(f"Health check error for {service.service_name}: {e}")
                consecutive_failures += 1

            # Wait for next check
            await asyncio.sleep(service.health_check.interval_sec)

    async def _perform_health_check(self, service: ServiceInfo) -> bool:
        """
        Perform a single health check.

        Args:
            service: Service to check

        Returns:
            True if healthy, False otherwise
        """
        if not service.health_check:
            return True

        try:
            if service.health_check.check_type == HealthCheckType.HTTP:
                return await self._http_health_check(service)
            elif service.health_check.check_type == HealthCheckType.TCP:
                return await self._tcp_health_check(service)
            elif service.health_check.check_type == HealthCheckType.REDIS:
                return await self._redis_health_check(service)
            elif service.health_check.check_type == HealthCheckType.GRPC:
                # gRPC health check not implemented yet
                logger.warning(f"gRPC health check not implemented for {service.service_name}")
                return True
            else:
                logger.warning(f"Unknown health check type: {service.health_check.check_type}")
                return True

        except Exception as e:
            logger.debug(f"Health check failed for {service.service_name}: {e}")
            return False

    async def _http_health_check(self, service: ServiceInfo) -> bool:
        """Perform HTTP health check."""
        if not service.health_check:
            return False

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    service.health_check.endpoint,
                    timeout=service.health_check.timeout_sec,
                )
                return response.status_code == 200
            except Exception:
                return False

    async def _tcp_health_check(self, service: ServiceInfo) -> bool:
        """Perform TCP health check."""
        if not service.health_check:
            return False

        try:
            # Parse host:port from endpoint
            parts = service.health_check.endpoint.split(":")
            if len(parts) != 2:
                return False

            host, port = parts[0], int(parts[1])

            # Try to connect
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=service.health_check.timeout_sec,
            )
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False

    async def _redis_health_check(self, service: ServiceInfo) -> bool:
        """Perform Redis health check."""
        if not service.health_check:
            return False

        try:
            import redis.asyncio as redis

            r = redis.from_url(
                service.health_check.endpoint,
                socket_connect_timeout=service.health_check.timeout_sec,
            )
            await r.ping()
            await r.aclose()
            return True
        except Exception:
            return False

    async def get_health_summary(self) -> Dict[str, any]:
        """
        Get overall health summary.

        Returns:
            Dictionary with health statistics
        """
        async with self._lock:
            total = len(self._services)
            healthy = sum(1 for s in self._services.values() if s.status == ServiceStatus.HEALTHY)
            unhealthy = sum(1 for s in self._services.values() if s.status == ServiceStatus.UNHEALTHY)
            degraded = sum(1 for s in self._services.values() if s.status == ServiceStatus.DEGRADED)
            unknown = sum(1 for s in self._services.values() if s.status == ServiceStatus.UNKNOWN)

            return {
                "total_services": total,
                "healthy": healthy,
                "unhealthy": unhealthy,
                "degraded": degraded,
                "unknown": unknown,
                "health_percentage": (healthy / total * 100) if total > 0 else 0,
            }

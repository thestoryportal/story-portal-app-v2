"""
L11 Integration Layer - Main Integration Layer Class.

Orchestrates all integration layer services.
"""

import asyncio
import logging
from typing import Optional

from .services import (
    ServiceRegistry,
    EventBusManager,
    CircuitBreaker,
    RequestOrchestrator,
    SagaOrchestrator,
    ObservabilityCollector,
)
from .models import IntegrationError, ErrorCode


logger = logging.getLogger(__name__)


class IntegrationLayer:
    """
    Main integration layer class.

    Coordinates all integration layer services for cross-layer communication.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        observability_output_file: Optional[str] = None,
    ):
        """
        Initialize integration layer.

        Args:
            redis_url: Redis connection URL for event bus
            observability_output_file: Optional file path for observability data
        """
        # Initialize services
        self.service_registry = ServiceRegistry()
        self.event_bus = EventBusManager(redis_url=redis_url)
        self.circuit_breaker = CircuitBreaker()
        self.observability = ObservabilityCollector(output_file=observability_output_file)

        # Initialize orchestrators (depend on other services)
        self.request_orchestrator = RequestOrchestrator(
            service_registry=self.service_registry,
            circuit_breaker=self.circuit_breaker,
        )
        self.saga_orchestrator = SagaOrchestrator(
            request_orchestrator=self.request_orchestrator,
        )

        self._running = False

    async def start(self) -> None:
        """Start the integration layer and all services."""
        if self._running:
            logger.warning("Integration layer already running")
            return

        logger.info("Starting L11 Integration Layer...")

        try:
            # Start services in order
            await self.service_registry.start()
            await self.event_bus.start()
            await self.observability.start()
            await self.request_orchestrator.start()

            self._running = True
            logger.info("L11 Integration Layer started successfully")

        except Exception as e:
            logger.error(f"Failed to start integration layer: {e}")
            # Cleanup on failure
            await self.stop()
            raise IntegrationError.from_code(
                ErrorCode.E11903,
                details={"error": str(e)},
            )

    async def stop(self) -> None:
        """Stop the integration layer and all services."""
        if not self._running:
            logger.warning("Integration layer not running")
            return

        logger.info("Stopping L11 Integration Layer...")

        try:
            # Stop services in reverse order
            await self.request_orchestrator.stop()
            await self.observability.stop()
            await self.event_bus.stop()
            await self.service_registry.stop()

            self._running = False
            logger.info("L11 Integration Layer stopped successfully")

        except Exception as e:
            logger.error(f"Error stopping integration layer: {e}")
            raise IntegrationError.from_code(
                ErrorCode.E11904,
                details={"error": str(e)},
            )

    def is_running(self) -> bool:
        """Check if integration layer is running."""
        return self._running

    async def health_check(self) -> dict:
        """
        Perform health check on integration layer.

        Returns:
            Dictionary with health status
        """
        health = {
            "status": "healthy" if self._running else "unhealthy",
            "services": {},
        }

        if self._running:
            try:
                # Check service registry
                registry_health = await self.service_registry.get_health_summary()
                health["services"]["service_registry"] = {
                    "status": "healthy",
                    "details": registry_health,
                }

                # Check circuit breaker
                cb_metrics = self.circuit_breaker.get_metrics()
                health["services"]["circuit_breaker"] = {
                    "status": "healthy",
                    "details": cb_metrics,
                }

                # Check saga orchestrator
                saga_metrics = self.saga_orchestrator.get_metrics()
                health["services"]["saga_orchestrator"] = {
                    "status": "healthy",
                    "details": saga_metrics,
                }

            except Exception as e:
                logger.error(f"Health check error: {e}")
                health["status"] = "degraded"
                health["error"] = str(e)

        return health

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()

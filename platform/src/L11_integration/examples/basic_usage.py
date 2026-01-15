"""
L11 Integration Layer - Basic Usage Example.

Demonstrates the core functionality of the integration layer.
"""

import asyncio
import logging
from typing import Dict, Any

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from L11_integration import (
    IntegrationLayer,
    ServiceInfo,
    HealthCheck,
    HealthCheckType,
    EventMessage,
    SagaDefinition,
    SagaStep,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def example_service_registry():
    """Example: Service registry usage."""
    logger.info("=== Service Registry Example ===")

    integration = IntegrationLayer()
    await integration.start()

    try:
        # Register services
        services = [
            ServiceInfo.create(
                service_name="L02_runtime",
                service_version="0.1.0",
                endpoint="http://localhost:8002",
                health_check=HealthCheck(
                    check_type=HealthCheckType.HTTP,
                    endpoint="http://localhost:8002/health",
                    interval_sec=30,
                ),
            ),
            ServiceInfo.create(
                service_name="L03_tool_execution",
                service_version="0.1.0",
                endpoint="http://localhost:8003",
                health_check=HealthCheck(
                    check_type=HealthCheckType.HTTP,
                    endpoint="http://localhost:8003/health",
                    interval_sec=30,
                ),
            ),
        ]

        for service in services:
            await integration.service_registry.register_service(service)
            logger.info(f"Registered: {service.service_name}")

        # Get all services
        all_services = await integration.service_registry.get_all_services()
        logger.info(f"Total services registered: {len(all_services)}")

        # Get health summary
        health = await integration.service_registry.get_health_summary()
        logger.info(f"Health summary: {health}")

    finally:
        await integration.stop()


async def example_event_bus():
    """Example: Event bus usage."""
    logger.info("=== Event Bus Example ===")

    integration = IntegrationLayer()
    await integration.start()

    try:
        received_events = []

        # Event handler
        async def handle_agent_event(event: EventMessage):
            logger.info(f"Received event: {event.topic} - {event.event_type}")
            logger.info(f"Payload: {event.payload}")
            received_events.append(event)

        # Subscribe to agent events
        sub_id = await integration.event_bus.subscribe(
            topic="agent.*",
            handler=handle_agent_event,
            service_name="example_service",
        )
        logger.info(f"Subscribed to agent.* (subscription_id={sub_id})")

        # Wait for subscription to register
        await asyncio.sleep(0.5)

        # Publish events
        events = [
            EventMessage.create(
                topic="agent.created",
                event_type="created",
                payload={"agent_id": "agent-123", "name": "TestAgent"},
                source_service="example_publisher",
            ),
            EventMessage.create(
                topic="agent.started",
                event_type="started",
                payload={"agent_id": "agent-123"},
                source_service="example_publisher",
            ),
        ]

        for event in events:
            await integration.event_bus.publish(event)
            logger.info(f"Published: {event.topic}")

        # Wait for events to be processed
        await asyncio.sleep(1)

        logger.info(f"Received {len(received_events)} events")

        # Cleanup
        await integration.event_bus.unsubscribe(sub_id)

    finally:
        await integration.stop()


async def example_circuit_breaker():
    """Example: Circuit breaker usage."""
    logger.info("=== Circuit Breaker Example ===")

    integration = IntegrationLayer()
    await integration.start()

    try:
        # Simulated service call
        call_count = {"success": 0, "failure": 0}

        async def call_service():
            # Simulate intermittent failures
            call_count["success"] += 1
            if call_count["success"] % 3 == 0:
                call_count["failure"] += 1
                raise Exception("Service temporarily unavailable")
            return {"status": "success"}

        # Execute with circuit breaker protection
        for i in range(10):
            try:
                result = await integration.circuit_breaker.execute(
                    "example_service",
                    call_service,
                )
                logger.info(f"Call {i+1}: Success - {result}")
            except Exception as e:
                logger.warning(f"Call {i+1}: Failed - {e}")

            await asyncio.sleep(0.1)

        # Check circuit state
        state = await integration.circuit_breaker.get_state("example_service")
        if state:
            logger.info(f"Circuit breaker state: {state.state.value}")
            logger.info(f"Error rate: {state.get_error_rate():.2%}")

    finally:
        await integration.stop()


async def example_saga_orchestration():
    """Example: Saga orchestration usage."""
    logger.info("=== Saga Orchestration Example ===")

    integration = IntegrationLayer()
    await integration.start()

    try:
        # Define saga steps
        async def step1_build(context: Dict[str, Any]) -> Dict[str, Any]:
            logger.info("Executing: Build application")
            await asyncio.sleep(0.5)
            return {"build_id": "build-123", "status": "built"}

        async def step1_rollback(context: Dict[str, Any]) -> None:
            logger.info("Rolling back: Build application")
            await asyncio.sleep(0.2)

        async def step2_deploy(context: Dict[str, Any]) -> Dict[str, Any]:
            logger.info("Executing: Deploy application")
            await asyncio.sleep(0.5)
            build_id = context.get("build_id")
            return {"deployment_id": "deploy-456", "build_id": build_id}

        async def step2_rollback(context: Dict[str, Any]) -> None:
            logger.info("Rolling back: Deploy application")
            await asyncio.sleep(0.2)

        async def step3_verify(context: Dict[str, Any]) -> Dict[str, Any]:
            logger.info("Executing: Verify deployment")
            await asyncio.sleep(0.5)
            return {"verification": "passed"}

        # Create saga
        saga = SagaDefinition.create(
            saga_name="deploy_application",
            auto_compensate=True,
            steps=[
                SagaStep(
                    step_id="build",
                    step_name="Build application",
                    action=step1_build,
                    compensation=step1_rollback,
                ),
                SagaStep(
                    step_id="deploy",
                    step_name="Deploy application",
                    action=step2_deploy,
                    compensation=step2_rollback,
                ),
                SagaStep(
                    step_id="verify",
                    step_name="Verify deployment",
                    action=step3_verify,
                ),
            ],
        )

        # Execute saga
        logger.info("Starting saga execution...")
        execution = await integration.saga_orchestrator.execute_saga(
            saga,
            context={"environment": "production"},
        )

        logger.info(f"Saga completed: {execution.status.value}")
        logger.info(f"Final context: {execution.context}")

    finally:
        await integration.stop()


async def example_observability():
    """Example: Observability usage."""
    logger.info("=== Observability Example ===")

    integration = IntegrationLayer(
        observability_output_file="observability.log"
    )
    await integration.start()

    try:
        # Create counter metric
        counter = integration.observability.create_counter(
            name="l11_example_requests_total",
            labels={"service": "example"},
        )

        # Create gauge metric
        gauge = integration.observability.create_gauge(
            name="l11_example_active_connections",
            labels={"service": "example"},
        )

        # Create histogram metric
        histogram = integration.observability.create_histogram(
            name="l11_example_request_duration_seconds",
            labels={"service": "example"},
        )

        # Record metrics
        for i in range(10):
            await counter.inc()
            await gauge.set(float(i % 5))
            await histogram.observe(0.1 + (i * 0.01))
            await asyncio.sleep(0.1)

        logger.info("Recorded metrics")

        # Get metric summary
        summary = await integration.observability.get_metric_summary(
            "l11_example_request_duration_seconds",
            labels={"service": "example"},
        )
        logger.info(f"Duration summary: {summary}")

    finally:
        await integration.stop()


async def main():
    """Run all examples."""
    examples = [
        ("Service Registry", example_service_registry),
        ("Event Bus", example_event_bus),
        ("Circuit Breaker", example_circuit_breaker),
        ("Saga Orchestration", example_saga_orchestration),
        ("Observability", example_observability),
    ]

    for name, example_func in examples:
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"Running: {name}")
            logger.info(f"{'='*60}\n")
            await example_func()
        except Exception as e:
            logger.error(f"Error in {name}: {e}", exc_info=True)

        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())

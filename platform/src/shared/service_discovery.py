"""
Service Discovery with Consul

Provides service registration, discovery, and health checking for the Agentic Platform.
"""

import logging
import socket
import asyncio
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
import httpx
import json

logger = logging.getLogger(__name__)


@dataclass
class ServiceInstance:
    """Service instance information."""
    id: str
    name: str
    address: str
    port: int
    tags: List[str]
    meta: Dict[str, str]
    health_status: str = "passing"


class ConsulClient:
    """
    Async Consul client for service discovery.

    Features:
    - Service registration with health checks
    - Service discovery with caching
    - Health status monitoring
    - Graceful deregistration

    Example:
        consul = ConsulClient("http://consul:8500")

        # Register service
        await consul.register_service(
            name="l01-data-layer",
            port=8001,
            tags=["api", "v1"],
            health_check_path="/health/ready",
        )

        # Discover service
        instances = await consul.discover_service("l01-data-layer")
        for instance in instances:
            logger.info(f"{instance.name} at {instance.address}:{instance.port}")
    """

    def __init__(
        self,
        consul_url: str = "http://localhost:8500",
        timeout: float = 5.0,
    ):
        """
        Initialize Consul client.

        Args:
            consul_url: Consul HTTP API URL
            timeout: HTTP request timeout in seconds
        """
        self.consul_url = consul_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._service_id: Optional[str] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._service_id:
            await self.deregister_service(self._service_id)
        if self._client:
            await self._client.aclose()

    async def register_service(
        self,
        name: str,
        port: int,
        address: Optional[str] = None,
        service_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        meta: Optional[Dict[str, str]] = None,
        health_check_path: str = "/health/ready",
        health_check_interval: str = "10s",
        health_check_timeout: str = "5s",
        health_check_deregister_after: str = "1m",
    ) -> str:
        """
        Register service with Consul.

        Args:
            name: Service name
            port: Service port
            address: Service address (auto-detected if None)
            service_id: Unique service ID (generated if None)
            tags: Service tags for discovery
            meta: Service metadata
            health_check_path: HTTP health check endpoint
            health_check_interval: Health check interval
            health_check_timeout: Health check timeout
            health_check_deregister_after: Auto-deregister after failures

        Returns:
            Service ID

        Raises:
            Exception: If registration fails
        """
        # Auto-detect address if not provided
        if address is None:
            address = self._get_local_ip()

        # Generate service ID if not provided
        if service_id is None:
            import uuid
            service_id = f"{name}-{uuid.uuid4().hex[:8]}"

        # Build registration payload
        registration = {
            "ID": service_id,
            "Name": name,
            "Address": address,
            "Port": port,
            "Tags": tags or [],
            "Meta": meta or {},
            "Check": {
                "HTTP": f"http://{address}:{port}{health_check_path}",
                "Interval": health_check_interval,
                "Timeout": health_check_timeout,
                "DeregisterCriticalServiceAfter": health_check_deregister_after,
            },
        }

        logger.info(
            f"Registering service {name}",
            extra={
                'event': 'service_registration',
                'service_id': service_id,
                'service_name': name,
                'address': address,
                'port': port,
            }
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.put(
                f"{self.consul_url}/v1/agent/service/register",
                json=registration,
            )
            response.raise_for_status()

        self._service_id = service_id

        logger.info(
            f"Service {name} registered successfully",
            extra={
                'event': 'service_registered',
                'service_id': service_id,
            }
        )

        return service_id

    async def deregister_service(self, service_id: str):
        """
        Deregister service from Consul.

        Args:
            service_id: Service ID to deregister
        """
        logger.info(
            f"Deregistering service {service_id}",
            extra={
                'event': 'service_deregistration',
                'service_id': service_id,
            }
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(
                    f"{self.consul_url}/v1/agent/service/deregister/{service_id}"
                )
                response.raise_for_status()

            logger.info(
                f"Service {service_id} deregistered",
                extra={
                    'event': 'service_deregistered',
                    'service_id': service_id,
                }
            )
        except Exception as e:
            logger.error(
                f"Failed to deregister service {service_id}: {e}",
                extra={
                    'event': 'service_deregistration_failed',
                    'service_id': service_id,
                    'error': str(e),
                },
                exc_info=True,
            )

    async def discover_service(
        self,
        name: str,
        tag: Optional[str] = None,
        passing_only: bool = True,
    ) -> List[ServiceInstance]:
        """
        Discover service instances.

        Args:
            name: Service name to discover
            tag: Filter by tag (optional)
            passing_only: Only return healthy instances

        Returns:
            List of service instances
        """
        # Build query parameters
        params = {}
        if tag:
            params["tag"] = tag
        if passing_only:
            params["passing"] = "true"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.consul_url}/v1/health/service/{name}",
                params=params,
            )
            response.raise_for_status()
            data = response.json()

        # Parse response
        instances = []
        for entry in data:
            service = entry.get("Service", {})
            checks = entry.get("Checks", [])

            # Determine health status
            health_status = "passing"
            for check in checks:
                if check.get("Status") != "passing":
                    health_status = check.get("Status", "unknown")
                    break

            instances.append(ServiceInstance(
                id=service.get("ID"),
                name=service.get("Service"),
                address=service.get("Address"),
                port=service.get("Port"),
                tags=service.get("Tags", []),
                meta=service.get("Meta", {}),
                health_status=health_status,
            ))

        logger.debug(
            f"Discovered {len(instances)} instances of {name}",
            extra={
                'event': 'service_discovered',
                'service_name': name,
                'instance_count': len(instances),
            }
        )

        return instances

    async def get_service_address(
        self,
        name: str,
        tag: Optional[str] = None,
        strategy: str = "round-robin",
    ) -> Optional[tuple[str, int]]:
        """
        Get service address for load balancing.

        Args:
            name: Service name
            tag: Filter by tag (optional)
            strategy: Load balancing strategy ("round-robin", "random", "first")

        Returns:
            Tuple of (address, port) or None if no instances found
        """
        instances = await self.discover_service(name, tag=tag, passing_only=True)

        if not instances:
            logger.warning(
                f"No healthy instances found for {name}",
                extra={
                    'event': 'no_service_instances',
                    'service_name': name,
                }
            )
            return None

        # Select instance based on strategy
        if strategy == "first":
            instance = instances[0]
        elif strategy == "random":
            import random
            instance = random.choice(instances)
        elif strategy == "round-robin":
            # Simple round-robin using instance count
            index = hash(name) % len(instances)
            instance = instances[index]
        else:
            instance = instances[0]

        return (instance.address, instance.port)

    async def list_services(self) -> Dict[str, List[str]]:
        """
        List all registered services.

        Returns:
            Dictionary mapping service names to tags
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.consul_url}/v1/catalog/services"
            )
            response.raise_for_status()
            return response.json()

    def _get_local_ip(self) -> str:
        """Get local IP address."""
        try:
            # Create socket to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"


class ServiceRegistry:
    """
    High-level service registry with automatic registration and health checks.

    Example:
        from fastapi import FastAPI

        app = FastAPI()
        registry = ServiceRegistry(
            consul_url="http://consul:8500",
            service_name="l01-data-layer",
            service_port=8001,
        )

        @app.on_event("startup")
        async def startup():
            await registry.register()

        @app.on_event("shutdown")
        async def shutdown():
            await registry.deregister()
    """

    def __init__(
        self,
        consul_url: str,
        service_name: str,
        service_port: int,
        service_address: Optional[str] = None,
        tags: Optional[List[str]] = None,
        meta: Optional[Dict[str, str]] = None,
        health_check_path: str = "/health/ready",
    ):
        """
        Initialize service registry.

        Args:
            consul_url: Consul HTTP API URL
            service_name: Service name
            service_port: Service port
            service_address: Service address (auto-detected if None)
            tags: Service tags
            meta: Service metadata
            health_check_path: Health check endpoint path
        """
        self.consul = ConsulClient(consul_url)
        self.service_name = service_name
        self.service_port = service_port
        self.service_address = service_address
        self.tags = tags or []
        self.meta = meta or {}
        self.health_check_path = health_check_path
        self.service_id: Optional[str] = None

    async def register(self):
        """Register service with Consul."""
        self.service_id = await self.consul.register_service(
            name=self.service_name,
            port=self.service_port,
            address=self.service_address,
            tags=self.tags,
            meta=self.meta,
            health_check_path=self.health_check_path,
        )

    async def deregister(self):
        """Deregister service from Consul."""
        if self.service_id:
            await self.consul.deregister_service(self.service_id)

    async def discover(self, service_name: str) -> List[ServiceInstance]:
        """Discover service instances."""
        return await self.consul.discover_service(service_name)

    async def get_service_url(self, service_name: str) -> Optional[str]:
        """
        Get service URL for making requests.

        Args:
            service_name: Service to discover

        Returns:
            Service URL (http://address:port) or None
        """
        result = await self.consul.get_service_address(service_name)
        if result:
            address, port = result
            return f"http://{address}:{port}"
        return None


# Convenience functions for FastAPI integration

def create_service_registry(
    service_name: str,
    service_port: int,
    consul_url: str = "http://consul:8500",
    tags: Optional[List[str]] = None,
    **kwargs
) -> ServiceRegistry:
    """
    Create service registry for FastAPI application.

    Args:
        service_name: Service name
        service_port: Service port
        consul_url: Consul URL
        tags: Service tags
        **kwargs: Additional registry arguments

    Returns:
        ServiceRegistry instance

    Example:
        from fastapi import FastAPI

        app = FastAPI()
        registry = create_service_registry("l01-data-layer", 8001)

        @app.on_event("startup")
        async def startup():
            await registry.register()

        @app.on_event("shutdown")
        async def shutdown():
            await registry.deregister()
    """
    return ServiceRegistry(
        consul_url=consul_url,
        service_name=service_name,
        service_port=service_port,
        tags=tags,
        **kwargs
    )


async def register_with_consul(
    service_name: str,
    service_port: int,
    consul_url: str = "http://consul:8500",
    tags: Optional[List[str]] = None,
) -> str:
    """
    Quick function to register service with Consul.

    Args:
        service_name: Service name
        service_port: Service port
        consul_url: Consul URL
        tags: Service tags

    Returns:
        Service ID
    """
    async with ConsulClient(consul_url) as consul:
        return await consul.register_service(
            name=service_name,
            port=service_port,
            tags=tags,
        )

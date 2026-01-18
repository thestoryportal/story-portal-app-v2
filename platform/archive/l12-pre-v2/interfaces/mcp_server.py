"""MCP Server for L12 Natural Language Interface.

This module implements a Model Context Protocol (MCP) server for Claude CLI
integration. It provides 6 tools for seamless access to platform services:

1. invoke_service - Execute a service method
2. search_services - Fuzzy search services with disambiguation
3. list_services - List all services or filter by layer
4. get_service_info - Get detailed service information
5. list_methods - List methods available on a service
6. get_session_info - Get session metrics and state

Example:
    # Run MCP server for Claude CLI
    python -m L12_nl_interface.interfaces.mcp_server
"""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List, Optional

from ..config.settings import get_settings
from ..core.service_factory import ServiceFactory
from ..core.service_registry import ServiceRegistry, get_registry
from ..core.session_manager import SessionManager
from ..models.command_models import InvokeRequest, InvocationStatus
from ..routing.command_router import CommandRouter
from ..routing.exact_matcher import ExactMatcher
from ..routing.fuzzy_matcher import FuzzyMatcher
from ..services.memory_monitor import MemoryMonitor

logger = logging.getLogger(__name__)

# MCP protocol version
MCP_VERSION = "2024-11-05"

# Default session ID for MCP (single-user context)
DEFAULT_SESSION_ID = "mcp-session-default"


class MCPServer:
    """MCP Server for Claude CLI integration.

    Implements the Model Context Protocol for exposing L12 services
    to Claude CLI as native tools.

    Attributes:
        registry: ServiceRegistry for metadata
        factory: ServiceFactory for service creation
        session_manager: SessionManager for lifecycle
        command_router: CommandRouter for invocation
        exact_matcher: ExactMatcher for lookups
        fuzzy_matcher: FuzzyMatcher for search
        session_id: Default session ID for MCP context
    """

    def __init__(self):
        """Initialize MCP server with L12 components."""
        self.settings = get_settings()
        self.settings.configure_logging()

        # Initialize core components
        self.registry = get_registry()
        self.factory = ServiceFactory(self.registry)
        self.memory_monitor = MemoryMonitor(
            enabled=self.settings.enable_memory_monitor,
            memory_limit_mb=self.settings.memory_limit_mb,
        )
        self.session_manager = SessionManager(
            self.factory,
            self.memory_monitor,
            ttl_seconds=self.settings.session_ttl_seconds,
        )

        # Initialize routing
        self.exact_matcher = ExactMatcher(self.registry)
        self.fuzzy_matcher = FuzzyMatcher(
            self.registry, use_semantic=self.settings.use_semantic_matching
        )
        self.command_router = CommandRouter(
            self.registry,
            self.factory,
            self.session_manager,
            self.exact_matcher,
            self.fuzzy_matcher,
        )

        self.session_id = DEFAULT_SESSION_ID

        logger.info(
            f"MCP Server initialized: {len(self.registry.list_all_services())} services"
        )

    async def start(self):
        """Start MCP server and session manager."""
        await self.session_manager.start()
        logger.info("MCP Server started")

    async def stop(self):
        """Stop MCP server and cleanup."""
        await self.session_manager.stop()
        logger.info("MCP Server stopped")

    def get_tools_manifest(self) -> List[Dict[str, Any]]:
        """Get MCP tools manifest for Claude CLI.

        Returns:
            List of tool definitions with schemas

        Example:
            >>> server = MCPServer()
            >>> tools = server.get_tools_manifest()
            >>> print(f"Available tools: {len(tools)}")
        """
        return [
            {
                "name": "invoke_service",
                "description": (
                    "Execute a service method with parameters. "
                    "Use format: 'ServiceName.method_name' or just 'ServiceName' for default method. "
                    "Example: invoke_service(command='PlanningService.create_plan', parameters={'goal': 'test'})"
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Service and method in format 'ServiceName.method_name'",
                        },
                        "parameters": {
                            "type": "object",
                            "description": "Method parameters as key-value pairs",
                            "default": {},
                        },
                        "timeout_seconds": {
                            "type": "number",
                            "description": "Optional timeout in seconds",
                        },
                    },
                    "required": ["command"],
                },
            },
            {
                "name": "search_services",
                "description": (
                    "Search for services using natural language. "
                    "Returns ranked list of matching services with scores. "
                    "Use this to discover available services. "
                    "Example: search_services(query='create a plan', threshold=0.6)"
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language search query",
                        },
                        "threshold": {
                            "type": "number",
                            "description": "Minimum match score 0.0-1.0 (default: 0.7)",
                            "default": 0.7,
                            "minimum": 0.0,
                            "maximum": 1.0,
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum results to return (default: 10)",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50,
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "list_services",
                "description": (
                    "List all available services or filter by layer. "
                    "Shows service name, description, layer, and method count. "
                    "Layers: L01-L11 (e.g., L05 for Planning Layer). "
                    "Example: list_services(layer='L05')"
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "layer": {
                            "type": "string",
                            "description": "Optional layer filter (e.g., 'L05')",
                        }
                    },
                },
            },
            {
                "name": "get_service_info",
                "description": (
                    "Get detailed information about a specific service. "
                    "Returns full metadata including methods, parameters, dependencies. "
                    "Example: get_service_info(service_name='PlanningService')"
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "service_name": {
                            "type": "string",
                            "description": "Name of the service to get info for",
                        }
                    },
                    "required": ["service_name"],
                },
            },
            {
                "name": "list_methods",
                "description": (
                    "List all methods available on a service. "
                    "Shows method name, description, parameters, and return type. "
                    "Example: list_methods(service_name='PlanningService')"
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "service_name": {
                            "type": "string",
                            "description": "Name of the service",
                        }
                    },
                    "required": ["service_name"],
                },
            },
            {
                "name": "get_session_info",
                "description": (
                    "Get information about the current session. "
                    "Shows active services, memory usage, age, and metrics. "
                    "Example: get_session_info()"
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]

    async def invoke_service(
        self,
        command: str,
        parameters: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[float] = None,
    ) -> str:
        """Tool: Execute a service method.

        Args:
            command: Service and method (e.g., "PlanningService.create_plan")
            parameters: Method parameters
            timeout_seconds: Optional timeout

        Returns:
            Formatted result string

        Example:
            >>> result = await server.invoke_service(
            ...     "PlanningService.create_plan",
            ...     {"goal": "test"}
            ... )
        """
        try:
            response = await self.command_router.route(
                command, self.session_id, parameters or {}, timeout_seconds
            )

            if response.status == InvocationStatus.SUCCESS:
                result_str = json.dumps(response.result, indent=2) if response.result else "Success (no return value)"
                return (
                    f"✅ Service invocation successful\n"
                    f"Service: {response.service_name}\n"
                    f"Method: {response.method_name}\n"
                    f"Execution time: {response.execution_time_ms:.2f}ms\n\n"
                    f"Result:\n{result_str}"
                )
            else:
                error = response.error
                return (
                    f"❌ Service invocation failed\n"
                    f"Service: {response.service_name}\n"
                    f"Method: {response.method_name}\n"
                    f"Error code: {error.code.value if error else 'unknown'}\n"
                    f"Error message: {error.message if error else 'unknown'}\n\n"
                    f"Details: {json.dumps(error.details, indent=2) if error and error.details else 'none'}"
                )

        except Exception as e:
            logger.error(f"Error invoking service: {e}", exc_info=True)
            return f"❌ Error invoking service: {str(e)}"

    async def search_services(
        self, query: str, threshold: float = 0.7, max_results: int = 10
    ) -> str:
        """Tool: Search services using fuzzy matching.

        Args:
            query: Natural language query
            threshold: Minimum match score
            max_results: Maximum results

        Returns:
            Formatted search results

        Example:
            >>> results = await server.search_services("create a plan")
        """
        try:
            matches = self.fuzzy_matcher.match(query, threshold, max_results)

            if not matches:
                return (
                    f"No services found matching '{query}' with threshold {threshold}\n\n"
                    f"Try:\n"
                    f"- Lowering the threshold (e.g., 0.5)\n"
                    f"- Using different keywords\n"
                    f"- Use list_services() to see all available services"
                )

            result = f"🔍 Found {len(matches)} service(s) matching '{query}':\n\n"
            for i, match in enumerate(matches, 1):
                service = match.service
                result += (
                    f"{i}. {service.service_name} (score: {match.score:.2f})\n"
                    f"   Layer: {service.layer}\n"
                    f"   Description: {service.description}\n"
                    f"   Keywords: {', '.join(service.keywords[:5])}\n"
                    f"   Methods: {len(service.methods)} available\n"
                    f"   Match reason: {match.match_reason}\n\n"
                )

            result += (
                f"💡 To use a service:\n"
                f"   invoke_service(command='{matches[0].service.service_name}.method_name', parameters={{...}})\n"
                f"   Or get details: get_service_info(service_name='{matches[0].service.service_name}')"
            )

            return result

        except Exception as e:
            logger.error(f"Error searching services: {e}", exc_info=True)
            return f"❌ Error searching services: {str(e)}"

    async def list_services(self, layer: Optional[str] = None) -> str:
        """Tool: List all services or filter by layer.

        Args:
            layer: Optional layer filter (e.g., "L05")

        Returns:
            Formatted service list

        Example:
            >>> services = await server.list_services(layer="L05")
        """
        try:
            if layer:
                services = self.registry.list_by_layer(layer)
                title = f"📋 Services in {layer}"
            else:
                services = self.registry.list_all_services()
                title = "📋 All Available Services"

            if not services:
                return f"No services found{' in layer ' + layer if layer else ''}"

            # Group by layer
            by_layer: Dict[str, List] = {}
            for service in services:
                if service.layer not in by_layer:
                    by_layer[service.layer] = []
                by_layer[service.layer].append(service)

            result = f"{title} ({len(services)} total):\n\n"

            for layer_name in sorted(by_layer.keys()):
                layer_services = by_layer[layer_name]
                result += f"### {layer_name} ({len(layer_services)} services)\n"

                for service in layer_services:
                    result += (
                        f"  • {service.service_name}\n"
                        f"    {service.description}\n"
                        f"    Methods: {len(service.methods)} | "
                        f"Dependencies: {len(service.dependencies)}\n"
                    )

                result += "\n"

            result += (
                f"💡 To learn more about a service:\n"
                f"   get_service_info(service_name='ServiceName')\n"
                f"   Or search: search_services(query='your query')"
            )

            return result

        except Exception as e:
            logger.error(f"Error listing services: {e}", exc_info=True)
            return f"❌ Error listing services: {str(e)}"

    async def get_service_info(self, service_name: str) -> str:
        """Tool: Get detailed service information.

        Args:
            service_name: Name of service

        Returns:
            Formatted service details

        Example:
            >>> info = await server.get_service_info("PlanningService")
        """
        try:
            service = self.registry.get_service(service_name)
            if not service:
                # Try fuzzy match
                matches = self.fuzzy_matcher.match(service_name, threshold=0.6, max_results=3)
                if matches:
                    suggestions = [m.service.service_name for m in matches]
                    return (
                        f"❌ Service '{service_name}' not found\n\n"
                        f"Did you mean:\n" + "\n".join(f"  • {s}" for s in suggestions)
                    )
                return f"❌ Service '{service_name}' not found"

            result = (
                f"📖 Service Information: {service.service_name}\n\n"
                f"Layer: {service.layer}\n"
                f"Description: {service.description}\n"
                f"Module: {service.module_path}\n"
                f"Class: {service.class_name}\n"
                f"Async Init: {'Yes' if service.requires_async_init else 'No'}\n\n"
            )

            if service.keywords:
                result += f"Keywords: {', '.join(service.keywords)}\n\n"

            if service.dependencies:
                result += f"Dependencies ({len(service.dependencies)}):\n"
                for dep in service.dependencies:
                    result += f"  • {dep}\n"
                result += "\n"

            if service.methods:
                result += f"Methods ({len(service.methods)}):\n\n"
                for method in service.methods:
                    result += f"  📌 {method.name}()\n"
                    result += f"     {method.description}\n"

                    if method.parameters:
                        result += f"     Parameters:\n"
                        for param in method.parameters:
                            required = "required" if param.required else "optional"
                            result += f"       - {param.name}: {param.type} ({required})\n"
                            if param.description:
                                result += f"         {param.description}\n"

                    if method.returns:
                        result += f"     Returns: {method.returns}\n"

                    result += "\n"

            result += (
                f"💡 To invoke:\n"
                f"   invoke_service(command='{service.service_name}.method_name', parameters={{...}})"
            )

            return result

        except Exception as e:
            logger.error(f"Error getting service info: {e}", exc_info=True)
            return f"❌ Error getting service info: {str(e)}"

    async def list_methods(self, service_name: str) -> str:
        """Tool: List methods for a service.

        Args:
            service_name: Name of service

        Returns:
            Formatted method list

        Example:
            >>> methods = await server.list_methods("PlanningService")
        """
        try:
            service = self.registry.get_service(service_name)
            if not service:
                return f"❌ Service '{service_name}' not found"

            if not service.methods:
                return f"ℹ️ Service '{service_name}' has no documented methods"

            result = f"📋 Methods for {service_name} ({len(service.methods)} total):\n\n"

            for i, method in enumerate(service.methods, 1):
                result += f"{i}. {method.name}()\n"
                result += f"   {method.description}\n"

                if method.parameters:
                    param_strs = []
                    for param in method.parameters:
                        req = "required" if param.required else "optional"
                        param_strs.append(f"{param.name}: {param.type} ({req})")
                    result += f"   Parameters: {', '.join(param_strs)}\n"

                if method.returns:
                    result += f"   Returns: {method.returns}\n"

                result += "\n"

            result += (
                f"💡 To invoke:\n"
                f"   invoke_service(command='{service_name}.{service.methods[0].name}', parameters={{...}})"
            )

            return result

        except Exception as e:
            logger.error(f"Error listing methods: {e}", exc_info=True)
            return f"❌ Error listing methods: {str(e)}"

    async def get_session_info(self) -> str:
        """Tool: Get current session information.

        Returns:
            Formatted session metrics

        Example:
            >>> info = await server.get_session_info()
        """
        try:
            metrics = self.session_manager.get_session_metrics(self.session_id)

            if not metrics:
                return (
                    f"ℹ️ No active session yet\n\n"
                    f"A session will be created when you first invoke a service."
                )

            result = (
                f"📊 Session Information: {self.session_id}\n\n"
                f"Created: {metrics['created_at']}\n"
                f"Last accessed: {metrics['last_accessed']}\n"
                f"Age: {metrics['age_seconds']:.1f} seconds\n"
                f"Idle: {metrics['idle_seconds']:.1f} seconds\n"
                f"Active services: {metrics['service_count']}\n"
                f"Memory usage: {metrics['memory_mb']:.2f} MB\n"
                f"Peak memory: {metrics['memory_peak_mb']:.2f} MB\n"
                f"Average memory: {metrics['memory_average_mb']:.2f} MB\n"
                f"Expired: {'Yes' if metrics['is_expired'] else 'No'}\n"
            )

            # Get cached services
            cached = self.factory.get_cached_services(self.session_id)
            if cached:
                result += f"\nCached services: {', '.join(cached)}\n"

            return result

        except Exception as e:
            logger.error(f"Error getting session info: {e}", exc_info=True)
            return f"❌ Error getting session info: {str(e)}"

    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Handle a tool call from Claude CLI.

        Args:
            tool_name: Name of the tool to invoke
            arguments: Tool arguments

        Returns:
            Tool result as formatted string

        Example:
            >>> result = await server.handle_tool_call("search_services", {"query": "plan"})
        """
        try:
            if tool_name == "invoke_service":
                return await self.invoke_service(**arguments)
            elif tool_name == "search_services":
                return await self.search_services(**arguments)
            elif tool_name == "list_services":
                return await self.list_services(**arguments)
            elif tool_name == "get_service_info":
                return await self.get_service_info(**arguments)
            elif tool_name == "list_methods":
                return await self.list_methods(**arguments)
            elif tool_name == "get_session_info":
                return await self.get_session_info(**arguments)
            else:
                return f"❌ Unknown tool: {tool_name}"

        except Exception as e:
            logger.error(f"Error handling tool call '{tool_name}': {e}", exc_info=True)
            return f"❌ Error: {str(e)}"


async def main():
    """Main entry point for MCP server.

    Runs the MCP server and handles stdio communication with Claude CLI.
    """
    server = MCPServer()
    await server.start()

    try:
        # MCP protocol communication via stdio
        logger.info("MCP Server ready for Claude CLI connections")

        # For now, just demonstrate the tools
        print("L12 MCP Server - Available Tools:")
        print("=" * 60)
        tools = server.get_tools_manifest()
        for tool in tools:
            print(f"\n{tool['name']}")
            print(f"  {tool['description']}")

        print("\n" + "=" * 60)
        print(f"Total tools available: {len(tools)}")
        print("\nNote: Full MCP protocol implementation requires stdio handling")
        print("      This server is ready for integration with Claude CLI")

    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())

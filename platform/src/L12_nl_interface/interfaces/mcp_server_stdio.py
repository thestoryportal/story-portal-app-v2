#!/usr/bin/env python3
"""MCP Server for L12 - STDIO Protocol Implementation.

This module implements a fully MCP-compliant server using stdio communication
for seamless Claude CLI integration.

Usage:
    python -m src.L12_nl_interface.interfaces.mcp_server_stdio
"""

import asyncio
import json
import logging
import sys
from typing import Any, Dict

from ..config.settings import get_settings
from ..core.service_factory import ServiceFactory
from ..core.service_registry import get_registry
from ..core.session_manager import SessionManager
from ..routing.command_router import CommandRouter
from ..routing.exact_matcher import ExactMatcher
from ..routing.fuzzy_matcher import FuzzyMatcher
from ..services.memory_monitor import MemoryMonitor

# Configure logging to file (not stdout/stderr to avoid MCP protocol interference)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("/tmp/l12_mcp_server.log"),
    ],
)
logger = logging.getLogger(__name__)

# MCP Protocol Constants
MCP_VERSION = "2024-11-05"
DEFAULT_SESSION_ID = "mcp-session-default"


class L12MCPServer:
    """MCP Server for L12 Natural Language Interface.

    Implements stdio-based MCP protocol for Claude CLI integration.
    """

    def __init__(self):
        """Initialize L12 MCP server with all components."""
        try:
            self.settings = get_settings()

            # Initialize core components
            self.registry = get_registry()
            self.factory = ServiceFactory(self.registry)
            self.memory_monitor = MemoryMonitor(enabled=False)  # Disable for MCP
            self.session_manager = SessionManager(
                self.factory,
                self.memory_monitor,
                ttl_seconds=self.settings.session_ttl_seconds,
            )

            # Initialize routing
            self.exact_matcher = ExactMatcher(self.registry)
            self.fuzzy_matcher = FuzzyMatcher(
                self.registry, use_semantic=False  # Disable for lower latency
            )
            self.command_router = CommandRouter(
                self.registry,
                self.factory,
                self.session_manager,
                self.exact_matcher,
                self.fuzzy_matcher,
            )

            self.session_id = DEFAULT_SESSION_ID
            self.running = False

            logger.info(f"L12 MCP Server initialized with {len(self.registry.list_all_services())} services")

        except Exception as e:
            logger.error(f"Failed to initialize MCP server: {e}", exc_info=True)
            raise

    async def start(self):
        """Start the MCP server."""
        await self.session_manager.start()
        self.running = True
        logger.info("L12 MCP Server started")

    async def stop(self):
        """Stop the MCP server."""
        self.running = False
        await self.session_manager.stop()
        logger.info("L12 MCP Server stopped")

    def get_server_info(self) -> Dict[str, Any]:
        """Get MCP server information."""
        return {
            "protocolVersion": MCP_VERSION,
            "serverInfo": {
                "name": "l12-platform",
                "version": "1.0.0",
            },
            "capabilities": {
                "tools": {},
            },
        }

    def get_tools(self) -> list:
        """Get list of available MCP tools."""
        return [
            {
                "name": "invoke_service",
                "description": (
                    "Execute a platform service method. Use format: 'ServiceName.method_name'. "
                    "Example: invoke_service(command='PlanningService.create_plan', parameters={'goal': 'test'})"
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Service and method in format 'ServiceName.method_name'",
                        },
                        "parameters": {
                            "type": "object",
                            "description": "Method parameters as key-value pairs",
                        },
                    },
                    "required": ["command"],
                },
            },
            {
                "name": "search_services",
                "description": (
                    "Search for platform services using natural language. "
                    "Returns ranked list of matching services with scores. "
                    "Example: search_services(query='create a plan', threshold=0.6)"
                ),
                "inputSchema": {
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
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum results to return (default: 10)",
                            "default": 10,
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "list_services",
                "description": (
                    "List all available platform services or filter by layer. "
                    "Shows service name, description, layer, and available methods. "
                    "Example: list_services(layer='L05')"
                ),
                "inputSchema": {
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
                    "Get detailed information about a specific service including methods, "
                    "parameters, dependencies, and usage examples. "
                    "Example: get_service_info(service_name='PlanningService')"
                ),
                "inputSchema": {
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
                    "List all methods available on a service with parameters and return types. "
                    "Example: list_methods(service_name='PlanningService')"
                ),
                "inputSchema": {
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
                    "Get information about the current session including active services, "
                    "memory usage, and metrics. "
                    "Example: get_session_info()"
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]

    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Handle MCP tool call."""
        try:
            logger.info(f"Handling tool call: {tool_name} with args: {arguments}")

            if tool_name == "invoke_service":
                return await self._invoke_service(arguments)
            elif tool_name == "search_services":
                return await self._search_services(arguments)
            elif tool_name == "list_services":
                return await self._list_services(arguments)
            elif tool_name == "get_service_info":
                return await self._get_service_info(arguments)
            elif tool_name == "list_methods":
                return await self._list_methods(arguments)
            elif tool_name == "get_session_info":
                return await self._get_session_info(arguments)
            else:
                return f"❌ Unknown tool: {tool_name}"

        except Exception as e:
            logger.error(f"Error handling tool call: {e}", exc_info=True)
            return f"❌ Error: {str(e)}"

    async def _invoke_service(self, args: Dict[str, Any]) -> str:
        """Execute a service method."""
        command = args.get("command")
        parameters = args.get("parameters", {})

        response = await self.command_router.route(
            command, self.session_id, parameters
        )

        if response.status.value == "success":
            result_str = json.dumps(response.result, indent=2) if response.result else "Success"
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
                f"Error: {error.message if error else 'unknown'}"
            )

    async def _search_services(self, args: Dict[str, Any]) -> str:
        """Search for services."""
        query = args.get("query")
        threshold = args.get("threshold", 0.7)
        max_results = args.get("max_results", 10)

        matches = self.fuzzy_matcher.match(query, threshold, max_results)

        if not matches:
            return f"No services found matching '{query}'"

        result = f"🔍 Found {len(matches)} service(s) matching '{query}':\n\n"
        for i, match in enumerate(matches, 1):
            service = match.service
            result += (
                f"{i}. **{service.service_name}** (score: {match.score:.2f})\n"
                f"   Layer: {service.layer}\n"
                f"   Description: {service.description}\n"
                f"   Methods: {len(service.methods)} available\n\n"
            )

        return result

    async def _list_services(self, args: Dict[str, Any]) -> str:
        """List all services or filter by layer."""
        layer = args.get("layer")

        if layer:
            services = self.registry.list_by_layer(layer)
            title = f"📋 Services in {layer}"
        else:
            services = self.registry.list_all_services()
            title = "📋 All Available Services"

        if not services:
            return f"No services found"

        result = f"{title} ({len(services)} total):\n\n"
        for service in services:
            result += (
                f"• **{service.service_name}** ({service.layer})\n"
                f"  {service.description}\n"
                f"  Methods: {len(service.methods)}\n\n"
            )

        return result

    async def _get_service_info(self, args: Dict[str, Any]) -> str:
        """Get detailed service information."""
        service_name = args.get("service_name")
        service = self.registry.get_service(service_name)

        if not service:
            return f"❌ Service '{service_name}' not found"

        result = (
            f"📖 **{service.service_name}**\n\n"
            f"**Description**: {service.description}\n"
            f"**Layer**: {service.layer}\n"
            f"**Module**: {service.module_path}\n"
            f"**Class**: {service.class_name}\n\n"
        )

        if service.methods:
            result += f"**Methods** ({len(service.methods)}):\n\n"
            for method in service.methods:
                result += f"• **{method.name}()**\n"
                result += f"  {method.description}\n"
                if method.parameters:
                    result += f"  Parameters: "
                    params = [f"{p.name}: {p.type}" for p in method.parameters]
                    result += ", ".join(params) + "\n"
                if method.returns:
                    result += f"  Returns: {method.returns}\n"
                result += "\n"

        return result

    async def _list_methods(self, args: Dict[str, Any]) -> str:
        """List methods for a service."""
        service_name = args.get("service_name")
        service = self.registry.get_service(service_name)

        if not service:
            return f"❌ Service '{service_name}' not found"

        if not service.methods:
            return f"ℹ️ Service '{service_name}' has no documented methods"

        result = f"📋 Methods for **{service_name}** ({len(service.methods)} total):\n\n"
        for i, method in enumerate(service.methods, 1):
            result += f"{i}. **{method.name}()**\n"
            result += f"   {method.description}\n\n"

        return result

    async def _get_session_info(self, args: Dict[str, Any]) -> str:
        """Get current session information."""
        metrics = self.session_manager.get_session_metrics(self.session_id)

        if not metrics:
            return "ℹ️ No active session yet"

        return (
            f"📊 **Session Information**\n\n"
            f"Session ID: {self.session_id}\n"
            f"Active services: {metrics['service_count']}\n"
            f"Memory usage: {metrics['memory_mb']:.2f} MB\n"
            f"Age: {metrics['age_seconds']:.1f} seconds\n"
        )

    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP message."""
        try:
            method = message.get("method")
            params = message.get("params", {})
            msg_id = message.get("id")

            logger.info(f"Received message: method={method}, id={msg_id}")

            if method == "initialize":
                result = self.get_server_info()
            elif method == "tools/list":
                result = {"tools": self.get_tools()}
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                content = await self.handle_tool_call(tool_name, arguments)
                result = {
                    "content": [
                        {
                            "type": "text",
                            "text": content,
                        }
                    ]
                }
            else:
                raise ValueError(f"Unknown method: {method}")

            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": result,
            }

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            return {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "error": {
                    "code": -32603,
                    "message": str(e),
                },
            }

    async def run(self):
        """Run the MCP server with stdio communication."""
        await self.start()

        try:
            logger.info("MCP Server listening on stdio")

            # Read from stdin, write to stdout
            while self.running:
                try:
                    # Read one line from stdin
                    line = await asyncio.get_event_loop().run_in_executor(
                        None, sys.stdin.readline
                    )

                    if not line:
                        logger.info("EOF received, shutting down")
                        break

                    line = line.strip()
                    if not line:
                        continue

                    # Parse JSON-RPC message
                    message = json.loads(line)
                    logger.info(f"Received: {message}")

                    # Handle message
                    response = await self.handle_message(message)

                    # Write response to stdout
                    response_str = json.dumps(response)
                    print(response_str, flush=True)
                    logger.info(f"Sent: {response_str}")

                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)

        finally:
            await self.stop()


async def main():
    """Main entry point for MCP server."""
    logger.info("Starting L12 MCP Server")

    server = L12MCPServer()
    await server.run()

    logger.info("L12 MCP Server shut down")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server crashed: {e}", exc_info=True)
        sys.exit(1)

"""MCP Server for L12 Natural Language Interface.

This module implements a Model Context Protocol (MCP) server for Claude CLI
integration. It provides tools for seamless access to platform services:

Service Discovery & Invocation:
1. invoke_service - Execute a service method
2. search_services - Fuzzy search services with disambiguation
3. list_services - List all services or filter by layer
4. get_service_info - Get detailed service information
5. list_methods - List methods available on a service
6. get_session_info - Get session metrics and state

Workflow Management:
7. create_workflow - Create a new workflow definition
8. execute_workflow - Execute a workflow with parameters
9. get_workflow_status - Get workflow execution status
10. list_workflows - List workflow definitions or executions
11. cancel_workflow - Cancel a running workflow
12. suggest_workflow - AI-assisted workflow generation

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

# Workflow imports (lazy loaded to avoid circular imports)
WorkflowStore = None
workflow_models = None

def _get_workflow_store():
    """Lazy import WorkflowStore."""
    global WorkflowStore
    if WorkflowStore is None:
        from L01_data_layer.services import WorkflowStore as WS
        WorkflowStore = WS
    return WorkflowStore

def _get_workflow_models():
    """Lazy import workflow models."""
    global workflow_models
    if workflow_models is None:
        from L01_data_layer import models as wm
        workflow_models = wm
    return workflow_models

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
            # ========== Workflow Management Tools ==========
            {
                "name": "create_workflow",
                "description": (
                    "Create a new workflow definition from JSON or DSL format. "
                    "Workflows define DAG-based execution pipelines with nodes, edges, and parameters. "
                    "Example: create_workflow(definition={...}, format='json')"
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "definition": {
                            "type": "object",
                            "description": "Workflow definition with nodes, edges, entry_node_id, etc.",
                        },
                        "format": {
                            "type": "string",
                            "description": "Definition format: 'json' (default) or 'yaml'",
                            "default": "json",
                            "enum": ["json", "yaml"],
                        },
                        "validate_only": {
                            "type": "boolean",
                            "description": "Only validate without saving (default: false)",
                            "default": False,
                        },
                    },
                    "required": ["definition"],
                },
            },
            {
                "name": "execute_workflow",
                "description": (
                    "Execute a workflow with optional parameters. "
                    "Returns execution ID for status tracking. "
                    "Example: execute_workflow(workflow_id='wf_abc123', parameters={'input': 'data'})"
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {
                            "type": "string",
                            "description": "ID of the workflow to execute",
                        },
                        "parameters": {
                            "type": "object",
                            "description": "Input parameters for the workflow",
                            "default": {},
                        },
                        "async_mode": {
                            "type": "boolean",
                            "description": "Run asynchronously (default: true)",
                            "default": True,
                        },
                    },
                    "required": ["workflow_id"],
                },
            },
            {
                "name": "get_workflow_status",
                "description": (
                    "Get the status of a workflow execution. "
                    "Shows current node, completed nodes, errors, and approvals. "
                    "Example: get_workflow_status(execution_id='exec_abc123')"
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "execution_id": {
                            "type": "string",
                            "description": "Execution ID to check",
                        },
                        "include_node_details": {
                            "type": "boolean",
                            "description": "Include individual node execution details",
                            "default": True,
                        },
                    },
                    "required": ["execution_id"],
                },
            },
            {
                "name": "list_workflows",
                "description": (
                    "List workflow definitions or executions. "
                    "Filter by status, category, or type. "
                    "Example: list_workflows(type='definitions', status='active')"
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "description": "What to list: 'definitions' or 'executions'",
                            "default": "definitions",
                            "enum": ["definitions", "executions"],
                        },
                        "status": {
                            "type": "string",
                            "description": "Filter by status (definitions: draft/active/deprecated; executions: running/completed/failed)",
                        },
                        "category": {
                            "type": "string",
                            "description": "Filter by category (for definitions)",
                        },
                        "workflow_id": {
                            "type": "string",
                            "description": "Filter executions by workflow_id",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results (default: 20)",
                            "default": 20,
                        },
                    },
                },
            },
            {
                "name": "cancel_workflow",
                "description": (
                    "Cancel a running workflow execution. "
                    "Optionally trigger compensation/rollback for saga pattern. "
                    "Example: cancel_workflow(execution_id='exec_abc123', compensate=true)"
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "execution_id": {
                            "type": "string",
                            "description": "Execution ID to cancel",
                        },
                        "compensate": {
                            "type": "boolean",
                            "description": "Run compensation/rollback for completed steps",
                            "default": False,
                        },
                        "reason": {
                            "type": "string",
                            "description": "Reason for cancellation",
                        },
                    },
                    "required": ["execution_id"],
                },
            },
            {
                "name": "suggest_workflow",
                "description": (
                    "AI-assisted workflow generation from natural language description. "
                    "Generates a workflow definition based on the described task. "
                    "Example: suggest_workflow(description='Deploy my app with tests and rollback on failure')"
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "Natural language description of the workflow",
                        },
                        "include_compensation": {
                            "type": "boolean",
                            "description": "Include compensation/rollback steps (saga pattern)",
                            "default": True,
                        },
                        "format": {
                            "type": "string",
                            "description": "Output format: 'json' or 'dsl'",
                            "default": "json",
                            "enum": ["json", "dsl"],
                        },
                    },
                    "required": ["description"],
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

    # =========================================================================
    # Workflow Management Tools
    # =========================================================================

    def _get_workflow_store(self):
        """Get or create WorkflowStore instance."""
        if not hasattr(self, "_workflow_store"):
            # Get database pool from L01 - in real implementation this would
            # be injected or retrieved from a connection manager
            self._workflow_store = None
            try:
                from L01_data_layer.database import db
                if db.pool:
                    WS = _get_workflow_store()
                    self._workflow_store = WS(db.pool)
            except Exception as e:
                logger.warning(f"Could not initialize WorkflowStore: {e}")
        return self._workflow_store

    async def create_workflow(
        self,
        definition: Dict[str, Any],
        format: str = "json",
        validate_only: bool = False,
    ) -> str:
        """Tool: Create a new workflow definition.

        Args:
            definition: Workflow definition dict
            format: Definition format (json or yaml)
            validate_only: Only validate without saving

        Returns:
            Formatted result with workflow ID
        """
        try:
            models = _get_workflow_models()

            # Parse nodes
            nodes = []
            for node_data in definition.get("nodes", []):
                node = models.WorkflowNodeDefinition(**node_data)
                nodes.append(node)

            # Parse edges
            edges = []
            for edge_data in definition.get("edges", []):
                edge = models.WorkflowEdgeDefinition(**edge_data)
                edges.append(edge)

            # Parse parameters
            parameters = []
            for param_data in definition.get("parameters", []):
                param = models.WorkflowParameter(**param_data)
                parameters.append(param)

            # Create the definition model
            workflow_def = models.WorkflowDefinitionCreate(
                name=definition.get("name", "Unnamed Workflow"),
                description=definition.get("description"),
                version=definition.get("version", "1.0.0"),
                paradigm=models.WorkflowParadigm(definition.get("paradigm", "dag")),
                nodes=nodes,
                edges=edges,
                entry_node_id=definition.get("entry_node_id", nodes[0].node_id if nodes else ""),
                parameters=parameters,
                category=definition.get("category", "general"),
                tags=definition.get("tags", []),
                visibility=models.WorkflowVisibility(definition.get("visibility", "private")),
                metadata=definition.get("metadata", {}),
            )

            if validate_only:
                return (
                    f"✅ Workflow definition is valid\n\n"
                    f"Name: {workflow_def.name}\n"
                    f"Version: {workflow_def.version}\n"
                    f"Nodes: {len(workflow_def.nodes)}\n"
                    f"Edges: {len(workflow_def.edges)}\n"
                    f"Entry node: {workflow_def.entry_node_id}\n"
                )

            store = self._get_workflow_store()
            if not store:
                return (
                    f"⚠️ WorkflowStore not available (database not connected)\n\n"
                    f"Workflow definition is valid:\n"
                    f"Name: {workflow_def.name}\n"
                    f"Nodes: {len(workflow_def.nodes)}\n"
                    f"Edges: {len(workflow_def.edges)}\n"
                )

            workflow = await store.create_workflow(workflow_def)
            return (
                f"✅ Workflow created successfully\n\n"
                f"Workflow ID: {workflow.workflow_id}\n"
                f"Name: {workflow.name}\n"
                f"Version: {workflow.version}\n"
                f"Status: {workflow.status.value}\n"
                f"Nodes: {len(nodes)}\n"
                f"Edges: {len(edges)}\n\n"
                f"💡 To execute:\n"
                f"   execute_workflow(workflow_id='{workflow.workflow_id}')"
            )

        except Exception as e:
            logger.error(f"Error creating workflow: {e}", exc_info=True)
            return f"❌ Error creating workflow: {str(e)}"

    async def execute_workflow(
        self,
        workflow_id: str,
        parameters: Optional[Dict[str, Any]] = None,
        async_mode: bool = True,
    ) -> str:
        """Tool: Execute a workflow with parameters.

        Args:
            workflow_id: ID of workflow to execute
            parameters: Input parameters
            async_mode: Run asynchronously

        Returns:
            Formatted result with execution ID
        """
        try:
            store = self._get_workflow_store()
            if not store:
                return "❌ WorkflowStore not available (database not connected)"

            models = _get_workflow_models()

            # Create execution
            exec_create = models.WorkflowExecutionCreate(
                workflow_id=workflow_id,
                parameters=parameters or {},
            )

            execution = await store.create_execution(exec_create)

            # Start execution
            await store.start_execution(execution.execution_id)

            return (
                f"✅ Workflow execution started\n\n"
                f"Execution ID: {execution.execution_id}\n"
                f"Workflow ID: {workflow_id}\n"
                f"Status: running\n"
                f"Trace ID: {execution.trace_id}\n\n"
                f"💡 To check status:\n"
                f"   get_workflow_status(execution_id='{execution.execution_id}')"
            )

        except Exception as e:
            logger.error(f"Error executing workflow: {e}", exc_info=True)
            return f"❌ Error executing workflow: {str(e)}"

    async def get_workflow_status(
        self,
        execution_id: str,
        include_node_details: bool = True,
    ) -> str:
        """Tool: Get workflow execution status.

        Args:
            execution_id: Execution ID to check
            include_node_details: Include node execution details

        Returns:
            Formatted execution status
        """
        try:
            store = self._get_workflow_store()
            if not store:
                return "❌ WorkflowStore not available (database not connected)"

            if include_node_details:
                response = await store.get_execution_response(execution_id)
                if not response:
                    return f"❌ Execution '{execution_id}' not found"

                execution = response.execution
                node_execs = response.node_executions
                approvals = response.pending_approvals
            else:
                execution = await store.get_execution(execution_id)
                if not execution:
                    return f"❌ Execution '{execution_id}' not found"
                node_execs = []
                approvals = []

            # Format status icon
            status_icons = {
                "pending": "⏳",
                "running": "🔄",
                "completed": "✅",
                "failed": "❌",
                "cancelled": "🚫",
                "paused": "⏸️",
                "waiting_approval": "🔔",
                "compensating": "↩️",
            }
            icon = status_icons.get(execution.status.value if hasattr(execution.status, 'value') else execution.status, "❓")

            result = (
                f"{icon} Workflow Execution Status\n\n"
                f"Execution ID: {execution.execution_id}\n"
                f"Workflow ID: {execution.workflow_id}\n"
                f"Version: {execution.workflow_version}\n"
                f"Status: {execution.status.value if hasattr(execution.status, 'value') else execution.status}\n"
            )

            if execution.current_node_id:
                result += f"Current node: {execution.current_node_id}\n"

            if execution.started_at:
                result += f"Started: {execution.started_at}\n"

            if execution.completed_at:
                result += f"Completed: {execution.completed_at}\n"
                if execution.duration_ms:
                    result += f"Duration: {execution.duration_ms}ms\n"

            if execution.error_message:
                result += f"\n⚠️ Error: {execution.error_code or 'unknown'}\n"
                result += f"   {execution.error_message}\n"

            if execution.compensation_required:
                result += f"\n↩️ Compensation: {execution.compensation_status}\n"
                if execution.compensated_nodes:
                    result += f"   Compensated nodes: {', '.join(execution.compensated_nodes)}\n"

            if node_execs:
                result += f"\n📊 Node Executions ({len(node_execs)}):\n"
                for node in node_execs:
                    node_icon = status_icons.get(node.status.value if hasattr(node.status, 'value') else node.status, "❓")
                    result += f"  {node_icon} {node.node_id} ({node.node_type.value if hasattr(node.node_type, 'value') else node.node_type})\n"
                    if node.duration_ms:
                        result += f"     Duration: {node.duration_ms}ms\n"
                    if node.error_message:
                        result += f"     Error: {node.error_message}\n"

            if approvals:
                result += f"\n🔔 Pending Approvals ({len(approvals)}):\n"
                for approval in approvals:
                    result += f"  • {approval.approval_id}: {approval.request_message or 'Approval required'}\n"
                    if approval.expires_at:
                        result += f"    Expires: {approval.expires_at}\n"

            return result

        except Exception as e:
            logger.error(f"Error getting workflow status: {e}", exc_info=True)
            return f"❌ Error getting workflow status: {str(e)}"

    async def list_workflows(
        self,
        type: str = "definitions",
        status: Optional[str] = None,
        category: Optional[str] = None,
        workflow_id: Optional[str] = None,
        limit: int = 20,
    ) -> str:
        """Tool: List workflow definitions or executions.

        Args:
            type: What to list (definitions or executions)
            status: Filter by status
            category: Filter by category
            workflow_id: Filter executions by workflow
            limit: Maximum results

        Returns:
            Formatted list
        """
        try:
            store = self._get_workflow_store()
            if not store:
                return "❌ WorkflowStore not available (database not connected)"

            models = _get_workflow_models()

            if type == "executions":
                exec_status = models.ExecutionStatus(status) if status else None
                response = await store.list_executions(
                    workflow_id=workflow_id,
                    status=exec_status,
                    limit=limit,
                )

                if not response.executions:
                    return "ℹ️ No workflow executions found"

                result = f"📋 Workflow Executions ({response.total} total):\n\n"
                for exec in response.executions:
                    status_str = exec.status.value if hasattr(exec.status, 'value') else exec.status
                    result += (
                        f"• {exec.execution_id}\n"
                        f"  Workflow: {exec.workflow_id}\n"
                        f"  Status: {status_str}\n"
                        f"  Started: {exec.started_at or 'not started'}\n\n"
                    )

            else:  # definitions
                wf_status = models.WorkflowStatus(status) if status else None
                response = await store.list_workflows(
                    status=wf_status,
                    category=category,
                    limit=limit,
                )

                if not response.workflows:
                    return "ℹ️ No workflow definitions found"

                result = f"📋 Workflow Definitions ({response.total} total):\n\n"
                for wf in response.workflows:
                    status_str = wf.status.value if hasattr(wf.status, 'value') else wf.status
                    result += (
                        f"• {wf.workflow_id}\n"
                        f"  Name: {wf.name}\n"
                        f"  Version: {wf.version}\n"
                        f"  Status: {status_str}\n"
                        f"  Category: {wf.category}\n"
                        f"  Description: {wf.description or 'No description'}\n\n"
                    )

            result += (
                f"💡 For more details:\n"
                f"   get_workflow_status(execution_id='...') for executions\n"
                f"   Or invoke_service(command='WorkflowStore.get_workflow', parameters={{'workflow_id': '...'}})"
            )

            return result

        except Exception as e:
            logger.error(f"Error listing workflows: {e}", exc_info=True)
            return f"❌ Error listing workflows: {str(e)}"

    async def cancel_workflow(
        self,
        execution_id: str,
        compensate: bool = False,
        reason: Optional[str] = None,
    ) -> str:
        """Tool: Cancel a running workflow execution.

        Args:
            execution_id: Execution to cancel
            compensate: Run compensation/rollback
            reason: Cancellation reason

        Returns:
            Formatted result
        """
        try:
            store = self._get_workflow_store()
            if not store:
                return "❌ WorkflowStore not available (database not connected)"

            models = _get_workflow_models()

            # Get current status
            execution = await store.get_execution(execution_id)
            if not execution:
                return f"❌ Execution '{execution_id}' not found"

            current_status = execution.status.value if hasattr(execution.status, 'value') else execution.status
            if current_status in ("completed", "failed", "cancelled"):
                return f"ℹ️ Execution already in terminal state: {current_status}"

            if compensate:
                # Mark for compensation
                execution = await store.mark_for_compensation(execution_id)
                return (
                    f"↩️ Workflow marked for compensation\n\n"
                    f"Execution ID: {execution_id}\n"
                    f"Status: compensating\n"
                    f"Reason: {reason or 'User requested cancellation with rollback'}\n\n"
                    f"Compensation will run for completed nodes in reverse order."
                )
            else:
                # Simple cancel
                await store.fail_execution(
                    execution_id,
                    error_code="CANCELLED",
                    error_message=reason or "User requested cancellation",
                )
                return (
                    f"🚫 Workflow cancelled\n\n"
                    f"Execution ID: {execution_id}\n"
                    f"Status: cancelled\n"
                    f"Reason: {reason or 'User requested cancellation'}\n"
                )

        except Exception as e:
            logger.error(f"Error cancelling workflow: {e}", exc_info=True)
            return f"❌ Error cancelling workflow: {str(e)}"

    async def suggest_workflow(
        self,
        description: str,
        include_compensation: bool = True,
        format: str = "json",
    ) -> str:
        """Tool: AI-assisted workflow generation.

        Args:
            description: Natural language description
            include_compensation: Include saga compensation
            format: Output format (json or dsl)

        Returns:
            Generated workflow definition
        """
        try:
            # This is a placeholder implementation
            # In a full implementation, this would use the AI co-pilot
            # to generate a workflow from the description

            # Parse keywords from description to suggest steps
            keywords = description.lower()
            suggested_steps = []

            if "test" in keywords:
                suggested_steps.append({
                    "node_id": "run_tests",
                    "node_type": "service",
                    "name": "Run Tests",
                    "description": "Execute test suite",
                    "service": "TestRunner",
                    "method": "run_tests",
                })

            if "build" in keywords:
                suggested_steps.append({
                    "node_id": "build",
                    "node_type": "service",
                    "name": "Build",
                    "description": "Build application",
                    "service": "BuildService",
                    "method": "build",
                })

            if "deploy" in keywords:
                suggested_steps.append({
                    "node_id": "deploy",
                    "node_type": "service",
                    "name": "Deploy",
                    "description": "Deploy to environment",
                    "service": "DeploymentService",
                    "method": "deploy",
                })
                if include_compensation:
                    suggested_steps[-1]["compensation"] = {
                        "service": "DeploymentService",
                        "method": "rollback",
                    }

            if "approve" in keywords or "review" in keywords:
                suggested_steps.append({
                    "node_id": "approval",
                    "node_type": "human_approval",
                    "name": "Human Approval",
                    "description": "Requires human approval",
                    "approval_message": "Please review and approve",
                })

            if not suggested_steps:
                suggested_steps = [
                    {
                        "node_id": "step_1",
                        "node_type": "service",
                        "name": "Step 1",
                        "description": "First step - customize as needed",
                    },
                    {
                        "node_id": "step_2",
                        "node_type": "service",
                        "name": "Step 2",
                        "description": "Second step - customize as needed",
                    },
                ]

            # Build edges
            edges = []
            for i in range(len(suggested_steps) - 1):
                edges.append({
                    "source_node_id": suggested_steps[i]["node_id"],
                    "target_node_id": suggested_steps[i + 1]["node_id"],
                })

            workflow = {
                "name": f"Generated: {description[:50]}...",
                "description": f"AI-generated workflow for: {description}",
                "version": "1.0.0",
                "paradigm": "dag",
                "nodes": suggested_steps,
                "edges": edges,
                "entry_node_id": suggested_steps[0]["node_id"] if suggested_steps else "step_1",
                "parameters": [],
                "category": "generated",
                "tags": ["ai-generated"],
            }

            if format == "dsl":
                # Format as Python DSL
                dsl_code = self._format_workflow_as_dsl(workflow)
                return (
                    f"🤖 Generated Workflow (Python DSL)\n\n"
                    f"Description: {description}\n\n"
                    f"```python\n{dsl_code}\n```\n\n"
                    f"💡 Copy this code and save as a .py file, then use:\n"
                    f"   definition = MyWorkflow.compile()"
                )
            else:
                # Format as JSON
                workflow_json = json.dumps(workflow, indent=2)
                return (
                    f"🤖 Generated Workflow (JSON)\n\n"
                    f"Description: {description}\n\n"
                    f"```json\n{workflow_json}\n```\n\n"
                    f"💡 To create this workflow:\n"
                    f"   create_workflow(definition={{...above...}})"
                )

        except Exception as e:
            logger.error(f"Error suggesting workflow: {e}", exc_info=True)
            return f"❌ Error suggesting workflow: {str(e)}"

    def _format_workflow_as_dsl(self, workflow: Dict[str, Any]) -> str:
        """Format a workflow dict as Python DSL code."""
        lines = [
            "from L02_runtime.dsl import workflow, step, compensation, approval_step",
            "",
            f"@workflow('{workflow['name']}')",
            "class MyWorkflow:",
            f"    '''{workflow['description']}'''",
            "",
        ]

        nodes = workflow.get("nodes", [])
        edges = workflow.get("edges", [])

        # Build edge map for routing
        edge_map = {}
        for edge in edges:
            src = edge["source_node_id"]
            tgt = edge["target_node_id"]
            if src not in edge_map:
                edge_map[src] = []
            edge_map[src].append(tgt)

        for node in nodes:
            node_id = node["node_id"]
            node_type = node.get("node_type", "service")
            next_nodes = edge_map.get(node_id, [])
            next_param = f", next='{next_nodes[0]}'" if len(next_nodes) == 1 else ""

            if node_type == "human_approval":
                lines.append(f"    @approval_step('{node_id}', message='{node.get('approval_message', 'Approve?')}'{next_param})")
            else:
                lines.append(f"    @step('{node_id}'{next_param})")

            lines.append(f"    async def {node_id}(self, ctx):")
            lines.append(f"        '''{node.get('description', 'Step implementation')}'''")
            lines.append(f"        return {{}}")
            lines.append("")

        return "\n".join(lines)

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
            # Service discovery & invocation tools
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
            # Workflow management tools
            elif tool_name == "create_workflow":
                return await self.create_workflow(**arguments)
            elif tool_name == "execute_workflow":
                return await self.execute_workflow(**arguments)
            elif tool_name == "get_workflow_status":
                return await self.get_workflow_status(**arguments)
            elif tool_name == "list_workflows":
                return await self.list_workflows(**arguments)
            elif tool_name == "cancel_workflow":
                return await self.cancel_workflow(**arguments)
            elif tool_name == "suggest_workflow":
                return await self.suggest_workflow(**arguments)
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

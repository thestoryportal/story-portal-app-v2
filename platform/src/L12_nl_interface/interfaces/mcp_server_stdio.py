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
from ..services.workflow_templates import WorkflowTemplates
from ..utils.service_categorizer import ServiceCategorizer

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

            # Initialize workflow templates
            self.workflow_templates = WorkflowTemplates(self.registry, self.factory)

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
                "name": "platform-services",
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
                "name": "browse_services",
                "description": (
                    "Browse all platform services organized by functional category. "
                    "Services are grouped by usage (e.g., Data Storage, Agent Management, AI Models). "
                    "Optionally filter by search term. "
                    "Example: browse_services() or browse_services(search='planning')"
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "search": {
                            "type": "string",
                            "description": "Optional search term to filter services",
                        }
                    },
                },
            },
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
            {
                "name": "list_workflows",
                "description": (
                    "List available workflow templates. Workflows are pre-defined multi-service "
                    "operations for common tasks like testing, deployment, ETL, and monitoring. "
                    "Optionally filter by category. "
                    "Example: list_workflows() or list_workflows(category='testing')"
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Filter by category: testing, deployment, data_pipeline, or monitoring",
                        }
                    },
                },
            },
            {
                "name": "get_workflow_info",
                "description": (
                    "Get detailed information about a specific workflow template including steps, "
                    "parameters, and dependencies. "
                    "Example: get_workflow_info(workflow_name='testing.unit')"
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflow_name": {
                            "type": "string",
                            "description": "Name of the workflow template",
                        }
                    },
                    "required": ["workflow_name"],
                },
            },
            {
                "name": "execute_workflow",
                "description": (
                    "Execute a workflow template with optional parameters. "
                    "Returns execution results for each step. "
                    "Example: execute_workflow(workflow_name='testing.unit', parameters={'test_path': 'tests/'})"
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflow_name": {
                            "type": "string",
                            "description": "Name of the workflow to execute",
                        },
                        "parameters": {
                            "type": "object",
                            "description": "Workflow parameters to override defaults",
                        },
                    },
                    "required": ["workflow_name"],
                },
            },
            {
                "name": "search_workflows",
                "description": (
                    "Search for workflow templates by name, description, or tags. "
                    "Example: search_workflows(query='deployment')"
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query",
                        }
                    },
                    "required": ["query"],
                },
            },
            # Workflow Builder tools (persistent workflow definitions)
            {
                "name": "create_workflow",
                "description": (
                    "Create a new persistent workflow definition with nodes, edges, and parameters. "
                    "Supports DAG, sequential, event-driven, and state machine paradigms. "
                    "Example: create_workflow(definition={name: 'my_pipeline', nodes: [...], entry_node_id: 'start'})"
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "definition": {
                            "type": "object",
                            "description": "Workflow definition with name, description, nodes, edges, entry_node_id, parameters",
                        },
                        "validate_only": {
                            "type": "boolean",
                            "description": "If true, only validate without saving (default: false)",
                        },
                    },
                    "required": ["definition"],
                },
            },
            {
                "name": "start_workflow",
                "description": (
                    "Start execution of a workflow definition. Returns execution_id for tracking. "
                    "Example: start_workflow(workflow_id='wf_abc123', parameters={'input': 'data'})"
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {
                            "type": "string",
                            "description": "ID of the workflow definition to execute",
                        },
                        "parameters": {
                            "type": "object",
                            "description": "Input parameters for the workflow",
                        },
                        "async_mode": {
                            "type": "boolean",
                            "description": "If true, return immediately with execution_id (default: false)",
                        },
                    },
                    "required": ["workflow_id"],
                },
            },
            {
                "name": "workflow_status",
                "description": (
                    "Get the status of a workflow execution including node progress. "
                    "Example: workflow_status(execution_id='exec_123')"
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "execution_id": {
                            "type": "string",
                            "description": "ID of the workflow execution",
                        },
                        "include_node_details": {
                            "type": "boolean",
                            "description": "Include individual node execution details (default: true)",
                        },
                    },
                    "required": ["execution_id"],
                },
            },
            {
                "name": "list_workflow_definitions",
                "description": (
                    "List persistent workflow definitions (not templates). "
                    "Example: list_workflow_definitions(status='active', category='data_pipeline')"
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "description": "Filter by status: draft, active, deprecated, archived",
                        },
                        "category": {
                            "type": "string",
                            "description": "Filter by category",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results (default: 20)",
                        },
                    },
                },
            },
            {
                "name": "cancel_workflow",
                "description": (
                    "Cancel a running workflow execution with optional compensation. "
                    "Example: cancel_workflow(execution_id='exec_123', compensate=true)"
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "execution_id": {
                            "type": "string",
                            "description": "ID of the execution to cancel",
                        },
                        "compensate": {
                            "type": "boolean",
                            "description": "Run compensation actions to rollback (default: true)",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Optional reason for cancellation",
                        },
                    },
                    "required": ["execution_id"],
                },
            },
            {
                "name": "suggest_workflow",
                "description": (
                    "AI-assisted workflow generation from natural language description. "
                    "Example: suggest_workflow(description='Run tests then deploy if successful')"
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "Natural language description of the desired workflow",
                        },
                        "include_compensation": {
                            "type": "boolean",
                            "description": "Generate compensation/rollback logic (default: true)",
                        },
                    },
                    "required": ["description"],
                },
            },
        ]

    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Handle MCP tool call."""
        try:
            logger.info(f"Handling tool call: {tool_name} with args: {arguments}")

            if tool_name == "browse_services":
                return await self._browse_services(arguments)
            elif tool_name == "invoke_service":
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
            elif tool_name == "list_workflows":
                return await self._list_workflows(arguments)
            elif tool_name == "get_workflow_info":
                return await self._get_workflow_info(arguments)
            elif tool_name == "execute_workflow":
                return await self._execute_workflow(arguments)
            elif tool_name == "search_workflows":
                return await self._search_workflows(arguments)
            # Workflow Builder tools
            elif tool_name == "create_workflow":
                return await self._create_workflow(arguments)
            elif tool_name == "start_workflow":
                return await self._start_workflow(arguments)
            elif tool_name == "workflow_status":
                return await self._workflow_status(arguments)
            elif tool_name == "list_workflow_definitions":
                return await self._list_workflow_definitions(arguments)
            elif tool_name == "cancel_workflow":
                return await self._cancel_workflow(arguments)
            elif tool_name == "suggest_workflow":
                return await self._suggest_workflow(arguments)
            else:
                return f"❌ Unknown tool: {tool_name}"

        except Exception as e:
            logger.error(f"Error handling tool call: {e}", exc_info=True)
            return f"❌ Error: {str(e)}"

    async def _browse_services(self, args: Dict[str, Any]) -> str:
        """Browse services organized by functional category."""
        search_term = args.get("search")

        # Get all services or filter by search
        if search_term:
            # Use fuzzy matcher for search
            matches = self.fuzzy_matcher.match(search_term, threshold=0.3, max_results=50)
            services = [match.service for match in matches]
        else:
            services = self.registry.list_all_services()

        if not services:
            if search_term:
                return f"No services found matching '{search_term}'"
            return "No services available"

        # Format services by category
        return ServiceCategorizer.format_categorized_services(services, search_term)

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

    async def _list_workflows(self, args: Dict[str, Any]) -> str:
        """List available workflow templates."""
        from ..services.workflow_templates import WorkflowCategory

        category_str = args.get("category")
        category = None

        if category_str:
            try:
                category = WorkflowCategory(category_str)
            except ValueError:
                return f"❌ Invalid category '{category_str}'. Valid categories: testing, deployment, data_pipeline, monitoring"

        templates = self.workflow_templates.list_templates(category)

        if not templates:
            if category:
                return f"No workflow templates found for category '{category_str}'"
            return "No workflow templates available"

        result = f"🔧 Available Workflow Templates ({len(templates)} total):\n\n"

        # Group by category
        by_category = {}
        for template in templates:
            cat = template.category.value
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(template)

        for cat, cat_templates in sorted(by_category.items()):
            result += f"**{cat.upper()}**\n"
            for template in cat_templates:
                result += f"• **{template.name}**\n"
                result += f"  {template.description}\n"
                result += f"  Steps: {len(template.steps)}\n"
                result += f"  Tags: {', '.join(template.tags)}\n\n"

        return result

    async def _get_workflow_info(self, args: Dict[str, Any]) -> str:
        """Get detailed workflow template information."""
        workflow_name = args.get("workflow_name")
        template = self.workflow_templates.get_template(workflow_name)

        if not template:
            return f"❌ Workflow template '{workflow_name}' not found"

        result = (
            f"🔧 **{template.name}**\n\n"
            f"**Description**: {template.description}\n"
            f"**Category**: {template.category.value}\n"
            f"**Tags**: {', '.join(template.tags)}\n\n"
        )

        if template.parameters:
            result += "**Default Parameters**:\n"
            for key, value in template.parameters.items():
                result += f"• {key}: {value}\n"
            result += "\n"

        if template.steps:
            result += f"**Workflow Steps** ({len(template.steps)} total):\n\n"
            for i, step in enumerate(template.steps, 1):
                result += f"{i}. **{step.step_id}**\n"
                result += f"   Service: {step.service_name}.{step.method_name}\n"
                if step.depends_on:
                    result += f"   Depends on: {', '.join(step.depends_on)}\n"
                if step.on_error != "abort":
                    result += f"   On error: {step.on_error}\n"
                if step.retry_count > 0:
                    result += f"   Retries: {step.retry_count}\n"
                result += "\n"

        return result

    async def _execute_workflow(self, args: Dict[str, Any]) -> str:
        """Execute a workflow template."""
        workflow_name = args.get("workflow_name")
        parameters = args.get("parameters", {})

        # Check if template exists
        template = self.workflow_templates.get_template(workflow_name)
        if not template:
            return f"❌ Workflow template '{workflow_name}' not found"

        # Execute workflow
        result = await self.workflow_templates.execute_workflow(
            workflow_name, parameters, self.session_id
        )

        # Format result
        output = (
            f"🔧 **Workflow Execution: {result.workflow_name}**\n\n"
            f"Status: {result.status.value.upper()}\n"
            f"Started: {result.started_at.isoformat()}\n"
        )

        if result.completed_at:
            duration = (result.completed_at - result.started_at).total_seconds()
            output += f"Duration: {duration:.2f} seconds\n"

        output += "\n"

        if result.error:
            output += f"**Error**: {result.error}\n\n"

        if result.step_results:
            output += f"**Step Results** ({len(result.step_results)} steps):\n\n"
            for step_id, step_result in result.step_results.items():
                status = step_result.get("status", "unknown")
                output += f"• **{step_id}**: {status}\n"
                if step_result.get("error"):
                    output += f"  Error: {step_result['error']}\n"
                elif step_result.get("result"):
                    output += f"  Result: {json.dumps(step_result['result'], indent=2)[:200]}...\n"
                output += "\n"

        return output

    async def _search_workflows(self, args: Dict[str, Any]) -> str:
        """Search for workflow templates."""
        query = args.get("query")

        matches = self.workflow_templates.search_templates(query)

        if not matches:
            return f"No workflow templates found matching '{query}'"

        result = f"🔍 Found {len(matches)} workflow template(s) matching '{query}':\n\n"
        for i, template in enumerate(matches, 1):
            result += (
                f"{i}. **{template.name}** ({template.category.value})\n"
                f"   {template.description}\n"
                f"   Steps: {len(template.steps)} | Tags: {', '.join(template.tags)}\n\n"
            )

        return result

    # ==================== Workflow Builder Methods ====================

    def _get_workflow_store(self):
        """Lazy load WorkflowStore to avoid import issues."""
        if not hasattr(self, '_workflow_store'):
            try:
                from src.L01_data_layer.services.workflow_store import WorkflowStore
                self._workflow_store = WorkflowStore()
            except ImportError as e:
                logger.warning(f"WorkflowStore not available: {e}")
                self._workflow_store = None
        return self._workflow_store

    async def _create_workflow(self, args: Dict[str, Any]) -> str:
        """Create a new workflow definition."""
        definition = args.get("definition", {})
        validate_only = args.get("validate_only", False)

        if not definition:
            return "❌ Error: 'definition' is required"

        store = self._get_workflow_store()
        if not store:
            return "❌ Error: WorkflowStore not available. Check database connection."

        try:
            # Import models
            from src.L01_data_layer.models.workflow import (
                WorkflowDefinitionCreate,
                WorkflowNodeDefinition,
                NodeType,
            )

            # Build node definitions
            nodes = []
            for node_data in definition.get("nodes", []):
                node_type = node_data.get("type", "service")
                try:
                    node_type_enum = NodeType(node_type.lower())
                except ValueError:
                    node_type_enum = NodeType.SERVICE

                nodes.append(WorkflowNodeDefinition(
                    node_id=node_data.get("node_id", node_data.get("id")),
                    type=node_type_enum,
                    name=node_data.get("name", node_data.get("node_id")),
                    description=node_data.get("description"),
                    service=node_data.get("service"),
                    method=node_data.get("method"),
                    parameters=node_data.get("parameters", {}),
                    routes=node_data.get("routes", {}),
                ))

            # Create workflow definition
            workflow_create = WorkflowDefinitionCreate(
                name=definition.get("name", "unnamed_workflow"),
                description=definition.get("description", ""),
                nodes=nodes,
                entry_node_id=definition.get("entry_node_id"),
                parameters=definition.get("parameters", {}),
                category=definition.get("category", "general"),
                tags=definition.get("tags", []),
            )

            if validate_only:
                return (
                    f"✅ Workflow definition is valid\n\n"
                    f"Name: {workflow_create.name}\n"
                    f"Nodes: {len(nodes)}\n"
                    f"Entry: {workflow_create.entry_node_id}\n"
                )

            # Save to database
            await store.initialize()
            workflow = await store.create_workflow(workflow_create)

            return (
                f"✅ Workflow created successfully\n\n"
                f"**Workflow ID**: {workflow.workflow_id}\n"
                f"**Name**: {workflow.name}\n"
                f"**Status**: {workflow.status.value}\n"
                f"**Nodes**: {len(nodes)}\n"
                f"**Entry Node**: {workflow.entry_node_id}\n\n"
                f"To execute: start_workflow(workflow_id='{workflow.workflow_id}')"
            )

        except Exception as e:
            logger.error(f"Error creating workflow: {e}", exc_info=True)
            return f"❌ Error creating workflow: {str(e)}"

    async def _start_workflow(self, args: Dict[str, Any]) -> str:
        """Start execution of a workflow definition."""
        workflow_id = args.get("workflow_id")
        parameters = args.get("parameters", {})
        async_mode = args.get("async_mode", False)

        if not workflow_id:
            return "❌ Error: 'workflow_id' is required"

        store = self._get_workflow_store()
        if not store:
            return "❌ Error: WorkflowStore not available. Check database connection."

        try:
            from src.L01_data_layer.models.workflow import WorkflowExecutionCreate

            await store.initialize()

            # Check workflow exists
            workflow = await store.get_workflow(workflow_id)
            if not workflow:
                return f"❌ Workflow '{workflow_id}' not found"

            # Create execution
            exec_create = WorkflowExecutionCreate(
                workflow_id=workflow_id,
                input_parameters=parameters,
                session_id=self.session_id,
            )
            execution = await store.create_execution(exec_create)

            # Start execution
            execution = await store.start_execution(execution.execution_id)

            result = (
                f"🚀 Workflow execution started\n\n"
                f"**Execution ID**: {execution.execution_id}\n"
                f"**Workflow**: {workflow.name} ({workflow_id})\n"
                f"**Status**: {execution.status.value}\n"
                f"**Started**: {execution.started_at}\n\n"
                f"To check status: workflow_status(execution_id='{execution.execution_id}')"
            )

            if async_mode:
                result += "\n\n_Running in async mode - check status for updates_"
            else:
                # For sync mode, we would wait for completion
                # For now, just return the started status
                result += "\n\n_Note: Full sync execution requires WorkflowEngine integration_"

            return result

        except Exception as e:
            logger.error(f"Error starting workflow: {e}", exc_info=True)
            return f"❌ Error starting workflow: {str(e)}"

    async def _workflow_status(self, args: Dict[str, Any]) -> str:
        """Get workflow execution status."""
        execution_id = args.get("execution_id")
        include_node_details = args.get("include_node_details", True)

        if not execution_id:
            return "❌ Error: 'execution_id' is required"

        store = self._get_workflow_store()
        if not store:
            return "❌ Error: WorkflowStore not available. Check database connection."

        try:
            await store.initialize()

            execution = await store.get_execution(execution_id)
            if not execution:
                return f"❌ Execution '{execution_id}' not found"

            # Get workflow info
            workflow = await store.get_workflow(execution.workflow_id)
            workflow_name = workflow.name if workflow else execution.workflow_id

            result = (
                f"📊 **Workflow Execution Status**\n\n"
                f"**Execution ID**: {execution.execution_id}\n"
                f"**Workflow**: {workflow_name}\n"
                f"**Status**: {execution.status.value.upper()}\n"
            )

            if execution.current_node_id:
                result += f"**Current Node**: {execution.current_node_id}\n"

            if execution.started_at:
                result += f"**Started**: {execution.started_at}\n"

            if execution.completed_at:
                result += f"**Completed**: {execution.completed_at}\n"
                if execution.duration_ms:
                    result += f"**Duration**: {execution.duration_ms}ms\n"

            if execution.error_message:
                result += f"\n**Error**: {execution.error_message}\n"

            if execution.compensation_required:
                result += f"\n⚠️ **Compensation Required**: {execution.compensation_status or 'pending'}\n"

            if include_node_details:
                node_executions = await store.get_node_executions(execution_id)
                if node_executions:
                    result += f"\n**Node Executions** ({len(node_executions)}):\n"
                    for node_exec in node_executions:
                        status_icon = "✅" if node_exec.get("status") == "completed" else "❌" if node_exec.get("status") == "failed" else "⏳"
                        result += f"  {status_icon} {node_exec.get('node_id')}: {node_exec.get('status', 'unknown')}\n"

            return result

        except Exception as e:
            logger.error(f"Error getting workflow status: {e}", exc_info=True)
            return f"❌ Error getting status: {str(e)}"

    async def _list_workflow_definitions(self, args: Dict[str, Any]) -> str:
        """List persistent workflow definitions."""
        status_filter = args.get("status")
        category = args.get("category")
        limit = args.get("limit", 20)

        store = self._get_workflow_store()
        if not store:
            return "❌ Error: WorkflowStore not available. Check database connection."

        try:
            from src.L01_data_layer.models.workflow import WorkflowStatus

            await store.initialize()

            # Convert status string to enum if provided
            status_enum = None
            if status_filter:
                try:
                    status_enum = WorkflowStatus(status_filter.lower())
                except ValueError:
                    return f"❌ Invalid status '{status_filter}'. Valid: draft, active, deprecated, archived"

            workflows = await store.list_workflows(
                status=status_enum,
                category=category,
                limit=limit,
            )

            if not workflows:
                filter_msg = ""
                if status_filter:
                    filter_msg += f" with status '{status_filter}'"
                if category:
                    filter_msg += f" in category '{category}'"
                return f"No workflow definitions found{filter_msg}"

            result = f"📋 **Workflow Definitions** ({len(workflows)} total):\n\n"

            for wf in workflows:
                status_icon = "✅" if wf.status.value == "active" else "📝" if wf.status.value == "draft" else "📦"
                result += (
                    f"{status_icon} **{wf.name}** (`{wf.workflow_id}`)\n"
                    f"   Status: {wf.status.value} | Category: {wf.category}\n"
                    f"   {wf.description[:100]}{'...' if len(wf.description or '') > 100 else ''}\n\n"
                )

            return result

        except Exception as e:
            logger.error(f"Error listing workflows: {e}", exc_info=True)
            return f"❌ Error listing workflows: {str(e)}"

    async def _cancel_workflow(self, args: Dict[str, Any]) -> str:
        """Cancel a running workflow execution."""
        execution_id = args.get("execution_id")
        compensate = args.get("compensate", True)
        reason = args.get("reason", "User requested cancellation")

        if not execution_id:
            return "❌ Error: 'execution_id' is required"

        store = self._get_workflow_store()
        if not store:
            return "❌ Error: WorkflowStore not available. Check database connection."

        try:
            from src.L01_data_layer.models.workflow import ExecutionStatus

            await store.initialize()

            execution = await store.get_execution(execution_id)
            if not execution:
                return f"❌ Execution '{execution_id}' not found"

            if execution.status.value in ["completed", "cancelled"]:
                return f"ℹ️ Execution already {execution.status.value}"

            # Cancel the execution
            execution = await store.update_execution_status(
                execution_id,
                ExecutionStatus.CANCELLED,
                error_message=reason,
            )

            result = (
                f"🛑 Workflow execution cancelled\n\n"
                f"**Execution ID**: {execution_id}\n"
                f"**Status**: {execution.status.value}\n"
                f"**Reason**: {reason}\n"
            )

            if compensate:
                execution = await store.mark_for_compensation(execution_id)
                result += f"\n⚠️ **Compensation**: Rollback initiated"
                result += f"\n   Status: {execution.compensation_status or 'pending'}"

            return result

        except Exception as e:
            logger.error(f"Error cancelling workflow: {e}", exc_info=True)
            return f"❌ Error cancelling workflow: {str(e)}"

    async def _suggest_workflow(self, args: Dict[str, Any]) -> str:
        """AI-assisted workflow generation."""
        description = args.get("description")
        include_compensation = args.get("include_compensation", True)

        if not description:
            return "❌ Error: 'description' is required"

        # Generate workflow suggestion based on description
        # This is a simplified implementation - full version would use LLM
        result = f"💡 **Suggested Workflow for**: \"{description}\"\n\n"

        # Parse common patterns from description
        description_lower = description.lower()

        nodes = []
        if "test" in description_lower:
            nodes.append({
                "node_id": "run_tests",
                "type": "service",
                "name": "Run Tests",
                "service": "TestRunner",
                "method": "run_tests",
            })
        if "deploy" in description_lower:
            nodes.append({
                "node_id": "deploy",
                "type": "service",
                "name": "Deploy Application",
                "service": "DeploymentService",
                "method": "deploy",
            })
        if "build" in description_lower:
            nodes.insert(0, {
                "node_id": "build",
                "type": "service",
                "name": "Build Application",
                "service": "BuildService",
                "method": "build",
            })
        if "notify" in description_lower or "alert" in description_lower:
            nodes.append({
                "node_id": "notify",
                "type": "service",
                "name": "Send Notification",
                "service": "NotificationService",
                "method": "send",
            })

        if not nodes:
            nodes = [
                {"node_id": "step_1", "type": "service", "name": "Step 1"},
                {"node_id": "step_2", "type": "service", "name": "Step 2"},
            ]

        result += "**Suggested Definition**:\n```json\n"
        suggested = {
            "name": description[:50].replace(" ", "_").lower(),
            "description": description,
            "entry_node_id": nodes[0]["node_id"] if nodes else "start",
            "nodes": nodes,
            "parameters": {},
        }

        if include_compensation:
            for node in nodes:
                if "deploy" in node.get("node_id", ""):
                    node["compensation"] = {
                        "service": "DeploymentService",
                        "method": "rollback",
                    }

        result += json.dumps(suggested, indent=2)
        result += "\n```\n\n"
        result += f"To create: `create_workflow(definition={{...above...}})`"

        return result

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

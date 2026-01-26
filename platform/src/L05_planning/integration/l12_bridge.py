"""
L12 Bridge - Connects L05 Planning to L12 Natural Language Interface
Path: platform/src/L05_planning/integration/l12_bridge.py
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class CommandStatus(Enum):
    """Status of a routed command."""
    HANDLED = "handled"
    NOT_FOUND = "not_found"
    ERROR = "error"
    TIMEOUT = "timeout"
    PENDING = "pending"


class CommandCategory(Enum):
    """Categories of commands that can be routed."""
    PLANNING = "planning"
    EXECUTION = "execution"
    VALIDATION = "validation"
    QUERY = "query"
    SYSTEM = "system"


@dataclass
class RouteRequest:
    """Request to route a command through L12."""
    command: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None
    category: CommandCategory = CommandCategory.PLANNING
    timeout_seconds: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RouteResult:
    """Result of routing a command through L12."""
    request_id: str
    command: str
    status: CommandStatus
    handled: bool
    result: Optional[Any] = None
    error_message: Optional[str] = None
    service_name: Optional[str] = None
    method_name: Optional[str] = None
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ServiceInfo:
    """Information about a registered service."""
    name: str
    methods: List[str]
    description: str = ""
    category: CommandCategory = CommandCategory.PLANNING


class L12Bridge:
    """
    Bridge to L12 Natural Language Interface for command routing.

    Provides abstraction for:
    - Routing planning commands
    - Service discovery
    - Command execution tracking
    - Natural language command resolution
    """

    def __init__(
        self,
        command_router: Optional[Any] = None,
        base_url: Optional[str] = None,
        default_session_id: Optional[str] = None,
    ):
        """
        Initialize L12 bridge.

        Args:
            command_router: Optional L12 CommandRouter instance
            base_url: Optional base URL for L12 service
            default_session_id: Default session ID for commands
        """
        self.command_router = command_router
        self.base_url = base_url or "http://localhost:8012"
        self.default_session_id = default_session_id or f"l05-{str(uuid4())[:8]}"
        self._initialized = False
        self._route_history: List[RouteResult] = []
        self._registered_services: Dict[str, ServiceInfo] = {}
        self._command_aliases: Dict[str, str] = {}

        # Register default planning commands
        self._register_default_services()

    async def initialize(self):
        """Initialize connection to L12."""
        if self._initialized:
            return

        logger.info(f"L12Bridge initialized (base_url={self.base_url})")
        self._initialized = True

    def _register_default_services(self):
        """Register default planning-related services."""
        # Planning service
        self._registered_services["PlanningService"] = ServiceInfo(
            name="PlanningService",
            methods=["create_plan", "execute_plan", "validate_plan", "get_plan_status"],
            description="Plan creation and execution",
            category=CommandCategory.PLANNING,
        )

        # Execution service
        self._registered_services["ExecutionService"] = ServiceInfo(
            name="ExecutionService",
            methods=["execute_unit", "get_execution_status", "pause_execution", "resume_execution"],
            description="Unit execution management",
            category=CommandCategory.EXECUTION,
        )

        # Validation service
        self._registered_services["ValidationService"] = ServiceInfo(
            name="ValidationService",
            methods=["validate_unit", "run_acceptance_criteria", "check_regression"],
            description="Validation and testing",
            category=CommandCategory.VALIDATION,
        )

        # Command aliases for natural language
        self._command_aliases = {
            "create plan": "PlanningService.create_plan",
            "execute plan": "PlanningService.execute_plan",
            "validate plan": "PlanningService.validate_plan",
            "run unit": "ExecutionService.execute_unit",
            "validate unit": "ValidationService.validate_unit",
            "check status": "PlanningService.get_plan_status",
        }

    def route_command(
        self,
        command: str,
        parameters: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ) -> RouteResult:
        """
        Routes a command through L12 for execution.

        Args:
            command: Command string (e.g., "PlanningService.create_plan" or "create plan")
            parameters: Optional command parameters
            session_id: Optional session ID (uses default if not provided)
            timeout_seconds: Optional timeout

        Returns:
            RouteResult with handled status and result
        """
        start_time = datetime.now()
        request_id = str(uuid4())[:8]
        use_session = session_id or self.default_session_id

        logger.debug(f"Routing command: {command} (session={use_session})")

        # Resolve command alias if needed
        resolved_command = self._resolve_command(command)

        # Parse command into service.method
        service_name, method_name = self._parse_command(resolved_command)

        if not service_name or not method_name:
            return RouteResult(
                request_id=request_id,
                command=command,
                status=CommandStatus.NOT_FOUND,
                handled=False,
                error_message=f"Could not parse command: {command}",
            )

        # Check if service is registered
        if service_name not in self._registered_services:
            return RouteResult(
                request_id=request_id,
                command=command,
                status=CommandStatus.NOT_FOUND,
                handled=False,
                error_message=f"Service not found: {service_name}",
                service_name=service_name,
                method_name=method_name,
            )

        service_info = self._registered_services[service_name]

        # Check if method exists
        if method_name not in service_info.methods:
            return RouteResult(
                request_id=request_id,
                command=command,
                status=CommandStatus.NOT_FOUND,
                handled=False,
                error_message=f"Method not found: {method_name} on {service_name}",
                service_name=service_name,
                method_name=method_name,
            )

        # If command router available, use it
        if self.command_router:
            try:
                result = self._execute_via_router(
                    service_name, method_name, parameters or {}, use_session, timeout_seconds
                )
            except Exception as e:
                end_time = datetime.now()
                execution_time = (end_time - start_time).total_seconds() * 1000

                return RouteResult(
                    request_id=request_id,
                    command=command,
                    status=CommandStatus.ERROR,
                    handled=False,
                    error_message=str(e),
                    service_name=service_name,
                    method_name=method_name,
                    execution_time_ms=execution_time,
                )
        else:
            # Mock execution for standalone operation
            result = self._execute_mock(service_name, method_name, parameters or {})

        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds() * 1000

        route_result = RouteResult(
            request_id=request_id,
            command=command,
            status=CommandStatus.HANDLED,
            handled=True,
            result=result,
            service_name=service_name,
            method_name=method_name,
            execution_time_ms=execution_time,
            metadata={
                "session_id": use_session,
                "resolved_command": resolved_command,
            }
        )

        self._route_history.append(route_result)
        logger.info(f"Command handled: {command} -> {service_name}.{method_name} ({execution_time:.1f}ms)")

        return route_result

    def _resolve_command(self, command: str) -> str:
        """Resolves command aliases to full command format."""
        command_lower = command.lower().strip()

        # Check aliases
        if command_lower in self._command_aliases:
            return self._command_aliases[command_lower]

        # Return original if no alias found
        return command

    def _parse_command(self, command: str) -> tuple:
        """Parses command into (service_name, method_name)."""
        if "." not in command:
            return (None, None)

        parts = command.split(".", 1)
        if len(parts) == 2:
            return (parts[0].strip(), parts[1].strip())

        return (None, None)

    def _execute_via_router(
        self,
        service_name: str,
        method_name: str,
        parameters: Dict[str, Any],
        session_id: str,
        timeout_seconds: Optional[float],
    ) -> Any:
        """Execute command via L12 CommandRouter."""
        # This would call the actual L12 command router
        # For now, return mock result
        return self._execute_mock(service_name, method_name, parameters)

    def _execute_mock(
        self,
        service_name: str,
        method_name: str,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute mock command for testing."""
        return {
            "status": "success",
            "service": service_name,
            "method": method_name,
            "parameters_received": list(parameters.keys()),
            "mock": True,
        }

    def register_service(
        self,
        name: str,
        methods: List[str],
        description: str = "",
        category: CommandCategory = CommandCategory.PLANNING,
    ):
        """
        Registers a service for command routing.

        Args:
            name: Service name
            methods: List of method names
            description: Service description
            category: Service category
        """
        self._registered_services[name] = ServiceInfo(
            name=name,
            methods=methods,
            description=description,
            category=category,
        )
        logger.debug(f"Registered service: {name} ({len(methods)} methods)")

    def register_alias(self, alias: str, command: str):
        """
        Registers a command alias.

        Args:
            alias: Natural language alias
            command: Full command (Service.method)
        """
        self._command_aliases[alias.lower()] = command
        logger.debug(f"Registered alias: '{alias}' -> {command}")

    def get_available_services(self) -> List[ServiceInfo]:
        """Returns list of registered services."""
        return list(self._registered_services.values())

    def get_available_commands(self) -> List[str]:
        """Returns list of all available commands."""
        commands = []
        for service_info in self._registered_services.values():
            for method in service_info.methods:
                commands.append(f"{service_info.name}.{method}")
        return sorted(commands)

    def get_route_history(
        self,
        limit: int = 100,
        status_filter: Optional[CommandStatus] = None,
    ) -> List[RouteResult]:
        """
        Gets command routing history.

        Args:
            limit: Maximum results
            status_filter: Optional filter by status

        Returns:
            List of RouteResults
        """
        history = self._route_history
        if status_filter:
            history = [r for r in history if r.status == status_filter]
        return history[-limit:]

    def suggest_commands(
        self,
        query: str,
        max_suggestions: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Suggests commands based on natural language query.

        Args:
            query: Natural language query
            max_suggestions: Maximum suggestions

        Returns:
            List of suggestion dicts
        """
        query_lower = query.lower()
        suggestions = []

        # Check aliases first
        for alias, command in self._command_aliases.items():
            if query_lower in alias or alias in query_lower:
                service, method = self._parse_command(command)
                suggestions.append({
                    "command": command,
                    "alias": alias,
                    "service": service,
                    "method": method,
                    "score": 0.9 if alias in query_lower else 0.7,
                })

        # Check service/method names
        for service_info in self._registered_services.values():
            if query_lower in service_info.name.lower():
                for method in service_info.methods:
                    suggestions.append({
                        "command": f"{service_info.name}.{method}",
                        "alias": None,
                        "service": service_info.name,
                        "method": method,
                        "score": 0.6,
                    })

        # Sort by score and limit
        suggestions.sort(key=lambda x: x["score"], reverse=True)
        return suggestions[:max_suggestions]

    def get_statistics(self) -> Dict[str, Any]:
        """Returns bridge statistics."""
        handled_count = len([r for r in self._route_history if r.handled])
        error_count = len([r for r in self._route_history if r.status == CommandStatus.ERROR])

        total_time = sum(r.execution_time_ms for r in self._route_history)

        return {
            "total_commands": len(self._route_history),
            "handled_commands": handled_count,
            "error_commands": error_count,
            "success_rate": (handled_count / len(self._route_history) * 100) if self._route_history else 0,
            "total_execution_time_ms": total_time,
            "average_execution_time_ms": total_time / len(self._route_history) if self._route_history else 0,
            "registered_services": len(self._registered_services),
            "registered_aliases": len(self._command_aliases),
            "initialized": self._initialized,
        }

    def clear_history(self):
        """Clears route history."""
        self._route_history = []

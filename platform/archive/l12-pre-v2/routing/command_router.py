"""Command Router for L12 Natural Language Interface.

This module implements the CommandRouter class which routes commands
to appropriate service methods. It integrates exact and fuzzy matching,
service instantiation, method invocation, and error handling.

Key features:
- Command parsing (e.g., "PlanningService.create_plan" or "Let's Plan")
- Exact and fuzzy matching integration
- Service instantiation via SessionManager
- Method validation and invocation (sync and async)
- Comprehensive error handling with structured responses

Example:
    >>> router = CommandRouter(registry, factory, session_manager, exact_matcher, fuzzy_matcher)
    >>> response = await router.route("PlanningService.create_plan", "session-123", {"goal": "test"})
    >>> print(response.status)
"""

import asyncio
import inspect
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from ..core.service_factory import ServiceFactory
from ..core.service_registry import ServiceRegistry
from ..core.session_manager import SessionManager
from ..models.command_models import (
    ErrorCode,
    ErrorResponse,
    InvocationStatus,
    InvokeRequest,
    InvokeResponse,
)
from ..models.service_metadata import ServiceMetadata
from ..services.l01_bridge import L12Bridge
from ..services.command_history import CommandHistory
from .exact_matcher import ExactMatcher
from .fuzzy_matcher import FuzzyMatcher, ServiceMatch

logger = logging.getLogger(__name__)


class CommandRouter:
    """Router for commands to service methods.

    The CommandRouter handles the full lifecycle of command execution:
    1. Parse command to extract service and method
    2. Match service using exact or fuzzy matching
    3. Validate method exists and is callable
    4. Get or create service instance via SessionManager
    5. Invoke method with parameters
    6. Handle errors and return structured response

    Attributes:
        registry: ServiceRegistry for metadata
        factory: ServiceFactory for service creation
        session_manager: SessionManager for service lifecycle
        exact_matcher: ExactMatcher for O(1) exact lookups
        fuzzy_matcher: FuzzyMatcher for natural language queries

    Example:
        >>> router = CommandRouter(registry, factory, session_manager, exact_matcher, fuzzy_matcher)
        >>> response = await router.route_request(invoke_request)
        >>> if response.status == InvocationStatus.SUCCESS:
        ...     print(f"Result: {response.result}")
    """

    def __init__(
        self,
        registry: ServiceRegistry,
        factory: ServiceFactory,
        session_manager: SessionManager,
        exact_matcher: ExactMatcher,
        fuzzy_matcher: FuzzyMatcher,
        l01_bridge: Optional[L12Bridge] = None,
        command_history: Optional[CommandHistory] = None,
    ):
        """Initialize the command router.

        Args:
            registry: ServiceRegistry instance
            factory: ServiceFactory instance
            session_manager: SessionManager instance
            exact_matcher: ExactMatcher instance
            fuzzy_matcher: FuzzyMatcher instance
            l01_bridge: Optional L12Bridge for usage tracking
            command_history: Optional CommandHistory for command replay
        """
        self.registry = registry
        self.factory = factory
        self.session_manager = session_manager
        self.exact_matcher = exact_matcher
        self.fuzzy_matcher = fuzzy_matcher
        self.l01_bridge = l01_bridge
        self.command_history = command_history

        logger.info("CommandRouter initialized")

    async def route(
        self,
        command: str,
        session_id: str,
        parameters: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[float] = None,
    ) -> InvokeResponse:
        """Route command to appropriate service method.

        This is a convenience method that creates an InvokeRequest
        and calls route_request().

        Args:
            command: Command string (e.g., "PlanningService.create_plan" or "Let's Plan")
            session_id: Session identifier
            parameters: Optional method parameters
            timeout_seconds: Optional timeout in seconds

        Returns:
            InvokeResponse with result or error

        Example:
            >>> response = await router.route("PlanningService.create_plan", "session-123")
        """
        # Parse command to extract service and method
        service_name, method_name = self._parse_command(command)

        if not service_name:
            # Command is just a query, not "Service.method" format
            return self._error_response(
                "",
                "",
                session_id,
                ErrorCode.INVALID_REQUEST,
                f"Invalid command format: '{command}'. Expected 'ServiceName.method_name'",
            )

        # Create InvokeRequest
        request = InvokeRequest(
            service_name=service_name,
            method_name=method_name or "invoke",  # Default method
            parameters=parameters or {},
            session_id=session_id,
            timeout_seconds=timeout_seconds,
        )

        return await self.route_request(request)

    async def route_request(self, request: InvokeRequest) -> InvokeResponse:
        """Route InvokeRequest to appropriate service method.

        This is the main routing method that handles:
        1. Service matching (exact or fuzzy)
        2. Method validation
        3. Service instantiation
        4. Method invocation
        5. Error handling

        Args:
            request: InvokeRequest with service, method, parameters

        Returns:
            InvokeResponse with result or error

        Example:
            >>> request = InvokeRequest(
            ...     service_name="PlanningService",
            ...     method_name="create_plan",
            ...     parameters={"goal": "test"},
            ...     session_id="session-123"
            ... )
            >>> response = await router.route_request(request)
        """
        start_time = time.time()

        try:
            # Step 1: Match service
            service_metadata = self._match_service(request.service_name)
            if not service_metadata:
                return self._error_response(
                    request.service_name,
                    request.method_name,
                    request.session_id,
                    ErrorCode.SERVICE_NOT_FOUND,
                    f"Service '{request.service_name}' not found",
                )

            # Step 2: Validate method
            method_metadata = self._validate_method(
                service_metadata, request.method_name
            )
            if not method_metadata:
                return self._error_response(
                    service_metadata.service_name,
                    request.method_name,
                    request.session_id,
                    ErrorCode.METHOD_NOT_FOUND,
                    f"Method '{request.method_name}' not found on service '{service_metadata.service_name}'",
                )

            # Step 3: Get or create service instance
            try:
                service_instance = await self.session_manager.get_service(
                    request.session_id, service_metadata.service_name
                )
            except Exception as e:
                return self._error_response(
                    service_metadata.service_name,
                    request.method_name,
                    request.session_id,
                    ErrorCode.SERVICE_INIT_ERROR,
                    f"Failed to initialize service: {str(e)}",
                )

            # Step 4: Invoke method
            try:
                result = await self._invoke_method(
                    service_instance,
                    request.method_name,
                    request.parameters,
                    request.timeout_seconds,
                )

                # Success!
                execution_time_ms = (time.time() - start_time) * 1000
                response = InvokeResponse(
                    status=InvocationStatus.SUCCESS,
                    result=result,
                    service_name=service_metadata.service_name,
                    method_name=request.method_name,
                    session_id=request.session_id,
                    execution_time_ms=execution_time_ms,
                )

                # Record to L01 if bridge available
                if self.l01_bridge:
                    asyncio.create_task(
                        self.l01_bridge.record_invocation(
                            session_id=request.session_id,
                            service_name=service_metadata.service_name,
                            method_name=request.method_name,
                            parameters=request.parameters,
                            result=result,
                            execution_time_ms=execution_time_ms,
                            status="success",
                        )
                    )

                # Record to command history if available
                if self.command_history:
                    asyncio.create_task(
                        self.command_history.add_command(
                            session_id=request.session_id,
                            service_name=service_metadata.service_name,
                            method_name=request.method_name,
                            parameters=request.parameters,
                            status="success",
                            execution_time_ms=execution_time_ms,
                            result=result,
                        )
                    )

                return response

            except asyncio.TimeoutError:
                return self._error_response(
                    service_metadata.service_name,
                    request.method_name,
                    request.session_id,
                    ErrorCode.TIMEOUT,
                    f"Method execution exceeded timeout of {request.timeout_seconds}s",
                )
            except Exception as e:
                return self._error_response(
                    service_metadata.service_name,
                    request.method_name,
                    request.session_id,
                    ErrorCode.EXECUTION_ERROR,
                    f"Method execution failed: {str(e)}",
                    details={"exception_type": type(e).__name__},
                )

        except Exception as e:
            # Catch-all for unexpected errors
            logger.error(f"Unexpected error in command router: {e}", exc_info=True)
            return self._error_response(
                request.service_name,
                request.method_name,
                request.session_id,
                ErrorCode.INTERNAL_ERROR,
                f"Internal routing error: {str(e)}",
            )

    def _parse_command(self, command: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse command string to extract service and method names.

        Expected formats:
        - "ServiceName.method_name" → ("ServiceName", "method_name")
        - "ServiceName" → ("ServiceName", None)
        - "natural language" → (None, None)

        Args:
            command: Command string

        Returns:
            Tuple of (service_name, method_name)

        Example:
            >>> router._parse_command("PlanningService.create_plan")
            ('PlanningService', 'create_plan')
        """
        if not command or "." not in command:
            # No dot separator, could be service name or natural language
            # Try exact match first
            if self.exact_matcher.is_exact_match(command):
                return (command, None)
            return (None, None)

        # Split on first dot
        parts = command.split(".", 1)
        if len(parts) == 2:
            return (parts[0].strip(), parts[1].strip())

        return (None, None)

    def _match_service(self, service_name: str) -> Optional[ServiceMetadata]:
        """Match service name to ServiceMetadata.

        Tries exact match first, then falls back to fuzzy match
        if exact match fails.

        Args:
            service_name: Service name or natural language query

        Returns:
            ServiceMetadata if match found, None otherwise

        Example:
            >>> service = router._match_service("PlanningService")
        """
        # Try exact match first
        service = self.exact_matcher.match(service_name)
        if service:
            logger.debug(f"Exact match found for '{service_name}'")
            return service

        # Try fuzzy match
        fuzzy_matches = self.fuzzy_matcher.match(service_name, threshold=0.7, max_results=1)
        if fuzzy_matches:
            service = fuzzy_matches[0].service
            logger.debug(
                f"Fuzzy match found for '{service_name}': {service.service_name} "
                f"(score: {fuzzy_matches[0].score:.2f})"
            )
            return service

        logger.debug(f"No match found for '{service_name}'")
        return None

    def _validate_method(
        self, service_metadata: ServiceMetadata, method_name: str
    ) -> Optional[Any]:
        """Validate method exists on service.

        Args:
            service_metadata: Service metadata
            method_name: Method name to validate

        Returns:
            MethodMetadata if found, None otherwise

        Example:
            >>> method = router._validate_method(service_metadata, "create_plan")
        """
        # Check if method_name is in service methods
        for method in service_metadata.methods:
            if method.name == method_name:
                return method

        logger.debug(
            f"Method '{method_name}' not found in metadata for service '{service_metadata.service_name}'"
        )
        return None

    async def _invoke_method(
        self,
        service_instance: Any,
        method_name: str,
        parameters: Dict[str, Any],
        timeout_seconds: Optional[float] = None,
    ) -> Any:
        """Invoke method on service instance.

        Handles both sync and async methods.

        Args:
            service_instance: Service instance
            method_name: Method name to invoke
            parameters: Method parameters
            timeout_seconds: Optional timeout

        Returns:
            Method result

        Raises:
            AttributeError: If method not found
            asyncio.TimeoutError: If execution exceeds timeout
            Exception: Any exception raised by the method

        Example:
            >>> result = await router._invoke_method(service, "create_plan", {"goal": "test"})
        """
        # Get method
        if not hasattr(service_instance, method_name):
            raise AttributeError(f"Method '{method_name}' not found on service instance")

        method = getattr(service_instance, method_name)

        # Check if callable
        if not callable(method):
            raise TypeError(f"'{method_name}' is not callable")

        # Invoke method
        if inspect.iscoroutinefunction(method):
            # Async method
            if timeout_seconds:
                result = await asyncio.wait_for(
                    method(**parameters), timeout=timeout_seconds
                )
            else:
                result = await method(**parameters)
        else:
            # Sync method - run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            if timeout_seconds:
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: method(**parameters)),
                    timeout=timeout_seconds,
                )
            else:
                result = await loop.run_in_executor(None, lambda: method(**parameters))

        return result

    def _error_response(
        self,
        service_name: str,
        method_name: str,
        session_id: str,
        error_code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> InvokeResponse:
        """Create error InvokeResponse.

        Args:
            service_name: Service name
            method_name: Method name
            session_id: Session ID
            error_code: ErrorCode enum value
            message: Error message
            details: Optional additional error details

        Returns:
            InvokeResponse with error

        Example:
            >>> response = router._error_response(
            ...     "PlanningService", "create_plan", "session-123",
            ...     ErrorCode.METHOD_NOT_FOUND, "Method not found"
            ... )
        """
        error = ErrorResponse(
            code=error_code, message=message, details=details or {}
        )

        response = InvokeResponse(
            status=InvocationStatus.ERROR,
            error=error,
            service_name=service_name,
            method_name=method_name,
            session_id=session_id,
        )

        # Record error to L01 if bridge available
        if self.l01_bridge:
            asyncio.create_task(
                self.l01_bridge.record_invocation(
                    session_id=session_id,
                    service_name=service_name,
                    method_name=method_name,
                    parameters={},  # Parameters not available in error path
                    result=message,
                    execution_time_ms=0.0,  # Not tracked for errors
                    status="error",
                )
            )

        # Record error to command history if available
        if self.command_history:
            asyncio.create_task(
                self.command_history.add_command(
                    session_id=session_id,
                    service_name=service_name,
                    method_name=method_name,
                    parameters={},  # Parameters not available in error path
                    status="error",
                    execution_time_ms=0.0,  # Not tracked for errors
                    result=message,
                )
            )

        return response

    def get_available_commands(self) -> List[str]:
        """Get list of all available commands.

        Returns:
            List of command strings in "ServiceName.method_name" format

        Example:
            >>> commands = router.get_available_commands()
            >>> print(f"Available: {len(commands)} commands")
        """
        commands = []
        all_services = self.registry.list_all_services()

        for service in all_services:
            for method in service.methods:
                command = f"{service.service_name}.{method.name}"
                commands.append(command)

        return sorted(commands)

    def get_service_methods(self, service_name: str) -> List[str]:
        """Get list of methods for a service.

        Args:
            service_name: Service name

        Returns:
            List of method names

        Example:
            >>> methods = router.get_service_methods("PlanningService")
            >>> print(f"Methods: {methods}")
        """
        service = self._match_service(service_name)
        if not service:
            return []

        return [method.name for method in service.methods]

    def suggest_commands(self, query: str, max_suggestions: int = 5) -> List[Dict[str, Any]]:
        """Suggest commands based on fuzzy matching.

        Args:
            query: Natural language query
            max_suggestions: Maximum number of suggestions

        Returns:
            List of suggestion dicts with service, method, score

        Example:
            >>> suggestions = router.suggest_commands("create a plan")
            >>> for s in suggestions:
            ...     print(f"{s['service']}.{s['method']}: {s['score']:.2f}")
        """
        matches = self.fuzzy_matcher.match(query, threshold=0.5, max_results=max_suggestions)

        suggestions = []
        for match in matches:
            service = match.service
            for method in service.methods:
                suggestions.append({
                    "service": service.service_name,
                    "method": method.name,
                    "command": f"{service.service_name}.{method.name}",
                    "score": match.score,
                    "description": method.description,
                })

        return suggestions[:max_suggestions]

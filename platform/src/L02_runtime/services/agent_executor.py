"""
Agent Executor

Executes agent code within configured sandbox, managing tool invocations and context.
Handles concurrent tool execution, streaming, and context window management.

Based on Section 3.3.1 of agent-runtime-layer-specification-v1.2-final-ASCII.md
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, AsyncIterator, Callable
from datetime import datetime, timezone
from dataclasses import dataclass, field

from ..models import (
    AgentConfig,
    AgentState,
    ToolDefinition,
)
from .model_gateway_bridge import ModelGatewayBridge, ModelGatewayBridgeError


logger = logging.getLogger(__name__)


class ExecutorError(Exception):
    """Agent execution error"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


@dataclass
class ToolInvocation:
    """Tool execution request"""
    tool_name: str
    parameters: Dict[str, Any]
    invocation_id: str = field(default_factory=lambda: f"tool_{datetime.now(timezone.utc).timestamp()}")
    timeout_seconds: int = 300


@dataclass
class ToolResult:
    """Tool execution result"""
    invocation_id: str
    tool_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0


@dataclass
class ExecutionContext:
    """Agent execution context"""
    agent_id: str
    session_id: str
    messages: List[Dict[str, Any]] = field(default_factory=list)
    tools: List[ToolDefinition] = field(default_factory=list)
    context_window_tokens: int = 128000
    current_tokens: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: str, content: str, tokens: int = 0):
        """Add a message to the context"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self.current_tokens += tokens

    def is_context_full(self) -> bool:
        """Check if context window is exceeded"""
        return self.current_tokens >= self.context_window_tokens


class AgentExecutor:
    """
    Manages agent code execution with tool support.

    Responsibilities:
    - Execute agent code within sandbox
    - Handle tool invocations (concurrent, with timeout)
    - Manage execution context and token tracking
    - Support streaming responses
    - Retry logic for failed tools
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        model_bridge: Optional[ModelGatewayBridge] = None
    ):
        """
        Initialize AgentExecutor.

        Args:
            config: Configuration dict with:
                - max_concurrent_tools: Maximum concurrent tool invocations
                - tool_timeout_seconds: Default tool timeout
                - context_window_tokens: Context window size
                - enable_streaming: Enable streaming responses
                - retry_on_tool_failure: Retry failed tools
                - max_tool_retries: Maximum retry attempts
                - system_prompt: Default system prompt for agents
                - temperature: Default temperature for LLM inference
                - max_tokens: Default max tokens for LLM inference
            model_bridge: ModelGatewayBridge for LLM inference (created if None)
        """
        self.config = config or {}

        # Configuration
        self.max_concurrent_tools = self.config.get("max_concurrent_tools", 10)
        self.tool_timeout = self.config.get("tool_timeout_seconds", 300)
        self.context_window_tokens = self.config.get("context_window_tokens", 128000)
        self.enable_streaming = self.config.get("enable_streaming", True)
        self.retry_on_failure = self.config.get("retry_on_tool_failure", True)
        self.max_tool_retries = self.config.get("max_tool_retries", 3)
        self.default_system_prompt = self.config.get(
            "system_prompt",
            "You are a helpful AI assistant. Execute tasks efficiently and accurately."
        )
        self.default_temperature = self.config.get("temperature", 0.7)
        self.default_max_tokens = self.config.get("max_tokens", 4096)

        # Model gateway bridge for LLM inference
        self.model_bridge = model_bridge or ModelGatewayBridge()

        # Tool registry: tool_name -> callable
        self._tool_registry: Dict[str, Callable] = {}

        # Active execution contexts
        self._contexts: Dict[str, ExecutionContext] = {}

        # Tool execution semaphore
        self._tool_semaphore = asyncio.Semaphore(self.max_concurrent_tools)

        logger.info(
            f"AgentExecutor initialized: "
            f"max_concurrent_tools={self.max_concurrent_tools}, "
            f"context_window={self.context_window_tokens}, "
            f"model_bridge={type(self.model_bridge).__name__}"
        )

    async def initialize(self) -> None:
        """Initialize executor"""
        logger.info("AgentExecutor initialization complete")

    def register_tool(self, name: str, handler: Callable) -> None:
        """
        Register a tool handler.

        Args:
            name: Tool name
            handler: Async callable that accepts parameters dict and returns result
        """
        self._tool_registry[name] = handler
        logger.info(f"Registered tool: {name}")

    def unregister_tool(self, name: str) -> None:
        """
        Unregister a tool handler.

        Args:
            name: Tool name
        """
        if name in self._tool_registry:
            del self._tool_registry[name]
            logger.info(f"Unregistered tool: {name}")

    async def create_context(
        self,
        agent_id: str,
        session_id: str,
        config: AgentConfig,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> ExecutionContext:
        """
        Create execution context for an agent.

        Args:
            agent_id: Agent identifier
            session_id: Session identifier
            config: Agent configuration with tools
            initial_context: Optional initial context data

        Returns:
            ExecutionContext
        """
        context = ExecutionContext(
            agent_id=agent_id,
            session_id=session_id,
            tools=config.tools,
            context_window_tokens=self.context_window_tokens,
            metadata=initial_context or {},
        )

        self._contexts[agent_id] = context
        logger.info(f"Created execution context for agent {agent_id}")

        return context

    async def get_context(self, agent_id: str) -> ExecutionContext:
        """
        Get execution context for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            ExecutionContext

        Raises:
            ExecutorError: If context not found
        """
        context = self._contexts.get(agent_id)
        if not context:
            raise ExecutorError(
                code="E2000",
                message=f"Execution context not found for agent {agent_id}"
            )
        return context

    async def execute(
        self,
        agent_id: str,
        input_data: Dict[str, Any],
        stream: bool = False
    ) -> Any:
        """
        Execute agent with input data.

        Args:
            agent_id: Agent identifier
            input_data: Input data for execution
            stream: Whether to stream results

        Returns:
            Execution result (dict or async iterator if streaming)

        Raises:
            ExecutorError: If execution fails
        """
        logger.info(f"Executing agent {agent_id} (stream={stream})")

        context = await self.get_context(agent_id)

        # Check context overflow
        if context.is_context_full():
            raise ExecutorError(
                code="E2003",
                message="Context window exceeded"
            )

        # Add input to context
        input_content = str(input_data.get("content", ""))
        input_tokens = len(input_content.split())  # Simple token estimation
        context.add_message("user", input_content, input_tokens)

        try:
            if stream and self.enable_streaming:
                return self._execute_streaming(agent_id, context, input_data)
            else:
                return await self._execute_sync(agent_id, context, input_data)

        except Exception as e:
            logger.error(f"Execution failed for agent {agent_id}: {e}")
            raise ExecutorError(
                code="E2004",
                message=f"Execution failed: {str(e)}"
            )

    async def _execute_sync(
        self,
        agent_id: str,
        context: ExecutionContext,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute agent synchronously via LLM inference.

        Args:
            agent_id: Agent identifier
            context: Execution context
            input_data: Input data

        Returns:
            Execution result with LLM response
        """
        # Build messages for LLM from context
        messages = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in context.messages
        ]

        # Get system prompt from input or use default
        system_prompt = input_data.get("system_prompt", self.default_system_prompt)
        temperature = input_data.get("temperature", self.default_temperature)
        max_tokens = input_data.get("max_tokens", self.default_max_tokens)

        try:
            # Request LLM inference via model bridge
            response = await self.model_bridge.request_inference(
                agent_did=agent_id,
                messages=messages,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                streaming=False
            )

            # Extract response content
            content = response.get("content", "")
            token_usage = response.get("token_usage", {})
            total_tokens = token_usage.get("total_tokens", 0)

            # Parse tool calls from L04 response
            tool_calls = self._parse_tool_calls(response)

            result = {
                "agent_id": agent_id,
                "session_id": context.session_id,
                "response": content,
                "request_id": response.get("request_id"),
                "model_id": response.get("model_id"),
                "provider": response.get("provider"),
                "tool_calls": tool_calls,
                "tokens_used": total_tokens,
                "token_usage": token_usage,
                "latency_ms": response.get("latency_ms"),
                "cached": response.get("cached", False),
            }

            # Add response to context
            output_tokens = token_usage.get("output_tokens", len(content.split()))
            context.add_message("assistant", content, output_tokens)

            logger.info(
                f"Agent {agent_id} execution complete: "
                f"tokens={total_tokens}, latency={response.get('latency_ms', 0)}ms"
            )

            return result

        except ModelGatewayBridgeError as e:
            logger.error(f"LLM inference failed for agent {agent_id}: {e}")
            raise ExecutorError(
                code=e.error_code or "E2005",
                message=f"LLM inference failed: {str(e)}"
            )

    async def _execute_streaming(
        self,
        agent_id: str,
        context: ExecutionContext,
        input_data: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute agent with streaming LLM response.

        Args:
            agent_id: Agent identifier
            context: Execution context
            input_data: Input data

        Yields:
            Streaming response chunks with incremental content
        """
        # Build messages for LLM from context
        messages = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in context.messages
        ]

        # Get system prompt from input or use default
        system_prompt = input_data.get("system_prompt", self.default_system_prompt)
        temperature = input_data.get("temperature", self.default_temperature)
        max_tokens = input_data.get("max_tokens", self.default_max_tokens)

        try:
            # Request streaming inference via model bridge
            response = await self.model_bridge.request_inference(
                agent_did=agent_id,
                messages=messages,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                streaming=True
            )

            # Yield start event
            yield {
                "type": "start",
                "agent_id": agent_id,
                "session_id": context.session_id
            }

            # Accumulate full content for context update
            full_content = ""
            total_tokens = 0
            request_id = None

            # Stream chunks from model bridge
            stream = response.get("stream")
            if stream:
                async for chunk in stream:
                    request_id = chunk.get("request_id") or request_id
                    content_delta = chunk.get("content_delta", "")
                    full_content += content_delta

                    # Yield content chunk
                    yield {
                        "type": "content",
                        "delta": content_delta,
                        "request_id": request_id
                    }

                    # Check for final chunk
                    if chunk.get("is_final"):
                        total_tokens = chunk.get("token_count", 0)
                        break

            # Add full response to context
            output_tokens = total_tokens or len(full_content.split())
            context.add_message("assistant", full_content, output_tokens)

            # Yield end event
            yield {
                "type": "end",
                "agent_id": agent_id,
                "session_id": context.session_id,
                "request_id": request_id,
                "tokens_used": total_tokens,
                "content_length": len(full_content)
            }

            logger.info(
                f"Agent {agent_id} streaming complete: "
                f"content_length={len(full_content)}, tokens={total_tokens}"
            )

        except ModelGatewayBridgeError as e:
            logger.error(f"Streaming LLM inference failed for agent {agent_id}: {e}")
            # Yield error event
            yield {
                "type": "error",
                "agent_id": agent_id,
                "error_code": e.error_code or "E2005",
                "message": str(e)
            }

    def _parse_tool_calls(self, response: Dict[str, Any]) -> List[ToolInvocation]:
        """
        Parse tool_calls from L04 response into L02 ToolInvocation format.

        L04 returns tool_calls in format:
        [{"id": "...", "name": "...", "arguments": {...}}, ...]

        Args:
            response: L04 inference response

        Returns:
            List of ToolInvocation objects
        """
        raw_tool_calls = response.get("tool_calls", [])
        if not raw_tool_calls:
            return []

        tool_invocations = []
        for tc in raw_tool_calls:
            if not tc:
                continue

            # Handle both dict format and potential object format
            if isinstance(tc, dict):
                tool_name = tc.get("name", "")
                arguments = tc.get("arguments", {})
                invocation_id = tc.get("id", f"tool_{datetime.now(timezone.utc).timestamp()}")
            else:
                # Handle potential object with attributes
                tool_name = getattr(tc, "name", "")
                arguments = getattr(tc, "arguments", {})
                invocation_id = getattr(tc, "id", f"tool_{datetime.now(timezone.utc).timestamp()}")

            if not tool_name:
                logger.warning(f"Skipping tool call with empty name: {tc}")
                continue

            tool_invocations.append(
                ToolInvocation(
                    tool_name=tool_name,
                    parameters=arguments if isinstance(arguments, dict) else {},
                    invocation_id=invocation_id,
                    timeout_seconds=self.tool_timeout,
                )
            )

        if tool_invocations:
            logger.info(f"Parsed {len(tool_invocations)} tool calls from L04 response")

        return tool_invocations

    async def invoke_tool(
        self,
        agent_id: str,
        invocation: ToolInvocation
    ) -> ToolResult:
        """
        Invoke a tool with retry logic.

        Args:
            agent_id: Agent identifier
            invocation: Tool invocation request

        Returns:
            ToolResult

        Raises:
            ExecutorError: If tool invocation fails
        """
        logger.info(
            f"Invoking tool {invocation.tool_name} for agent {agent_id} "
            f"(invocation_id={invocation.invocation_id})"
        )

        # Check if tool is registered
        handler = self._tool_registry.get(invocation.tool_name)
        if not handler:
            raise ExecutorError(
                code="E2001",
                message=f"Tool {invocation.tool_name} not registered"
            )

        # Retry logic
        attempt = 0
        max_attempts = self.max_tool_retries if self.retry_on_failure else 1
        last_error = None

        while attempt < max_attempts:
            try:
                result = await self._invoke_tool_once(
                    agent_id,
                    invocation,
                    handler
                )
                return result

            except ExecutorError as e:
                last_error = e
                attempt += 1
                if attempt < max_attempts:
                    logger.warning(
                        f"Tool {invocation.tool_name} failed (attempt {attempt}/{max_attempts}), "
                        f"retrying: {e.message}"
                    )
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(
                        f"Tool {invocation.tool_name} failed after {max_attempts} attempts"
                    )

        # All retries exhausted
        raise last_error or ExecutorError(
            code="E2001",
            message=f"Tool {invocation.tool_name} failed after {max_attempts} attempts"
        )

    async def _invoke_tool_once(
        self,
        agent_id: str,
        invocation: ToolInvocation,
        handler: Callable
    ) -> ToolResult:
        """
        Single tool invocation attempt.

        Args:
            agent_id: Agent identifier
            invocation: Tool invocation request
            handler: Tool handler callable

        Returns:
            ToolResult

        Raises:
            ExecutorError: If tool invocation fails
        """
        start_time = datetime.now(timezone.utc)

        try:
            # Acquire semaphore for concurrent tool execution
            async with self._tool_semaphore:
                # Execute with timeout
                result = await asyncio.wait_for(
                    handler(invocation.parameters),
                    timeout=invocation.timeout_seconds
                )

            # Calculate execution time
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            logger.info(
                f"Tool {invocation.tool_name} executed successfully "
                f"(execution_time={execution_time:.2f}ms)"
            )

            return ToolResult(
                invocation_id=invocation.invocation_id,
                tool_name=invocation.tool_name,
                success=True,
                result=result,
                execution_time_ms=execution_time,
            )

        except asyncio.TimeoutError:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            raise ExecutorError(
                code="E2002",
                message=f"Tool {invocation.tool_name} timeout after {invocation.timeout_seconds}s"
            )
        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            logger.error(f"Tool {invocation.tool_name} failed: {e}")
            raise ExecutorError(
                code="E2001",
                message=f"Tool {invocation.tool_name} failed: {str(e)}"
            )

    async def invoke_tools_parallel(
        self,
        agent_id: str,
        invocations: List[ToolInvocation]
    ) -> List[ToolResult]:
        """
        Invoke multiple tools in parallel.

        Args:
            agent_id: Agent identifier
            invocations: List of tool invocations

        Returns:
            List of ToolResults (same order as invocations)
        """
        logger.info(f"Invoking {len(invocations)} tools in parallel for agent {agent_id}")

        tasks = [
            self.invoke_tool(agent_id, invocation)
            for invocation in invocations
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error results
        tool_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                tool_results.append(ToolResult(
                    invocation_id=invocations[i].invocation_id,
                    tool_name=invocations[i].tool_name,
                    success=False,
                    error=str(result),
                ))
            else:
                tool_results.append(result)

        return tool_results

    async def cleanup_context(self, agent_id: str) -> None:
        """
        Cleanup execution context for an agent.

        Args:
            agent_id: Agent identifier
        """
        if agent_id in self._contexts:
            del self._contexts[agent_id]
            logger.info(f"Cleaned up execution context for agent {agent_id}")

    async def cleanup(self) -> None:
        """Cleanup all execution contexts and resources"""
        logger.info("Cleaning up AgentExecutor")
        self._contexts.clear()
        self._tool_registry.clear()

        # Close model bridge
        if self.model_bridge:
            await self.model_bridge.close()

        logger.info("AgentExecutor cleanup complete")

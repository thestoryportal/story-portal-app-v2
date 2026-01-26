"""
Agent Executor

Executes agent code within configured sandbox, managing tool invocations and context.
Handles concurrent tool execution, streaming, and context window management.

Based on Section 3.3.1 of agent-runtime-layer-specification-v1.2-final-ASCII.md
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, AsyncIterator, Callable, TYPE_CHECKING
from datetime import datetime, timezone
from dataclasses import dataclass, field
import uuid

from ..models import (
    AgentConfig,
    AgentState,
    ToolDefinition,
)

# Type hints for L04 integration (avoid circular imports)
if TYPE_CHECKING:
    from L04_model_gateway.services import ModelGateway


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
        model_gateway: Optional["ModelGateway"] = None
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
            model_gateway: Optional L04 ModelGateway for LLM inference
        """
        self.config = config or {}

        # Configuration
        self.max_concurrent_tools = self.config.get("max_concurrent_tools", 10)
        self.tool_timeout = self.config.get("tool_timeout_seconds", 300)
        self.context_window_tokens = self.config.get("context_window_tokens", 128000)
        self.enable_streaming = self.config.get("enable_streaming", True)
        self.retry_on_failure = self.config.get("retry_on_tool_failure", True)
        self.max_tool_retries = self.config.get("max_tool_retries", 3)

        # L04 ModelGateway integration
        self._model_gateway = model_gateway

        # Tool registry: tool_name -> callable
        self._tool_registry: Dict[str, Callable] = {}

        # Active execution contexts
        self._contexts: Dict[str, ExecutionContext] = {}

        # Tool execution semaphore
        self._tool_semaphore = asyncio.Semaphore(self.max_concurrent_tools)

        gateway_status = "connected" if model_gateway else "not configured"
        logger.info(
            f"AgentExecutor initialized: "
            f"max_concurrent_tools={self.max_concurrent_tools}, "
            f"context_window={self.context_window_tokens}, "
            f"model_gateway={gateway_status}"
        )

    async def initialize(self) -> None:
        """Initialize executor"""
        logger.info("AgentExecutor initialization complete")

    def set_model_gateway(self, gateway: "ModelGateway") -> None:
        """
        Set the L04 ModelGateway for LLM inference.

        Args:
            gateway: L04 ModelGateway instance
        """
        self._model_gateway = gateway
        logger.info("ModelGateway connected to AgentExecutor")

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

        # Auto-create context if not exists (allows L05 to call execute directly)
        if agent_id not in self._contexts:
            from uuid import uuid4
            session_id = input_data.get("session_id", f"auto-{uuid4().hex[:8]}")
            context = ExecutionContext(
                agent_id=agent_id,
                session_id=session_id,
                context_window_tokens=self.context_window_tokens,
            )
            self._contexts[agent_id] = context
            logger.info(f"Auto-created execution context for agent {agent_id}")
        else:
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
        Execute agent synchronously.

        Args:
            agent_id: Agent identifier
            context: Execution context
            input_data: Input data

        Returns:
            Execution result
        """
        # If ModelGateway is configured, use real LLM inference
        if self._model_gateway:
            return await self._execute_with_gateway(agent_id, context, input_data)

        # Fallback to stub result (for testing or when gateway not configured)
        logger.warning(f"No ModelGateway configured for agent {agent_id}, returning stub result")
        result = {
            "agent_id": agent_id,
            "session_id": context.session_id,
            "response": "Agent execution result (stub - no ModelGateway configured)",
            "tool_calls": [],
            "tokens_used": 0,
        }

        # Add response to context
        response_tokens = len(result["response"].split())
        context.add_message("assistant", result["response"], response_tokens)

        return result

    async def _execute_with_gateway(
        self,
        agent_id: str,
        context: ExecutionContext,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute agent using L04 ModelGateway for real LLM inference.

        Args:
            agent_id: Agent identifier
            context: Execution context
            input_data: Input data

        Returns:
            Execution result with real LLM response
        """
        # Import L04 models (deferred to avoid circular imports)
        from L04_model_gateway.models import (
            InferenceRequest,
            LogicalPrompt,
            Message,
            MessageRole,
        )

        logger.info(f"Executing agent {agent_id} via L04 ModelGateway")

        # Build messages from context
        messages = []
        for msg in context.messages:
            role_map = {
                "system": MessageRole.SYSTEM,
                "user": MessageRole.USER,
                "assistant": MessageRole.ASSISTANT,
                "tool": MessageRole.TOOL,
            }
            role = role_map.get(msg["role"], MessageRole.USER)
            messages.append(Message(role=role, content=msg["content"]))

        # Add current input as user message if not already in context
        input_content = input_data.get("content", "")
        if input_content and (not messages or messages[-1].content != input_content):
            messages.append(Message(role=MessageRole.USER, content=input_content))

        # Build system prompt from task metadata
        system_prompt = input_data.get("system_prompt")
        if not system_prompt:
            task_name = input_data.get("task_name", "task")
            task_type = input_data.get("task_type", "general")
            system_prompt = f"You are an AI agent executing a {task_type} task: {task_name}. Complete the task based on the user's request."

        # Create logical prompt
        logical_prompt = LogicalPrompt(
            messages=messages,
            system_prompt=system_prompt,
            temperature=input_data.get("temperature", 0.7),
            max_tokens=input_data.get("max_tokens", 4096),
        )

        # Create inference request
        request = InferenceRequest(
            request_id=str(uuid.uuid4()),
            agent_did=agent_id,
            logical_prompt=logical_prompt,
            metadata={
                "task_id": input_data.get("task_id"),
                "task_name": input_data.get("task_name"),
                "task_type": input_data.get("task_type"),
            },
            enable_cache=input_data.get("enable_cache", True),
        )

        # Execute via ModelGateway
        try:
            response = await self._model_gateway.execute(request)

            # Build result
            result = {
                "agent_id": agent_id,
                "session_id": context.session_id,
                "response": response.content,
                "tool_calls": [tc.to_dict() for tc in (response.tool_calls or [])],
                "tokens_used": response.token_usage.total_tokens,
                "model_id": response.model_id,
                "provider": response.provider,
                "latency_ms": response.latency_ms,
                "cached": response.cached,
            }

            # Add response to context
            response_tokens = response.token_usage.output_tokens
            context.add_message("assistant", response.content, response_tokens)

            logger.info(
                f"Agent {agent_id} execution complete: "
                f"model={response.model_id}, tokens={response.token_usage.total_tokens}, "
                f"latency={response.latency_ms}ms, cached={response.cached}"
            )

            return result

        except Exception as e:
            logger.error(f"ModelGateway execution failed for agent {agent_id}: {e}")
            raise ExecutorError(
                code="E2005",
                message=f"LLM inference failed: {str(e)}"
            )

    async def _execute_streaming(
        self,
        agent_id: str,
        context: ExecutionContext,
        input_data: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute agent with streaming response.

        Args:
            agent_id: Agent identifier
            context: Execution context
            input_data: Input data

        Yields:
            Streaming response chunks
        """
        # If ModelGateway is configured, use real streaming
        if self._model_gateway:
            async for chunk in self._stream_with_gateway(agent_id, context, input_data):
                yield chunk
            return

        # Fallback to stub chunks (for testing or when gateway not configured)
        logger.warning(f"No ModelGateway configured for agent {agent_id}, returning stub stream")
        chunks = [
            {"type": "start", "agent_id": agent_id},
            {"type": "content", "delta": "Agent "},
            {"type": "content", "delta": "execution "},
            {"type": "content", "delta": "result "},
            {"type": "content", "delta": "(stub - no ModelGateway)"},
            {"type": "end", "tokens_used": 0},
        ]

        for chunk in chunks:
            yield chunk
            await asyncio.sleep(0.1)  # Simulate streaming delay

    async def _stream_with_gateway(
        self,
        agent_id: str,
        context: ExecutionContext,
        input_data: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream agent execution using L04 ModelGateway.

        Args:
            agent_id: Agent identifier
            context: Execution context
            input_data: Input data

        Yields:
            Streaming response chunks
        """
        # Import L04 models (deferred to avoid circular imports)
        from L04_model_gateway.models import (
            InferenceRequest,
            LogicalPrompt,
            Message,
            MessageRole,
        )

        logger.info(f"Streaming agent {agent_id} execution via L04 ModelGateway")

        # Build messages from context (same as _execute_with_gateway)
        messages = []
        for msg in context.messages:
            role_map = {
                "system": MessageRole.SYSTEM,
                "user": MessageRole.USER,
                "assistant": MessageRole.ASSISTANT,
                "tool": MessageRole.TOOL,
            }
            role = role_map.get(msg["role"], MessageRole.USER)
            messages.append(Message(role=role, content=msg["content"]))

        input_content = input_data.get("content", "")
        if input_content and (not messages or messages[-1].content != input_content):
            messages.append(Message(role=MessageRole.USER, content=input_content))

        # Build system prompt
        system_prompt = input_data.get("system_prompt")
        if not system_prompt:
            task_name = input_data.get("task_name", "task")
            task_type = input_data.get("task_type", "general")
            system_prompt = f"You are an AI agent executing a {task_type} task: {task_name}. Complete the task based on the user's request."

        # Create inference request with streaming enabled
        logical_prompt = LogicalPrompt(
            messages=messages,
            system_prompt=system_prompt,
            temperature=input_data.get("temperature", 0.7),
            max_tokens=input_data.get("max_tokens", 4096),
        )

        request = InferenceRequest(
            request_id=str(uuid.uuid4()),
            agent_did=agent_id,
            logical_prompt=logical_prompt,
            metadata={
                "task_id": input_data.get("task_id"),
                "task_name": input_data.get("task_name"),
                "task_type": input_data.get("task_type"),
            },
            enable_streaming=True,
        )

        # Yield start chunk
        yield {"type": "start", "agent_id": agent_id, "request_id": request.request_id}

        # Stream via ModelGateway
        full_content = ""
        total_tokens = 0

        try:
            async for chunk in self._model_gateway.stream(request):
                full_content += chunk.content_delta
                if chunk.token_count:
                    total_tokens = chunk.token_count

                yield {
                    "type": "content",
                    "delta": chunk.content_delta,
                    "is_final": chunk.is_final,
                }

                if chunk.is_final:
                    break

            # Add full response to context
            context.add_message("assistant", full_content, total_tokens)

            # Yield end chunk
            yield {
                "type": "end",
                "agent_id": agent_id,
                "tokens_used": total_tokens,
                "full_content": full_content,
            }

            logger.info(f"Agent {agent_id} streaming complete: tokens={total_tokens}")

        except Exception as e:
            logger.error(f"ModelGateway streaming failed for agent {agent_id}: {e}")
            yield {
                "type": "error",
                "agent_id": agent_id,
                "error": str(e),
            }

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
        """Cleanup all execution contexts"""
        logger.info("Cleaning up AgentExecutor")
        self._contexts.clear()
        self._tool_registry.clear()
        logger.info("AgentExecutor cleanup complete")

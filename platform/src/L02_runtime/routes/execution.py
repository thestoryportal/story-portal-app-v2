"""
L02 Agent Runtime - Execution HTTP API Routes

Provides HTTP endpoints for agent execution operations.
Includes synchronous execution and SSE streaming support.
"""

import logging
import json
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from ..dtos import (
    ExecuteRequestDTO,
    ExecuteResponseDTO,
    StreamChunkDTO,
    ToolCallDTO,
    TokenUsageDTO,
    ErrorResponseDTO,
)
from ..services.agent_executor import ExecutorError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents", tags=["execution"])


# ============================================================================
# Endpoints
# ============================================================================

@router.post(
    "/{agent_id}/execute",
    response_model=ExecuteResponseDTO,
    responses={
        400: {"model": ErrorResponseDTO, "description": "Invalid request"},
        404: {"model": ErrorResponseDTO, "description": "Agent not found"},
        500: {"model": ErrorResponseDTO, "description": "Internal error"},
        503: {"model": ErrorResponseDTO, "description": "Service unavailable"},
    }
)
async def execute_agent(
    agent_id: str,
    request_dto: ExecuteRequestDTO,
    request: Request
) -> ExecuteResponseDTO:
    """
    Execute agent with input synchronously.

    Sends input to the agent and waits for complete response.
    For streaming responses, use the /execute/stream endpoint.
    """
    runtime = getattr(request.app.state, "runtime", None)
    if not runtime:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponseDTO(
                error_code="E2000",
                message="AgentRuntime not initialized"
            ).model_dump()
        )

    executor = runtime.agent_executor
    if not executor:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponseDTO(
                error_code="E2000",
                message="AgentExecutor not initialized"
            ).model_dump()
        )

    try:
        logger.info(f"Execute request for agent {agent_id}")

        # Build input data
        input_data = {
            "content": request_dto.content,
        }
        if request_dto.system_prompt:
            input_data["system_prompt"] = request_dto.system_prompt
        if request_dto.temperature is not None:
            input_data["temperature"] = request_dto.temperature
        if request_dto.max_tokens:
            input_data["max_tokens"] = request_dto.max_tokens

        # Execute via agent executor
        result = await executor.execute(
            agent_id=agent_id,
            input_data=input_data,
            stream=False,
        )

        # Parse tool calls from result
        tool_calls = []
        for tc in result.get("tool_calls", []):
            if hasattr(tc, "tool_name"):
                # ToolInvocation object
                tool_calls.append(ToolCallDTO(
                    id=tc.invocation_id,
                    name=tc.tool_name,
                    arguments=tc.parameters,
                ))
            elif isinstance(tc, dict):
                # Dictionary from L04
                tool_calls.append(ToolCallDTO(
                    id=tc.get("id", ""),
                    name=tc.get("name", ""),
                    arguments=tc.get("arguments", {}),
                ))

        # Build token usage
        token_usage_data = result.get("token_usage", {})
        token_usage = TokenUsageDTO(
            input_tokens=token_usage_data.get("input_tokens", 0),
            output_tokens=token_usage_data.get("output_tokens", 0),
            cached_tokens=token_usage_data.get("cached_tokens", 0),
            total_tokens=token_usage_data.get("total_tokens", result.get("tokens_used", 0)),
        )

        return ExecuteResponseDTO(
            agent_id=result["agent_id"],
            session_id=result["session_id"],
            request_id=result.get("request_id"),
            model_id=result.get("model_id"),
            provider=result.get("provider"),
            response=result.get("response", ""),
            tool_calls=tool_calls,
            token_usage=token_usage,
            latency_ms=result.get("latency_ms"),
            cached=result.get("cached", False),
        )

    except ExecutorError as e:
        logger.error(f"Executor error for agent {agent_id}: {e}")
        status_code = 500
        if e.code == "E2000":
            status_code = 404
        elif e.code == "E2003":
            status_code = 400  # Context overflow

        raise HTTPException(
            status_code=status_code,
            detail=ErrorResponseDTO(
                error_code=e.code,
                message=e.message
            ).model_dump()
        )
    except Exception as e:
        logger.exception(f"Failed to execute agent {agent_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponseDTO(
                error_code="E2004",
                message=f"Execution failed: {str(e)}"
            ).model_dump()
        )


@router.post(
    "/{agent_id}/execute/stream",
    responses={
        400: {"model": ErrorResponseDTO, "description": "Invalid request"},
        404: {"model": ErrorResponseDTO, "description": "Agent not found"},
        500: {"model": ErrorResponseDTO, "description": "Internal error"},
        503: {"model": ErrorResponseDTO, "description": "Service unavailable"},
    }
)
async def execute_agent_stream(
    agent_id: str,
    request_dto: ExecuteRequestDTO,
    request: Request
):
    """
    Execute agent with streaming response.

    Returns Server-Sent Events (SSE) stream with incremental content.
    Each event contains a StreamChunkDTO.

    Event types:
    - start: Stream started
    - content: Content chunk with delta text
    - tool_call: Tool invocation requested
    - end: Stream completed with final stats
    - error: Error occurred
    """
    runtime = getattr(request.app.state, "runtime", None)
    if not runtime:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponseDTO(
                error_code="E2000",
                message="AgentRuntime not initialized"
            ).model_dump()
        )

    executor = runtime.agent_executor
    if not executor:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponseDTO(
                error_code="E2000",
                message="AgentExecutor not initialized"
            ).model_dump()
        )

    async def generate_sse() -> AsyncIterator[str]:
        """Generate SSE stream from executor"""
        try:
            logger.info(f"Streaming execute request for agent {agent_id}")

            # Build input data
            input_data = {
                "content": request_dto.content,
            }
            if request_dto.system_prompt:
                input_data["system_prompt"] = request_dto.system_prompt
            if request_dto.temperature is not None:
                input_data["temperature"] = request_dto.temperature
            if request_dto.max_tokens:
                input_data["max_tokens"] = request_dto.max_tokens

            # Execute with streaming
            result = await executor.execute(
                agent_id=agent_id,
                input_data=input_data,
                stream=True,
            )

            # Stream chunks
            async for chunk in result:
                chunk_type = chunk.get("type", "content")

                if chunk_type == "start":
                    dto = StreamChunkDTO(
                        type="start",
                        agent_id=agent_id,
                        session_id=chunk.get("session_id"),
                    )
                elif chunk_type == "content":
                    dto = StreamChunkDTO(
                        type="content",
                        agent_id=agent_id,
                        request_id=chunk.get("request_id"),
                        delta=chunk.get("delta", ""),
                    )
                elif chunk_type == "end":
                    dto = StreamChunkDTO(
                        type="end",
                        agent_id=agent_id,
                        session_id=chunk.get("session_id"),
                        request_id=chunk.get("request_id"),
                        tokens_used=chunk.get("tokens_used"),
                        content_length=chunk.get("content_length"),
                    )
                elif chunk_type == "error":
                    dto = StreamChunkDTO(
                        type="error",
                        agent_id=agent_id,
                        error_code=chunk.get("error_code", "E2004"),
                        message=chunk.get("message", "Unknown error"),
                    )
                else:
                    # Unknown chunk type, skip
                    continue

                yield f"data: {dto.model_dump_json()}\n\n"

                if chunk_type in ("end", "error"):
                    break

            # Send done event
            yield "data: [DONE]\n\n"

        except ExecutorError as e:
            logger.error(f"Executor error during streaming for agent {agent_id}: {e}")
            error_dto = StreamChunkDTO(
                type="error",
                agent_id=agent_id,
                error_code=e.code,
                message=e.message,
            )
            yield f"data: {error_dto.model_dump_json()}\n\n"

        except Exception as e:
            logger.exception(f"Error during streaming for agent {agent_id}: {e}")
            error_dto = StreamChunkDTO(
                type="error",
                agent_id=agent_id,
                error_code="E2004",
                message=f"Streaming error: {str(e)}",
            )
            yield f"data: {error_dto.model_dump_json()}\n\n"

    return StreamingResponse(
        generate_sse(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

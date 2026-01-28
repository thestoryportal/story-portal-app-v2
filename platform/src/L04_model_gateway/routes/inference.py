"""
L04 Model Gateway Layer - Inference HTTP API Routes

Provides HTTP endpoints for LLM inference operations.
These endpoints are consumed by L02 Runtime via ModelGatewayBridge.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json

from ..models import (
    Message,
    MessageRole,
    LogicalPrompt,
    InferenceRequest,
    InferenceResponse,
    StreamChunk,
    L04Error,
    L04ErrorCode
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["inference"])


# ============================================================================
# Request/Response DTOs (Pydantic v2)
# ============================================================================

class MessageDTO(BaseModel):
    """Message in conversation format"""
    role: str = Field(..., description="Message role: system, user, assistant, tool")
    content: str = Field(..., description="Message content")
    name: Optional[str] = Field(None, description="Optional name for the message sender")
    tool_call_id: Optional[str] = Field(None, description="Tool call ID if this is a tool response")

    model_config = {"extra": "ignore"}


class InferenceRequestDTO(BaseModel):
    """HTTP request DTO for inference endpoint"""
    agent_did: str = Field(..., description="Agent DID requesting inference")
    messages: List[MessageDTO] = Field(..., description="Conversation messages")
    system_prompt: Optional[str] = Field(None, description="System prompt")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, gt=0, description="Maximum tokens to generate")
    model_id: Optional[str] = Field(None, description="Specific model to use (optional)")
    enable_cache: bool = Field(True, description="Enable semantic caching")
    capabilities: Optional[List[str]] = Field(None, description="Required capabilities")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    model_config = {"extra": "ignore"}


class TokenUsageDTO(BaseModel):
    """Token usage information"""
    input_tokens: int
    output_tokens: int
    cached_tokens: int = 0
    total_tokens: int


class InferenceResponseDTO(BaseModel):
    """HTTP response DTO for inference endpoint"""
    request_id: str
    model_id: str
    provider: str
    content: str
    token_usage: TokenUsageDTO
    latency_ms: int
    cached: bool = False
    finish_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    model_config = {"extra": "ignore"}


class StreamChunkDTO(BaseModel):
    """SSE chunk for streaming responses"""
    request_id: str
    content_delta: str
    is_final: bool = False
    token_count: Optional[int] = None
    finish_reason: Optional[str] = None


class ErrorResponseDTO(BaseModel):
    """Error response DTO"""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None


# ============================================================================
# Helper Functions
# ============================================================================

def dto_to_inference_request(dto: InferenceRequestDTO) -> InferenceRequest:
    """Convert HTTP DTO to internal InferenceRequest"""
    messages = [
        Message(
            role=MessageRole(msg.role),
            content=msg.content,
            name=msg.name,
            tool_call_id=msg.tool_call_id
        )
        for msg in dto.messages
    ]

    logical_prompt = LogicalPrompt(
        messages=messages,
        system_prompt=dto.system_prompt,
        temperature=dto.temperature,
        max_tokens=dto.max_tokens
    )

    return InferenceRequest(
        request_id=str(uuid.uuid4()),
        agent_did=dto.agent_did,
        logical_prompt=logical_prompt,
        enable_cache=dto.enable_cache,
        metadata=dto.metadata or {}
    )


def inference_response_to_dto(response: InferenceResponse) -> InferenceResponseDTO:
    """Convert internal InferenceResponse to HTTP DTO"""
    return InferenceResponseDTO(
        request_id=response.request_id,
        model_id=response.model_id,
        provider=response.provider,
        content=response.content,
        token_usage=TokenUsageDTO(
            input_tokens=response.token_usage.input_tokens,
            output_tokens=response.token_usage.output_tokens,
            cached_tokens=response.token_usage.cached_tokens,
            total_tokens=response.token_usage.total_tokens
        ),
        latency_ms=response.latency_ms,
        cached=response.cached,
        finish_reason=response.finish_reason,
        metadata=response.metadata
    )


# ============================================================================
# Endpoints
# ============================================================================

@router.post(
    "/inference",
    response_model=InferenceResponseDTO,
    responses={
        400: {"model": ErrorResponseDTO, "description": "Invalid request"},
        429: {"model": ErrorResponseDTO, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponseDTO, "description": "Internal error"},
        503: {"model": ErrorResponseDTO, "description": "Service unavailable"}
    }
)
async def inference(
    request_dto: InferenceRequestDTO,
    request: Request
) -> InferenceResponseDTO:
    """
    Execute synchronous LLM inference

    Receives a prompt and returns the complete model response.
    Uses the ModelGateway service for routing, caching, and failover.
    """
    # Get gateway from app state
    gateway = request.app.state.model_gateway
    if not gateway:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponseDTO(
                error_code="E4000",
                message="ModelGateway not initialized"
            ).model_dump()
        )

    try:
        logger.info(f"Inference request from agent {request_dto.agent_did}")

        # Convert DTO to internal request
        inference_req = dto_to_inference_request(request_dto)

        # Execute through gateway
        response = await gateway.execute(inference_req)

        # Convert to response DTO
        return inference_response_to_dto(response)

    except L04Error as e:
        logger.error(f"L04 error during inference: {e}")
        status_code = 500
        if e.code.name.startswith("E43"):  # Rate limit errors
            status_code = 429
        elif e.code.name.startswith("E42"):  # Provider errors
            status_code = 503

        raise HTTPException(
            status_code=status_code,
            detail=ErrorResponseDTO(
                error_code=e.code.name,
                message=str(e),
                details=e.details
            ).model_dump()
        )
    except Exception as e:
        logger.exception(f"Unexpected error during inference: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponseDTO(
                error_code="E4999",
                message=f"Unexpected error: {str(e)}"
            ).model_dump()
        )


@router.post(
    "/inference/stream",
    responses={
        400: {"model": ErrorResponseDTO, "description": "Invalid request"},
        429: {"model": ErrorResponseDTO, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponseDTO, "description": "Internal error"},
        503: {"model": ErrorResponseDTO, "description": "Service unavailable"}
    }
)
async def inference_stream(
    request_dto: InferenceRequestDTO,
    request: Request
):
    """
    Execute streaming LLM inference

    Returns Server-Sent Events (SSE) stream with incremental content.
    Each event contains a StreamChunkDTO.
    """
    # Get gateway from app state
    gateway = request.app.state.model_gateway
    if not gateway:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponseDTO(
                error_code="E4000",
                message="ModelGateway not initialized"
            ).model_dump()
        )

    async def generate_sse():
        """Generate SSE stream from ModelGateway"""
        try:
            logger.info(f"Streaming inference request from agent {request_dto.agent_did}")

            # Convert DTO to internal request
            inference_req = dto_to_inference_request(request_dto)
            inference_req.enable_streaming = True

            # Stream through gateway
            async for chunk in gateway.stream(inference_req):
                chunk_dto = StreamChunkDTO(
                    request_id=chunk.request_id,
                    content_delta=chunk.content_delta,
                    is_final=chunk.is_final,
                    token_count=chunk.token_count,
                    finish_reason=chunk.finish_reason
                )
                yield f"data: {chunk_dto.model_dump_json()}\n\n"

                if chunk.is_final:
                    break

            # Send done event
            yield "data: [DONE]\n\n"

        except L04Error as e:
            logger.error(f"L04 error during streaming: {e}")
            error_dto = ErrorResponseDTO(
                error_code=e.code.name,
                message=str(e),
                details=e.details
            )
            yield f"data: {json.dumps({'error': error_dto.model_dump()})}\n\n"
        except Exception as e:
            logger.exception(f"Unexpected error during streaming: {e}")
            error_dto = ErrorResponseDTO(
                error_code="E4999",
                message=f"Streaming error: {str(e)}"
            )
            yield f"data: {json.dumps({'error': error_dto.model_dump()})}\n\n"

    return StreamingResponse(
        generate_sse(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/inference/health")
async def inference_health(request: Request):
    """
    Check inference service health

    Returns health status of the ModelGateway and all providers.
    """
    gateway = request.app.state.model_gateway
    if not gateway:
        return {
            "status": "unhealthy",
            "message": "ModelGateway not initialized"
        }

    try:
        health = await gateway.health_check()
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "gateway": health
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

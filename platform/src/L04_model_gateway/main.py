"""
L04 Model Gateway - FastAPI Application

Provides HTTP endpoints for LLM inference with intelligent routing,
caching, rate limiting, and failover.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging
import asyncio
import json

from .services.model_gateway import ModelGateway
from .services.model_registry import ModelRegistry
from .models import (
    InferenceRequest,
    InferenceResponse,
    LogicalPrompt,
    Message,
    MessageRole,
    ModelRequirements,
    RequestConstraints,
    RoutingStrategy,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="L04 Model Gateway",
    description="Intelligent LLM inference gateway with routing, caching, and failover",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global gateway instance
gateway: Optional[ModelGateway] = None


# ============================================================================
# Pydantic Models for API
# ============================================================================

class MessageInput(BaseModel):
    """API message input"""
    role: str = Field(..., description="Message role: system, user, assistant, tool")
    content: str = Field(..., description="Message content")
    name: Optional[str] = None
    tool_call_id: Optional[str] = None


class InferenceRequestInput(BaseModel):
    """API inference request"""
    model_id: Optional[str] = Field(None, description="Specific model to use (optional)")
    prompt: Optional[str] = Field(None, description="Simple prompt (alternative to messages)")
    messages: Optional[List[MessageInput]] = Field(None, description="Chat messages")
    system_prompt: Optional[str] = Field(None, description="System prompt")
    temperature: float = Field(0.7, ge=0, le=2, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, description="Maximum output tokens")
    agent_did: str = Field("did:agent:api-client", description="Agent DID for tracking")
    enable_cache: bool = Field(True, description="Enable response caching")
    enable_streaming: bool = Field(False, description="Enable streaming response")
    capabilities: Optional[List[str]] = Field(None, description="Required capabilities")
    routing_strategy: Optional[str] = Field(None, description="Routing strategy: cost, quality, latency, balanced")


class InferenceResponseOutput(BaseModel):
    """API inference response"""
    request_id: str
    model_id: str
    provider: str
    content: str
    token_usage: Dict[str, int]
    latency_ms: int
    cached: bool
    status: str
    finish_reason: Optional[str] = None
    error_message: Optional[str] = None


class ModelInfo(BaseModel):
    """Model information for listing"""
    model_id: str
    provider: str
    display_name: str
    context_window: int
    max_output_tokens: int
    capabilities: List[str]
    status: str
    cost_per_1m_input: float
    cost_per_1m_output: float


# ============================================================================
# Health Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "L04 Model Gateway",
        "version": "2.0.0",
        "status": "operational",
        "endpoints": {
            "inference": "/api/v1/inference",
            "models": "/api/v1/models",
            "health": "/health"
        }
    }


@app.get("/health")
async def health():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "service": "l04-model-gateway",
        "version": "2.0.0"
    }


@app.get("/health/live")
async def health_live():
    """Liveness probe"""
    return {"status": "alive"}


@app.get("/health/ready")
async def health_ready():
    """Readiness probe"""
    if gateway is None:
        raise HTTPException(status_code=503, detail="Gateway not initialized")
    return {"status": "ready"}


@app.get("/health/detailed")
async def health_detailed():
    """Detailed health check with component status"""
    if gateway is None:
        raise HTTPException(status_code=503, detail="Gateway not initialized")

    try:
        health_data = await gateway.health_check()
        return health_data
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Model Endpoints
# ============================================================================

@app.get("/api/v1/models", response_model=List[ModelInfo])
async def list_models(
    provider: Optional[str] = None,
    capability: Optional[str] = None
):
    """
    List available models

    Args:
        provider: Filter by provider (e.g., "ollama", "openai")
        capability: Filter by capability (e.g., "vision", "tool_use")
    """
    if gateway is None:
        raise HTTPException(status_code=503, detail="Gateway not initialized")

    try:
        models = []
        all_models = gateway.registry.get_all_models()

        for model in all_models:
            # Apply filters
            if provider and model.provider != provider:
                continue
            if capability and capability not in model.capabilities.capabilities_list:
                continue

            models.append(ModelInfo(
                model_id=model.model_id,
                provider=model.provider,
                display_name=model.display_name,
                context_window=model.context_window,
                max_output_tokens=model.max_output_tokens,
                capabilities=model.capabilities.capabilities_list,
                status=model.status.value,
                cost_per_1m_input=model.cost_per_1m_input_tokens,
                cost_per_1m_output=model.cost_per_1m_output_tokens,
            ))

        return models

    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/models/{model_id}")
async def get_model(model_id: str):
    """Get details for a specific model"""
    if gateway is None:
        raise HTTPException(status_code=503, detail="Gateway not initialized")

    model = gateway.registry.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model not found: {model_id}")

    return ModelInfo(
        model_id=model.model_id,
        provider=model.provider,
        display_name=model.display_name,
        context_window=model.context_window,
        max_output_tokens=model.max_output_tokens,
        capabilities=model.capabilities.capabilities_list,
        status=model.status.value,
        cost_per_1m_input=model.cost_per_1m_input_tokens,
        cost_per_1m_output=model.cost_per_1m_output_tokens,
    )


# ============================================================================
# Inference Endpoints
# ============================================================================

@app.post("/api/v1/inference", response_model=InferenceResponseOutput)
async def inference(request: InferenceRequestInput):
    """
    Execute inference request

    Supports both simple prompts and chat messages format.
    """
    if gateway is None:
        raise HTTPException(status_code=503, detail="Gateway not initialized")

    try:
        # Build messages
        messages = []

        if request.system_prompt:
            messages.append(Message(
                role=MessageRole.SYSTEM,
                content=request.system_prompt
            ))

        if request.messages:
            for msg in request.messages:
                role = MessageRole(msg.role)
                messages.append(Message(
                    role=role,
                    content=msg.content,
                    name=msg.name,
                    tool_call_id=msg.tool_call_id
                ))
        elif request.prompt:
            messages.append(Message(
                role=MessageRole.USER,
                content=request.prompt
            ))
        else:
            raise HTTPException(
                status_code=400,
                detail="Either 'prompt' or 'messages' must be provided"
            )

        # Build logical prompt
        logical_prompt = LogicalPrompt(
            messages=messages,
            system_prompt=request.system_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )

        # Build requirements
        requirements = ModelRequirements(
            capabilities=request.capabilities or [],
            max_output_tokens=request.max_tokens or 4096
        )

        # Create inference request
        inference_req = InferenceRequest.create(
            agent_did=request.agent_did,
            messages=messages,
            system_prompt=request.system_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            capabilities=request.capabilities,
            enable_cache=request.enable_cache,
            enable_streaming=request.enable_streaming
        )

        # Parse routing strategy
        routing_strategy = None
        if request.routing_strategy:
            try:
                routing_strategy = RoutingStrategy(request.routing_strategy)
            except ValueError:
                pass  # Use default

        # Execute request
        response = await gateway.execute(inference_req, routing_strategy)

        return InferenceResponseOutput(
            request_id=response.request_id,
            model_id=response.model_id,
            provider=response.provider,
            content=response.content,
            token_usage=response.token_usage.to_dict(),
            latency_ms=response.latency_ms,
            cached=response.cached,
            status=response.status.value,
            finish_reason=response.finish_reason,
            error_message=response.error_message
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Inference failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/inference/stream")
async def inference_stream(request: InferenceRequestInput):
    """
    Execute streaming inference request

    Returns Server-Sent Events (SSE) stream.
    """
    if gateway is None:
        raise HTTPException(status_code=503, detail="Gateway not initialized")

    try:
        # Build messages (same as non-streaming)
        messages = []

        if request.system_prompt:
            messages.append(Message(
                role=MessageRole.SYSTEM,
                content=request.system_prompt
            ))

        if request.messages:
            for msg in request.messages:
                role = MessageRole(msg.role)
                messages.append(Message(
                    role=role,
                    content=msg.content,
                    name=msg.name,
                    tool_call_id=msg.tool_call_id
                ))
        elif request.prompt:
            messages.append(Message(
                role=MessageRole.USER,
                content=request.prompt
            ))
        else:
            raise HTTPException(
                status_code=400,
                detail="Either 'prompt' or 'messages' must be provided"
            )

        # Create inference request
        inference_req = InferenceRequest.create(
            agent_did=request.agent_did,
            messages=messages,
            system_prompt=request.system_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            capabilities=request.capabilities,
            enable_cache=False,  # Streaming bypasses cache
            enable_streaming=True
        )

        async def generate():
            try:
                async for chunk in gateway.stream(inference_req):
                    data = json.dumps(chunk.to_dict())
                    yield f"data: {data}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                error_data = json.dumps({"error": str(e)})
                yield f"data: {error_data}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Streaming inference failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Simple completion endpoint (OpenAI-compatible format)
@app.post("/api/v1/completions")
async def completions(
    model: str = "llama3.2:3b",
    prompt: str = "",
    max_tokens: int = 256,
    temperature: float = 0.7
):
    """
    Simple completion endpoint (OpenAI-compatible)
    """
    request = InferenceRequestInput(
        model_id=model,
        prompt=prompt,
        max_tokens=max_tokens,
        temperature=temperature
    )
    return await inference(request)


# ============================================================================
# Lifecycle Events
# ============================================================================

@app.on_event("startup")
async def startup():
    """Initialize gateway on startup"""
    global gateway

    logger.info("L04 Model Gateway starting...")

    try:
        # Initialize gateway with all components
        gateway = ModelGateway()

        # Log registered models
        models = gateway.registry.get_all_models()
        logger.info(f"Registered {len(models)} models:")
        for model in models:
            logger.info(f"  - {model.model_id} ({model.provider})")

        # Log available providers
        logger.info(f"Available providers: {list(gateway.providers.keys())}")

        logger.info("L04 Model Gateway started successfully")

    except Exception as e:
        logger.error(f"Failed to initialize gateway: {e}")
        # Don't fail startup - health checks will report not ready


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    global gateway

    logger.info("L04 Model Gateway shutting down...")

    if gateway:
        await gateway.close()

    logger.info("L04 Model Gateway shutdown complete")

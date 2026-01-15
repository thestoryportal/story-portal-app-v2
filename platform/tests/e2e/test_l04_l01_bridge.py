"""
E2E tests for L04 Model Gateway - L01 Data Layer bridge integration.

Tests the complete flow of recording model inference usage in L01.
"""

import pytest
import asyncio
import httpx
from datetime import datetime
from decimal import Decimal

from src.L04_model_gateway.services.l01_bridge import L04Bridge
from src.L04_model_gateway.models import (
    InferenceRequest,
    InferenceResponse,
    TokenUsage,
    CostBreakdown,
    ResponseStatus,
    Message,
    MessageRole
)
from src.L01_data_layer.client import L01Client


@pytest.mark.asyncio
class TestL04L01Integration:
    """Test L04-L01 integration end-to-end."""

    @pytest.fixture
    async def bridge(self):
        """Create L04Bridge instance."""
        bridge = L04Bridge(l01_base_url="http://localhost:8002")
        await bridge.initialize()
        yield bridge
        await bridge.cleanup()

    @pytest.fixture
    async def l01_client(self):
        """Create L01Client instance for verification."""
        client = L01Client(base_url="http://localhost:8002")
        yield client
        await client.close()

    async def test_bridge_initialization(self, bridge):
        """Test that L04Bridge initializes correctly."""
        assert bridge is not None
        assert bridge.l01_client is not None
        assert bridge.enabled is True

    async def test_record_successful_inference(self, bridge, l01_client):
        """Test recording a successful model inference."""
        # Create inference request
        request = InferenceRequest.create(
            agent_did="did:example:test-agent-123",
            messages=[Message(role=MessageRole.USER, content="Hello, world!")],
            metadata={
                "tenant_id": "tenant-001",
                "session_id": "session-abc-123"
            }
        )

        # Create successful response
        response = InferenceResponse(
            request_id=request.request_id,
            model_id="qwen2.5:latest",
            provider="ollama",
            content="Hello! How can I help you today?",
            token_usage=TokenUsage(
                input_tokens=12,
                output_tokens=8,
                cached_tokens=0
            ),
            cost_breakdown=CostBreakdown(
                input_cost_cents=0.024,
                output_cost_cents=0.032,
                cached_cost_cents=0.0
            ),
            latency_ms=145,
            cached=False,
            status=ResponseStatus.SUCCESS,
            finish_reason="stop"
        )

        # Record in L01
        result = await bridge.record_inference(request, response)
        assert result is True

        # Verify record was created in L01
        await asyncio.sleep(0.1)  # Allow async write to complete

        # Query L01 to verify
        async with httpx.AsyncClient() as client:
            http_response = await client.get("http://localhost:8002/models/usage?limit=1")
            http_response.raise_for_status()
            response_data = http_response.json()

        assert len(response_data) > 0
        record = response_data[0]
        assert record["request_id"] == request.request_id
        assert record["model_id"] == "qwen2.5:latest"
        assert record["model_provider"] == "ollama"
        assert record["input_tokens"] == 12
        assert record["output_tokens"] == 8
        assert record["total_tokens"] == 20
        assert record["latency_ms"] == 145
        assert record["cached"] is False
        assert record["finish_reason"] == "stop"
        assert record["response_status"] == "success"

    async def test_record_failed_inference(self, bridge, l01_client):
        """Test recording a failed model inference."""
        # Create inference request
        request = InferenceRequest.create(
            agent_did="did:example:test-agent-456",
            messages=[Message(role=MessageRole.USER, content="Test error handling")],
            metadata={"session_id": "session-error-789"}
        )

        # Create failed response
        response = InferenceResponse(
            request_id=request.request_id,
            model_id="nonexistent-model",
            provider="ollama",
            content="",
            token_usage=TokenUsage(
                input_tokens=5,
                output_tokens=0,
                cached_tokens=0
            ),
            latency_ms=50,
            cached=False,
            status=ResponseStatus.ERROR,
            finish_reason="error",
            error_message="Model not found: nonexistent-model"
        )

        # Record in L01
        result = await bridge.record_inference(request, response)
        assert result is True

        # Verify error record was created
        await asyncio.sleep(0.1)

        async with httpx.AsyncClient() as client:
            http_response = await client.get("http://localhost:8002/models/usage?limit=1")
            http_response.raise_for_status()
            response_data = http_response.json()

        assert len(response_data) > 0
        record = response_data[0]
        assert record["request_id"] == request.request_id
        assert record["response_status"] == "error"
        assert record["error_message"] == "Model not found: nonexistent-model"
        assert record["finish_reason"] == "error"
        assert record["output_tokens"] == 0

    async def test_record_cached_inference(self, bridge, l01_client):
        """Test recording a cached model inference."""
        # Create inference request
        request = InferenceRequest.create(
            agent_did="did:example:test-agent-789",
            messages=[Message(role=MessageRole.USER, content="Cached response test")],
            enable_cache=True,
            metadata={
                "tenant_id": "tenant-002",
                "session_id": "session-cache-456"
            }
        )

        # Create cached response (no cost, fast latency)
        response = InferenceResponse(
            request_id=request.request_id,
            model_id="llama3.2:latest",
            provider="ollama",
            content="This is a cached response!",
            token_usage=TokenUsage(
                input_tokens=8,
                output_tokens=6,
                cached_tokens=6  # Output was cached
            ),
            cost_breakdown=CostBreakdown(
                input_cost_cents=0.016,
                output_cost_cents=0.0,  # No output cost for cached
                cached_cost_cents=0.006  # Small cache retrieval cost
            ),
            latency_ms=12,  # Very fast due to cache
            cached=True,
            status=ResponseStatus.SUCCESS,
            finish_reason="stop"
        )

        # Record in L01
        result = await bridge.record_inference(request, response)
        assert result is True

        # Verify cached record
        await asyncio.sleep(0.1)

        async with httpx.AsyncClient() as client:
            http_response = await client.get("http://localhost:8002/models/usage?limit=1")
            http_response.raise_for_status()
            response_data = http_response.json()

        assert len(response_data) > 0
        record = response_data[0]
        assert record["request_id"] == request.request_id
        assert record["cached"] is True
        assert record["cached_tokens"] == 6
        assert record["latency_ms"] == 12
        assert float(record["cost_cached_cents"]) == 0.006

    async def test_full_inference_lifecycle_with_metadata(self, bridge, l01_client):
        """Test complete inference lifecycle with rich metadata."""
        # Create request with extensive metadata
        request = InferenceRequest.create(
            agent_did="did:example:production-agent",
            messages=[
                Message(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
                Message(role=MessageRole.USER, content="Explain quantum computing in simple terms.")
            ],
            system_prompt="You are a helpful assistant.",
            temperature=0.7,
            max_tokens=500,
            enable_cache=False,
            metadata={
                "tenant_id": "tenant-prod-001",
                "session_id": "session-quantum-discussion",
                "user_id": "user-12345",
                "request_source": "web-app",
                "feature": "chat"
            }
        )

        # Create response with full details
        response = InferenceResponse(
            request_id=request.request_id,
            model_id="mixtral:8x7b",
            provider="ollama",
            content="Quantum computing is like having a super powerful computer that...",
            token_usage=TokenUsage(
                input_tokens=35,
                output_tokens=142,
                cached_tokens=0
            ),
            cost_breakdown=CostBreakdown(
                input_cost_cents=0.14,   # $0.004 per 1K tokens
                output_cost_cents=1.704,  # $0.012 per 1K tokens
                cached_cost_cents=0.0
            ),
            latency_ms=2340,
            cached=False,
            status=ResponseStatus.SUCCESS,
            finish_reason="stop",
            metadata={
                "model_version": "mixtral-8x7b-instruct-v0.1",
                "temperature_used": 0.7,
                "tokens_limit": 500,
                "stop_reason": "natural_completion"
            }
        )

        # Record in L01
        result = await bridge.record_inference(request, response)
        assert result is True

        # Verify complete record with all metadata
        await asyncio.sleep(0.1)

        async with httpx.AsyncClient() as client:
            http_response = await client.get("http://localhost:8002/models/usage?limit=1")
            http_response.raise_for_status()
            response_data = http_response.json()

        assert len(response_data) > 0
        record = response_data[0]

        # Verify core fields
        assert record["request_id"] == request.request_id
        assert record["agent_did"] == "did:example:production-agent"
        assert record["tenant_id"] == "tenant-prod-001"
        assert record["session_id"] == "session-quantum-discussion"
        assert record["model_id"] == "mixtral:8x7b"
        assert record["model_provider"] == "ollama"

        # Verify token usage
        assert record["input_tokens"] == 35
        assert record["output_tokens"] == 142
        assert record["total_tokens"] == 177

        # Verify cost breakdown
        assert float(record["cost_estimate"]) == 0.01844
        assert float(record["cost_input_cents"]) == 0.14
        assert float(record["cost_output_cents"]) == 1.704

        # Verify performance
        assert record["latency_ms"] == 2340
        assert record["cached"] is False

        # Verify status
        assert record["finish_reason"] == "stop"
        assert record["response_status"] == "success"

        # Verify metadata JSONB field contains response metadata
        assert record["metadata"] is not None
        assert "model_version" in record["metadata"]

    async def test_bridge_disabled(self):
        """Test that disabled bridge doesn't record."""
        bridge = L04Bridge()
        bridge.enabled = False

        request = InferenceRequest.create(
            agent_did="did:example:test",
            messages=[Message(role=MessageRole.USER, content="test")]
        )

        response = InferenceResponse(
            request_id=request.request_id,
            model_id="test-model",
            provider="mock",
            content="test",
            token_usage=TokenUsage(input_tokens=1, output_tokens=1),
            latency_ms=10,
            status=ResponseStatus.SUCCESS
        )

        result = await bridge.record_inference(request, response)
        assert result is False

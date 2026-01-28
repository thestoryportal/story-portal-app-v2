# L04 Model Gateway Layer

The Model Gateway Layer provides intelligent routing and execution of LLM inference requests across multiple providers with caching, rate limiting, and failover capabilities.

## Status: Production Ready

- 194 tests passing (unit, integration, E2E)
- 5 provider adapters implemented
- Prometheus metrics instrumented
- L01 integration complete

## Overview

The L04 Model Gateway Layer sits between the agent runtime (L02) and external LLM providers, providing:

- **Unified Interface**: Single API for multiple LLM providers (Anthropic, OpenAI, Ollama, Claude Code)
- **Intelligent Routing**: Capability-based model selection with cost and latency optimization
- **Semantic Caching**: Embedding-based caching to reduce costs and improve latency
- **Rate Limiting**: Token bucket rate limiting per agent and provider
- **Circuit Breaker**: Automatic failover when providers are unhealthy
- **Request Queue**: Priority queue for request buffering during load spikes
- **Observability**: Prometheus metrics for monitoring and alerting

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Model Gateway Layer (L04)                      │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Registry │  │  Router  │  │  Health  │  │ Metrics  │   │
│  │          │  │          │  │  Monitor │  │          │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   Rate   │→ │  Cache   │→ │ Circuit  │→ │ Provider │   │
│  │ Limiter  │  │  Lookup  │  │ Breaker  │  │  Adapter │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Components

### Core Services

| Service | Description |
|---------|-------------|
| **ModelRegistry** | Catalog of available models with capabilities, costs, and limits |
| **LLMRouter** | Intelligent model selection based on requirements and constraints |
| **SemanticCache** | Embedding-based cache for response deduplication |
| **RateLimiter** | Token bucket rate limiting with Redis backend |
| **CircuitBreaker** | Provider health monitoring and automatic failover |
| **RequestQueue** | Priority queue for request buffering during load spikes |
| **MetricsManager** | Prometheus metrics collection and exposure |
| **L01Bridge** | Integration with L01 Data Layer for usage tracking |

### Provider Adapters

| Adapter | Models | Capabilities |
|---------|--------|--------------|
| **AnthropicAdapter** | claude-opus-4-5, claude-3-5-sonnet, claude-3-opus, claude-3-haiku | text, vision, streaming, tool_use |
| **OpenAIAdapter** | gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo | text, vision, streaming, function_calling |
| **OllamaAdapter** | llama3, mistral, codellama, any local model | text, streaming |
| **ClaudeCodeAdapter** | Claude via local Claude Code CLI | text, streaming, tool_use |
| **MockAdapter** | mock | text, streaming (for testing) |

## Prometheus Metrics

All metrics are prefixed with `l04_`:

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `l04_inference_requests_total` | Counter | provider, model, status | Total inference requests |
| `l04_inference_latency_seconds` | Histogram | provider, model | Request latency distribution |
| `l04_cache_hits_total` | Counter | - | Cache hit count |
| `l04_cache_misses_total` | Counter | - | Cache miss count |
| `l04_rate_limit_rejections_total` | Counter | agent_did | Rate limit rejections |
| `l04_circuit_breaker_state` | Gauge | provider | Circuit state (0=closed, 1=half_open, 2=open) |
| `l04_active_requests` | Gauge | provider | Currently active requests |
| `l04_token_usage_total` | Counter | direction, model | Token consumption |
| `l04_gateway` | Info | version, layer | Gateway metadata |

## Usage Example

```python
from L04_model_gateway.services import ModelGateway
from L04_model_gateway.models import InferenceRequest, Message, MessageRole

# Initialize gateway (uses default providers)
gateway = ModelGateway()

# Create a request
request = InferenceRequest.create(
    agent_did="did:key:agent1",
    messages=[
        Message(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
        Message(role=MessageRole.USER, content="Hello, world!")
    ],
    model_id="claude-3-5-sonnet-20241022",  # Optional: explicit model
    enable_cache=True,
    max_tokens=100
)

# Execute inference
response = await gateway.execute(request)

print(f"Response: {response.content}")
print(f"Tokens: {response.token_usage.total_tokens}")
print(f"Latency: {response.latency_ms}ms")
print(f"Cached: {response.cached}")

# Streaming inference
async for chunk in gateway.stream(request):
    print(chunk.content_delta, end="", flush=True)
    if chunk.is_final:
        print(f"\nTotal tokens: {chunk.token_usage.total_tokens}")

# Health check
health = await gateway.health_check()
print(f"Gateway status: {health['gateway']}")

# Cleanup
await gateway.close()
```

## Error Codes

L04 uses error codes in the range E4000-E4999:

| Range | Category | Common Codes |
|-------|----------|--------------|
| E4000-E4099 | Configuration | E4001: Model not found, E4002: Provider not configured |
| E4100-E4199 | Routing | E4100: No suitable model, E4102: All models unavailable |
| E4200-E4299 | Provider | E4200: Provider error, E4202: Timeout, E4203: Auth failed |
| E4300-E4399 | Cache | E4300: Cache error, E4301: Embedding failed |
| E4400-E4499 | Rate Limit | E4401: Rate limit exceeded, E4402: Quota exhausted |
| E4500-E4599 | Validation | E4500: Invalid request, E4501: Invalid messages |
| E4600-E4699 | Response | E4600: Parse error, E4604: Streaming error |
| E4700-E4799 | Circuit Breaker | E4701: Circuit open, E4702: Recovery failed |

## Configuration

### Environment Variables

```bash
# Provider API Keys
ANTHROPIC_API_KEY=sk-ant-...        # Anthropic Claude API
OPENAI_API_KEY=sk-...               # OpenAI API

# Local Providers
OLLAMA_URL=http://localhost:11434   # Ollama server URL
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_EMBEDDING_DIMENSIONS=768

# Caching
REDIS_URL=redis://localhost:6379/0  # Redis for rate limiting & cache
CACHE_ENABLED=true                  # Enable semantic caching
CACHE_TTL=3600                      # Cache TTL in seconds
CACHE_SIMILARITY_THRESHOLD=0.85     # Embedding similarity threshold

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=60   # Default rate limit
RATE_LIMIT_TOKENS_PER_MINUTE=100000 # Token rate limit

# Circuit Breaker
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5  # Failures before opening
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60  # Seconds before retry

# L01 Integration
L01_BASE_URL=http://localhost:8001  # L01 Data Layer URL
L01_API_KEY=dev_key_local_ONLY      # L01 authentication
```

### Provider-Specific Configuration

```python
from L04_model_gateway.providers import AnthropicAdapter, OpenAIAdapter, OllamaAdapter

# Anthropic with custom settings
anthropic = AnthropicAdapter(
    api_key="sk-ant-...",
    base_url="https://api.anthropic.com",  # Default
    timeout=60.0
)

# OpenAI with custom settings
openai = OpenAIAdapter(
    api_key="sk-...",
    base_url="https://api.openai.com",  # Default
    timeout=60.0
)

# Ollama for local models
ollama = OllamaAdapter(
    base_url="http://localhost:11434",
    timeout=120.0  # Longer timeout for local inference
)

# Custom gateway with specific providers
gateway = ModelGateway(
    providers={
        "anthropic": anthropic,
        "openai": openai,
        "ollama": ollama,
    }
)
```

## Directory Structure

```
L04_model_gateway/
├── __init__.py
├── README.md
├── models/                    # Data models and error codes
│   ├── __init__.py
│   ├── error_codes.py         # L04 error code definitions
│   ├── inference_request.py   # Request models
│   ├── inference_response.py  # Response models
│   ├── model_config.py        # Model configuration
│   ├── provider_config.py     # Provider configuration
│   └── routing_config.py      # Routing configuration
├── services/                  # Core services
│   ├── __init__.py
│   ├── model_registry.py      # Model catalog
│   ├── llm_router.py          # Intelligent routing
│   ├── semantic_cache.py      # Response caching
│   ├── rate_limiter.py        # Rate limiting
│   ├── circuit_breaker.py     # Failover management
│   ├── request_queue.py       # Request buffering
│   ├── model_gateway.py       # Main gateway service
│   ├── metrics.py             # Prometheus metrics
│   └── l01_bridge.py          # L01 integration
├── providers/                 # Provider adapters
│   ├── __init__.py
│   ├── base.py                # Base adapter protocol
│   ├── anthropic_adapter.py   # Anthropic Claude
│   ├── openai_adapter.py      # OpenAI GPT
│   ├── ollama_adapter.py      # Local Ollama
│   ├── claude_code_adapter.py # Claude Code CLI
│   ├── mock_adapter.py        # Testing mock
│   └── token_counter.py       # Token counting utilities
└── tests/                     # Test suite
    ├── __init__.py
    ├── conftest.py            # Shared fixtures
    ├── fixtures/              # Test fixtures
    │   ├── api_responses.py   # Mock API responses
    │   └── mock_clients.py    # Mock HTTP clients
    ├── integration/           # Integration tests
    │   ├── conftest.py
    │   └── test_e2e_inference.py
    ├── test_anthropic_adapter.py
    ├── test_openai_adapter.py
    ├── test_token_counter.py
    ├── test_l01_bridge.py
    ├── test_metrics.py
    ├── test_models.py
    ├── test_registry.py
    ├── test_router.py
    └── test_services.py
```

## Testing

```bash
# Run all L04 tests
pytest src/L04_model_gateway/tests/ -v

# Run with coverage
pytest src/L04_model_gateway/tests/ --cov=src/L04_model_gateway --cov-report=html

# Run specific test categories
pytest src/L04_model_gateway/tests/ -m "unit"        # Unit tests only
pytest src/L04_model_gateway/tests/ -m "integration" # Integration tests
pytest src/L04_model_gateway/tests/ -m "e2e"         # End-to-end tests

# Run specific adapter tests
pytest src/L04_model_gateway/tests/test_anthropic_adapter.py -v
pytest src/L04_model_gateway/tests/test_openai_adapter.py -v
```

## Integration

### With L01 Data Layer

Usage events are automatically recorded via L01Bridge:

```python
from L04_model_gateway.services import ModelGateway, L01Bridge

# Gateway with L01 integration
bridge = L01Bridge(
    base_url="http://localhost:8001",
    api_key="dev_key_local_ONLY"
)
gateway = ModelGateway(l01_bridge=bridge)

# Inference automatically records usage in L01
response = await gateway.execute(request)
# Event recorded: inference_completed with tokens, latency, cost
```

### With L02 Runtime Layer

```python
from L02_runtime import AgentRuntime
from L04_model_gateway import ModelGateway

runtime = AgentRuntime()
gateway = ModelGateway()

# Runtime uses gateway for inference
response = await gateway.execute(request)
```

### With L05 Planning Layer

```python
from L05_planning.integration.l04_bridge import L04Bridge

# L05 uses bridge pattern for L04 access
bridge = L04Bridge(base_url="http://localhost:8004")
response = await bridge.generate(
    prompt="Plan the following task...",
    model="claude-3-5-sonnet-20241022"
)
```

## License

Copyright 2026 Story Portal Platform

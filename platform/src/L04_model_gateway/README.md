# L04 Model Gateway Layer

The Model Gateway Layer provides intelligent routing and execution of LLM inference requests across multiple providers with caching, rate limiting, and failover capabilities.

## Overview

The L04 Model Gateway Layer sits between the agent runtime (L02) and external LLM providers, providing:

- **Unified Interface**: Single API for multiple LLM providers (Anthropic, OpenAI, Azure, Google, local models)
- **Intelligent Routing**: Capability-based model selection with cost and latency optimization
- **Semantic Caching**: Embedding-based caching to reduce costs and improve latency
- **Rate Limiting**: Token bucket rate limiting per agent and provider
- **Circuit Breaker**: Automatic failover when providers are unhealthy
- **Request Queue**: Priority queue for request buffering during load spikes

## Architecture

```
┌─────────────────────────────────────────────────┐
│           Model Gateway Layer (L04)             │
├─────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ Registry │  │  Router  │  │  Health  │     │
│  │          │  │          │  │  Monitor │     │
│  └──────────┘  └──────────┘  └──────────┘     │
├─────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │   Rate   │→ │  Cache   │→ │ Provider │     │
│  │ Limiter  │  │  Lookup  │  │  Adapter │     │
│  └──────────┘  └──────────┘  └──────────┘     │
└─────────────────────────────────────────────────┘
```

## Components

### Core Services

- **Model Registry**: Catalog of available models with capabilities, costs, and limits
- **LLM Router**: Intelligent model selection based on requirements and constraints
- **Semantic Cache**: Embedding-based cache using Redis and SQLite
- **Rate Limiter**: Token bucket rate limiting with Redis backend
- **Circuit Breaker**: Provider health monitoring and failover
- **Request Queue**: Priority queue for request buffering

### Provider Adapters

- **Anthropic Adapter**: Claude models via Anthropic API
- **OpenAI Adapter**: GPT models via OpenAI API
- **Azure Adapter**: Azure OpenAI Service
- **Google Adapter**: Vertex AI models
- **Ollama Adapter**: Local models via Ollama

### Data Models

- **InferenceRequest**: Logical prompt with requirements and constraints
- **InferenceResponse**: Normalized response with token usage and cost
- **ModelConfig**: Model definition with capabilities and pricing
- **ProviderConfig**: Provider connection and behavior configuration
- **RoutingDecision**: Result of routing logic with fallback options

## Error Codes

L04 uses error codes in the range E4000-E4999:

| Range | Category |
|-------|----------|
| E4000-E4099 | Configuration errors |
| E4100-E4199 | Routing errors |
| E4200-E4299 | Provider errors |
| E4300-E4399 | Cache errors |
| E4400-E4499 | Rate limit errors |
| E4500-E4599 | Request validation errors |
| E4600-E4699 | Response processing errors |
| E4700-E4799 | Circuit breaker errors |

## Usage Example

```python
from L04_model_gateway import ModelRegistry
from L04_model_gateway.models import InferenceRequest, Message, MessageRole

# Initialize registry
registry = ModelRegistry()
registry.load_default_models()

# Create a request
messages = [Message(role=MessageRole.USER, content="Hello, world!")]
request = InferenceRequest.create(
    agent_did="did:key:agent1",
    messages=messages,
    capabilities=["text"],
    max_tokens=100
)

# Route and execute (gateway integration coming in later phases)
```

## Configuration

### Local Development

For local development with Ollama:

```python
# Default configuration
OLLAMA_BASE_URL = "http://localhost:11434"
REDIS_URL = "redis://localhost:6379"
CACHE_TTL = 3600  # seconds
CACHE_SIMILARITY_THRESHOLD = 0.85
```

### Production

Production configuration uses environment variables:

- `ANTHROPIC_API_KEY`: Anthropic API key
- `OPENAI_API_KEY`: OpenAI API key
- `AZURE_OPENAI_KEY`: Azure OpenAI key
- `REDIS_URL`: Redis connection URL
- `CACHE_ENABLED`: Enable semantic caching (default: true)

## Development

### Directory Structure

```
L04_model_gateway/
├── __init__.py
├── README.md
├── PROGRESS.md
├── models/              # Data models and error codes
│   ├── __init__.py
│   ├── error_codes.py
│   ├── inference_request.py
│   ├── inference_response.py
│   ├── model_config.py
│   ├── provider_config.py
│   └── routing_config.py
├── services/            # Core services
│   ├── __init__.py
│   ├── model_registry.py
│   ├── llm_router.py
│   ├── semantic_cache.py
│   ├── rate_limiter.py
│   ├── request_queue.py
│   ├── circuit_breaker.py
│   ├── provider_health.py
│   └── model_gateway.py
├── providers/           # Provider adapters
│   ├── __init__.py
│   ├── base.py
│   ├── anthropic_adapter.py
│   ├── openai_adapter.py
│   ├── ollama_adapter.py
│   └── mock_adapter.py
└── tests/              # Test suite
    ├── __init__.py
    ├── conftest.py
    └── test_*.py
```

### Testing

```bash
# Run tests
cd /Volumes/Extreme SSD/projects/story-portal-app/platform
python3 -m pytest src/L04_model_gateway/tests/

# Type checking
python3 -m mypy src/L04_model_gateway/

# Syntax validation
python3 -m py_compile $(find src/L04_model_gateway -name "*.py")
```

## Integration

### With L02 Runtime Layer

The L02 Runtime Layer calls L04 for model inference:

```python
from L02_runtime import AgentRuntime
from L04_model_gateway import ModelGateway

runtime = AgentRuntime()
gateway = ModelGateway()

# Runtime uses gateway for inference
response = await gateway.execute(request)
```

### With L03 Tool Execution Layer

Tool execution results can be passed back through the gateway:

```python
from L03_tool_execution import ToolExecutor
from L04_model_gateway import ModelGateway

executor = ToolExecutor()
gateway = ModelGateway()

# Execute tool, feed result back to model
tool_result = await executor.execute(tool_call)
response = await gateway.execute_with_tools(request, [tool_result])
```

## Status

See [PROGRESS.md](PROGRESS.md) for implementation status.

## License

Copyright 2026 Story Portal Platform

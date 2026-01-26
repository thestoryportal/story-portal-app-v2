# Service 36/44: ModelRegistry

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L04 (Model Gateway Layer) |
| **Module** | `L04_model_gateway.services.model_registry` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | None (in-memory state) |
| **Category** | AI/ML / Model Configuration |

## Role in Development Environment

The **ModelRegistry** maintains an authoritative catalog of available models with their capabilities, costs, and operational limits. It provides:
- Central model registration and configuration
- Capability-based model discovery
- Provider-based model grouping
- Quality scores for model selection
- Status management (active, deprecated, etc.)
- Default models for local development

This is **the model catalog for the platform** - when the LLMRouter needs to select a model or the ModelGateway needs model configuration, ModelRegistry provides the authoritative source.

## Data Model

### ModelConfig (key fields)
- `model_id: str` - Unique model identifier
- `provider: str` - Provider name (ollama, openai, anthropic)
- `display_name: str` - Human-readable name
- `capabilities: ModelCapabilities` - What the model supports
- `context_window: int` - Maximum context length
- `max_output_tokens: int` - Maximum output tokens
- `cost_per_1m_input_tokens: float` - Input cost
- `cost_per_1m_output_tokens: float` - Output cost
- `rate_limit_rpm: int` - Requests per minute limit
- `rate_limit_tpm: int` - Tokens per minute limit
- `latency_p50_ms: int` - Median latency
- `latency_p99_ms: int` - 99th percentile latency
- `status: ModelStatus` - Current status
- `quality_scores: QualityScores` - Quality metrics

### ModelCapabilities
- `supports_streaming: bool` - Stream responses
- `supports_vision: bool` - Image understanding
- `supports_tool_use: bool` - Function calling
- `supports_json_mode: bool` - JSON output mode

### QualityScores
- `reasoning: float` - Reasoning quality (0-1)
- `coding: float` - Code generation quality (0-1)
- `creative: float` - Creative writing quality (0-1)
- `summarization: float` - Summary quality (0-1)

### ModelStatus Enum
- `ACTIVE` - Available for use
- `DEPRECATED` - Being phased out
- `DISABLED` - Temporarily disabled
- `MAINTENANCE` - Under maintenance

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| (none) | - | In-memory registry, no config |

## API Methods

| Method | Description |
|--------|-------------|
| `register_model(model)` | Register a model |
| `get_model(model_id)` | Get model by ID |
| `get_model_or_raise(model_id)` | Get model or raise error |
| `list_models(provider, status)` | List models with filters |
| `get_models_by_capability(capability)` | Find by capability |
| `get_models_by_capabilities(capabilities)` | Find by multiple capabilities |
| `get_models_by_provider(provider)` | Find by provider |
| `get_available_models()` | Get all active models |
| `get_providers()` | List all providers |
| `get_capabilities()` | List all capabilities |
| `update_model_status(model_id, status)` | Update model status |
| `load_default_models()` | Load development models |
| `is_initialized()` | Check if initialized |
| `get_stats()` | Get registry statistics |

## Use Cases in Your Workflow

### 1. Initialize Model Registry
```python
from L04_model_gateway.services.model_registry import ModelRegistry

# Create registry
registry = ModelRegistry()

# Load default models for development
registry.load_default_models()

print(f"Loaded {registry.get_stats()['total_models']} models")
```

### 2. Register Custom Model
```python
from L04_model_gateway.models import (
    ModelConfig,
    ModelCapabilities,
    QualityScores,
    ModelStatus
)

# Define model configuration
claude_opus = ModelConfig(
    model_id="claude-3-opus",
    provider="anthropic",
    display_name="Claude 3 Opus",
    capabilities=ModelCapabilities(
        supports_streaming=True,
        supports_vision=True,
        supports_tool_use=True,
        supports_json_mode=True
    ),
    context_window=200000,
    max_output_tokens=4096,
    cost_per_1m_input_tokens=15.0,
    cost_per_1m_output_tokens=75.0,
    rate_limit_rpm=60,
    rate_limit_tpm=100000,
    latency_p50_ms=2000,
    latency_p99_ms=8000,
    status=ModelStatus.ACTIVE,
    quality_scores=QualityScores(
        reasoning=0.95,
        coding=0.92,
        creative=0.90,
        summarization=0.93
    )
)

# Register
registry.register_model(claude_opus)
```

### 3. Get Model by ID
```python
# Get specific model
model = registry.get_model("llama3.1:8b")

if model:
    print(f"Model: {model.display_name}")
    print(f"Provider: {model.provider}")
    print(f"Context: {model.context_window} tokens")
    print(f"Status: {model.status.value}")
else:
    print("Model not found")

# Or raise error if not found
model = registry.get_model_or_raise("llama3.1:8b")
```

### 4. Find Models by Capability
```python
# Find all models with vision support
vision_models = registry.get_models_by_capability("vision")

for model in vision_models:
    print(f"- {model.model_id} ({model.provider})")

# Find models with multiple capabilities
code_models = registry.get_models_by_capabilities(["code", "tool_use"])

for model in code_models:
    print(f"- {model.model_id} (coding: {model.quality_scores.coding})")
```

### 5. Find Models by Provider
```python
# Get all Ollama models
ollama_models = registry.get_models_by_provider("ollama")

print(f"Ollama models: {len(ollama_models)}")
for model in ollama_models:
    print(f"  - {model.model_id}")
```

### 6. List Available Models
```python
# Get all active models
available = registry.get_available_models()

print(f"{len(available)} available models:")
for model in available:
    print(f"  - {model.model_id} ({model.status.value})")
```

### 7. List with Filters
```python
from L04_model_gateway.models import ModelStatus

# List only active Anthropic models
models = await registry.list_models(
    provider="anthropic",
    status=ModelStatus.ACTIVE
)

for model in models:
    print(f"- {model.display_name}")
```

### 8. Update Model Status
```python
from L04_model_gateway.models import ModelStatus

# Deprecate a model
registry.update_model_status("old-model-v1", ModelStatus.DEPRECATED)

# Disable for maintenance
registry.update_model_status("llama3.1:8b", ModelStatus.MAINTENANCE)

# Re-enable
registry.update_model_status("llama3.1:8b", ModelStatus.ACTIVE)
```

### 9. Get Registry Statistics
```python
stats = registry.get_stats()

print(f"Total models: {stats['total_models']}")
print(f"Active models: {stats['active_models']}")
print(f"Providers: {stats['providers']}")
print(f"Capabilities: {stats['capabilities']}")
```

### 10. Integration with LLMRouter
```python
from L04_model_gateway.services.llm_router import LLMRouter

# Create registry and load models
registry = ModelRegistry()
registry.load_default_models()

# Create router with registry
router = LLMRouter(registry=registry)

# Router uses registry to find capable models
decision = router.route(request)
```

## Service Interactions

```
+------------------+
|  ModelRegistry   | <--- L04 Model Gateway Layer
|      (L04)       |
+--------+---------+
         |
   Provides to:
         |
+--------+--------+--------+
|                 |        |
v                 v        v
LLMRouter      Gateway   Health
(Selection)    (Config)  (Status)
```

**Integration Points:**
- **LLMRouter (L04)**: Uses registry for model selection
- **ModelGateway (L04)**: Gets model configuration
- **Health Check (L04)**: Reports model availability

## Default Models

Models loaded by `load_default_models()`:

| Model ID | Provider | Context | Quality |
|----------|----------|---------|---------|
| llama3.1:8b | ollama | 128K | 0.75 reasoning |
| llama3.2:3b | ollama | 128K | 0.65 reasoning |
| llava-llama3:latest | ollama | 8K | Vision support |

## Indexing

### Capability Index
```
capability -> set of model_ids

"streaming" -> {llama3.1:8b, llama3.2:3b, llava-llama3}
"vision" -> {llava-llama3}
"json_mode" -> {llama3.1:8b, llama3.2:3b}
```

### Provider Index
```
provider -> set of model_ids

"ollama" -> {llama3.1:8b, llama3.2:3b, llava-llama3}
"anthropic" -> {claude-3-opus, claude-3-sonnet}
"openai" -> {gpt-4, gpt-3.5-turbo}
```

## Error Codes

| Code | Description | Retryable |
|------|-------------|-----------|
| E4001 | Model not found | No |
| E4003 | Invalid model config | No |

## Execution Examples

```python
# Complete model registry workflow
from L04_model_gateway.services.model_registry import ModelRegistry
from L04_model_gateway.models import (
    ModelConfig,
    ModelCapabilities,
    QualityScores,
    ModelStatus
)

# Initialize
registry = ModelRegistry()

# 1. Load default models
registry.load_default_models()
print(f"Default models loaded: {registry.get_stats()['total_models']}")

# 2. Register custom model
custom_model = ModelConfig(
    model_id="gpt-4-turbo",
    provider="openai",
    display_name="GPT-4 Turbo",
    capabilities=ModelCapabilities(
        supports_streaming=True,
        supports_vision=True,
        supports_tool_use=True,
        supports_json_mode=True
    ),
    context_window=128000,
    max_output_tokens=4096,
    cost_per_1m_input_tokens=10.0,
    cost_per_1m_output_tokens=30.0,
    rate_limit_rpm=500,
    rate_limit_tpm=90000,
    latency_p50_ms=1000,
    latency_p99_ms=5000,
    status=ModelStatus.ACTIVE,
    quality_scores=QualityScores(
        reasoning=0.90,
        coding=0.88,
        creative=0.85,
        summarization=0.87
    )
)
registry.register_model(custom_model)

# 3. Query by capability
print("\n=== Vision Models ===")
for model in registry.get_models_by_capability("vision"):
    print(f"  {model.model_id} ({model.provider})")

# 4. Query by multiple capabilities
print("\n=== Streaming + Tool Use ===")
for model in registry.get_models_by_capabilities(["streaming", "tool_use"]):
    print(f"  {model.model_id}")

# 5. Query by provider
print("\n=== OpenAI Models ===")
for model in registry.get_models_by_provider("openai"):
    print(f"  {model.display_name}")

# 6. Get specific model
model = registry.get_model("llama3.1:8b")
if model:
    print(f"\n=== {model.display_name} ===")
    print(f"  Context: {model.context_window:,} tokens")
    print(f"  Latency: {model.latency_p50_ms}ms (p50)")
    print(f"  Quality: reasoning={model.quality_scores.reasoning}")

# 7. Update status
registry.update_model_status("llama3.2:3b", ModelStatus.DEPRECATED)
print(f"\nllama3.2:3b status: {registry.get_model('llama3.2:3b').status.value}")

# 8. Get available models
available = registry.get_available_models()
print(f"\n{len(available)} available models")

# 9. Get statistics
stats = registry.get_stats()
print(f"\n=== Registry Stats ===")
print(f"  Total: {stats['total_models']}")
print(f"  Active: {stats['active_models']}")
print(f"  Providers: {stats['providers']}")
print(f"  Capabilities: {stats['capabilities']}")
```

## Implementation Status

| Component | Status |
|-----------|--------|
| register_model() | Complete |
| get_model() | Complete |
| get_model_or_raise() | Complete |
| list_models() | Complete |
| get_models_by_capability() | Complete |
| get_models_by_capabilities() | Complete |
| get_models_by_provider() | Complete |
| get_available_models() | Complete |
| get_providers() | Complete |
| get_capabilities() | Complete |
| update_model_status() | Complete |
| load_default_models() | Complete |
| get_stats() | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Persistent Storage | High | Store in database |
| Model Hot Reload | Medium | Update without restart |
| Model Versioning | Medium | Track model versions |
| Cost Tracking | Medium | Real-time cost updates |
| External Config | Low | Load from YAML/JSON |
| Prometheus Metrics | Low | Export registry metrics |

## Strengths

- **Indexed lookups** - Fast capability/provider queries
- **Rich metadata** - Quality scores, latency, costs
- **Default models** - Ready for local development
- **Status management** - Active, deprecated, etc.
- **Validation** - Config validation on register
- **In-memory** - Fast, no external dependencies

## Weaknesses

- **In-memory only** - Lost on restart
- **No persistence** - Must reload on start
- **No versioning** - Can't track model updates
- **No hot reload** - Must restart to add models
- **Single instance** - Not distributed
- **Static costs** - No real-time cost updates

## Best Practices

### Model Registration
Include complete metadata:
```python
ModelConfig(
    model_id="unique-id",
    provider="provider-name",
    display_name="Human Readable Name",
    capabilities=ModelCapabilities(...),  # All capabilities
    context_window=128000,
    max_output_tokens=4096,
    cost_per_1m_input_tokens=10.0,        # Actual cost
    cost_per_1m_output_tokens=30.0,
    rate_limit_rpm=500,                    # Provider limits
    rate_limit_tpm=90000,
    latency_p50_ms=1000,                   # Measured latency
    latency_p99_ms=5000,
    status=ModelStatus.ACTIVE,
    quality_scores=QualityScores(          # Benchmarked scores
        reasoning=0.90,
        coding=0.88,
        creative=0.85,
        summarization=0.87
    )
)
```

### Status Updates
Use status appropriately:
```python
# Before maintenance
registry.update_model_status("model-id", ModelStatus.MAINTENANCE)

# After maintenance
registry.update_model_status("model-id", ModelStatus.ACTIVE)

# Phasing out
registry.update_model_status("old-model", ModelStatus.DEPRECATED)

# Permanently unavailable
registry.update_model_status("removed-model", ModelStatus.DISABLED)
```

### Capability Queries
Query efficiently:
```python
# Single capability - fast
models = registry.get_models_by_capability("vision")

# Multiple capabilities - intersection
models = registry.get_models_by_capabilities(["vision", "tool_use"])

# Avoid: listing then filtering
# models = [m for m in registry.list_models() if m.has_capability("vision")]
```

## Source Files

- Service: `platform/src/L04_model_gateway/services/model_registry.py`
- Models: `platform/src/L04_model_gateway/models/model_config.py`
- Error Codes: `platform/src/L04_model_gateway/models/__init__.py`
- Spec: L04 Model Gateway Layer specification

## Related Services

- LLMRouter (L04) - Uses for model selection
- ModelGateway (L04) - Uses for configuration
- RateLimiter (L04) - Uses rate limits from config
- Provider Adapters - Use model config

---
*Generated: 2026-01-24 | Platform Services Documentation*

Implement L04 Model Gateway Layer: Autonomous end-to-end sprint.

## CRITICAL ENVIRONMENT CONSTRAINTS

READ THESE FIRST - DO NOT VIOLATE:

1. DO NOT create docker-compose files - infrastructure ALREADY RUNNING
2. DO NOT create virtual environments (venv) - use system Python
3. DO NOT run docker-compose up - services ALREADY RUNNING
4. ALWAYS use: pip install <package> --break-system-packages
5. CORRECT directory: /Volumes/Extreme SSD/projects/story-portal-app/platform/src/L04_model_gateway/

## Running Infrastructure (DO NOT RECREATE)

| Service | Host | Port | Container/Process |
|---------|------|------|-------------------|
| PostgreSQL | localhost | 5432 | agentic-postgres |
| Redis | localhost | 6379 | agentic-redis |
| Ollama | localhost | 11434 | native process |

Verify with: docker ps | grep agentic && curl -s localhost:11434/api/tags | head

## Specification

Location: /Volumes/Extreme SSD/projects/story-portal-app/platform/specs/model-gateway-layer-specification-v1.2-final-ASCII.md

Read specification Sections 3 (Architecture) and 11 (Implementation Guide) first.

## Output Location

/Volumes/Extreme SSD/projects/story-portal-app/platform/src/L04_model_gateway/

## Reference: L02/L03 Pattern

Follow implementation patterns from:
- /Volumes/Extreme SSD/projects/story-portal-app/platform/src/L02_runtime/
- /Volumes/Extreme SSD/projects/story-portal-app/platform/src/L03_tool_execution/

## Directory Structure

Create these directories and files:

Root: platform/src/L04_model_gateway/
  - __init__.py
  - PROGRESS.md
  - README.md

Subdirectory: platform/src/L04_model_gateway/models/
  - __init__.py
  - inference_request.py (InferenceRequest, LogicalPrompt)
  - inference_response.py (InferenceResponse, TokenUsage)
  - model_config.py (ModelConfig, ModelCapabilities)
  - provider_config.py (ProviderConfig, ProviderHealth)
  - routing_config.py (RoutingStrategy, RoutingDecision)
  - error_codes.py (E4000-E4999)

Subdirectory: platform/src/L04_model_gateway/services/
  - __init__.py
  - model_registry.py (Model catalog with capabilities)
  - llm_router.py (Capability-based routing)
  - semantic_cache.py (Embedding similarity cache)
  - rate_limiter.py (Token bucket rate limiting)
  - request_queue.py (Priority queue with deadlines)
  - circuit_breaker.py (Failover management)
  - provider_health.py (Health monitoring)
  - model_gateway.py (Main gateway service)

Subdirectory: platform/src/L04_model_gateway/providers/
  - __init__.py
  - base.py (ProviderAdapter protocol)
  - anthropic_adapter.py (Anthropic Claude API)
  - openai_adapter.py (OpenAI API)
  - ollama_adapter.py (Local Ollama models)
  - mock_adapter.py (Testing adapter)

Subdirectory: platform/src/L04_model_gateway/tests/
  - __init__.py
  - conftest.py
  - test_models.py
  - test_registry.py
  - test_router.py
  - test_cache.py
  - test_providers.py

## Implementation Phases

Execute in order per spec Section 11:

### Phase 1: Foundation (Models and Registry)

Create data models for InferenceRequest, InferenceResponse, ModelConfig.
Define error codes E4000-E4999.
Build Model Registry with register, list, get models by capability.
Create provider configuration schema.

Key dataclasses from spec Section 4:

InferenceRequest fields:
  - request_id: str
  - agent_did: str
  - logical_prompt: LogicalPrompt
  - requirements: ModelRequirements
  - constraints: RequestConstraints
  - metadata: dict

InferenceResponse fields:
  - request_id: str
  - model_id: str
  - provider: str
  - content: str
  - token_usage: TokenUsage
  - latency_ms: int
  - cached: bool
  - metadata: dict

ModelRequirements fields:
  - capabilities: list[str] (vision, tool_use, long_context)
  - min_context_length: int (default 4096)
  - max_output_tokens: int (default 4096)

RequestConstraints fields:
  - max_latency_ms: int (default 30000)
  - max_cost_cents: int (default 100)
  - preferred_providers: list[str]

### Phase 2: Provider Adapters

Create base ProviderAdapter protocol with methods:
  - complete(request, model_id) -> InferenceResponse
  - stream(request, model_id) -> AsyncIterator[str]
  - health_check() -> ProviderHealth
  - supports_capability(capability) -> bool

Implement adapters:
  - OllamaAdapter (primary for local dev, fully functional)
  - MockAdapter (for testing, returns canned responses)
  - AnthropicAdapter (stub, needs API key)
  - OpenAIAdapter (stub, needs API key)

### Phase 3: LLM Router

Build capability-based model selection:
  1. Filter models by required capabilities
  2. Filter by context length requirements
  3. Filter by provider health (circuit breaker state)
  4. Sort by cost or latency based on strategy
  5. Return best match with fallback chain

### Phase 4: Semantic Cache

Redis-backed cache with:
  - Embedding generation via Ollama (nomic-embed-text)
  - Similarity matching (cosine similarity >= 0.85)
  - TTL-based expiration (default 3600 seconds)
  - Cache key derivation from request hash

### Phase 5: Rate Limiter and Circuit Breaker

Token bucket rate limiting:
  - Redis-backed distributed state
  - Per-agent and per-provider limits

Circuit breaker with states:
  - CLOSED (normal operation)
  - OPEN (failing, reject requests)
  - HALF_OPEN (testing recovery)
  - Failure threshold: 5 failures
  - Cooldown: 60 seconds

### Phase 6: Request Queue

Priority queue for request buffering:
  - Deadline-aware processing
  - Priority levels (high, normal, low)
  - Batch processing support

### Phase 7: Gateway Service

Main ModelGateway class combining all components:
  - Check rate limit
  - Check cache
  - Route to provider
  - Execute with circuit breaker
  - Cache response
  - Return result

### Phase 8: Observability and Hardening

Add metrics, logging, error handling:
  - Request count, latency, cache hit rate
  - Structured logging
  - Error handling with E4xxx codes
  - Input validation
  - Comprehensive docstrings

## Error Code Range

L04 uses E4000-E4999:

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

## Local Development Configuration

Ollama models available (check with ollama list).
Default provider for local dev: Ollama at localhost:11434.

Default config values:
  - Cache Redis URL: redis://localhost:6379
  - Cache embedding model: nomic-embed-text
  - Cache TTL: 3600 seconds
  - Cache similarity threshold: 0.85
  - Rate limit default RPM: 60
  - Rate limit default TPM: 100000

## Test Configuration

Create tests/conftest.py with:
  - Event loop fixture
  - Cleanup timeout fixture (2 second max)
  - Mock Ollama response fixture

## Validation After Each Phase

Run after each phase:
  cd /Volumes/Extreme SSD/projects/story-portal-app/platform
  python3 -m py_compile $(find src/L04_model_gateway -name "*.py")
  python3 -c "from src.L04_model_gateway import *; print('OK')"

## Progress Logging

After each phase append to PROGRESS.md:
  Phase [N] complete: [components] - [timestamp]

## Final Validation

After all phases:
  1. Syntax check all files
  2. Import check main gateway
  3. Run test suite with 30 second timeout
  4. Test Ollama adapter health check

## Completion Criteria

Sprint complete when:
  - All 8 phases implemented
  - All files pass syntax validation
  - All imports resolve
  - Tests exist for each component
  - Tests pass with no hangs
  - Ollama adapter works with local models
  - PROGRESS.md shows all phases complete

## Error Handling

If blocked:
  1. Log blocker to PROGRESS.md
  2. Stub the problematic component with TODO
  3. Continue to next phase
  4. Do not stop the sprint

## Final Steps

1. Create completion summary in PROGRESS.md
2. Stage files: git add platform/src/L04_model_gateway/
3. Do NOT commit - await human review

## REMINDERS

- NO docker-compose
- NO venv
- Use --break-system-packages for pip
- Infrastructure ALREADY RUNNING
- Use Ollama as primary provider for local dev
- Follow L02/L03 patterns

## Begin

Read the specification. Execute all phases. Log progress. Complete end-to-end.
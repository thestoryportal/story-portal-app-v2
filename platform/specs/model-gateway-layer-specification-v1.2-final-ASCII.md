# Model Gateway Layer Specification

**Layer ID:** L04  
**Version:** 1.2.0  
**Status:** Final  
**Date:** January 04, 2026  
**Depends On:** L00 Infrastructure, L01 Data Layer  
**Depended By:** L02 Agent Runtime, L05 Planning, L06 Evaluation, L07 Learning

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Scope Definition](#2-scope-definition)
3. [Architecture](#3-architecture)
4. [Interfaces](#4-interfaces)
5. [Data Model](#5-data-model)
6. [Integration with Data Layer](#6-integration-with-data-layer)
7. [Reliability and Scalability](#7-reliability-and-scalability)
8. [Security](#8-security)
9. [Observability](#9-observability)
10. [Configuration](#10-configuration)
11. [Implementation Guide](#11-implementation-guide)
12. [Testing Strategy](#12-testing-strategy)
13. [Migration and Versioning](#13-migration-and-versioning)
14. [Open Questions](#14-open-questions)
15. [References](#15-references)
16. [Appendices](#16-appendices)

---

## 1. Executive Summary

### 1.1 Purpose

The Model Gateway Layer abstracts LLM provider complexity from consuming layers, routing inference requests across multiple providers (Anthropic, OpenAI, Azure OpenAI, Google Vertex AI, local models) based on capability requirements, cost constraints, and availability. This layer serves as the single point of access for all LLM interactions within the Agentic AI Workforce stack, ensuring consistent model access regardless of underlying provider topology.

L04 exists as a distinct layer for three strategic reasons:

1. **Agent Intelligence Enablement** -- All agent reasoning flows through this layer; without L04, agents cannot execute LLM calls
2. **Token Optimization Foundation** -- Centralizes token counting, semantic caching, cost-aware routing, and request optimization
3. **Provider Independence** -- Shields the system from provider-specific APIs, enabling multi-cloud and local model deployments

### 1.2 Key Capabilities

| Capability | Description |
|------------|-------------|
| Provider Abstraction | Normalize request/response formats across Anthropic, OpenAI, Azure, Google, and local model APIs into unified OpenAI-compatible interface |
| Intelligent Routing | Route requests based on capability requirements (vision, tool use, long context), latency SLAs, cost tiers, and provider health |
| Semantic Caching | Cache semantically similar requests using embedding-based similarity matching to reduce API calls by 20-35% |
| Failover Management | Circuit breaker pattern with sequential fallback across providers; automatic recovery testing |
| Usage Quota Enforcement | Track token consumption per agent/project; enforce budget limits and rate caps with distributed Redis counters |
| Request Optimization | Request batching for batch endpoints, provider prompt caching integration, token budget enforcement |
| Response Processing | Normalize responses, handle streaming with token counting, extract structured outputs |

### 1.3 Position in Stack

```
+=====================================================================+
|                        EXTERNAL LLM PROVIDERS                        |
|     Anthropic | OpenAI | Azure OpenAI | Google Vertex | Local        |
+=====================================================================+
                                  ^
                                  | HTTPS/gRPC (Provider APIs)
                                  |
+---------------------------------------------------------------------+
|                                                                     |
|          >>>  MODEL GATEWAY LAYER (L04) -- THIS DOCUMENT  <<<       |
|                                                                     |
|  +---------------+  +---------------+  +---------------+            |
|  | Model Registry|  | LLM Router    |  | Semantic Cache|            |
|  +---------------+  +---------------+  +---------------+            |
|  +---------------+  +---------------+  +---------------+            |
|  | Rate Limiter  |  | Request Queue |  | Provider      |            |
|  |               |  |               |  | Adapters      |            |
|  +---------------+  +---------------+  +---------------+            |
|                                                                     |
+---------------------------------------------------------------------+
                                  ^
                                  | InferenceRequest/Response (BC-3)
                                  |
+=====================================================================+
||                     CONSUMER LAYERS                                ||
||   L02 Runtime | L05 Planning | L06 Evaluation | L07 Learning       ||
+=====================================================================+
                                  ^
                                  | Events, Storage, Config, Identity
                                  |
+=====================================================================+
||                      DATA LAYER (L01)                              ||
||   Event Store | Storage | Configuration | DID Registry             ||
+=====================================================================+
                                  ^
                                  | Secrets, Network, Compute, Observability
                                  |
+=====================================================================+
||                      INFRASTRUCTURE (L00)                          ||
||   Kubernetes | Vault | Prometheus | Cilium | Cert Manager          ||
+=====================================================================+
```

### 1.4 Design Principles

| Principle | Implementation |
|-----------|----------------|
| Provider Agnostic | All consuming layers interact through BC-3 contract; provider details hidden |
| Fail Fast, Recover Gracefully | Circuit breakers prevent cascading failures; automatic fallback routing |
| Cost Aware | Every request tracks cost; budget enforcement prevents runaway spending |
| Observable by Default | All requests/responses emit events; comprehensive metrics for FinOps |
| Secure by Design | Provider keys in Vault; per-agent authorization; audit logging |

### 1.5 Technology Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| API Surface | OpenAI-compatible | Industry standard; broad client compatibility |
| Internal Protocol | gRPC (primary), HTTP (compatibility) | Performance for internal calls; accessibility for debugging |
| Cache Backend | Redis + SQLite | Redis for hot cache; SQLite for persistence and vector search |
| Embedding Model | text-embedding-3-small (OpenAI) | Balance of quality and cost; 1536 dimensions |
| Rate Limit Algorithm | Token bucket with Redis | Handles bursts; distributed state |
| Configuration | L01 Configuration Service | Centralized; hot-reload capable |

---

## 2. Scope Definition

### 2.1 In Scope

| Responsibility | Description |
|----------------|-------------|
| Provider Abstraction | Translate LogicalPrompt (BC-3) into provider-specific API calls; normalize responses |
| Capability-Based Routing | Match request requirements (vision, tools, context length) to model capabilities |
| Cost-Optimized Routing | Select cheapest provider meeting latency SLA when multiple models qualify |
| Failover Management | Circuit breaker (5 failures, 60s cooldown); sequential fallback across providers |
| Semantic Caching | Embedding-based similarity (0.85 threshold); cache invalidation by TTL and category |
| Exact Match Caching | Hash-based cache for identical requests (higher hit rate, lower compute) |
| Rate Limiting | Per-tenant, per-model rate limits using distributed token bucket |
| Token Counting | Accurate counting for metering, including streaming responses |
| Request Queue | Priority queue for load spike buffering; deadline-aware processing |
| Batch Processing | Queue low-priority requests for provider batch APIs (50% cost savings) |
| Provider Health Monitoring | Track latency, error rates, availability per provider endpoint |
| Response Streaming | Proxy streaming responses with incremental token counting |
| Structured Output Extraction | Parse JSON/structured responses per output schema |
| Cost Tracking | Emit cost events per request for FinOps integration |
| Model Registry | Maintain catalog of available models with capabilities, costs, limits |
| Provider Prompt Caching | Leverage Anthropic/OpenAI prompt caching for stable prefixes |

### 2.2 Out of Scope

| Item | Owning Layer | Rationale |
|------|--------------|-----------|
| Agent execution orchestration | L02 Agent Runtime | Runtime executes agents; gateway provides model access only |
| Prompt template versioning | L05 Planning | Planning owns logical prompt construction and templates |
| Provider-agnostic prompt construction | L05 Planning | Per BC-3, Planning constructs LogicalPrompt; Gateway formats |
| Output quality scoring | L06 Evaluation | Evaluation owns quality metrics and assessment |
| Model fine-tuning orchestration | L07 Learning | Learning owns training pipelines and fine-tune jobs |
| GPU/compute scheduling | L00 Infrastructure | Hardware resource management is infrastructure concern |
| Network policies and firewall rules | L00 Infrastructure | L04 declares egress requirements; L00 enforces |
| Content moderation (semantic) | L05 Planning | Prompt-level guardrails owned by Planning; L04 provides gateway-level defense-in-depth only |
| PII redaction | L01 Data Layer | Data classification and handling owned by Data Layer |
| User authentication | L09 API Gateway | External auth handled at API Gateway |

### 2.3 Boundary Decisions

**BD-1: LogicalPrompt Ownership**

L05 Planning constructs the `LogicalPrompt` structure containing system message, conversation history, tools, and output schema. L04 receives this structure and formats it for provider-specific APIs. L04 does NOT modify prompt content beyond formatting.

**BD-2: Prompt Compression Location**

Prompt compression (LLMLingua-style) is optionally performed by L04 when token budget constraints require reduction. L05 may request compression via `routing_hints.allow_compression: true`. Rationale: Compression requires token counting which L04 already performs; keeps compression co-located with gateway logic.

**BD-3: Embedding Model Management**

L04 owns the embedding model used for semantic cache similarity. This model is separate from the LLMs used for inference. Current choice: OpenAI text-embedding-3-small. Alternative: Local embedding model on CPU for cost reduction.

**BD-4: Provider Key Management**

Provider API keys are stored in HashiCorp Vault and accessed via L00's External Secrets Operator. L04 receives keys as Kubernetes secrets mounted into gateway pods. Key rotation is handled by Vault; L04 pods detect rotation via mounted secret updates.

**BD-5: Network Boundary**

L04 runs cluster-internal. External egress to provider APIs routes through L00 network infrastructure with CiliumNetworkPolicy enforcement. L04 declares required FQDNs; L00 provisions egress rules.

---

## 3. Architecture

### 3.1 Component Diagram

```
+-------------------------------------------------------------------------+
|                        MODEL GATEWAY LAYER (L04)                         |
|                                                                          |
|  +-------------------------------------------------------------------+  |
|  |                        CONTROL PLANE                               |  |
|  |  +------------------+  +------------------+  +------------------+  |  |
|  |  | Model Registry   |  | Routing Engine   |  | Health Monitor   |  |  |
|  |  | - Model catalog  |  | - Strategy exec  |  | - Provider health|  |  |
|  |  | - Capabilities   |  | - Cost optimizer |  | - Circuit state  |  |  |
|  |  | - Cost/limits    |  | - Load balancer  |  | - Latency stats  |  |  |
|  |  +------------------+  +------------------+  +------------------+  |  |
|  +-------------------------------------------------------------------+  |
|                                    |                                     |
|                                    v                                     |
|  +-------------------------------------------------------------------+  |
|  |                        REQUEST PIPELINE                            |  |
|  |                                                                    |  |
|  |  +----------+   +----------+   +----------+   +----------+         |  |
|  |  | Request  |-->| Rate     |-->| Cache    |-->| Request  |         |  |
|  |  | Validator|   | Limiter  |   | Lookup   |   | Router   |         |  |
|  |  +----------+   +----------+   +----------+   +----------+         |  |
|  |                                     |              |                |  |
|  |                            cache hit|              | cache miss     |  |
|  |                                     v              v                |  |
|  |                             +--------------+  +----------+          |  |
|  |                             | Cache Store  |  | Provider |          |  |
|  |                             | (Redis+SQLite|  | Adapter  |          |  |
|  |                             +--------------+  +----------+          |  |
|  |                                                    |                |  |
|  +-------------------------------------------------------------------+  |
|                                    |                                     |
|                                    v                                     |
|  +-------------------------------------------------------------------+  |
|  |                        PROVIDER ADAPTERS                           |  |
|  |                                                                    |  |
|  |  +------------+  +------------+  +------------+  +------------+   |  |
|  |  | Anthropic  |  | OpenAI     |  | Azure      |  | Google     |   |  |
|  |  | Adapter    |  | Adapter    |  | Adapter    |  | Adapter    |   |  |
|  |  +------------+  +------------+  +------------+  +------------+   |  |
|  |                                                                    |  |
|  |  +------------+  +------------+                                    |  |
|  |  | Local/vLLM |  | Custom     |                                    |  |
|  |  | Adapter    |  | Adapter    |                                    |  |
|  |  +------------+  +------------+                                    |  |
|  +-------------------------------------------------------------------+  |
|                                    |                                     |
|                                    v                                     |
|  +-------------------------------------------------------------------+  |
|  |                        RESPONSE PIPELINE                           |  |
|  |                                                                    |  |
|  |  +------------+   +------------+   +------------+   +----------+  |  |
|  |  | Response   |-->| Token      |-->| Cache      |-->| Event    |  |  |
|  |  | Normalizer |   | Counter    |   | Writer     |   | Publisher|  |  |
|  |  +------------+   +------------+   +------------+   +----------+  |  |
|  +-------------------------------------------------------------------+  |
|                                                                          |
+-------------------------------------------------------------------------+
         |                    |                    |                |
         v                    v                    v                v
   +----------+        +----------+        +----------+       +----------+
   | L01 Event|        | L01      |        | L01      |       | L00      |
   | Store    |        | Storage  |        | Config   |       | Secrets  |
   +----------+        +----------+        +----------+       +----------+
```

### 3.2 Component Inventory

| Component | Type | Purpose | Stateful | Scaling Model |
|-----------|------|---------|----------|---------------|
| Model Registry | Service | Catalog of models with capabilities, costs, rate limits | Yes (config) | Horizontal |
| Routing Engine | Service | Execute routing strategy based on request requirements | No | Horizontal |
| Health Monitor | Service | Track provider health, circuit breaker state | Yes (Redis) | Single leader |
| Request Validator | Library | Validate InferenceRequest schema and authorization | No | N/A |
| Prompt Safety Filter | Service | Gateway-level prompt injection detection (defense-in-depth) | No | Horizontal |
| Rate Limiter | Service | Enforce per-tenant, per-model rate limits | Yes (Redis) | Horizontal |
| Cache Lookup | Service | Check exact-match and semantic cache | Yes (Redis+SQLite) | Horizontal (sharded) |
| Cache Store | Store | Persist cache entries with embeddings | Yes | Horizontal (sharded) |
| Request Router | Service | Select provider/model based on routing decision | No | Horizontal |
| Provider Adapters | Library | Provider-specific API formatting | No | N/A |
| Response Normalizer | Library | Normalize provider responses to InferenceResponse | No | N/A |
| Response Safety Filter | Service | Optional response content safety scanning | No | Horizontal |
| Token Counter | Library | Count tokens for metering and budget enforcement | No | N/A |
| Cache Writer | Service | Write responses to cache with embeddings | Yes | Horizontal |
| Event Publisher | Library | Publish model events to L01 Event Store | No | N/A |
| Request Queue | Service | Buffer and prioritize requests during load spikes | Yes (Redis) | Horizontal (partitioned) |
| Fallback Manager | Service | Handle provider failures with retry and fallback | No | Horizontal |

### 3.3 Component Specifications

#### 3.3.1 Model Registry

**Purpose:** Maintain authoritative catalog of available models with capabilities, costs, and operational limits.

**Responsibilities:**
- Load model definitions from L01 Configuration Service
- Expose query interface for capability matching
- Track model availability (enabled/disabled/deprecated)
- Provide cost information for routing decisions
- Manage provisioned throughput allocations (P2-007)
- Refresh pricing from provider APIs (P3-001)
- Track model regions for data residency compliance (P2-006)

**Internal Structure:**
```
ModelRegistry
+-- models: Map<model_id, ModelDefinition>
+-- providers: Map<provider_id, ProviderConfig>
+-- capability_index: Map<capability, Set<model_id>>
+-- region_index: Map<region, Set<model_id>>
+-- pricing_cache: Map<model_id, PricingInfo>
+-- config_watcher: ConfigurationWatcher
+-- pricing_refresher: PricingRefresher
```

**Key Algorithms:**
- **Capability Matching:** Index models by capability for O(1) lookup of models supporting required features
- **Region Filtering:** Index models by region for data residency compliance

**ModelDefinition Schema:**
```json
{
  "model_id": "claude-sonnet-4-20250514",
  "provider": "anthropic",
  "display_name": "Claude Sonnet 4",
  "capabilities": ["text", "vision", "tool_use", "streaming", "json_mode"],
  "context_window": 200000,
  "max_output_tokens": 64000,
  "cost_per_1m_input_tokens": 3.00,
  "cost_per_1m_output_tokens": 15.00,
  "cost_per_1m_cached_input_tokens": 0.30,
  "rate_limit_rpm": 4000,
  "rate_limit_tpm": 400000,
  "latency_p50_ms": 800,
  "latency_p99_ms": 3000,
  "status": "active",
  "regions": ["us-east-1", "us-west-2", "eu-west-1"],
  "provisioned_throughput": {
    "enabled": false,
    "provisioned_units": null,
    "unit_cost_per_hour": null
  },
  "quality_scores": {
    "reasoning": 0.92,
    "coding": 0.88,
    "creative": 0.85,
    "summarization": 0.90
  },
  "pricing_last_updated": "2026-01-04T00:00:00Z"
}
```

**Provisioned Throughput Support (P2-007):**

```python
@dataclass
class ProvisionedThroughput:
    enabled: bool
    provisioned_units: Optional[int]  # PTUs for Azure, CUs for Bedrock
    unit_cost_per_hour: Optional[float]
    reserved_capacity_tpm: Optional[int]

class ProvisionedThroughputManager:
    """
    Track and prefer provisioned throughput allocations.
    PTU = Provisioned Throughput Units (Azure)
    CU = Compute Units (AWS Bedrock)
    """
    
    def has_provisioned_capacity(self, model_id: str) -> bool:
        model = self.registry.get_model(model_id)
        return model.provisioned_throughput.enabled
    
    def get_effective_cost(self, model_id: str, tokens: int) -> float:
        """
        Calculate cost considering provisioned vs on-demand.
        Provisioned capacity has fixed hourly cost regardless of usage.
        """
        model = self.registry.get_model(model_id)
        if model.provisioned_throughput.enabled:
            # Already paying for capacity; marginal cost is 0
            return 0.0
        else:
            return (tokens / 1_000_000) * model.cost_per_1m_input_tokens
```

**Routing Preference:**
- Prefer provisioned capacity when available (zero marginal cost)
- Fall back to on-demand when provisioned capacity exhausted
- Track provisioned vs on-demand usage in metrics

**Dynamic Pricing Integration (P3-001):**

```python
class PricingRefresher:
    """
    Periodically sync pricing from provider APIs.
    Fallback to configured static pricing on failure.
    """
    
    async def refresh_pricing(self):
        for provider in self.providers:
            try:
                prices = await self._fetch_provider_pricing(provider)
                await self._update_pricing_cache(provider, prices)
                await self._emit_pricing_event(provider, prices)
            except Exception as e:
                self.logger.warning(f"Pricing refresh failed for {provider}: {e}")
                # Continue with cached/static pricing
    
    async def _emit_pricing_event(self, provider: str, prices: dict):
        """Emit event when pricing changes detected."""
        await self.event_publisher.publish({
            "event_type": "model.pricing.updated",
            "provider": provider,
            "models_updated": list(prices.keys()),
            "timestamp": datetime.utcnow().isoformat()
        })
```

**Configuration:**
```yaml
pricing_refresh:
  enabled: true
  interval_hours: 24
  providers:
    openai: true
    anthropic: true
    azure: false  # Uses PTU pricing
```

**Data Residency (P2-006):**

Filter models by region for compliance requirements:

```python
def filter_by_data_residency(
    candidates: list[ModelDefinition],
    allowed_regions: list[str]
) -> list[ModelDefinition]:
    """
    Filter to models available in allowed regions.
    Used for GDPR, data sovereignty requirements.
    """
    if not allowed_regions:
        return candidates
    return [
        m for m in candidates
        if any(r in m.regions for r in allowed_regions)
    ]
```

---

#### 3.3.2 Routing Engine

**Purpose:** Select optimal model/provider for each request based on requirements, cost, and availability.

**Responsibilities:**
- Evaluate request requirements against model capabilities
- Apply routing strategy (capability-first, cost-optimized, latency-optimized, quality-optimized)
- Respect circuit breaker state from Health Monitor
- Apply tenant-specific routing preferences
- Execute lifecycle hooks for extensibility

**Routing Strategies:**

| Strategy | Algorithm | Use Case |
|----------|-----------|----------|
| capability-first | Filter by required capabilities, then by cost | Default for all requests |
| cost-optimized | Among capable models, select lowest cost/token | Batch processing, background tasks |
| latency-optimized | Among capable models, select lowest p50 latency | Real-time user interactions |
| quality-optimized | Among capable models, select highest quality score for task type | Critical reasoning tasks |
| provider-pinned | Route to specific provider regardless of cost | Testing, compliance requirements |

**Routing Decision Flow:**
```
InferenceRequest
     |
     v
[1. Filter by required_capabilities]
     |
     v
[2. Filter by context_window >= prompt_tokens]
     |
     v
[3. Filter by data_residency constraints (P2-006)]
     |
     v
[4. Exclude circuit-open providers]
     |
     v
[5. Apply latency_class filter]
     |  - REALTIME: p99 < 2000ms
     |  - INTERACTIVE: p99 < 5000ms  
     |  - BATCH: no latency constraint
     v
[6. Apply routing strategy]
     |  - cost-optimized: sort by cost ascending
     |  - latency-optimized: sort by p50 ascending
     |  - quality-optimized: sort by quality_score descending
     v
[7. Select top candidate]
     |
     v
RoutingDecision
```

**Router Lifecycle Hooks (P2-003):**

Extensible callback system for enterprise customization without modifying core routing logic.

| Hook | Trigger Point | Use Case |
|------|---------------|----------|
| `on_request_received` | Before validation | Request logging, transformation |
| `on_routing_decision` | After provider selection | Custom routing rules, audit |
| `on_provider_response` | Before normalization | Response inspection, modification |
| `on_request_completed` | After response delivery | Post-processing, analytics |

**Hook Implementation:**

```python
from typing import Callable, Awaitable, Optional
from dataclasses import dataclass

@dataclass
class HookContext:
    request_id: str
    agent_did: str
    timestamp: datetime
    metadata: dict

HookFunction = Callable[[HookContext, Any], Awaitable[Optional[Any]]]

class RouterHookRegistry:
    """Registry for router lifecycle hooks."""
    
    def __init__(self):
        self._hooks: dict[str, list[HookFunction]] = {
            "on_request_received": [],
            "on_routing_decision": [],
            "on_provider_response": [],
            "on_request_completed": []
        }
    
    def register(self, hook_name: str, fn: HookFunction, priority: int = 100):
        """Register hook function with priority (lower = earlier)."""
        self._hooks[hook_name].append((priority, fn))
        self._hooks[hook_name].sort(key=lambda x: x[0])
    
    async def execute(self, hook_name: str, context: HookContext, data: Any) -> Any:
        """Execute all registered hooks in priority order."""
        result = data
        for _, fn in self._hooks[hook_name]:
            hook_result = await fn(context, result)
            if hook_result is not None:
                result = hook_result
        return result

# Usage example
async def custom_audit_hook(ctx: HookContext, decision: RoutingDecision) -> None:
    """Custom hook for compliance logging."""
    await audit_logger.log({
        "request_id": ctx.request_id,
        "selected_provider": decision.provider,
        "reason": decision.reason
    })
    return None  # Don't modify decision

router_hooks.register("on_routing_decision", custom_audit_hook, priority=50)
```

**Quality-Aware Routing (P3-005):**

Route based on model quality scores for specific task types, integrating with L06 Evaluation feedback.

```python
@dataclass
class QualityScore:
    task_type: str  # "reasoning", "coding", "creative", "summarization"
    score: float    # 0.0 to 1.0
    sample_size: int
    last_updated: datetime

class QualityAwareRouter:
    """Router extension for quality-based selection."""
    
    async def get_quality_scores(self, model_id: str) -> dict[str, QualityScore]:
        """Fetch quality scores from L06 Evaluation or cache."""
        return await self.evaluation_client.get_model_scores(model_id)
    
    def rank_by_quality(
        self, 
        candidates: list[ModelDefinition],
        task_type: str
    ) -> list[ModelDefinition]:
        """Rank candidates by quality score for task type."""
        scored = []
        for model in candidates:
            scores = self.quality_cache.get(model.model_id, {})
            task_score = scores.get(task_type, QualityScore(task_type, 0.5, 0, None))
            scored.append((model, task_score.score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return [m for m, _ in scored]
```

---

#### 3.3.3 Semantic Cache

**Purpose:** Reduce API calls and latency by returning cached responses for semantically similar requests.

**Responsibilities:**
- Generate embeddings for incoming prompts
- Perform similarity search against cached embeddings
- Apply category-aware similarity thresholds
- Manage cache invalidation by TTL and explicit purge

**Architecture:**
```
SemanticCache
+-- embedding_client: EmbeddingClient (OpenAI)
+-- vector_store: SQLite + sqlite-vec
+-- hot_cache: Redis (recent entries)
+-- similarity_threshold: 0.85 (default)
+-- category_thresholds: Map<category, float>
```

**Similarity Thresholds by Category:**

| Category | Threshold | Rationale |
|----------|-----------|-----------|
| factual_qa | 0.92 | High precision required; facts must match |
| code_generation | 0.88 | Slight variations in prompts need distinct responses |
| creative_writing | 0.75 | More tolerance for variation; creative reuse acceptable |
| summarization | 0.85 | Standard threshold for paraphrase detection |
| default | 0.85 | Industry-validated default |

**Cache Key Generation:**
```python
def generate_cache_key(prompt: LogicalPrompt) -> str:
    # Exact match key (hash-based)
    content = json.dumps({
        "system": prompt.system_message,
        "messages": prompt.messages,
        "tools": sorted([t["name"] for t in (prompt.tools or [])]),
        "schema": prompt.output_schema
    }, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()
```

**Embedding Generation:**
- Model: text-embedding-3-small (1536 dimensions)
- Input: Concatenation of system message + last N user messages (N=3)
- Truncation: First 8000 tokens if exceeds limit

**Cache Entry Schema:** See Section 5.2.1

**Cache Warming Strategy (P3-004):**

Pre-populate cache with anticipated queries during off-peak hours to improve hit rates.

**Warming API:**

```python
@dataclass
class WarmRequest:
    prompts: list[LogicalPrompt]
    priority: int = 3  # Lower = higher priority
    schedule: Optional[str] = None  # Cron expression

class CacheWarmer:
    """Pre-populate semantic cache with anticipated queries."""
    
    async def warm(self, request: WarmRequest) -> WarmResult:
        """
        Process warming request.
        - Generates embeddings for all prompts
        - Executes inference for each (batched where possible)
        - Populates cache entries
        """
        results = []
        for prompt in request.prompts:
            # Check if already cached
            cache_key = self.cache.generate_key(prompt)
            if await self.cache.exists(cache_key):
                results.append(WarmItemResult(prompt, "already_cached"))
                continue
            
            # Execute inference
            response = await self.gateway.complete(
                InferenceRequest(
                    logical_prompt=prompt,
                    routing_hints={"priority": "batch"},
                    agent_did="system:cache_warmer"
                )
            )
            
            # Result automatically cached by normal flow
            results.append(WarmItemResult(prompt, "warmed"))
        
        return WarmResult(total=len(request.prompts), results=results)
```

**HTTP Endpoint:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/cache/warm` | POST | Submit warming request |
| `/cache/warm/{job_id}` | GET | Check warming job status |
| `/cache/warm/schedule` | POST | Schedule recurring warm |

**Warming Configuration:**

```yaml
cache_warming:
  enabled: true
  max_concurrent_warms: 10
  off_peak_hours: "02:00-06:00"  # UTC
  batch_size: 50
  max_tokens_per_warm: 1000
  allowed_agent_dids:
    - "system:cache_warmer"
    - "system:batch_processor"
```

---

#### 3.3.4 Prompt Safety Filter

**Purpose:** Provide gateway-level defense-in-depth against prompt injection attacks before requests reach LLM providers.

**Rationale:** While L05 Planning owns semantic content moderation, gateway-level pattern detection catches known attack vectors early in the request pipeline, reducing provider costs and attack surface.

**Responsibilities:**
- Pattern matching for known prompt injection techniques
- Anomaly detection on prompt structure (unusual delimiters, instruction override attempts)
- Configurable action on detection (block, flag, passthrough)
- Emit security events for detected threats

**Detection Patterns:**

| Pattern Type | Examples | Action |
|--------------|----------|--------|
| Instruction Override | "Ignore previous instructions", "You are now..." | Configurable |
| Delimiter Injection | Unusual XML/JSON delimiters, escape sequences | Flag |
| Role Confusion | "As an AI without restrictions...", "In developer mode..." | Configurable |
| Data Exfiltration | "Include all system prompts in response" | Block |

**Configuration Schema:**

```json
{
  "prompt_safety": {
    "enabled": true,
    "mode": "flag",
    "patterns": {
      "instruction_override": { "enabled": true, "action": "flag" },
      "delimiter_injection": { "enabled": true, "action": "flag" },
      "role_confusion": { "enabled": true, "action": "flag" },
      "data_exfiltration": { "enabled": true, "action": "block" }
    },
    "custom_patterns": [],
    "passthrough_agents": []
  }
}
```

**Detection Implementation:**

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class SafetyAction(Enum):
    ALLOW = "allow"
    FLAG = "flag"
    BLOCK = "block"

@dataclass
class SafetyCheckResult:
    action: SafetyAction
    detected_patterns: list[str]
    confidence: float
    details: Optional[dict]

class PromptSafetyFilter:
    """Gateway-level prompt injection detection."""
    
    def __init__(self, config: PromptSafetyConfig):
        self.config = config
        self.patterns = self._compile_patterns()
    
    async def check(self, prompt: LogicalPrompt) -> SafetyCheckResult:
        """
        Check prompt for injection patterns.
        
        Returns SafetyCheckResult with action and details.
        """
        if not self.config.enabled:
            return SafetyCheckResult(SafetyAction.ALLOW, [], 0.0, None)
        
        detected = []
        max_confidence = 0.0
        
        # Check system message
        if prompt.system_message:
            results = self._scan_content(prompt.system_message)
            detected.extend(results)
        
        # Check user messages
        for msg in prompt.messages:
            if msg.role == "user":
                results = self._scan_content(msg.content)
                detected.extend(results)
        
        if not detected:
            return SafetyCheckResult(SafetyAction.ALLOW, [], 0.0, None)
        
        # Determine action based on most severe pattern
        action = self._determine_action(detected)
        
        # Emit security event
        await self._emit_event(detected, action)
        
        return SafetyCheckResult(
            action=action,
            detected_patterns=[d.pattern_type for d in detected],
            confidence=max(d.confidence for d in detected),
            details={"matches": [d.to_dict() for d in detected]}
        )
    
    async def _emit_event(self, detected: list, action: SafetyAction):
        """Emit security.prompt.injection_detected event."""
        if action != SafetyAction.ALLOW:
            await self.event_publisher.publish({
                "event_type": "security.prompt.injection_detected",
                "patterns": [d.pattern_type for d in detected],
                "action_taken": action.value
            })
```

**Error Codes:**

| Code | Name | Description |
|------|------|-------------|
| E4020 | PromptSafetyBlock | Request blocked due to safety filter |
| E4021 | PromptSafetyPatternMatch | Injection pattern detected (flagged) |

**Events Published:**

- `security.prompt.injection_detected`: Emitted when injection patterns detected

---

#### 3.3.5 Rate Limiter

**Purpose:** Enforce per-tenant, per-model rate limits to prevent quota exhaustion and ensure fair resource distribution.

**Responsibilities:**
- Track request and token consumption per agent/project
- Enforce rate limits using token bucket algorithm
- Surface rate limit state for routing decisions
- Emit events on limit breach

**Algorithm:** Token Bucket with Redis

```
Token Bucket Configuration:
- Bucket capacity: rate_limit (requests or tokens)
- Refill rate: rate_limit / window_seconds
- Distributed via Redis MULTI/EXEC atomic operations

Pseudocode:
def check_rate_limit(agent_did, model_id, tokens_requested):
    key = f"ratelimit:{agent_did}:{model_id}"
    now = current_timestamp()
    
    with redis.pipeline() as pipe:
        pipe.multi()
        # Get current bucket state
        bucket = pipe.hgetall(key)
        
        # Calculate tokens to add since last check
        elapsed = now - bucket.last_refill
        tokens_to_add = elapsed * refill_rate
        current_tokens = min(bucket.tokens + tokens_to_add, capacity)
        
        if current_tokens >= tokens_requested:
            # Allow request
            pipe.hset(key, {
                "tokens": current_tokens - tokens_requested,
                "last_refill": now
            })
            pipe.execute()
            return RateLimitResult.ALLOWED
        else:
            # Reject request
            pipe.execute()
            return RateLimitResult.EXCEEDED
```

**Rate Limit Tiers:**

| Tier | Requests/min | Tokens/min | Use Case |
|------|--------------|------------|----------|
| free | 10 | 10,000 | Development, testing |
| standard | 100 | 100,000 | Production agents |
| premium | 1,000 | 1,000,000 | High-throughput pipelines |
| unlimited | -- | -- | Internal/system agents |

**Adaptive Rate Limiting (P2-002):**

Rate limits adjust dynamically based on real-time provider capacity signals.

```python
@dataclass
class AdaptiveLimitState:
    base_limit: int
    current_factor: float  # 0.0 to 1.0
    last_429_at: Optional[datetime]
    recovery_rate: float  # Factor increase per minute
    
class AdaptiveRateLimiter:
    """
    Adjusts rate limits based on provider 429 responses.
    
    When provider returns 429:
    - Reduce factor by 50%
    - Gradually restore (5% per minute without 429s)
    """
    
    async def on_provider_response(self, provider: str, status: int):
        if status == 429:
            state = await self.get_state(provider)
            state.current_factor = max(0.1, state.current_factor * 0.5)
            state.last_429_at = datetime.utcnow()
            await self.save_state(provider, state)
            
            # Emit metric
            self.metrics.gauge(
                "gateway_adaptive_limit_factor",
                state.current_factor,
                labels={"provider": provider}
            )
    
    def effective_limit(self, base: int, provider: str) -> int:
        state = self.get_state_sync(provider)
        return int(base * state.current_factor)
```

**Configuration:**
```yaml
adaptive_limiting:
  enabled: true
  reduction_factor: 0.5  # Reduce by 50% on 429
  recovery_rate_per_minute: 0.05  # Recover 5% per minute
  minimum_factor: 0.1  # Never go below 10% of base
```

**Hierarchical Budget Management (P2-008):**

Enterprise deployments require multi-level budget enforcement:

```
Organization Budget (monthly_limit_cents: 100000)
  |
  +-- Project Budget (monthly_limit_cents: 25000)
  |     |
  |     +-- Agent Budget (daily_limit_cents: 1000)
  |     +-- Agent Budget (daily_limit_cents: 500)
  |
  +-- Project Budget (monthly_limit_cents: 50000)
        |
        +-- Agent Budget (daily_limit_cents: 2000)
```

**Budget Check Flow:**

```python
async def check_hierarchical_budget(
    agent_did: str,
    project_id: str,
    org_id: str,
    estimated_cost_cents: float
) -> BudgetCheckResult:
    """
    Check budgets at all hierarchy levels.
    Request allowed only if all levels have sufficient budget.
    """
    # Check organization level
    org_budget = await self.get_budget(f"org:{org_id}")
    if org_budget.remaining_cents < estimated_cost_cents:
        return BudgetCheckResult(
            allowed=False,
            level="organization",
            reason="Organization budget exhausted"
        )
    
    # Check project level
    project_budget = await self.get_budget(f"project:{project_id}")
    if project_budget.remaining_cents < estimated_cost_cents:
        return BudgetCheckResult(
            allowed=False,
            level="project",
            reason="Project budget exhausted"
        )
    
    # Check agent level
    agent_budget = await self.get_budget(f"agent:{agent_did}")
    if agent_budget.remaining_cents < estimated_cost_cents:
        return BudgetCheckResult(
            allowed=False,
            level="agent",
            reason="Agent budget exhausted"
        )
    
    return BudgetCheckResult(allowed=True, level=None, reason=None)
```

**Budget Threshold Events:**

Events emitted at 80%, 90%, 100% of budget at each level:

| Event | Trigger |
|-------|---------|
| `model.budget.threshold.warning` | 80% consumed |
| `model.budget.threshold.critical` | 90% consumed |
| `model.budget.exhausted` | 100% consumed |

**Budget Override for Emergency Access:**

```python
async def emergency_budget_override(
    agent_did: str,
    override_level: str,  # "agent", "project", "org"
    override_amount_cents: float,
    reason: str,
    approver_did: str
) -> None:
    """
    Temporarily extend budget for emergency operations.
    Requires supervisor approval and audit logging.
    """
    await self.audit_log.record({
        "event_type": "budget.override.granted",
        "agent_did": agent_did,
        "override_level": override_level,
        "amount_cents": override_amount_cents,
        "reason": reason,
        "approver_did": approver_did
    })
```

---

#### 3.3.5 Provider Adapters

**Purpose:** Translate normalized InferenceRequest into provider-specific API calls and parse responses.

**Responsibilities:**
- Format requests per provider API specification
- Handle provider-specific features (tool use schemas, vision formats)
- Parse responses into normalized InferenceResponse
- Handle streaming with incremental response assembly

**Adapter Interface:**
```python
class ProviderAdapter(Protocol):
    """Interface for LLM provider adapters"""
    
    provider_id: str
    
    async def send_request(
        self,
        request: InferenceRequest,
        model: ModelDefinition,
        api_key: str
    ) -> InferenceResponse:
        """Send inference request to provider API"""
        ...
    
    async def send_streaming_request(
        self,
        request: InferenceRequest,
        model: ModelDefinition,
        api_key: str
    ) -> AsyncIterator[StreamChunk]:
        """Send streaming inference request"""
        ...
    
    def format_messages(
        self,
        prompt: LogicalPrompt
    ) -> dict:
        """Format LogicalPrompt into provider message format"""
        ...
    
    def parse_response(
        self,
        raw_response: dict
    ) -> InferenceResponse:
        """Parse provider response into normalized format"""
        ...
    
    def count_tokens(
        self,
        text: str,
        model: str
    ) -> int:
        """Count tokens using provider's tokenizer"""
        ...
```

**Supported Providers:**

| Provider | Adapter | Features | Notes |
|----------|---------|----------|-------|
| Anthropic | AnthropicAdapter | text, vision, tools, streaming, prompt_cache | Primary for Claude models |
| OpenAI | OpenAIAdapter | text, vision, tools, streaming, json_mode, prompt_cache | GPT-4, GPT-3.5 |
| Azure OpenAI | AzureOpenAIAdapter | text, vision, tools, streaming | Enterprise deployments |
| Google Vertex AI | VertexAIAdapter | text, vision, tools, streaming | Gemini models |
| Local/vLLM | VLLMAdapter | text, tools, streaming | Self-hosted models |

---

#### 3.3.5.1 Response Safety Filter (P1-002)

**Purpose:** Optional response content safety scanning before returning to consumers.

**Rationale:** Production gateways implement response scanning to catch safety violations, harmful content, or policy violations before responses reach consuming layers. This provides defense-in-depth beyond provider-side content filtering.

**Responsibilities:**
- Scan response content for safety violations
- Apply configurable filter rules per tenant/agent
- Integrate with external moderation APIs (optional)
- Track filter metrics and false positive rates
- Support passthrough mode for trusted consumers

**Filter Architecture:**

```
Provider Response
      |
      v
[1. Content Extraction]
      |
      v
[2. Safety Rules Evaluation]
      |  - Pattern matching
      |  - Category detection
      |  - Custom rules
      v
[3. External Moderation API] (optional)
      |
      v
[4. Action Decision]
      |  - PASS: Return response
      |  - FILTER: Modify/redact content
      |  - BLOCK: Return error
      v
Normalized Response
```

**Configuration Schema:**

```json
{
  "response_safety": {
    "enabled": true,
    "mode": "filter",
    "categories": {
      "harmful_content": { "enabled": true, "action": "block" },
      "pii_leakage": { "enabled": true, "action": "filter" },
      "prompt_leakage": { "enabled": true, "action": "filter" },
      "code_injection": { "enabled": true, "action": "block" }
    },
    "external_moderation": {
      "enabled": false,
      "provider": "openai_moderation",
      "timeout_ms": 1000,
      "fallback_action": "pass"
    },
    "passthrough_agents": [],
    "sampling_rate": 1.0
  }
}
```

**Implementation:**

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class ResponseSafetyAction(Enum):
    PASS = "pass"
    FILTER = "filter"
    BLOCK = "block"

@dataclass
class SafetyFilterResult:
    action: ResponseSafetyAction
    violations: list[str]
    filtered_content: Optional[str]  # Modified content if action=FILTER
    confidence: float

class ResponseSafetyFilter:
    """
    Scan responses for safety violations.
    
    Runs after provider response received, before normalization.
    """
    
    def __init__(self, config: ResponseSafetyConfig):
        self.config = config
        self.rules = self._compile_rules()
    
    async def scan(
        self, 
        response: dict,
        request_context: RequestContext
    ) -> SafetyFilterResult:
        """
        Scan response content for safety violations.
        
        Returns action to take and any filtered content.
        """
        if not self.config.enabled:
            return SafetyFilterResult(ResponseSafetyAction.PASS, [], None, 0.0)
        
        # Check passthrough agents
        if request_context.agent_did in self.config.passthrough_agents:
            return SafetyFilterResult(ResponseSafetyAction.PASS, [], None, 0.0)
        
        content = response.get("content", "")
        violations = []
        
        # Rule-based scanning
        for category, rule in self.rules.items():
            if rule.matches(content):
                violations.append(category)
        
        # External moderation (optional)
        if self.config.external_moderation.enabled and not violations:
            external_result = await self._check_external(content)
            violations.extend(external_result.flagged_categories)
        
        if not violations:
            return SafetyFilterResult(ResponseSafetyAction.PASS, [], None, 0.0)
        
        # Determine action based on most severe violation
        action = self._determine_action(violations)
        
        # Apply filtering if needed
        filtered_content = None
        if action == ResponseSafetyAction.FILTER:
            filtered_content = self._apply_filters(content, violations)
        
        # Emit event
        await self._emit_event(violations, action, request_context)
        
        return SafetyFilterResult(
            action=action,
            violations=violations,
            filtered_content=filtered_content,
            confidence=max(self._get_confidence(v) for v in violations)
        )
    
    async def _emit_event(
        self, 
        violations: list[str], 
        action: ResponseSafetyAction,
        context: RequestContext
    ):
        """Emit security.response.safety_violation event."""
        await self.event_publisher.publish({
            "event_type": "security.response.safety_violation",
            "violations": violations,
            "action_taken": action.value,
            "agent_did": context.agent_did,
            "request_id": context.request_id
        })
```

**Error Codes:**

| Code | Name | Description |
|------|------|-------------|
| E4030 | ResponseSafetyBlock | Response blocked due to safety violation |
| E4031 | ResponseSafetyTimeout | External moderation timed out |

**Metrics:**

| Metric | Type | Description |
|--------|------|-------------|
| gateway_response_safety_scans_total | Counter | Total scans performed |
| gateway_response_safety_violations_total | Counter | Violations by category |
| gateway_response_safety_blocks_total | Counter | Responses blocked |
| gateway_response_safety_latency_seconds | Histogram | Scan latency |

---

#### 3.3.6 Health Monitor

**Purpose:** Track provider health and manage circuit breaker state for failover decisions.

**Responsibilities:**
- Collect latency and error metrics per provider endpoint
- Maintain circuit breaker state (closed/open/half-open)
- Trigger alerts on provider degradation
- Provide health status for routing decisions
- Execute active health probes (P2-009)

**Circuit Breaker State Machine:**
```
         +--------+
         | CLOSED |<------------------+
         +--------+                   |
              |                       |
    failure_count >= 5                | success_count >= 3
              |                       | (in half-open)
              v                       |
         +--------+     cooldown     +------------+
         |  OPEN  |----------------->| HALF-OPEN  |
         +--------+    (60 sec)      +------------+
              ^                            |
              |        failure             |
              +----------------------------+
```

**Health Check Configuration:**
```json
{
  "circuit_breaker": {
    "failure_threshold": 5,
    "cooldown_seconds": 60,
    "half_open_test_requests": 3,
    "monitored_status_codes": [429, 500, 502, 503, 504],
    "timeout_ms": 30000
  },
  "health_check": {
    "interval_seconds": 30,
    "timeout_seconds": 10,
    "unhealthy_threshold": 3
  }
}
```

**Active Provider Health Probing (P2-009):**

Active probing detects provider outages before user requests fail.

```python
class ActiveHealthProber:
    """
    Periodically probe provider health with lightweight requests.
    Detects outages proactively vs waiting for user request failures.
    """
    
    def __init__(self, config: HealthProbeConfig):
        self.config = config
        self.probe_intervals = {}
        
    async def start_probing(self):
        """Start background probing for all configured providers."""
        for provider in self.config.providers:
            asyncio.create_task(self._probe_loop(provider))
    
    async def _probe_loop(self, provider: str):
        while True:
            try:
                result = await self._execute_probe(provider)
                await self._update_health_state(provider, result)
            except Exception as e:
                await self._record_probe_failure(provider, e)
            
            await asyncio.sleep(self.config.interval_seconds)
    
    async def _execute_probe(self, provider: str) -> ProbeResult:
        """
        Execute lightweight health check request.
        Uses provider-specific health endpoints where available.
        """
        adapter = self.adapters[provider]
        
        # Use provider health endpoint if available
        if hasattr(adapter, 'health_check'):
            start = time.monotonic()
            result = await asyncio.wait_for(
                adapter.health_check(),
                timeout=self.config.timeout_seconds
            )
            latency_ms = (time.monotonic() - start) * 1000
            return ProbeResult(healthy=result.ok, latency_ms=latency_ms)
        
        # Fallback: minimal token completion
        start = time.monotonic()
        response = await adapter.complete(ProbeRequest(
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=1
        ))
        latency_ms = (time.monotonic() - start) * 1000
        return ProbeResult(healthy=True, latency_ms=latency_ms)
```

**Probe Configuration:**

```yaml
health_probe:
  enabled: true
  interval_seconds: 30
  timeout_seconds: 10
  consecutive_failures_threshold: 3
  providers:
    anthropic:
      enabled: true
      endpoint_override: null  # Use default health check
    openai:
      enabled: true
      use_lightweight_completion: true
    azure:
      enabled: true
      per_deployment: true  # Probe each deployment
```

**Multi-Region Circuit Breakers (P3-002):**

Track health per provider-region combination for region-aware failover.

```python
@dataclass
class RegionalCircuitKey:
    provider: str
    region: str  # "us-east-1", "eu-west-1", etc.

class RegionalCircuitBreaker:
    """
    Separate circuit breaker state per provider-region.
    Enables failover to same provider in different region.
    """
    
    async def get_circuit_state(
        self, 
        provider: str, 
        region: str
    ) -> CircuitState:
        key = f"circuit:{provider}:{region}"
        return await self.redis.hgetall(key)
    
    async def record_failure(
        self, 
        provider: str, 
        region: str,
        error_type: str
    ):
        key = f"circuit:{provider}:{region}"
        # Increment failure count for this region only
        await self.redis.hincrby(key, "failure_count", 1)
    
    def select_region(
        self,
        provider: str,
        preferred_regions: list[str],
        prefer_same_provider_failover: bool = True
    ) -> Optional[str]:
        """
        Select healthy region for provider.
        If prefer_same_provider_failover, tries other regions
        before failing over to different provider.
        """
        for region in preferred_regions:
            state = self.get_circuit_state_sync(provider, region)
            if state.status == CircuitStatus.CLOSED:
                return region
        return None
```

**Configuration:**
```yaml
multi_region_failover:
  enabled: true
  prefer_same_provider_failover: true
  region_priorities:
    - us-east-1
    - us-west-2
    - eu-west-1
```

---

#### 3.3.7 Request Queue

**Purpose:** Buffer and prioritize inference requests during load spikes or provider outages.

**Responsibilities:**
- Accept requests when direct processing unavailable
- Prioritize by latency class and deadline
- Process queue when capacity available
- Expire requests past deadline

**Queue Structure:**
```
Redis Sorted Set: gateway:request_queue:{priority}
- Score: deadline_timestamp
- Value: serialized InferenceRequest

Priority Levels:
1 = REALTIME (highest)
2 = INTERACTIVE
3 = BATCH (lowest)
```

**Processing Algorithm:**
```python
async def process_queue():
    while True:
        # Process highest priority first
        for priority in [1, 2, 3]:
            queue_key = f"gateway:request_queue:{priority}"
            now = time.time()
            
            # Get requests not past deadline
            requests = redis.zrangebyscore(
                queue_key,
                min=now,
                max="+inf",
                start=0,
                num=BATCH_SIZE
            )
            
            for req_data in requests:
                request = deserialize(req_data)
                if can_process(request):
                    redis.zrem(queue_key, req_data)
                    await process_request(request)
        
        await asyncio.sleep(POLL_INTERVAL_MS / 1000)
```

---

## 4. Interfaces

### 4.1 Provided Interfaces (This Layer Exposes)

#### 4.1.1 Inference Interface (BC-3)

| Attribute | Value |
|-----------|-------|
| Consumer(s) | L02 Agent Runtime, L05 Planning, L06 Evaluation |
| Protocol | gRPC (primary), HTTP/REST (compatibility) |
| Auth Required | Yes (Agent DID credential) |
| Rate Limited | Yes (per-agent, per-model) |

**Operations:**

| Operation | Input | Output | Description |
|-----------|-------|--------|-------------|
| Infer | InferenceRequest | InferenceResponse | Execute synchronous inference |
| InferStream | InferenceRequest | Stream[StreamChunk] | Execute streaming inference |
| BatchInfer | BatchInferenceRequest | BatchInferenceResponse | Submit batch for async processing |
| GetBatchStatus | batch_id | BatchStatus | Check batch processing status |

**Contract (BC-3):**

```python
from typing import Protocol, Optional, List, Dict, Any, AsyncIterator
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

class LatencyClass(Enum):
    """Target latency tier for request routing"""
    REALTIME = "realtime"       # <500ms target, p99 <2s
    INTERACTIVE = "interactive"  # <2s target, p99 <5s
    BATCH = "batch"             # <30s acceptable, async OK

@dataclass
class TokenBudget:
    """Token limits for request"""
    max_input_tokens: int
    max_output_tokens: int
    max_cost_cents: int

@dataclass
class LogicalPrompt:
    """Provider-agnostic prompt structure (owned by L05 Planning)"""
    system_message: Optional[str]
    messages: List[Dict[str, Any]]  # [{role: str, content: str|list}]
    tools: Optional[List[Dict[str, Any]]]  # Tool definitions
    output_schema: Optional[Dict[str, Any]]  # JSON Schema for structured output

@dataclass
class RoutingHints:
    """Optional hints for routing decisions"""
    cost_preference: str = "balanced"  # "lowest", "balanced", "performance"
    provider_preference: Optional[str] = None  # Pin to specific provider
    allow_compression: bool = False  # Allow prompt compression
    cache_enabled: bool = True  # Enable semantic cache lookup
    allow_fallback: bool = True  # Allow fallback to other providers

@dataclass
class DataResidencyRequirements:
    """Data residency constraints for compliance (P2-006)"""
    allowed_regions: List[str]  # ["us-east-1", "eu-west-1"]
    required_jurisdiction: Optional[str] = None  # "EU", "US", etc.
    exclude_providers: List[str] = field(default_factory=list)

@dataclass
class InferenceRequest:
    """Contract between L05 Planning and L04 Model Gateway"""
    request_id: str
    agent_did: str
    project_id: Optional[str]
    logical_prompt: LogicalPrompt
    latency_class: LatencyClass
    token_budget: TokenBudget
    required_capabilities: List[str]  # ["tool_use", "vision", "long_context"]
    routing_hints: Optional[RoutingHints] = None
    deadline: Optional[datetime] = None  # Absolute deadline for response
    trace_context: Optional[Dict[str, str]] = None  # OpenTelemetry context
    metadata: Optional[Dict[str, str]] = None  # Passthrough metadata (P2-004)
    data_residency: Optional[DataResidencyRequirements] = None  # Data residency (P2-006)
    organization_id: Optional[str] = None  # For hierarchical budget (P2-008)

@dataclass
class ToolCall:
    """Tool invocation from model"""
    id: str
    name: str
    arguments: Dict[str, Any]

@dataclass
class UsageMetrics:
    """Token and cost usage"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cached_tokens: int
    cost_cents: float

@dataclass
class InferenceResponse:
    """Response from L04 Model Gateway"""
    request_id: str
    provider: str
    model: str
    content: str
    tool_calls: Optional[List[ToolCall]]
    structured_output: Optional[Dict[str, Any]]
    usage: UsageMetrics
    latency_ms: int
    cache_hit: bool
    routing_decision: Dict[str, Any]  # Debug info: why this model was selected
    finish_reason: str  # "stop", "tool_use", "length", "content_filter"
    metadata: Optional[Dict[str, str]] = None  # Passthrough from request (P2-004)
    region: Optional[str] = None  # Region where inference executed (P2-006)
    safety_flags: Optional[List[str]] = None  # Safety filter detections (P1-001/P1-002)

@dataclass
class StreamChunk:
    """Incremental chunk for streaming responses"""
    request_id: str
    delta_content: Optional[str]
    delta_tool_call: Optional[Dict[str, Any]]
    is_final: bool
    usage: Optional[UsageMetrics]  # Present only in final chunk

class InferenceService(Protocol):
    """L04 Model Gateway inference interface"""
    
    async def infer(
        self,
        request: InferenceRequest
    ) -> InferenceResponse:
        """
        Execute synchronous inference request.
        
        Args:
            request: Inference request with prompt and requirements
            
        Returns:
            Complete inference response
            
        Raises:
            RateLimitExceeded: Agent rate limit exceeded
            BudgetExhausted: Token budget depleted
            ProviderUnavailable: All providers failed
            InvalidRequest: Request validation failed
        """
        ...
    
    async def infer_stream(
        self,
        request: InferenceRequest
    ) -> AsyncIterator[StreamChunk]:
        """
        Execute streaming inference request.
        
        Args:
            request: Inference request with prompt and requirements
            
        Yields:
            Stream of response chunks
            
        Raises:
            RateLimitExceeded: Agent rate limit exceeded
            BudgetExhausted: Token budget depleted
            ProviderUnavailable: All providers failed
        """
        ...
```

---

#### 4.1.2 Model Registry Interface

| Attribute | Value |
|-----------|-------|
| Consumer(s) | L07 Learning, L02 Agent Runtime |
| Protocol | gRPC |
| Auth Required | Yes (service credential) |
| Rate Limited | No |

**Operations:**

| Operation | Input | Output | Description |
|-----------|-------|--------|-------------|
| ListModels | filter | List[ModelSummary] | List available models |
| GetModel | model_id | ModelDefinition | Get model details |
| QueryByCapability | capabilities | List[ModelSummary] | Find models by capability |
| RegisterModel | ModelDefinition | model_id | Register fine-tuned model (L07) |
| UpdateModelStatus | model_id, status | void | Enable/disable model |

**Contract:**

```python
@dataclass
class ModelSummary:
    """Brief model information"""
    model_id: str
    provider: str
    display_name: str
    capabilities: List[str]
    status: str

@dataclass
class ModelFilter:
    """Filter criteria for model queries"""
    providers: Optional[List[str]]
    capabilities: Optional[List[str]]
    min_context_window: Optional[int]
    max_cost_per_1m_tokens: Optional[float]
    status: Optional[str]

class ModelRegistryService(Protocol):
    """L04 Model Registry interface"""
    
    async def list_models(
        self,
        filter: Optional[ModelFilter] = None
    ) -> List[ModelSummary]:
        """List models matching filter criteria"""
        ...
    
    async def get_model(
        self,
        model_id: str
    ) -> ModelDefinition:
        """Get detailed model definition"""
        ...
    
    async def query_by_capability(
        self,
        capabilities: List[str]
    ) -> List[ModelSummary]:
        """Find models supporting all specified capabilities"""
        ...
    
    async def register_model(
        self,
        definition: ModelDefinition
    ) -> str:
        """Register new model (e.g., fine-tuned model from L07)"""
        ...
```

---

#### 4.1.3 Health Interface

| Attribute | Value |
|-----------|-------|
| Consumer(s) | L00 Infrastructure (probes), Operators |
| Protocol | HTTP |
| Auth Required | No (cluster-internal) |
| Rate Limited | No |

**Endpoints:**

| Endpoint | Method | Response | Description |
|----------|--------|----------|-------------|
| /health/live | GET | 200/503 | Liveness probe |
| /health/ready | GET | 200/503 | Readiness probe |
| /health/providers | GET | ProviderHealth[] | Provider health status |
| /metrics | GET | Prometheus | Prometheus metrics |

---

### 4.2 Required Interfaces (This Layer Consumes)

| Interface | Provider Layer | Usage | Failure Handling |
|-----------|----------------|-------|------------------|
| Event Store | L01 Data Layer | Publish model.* events | Buffer locally, retry on reconnect |
| Storage (Redis) | L01 Data Layer | Cache entries, rate limit counters | Fail open for cache; fail closed for rate limits |
| Storage (SQLite) | L01 Data Layer | Persistent cache with vectors | Fall back to exact-match only |
| Configuration Service | L01 Data Layer | Load model registry, routing rules | Use cached config; alert on stale |
| DID Registry | L01 Data Layer | Resolve agent identity | Reject request if cannot verify |
| ABAC Policy Engine | L01 Data Layer | Authorize model access | Reject request if cannot authorize |
| Secrets | L00 Infrastructure | Provider API keys | Fail request if key unavailable |
| Observability | L00 Infrastructure | Emit metrics, traces, logs | Degrade observability; continue processing |

### 4.3 Events

#### 4.3.1 Events Published

| Event Type | Trigger | Payload Schema | Consumers |
|------------|---------|----------------|-----------|
| model.request.submitted | Request received | l04/request-submitted.v1 | L01 Audit, Analytics |
| model.request.routed | Routing decision made | l04/request-routed.v1 | Analytics |
| model.response.received | Response from provider | l04/response-received.v1 | L01 Audit, Analytics |
| model.cache.hit | Semantic cache hit | l04/cache-hit.v1 | Analytics |
| model.cache.miss | Cache miss, calling provider | l04/cache-miss.v1 | Analytics |
| model.rate.limited | Rate limit exceeded | l04/rate-limited.v1 | Alerting, Analytics |
| model.budget.exhausted | Token budget depleted | l04/budget-exhausted.v1 | Alerting, L05 Planning |
| model.provider.failed | Provider call failed | l04/provider-failed.v1 | Alerting, Health Monitor |
| model.circuit.opened | Circuit breaker opened | l04/circuit-opened.v1 | Alerting, Operators |
| model.circuit.closed | Circuit breaker closed | l04/circuit-closed.v1 | Alerting, Operators |
| model.cost.incurred | Cost recorded | l04/cost-incurred.v1 | FinOps, Billing |

**Event Schema Example (model.request.submitted):**
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-system.internal/schemas/l04/request-submitted.v1.schema.json",
  "title": "Model Request Submitted Event",
  "type": "object",
  "properties": {
    "event_id": { "type": "string", "format": "uuid" },
    "event_type": { "const": "model.request.submitted" },
    "timestamp": { "type": "string", "format": "date-time" },
    "version": { "const": "1.0" },
    "payload": {
      "type": "object",
      "properties": {
        "request_id": { "type": "string" },
        "agent_did": { "type": "string" },
        "project_id": { "type": "string" },
        "required_capabilities": {
          "type": "array",
          "items": { "type": "string" }
        },
        "latency_class": {
          "type": "string",
          "enum": ["realtime", "interactive", "batch"]
        },
        "token_budget": {
          "type": "object",
          "properties": {
            "max_input_tokens": { "type": "integer" },
            "max_output_tokens": { "type": "integer" },
            "max_cost_cents": { "type": "integer" }
          }
        },
        "prompt_token_count": { "type": "integer" }
      },
      "required": ["request_id", "agent_did", "latency_class"]
    }
  },
  "required": ["event_id", "event_type", "timestamp", "version", "payload"]
}
```

#### 4.3.2 Events Consumed

| Event Type | Source Layer | Handler | Action |
|------------|--------------|---------|--------|
| config.updated | L01 Config Service | ConfigReloadHandler | Reload model registry and routing rules |
| agent.budget.updated | L05 Planning | BudgetHandler | Update agent token budget |
| agent.deactivated | L02 Runtime | CleanupHandler | Purge agent-specific cache entries |

---

## 5. Data Model

### 5.1 Owned Entities

| Entity | Description | Storage Type | Retention |
|--------|-------------|--------------|-----------|
| CacheEntry | Cached prompt/response pair with embedding | Redis (hot) + SQLite (persistent) | 24h default, configurable |
| RateLimitState | Token bucket state per agent/model | Redis | Session duration + 1h |
| ProviderHealth | Circuit breaker and health metrics | Redis | 1h sliding window |
| QueuedRequest | Requests awaiting processing | Redis | Until deadline or processed |
| CostRecord | Token usage and cost per request | L01 Event Store | Per L01 retention policy |

### 5.2 Entity Schemas

#### 5.2.1 CacheEntry

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-system.internal/schemas/l04/cache-entry.schema.json",
  "title": "Cache Entry",
  "type": "object",
  "properties": {
    "cache_key": {
      "type": "string",
      "description": "SHA-256 hash of normalized prompt"
    },
    "embedding": {
      "type": "array",
      "items": { "type": "number" },
      "description": "1536-dimensional embedding vector"
    },
    "prompt_hash": {
      "type": "string",
      "description": "Hash for exact-match lookup"
    },
    "category": {
      "type": "string",
      "enum": ["factual_qa", "code_generation", "creative_writing", "summarization", "default"]
    },
    "response": {
      "type": "object",
      "properties": {
        "content": { "type": "string" },
        "tool_calls": {
          "type": "array",
          "items": { "$ref": "#/$defs/tool_call" }
        },
        "structured_output": { "type": "object" },
        "model": { "type": "string" },
        "provider": { "type": "string" }
      },
      "required": ["content", "model", "provider"]
    },
    "usage": {
      "type": "object",
      "properties": {
        "prompt_tokens": { "type": "integer" },
        "completion_tokens": { "type": "integer" }
      }
    },
    "created_at": { "type": "string", "format": "date-time" },
    "expires_at": { "type": "string", "format": "date-time" },
    "hit_count": { "type": "integer", "default": 0 }
  },
  "required": ["cache_key", "embedding", "prompt_hash", "response", "created_at", "expires_at"],
  "$defs": {
    "tool_call": {
      "type": "object",
      "properties": {
        "id": { "type": "string" },
        "name": { "type": "string" },
        "arguments": { "type": "object" }
      }
    }
  },
  "_schema_metadata": {
    "version": "1.0.0",
    "layer": "l04-model-gateway"
  }
}
```

#### 5.2.2 RateLimitState

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-system.internal/schemas/l04/rate-limit-state.schema.json",
  "title": "Rate Limit State",
  "type": "object",
  "properties": {
    "key": {
      "type": "string",
      "pattern": "^ratelimit:[^:]+:[^:]+$",
      "description": "Format: ratelimit:{agent_did}:{model_id}"
    },
    "tokens_remaining": {
      "type": "number",
      "description": "Current token count in bucket"
    },
    "requests_remaining": {
      "type": "integer",
      "description": "Current request count in bucket"
    },
    "last_refill": {
      "type": "string",
      "format": "date-time",
      "description": "Timestamp of last token refill"
    },
    "tier": {
      "type": "string",
      "enum": ["free", "standard", "premium", "unlimited"]
    },
    "window_start": {
      "type": "string",
      "format": "date-time"
    }
  },
  "required": ["key", "tokens_remaining", "requests_remaining", "last_refill", "tier"],
  "_schema_metadata": {
    "version": "1.0.0",
    "layer": "l04-model-gateway"
  }
}
```

#### 5.2.3 ProviderHealth

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-system.internal/schemas/l04/provider-health.schema.json",
  "title": "Provider Health",
  "type": "object",
  "properties": {
    "provider_id": { "type": "string" },
    "endpoint": { "type": "string", "format": "uri" },
    "circuit_state": {
      "type": "string",
      "enum": ["closed", "open", "half_open"]
    },
    "failure_count": {
      "type": "integer",
      "minimum": 0
    },
    "success_count": {
      "type": "integer",
      "minimum": 0,
      "description": "Successes in half-open state"
    },
    "last_failure": {
      "type": "string",
      "format": "date-time"
    },
    "last_success": {
      "type": "string",
      "format": "date-time"
    },
    "circuit_opened_at": {
      "type": "string",
      "format": "date-time"
    },
    "latency_p50_ms": { "type": "integer" },
    "latency_p99_ms": { "type": "integer" },
    "error_rate_1m": {
      "type": "number",
      "minimum": 0,
      "maximum": 1
    },
    "requests_1m": { "type": "integer" }
  },
  "required": ["provider_id", "circuit_state", "failure_count"],
  "_schema_metadata": {
    "version": "1.0.0",
    "layer": "l04-model-gateway"
  }
}
```

#### 5.2.4 QueuedRequest

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-system.internal/schemas/l04/queued-request.schema.json",
  "title": "Queued Request",
  "type": "object",
  "properties": {
    "queue_id": { "type": "string", "format": "uuid" },
    "request_id": { "type": "string" },
    "priority": {
      "type": "integer",
      "minimum": 1,
      "maximum": 5
    },
    "enqueued_at": { "type": "string", "format": "date-time" },
    "deadline": { "type": "string", "format": "date-time" },
    "attempt_count": {
      "type": "integer",
      "default": 0
    },
    "last_error": { "type": "string" },
    "request": {
      "type": "object",
      "description": "Serialized InferenceRequest"
    }
  },
  "required": ["queue_id", "request_id", "priority", "enqueued_at", "deadline", "request"],
  "_schema_metadata": {
    "version": "1.0.0",
    "layer": "l04-model-gateway"
  }
}
```

### 5.3 Data Flows

```
+-----------------------------------------------------------------------+
|                        INFERENCE DATA FLOW                             |
+-----------------------------------------------------------------------+

     Consumer Layer (L02/L05/L06)
              |
              | InferenceRequest
              v
     +------------------+
     | Request Validator|
     +------------------+
              |
              | Validated Request
              v
     +------------------+     +-------------------+
     | DID Resolution   |<--->| L01 DID Registry  |
     +------------------+     +-------------------+
              |
              | Agent Identity
              v
     +------------------+     +-------------------+
     | ABAC Check       |<--->| L01 Policy Engine |
     +------------------+     +-------------------+
              |
              | Authorized Request
              v
     +------------------+     +-------------------+
     | Rate Limiter     |<--->| Redis (L01)       |
     +------------------+     +-------------------+
              |
              | Rate OK
              v
     +------------------+     +-------------------+
     | Cache Lookup     |<--->| Redis + SQLite    |
     +------------------+     +-------------------+
              |
      +-------+-------+
      |               |
 Cache Hit       Cache Miss
      |               |
      v               v
 Return        +------------------+     +-------------------+
 Cached        | Routing Engine   |<--->| Model Registry    |
 Response      +------------------+     +-------------------+
                      |
                      | Routing Decision
                      v
              +------------------+     +-------------------+
              | Provider Adapter |---->| External Provider |
              +------------------+     +-------------------+
                      |
                      | Provider Response
                      v
              +------------------+
              | Token Counter    |
              +------------------+
                      |
                      | Usage Metrics
                      v
              +------------------+     +-------------------+
              | Cache Writer     |---->| Redis + SQLite    |
              +------------------+     +-------------------+
                      |
                      | Cached
                      v
              +------------------+     +-------------------+
              | Event Publisher  |---->| L01 Event Store   |
              +------------------+     +-------------------+
                      |
                      | InferenceResponse
                      v
              Consumer Layer
```

---

## 6. Integration with Data Layer

### 6.1 Data Layer Services Used

| Service | Component | Usage Pattern |
|---------|-----------|---------------|
| Event Store (L1) | Event Publisher | Append-only write of model.* events for audit and analytics |
| DID Registry (L0) | Request Validator | Resolve agent DID to verify identity and retrieve capabilities |
| Storage - Redis (L2) | Rate Limiter, Cache | Distributed counters, hot cache with TTL |
| Storage - SQLite (L2) | Semantic Cache | Persistent cache with sqlite-vec for vector similarity |
| Configuration Service (L9) | Model Registry | Hot-reload model definitions and routing rules |
| ABAC Policy Engine (L7) | Request Validator | Authorize agent access to specific models |
| Audit Log | All Components | Record all inference requests for compliance |

### 6.2 Shared Patterns

| Pattern | Data Layer Reference | L04 Usage |
|---------|---------------------|-----------|
| Event Sourcing | Phase 1, Section 1.1 | All model requests/responses stored as immutable events in Event Store |
| CQRS | Phase 1, Section 1.4 | Separate write path (inference) from read path (analytics queries) |
| Agent Identity | Phase 1, Section 1.2 | Every request attributed to agent via DID; credentials validated per session |
| ABAC/OPA | Phase 7, Section 7.1 | Model access controlled by OPA policies evaluating agent capabilities |
| Circuit Breaker | Phase 8, Section 8.1 | Circuit breaker pattern for provider failover matches L01 coordination patterns |
| Configuration Hot-Reload | Phase 11, Section 11.2 | Model registry subscribes to config.updated events for zero-downtime updates |

### 6.3 Identity Integration

L04 integrates with L01's DID-based identity system:

**Request Authentication Flow:**
```
1. Consumer sends InferenceRequest with agent_did
2. L04 calls L01 DID Registry to resolve DID document
3. DID document contains:
   - Public key for credential verification
   - Service endpoints
   - Capability manifest reference
4. L04 validates request signature against public key
5. L04 retrieves capability manifest
6. L04 passes (agent_did, capabilities, requested_model) to ABAC engine
7. ABAC returns allow/deny decision
8. On allow: proceed with inference
   On deny: return E4003 (Unauthorized Model Access)
```

**Capability-Based Model Access:**
```
# Example OPA policy for model access
package l04.model_access

default allow = false

allow {
    input.agent_capabilities[_] == "inference:premium"
    input.requested_model.tier == "premium"
}

allow {
    input.agent_capabilities[_] == "inference:standard"
    input.requested_model.tier in ["standard", "free"]
}

allow {
    input.agent_capabilities[_] == "inference:free"
    input.requested_model.tier == "free"
}
```

### 6.4 Event Store Integration

L04 publishes events to L01 Event Store following Phase 1 patterns:

**Event Publishing Contract:**
```python
from typing import Protocol
from dataclasses import dataclass

@dataclass
class ModelEvent:
    event_id: str
    event_type: str
    timestamp: str
    version: str
    agent_did: str
    correlation_id: str  # Links related events
    payload: dict

class EventPublisher(Protocol):
    async def publish(self, event: ModelEvent) -> None:
        """
        Publish event to L01 Event Store.
        
        Guarantees:
        - At-least-once delivery
        - Ordered within agent_did partition
        
        Failure handling:
        - Buffer locally on Event Store unavailability
        - Retry with exponential backoff
        - Alert after 3 failed attempts
        """
        ...
```

**Event Correlation:**
All events for a single inference request share a `correlation_id` (the `request_id`), enabling end-to-end tracing:

```
model.request.submitted (request_id=abc123)
    -> model.cache.miss (request_id=abc123)
    -> model.request.routed (request_id=abc123)
    -> model.response.received (request_id=abc123)
    -> model.cost.incurred (request_id=abc123)
```

### 6.5 Configuration Service Integration

L04 loads configuration from L01 Configuration Service (Phase 11):

**Configuration Files:**

| File | Schema | Reload Trigger |
|------|--------|----------------|
| config/l04/models.json | l04/model-registry.schema.json | config.updated event |
| config/l04/routing-rules.json | l04/routing-rules.schema.json | config.updated event |
| config/l04/cache-config.json | l04/cache-config.schema.json | config.updated event |
| config/l04/rate-limits.json | l04/rate-limits.schema.json | config.updated event |
| config/l04/providers.json | l04/providers.schema.json | Requires restart (secrets) |

**Hot-Reload Pattern:**
```python
class ConfigWatcher:
    def __init__(self, config_service: ConfigService):
        self.config_service = config_service
        self.current_version = None
        
    async def watch(self):
        async for event in self.config_service.subscribe("config.updated"):
            if event.payload.path.startswith("config/l04/"):
                await self.reload_config(event.payload.path)
    
    async def reload_config(self, path: str):
        new_config = await self.config_service.get(path)
        # Validate against schema
        validate(new_config, self.get_schema(path))
        # Atomic swap
        self.apply_config(path, new_config)
        logger.info(f"Reloaded {path}")
```

### 6.6 Storage Integration

**Redis Usage (via L01 Storage Service):**

| Purpose | Key Pattern | TTL | Operations |
|---------|-------------|-----|------------|
| Rate Limit Counters | ratelimit:{agent_did}:{model_id} | 1h | HGET, HSET, HINCRBY |
| Hot Cache | cache:hot:{cache_key} | 1h | GET, SET, DEL |
| Circuit Breaker | circuit:{provider_id} | none | HGET, HSET |
| Request Queue | queue:{priority} | none | ZADD, ZRANGEBYSCORE, ZREM |
| Provider Latency | latency:{provider_id} | 1h | LPUSH, LTRIM, LRANGE |

**SQLite Usage (via L01 Storage Service):**

| Table | Purpose | Indexes |
|-------|---------|---------|
| cache_entries | Persistent semantic cache | cache_key (unique), expires_at |
| cache_vectors | sqlite-vec virtual table | embedding (vector) |

**Vector Search Query:**
```sql
-- Find similar cache entries using sqlite-vec
SELECT 
    e.cache_key,
    e.response,
    vec_distance_cosine(v.embedding, ?) as distance
FROM cache_entries e
JOIN cache_vectors v ON e.cache_key = v.cache_key
WHERE 
    e.expires_at > datetime('now')
    AND distance < (1 - ?)  -- similarity threshold
ORDER BY distance ASC
LIMIT 1;
```

## 7. Reliability and Scalability

### 7.1 Scaling Model

L04 components scale independently based on distinct bottlenecks:

| Component | Scaling Trigger | Strategy | State Handling |
|-----------|-----------------|----------|----------------|
| Gateway Pods | Request latency > 200ms p99 | HPA (CPU/custom metrics) | Stateless |
| Semantic Cache | Cache miss latency > 50ms | Sharded by cache key hash | Redis Cluster |
| Rate Limiter | Counter operations > 10K/s | Distributed across pods | Redis atomic ops |
| Request Queue | Queue depth > 1000 | Partitioned by priority | Redis Sorted Sets |
| Health Monitor | Single leader, passive replicas | Leader election | Redis lease |

**Horizontal Pod Autoscaler Configuration:**

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: model-gateway
  namespace: model-gateway
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: model-gateway
  minReplicas: 3
  maxReplicas: 50
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Pods
      pods:
        metric:
          name: gateway_request_queue_depth
        target:
          type: AverageValue
          averageValue: "100"
    - type: External
      external:
        metric:
          name: gateway_request_latency_p99_ms
        target:
          type: Value
          value: "200"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
        - type: Percent
          value: 100
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
```

### 7.2 High Availability

**Deployment Topology:**

```
+------------------------------------------------------------------+
|                     KUBERNETES CLUSTER                            |
|                                                                   |
|  Zone A                    Zone B                    Zone C       |
|  +------------------+     +------------------+     +----------------+
|  | model-gateway-0  |     | model-gateway-1  |     | model-gateway-2|
|  | (active)         |     | (active)         |     | (active)       |
|  +------------------+     +------------------+     +----------------+
|          |                        |                        |
|          +------------------------+------------------------+
|                                   |
|                           +---------------+
|                           | Redis Cluster |
|                           | (6 nodes,     |
|                           |  3 primaries) |
|                           +---------------+
|                                   |
|          +------------------------+------------------------+
|          |                        |                        |
|  +----------------+      +----------------+      +----------------+
|  | Redis Primary  |      | Redis Primary  |      | Redis Primary  |
|  | (shard 0)      |      | (shard 1)      |      | (shard 2)      |
|  | + Replica      |      | + Replica      |      | + Replica      |
|  +----------------+      +----------------+      +----------------+
|                                                                   |
+------------------------------------------------------------------+
```

**High Availability Requirements:**

| Component | Availability Target | Recovery Time | Recovery Point |
|-----------|---------------------|---------------|----------------|
| Gateway Service | 99.9% (8.76h/year) | < 30 seconds | N/A (stateless) |
| Semantic Cache | 99.5% | < 5 minutes | 1 hour (warm cache rebuild) |
| Rate Limiter | 99.9% | < 10 seconds | Real-time (Redis sync) |
| Model Registry | 99.9% | < 30 seconds | Configuration reload |

**Pod Anti-Affinity:**

```yaml
affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchLabels:
            app: model-gateway
        topologyKey: topology.kubernetes.io/zone
```

**Pod Disruption Budget:**

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: model-gateway-pdb
  namespace: model-gateway
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: model-gateway
```

### 7.3 Circuit Breaker Pattern

L04 implements circuit breakers for each provider to prevent cascading failures:

**Circuit Breaker States:**

```
                    +--------+
                    | CLOSED |<------------------------+
                    +--------+                         |
                         |                             |
        failure_count >= threshold                     |
                         |                      success_count >= success_threshold
                         v                             |
                    +--------+                         |
                    | OPEN   |--- cooldown_elapsed --->+
                    +--------+                         |
                         |                             |
                   cooldown_timer                      |
                         |                             |
                         v                             |
                    +-----------+                      |
                    | HALF-OPEN |----------------------+
                    +-----------+      success
                         |
                       failure
                         |
                         v
                    +--------+
                    | OPEN   |
                    +--------+
```

**Circuit Breaker Configuration:**

| Parameter | Default | Per-Provider Override | Description |
|-----------|---------|----------------------|-------------|
| failure_threshold | 5 | Yes | Consecutive failures before opening |
| cooldown_seconds | 60 | Yes | Time in OPEN state before testing |
| success_threshold | 3 | Yes | Successes in HALF-OPEN to close |
| monitored_errors | [429, 500, 502, 503, 504] | Yes | HTTP status codes as failures |
| timeout_ms | 30000 | Yes | Request timeout (counts as failure) |

**Circuit Breaker State Schema:**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-system.internal/schemas/l04/circuit-breaker-state.schema.json",
  "title": "Circuit Breaker State",
  "type": "object",
  "properties": {
    "provider_id": { "type": "string" },
    "state": { 
      "type": "string", 
      "enum": ["CLOSED", "OPEN", "HALF_OPEN"] 
    },
    "failure_count": { "type": "integer", "minimum": 0 },
    "success_count": { "type": "integer", "minimum": 0 },
    "last_failure_time": { "type": "string", "format": "date-time" },
    "last_success_time": { "type": "string", "format": "date-time" },
    "state_changed_at": { "type": "string", "format": "date-time" },
    "next_retry_time": { 
      "type": "string", 
      "format": "date-time",
      "description": "When OPEN, earliest time to attempt HALF_OPEN transition"
    }
  },
  "required": ["provider_id", "state", "failure_count", "state_changed_at"]
}
```

**Redis Storage Pattern:**

```
Key: circuit:{provider_id}
Type: HASH
Fields:
  - state: "CLOSED" | "OPEN" | "HALF_OPEN"
  - failure_count: integer
  - success_count: integer
  - state_changed_at: ISO timestamp
  - next_retry_time: ISO timestamp

Operations:
  - HGETALL circuit:{provider_id}  -- Read state
  - HSET circuit:{provider_id} state OPEN failure_count 5 ...  -- Atomic update
  - WATCH + MULTI/EXEC for state transitions
```

### 7.4 Failover Strategy

**Sequential Fallback with Priority:**

```
InferenceRequest
     |
     v
[1. Check primary provider circuit]
     |
     +-- OPEN --> [Skip to fallback 1]
     |
     +-- CLOSED/HALF_OPEN
             |
             v
        [Send to primary]
             |
             +-- Success --> Return response
             |
             +-- Failure --> [Update circuit, try fallback 1]
                                   |
                                   v
                              [Check fallback 1 circuit]
                                   |
                                   +-- OPEN --> [Skip to fallback 2]
                                   |
                                   +-- CLOSED/HALF_OPEN
                                           |
                                           v
                                      [Send to fallback 1]
                                           |
                                           ...
                                           |
                                           v
                              [All providers exhausted]
                                           |
                                           v
                              Return E4001 (No Providers Available)
```

**Provider Priority Configuration:**

```json
{
  "fallback_chains": {
    "claude-sonnet-4": {
      "primary": "anthropic",
      "fallbacks": ["azure-openai", "aws-bedrock"],
      "max_fallback_attempts": 2
    },
    "gpt-4o": {
      "primary": "openai",
      "fallbacks": ["azure-openai"],
      "max_fallback_attempts": 1
    }
  }
}
```

### 7.5 Performance Targets

| Metric | Target | Measurement Point | Degradation Threshold |
|--------|--------|-------------------|----------------------|
| Request latency (gateway overhead) | < 20ms p50, < 50ms p99 | Gateway ingress to provider egress | > 100ms p99 |
| Cache lookup latency | < 10ms p50, < 30ms p99 | Cache query start to result | > 50ms p99 |
| Semantic embedding latency | < 50ms p50, < 100ms p99 | Embedding API call duration | > 200ms p99 |
| Rate limit check | < 2ms p99 | Redis operation duration | > 10ms p99 |
| Throughput (per pod) | 500 req/s sustained | Request completion rate | < 300 req/s |
| Cache hit ratio | > 25% (semantic + exact) | Hits / Total requests | < 15% |

**Load Shedding:**

When gateway pods reach 90% CPU or queue depth exceeds 5000:

1. Reject new BATCH priority requests with E4007 (Service Overloaded)
2. At 95% CPU: Reject INTERACTIVE priority requests
3. At 98% CPU: Reject all requests; emit alert

### 7.6 Capacity Planning

**Per-Pod Resource Requirements:**

| Resource | Request | Limit | Rationale |
|----------|---------|-------|-----------|
| CPU | 1000m | 4000m | Handle request bursts |
| Memory | 2Gi | 4Gi | Connection pools, buffering |
| Ephemeral storage | 1Gi | 5Gi | Response streaming buffers |

**Cluster Capacity Formula:**

```
Required Pods = ceil(
  (Peak RPS * Avg Latency in seconds * Safety Factor) / Throughput per Pod
)

Example:
  Peak RPS = 10,000
  Avg Latency = 2s (LLM response time)
  Safety Factor = 1.5
  Throughput per Pod = 500 RPS

  Required Pods = ceil((10000 * 2 * 1.5) / 500) = 60 pods
```

**Redis Cluster Sizing:**

| Metric | Calculation | Baseline |
|--------|-------------|----------|
| Memory per rate limit entry | 200 bytes | 1M agents * 10 models = 2GB |
| Memory per cache entry | 5KB (embedding + response) | 100K entries = 500MB |
| Operations per second | 2 ops/request | 10K RPS = 20K Redis ops/s |

## 8. Security

### 8.1 Trust Boundaries

```
+-----------------------------------------------------------------------+
|                                                                        |
|    UNTRUSTED                           SEMI-TRUSTED                    |
|    +-------------------+               +-----------------------------+ |
|    | External LLM      |               | Consumer Layers             | |
|    | Providers         |               | (L02, L05, L06, L07)        | |
|    | - Anthropic       |               | - Authenticated via mTLS    | |
|    | - OpenAI          |               | - Authorized via ABAC       | |
|    | - Azure           |               +-----------------------------+ |
|    +-------------------+                         |                     |
|            ^                                     v                     |
|            |                                                           |
|    +-------+--------------------------------------------+              |
|    |                                                    |              |
|    |     TRUST BOUNDARY 1: Provider Egress             |              |
|    |     - TLS 1.3 mandatory                           |              |
|    |     - Certificate validation                      |              |
|    |     - Request signing (where supported)           |              |
|    |                                                    |              |
|    +----------------------------------------------------+              |
|            |                                     ^                     |
|            v                                     |                     |
|    +----------------------------------------------------+              |
|    |                                                    |              |
|    |     TRUSTED: Model Gateway (L04)                  |              |
|    |     - Secrets from Vault                          |              |
|    |     - Network isolated namespace                  |              |
|    |     - Pod security context enforced               |              |
|    |                                                    |              |
|    +----------------------------------------------------+              |
|            |                                     ^                     |
|            v                                     |                     |
|    +-------+--------------------------------------------+              |
|    |                                                    |              |
|    |     TRUST BOUNDARY 2: Consumer Ingress            |              |
|    |     - mTLS authentication                         |              |
|    |     - Agent DID validation                        |              |
|    |     - Capability-based authorization              |              |
|    |                                                    |              |
|    +----------------------------------------------------+              |
|                                                                        |
|    TRUSTED                                                             |
|    +-------------------+      +--------------------+                   |
|    | L01 Data Layer    |      | L00 Infrastructure |                   |
|    | - Event Store     |      | - Vault (secrets)  |                   |
|    | - Config Service  |      | - Network policies |                   |
|    | - DID Registry    |      | - Observability    |                   |
|    +-------------------+      +--------------------+                   |
|                                                                        |
+-----------------------------------------------------------------------+
```

### 8.2 Authentication

#### 8.2.1 Consumer Authentication (Inbound)

Consumer layers authenticate to L04 via mTLS with certificates issued by L00 Certificate Manager.

**Certificate Requirements:**

| Attribute | Requirement |
|-----------|-------------|
| Issuer | L00 Internal CA (Cert Manager) |
| Subject CN | {layer-id}.agent-system.internal |
| SAN | DNS:{service-name}.{namespace}.svc.cluster.local |
| Key Algorithm | ECDSA P-256 |
| Validity | 90 days (auto-renewed at 60 days) |
| Extended Key Usage | clientAuth, serverAuth |

**mTLS Configuration:**

```yaml
# Envoy sidecar configuration
tls_context:
  common_tls_context:
    tls_certificate_sds_secret_configs:
      - name: model-gateway-cert
        sds_config:
          api_config_source:
            api_type: GRPC
            grpc_services:
              - envoy_grpc:
                  cluster_name: sds-grpc-cluster
    validation_context_sds_secret_config:
      name: trusted-ca
      sds_config:
        api_config_source:
          api_type: GRPC
  require_client_certificate: true
```

#### 8.2.2 Provider Authentication (Outbound)

L04 authenticates to external providers using API keys stored in HashiCorp Vault.

**Secret Access Pattern:**

```
+----------------+     +--------------------+     +----------------+
| Model Gateway  |---->| External Secrets   |---->| HashiCorp      |
| Pod            |     | Operator           |     | Vault          |
+----------------+     +--------------------+     +----------------+
        |                                                |
        | Mounted as file:                               |
        | /secrets/anthropic/api-key                     |
        | /secrets/openai/api-key                        |
        | /secrets/azure/api-key                         |
        v                                                v
+----------------+                              +----------------+
| Secret         |                              | Vault Path     |
| anthropic-     |<-----------------------------| secret/data/   |
| api-key        |     Sync every 1h           | llm-providers/ |
+----------------+                              | anthropic      |
                                                +----------------+
```

**ExternalSecret Definition:**

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: llm-provider-anthropic
  namespace: model-gateway
  labels:
    layer: l04
    provider: anthropic
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: ClusterSecretStore
  target:
    name: anthropic-api-key
    creationPolicy: Owner
  data:
    - secretKey: api-key
      remoteRef:
        key: secret/data/llm-providers/anthropic
        property: api_key
```

**Key Rotation Procedure:**

1. Vault operator updates key in Vault
2. External Secrets Operator detects change (1h refresh)
3. Kubernetes Secret updated atomically
4. Gateway pod file watcher detects change (fsnotify)
5. Provider adapter reloads key without restart
6. Event published: `security.key.rotated`

### 8.3 Authorization

#### 8.3.1 ABAC Policy Framework

L04 uses Attribute-Based Access Control via L01 ABAC service with OPA policies.

**Authorization Flow:**

```
InferenceRequest
      |
      v
[1. Extract agent_did from mTLS cert]
      |
      v
[2. Query L01 DID Registry for agent capabilities]
      |
      v
[3. Build authorization context]
      |
      +-- agent_did: "did:agent:abc123"
      +-- agent_capabilities: ["inference:standard", "vision:enabled"]
      +-- requested_model: "claude-sonnet-4"
      +-- model_tier: "premium"
      +-- estimated_cost_cents: 15
      |
      v
[4. Evaluate OPA policy]
      |
      +-- ALLOW --> Proceed with inference
      +-- DENY --> Return E4003 (Unauthorized Model Access)
```

**OPA Policy for Model Access:**

```rego
package l04.model_access

import future.keywords.if
import future.keywords.in

default allow := false

# Rule 1: Premium tier requires premium capability
allow if {
    input.requested_model.tier == "premium"
    "inference:premium" in input.agent_capabilities
}

# Rule 2: Standard tier allows standard or lower
allow if {
    input.requested_model.tier in ["standard", "free"]
    "inference:standard" in input.agent_capabilities
}

# Rule 3: Free tier only allows free models
allow if {
    input.requested_model.tier == "free"
    "inference:free" in input.agent_capabilities
}

# Rule 4: Vision capability required for vision models
allow if {
    "vision" in input.requested_model.capabilities
    "vision:enabled" in input.agent_capabilities
    base_tier_allowed
}

# Helper: Check base tier is allowed
base_tier_allowed if {
    input.requested_model.tier == "premium"
    "inference:premium" in input.agent_capabilities
}

base_tier_allowed if {
    input.requested_model.tier in ["standard", "free"]
    "inference:standard" in input.agent_capabilities
}

base_tier_allowed if {
    input.requested_model.tier == "free"
    "inference:free" in input.agent_capabilities
}

# Rule 5: Budget check
deny_reasons[msg] if {
    input.agent_budget_remaining_cents < input.estimated_cost_cents
    msg := "Insufficient budget for request"
}
```

**Authorization Resources:**

| Resource Type | Actions | Attributes |
|---------------|---------|------------|
| model | inference, batch_inference | tier, capabilities, provider |
| cache | read, write, invalidate | namespace |
| quota | read, modify | agent_did, project_id |
| registry | read, modify | provider |

#### 8.3.2 Per-Request Budget Enforcement

```python
@dataclass
class BudgetCheckResult:
    allowed: bool
    remaining_cents: float
    estimated_cost_cents: float
    reason: Optional[str]

async def check_budget(
    agent_did: str,
    estimated_cost_cents: float
) -> BudgetCheckResult:
    """
    Verify agent has sufficient budget for request.
    
    Budget state stored in L01 Storage Service (Redis).
    Budget limits configured in L01 Configuration Service.
    """
    budget_key = f"budget:{agent_did}"
    
    # Atomic read of current budget
    current = await redis.hget(budget_key, "remaining_cents")
    limit = await config_service.get(f"budgets/{agent_did}/daily_limit_cents")
    
    if current is None:
        # Initialize budget for new agent
        current = limit
        await redis.hset(budget_key, "remaining_cents", current)
    
    if float(current) < estimated_cost_cents:
        return BudgetCheckResult(
            allowed=False,
            remaining_cents=float(current),
            estimated_cost_cents=estimated_cost_cents,
            reason="Insufficient daily budget"
        )
    
    return BudgetCheckResult(
        allowed=True,
        remaining_cents=float(current),
        estimated_cost_cents=estimated_cost_cents,
        reason=None
    )
```

### 8.4 Data Protection

#### 8.4.1 Data Classification

| Data Type | Classification | Handling |
|-----------|----------------|----------|
| Provider API keys | SECRET | Vault storage, never logged |
| Agent credentials (mTLS certs) | CONFIDENTIAL | Cert Manager, rotated |
| Inference requests | INTERNAL | Logged with PII redaction |
| Inference responses | INTERNAL | Cached encrypted, logged with PII redaction |
| Cache embeddings | INTERNAL | Stored in encrypted Redis |
| Usage metrics | INTERNAL | No PII, aggregatable |

#### 8.4.2 Encryption

**At Rest:**

| Data Store | Encryption | Key Management |
|------------|------------|----------------|
| Redis (cache, counters) | AES-256-GCM | Vault Transit Engine |
| SQLite (vector cache) | SQLCipher | Key from Vault |
| Kubernetes Secrets | etcd encryption | Cloud KMS |

**In Transit:**

| Connection | Protocol | Certificate |
|------------|----------|-------------|
| Consumer -> Gateway | mTLS (TLS 1.3) | L00 Internal CA |
| Gateway -> Provider | TLS 1.3 | Provider CA (verified) |
| Gateway -> Redis | mTLS (TLS 1.2+) | L00 Internal CA |
| Gateway -> L01 Services | mTLS (TLS 1.3) | L00 Internal CA |

### 8.5 Threat Model

| Threat | Attack Vector | Mitigation | Residual Risk |
|--------|---------------|------------|---------------|
| T1: API Key Theft | Memory dump, log scraping | Vault storage, no logging of keys | Low |
| T2: Prompt Injection | Malicious user input | L05 responsibility (out of scope for L04) | N/A |
| T3: Response Cache Poisoning | Inject false responses | Cache key includes agent_did; integrity check | Low |
| T4: Rate Limit Bypass | Forged agent identity | mTLS with cert validation | Low |
| T5: Provider Impersonation | DNS hijacking | Certificate pinning, TLS verification | Low |
| T6: Denial of Service | Request flooding | Rate limiting, circuit breakers | Medium |
| T7: Unauthorized Model Access | Capability escalation | ABAC enforcement, audit logging | Low |
| T8: Cost Attack | Excessive token generation | Budget enforcement, max_tokens limits | Low |
| T9: Cache Timing Attack | Infer cache contents | Fixed-time similarity search | Low |
| T10: Credential Compromise | Stolen/leaked API keys used maliciously | Anomaly detection, usage monitoring (P1-003) | Medium |

**Credential Compromise Detection (P1-003):**

Detect potentially compromised provider API keys through usage anomaly detection.

```python
@dataclass
class UsageAnomaly:
    anomaly_type: str
    severity: str  # "warning", "critical"
    details: dict
    detected_at: datetime

class CredentialAnomalyDetector:
    """
    Detect anomalies indicating potential credential compromise.
    
    Monitors:
    - Usage patterns inconsistent with registered agents
    - Requests from unexpected source IPs
    - Provider-reported unauthorized access alerts
    - Unusual model access patterns
    """
    
    async def analyze_request(
        self, 
        request: InferenceRequest,
        source_context: RequestContext
    ) -> Optional[UsageAnomaly]:
        """Check request against baseline behavior."""
        
        # Check agent usage baseline
        baseline = await self.get_agent_baseline(request.agent_did)
        
        # Anomaly: Usage spike
        if await self._is_usage_spike(request.agent_did):
            return UsageAnomaly(
                anomaly_type="usage_spike",
                severity="warning",
                details={"current_rate": self._get_rate(request.agent_did)},
                detected_at=datetime.utcnow()
            )
        
        # Anomaly: Unusual model access
        if request.routing_hints.preferred_model not in baseline.typical_models:
            return UsageAnomaly(
                anomaly_type="unusual_model",
                severity="warning",
                details={"requested": request.routing_hints.preferred_model},
                detected_at=datetime.utcnow()
            )
        
        return None
    
    async def check_provider_alerts(self) -> list[ProviderAlert]:
        """Poll providers for security alerts about our credentials."""
        alerts = []
        for provider in self.providers:
            if hasattr(self.adapters[provider], 'get_security_alerts'):
                provider_alerts = await self.adapters[provider].get_security_alerts()
                alerts.extend(provider_alerts)
        return alerts
```

**Security Event:**

```json
{
  "event_type": "security.credential.compromise_suspected",
  "severity": "critical",
  "provider": "anthropic",
  "anomaly_type": "usage_spike",
  "details": {
    "baseline_rpm": 100,
    "current_rpm": 5000,
    "duration_minutes": 5
  },
  "recommended_action": "review_and_rotate"
}
```

**Response Procedures:**

| Anomaly Type | Detection | Response |
|--------------|-----------|----------|
| Usage spike (>10x baseline) | Real-time | Alert + manual review |
| Unusual model access | Real-time | Log + alert if repeated |
| Provider security alert | Poll every 5m | Immediate key rotation |
| IP anomaly | Real-time | Block + investigate |

**Threat Response Procedures:**

| Threat | Detection | Response |
|--------|-----------|----------|
| T1 | Vault audit log anomaly | Rotate all provider keys immediately |
| T3 | Cache integrity check failure | Purge affected cache entries; alert |
| T6 | Rate limit threshold breach | Block source; scale horizontally |
| T7 | Repeated authorization failures | Alert; consider temporary suspension |
| T8 | Budget exhaustion spike | Alert; investigate agent behavior |

### 8.6 Network Security

**CiliumNetworkPolicy for Egress:**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: model-gateway-egress
  namespace: model-gateway
spec:
  endpointSelector:
    matchLabels:
      app: model-gateway
  egress:
    # Allow DNS resolution
    - toEndpoints:
        - matchLabels:
            k8s:io.kubernetes.pod.namespace: kube-system
            k8s-app: kube-dns
      toPorts:
        - ports:
            - port: "53"
              protocol: UDP
    # Allow LLM provider APIs
    - toFQDNs:
        - matchName: "api.anthropic.com"
        - matchName: "api.openai.com"
        - matchPattern: "*.openai.azure.com"
        - matchName: "generativelanguage.googleapis.com"
        - matchName: "bedrock-runtime.*.amazonaws.com"
      toPorts:
        - ports:
            - port: "443"
              protocol: TCP
    # Allow L01 services (cluster internal)
    - toEndpoints:
        - matchLabels:
            k8s:io.kubernetes.pod.namespace: data-layer
      toPorts:
        - ports:
            - port: "6379"
              protocol: TCP
            - port: "8080"
              protocol: TCP
            - port: "9090"
              protocol: TCP
    # Allow L00 observability
    - toEndpoints:
        - matchLabels:
            k8s:io.kubernetes.pod.namespace: observability
      toPorts:
        - ports:
            - port: "9090"
              protocol: TCP
            - port: "4317"
              protocol: TCP
```

**CiliumNetworkPolicy for Ingress:**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: model-gateway-ingress
  namespace: model-gateway
spec:
  endpointSelector:
    matchLabels:
      app: model-gateway
  ingress:
    # Allow from consumer layers only
    - fromEndpoints:
        - matchLabels:
            layer: l02  # Agent Runtime
        - matchLabels:
            layer: l05  # Planning
        - matchLabels:
            layer: l06  # Evaluation
        - matchLabels:
            layer: l07  # Learning
      toPorts:
        - ports:
            - port: "8080"
              protocol: TCP
            - port: "50051"
              protocol: TCP
    # Allow Prometheus scraping
    - fromEndpoints:
        - matchLabels:
            k8s:io.kubernetes.pod.namespace: observability
            app: prometheus
      toPorts:
        - ports:
            - port: "9090"
              protocol: TCP
```

### 8.7 Pod Security

**Pod Security Context:**

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  seccompProfile:
    type: RuntimeDefault
  capabilities:
    drop:
      - ALL

containers:
  - name: model-gateway
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
          - ALL
    volumeMounts:
      - name: tmp
        mountPath: /tmp
      - name: secrets
        mountPath: /secrets
        readOnly: true

volumes:
  - name: tmp
    emptyDir:
      sizeLimit: 100Mi
  - name: secrets
    projected:
      sources:
        - secret:
            name: anthropic-api-key
        - secret:
            name: openai-api-key
```

### 8.8 Audit Logging

All security-relevant events are published to L01 Event Store for compliance and forensics.

**Audit Event Types:**

| Event | Trigger | Data Captured |
|-------|---------|---------------|
| security.auth.success | Successful mTLS handshake | agent_did, cert_fingerprint, timestamp |
| security.auth.failure | Failed authentication | source_ip, failure_reason, timestamp |
| security.authz.denied | ABAC policy denial | agent_did, resource, action, policy_reason |
| security.key.accessed | Provider key read | provider, accessor, timestamp |
| security.key.rotated | Key rotation detected | provider, timestamp |
| security.budget.exhausted | Budget limit hit | agent_did, limit, attempted_cost |
| security.rate.limited | Rate limit exceeded | agent_did, model_id, limit, actual |

**Audit Event Schema:**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-system.internal/schemas/l04/audit-event.schema.json",
  "title": "Security Audit Event",
  "type": "object",
  "properties": {
    "event_id": { "type": "string", "format": "uuid" },
    "event_type": { "type": "string", "pattern": "^security\\." },
    "timestamp": { "type": "string", "format": "date-time" },
    "severity": { 
      "type": "string", 
      "enum": ["INFO", "WARN", "ERROR", "CRITICAL"] 
    },
    "actor": {
      "type": "object",
      "properties": {
        "agent_did": { "type": "string" },
        "source_ip": { "type": "string" },
        "cert_fingerprint": { "type": "string" }
      }
    },
    "action": { "type": "string" },
    "resource": { "type": "string" },
    "outcome": { 
      "type": "string", 
      "enum": ["SUCCESS", "FAILURE", "DENIED"] 
    },
    "details": { "type": "object" }
  },
  "required": ["event_id", "event_type", "timestamp", "severity", "outcome"]
}
```

## 9. Observability

### 9.1 Metrics

L04 exposes metrics via Prometheus format on port 9090.

**OpenTelemetry GenAI Semantic Conventions (P2-001):**

L04 adopts OpenTelemetry GenAI semantic conventions for attribute naming, enabling interoperability with observability tools.

| Legacy L04 Attribute | OTel GenAI Convention | Notes |
|---------------------|----------------------|-------|
| prompt_tokens | gen_ai.usage.prompt_tokens | Standard |
| completion_tokens | gen_ai.usage.completion_tokens | Standard |
| model | gen_ai.request.model | Standard |
| provider | gen_ai.system | Standard |
| temperature | gen_ai.request.temperature | Standard |
| max_tokens | gen_ai.request.max_tokens | Standard |
| cost_cents | gen_ai.usage.cost | Custom extension |
| cache_hit | gen_ai.cache.hit | Custom extension |

#### 9.1.1 Metric Inventory

**Request Metrics:**

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| gateway_request_total | Counter | agent_did, model, provider, status, cache_hit | Total inference requests |
| gateway_request_duration_seconds | Histogram | agent_did, model, provider, phase | Request latency by phase |
| gateway_request_queue_depth | Gauge | priority | Current queue depth per priority |
| gateway_active_requests | Gauge | provider | In-flight requests per provider |

**Token Metrics:**

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| gateway_tokens_total | Counter | agent_did, model, provider, direction | Total tokens (input/output) |
| gateway_tokens_cached | Counter | agent_did, model | Tokens served from cache |
| gateway_cost_cents_total | Counter | agent_did, model, provider | Total cost in cents |
| gateway_cost_saved_cents_total | Counter | agent_did, model | Cost saved via caching |

**Cache Metrics:**

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| gateway_cache_hits_total | Counter | cache_type | Hits (exact, semantic) |
| gateway_cache_misses_total | Counter | cache_type | Misses |
| gateway_cache_latency_seconds | Histogram | cache_type, operation | Cache operation latency |
| gateway_cache_size_bytes | Gauge | cache_type | Current cache size |
| gateway_cache_entries | Gauge | cache_type | Current entry count |

**Provider Metrics:**

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| gateway_provider_latency_seconds | Histogram | provider, model | Provider response latency |
| gateway_provider_errors_total | Counter | provider, model, error_code | Provider errors |
| gateway_provider_circuit_state | Gauge | provider | Circuit state (0=closed, 1=open, 2=half-open) |
| gateway_provider_rate_limit_remaining | Gauge | provider | Remaining provider rate limit |

**Rate Limit Metrics:**

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| gateway_rate_limit_checks_total | Counter | agent_did, model, result | Rate limit check results |
| gateway_rate_limit_remaining | Gauge | agent_did, model | Remaining quota |
| gateway_rate_limit_rejects_total | Counter | agent_did, model | Rejected due to rate limit |
| gateway_adaptive_limit_factor | Gauge | provider | Adaptive rate limit factor 0.0-1.0 (P2-002) |

**Streaming-Specific Metrics (P3-003):**

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| gateway_time_to_first_token_seconds | Histogram | provider, model | Time until first token received |
| gateway_inter_token_latency_seconds | Histogram | provider, model | Latency between consecutive tokens |
| gateway_streaming_tokens_per_second | Gauge | provider, model | Current token throughput for streaming |
| gateway_streaming_duration_seconds | Histogram | provider, model | Total streaming response duration |

**Safety Metrics (P1-001/P1-002):**

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| gateway_safety_detections_total | Counter | filter_type, pattern_type, action | Safety filter detections |
| gateway_safety_blocks_total | Counter | filter_type | Requests blocked by safety filters |

#### 9.1.2 Metric Labels

| Label | Cardinality | Values |
|-------|-------------|--------|
| agent_did | High | Agent DID (hash for cardinality control) |
| model | Medium | claude-sonnet-4, gpt-4o, etc. |
| provider | Low | anthropic, openai, azure, google, local |
| status | Low | success, error, timeout, rate_limited |
| cache_type | Low | exact, semantic, none |
| phase | Low | validate, cache_lookup, route, provider, response |
| priority | Low | 1, 2, 3, 4, 5 |
| direction | Low | input, output |
| filter_type | Low | prompt, response |

**Cardinality Control:**

For high-cardinality labels (agent_did), use hash bucketing:

```python
def bucket_agent_did(agent_did: str, buckets: int = 1000) -> str:
    """Reduce cardinality by hashing to fixed buckets."""
    hash_value = int(hashlib.md5(agent_did.encode()).hexdigest()[:8], 16)
    return f"bucket_{hash_value % buckets:04d}"
```

#### 9.1.3 Prometheus Recording Rules

```yaml
groups:
  - name: l04_model_gateway
    interval: 30s
    rules:
      # Request rate by provider
      - record: gateway:request_rate:by_provider
        expr: sum(rate(gateway_request_total[5m])) by (provider)
      
      # Error rate by provider
      - record: gateway:error_rate:by_provider
        expr: |
          sum(rate(gateway_request_total{status=~"error|timeout"}[5m])) by (provider)
          /
          sum(rate(gateway_request_total[5m])) by (provider)
      
      # Cache hit ratio
      - record: gateway:cache_hit_ratio
        expr: |
          sum(rate(gateway_cache_hits_total[5m]))
          /
          (sum(rate(gateway_cache_hits_total[5m])) + sum(rate(gateway_cache_misses_total[5m])))
      
      # P99 latency by provider
      - record: gateway:latency_p99:by_provider
        expr: histogram_quantile(0.99, sum(rate(gateway_provider_latency_seconds_bucket[5m])) by (provider, le))
      
      # Cost rate (cents per minute)
      - record: gateway:cost_rate_cents_per_minute
        expr: sum(rate(gateway_cost_cents_total[5m])) * 60
      
      # Streaming metrics (P3-003)
      - record: gateway:ttft_p50:by_provider
        expr: histogram_quantile(0.50, sum(rate(gateway_time_to_first_token_seconds_bucket[5m])) by (provider, le))
      
      - record: gateway:ttft_p99:by_provider
        expr: histogram_quantile(0.99, sum(rate(gateway_time_to_first_token_seconds_bucket[5m])) by (provider, le))
      
      # Token throughput
      - record: gateway:token_throughput:by_direction
        expr: sum(rate(gateway_tokens_total[5m])) by (direction)
```

### 9.2 Traces

L04 emits OpenTelemetry traces to L00 observability stack (Tempo).

#### 9.2.1 Span Structure

```
gateway.request (root span)
  |
  +-- gateway.validate
  |     +-- Attributes: request_id, agent_did, model_requested
  |
  +-- gateway.cache.lookup
  |     +-- Attributes: cache_type, cache_key, hit
  |
  +-- gateway.route
  |     +-- Attributes: strategy, candidates_count, selected_provider
  |
  +-- gateway.provider.request (if cache miss)
  |     +-- Attributes: provider, model, prompt_tokens
  |     +-- Links: provider trace context (if propagated)
  |
  +-- gateway.response.process
  |     +-- Attributes: completion_tokens, cost_cents
  |
  +-- gateway.cache.write (if cacheable)
        +-- Attributes: cache_key, ttl_seconds
```

#### 9.2.2 Trace Context Propagation

```python
from opentelemetry import trace
from opentelemetry.propagate import inject, extract

class TracingMiddleware:
    def __init__(self, tracer: trace.Tracer):
        self.tracer = tracer
    
    async def handle_request(
        self, 
        request: InferenceRequest,
        carrier: dict
    ) -> InferenceResponse:
        # Extract context from incoming request
        ctx = extract(carrier)
        
        with self.tracer.start_as_current_span(
            "gateway.request",
            context=ctx,
            kind=trace.SpanKind.SERVER
        ) as span:
            span.set_attribute("request_id", request.request_id)
            span.set_attribute("agent_did", request.agent_did)
            span.set_attribute("model_requested", 
                               request.routing_hints.get("preferred_model", "auto"))
            
            # Process request...
            response = await self._process(request, span)
            
            span.set_attribute("cache_hit", response.cache_hit)
            span.set_attribute("provider", response.provider)
            span.set_attribute("total_tokens", response.usage["total_tokens"])
            span.set_attribute("cost_cents", response.cost_cents)
            
            return response
    
    async def _call_provider(
        self, 
        request: InferenceRequest,
        provider: str,
        parent_span: trace.Span
    ):
        with self.tracer.start_as_current_span(
            "gateway.provider.request",
            kind=trace.SpanKind.CLIENT
        ) as span:
            span.set_attribute("provider", provider)
            
            # Inject context for provider (if supported)
            headers = {}
            inject(headers)
            
            response = await self.adapters[provider].send_request(
                request, 
                headers=headers
            )
            
            return response
```

#### 9.2.3 Trace Sampling

| Scenario | Sampling Rate | Rationale |
|----------|---------------|-----------|
| Errors | 100% | All errors traced for debugging |
| High latency (> p99) | 100% | Performance investigation |
| Cache hits | 1% | Low-value, high-volume |
| Normal requests | 10% | Baseline visibility |

**Sampling Configuration:**

```yaml
# OpenTelemetry Collector config
processors:
  tail_sampling:
    decision_wait: 10s
    num_traces: 100000
    policies:
      - name: errors
        type: status_code
        status_code:
          status_codes:
            - ERROR
      - name: high_latency
        type: latency
        latency:
          threshold_ms: 5000
      - name: cache_hits
        type: string_attribute
        string_attribute:
          key: cache_hit
          values:
            - "true"
        sample_rate: 0.01
      - name: default
        type: probabilistic
        probabilistic:
          sampling_percentage: 10
```

### 9.3 Logs

L04 emits structured JSON logs to stdout, collected by L00 observability (Loki).

#### 9.3.1 Log Format

```json
{
  "timestamp": "2026-01-04T12:34:56.789Z",
  "level": "INFO",
  "logger": "l04.gateway",
  "message": "Inference request completed",
  "request_id": "req-abc123",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "agent_did": "did:agent:xyz789",
  "provider": "anthropic",
  "model": "claude-sonnet-4",
  "cache_hit": false,
  "latency_ms": 1234,
  "prompt_tokens": 500,
  "completion_tokens": 200,
  "cost_cents": 1.05
}
```

#### 9.3.2 Log Levels

| Level | Usage | Examples |
|-------|-------|----------|
| ERROR | Failures requiring attention | Provider errors, authorization failures |
| WARN | Degraded operation | Rate limit approached, fallback triggered |
| INFO | Normal operations | Request completed, cache hit, config reload |
| DEBUG | Detailed debugging | Routing decisions, cache key generation |

#### 9.3.3 Sensitive Data Handling

**Redaction Rules:**

| Field | Handling | Rationale |
|-------|----------|-----------|
| API keys | Never logged | Security |
| Prompt content | Hash only (first 8 chars of SHA-256) | Privacy |
| Response content | Hash only | Privacy |
| agent_did | Logged as-is | Required for debugging |
| Embeddings | Not logged | Volume |

```python
def redact_for_logging(request: InferenceRequest) -> dict:
    """Prepare request for logging with sensitive data redacted."""
    prompt_hash = hashlib.sha256(
        json.dumps(request.logical_prompt.messages).encode()
    ).hexdigest()[:8]
    
    return {
        "request_id": request.request_id,
        "agent_did": request.agent_did,
        "prompt_hash": prompt_hash,
        "required_capabilities": request.required_capabilities,
        "latency_class": request.latency_class.value,
        "token_budget": {
            "max_input": request.token_budget.max_input_tokens,
            "max_output": request.token_budget.max_output_tokens,
            "max_cost_cents": request.token_budget.max_cost_cents
        }
    }
```

**Full Request/Response Capture Mode (P2-005):**

Optional full content capture for debugging and fine-tuning data collection.

| Capture Mode | Behavior | Use Case |
|--------------|----------|----------|
| hash_only | Default; hash content for correlation | Production |
| full_encrypted | AES-256 encrypted full content | Debugging, compliance |
| none | No content logged | High-sensitivity |

**Configuration:**

```yaml
logging:
  capture_mode: "hash_only"  # hash_only | full_encrypted | none
  full_capture:
    enabled: false
    encryption_key_ref: "vault:secret/logging/capture-key"
    retention_days: 7
    allowed_agents: []  # Empty = all agents
    excluded_agents: []
    max_content_size_bytes: 1048576  # 1MB
```

**Encrypted Capture Implementation:**

```python
from cryptography.fernet import Fernet
from dataclasses import dataclass

@dataclass
class CapturedContent:
    request_id: str
    encrypted_prompt: bytes
    encrypted_response: bytes
    encryption_key_id: str
    captured_at: datetime
    retention_until: datetime

class FullCaptureLogger:
    """
    Capture full request/response content with encryption.
    
    Security controls:
    - Content encrypted with AES-256 before storage
    - Encryption key from Vault, separate from other secrets
    - Automatic retention enforcement
    - Access audit logging
    """
    
    def __init__(self, config: CaptureConfig):
        self.config = config
        self.fernet = Fernet(self._load_key())
    
    async def capture(
        self, 
        request: InferenceRequest, 
        response: InferenceResponse
    ) -> Optional[str]:
        """Capture and encrypt request/response if enabled."""
        if not self._should_capture(request):
            return None
        
        prompt_bytes = json.dumps(
            request.logical_prompt.to_dict()
        ).encode()
        response_bytes = json.dumps({
            "content": response.content,
            "tool_calls": response.tool_calls
        }).encode()
        
        captured = CapturedContent(
            request_id=request.request_id,
            encrypted_prompt=self.fernet.encrypt(prompt_bytes),
            encrypted_response=self.fernet.encrypt(response_bytes),
            encryption_key_id=self.current_key_id,
            captured_at=datetime.utcnow(),
            retention_until=datetime.utcnow() + timedelta(
                days=self.config.retention_days
            )
        )
        
        await self.storage.store(captured)
        return captured.request_id
    
    def _should_capture(self, request: InferenceRequest) -> bool:
        """Determine if request should be captured."""
        if not self.config.enabled:
            return False
        if request.agent_did in self.config.excluded_agents:
            return False
        if self.config.allowed_agents and \
           request.agent_did not in self.config.allowed_agents:
            return False
        return True
```

**Access Control:**

- Captured content accessible only via separate admin API
- All access logged to audit trail
- Decryption requires separate permission: `capture:decrypt`

### 9.4 Health Checks

#### 9.4.1 Health Endpoints

| Endpoint | Purpose | Frequency |
|----------|---------|-----------|
| /health/live | Kubernetes liveness probe | 10s |
| /health/ready | Kubernetes readiness probe | 5s |
| /health/startup | Kubernetes startup probe | 5s |
| /health/deep | Comprehensive health check | On-demand |

#### 9.4.2 Health Check Implementation

```python
from enum import Enum
from dataclasses import dataclass
from typing import List

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

@dataclass
class ComponentHealth:
    name: str
    status: HealthStatus
    latency_ms: float
    message: Optional[str] = None

@dataclass
class HealthResponse:
    status: HealthStatus
    components: List[ComponentHealth]
    version: str
    uptime_seconds: float

class HealthChecker:
    async def liveness(self) -> HealthResponse:
        """Basic liveness: process is running."""
        return HealthResponse(
            status=HealthStatus.HEALTHY,
            components=[],
            version=self.version,
            uptime_seconds=self.uptime()
        )
    
    async def readiness(self) -> HealthResponse:
        """Readiness: can accept traffic."""
        components = []
        
        # Check Redis connection
        redis_health = await self._check_redis()
        components.append(redis_health)
        
        # Check at least one provider is available
        provider_health = await self._check_providers()
        components.append(provider_health)
        
        # Check config loaded
        config_health = await self._check_config()
        components.append(config_health)
        
        overall = self._aggregate_status(components)
        
        return HealthResponse(
            status=overall,
            components=components,
            version=self.version,
            uptime_seconds=self.uptime()
        )
    
    async def deep(self) -> HealthResponse:
        """Deep health: all dependencies checked."""
        components = await asyncio.gather(
            self._check_redis(),
            self._check_sqlite(),
            self._check_providers(),
            self._check_config(),
            self._check_event_store(),
            self._check_abac()
        )
        
        overall = self._aggregate_status(components)
        
        return HealthResponse(
            status=overall,
            components=list(components),
            version=self.version,
            uptime_seconds=self.uptime()
        )
    
    def _aggregate_status(self, components: List[ComponentHealth]) -> HealthStatus:
        if any(c.status == HealthStatus.UNHEALTHY for c in components):
            return HealthStatus.UNHEALTHY
        if any(c.status == HealthStatus.DEGRADED for c in components):
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY
```

**Kubernetes Probes:**

```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 10
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 5
  failureThreshold: 2

startupProbe:
  httpGet:
    path: /health/startup
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
  failureThreshold: 30
```

### 9.5 Alerts

#### 9.5.1 Alert Definitions

**Critical Alerts (Page Immediately):**

| Alert | Condition | For | Severity |
|-------|-----------|-----|----------|
| GatewayDown | up{job="model-gateway"} == 0 | 1m | critical |
| AllProvidersUnavailable | sum(gateway_provider_circuit_state == 0) == 0 | 2m | critical |
| HighErrorRate | gateway:error_rate:by_provider > 0.1 | 5m | critical |
| BudgetExhaustion | sum(rate(gateway_rate_limit_rejects_total{reason="budget"}[5m])) > 100 | 5m | critical |

**Warning Alerts (Notify):**

| Alert | Condition | For | Severity |
|-------|-----------|-----|----------|
| HighLatency | gateway:latency_p99:by_provider > 10 | 5m | warning |
| LowCacheHitRate | gateway:cache_hit_ratio < 0.15 | 15m | warning |
| ProviderDegraded | gateway_provider_circuit_state == 2 | 5m | warning |
| QueueBacklog | gateway_request_queue_depth > 1000 | 5m | warning |
| RateLimitApproaching | gateway_rate_limit_remaining < 100 | 5m | warning |
| HighCostRate | gateway:cost_rate_cents_per_minute > 100 | 10m | warning |

#### 9.5.2 Alertmanager Configuration

```yaml
groups:
  - name: l04_model_gateway_alerts
    rules:
      - alert: GatewayDown
        expr: up{job="model-gateway"} == 0
        for: 1m
        labels:
          severity: critical
          layer: l04
        annotations:
          summary: "Model Gateway is down"
          description: "No Model Gateway pods are responding to health checks"
          runbook_url: "https://runbooks.internal/l04/gateway-down"
      
      - alert: AllProvidersUnavailable
        expr: sum(gateway_provider_circuit_state == 0) == 0
        for: 2m
        labels:
          severity: critical
          layer: l04
        annotations:
          summary: "All LLM providers have open circuits"
          description: "No LLM providers are available - all circuit breakers are open"
          runbook_url: "https://runbooks.internal/l04/all-providers-down"
      
      - alert: HighErrorRate
        expr: gateway:error_rate:by_provider > 0.1
        for: 5m
        labels:
          severity: critical
          layer: l04
        annotations:
          summary: "High error rate for provider {{ $labels.provider }}"
          description: "Error rate is {{ $value | humanizePercentage }} for {{ $labels.provider }}"
          runbook_url: "https://runbooks.internal/l04/high-error-rate"
      
      - alert: HighLatency
        expr: gateway:latency_p99:by_provider > 10
        for: 5m
        labels:
          severity: warning
          layer: l04
        annotations:
          summary: "High latency for provider {{ $labels.provider }}"
          description: "P99 latency is {{ $value }}s for {{ $labels.provider }}"
          runbook_url: "https://runbooks.internal/l04/high-latency"
      
      - alert: LowCacheHitRate
        expr: gateway:cache_hit_ratio < 0.15
        for: 15m
        labels:
          severity: warning
          layer: l04
        annotations:
          summary: "Low semantic cache hit rate"
          description: "Cache hit rate is {{ $value | humanizePercentage }}"
          runbook_url: "https://runbooks.internal/l04/low-cache-hit"
```

### 9.6 Dashboards

#### 9.6.1 Gateway Overview Dashboard

```
+-----------------------------------------------------------------------+
|                    MODEL GATEWAY OVERVIEW                              |
+-----------------------------------------------------------------------+
|                                                                        |
|  Request Rate         Error Rate           Cache Hit Ratio             |
|  +---------------+    +---------------+    +---------------+           |
|  |   1,234/s     |    |    0.5%       |    |    28.3%      |           |
|  |  [========>]  |    |  [=>         ]|    |  [=====>     ]|           |
|  +---------------+    +---------------+    +---------------+           |
|                                                                        |
|  Latency (P99)        Active Requests      Cost Rate                   |
|  +---------------+    +---------------+    +---------------+           |
|  |   1.23s       |    |     156       |    |  $0.45/min    |           |
|  +---------------+    +---------------+    +---------------+           |
|                                                                        |
+-----------------------------------------------------------------------+
|  PROVIDER STATUS                                                       |
|  +-------------------------------------------------------------+      |
|  | Provider   | Status | Circuit | Latency P99 | Error % | RPS |      |
|  |------------|--------|---------|-------------|---------|-----|      |
|  | anthropic  | [OK]   | CLOSED  |    0.9s     |  0.1%   | 500 |      |
|  | openai     | [OK]   | CLOSED  |    1.2s     |  0.3%   | 300 |      |
|  | azure      | [WARN] | HALF    |    2.1s     |  2.1%   | 100 |      |
|  +-------------------------------------------------------------+      |
|                                                                        |
+-----------------------------------------------------------------------+
|  TRAFFIC BY MODEL (Last Hour)                     COST BY AGENT        |
|  +-----------------------------+    +-----------------------------+   |
|  |    claude-sonnet-4: 45%     |    |  agent-001: $12.34          |   |
|  |    gpt-4o:          30%     |    |  agent-002: $8.76           |   |
|  |    claude-haiku:    15%     |    |  agent-003: $5.43           |   |
|  |    other:           10%     |    |  ...                         |   |
|  +-----------------------------+    +-----------------------------+   |
|                                                                        |
+-----------------------------------------------------------------------+
```

#### 9.6.2 Dashboard Queries

**Request Rate by Provider:**
```promql
sum(rate(gateway_request_total[5m])) by (provider)
```

**P99 Latency Trend:**
```promql
histogram_quantile(0.99, 
  sum(rate(gateway_request_duration_seconds_bucket{phase="total"}[5m])) by (le)
)
```

**Cost by Agent (Top 10):**
```promql
topk(10, 
  sum(increase(gateway_cost_cents_total[1h])) by (agent_did)
)
```

**Cache Hit Ratio Trend:**
```promql
sum(rate(gateway_cache_hits_total[5m])) 
/ 
(sum(rate(gateway_cache_hits_total[5m])) + sum(rate(gateway_cache_misses_total[5m])))
```

## 10. Configuration

### 10.1 Configuration Schema

L04 configuration is managed through L01 Configuration Service with JSON Schema validation.

#### 10.1.1 Configuration Files

| File | Purpose | Schema | Hot Reload |
|------|---------|--------|------------|
| config/l04/models.json | Model registry definitions | l04/model-registry.schema.json | Yes |
| config/l04/providers.json | Provider configurations | l04/providers.schema.json | No (secrets) |
| config/l04/routing-rules.json | Routing strategy configuration | l04/routing-rules.schema.json | Yes |
| config/l04/cache-config.json | Cache parameters | l04/cache-config.schema.json | Yes |
| config/l04/rate-limits.json | Rate limit policies | l04/rate-limits.schema.json | Yes |
| config/l04/circuit-breaker.json | Circuit breaker settings | l04/circuit-breaker.schema.json | Yes |

#### 10.1.2 Model Registry Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-system.internal/schemas/l04/model-registry.schema.json",
  "title": "Model Registry Configuration",
  "type": "object",
  "properties": {
    "version": { "type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$" },
    "models": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "model_id": { "type": "string" },
          "provider": { 
            "type": "string",
            "enum": ["anthropic", "openai", "azure", "google", "bedrock", "local"]
          },
          "display_name": { "type": "string" },
          "capabilities": {
            "type": "array",
            "items": {
              "type": "string",
              "enum": ["text", "vision", "tool_use", "streaming", "json_mode", 
                       "function_calling", "long_context", "code", "embedding"]
            }
          },
          "context_window": { "type": "integer", "minimum": 1024 },
          "max_output_tokens": { "type": "integer", "minimum": 1 },
          "cost_per_1m_input_tokens": { "type": "number", "minimum": 0 },
          "cost_per_1m_output_tokens": { "type": "number", "minimum": 0 },
          "cost_per_1m_cached_input_tokens": { "type": "number", "minimum": 0 },
          "rate_limit_rpm": { "type": "integer", "minimum": 1 },
          "rate_limit_tpm": { "type": "integer", "minimum": 1 },
          "latency_p50_ms": { "type": "integer" },
          "latency_p99_ms": { "type": "integer" },
          "tier": {
            "type": "string",
            "enum": ["free", "standard", "premium"]
          },
          "status": {
            "type": "string",
            "enum": ["active", "deprecated", "disabled"]
          }
        },
        "required": ["model_id", "provider", "capabilities", "context_window", 
                     "cost_per_1m_input_tokens", "cost_per_1m_output_tokens", 
                     "tier", "status"]
      }
    }
  },
  "required": ["version", "models"]
}
```

#### 10.1.3 Provider Configuration Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-system.internal/schemas/l04/providers.schema.json",
  "title": "Provider Configuration",
  "type": "object",
  "properties": {
    "version": { "type": "string" },
    "providers": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "provider_id": { "type": "string" },
          "display_name": { "type": "string" },
          "base_url": { "type": "string", "format": "uri" },
          "api_version": { "type": "string" },
          "secret_ref": {
            "type": "object",
            "properties": {
              "name": { "type": "string" },
              "key": { "type": "string" }
            },
            "required": ["name", "key"]
          },
          "timeout_ms": { "type": "integer", "minimum": 1000, "default": 30000 },
          "max_retries": { "type": "integer", "minimum": 0, "default": 3 },
          "retry_delay_ms": { "type": "integer", "minimum": 100, "default": 1000 },
          "headers": {
            "type": "object",
            "additionalProperties": { "type": "string" }
          },
          "enabled": { "type": "boolean", "default": true }
        },
        "required": ["provider_id", "base_url", "secret_ref"]
      }
    }
  },
  "required": ["version", "providers"]
}
```

#### 10.1.4 Routing Rules Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-system.internal/schemas/l04/routing-rules.schema.json",
  "title": "Routing Rules Configuration",
  "type": "object",
  "properties": {
    "version": { "type": "string" },
    "default_strategy": {
      "type": "string",
      "enum": ["capability_first", "cost_optimized", "latency_optimized", "provider_pinned"],
      "default": "capability_first"
    },
    "fallback_chains": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "primary": { "type": "string" },
          "fallbacks": {
            "type": "array",
            "items": { "type": "string" }
          },
          "max_fallback_attempts": { "type": "integer", "minimum": 0, "default": 2 }
        },
        "required": ["primary"]
      }
    },
    "latency_class_thresholds": {
      "type": "object",
      "properties": {
        "realtime_max_p99_ms": { "type": "integer", "default": 2000 },
        "interactive_max_p99_ms": { "type": "integer", "default": 5000 }
      }
    },
    "agent_overrides": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "strategy": { "type": "string" },
          "preferred_provider": { "type": "string" },
          "cost_multiplier": { "type": "number", "minimum": 0, "maximum": 10 }
        }
      }
    }
  },
  "required": ["version", "default_strategy"]
}
```

#### 10.1.5 Cache Configuration Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-system.internal/schemas/l04/cache-config.schema.json",
  "title": "Cache Configuration",
  "type": "object",
  "properties": {
    "version": { "type": "string" },
    "semantic_cache": {
      "type": "object",
      "properties": {
        "enabled": { "type": "boolean", "default": true },
        "embedding_model": { "type": "string", "default": "text-embedding-3-small" },
        "embedding_dimensions": { "type": "integer", "default": 1536 },
        "default_similarity_threshold": { "type": "number", "minimum": 0, "maximum": 1, "default": 0.85 },
        "category_thresholds": {
          "type": "object",
          "additionalProperties": { "type": "number", "minimum": 0, "maximum": 1 }
        },
        "ttl_seconds": { "type": "integer", "minimum": 60, "default": 86400 },
        "max_entries": { "type": "integer", "minimum": 1000, "default": 100000 },
        "max_prompt_tokens_for_embedding": { "type": "integer", "default": 8000 }
      }
    },
    "exact_cache": {
      "type": "object",
      "properties": {
        "enabled": { "type": "boolean", "default": true },
        "ttl_seconds": { "type": "integer", "minimum": 60, "default": 3600 },
        "max_entries": { "type": "integer", "minimum": 100, "default": 10000 }
      }
    },
    "hot_cache": {
      "type": "object",
      "properties": {
        "enabled": { "type": "boolean", "default": true },
        "ttl_seconds": { "type": "integer", "minimum": 60, "default": 3600 },
        "max_memory_mb": { "type": "integer", "minimum": 100, "default": 512 }
      }
    }
  },
  "required": ["version"]
}
```

#### 10.1.6 Rate Limits Configuration Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-system.internal/schemas/l04/rate-limits.schema.json",
  "title": "Rate Limits Configuration",
  "type": "object",
  "properties": {
    "version": { "type": "string" },
    "tiers": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "requests_per_minute": { "type": "integer", "minimum": 1 },
          "tokens_per_minute": { "type": "integer", "minimum": 1 },
          "daily_budget_cents": { "type": "integer", "minimum": 0 },
          "burst_multiplier": { "type": "number", "minimum": 1, "default": 2 }
        },
        "required": ["requests_per_minute", "tokens_per_minute"]
      }
    },
    "agent_overrides": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "tier": { "type": "string" },
          "custom_limits": {
            "type": "object",
            "properties": {
              "requests_per_minute": { "type": "integer" },
              "tokens_per_minute": { "type": "integer" },
              "daily_budget_cents": { "type": "integer" }
            }
          }
        }
      }
    },
    "global_limits": {
      "type": "object",
      "properties": {
        "max_concurrent_requests": { "type": "integer", "default": 10000 },
        "max_queue_depth": { "type": "integer", "default": 5000 }
      }
    }
  },
  "required": ["version", "tiers"]
}
```

#### 10.1.7 Circuit Breaker Configuration Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-system.internal/schemas/l04/circuit-breaker.schema.json",
  "title": "Circuit Breaker Configuration",
  "type": "object",
  "properties": {
    "version": { "type": "string" },
    "defaults": {
      "type": "object",
      "properties": {
        "failure_threshold": { "type": "integer", "minimum": 1, "default": 5 },
        "success_threshold": { "type": "integer", "minimum": 1, "default": 3 },
        "cooldown_seconds": { "type": "integer", "minimum": 10, "default": 60 },
        "monitored_status_codes": {
          "type": "array",
          "items": { "type": "integer" },
          "default": [429, 500, 502, 503, 504]
        },
        "timeout_ms": { "type": "integer", "minimum": 1000, "default": 30000 }
      }
    },
    "provider_overrides": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "failure_threshold": { "type": "integer" },
          "success_threshold": { "type": "integer" },
          "cooldown_seconds": { "type": "integer" },
          "timeout_ms": { "type": "integer" }
        }
      }
    }
  },
  "required": ["version", "defaults"]
}
```

### 10.2 Environment Variables

Environment variables provide deployment-specific overrides. Configuration Service values take precedence for runtime behavior.

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| L04_LOG_LEVEL | Log verbosity | INFO | No |
| L04_LOG_FORMAT | Log format (json, text) | json | No |
| L04_GRPC_PORT | gRPC server port | 50051 | No |
| L04_HTTP_PORT | HTTP server port | 8080 | No |
| L04_METRICS_PORT | Prometheus metrics port | 9090 | No |
| L04_REDIS_URL | Redis connection URL | - | Yes |
| L04_SQLITE_PATH | SQLite database path | /data/cache.db | No |
| L04_CONFIG_SERVICE_URL | L01 Configuration Service URL | - | Yes |
| L04_EVENT_STORE_URL | L01 Event Store URL | - | Yes |
| L04_DID_REGISTRY_URL | L01 DID Registry URL | - | Yes |
| L04_ABAC_URL | L01 ABAC service URL | - | Yes |
| L04_OTEL_ENDPOINT | OpenTelemetry collector endpoint | - | No |
| L04_SECRETS_PATH | Path to mounted secrets | /secrets | No |

**Environment Variable Validation:**

```python
from pydantic import BaseSettings, AnyUrl

class GatewaySettings(BaseSettings):
    log_level: str = "INFO"
    log_format: str = "json"
    grpc_port: int = 50051
    http_port: int = 8080
    metrics_port: int = 9090
    
    redis_url: AnyUrl
    sqlite_path: str = "/data/cache.db"
    
    config_service_url: AnyUrl
    event_store_url: AnyUrl
    did_registry_url: AnyUrl
    abac_url: AnyUrl
    
    otel_endpoint: Optional[AnyUrl] = None
    secrets_path: str = "/secrets"
    
    class Config:
        env_prefix = "L04_"
        case_sensitive = False
```

### 10.3 Feature Flags

Feature flags enable gradual rollout and kill-switch capabilities.

| Flag | Description | Default | Scope |
|------|-------------|---------|-------|
| semantic_cache_enabled | Enable semantic cache lookups | true | Global |
| exact_cache_enabled | Enable exact match cache | true | Global |
| streaming_enabled | Enable streaming responses | true | Global |
| prompt_compression_enabled | Enable optional prompt compression | false | Per-agent |
| batch_api_enabled | Enable batch API routing | true | Global |
| provider_prompt_caching | Use provider prompt caching features | true | Per-provider |
| new_routing_algorithm | Use new routing algorithm (A/B test) | false | Percentage |

**Feature Flag Schema:**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-system.internal/schemas/l04/feature-flags.schema.json",
  "title": "Feature Flags",
  "type": "object",
  "properties": {
    "version": { "type": "string" },
    "flags": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "enabled": { "type": "boolean" },
          "scope": {
            "type": "string",
            "enum": ["global", "per_agent", "per_provider", "percentage"]
          },
          "percentage": { "type": "number", "minimum": 0, "maximum": 100 },
          "agent_allowlist": {
            "type": "array",
            "items": { "type": "string" }
          },
          "provider_allowlist": {
            "type": "array",
            "items": { "type": "string" }
          },
          "description": { "type": "string" }
        },
        "required": ["enabled", "scope"]
      }
    }
  },
  "required": ["version", "flags"]
}
```

**Feature Flag Evaluation:**

```python
class FeatureFlagEvaluator:
    def __init__(self, config_service: ConfigService):
        self.config_service = config_service
        self.flags = {}
        
    async def load_flags(self):
        self.flags = await self.config_service.get("config/l04/feature-flags.json")
    
    def is_enabled(
        self, 
        flag_name: str, 
        agent_did: Optional[str] = None,
        provider: Optional[str] = None
    ) -> bool:
        flag = self.flags.get("flags", {}).get(flag_name)
        if not flag:
            return False
        
        if not flag.get("enabled", False):
            return False
        
        scope = flag.get("scope", "global")
        
        if scope == "global":
            return True
        
        if scope == "per_agent" and agent_did:
            allowlist = flag.get("agent_allowlist", [])
            return agent_did in allowlist or not allowlist
        
        if scope == "per_provider" and provider:
            allowlist = flag.get("provider_allowlist", [])
            return provider in allowlist or not allowlist
        
        if scope == "percentage":
            percentage = flag.get("percentage", 0)
            # Consistent hashing for stable assignment
            hash_input = f"{flag_name}:{agent_did or ''}"
            hash_value = int(hashlib.md5(hash_input.encode()).hexdigest()[:8], 16)
            return (hash_value % 100) < percentage
        
        return False
```

### 10.4 Configuration Hot-Reload

L04 subscribes to L01 Configuration Service events for hot-reload capability.

**Hot-Reload Flow:**

```
L01 Configuration Service
         |
         | config.updated event
         v
+-------------------+
| Config Watcher    |
| - Subscribe to    |
|   config/l04/*    |
+-------------------+
         |
         v
+-------------------+
| Schema Validator  |
| - Validate against|
|   JSON Schema     |
+-------------------+
         |
         +-- Invalid --> Log error, keep current config
         |
         +-- Valid
              |
              v
+-------------------+
| Config Applicator |
| - Atomic swap     |
| - Publish event   |
+-------------------+
         |
         v
config.applied event
```

**Configuration Watcher Implementation:**

```python
class ConfigWatcher:
    def __init__(
        self, 
        config_service: ConfigService,
        schema_registry: SchemaRegistry
    ):
        self.config_service = config_service
        self.schema_registry = schema_registry
        self.current_configs: Dict[str, Any] = {}
        self.callbacks: Dict[str, List[Callable]] = {}
    
    async def start(self):
        # Initial load
        await self._load_all_configs()
        
        # Subscribe to updates
        async for event in self.config_service.subscribe("config.updated"):
            if event.payload["path"].startswith("config/l04/"):
                await self._handle_update(event.payload["path"])
    
    async def _handle_update(self, path: str):
        try:
            # Fetch new config
            new_config = await self.config_service.get(path)
            
            # Validate against schema
            schema_id = self._get_schema_for_path(path)
            schema = await self.schema_registry.get(schema_id)
            validate(new_config, schema)
            
            # Atomic swap
            old_config = self.current_configs.get(path)
            self.current_configs[path] = new_config
            
            # Notify callbacks
            for callback in self.callbacks.get(path, []):
                await callback(new_config, old_config)
            
            logger.info(f"Configuration reloaded: {path}")
            
        except ValidationError as e:
            logger.error(f"Invalid configuration for {path}: {e}")
            # Keep existing config
        except Exception as e:
            logger.error(f"Failed to reload {path}: {e}")
    
    def register_callback(self, path: str, callback: Callable):
        if path not in self.callbacks:
            self.callbacks[path] = []
        self.callbacks[path].append(callback)
```

### 10.5 Default Configuration

**models.json (Default):**

```json
{
  "version": "1.0.0",
  "models": [
    {
      "model_id": "claude-sonnet-4-20250514",
      "provider": "anthropic",
      "display_name": "Claude Sonnet 4",
      "capabilities": ["text", "vision", "tool_use", "streaming", "json_mode"],
      "context_window": 200000,
      "max_output_tokens": 64000,
      "cost_per_1m_input_tokens": 3.00,
      "cost_per_1m_output_tokens": 15.00,
      "cost_per_1m_cached_input_tokens": 0.30,
      "rate_limit_rpm": 4000,
      "rate_limit_tpm": 400000,
      "latency_p50_ms": 800,
      "latency_p99_ms": 3000,
      "tier": "premium",
      "status": "active"
    },
    {
      "model_id": "claude-haiku-3-5-20241022",
      "provider": "anthropic",
      "display_name": "Claude 3.5 Haiku",
      "capabilities": ["text", "vision", "tool_use", "streaming", "json_mode"],
      "context_window": 200000,
      "max_output_tokens": 8192,
      "cost_per_1m_input_tokens": 0.80,
      "cost_per_1m_output_tokens": 4.00,
      "cost_per_1m_cached_input_tokens": 0.08,
      "rate_limit_rpm": 4000,
      "rate_limit_tpm": 400000,
      "latency_p50_ms": 400,
      "latency_p99_ms": 1500,
      "tier": "standard",
      "status": "active"
    },
    {
      "model_id": "gpt-4o-2024-11-20",
      "provider": "openai",
      "display_name": "GPT-4o",
      "capabilities": ["text", "vision", "tool_use", "streaming", "json_mode", "function_calling"],
      "context_window": 128000,
      "max_output_tokens": 16384,
      "cost_per_1m_input_tokens": 2.50,
      "cost_per_1m_output_tokens": 10.00,
      "cost_per_1m_cached_input_tokens": 1.25,
      "rate_limit_rpm": 10000,
      "rate_limit_tpm": 30000000,
      "latency_p50_ms": 600,
      "latency_p99_ms": 2500,
      "tier": "premium",
      "status": "active"
    },
    {
      "model_id": "gpt-4o-mini-2024-07-18",
      "provider": "openai",
      "display_name": "GPT-4o Mini",
      "capabilities": ["text", "vision", "tool_use", "streaming", "json_mode", "function_calling"],
      "context_window": 128000,
      "max_output_tokens": 16384,
      "cost_per_1m_input_tokens": 0.15,
      "cost_per_1m_output_tokens": 0.60,
      "cost_per_1m_cached_input_tokens": 0.075,
      "rate_limit_rpm": 30000,
      "rate_limit_tpm": 150000000,
      "latency_p50_ms": 300,
      "latency_p99_ms": 1000,
      "tier": "standard",
      "status": "active"
    }
  ]
}
```

**rate-limits.json (Default):**

```json
{
  "version": "1.0.0",
  "tiers": {
    "free": {
      "requests_per_minute": 10,
      "tokens_per_minute": 10000,
      "daily_budget_cents": 100,
      "burst_multiplier": 1.5
    },
    "standard": {
      "requests_per_minute": 100,
      "tokens_per_minute": 100000,
      "daily_budget_cents": 1000,
      "burst_multiplier": 2.0
    },
    "premium": {
      "requests_per_minute": 1000,
      "tokens_per_minute": 1000000,
      "daily_budget_cents": 10000,
      "burst_multiplier": 3.0
    },
    "unlimited": {
      "requests_per_minute": 100000,
      "tokens_per_minute": 100000000,
      "daily_budget_cents": 0,
      "burst_multiplier": 5.0
    }
  },
  "agent_overrides": {},
  "global_limits": {
    "max_concurrent_requests": 10000,
    "max_queue_depth": 5000
  }
}
```

## 11. Implementation Guide

### 11.1 Dependencies

**Language Decision:** The Model Gateway Layer implementation uses **Python 3.11+** as the primary language. This choice aligns with the Data Layer (L01) and provides:
- Native async/await with performance improvements in 3.11
- Pattern matching for routing logic
- Improved type hints including Self type
- TaskGroup for structured concurrency

#### 11.1.1 Runtime Dependencies

| Dependency | Version | Purpose | License |
|------------|---------|---------|---------|
| Python | 3.11+ | Runtime environment | PSF |
| asyncio | stdlib | Async request handling | PSF |
| httpx | 0.27+ | Async HTTP client for provider APIs | BSD-3 |
| grpcio | 1.60+ | gRPC server and client | Apache-2.0 |
| pydantic | 2.5+ | Data validation and serialization | MIT |
| redis | 5.0+ | Cache and rate limiting backend | MIT |
| tiktoken | 0.6+ | OpenAI token counting | MIT |
| anthropic-tokenizer | 0.1+ | Anthropic token counting | Apache-2.0 |
| sqlite-vec | 0.1+ | Vector similarity search | MIT |
| prometheus-client | 0.19+ | Metrics exposition | Apache-2.0 |
| opentelemetry-sdk | 1.22+ | Distributed tracing | Apache-2.0 |
| structlog | 24.1+ | Structured logging | Apache-2.0 |
| jsonschema | 4.21+ | Configuration validation | MIT |
| cryptography | 42.0+ | mTLS certificate handling | Apache-2.0 |

#### 11.1.2 Provider SDK Dependencies

| Provider | SDK | Version | Purpose |
|----------|-----|---------|---------|
| Anthropic | anthropic | 0.40+ | Claude API client |
| OpenAI | openai | 1.50+ | GPT API client |
| Azure OpenAI | azure-ai-openai | 1.0+ | Azure-hosted OpenAI |
| Google Vertex | google-cloud-aiplatform | 1.40+ | Vertex AI models |
| Local Models | vllm | 0.4+ | Local model serving (optional) |

#### 11.1.3 Development Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| pytest | 8.0+ | Test framework |
| pytest-asyncio | 0.23+ | Async test support |
| pytest-cov | 4.1+ | Coverage reporting |
| mypy | 1.8+ | Static type checking |
| ruff | 0.2+ | Linting and formatting |
| locust | 2.23+ | Load testing |
| hypothesis | 6.100+ | Property-based testing |
| respx | 0.20+ | HTTP request mocking |

#### 11.1.4 Infrastructure Dependencies

| Dependency | Version | Provider | Purpose |
|------------|---------|----------|---------|
| Redis Cluster | 7.2+ | L00 | Cache, rate limiting, queues |
| SQLite | 3.45+ | Local | Persistent cache with vector search |
| HashiCorp Vault | 1.15+ | L00 | Secrets management |
| Kubernetes | 1.28+ | L00 | Container orchestration |
| Cilium | 1.15+ | L00 | Network policy enforcement |

### 11.2 Directory Structure

```
src/model_gateway/
|-- __init__.py
|-- main.py                      # Application entrypoint
|-- config.py                    # Configuration loading and validation
|-- exceptions.py                # Custom exception hierarchy
|
|-- components/
|   |-- __init__.py
|   |-- model_registry.py        # Model catalog and capability queries
|   |-- llm_router.py            # Request routing logic
|   |-- semantic_cache.py        # Embedding-based caching
|   |-- exact_cache.py           # Hash-based exact match cache
|   |-- rate_limiter.py          # Token bucket rate limiting
|   |-- request_queue.py         # Priority queue management
|   |-- response_processor.py    # Response normalization
|   |-- token_counter.py         # Token counting utilities
|   |-- fallback_manager.py      # Circuit breaker and failover
|   |-- health_monitor.py        # Provider health tracking
|   |-- batch_processor.py       # Batch API handling
|
|-- adapters/
|   |-- __init__.py
|   |-- base.py                  # Abstract provider adapter
|   |-- anthropic_adapter.py     # Anthropic Claude adapter
|   |-- openai_adapter.py        # OpenAI GPT adapter
|   |-- azure_adapter.py         # Azure OpenAI adapter
|   |-- google_adapter.py        # Google Vertex AI adapter
|   |-- local_adapter.py         # Local model (vLLM) adapter
|
|-- interfaces/
|   |-- __init__.py
|   |-- provided/
|   |   |-- __init__.py
|   |   |-- inference_service.py     # BC-3 inference interface
|   |   |-- registry_service.py      # Model registry queries
|   |   |-- health_service.py        # Health check endpoints
|   |-- required/
|   |   |-- __init__.py
|   |   |-- event_publisher.py       # L01 Event Store client
|   |   |-- config_service.py        # L01 Configuration Service client
|   |   |-- did_resolver.py          # L01 DID Registry client
|   |   |-- abac_client.py           # L01 ABAC/OPA client
|
|-- models/
|   |-- __init__.py
|   |-- entities.py              # Core entity definitions
|   |-- events.py                # Event payload schemas
|   |-- requests.py              # InferenceRequest and related
|   |-- responses.py             # InferenceResponse and related
|
|-- storage/
|   |-- __init__.py
|   |-- redis_client.py          # Redis connection management
|   |-- sqlite_client.py         # SQLite + sqlite-vec operations
|   |-- cache_store.py           # Cache storage abstraction
|
|-- grpc/
|   |-- __init__.py
|   |-- server.py                # gRPC server implementation
|   |-- inference_pb2.py         # Generated protobuf messages
|   |-- inference_pb2_grpc.py    # Generated gRPC stubs
|
|-- http/
|   |-- __init__.py
|   |-- server.py                # HTTP server (OpenAI-compatible)
|   |-- routes.py                # Route definitions
|   |-- middleware.py            # Auth, logging, tracing middleware
|
|-- utils/
|   |-- __init__.py
|   |-- embedding.py             # Embedding generation utilities
|   |-- hashing.py               # Prompt hashing utilities
|   |-- retry.py                 # Retry logic with backoff
|   |-- metrics.py               # Prometheus metric definitions
|   |-- tracing.py               # OpenTelemetry span helpers

tests/
|-- __init__.py
|-- conftest.py                  # Pytest fixtures
|-- unit/
|   |-- components/
|   |   |-- test_model_registry.py
|   |   |-- test_llm_router.py
|   |   |-- test_semantic_cache.py
|   |   |-- test_rate_limiter.py
|   |   |-- test_token_counter.py
|   |-- adapters/
|   |   |-- test_anthropic_adapter.py
|   |   |-- test_openai_adapter.py
|-- integration/
|   |-- test_end_to_end.py
|   |-- test_data_layer_integration.py
|   |-- test_provider_failover.py
|-- performance/
|   |-- locustfile.py
|   |-- test_throughput.py
|   |-- test_cache_performance.py

config/
|-- models.json                  # Default model registry
|-- routing-rules.json           # Default routing configuration
|-- rate-limits.json             # Default rate limit tiers
|-- cache-config.json            # Cache configuration
|-- providers.json               # Provider endpoint configuration
|-- feature-flags.json           # Feature flag defaults

schemas/
|-- l04/
|   |-- model-registry.schema.json
|   |-- routing-rules.schema.json
|   |-- cache-config.schema.json
|   |-- rate-limits.schema.json
|   |-- inference-request.schema.json
|   |-- inference-response.schema.json
|   |-- events/
|       |-- model.request.submitted.schema.json
|       |-- model.response.received.schema.json
|       |-- model.cache.hit.schema.json
|       |-- model.cost.incurred.schema.json

deploy/
|-- kubernetes/
|   |-- namespace.yaml
|   |-- deployment.yaml
|   |-- service.yaml
|   |-- hpa.yaml
|   |-- pdb.yaml
|   |-- network-policy.yaml
|   |-- external-secret.yaml
|   |-- configmap.yaml
|-- helm/
|   |-- model-gateway/
|       |-- Chart.yaml
|       |-- values.yaml
|       |-- templates/
```

### 11.3 Implementation Sequence

The implementation sequence is ordered to establish foundational components before dependent services.

#### Phase 1: Core Infrastructure (Weeks 1-2)

| Step | Component | Dependencies | Rationale |
|------|-----------|--------------|-----------|
| 1.1 | Configuration loading | jsonschema | Foundation for all component initialization |
| 1.2 | Exception hierarchy | None | Standardized error handling across components |
| 1.3 | Metrics and tracing setup | prometheus-client, opentelemetry | Required before components for observability |
| 1.4 | Redis client | redis | Cache and rate limiting backend |
| 1.5 | SQLite client | sqlite-vec | Persistent cache storage |

**Milestone 1:** Configuration, logging, and storage clients operational.

#### Phase 2: Provider Adapters (Weeks 2-3)

| Step | Component | Dependencies | Rationale |
|------|-----------|--------------|-----------|
| 2.1 | Base adapter interface | Phase 1 | Abstract contract for all providers |
| 2.2 | Token counter | tiktoken, anthropic-tokenizer | Required for all adapters |
| 2.3 | OpenAI adapter | openai SDK | Most common provider; validates base adapter design |
| 2.4 | Anthropic adapter | anthropic SDK | Primary provider for agent workloads |
| 2.5 | Azure adapter | azure-ai-openai | Enterprise deployment variant |
| 2.6 | Google adapter | google-cloud-aiplatform | Multi-cloud support |

**Milestone 2:** All provider adapters functional with streaming support.

#### Phase 3: Routing and Caching (Weeks 3-4)

| Step | Component | Dependencies | Rationale |
|------|-----------|--------------|-----------|
| 3.1 | Model registry | Configuration, Phase 1 | Foundation for routing decisions |
| 3.2 | Exact match cache | Redis client | High-hit-rate cache layer |
| 3.3 | Embedding utilities | embedding model | Required for semantic cache |
| 3.4 | Semantic cache | SQLite client, embeddings | Intelligent cache for similar prompts |
| 3.5 | LLM router | Model registry, Phase 2 adapters | Core routing logic |
| 3.6 | Response processor | None | Normalize provider responses |

**Milestone 3:** Requests route to appropriate provider with caching active.

#### Phase 4: Reliability Features (Weeks 4-5)

| Step | Component | Dependencies | Rationale |
|------|-----------|--------------|-----------|
| 4.1 | Rate limiter | Redis client | Enforce quotas before expensive calls |
| 4.2 | Health monitor | Phase 2 adapters, Redis | Track provider health for routing |
| 4.3 | Fallback manager | Health monitor, Phase 2 | Circuit breaker and failover |
| 4.4 | Request queue | Redis client | Buffer requests during spikes |
| 4.5 | Batch processor | Request queue | Support batch API endpoints |

**Milestone 4:** Resilient request handling with failover and queuing.

#### Phase 5: External Interfaces (Weeks 5-6)

| Step | Component | Dependencies | Rationale |
|------|-----------|--------------|-----------|
| 5.1 | gRPC server | Phases 1-4 | Primary internal interface |
| 5.2 | HTTP server | Phases 1-4 | OpenAI-compatible external interface |
| 5.3 | L01 Event publisher | Event Store client | Event emission for all operations |
| 5.4 | L01 Config watcher | Configuration Service client | Hot-reload capability |
| 5.5 | L01 DID resolver | DID Registry client | Agent identity resolution |
| 5.6 | L01 ABAC client | OPA client | Authorization integration |

**Milestone 5:** Full L04 functionality with Data Layer integration.

#### Phase 6: Deployment and Operations (Week 6)

| Step | Component | Dependencies | Rationale |
|------|-----------|--------------|-----------|
| 6.1 | Kubernetes manifests | All phases | Deploy to cluster |
| 6.2 | Helm chart | K8s manifests | Parameterized deployment |
| 6.3 | Runbook documentation | Operational experience | Support production operations |
| 6.4 | Performance validation | Load testing | Verify targets met |

**Milestone 6:** Production-ready deployment.

### 11.4 Component Initialization Order

```
Application Start
      |
      v
+---------------------+
| 1. Load Config      |
|    - Validate JSON  |
|    - Set defaults   |
+---------------------+
      |
      v
+---------------------+
| 2. Init Storage     |
|    - Redis Cluster  |
|    - SQLite (local) |
+---------------------+
      |
      v
+---------------------+
| 3. Init Observability|
|    - Prometheus     |
|    - Tracing        |
|    - Structured Log |
+---------------------+
      |
      v
+---------------------+
| 4. Load Secrets     |
|    - Provider keys  |
|    - mTLS certs     |
+---------------------+
      |
      v
+---------------------+
| 5. Init Adapters    |
|    - Per-provider   |
|    - Health check   |
+---------------------+
      |
      v
+---------------------+
| 6. Init Components  |
|    - Model Registry |
|    - Router         |
|    - Cache          |
|    - Rate Limiter   |
+---------------------+
      |
      v
+---------------------+
| 7. Start Servers    |
|    - gRPC (8080)    |
|    - HTTP (8081)    |
|    - Metrics (9090) |
+---------------------+
      |
      v
+---------------------+
| 8. Register Health  |
|    - Readiness OK   |
+---------------------+
```

### 11.5 Code Style and Conventions

#### 11.5.1 Type Annotations

All code MUST use Python 3.11+ type hints:

```python
from typing import Protocol, Optional, List, Dict, Any
from dataclasses import dataclass

@dataclass
class InferenceResult:
    content: str
    tokens_used: int
    latency_ms: float
    cache_hit: bool

async def route_request(
    request: InferenceRequest,
    timeout_ms: int = 30000
) -> InferenceResult:
    """
    Route inference request to appropriate provider.
    
    Args:
        request: Validated inference request
        timeout_ms: Request timeout in milliseconds
        
    Returns:
        InferenceResult with model response
        
    Raises:
        RoutingError: No suitable provider available
        TimeoutError: Request exceeded timeout
    """
    ...
```

#### 11.5.2 Async Patterns

All I/O operations use asyncio:

```python
import asyncio
from contextlib import asynccontextmanager

@asynccontextmanager
async def acquire_rate_limit(agent_did: str, model_id: str):
    """Context manager for rate limit acquisition with automatic release."""
    token = await rate_limiter.acquire(agent_did, model_id)
    try:
        yield token
    finally:
        await rate_limiter.release(token)

async def process_request(request: InferenceRequest) -> InferenceResponse:
    async with acquire_rate_limit(request.agent_did, request.model_id):
        # Concurrent cache check and provider health lookup
        cache_result, health = await asyncio.gather(
            cache.get(request),
            health_monitor.get_provider_health(request.provider)
        )
        if cache_result:
            return cache_result
        return await adapter.invoke(request)
```

#### 11.5.3 Error Handling

Structured error handling with typed exceptions:

```python
from enum import Enum
from dataclasses import dataclass

class ErrorCode(Enum):
    E4001 = "PROVIDER_UNAVAILABLE"
    E4002 = "RATE_LIMIT_EXCEEDED"
    E4003 = "UNAUTHORIZED_MODEL"
    E4004 = "INVALID_REQUEST"
    E4005 = "TOKEN_BUDGET_EXCEEDED"
    E4006 = "TIMEOUT"
    E4007 = "ROUTING_FAILED"

@dataclass
class GatewayError(Exception):
    code: ErrorCode
    message: str
    details: Optional[Dict[str, Any]] = None
    retry_after_ms: Optional[int] = None

class ProviderUnavailableError(GatewayError):
    def __init__(self, provider: str, reason: str):
        super().__init__(
            code=ErrorCode.E4001,
            message=f"Provider {provider} unavailable: {reason}",
            details={"provider": provider, "reason": reason}
        )
```

---

## 12. Testing Strategy

### 12.1 Unit Tests

#### 12.1.1 Coverage Targets

| Component | Coverage Target | Critical Paths |
|-----------|-----------------|----------------|
| Model Registry | 95% | Capability matching, model selection |
| LLM Router | 95% | Routing decisions, fallback selection |
| Semantic Cache | 90% | Embedding generation, similarity matching, TTL expiry |
| Exact Cache | 90% | Hash generation, hit/miss logic |
| Rate Limiter | 95% | Token acquisition, burst handling, quota enforcement |
| Token Counter | 98% | Accurate counting for all providers |
| Provider Adapters | 90% | Request formatting, response parsing, streaming |
| Fallback Manager | 95% | Circuit state transitions, retry logic |

#### 12.1.2 Unit Test Patterns

**Model Registry Tests:**

```python
import pytest
from model_gateway.components.model_registry import ModelRegistry

class TestModelRegistry:
    @pytest.fixture
    def registry(self):
        return ModelRegistry(config=TEST_MODEL_CONFIG)
    
    def test_capability_filter_vision(self, registry):
        """Models filtered by vision capability."""
        models = registry.find_models(capabilities=["vision"])
        assert all("vision" in m.capabilities for m in models)
    
    def test_capability_filter_long_context(self, registry):
        """Models filtered by context window requirement."""
        models = registry.find_models(min_context_window=100000)
        assert all(m.context_window >= 100000 for m in models)
    
    def test_cost_ranking(self, registry):
        """Models ranked by cost when multiple match."""
        models = registry.find_models(
            capabilities=["text"],
            sort_by="cost"
        )
        costs = [m.cost_per_1m_input_tokens for m in models]
        assert costs == sorted(costs)
    
    def test_inactive_model_excluded(self, registry):
        """Inactive models not returned in queries."""
        registry.set_status("model-123", "inactive")
        models = registry.find_models()
        assert not any(m.model_id == "model-123" for m in models)
```

**Semantic Cache Tests:**

```python
import pytest
import numpy as np
from model_gateway.components.semantic_cache import SemanticCache

class TestSemanticCache:
    @pytest.fixture
    def cache(self, mock_embedding_model):
        return SemanticCache(
            embedding_model=mock_embedding_model,
            similarity_threshold=0.85,
            ttl_seconds=3600
        )
    
    @pytest.mark.asyncio
    async def test_exact_semantic_match(self, cache):
        """Identical prompts return cached response."""
        prompt = "What is the capital of France?"
        response = "Paris is the capital of France."
        
        await cache.set(prompt, response)
        result = await cache.get(prompt)
        
        assert result.hit is True
        assert result.response == response
        assert result.similarity == 1.0
    
    @pytest.mark.asyncio
    async def test_similar_prompt_hit(self, cache, mock_embedding_model):
        """Semantically similar prompt returns cached response."""
        # Configure embeddings to be 0.90 similar
        mock_embedding_model.similarity_matrix = {
            ("What is France's capital?", "What is the capital of France?"): 0.90
        }
        
        await cache.set("What is the capital of France?", "Paris")
        result = await cache.get("What is France's capital?")
        
        assert result.hit is True
        assert result.similarity >= 0.85
    
    @pytest.mark.asyncio
    async def test_dissimilar_prompt_miss(self, cache, mock_embedding_model):
        """Semantically different prompt results in cache miss."""
        mock_embedding_model.similarity_matrix = {
            ("What is 2+2?", "What is the capital of France?"): 0.20
        }
        
        await cache.set("What is the capital of France?", "Paris")
        result = await cache.get("What is 2+2?")
        
        assert result.hit is False
    
    @pytest.mark.asyncio
    async def test_ttl_expiry(self, cache, freezer):
        """Cached entries expire after TTL."""
        await cache.set("prompt", "response")
        
        freezer.move_to("+3601 seconds")  # Past TTL
        result = await cache.get("prompt")
        
        assert result.hit is False
```

**Rate Limiter Tests:**

```python
import pytest
from model_gateway.components.rate_limiter import TokenBucketRateLimiter

class TestRateLimiter:
    @pytest.fixture
    def limiter(self, mock_redis):
        return TokenBucketRateLimiter(
            redis=mock_redis,
            default_rpm=100,
            default_tpm=100000
        )
    
    @pytest.mark.asyncio
    async def test_acquire_within_limit(self, limiter):
        """Request within rate limit succeeds."""
        result = await limiter.acquire(
            agent_did="did:agent:123",
            model_id="claude-sonnet",
            tokens=1000
        )
        assert result.allowed is True
    
    @pytest.mark.asyncio
    async def test_acquire_exceeds_rpm(self, limiter, mock_redis):
        """Request exceeding RPM is rejected."""
        # Exhaust rate limit
        for _ in range(100):
            await limiter.acquire("did:agent:123", "claude-sonnet", 100)
        
        result = await limiter.acquire("did:agent:123", "claude-sonnet", 100)
        assert result.allowed is False
        assert result.retry_after_ms > 0
    
    @pytest.mark.asyncio
    async def test_burst_allowance(self, limiter):
        """Burst multiplier allows temporary spikes."""
        # Configure 2x burst
        limiter.set_burst_multiplier("did:agent:123", 2.0)
        
        # Should allow 200 requests (100 base * 2x burst)
        for _ in range(200):
            result = await limiter.acquire("did:agent:123", "claude-sonnet", 100)
            assert result.allowed is True
        
        # 201st should fail
        result = await limiter.acquire("did:agent:123", "claude-sonnet", 100)
        assert result.allowed is False
```

### 12.2 Integration Tests

#### 12.2.1 Integration Test Matrix

| Integration | Test Focus | Mock Strategy | Environment |
|-------------|------------|---------------|-------------|
| L04 <-> Provider APIs | Request formatting, response parsing | Mock HTTP server | CI |
| L04 <-> Redis | Cache operations, rate limit state | Real Redis (container) | CI |
| L04 <-> L01 Event Store | Event publishing, ordering | Mock or real Kafka | CI/Staging |
| L04 <-> L01 Config Service | Config loading, hot reload | Mock service | CI |
| L04 <-> L01 DID Registry | Identity resolution | Mock service | CI |
| L04 <-> Multiple Providers | Failover behavior | Mock HTTP servers | CI |

#### 12.2.2 End-to-End Test Scenarios

**E2E-1: Basic Inference Flow**

```python
@pytest.mark.integration
async def test_basic_inference_flow(gateway_client, mock_anthropic_server):
    """Complete inference request through gateway."""
    request = InferenceRequest(
        request_id="test-001",
        agent_did="did:agent:test",
        logical_prompt=LogicalPrompt(
            system_message="You are a helpful assistant.",
            messages=[{"role": "user", "content": "Hello"}]
        ),
        latency_class=LatencyClass.INTERACTIVE,
        token_budget=TokenBudget(
            max_input_tokens=1000,
            max_output_tokens=1000,
            max_cost_cents=10
        ),
        required_capabilities=["text"]
    )
    
    response = await gateway_client.inference(request)
    
    assert response.request_id == "test-001"
    assert response.provider == "anthropic"
    assert response.content is not None
    assert response.usage["total_tokens"] > 0
    assert response.latency_ms < 2000
```

**E2E-2: Cache Hit Scenario**

```python
@pytest.mark.integration
async def test_cache_hit_returns_cached_response(gateway_client):
    """Second identical request returns cached response."""
    request = create_test_request(prompt="What is 2+2?")
    
    # First request - cache miss
    response1 = await gateway_client.inference(request)
    assert response1.cache_hit is False
    
    # Second request - cache hit
    response2 = await gateway_client.inference(request)
    assert response2.cache_hit is True
    assert response2.content == response1.content
    assert response2.latency_ms < response1.latency_ms
```

**E2E-3: Provider Failover**

```python
@pytest.mark.integration
async def test_provider_failover(
    gateway_client, 
    mock_anthropic_server,
    mock_openai_server
):
    """Request fails over to secondary provider on primary failure."""
    # Configure primary to fail
    mock_anthropic_server.set_response_status(503)
    
    request = create_test_request(
        required_capabilities=["text"],
        routing_hints={"fallback_providers": ["openai"]}
    )
    
    response = await gateway_client.inference(request)
    
    # Should succeed via fallback
    assert response.provider == "openai"
    assert response.content is not None
```

**E2E-4: Rate Limit Enforcement**

```python
@pytest.mark.integration
async def test_rate_limit_enforcement(gateway_client):
    """Requests exceeding rate limit are rejected."""
    # Configure low rate limit
    await gateway_client.set_rate_limit(
        agent_did="did:agent:test",
        rpm=5
    )
    
    # Send 5 requests - should succeed
    for _ in range(5):
        response = await gateway_client.inference(create_test_request())
        assert response is not None
    
    # 6th request should be rate limited
    with pytest.raises(RateLimitExceededError) as exc_info:
        await gateway_client.inference(create_test_request())
    
    assert exc_info.value.retry_after_ms > 0
```

**E2E-5: Data Layer Event Publishing**

```python
@pytest.mark.integration
async def test_events_published_to_event_store(
    gateway_client,
    event_store_consumer
):
    """Inference request publishes expected events."""
    request = create_test_request(request_id="event-test-001")
    
    await gateway_client.inference(request)
    
    # Collect events for this request
    events = await event_store_consumer.get_events(
        correlation_id="event-test-001",
        timeout_seconds=5
    )
    
    event_types = [e.event_type for e in events]
    
    assert "model.request.submitted" in event_types
    assert "model.response.received" in event_types
    assert "model.cost.incurred" in event_types
```

### 12.3 Performance Tests

#### 12.3.1 Performance Targets

| Metric | Target | Degraded | Critical | Test Method |
|--------|--------|----------|----------|-------------|
| Throughput | 1000 req/s | 500 req/s | 100 req/s | Locust load test |
| Latency overhead (p50) | 15ms | 25ms | 50ms | Measured delta vs direct API |
| Latency overhead (p99) | 50ms | 100ms | 200ms | Measured delta vs direct API |
| Cache hit latency (p99) | 20ms | 35ms | 50ms | Cache-only test |
| Rate limit check | 0.5ms | 1ms | 2ms | Isolated benchmark |
| Memory per request | 2KB | 5KB | 10KB | Memory profiling |

#### 12.3.2 Load Test Configuration

**Locust Test Definition:**

```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between
import json

class GatewayUser(HttpUser):
    wait_time = between(0.1, 0.5)
    
    def on_start(self):
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.environment.parsed_options.api_key}"
        }
    
    @task(10)
    def simple_inference(self):
        """Simple text completion request."""
        payload = {
            "model": "claude-sonnet",
            "messages": [
                {"role": "user", "content": "Say hello in one word."}
            ],
            "max_tokens": 10
        }
        self.client.post(
            "/v1/chat/completions",
            json=payload,
            headers=self.headers
        )
    
    @task(3)
    def streaming_inference(self):
        """Streaming text completion."""
        payload = {
            "model": "claude-sonnet",
            "messages": [
                {"role": "user", "content": "Count from 1 to 5."}
            ],
            "max_tokens": 50,
            "stream": True
        }
        with self.client.post(
            "/v1/chat/completions",
            json=payload,
            headers=self.headers,
            stream=True
        ) as response:
            for chunk in response.iter_lines():
                pass  # Consume stream
    
    @task(5)
    def cache_hit_request(self):
        """Request expected to hit cache."""
        payload = {
            "model": "claude-sonnet",
            "messages": [
                {"role": "user", "content": "What is 2+2?"}  # Stable prompt
            ],
            "max_tokens": 10
        }
        self.client.post(
            "/v1/chat/completions",
            json=payload,
            headers=self.headers
        )
```

**Load Test Execution:**

```bash
# Baseline test (single user)
locust --headless -u 1 -r 1 -t 1m --host http://localhost:8081

# Standard load test (100 concurrent users)
locust --headless -u 100 -r 10 -t 5m --host http://localhost:8081

# Stress test (1000 concurrent users)
locust --headless -u 1000 -r 50 -t 10m --host http://localhost:8081

# Spike test (rapid scale-up)
locust --headless -u 500 -r 500 -t 2m --host http://localhost:8081
```

#### 12.3.3 Cache Performance Tests

```python
@pytest.mark.performance
async def test_semantic_cache_throughput(cache, embeddings):
    """Semantic cache handles target throughput."""
    # Warm up cache with 10K entries
    for i in range(10000):
        await cache.set(f"prompt-{i}", f"response-{i}")
    
    # Measure lookup throughput
    start = time.monotonic()
    operations = 0
    
    while time.monotonic() - start < 10.0:  # 10 second test
        await cache.get(f"prompt-{random.randint(0, 9999)}")
        operations += 1
    
    throughput = operations / 10.0
    assert throughput >= 5000  # 5K lookups/second minimum

@pytest.mark.performance
async def test_semantic_cache_latency(cache):
    """Semantic cache lookup latency within target."""
    await cache.set("test-prompt", "test-response")
    
    latencies = []
    for _ in range(1000):
        start = time.monotonic()
        await cache.get("test-prompt")
        latencies.append((time.monotonic() - start) * 1000)
    
    p99_latency = np.percentile(latencies, 99)
    assert p99_latency < 20  # 20ms p99 target
```

### 12.4 Test Fixtures

#### 12.4.1 Common Fixtures

```python
# tests/conftest.py
import pytest
import asyncio
from testcontainers.redis import RedisContainer

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def redis_container():
    """Start Redis container for integration tests."""
    with RedisContainer("redis:7.2") as redis:
        yield redis

@pytest.fixture
async def redis_client(redis_container):
    """Redis client connected to test container."""
    import redis.asyncio as redis
    client = redis.from_url(redis_container.get_connection_url())
    yield client
    await client.flushall()
    await client.close()

@pytest.fixture
def mock_anthropic_server(respx_mock):
    """Mock Anthropic API server."""
    respx_mock.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "msg_test",
                "content": [{"type": "text", "text": "Hello!"}],
                "model": "claude-sonnet-4-20250514",
                "usage": {"input_tokens": 10, "output_tokens": 5}
            }
        )
    )
    return respx_mock

@pytest.fixture
def mock_openai_server(respx_mock):
    """Mock OpenAI API server."""
    respx_mock.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "choices": [{"message": {"content": "Hello!"}}],
                "model": "gpt-4o",
                "usage": {"prompt_tokens": 10, "completion_tokens": 5}
            }
        )
    )
    return respx_mock

@pytest.fixture
def gateway_client(redis_client, mock_anthropic_server):
    """Configured gateway client for testing."""
    from model_gateway import GatewayClient
    return GatewayClient(
        redis=redis_client,
        config=TEST_CONFIG
    )
```

### 12.5 Test Automation

#### 12.5.1 CI Pipeline Configuration

```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      - name: Run unit tests
        run: |
          pytest tests/unit -v --cov=model_gateway --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v4

  integration-tests:
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis:7.2
        ports:
          - 6379:6379
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      - name: Run integration tests
        run: |
          pytest tests/integration -v
        env:
          REDIS_URL: redis://localhost:6379

  performance-tests:
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - name: Run performance tests
        run: |
          pytest tests/performance -v --benchmark-json=benchmark.json
      - name: Store benchmark
        uses: benchmark-action/github-action-benchmark@v1
        with:
          tool: 'pytest'
          output-file-path: benchmark.json
```

---

## 13. Migration and Versioning

### 13.1 Version History

| Version | Date | Changes | Migration Required |
|---------|------|---------|-------------------|
| 1.0.0 | 2026-01-04 | Initial specification | N/A |

### 13.2 Semantic Versioning Policy

L04 follows [Semantic Versioning 2.0.0](https://semver.org/):

| Version Component | Change Type | Example |
|-------------------|-------------|---------|
| MAJOR (X.0.0) | Breaking changes to BC-3 contract | InferenceRequest field removal |
| MINOR (0.X.0) | Backward-compatible additions | New provider adapter |
| PATCH (0.0.X) | Bug fixes, performance improvements | Cache efficiency improvement |

### 13.3 Breaking Changes Policy

**Definition:** A breaking change is any modification that requires consumer layers to update their code or configuration.

**Breaking Changes Include:**
- Removing or renaming fields in InferenceRequest/InferenceResponse
- Changing required fields in API contracts
- Modifying event schemas in incompatible ways
- Removing supported providers
- Changing authentication requirements

**Breaking Changes Exclude:**
- Adding optional fields to existing schemas
- Adding new event types
- Adding new providers
- Performance improvements
- Internal implementation changes

**Breaking Change Process:**

```
+--------------------+
| 1. Announce        |
|    - 30 days notice|
|    - Migration doc |
+--------------------+
         |
         v
+--------------------+
| 2. Deprecate       |
|    - Mark old API  |
|    - Log warnings  |
+--------------------+
         |
         v
+--------------------+
| 3. Parallel Run    |
|    - Both versions |
|    - 14 days min   |
+--------------------+
         |
         v
+--------------------+
| 4. Remove          |
|    - Old version   |
|    - Verify clean  |
+--------------------+
```

### 13.4 API Versioning

#### 13.4.1 gRPC Versioning

gRPC services use package versioning:

```protobuf
// v1 - Current stable
package agent_system.model_gateway.v1;

service InferenceService {
    rpc Inference(InferenceRequest) returns (InferenceResponse);
}

// v2 - Future breaking changes
package agent_system.model_gateway.v2;

service InferenceService {
    rpc Inference(InferenceRequestV2) returns (InferenceResponseV2);
}
```

#### 13.4.2 HTTP API Versioning

HTTP endpoints use URL path versioning:

| Version | Base Path | Status |
|---------|-----------|--------|
| v1 | /v1/chat/completions | Current, Stable |
| v2 | /v2/chat/completions | Future |

### 13.5 Configuration Migration

#### 13.5.1 Schema Migrations

Configuration schema changes follow a migration pattern:

```python
class ConfigMigrator:
    migrations = {
        ("1.0.0", "1.1.0"): migrate_v1_0_to_v1_1,
        ("1.1.0", "1.2.0"): migrate_v1_1_to_v1_2,
    }
    
    async def migrate(self, config: dict, from_version: str, to_version: str):
        current = from_version
        while current != to_version:
            next_version = self.get_next_version(current)
            migration_fn = self.migrations.get((current, next_version))
            if not migration_fn:
                raise MigrationError(f"No migration from {current} to {next_version}")
            config = await migration_fn(config)
            current = next_version
        return config
```

#### 13.5.2 Example Migration: Adding New Field

```python
def migrate_v1_0_to_v1_1(config: dict) -> dict:
    """
    Migration: v1.0.0 -> v1.1.0
    Adds: cost_per_1m_cached_input_tokens to model definitions
    """
    for model in config.get("models", []):
        if "cost_per_1m_cached_input_tokens" not in model:
            # Default: 10% of input token cost
            model["cost_per_1m_cached_input_tokens"] = (
                model.get("cost_per_1m_input_tokens", 0) * 0.1
            )
    config["version"] = "1.1.0"
    return config
```

### 13.6 Cache Migration

#### 13.6.1 Cache Invalidation on Upgrade

When cache schema changes, entries must be invalidated:

```python
class CacheManager:
    CACHE_VERSION = "1.0.0"
    
    async def get(self, key: str) -> Optional[CacheEntry]:
        entry = await self.storage.get(key)
        if entry and entry.version != self.CACHE_VERSION:
            # Stale entry from previous version
            await self.storage.delete(key)
            return None
        return entry
    
    async def migrate_cache(self, old_version: str, new_version: str):
        """
        Migrate cache entries or invalidate if incompatible.
        """
        if self.is_compatible(old_version, new_version):
            await self.update_version_markers(new_version)
        else:
            await self.flush_cache()
            logger.info(f"Cache flushed for migration {old_version} -> {new_version}")
```

### 13.7 Rollback Procedures

#### 13.7.1 Deployment Rollback

```bash
# Rollback to previous deployment
kubectl rollout undo deployment/model-gateway -n model-gateway

# Rollback to specific revision
kubectl rollout undo deployment/model-gateway --to-revision=5 -n model-gateway

# Verify rollback
kubectl rollout status deployment/model-gateway -n model-gateway
```

#### 13.7.2 Configuration Rollback

```bash
# L01 Configuration Service maintains version history
# Restore previous configuration version
curl -X POST "http://config-service/api/v1/config/l04/models.json/rollback" \
  -H "Content-Type: application/json" \
  -d '{"target_version": "v1.2.3"}'
```

#### 13.7.3 Data Rollback

| Data Store | Rollback Method | Recovery Point |
|------------|-----------------|----------------|
| Redis Cache | Flush and rebuild | N/A (ephemeral) |
| SQLite Cache | Restore from backup | Daily backup |
| Event Store | Events are immutable | N/A |
| Configuration | Version history | Any previous version |

---

## 14. Open Questions

### 14.1 Resolved Questions

| # | Question | Resolution | Resolved In |
|---|----------|------------|-------------|
| Q1 | How should semantic similarity be computed for cache hits? | text-embedding-3-small with cosine similarity, 0.85 threshold | Section 3.3.3 |
| Q2 | What caching strategy for streaming responses? | Cache final accumulated response after stream completion | Section 3.3.3 |
| Q3 | How to handle provider-specific features (tool use, vision)? | Provider adapters normalize; capability flags in LogicalPrompt | Section 3.3.5 |
| Q5 | How to implement routing decisions? | Capability match -> latency filter -> cost optimization | Section 3.3.2 |
| Q8 | Network boundary for Model Gateway? | DMZ placement with Cilium egress policies | Section 8.6 |
| Q9 | Circuit breaker patterns? | Per-provider circuit breaker; 5 failures, 60s cooldown | Section 7.3 |

### 14.2 Outstanding Questions

| # | Question | Priority | Target Resolution | Owner |
|---|----------|----------|-------------------|-------|
| Q4 | What metrics are needed for FinOps integration (cost attribution, budget alerts)? | Medium | L04 v1.1 | FinOps Team |
| Q6 | Should the gateway handle prompt optimization/compression? | Medium | L04 v1.1 | L04 Team |
| Q7 | How to support fine-tuned models alongside base models in the registry? | Medium | After L07 spec | L07 Team |
| Q10 | Token counting accuracy for streaming responses? | Medium | L04 v1.0.1 | L04 Team |
| Q11 | Multi-region gateway deployment topology? | Low | L04 v1.2 | Platform Team |
| Q12 | Provider prompt caching coordination (Anthropic cache_control)? | Medium | L04 v1.1 | L04 Team |

### 14.3 Deferred Decisions

| Decision | Rationale for Deferral | Revisit Date |
|----------|------------------------|--------------|
| Local model deployment strategy | Requires L00 GPU infrastructure finalization | 2026-Q2 |
| Multi-tenancy isolation model | Depends on L02 Agent Runtime design | After L02 spec |
| FinOps dashboard integration | Requires enterprise FinOps tooling selection | 2026-Q2 |

---

## 15. References

### 15.1 Internal References

| Document | Version | Relevance to L04 |
|----------|---------|------------------|
| Infrastructure Layer Specification | v1.2 | L00 dependencies (Secrets, Network, Observability) |
| Agentic Data Layer Master Specification | v3.2.1 | L01 integration (Events, Storage, Config, Identity) |
| Layer Specification Template | v1.0 | Document structure |
| Specification Integration Guide | v1.0 | Cross-layer patterns |
| Model Gateway Research Findings | v1.0 | Industry patterns informing design |
| Model Gateway Gap Analysis | v1.0 | Integration requirements |

### 15.2 Cross-Layer Interface References

| Interface | Specification Location | L04 Usage |
|-----------|------------------------|-----------|
| BC-3 (InferenceRequest) | This document, Section 4.1.1 | Primary interface with L02, L05, L06, L07 |
| Event Store Protocol | L01 Spec, Phase 1 | Event publishing |
| DID Resolution | L01 Spec, Phase 0 | Agent identity |
| ABAC/OPA Integration | L01 Spec, Cross-cutting | Authorization |
| Configuration Service | L01 Spec, Phase 11 | Config management |
| Storage Service | L01 Spec, Phase 2 | Redis and SQLite access |

### 15.3 External References

| Reference | URL | Relevance |
|-----------|-----|-----------|
| OpenAI API Reference | https://platform.openai.com/docs/api-reference | OpenAI-compatible interface design |
| Anthropic API Reference | https://docs.anthropic.com/en/api | Anthropic adapter implementation |
| Azure OpenAI API Reference | https://learn.microsoft.com/en-us/azure/ai-services/openai/reference | Azure adapter implementation |
| Google Vertex AI API | https://cloud.google.com/vertex-ai/docs/reference | Google adapter implementation |
| LiteLLM Documentation | https://docs.litellm.ai/ | Multi-provider abstraction patterns |
| GPTCache | https://github.com/zilliztech/GPTCache | Semantic caching patterns |
| Redis Cluster | https://redis.io/docs/management/scaling/ | Distributed caching |
| sqlite-vec | https://github.com/asg017/sqlite-vec | Vector similarity search |
| Circuit Breaker Pattern | https://martinfowler.com/bliki/CircuitBreaker.html | Resilience pattern |
| Token Bucket Algorithm | https://en.wikipedia.org/wiki/Token_bucket | Rate limiting |
| OpenTelemetry Specification | https://opentelemetry.io/docs/specs/ | Observability standards |

### 15.4 Standards References

| Standard | Version | Usage |
|----------|---------|-------|
| JSON Schema | Draft 2020-12 | Configuration and event schemas |
| OpenAPI | 3.1.0 | HTTP API documentation |
| gRPC | 1.60 | Internal service communication |
| Semantic Versioning | 2.0.0 | Version management |
| RFC 3339 | - | Timestamp formatting |
| RFC 7807 | - | Problem details for HTTP APIs |

---

## 16. Appendices

### Appendix A: Glossary

| Term | Definition |
|------|------------|
| BC-3 | Boundary Contract 3: The InferenceRequest/InferenceResponse interface between L04 and consuming layers |
| Circuit Breaker | Pattern that prevents cascading failures by failing fast when a provider is unhealthy |
| DID | Decentralized Identifier: Unique identifier for agents in the system |
| Embedding | Dense vector representation of text used for semantic similarity comparison |
| Exact Cache | Cache layer using hash-based lookup for identical request matching |
| Failover | Automatic routing to backup provider when primary is unavailable |
| gRPC | Google Remote Procedure Call: Binary protocol for internal service communication |
| Hot Cache | In-memory cache layer (Redis) for frequently accessed data |
| InferenceRequest | Standardized request format for LLM inference (see Section 4.1.1) |
| InferenceResponse | Standardized response format from LLM inference (see Section 4.1.1) |
| Latency Class | Request urgency classification (REALTIME, INTERACTIVE, BATCH) |
| LogicalPrompt | Provider-agnostic prompt structure constructed by L05 Planning |
| Model Registry | Catalog of available models with capabilities, costs, and limits |
| mTLS | Mutual TLS: Two-way certificate authentication |
| OPA | Open Policy Agent: Policy engine for authorization decisions |
| Provider Adapter | Component that translates between BC-3 format and provider-specific APIs |
| Rate Limiter | Component enforcing request and token quotas |
| Semantic Cache | Cache layer using embedding similarity for semantically similar requests |
| Token Budget | Maximum tokens and cost constraints for a request |
| Token Bucket | Rate limiting algorithm that allows controlled bursting |
| Warm Cache | Persistent cache layer (SQLite) for less frequently accessed data |

### Appendix B: Decision Log

| Decision ID | Date | Decision | Rationale | Alternatives Considered |
|-------------|------|----------|-----------|------------------------|
| D-04-001 | 2026-01-04 | Use OpenAI-compatible HTTP interface | Industry standard maximizes client compatibility | Custom API, gRPC-only |
| D-04-002 | 2026-01-04 | Dual cache architecture (exact + semantic) | Exact cache is faster/cheaper; semantic catches variations | Single cache layer |
| D-04-003 | 2026-01-04 | text-embedding-3-small for semantic cache | Balance of quality and cost at 1536 dimensions | text-embedding-3-large, local models |
| D-04-004 | 2026-01-04 | 0.85 similarity threshold for cache hits | Industry research shows optimal precision/recall balance | 0.80, 0.90, configurable |
| D-04-005 | 2026-01-04 | Token bucket for rate limiting | Handles bursts gracefully; well-understood algorithm | Sliding window, leaky bucket |
| D-04-006 | 2026-01-04 | Per-provider circuit breakers | Isolates failures; prevents all-or-nothing scenarios | Global circuit breaker |
| D-04-007 | 2026-01-04 | Redis Cluster for distributed state | Proven at scale; low latency; atomic operations | Memcached, etcd |
| D-04-008 | 2026-01-04 | SQLite + sqlite-vec for persistent cache | Simple deployment; sufficient performance for cache workload | PostgreSQL + pgvector |
| D-04-009 | 2026-01-04 | Sequential fallback (not parallel) | Reduces cost; most failures are transient | Parallel requests with first-response |
| D-04-010 | 2026-01-04 | DMZ network placement | Required for egress to external APIs | Internal-only with proxy |

### Appendix C: Provider Adapter Specifications

#### C.1 Anthropic Adapter

**Endpoint:** https://api.anthropic.com/v1/messages

**Request Mapping:**

| BC-3 Field | Anthropic Field | Transformation |
|------------|-----------------|----------------|
| logical_prompt.system_message | system | Direct mapping |
| logical_prompt.messages | messages | Role: user/assistant |
| logical_prompt.tools | tools | Convert to Anthropic tool schema |
| logical_prompt.output_schema | tools[type=json] | Wrap in tool call |
| token_budget.max_output_tokens | max_tokens | Direct mapping |

**Response Mapping:**

| Anthropic Field | BC-3 Field | Transformation |
|-----------------|------------|----------------|
| content[0].text | content | Extract text block |
| content[type=tool_use] | tool_calls | Parse tool call response |
| usage.input_tokens | usage.prompt_tokens | Direct mapping |
| usage.output_tokens | usage.completion_tokens | Direct mapping |
| model | model | Direct mapping |

**Special Features:**
- Prompt caching via `cache_control` blocks
- Extended thinking for complex reasoning
- Native vision support in messages

**Error Mapping:**

| Anthropic Error | BC-3 Error Code | Retry |
|-----------------|-----------------|-------|
| 400 Bad Request | E4004 | No |
| 401 Unauthorized | E4003 | No |
| 429 Rate Limit | E4002 | Yes (retry_after header) |
| 500 Internal Error | E4001 | Yes (exponential backoff) |
| 529 Overloaded | E4001 | Yes (exponential backoff) |

#### C.2 OpenAI Adapter

**Endpoint:** https://api.openai.com/v1/chat/completions

**Request Mapping:**

| BC-3 Field | OpenAI Field | Transformation |
|------------|--------------|----------------|
| logical_prompt.system_message | messages[0] | role: system |
| logical_prompt.messages | messages | Direct append |
| logical_prompt.tools | tools | Convert to OpenAI function schema |
| logical_prompt.output_schema | response_format | JSON mode or structured outputs |
| token_budget.max_output_tokens | max_tokens | Direct mapping |
| routing_hints.model | model | Model selection |

**Response Mapping:**

| OpenAI Field | BC-3 Field | Transformation |
|--------------|------------|----------------|
| choices[0].message.content | content | Direct mapping |
| choices[0].message.tool_calls | tool_calls | Direct mapping |
| usage.prompt_tokens | usage.prompt_tokens | Direct mapping |
| usage.completion_tokens | usage.completion_tokens | Direct mapping |
| model | model | Direct mapping |

**Special Features:**
- Structured outputs with JSON schema
- Function calling (legacy and modern)
- Vision with image URLs or base64
- Batch API for non-urgent requests

**Error Mapping:**

| OpenAI Error | BC-3 Error Code | Retry |
|--------------|-----------------|-------|
| 400 Bad Request | E4004 | No |
| 401 Unauthorized | E4003 | No |
| 429 Rate Limit | E4002 | Yes (retry_after header) |
| 500 Server Error | E4001 | Yes (exponential backoff) |
| 503 Service Unavailable | E4001 | Yes (exponential backoff) |

#### C.3 Azure OpenAI Adapter

**Endpoint:** https://{resource}.openai.azure.com/openai/deployments/{deployment}/chat/completions?api-version={version}

**Configuration:**

| Parameter | Source | Description |
|-----------|--------|-------------|
| resource | Config | Azure resource name |
| deployment | Model Registry | Deployment name per model |
| api-version | Config | API version (2024-02-15-preview) |

**Request Mapping:**
Identical to OpenAI adapter with endpoint URL transformation.

**Authentication:**
- API Key via `api-key` header
- Azure AD via Bearer token

**Special Features:**
- Content filtering integration
- Private endpoint support
- Regional deployment selection

#### C.4 Google Vertex AI Adapter

**Endpoint:** https://{region}-aiplatform.googleapis.com/v1/projects/{project}/locations/{region}/publishers/google/models/{model}:streamGenerateContent

**Request Mapping:**

| BC-3 Field | Vertex Field | Transformation |
|------------|--------------|----------------|
| logical_prompt.system_message | systemInstruction | Wrap in Content |
| logical_prompt.messages | contents | Role: user/model |
| logical_prompt.tools | tools | Convert to Vertex tool schema |
| token_budget.max_output_tokens | generationConfig.maxOutputTokens | Direct mapping |

**Response Mapping:**

| Vertex Field | BC-3 Field | Transformation |
|--------------|------------|----------------|
| candidates[0].content.parts[0].text | content | Extract text |
| usageMetadata.promptTokenCount | usage.prompt_tokens | Direct mapping |
| usageMetadata.candidatesTokenCount | usage.completion_tokens | Direct mapping |

**Authentication:**
- Service Account JSON via `GOOGLE_APPLICATION_CREDENTIALS`
- Workload Identity for GKE deployments

**Special Features:**
- Grounding with Google Search
- Safety settings configuration
- Tuned model support

### Appendix D: Error Code Reference

| Code | Name | HTTP Status | Description | Retry |
|------|------|-------------|-------------|-------|
| E4001 | PROVIDER_UNAVAILABLE | 503 | No healthy provider available | Yes |
| E4002 | RATE_LIMIT_EXCEEDED | 429 | Agent or provider rate limit hit | Yes |
| E4003 | UNAUTHORIZED_MODEL | 403 | Agent lacks capability for model | No |
| E4004 | INVALID_REQUEST | 400 | Malformed or invalid request | No |
| E4005 | TOKEN_BUDGET_EXCEEDED | 400 | Request exceeds token budget | No |
| E4006 | TIMEOUT | 504 | Request exceeded timeout | Yes |
| E4007 | ROUTING_FAILED | 500 | No model matches requirements | No |
| E4008 | CACHE_ERROR | 500 | Cache operation failed | Yes |
| E4009 | CIRCUIT_OPEN | 503 | Provider circuit breaker open | Yes |
| E4010 | QUOTA_EXCEEDED | 402 | Daily budget exhausted | No |

### Appendix E: Metric Reference

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| gateway_requests_total | Counter | provider, model, status, cache_hit | Total requests processed |
| gateway_request_duration_seconds | Histogram | provider, model, latency_class | Request latency distribution |
| gateway_tokens_total | Counter | provider, model, direction | Token usage (input/output) |
| gateway_cost_cents_total | Counter | provider, model, agent_did | Cost incurred |
| gateway_cache_operations_total | Counter | cache_type, operation, result | Cache operations |
| gateway_cache_hit_ratio | Gauge | cache_type | Rolling cache hit ratio |
| gateway_rate_limit_rejections_total | Counter | agent_did, model | Rate limit rejections |
| gateway_circuit_breaker_state | Gauge | provider | Circuit state (0=closed, 1=open, 2=half-open) |
| gateway_queue_depth | Gauge | priority | Current queue depth |
| gateway_provider_latency_seconds | Histogram | provider | Provider response time |
| gateway_provider_errors_total | Counter | provider, error_type | Provider error count |

### Appendix F: Event Schema Reference

#### F.1 model.request.submitted

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-system.internal/schemas/l04/events/model.request.submitted.schema.json",
  "title": "Model Request Submitted Event",
  "type": "object",
  "properties": {
    "event_id": { "type": "string", "format": "uuid" },
    "event_type": { "const": "model.request.submitted" },
    "timestamp": { "type": "string", "format": "date-time" },
    "version": { "const": "1.0.0" },
    "agent_did": { "type": "string", "pattern": "^did:agent:" },
    "correlation_id": { "type": "string" },
    "payload": {
      "type": "object",
      "properties": {
        "request_id": { "type": "string" },
        "latency_class": { "enum": ["realtime", "interactive", "batch"] },
        "required_capabilities": { "type": "array", "items": { "type": "string" } },
        "token_budget": {
          "type": "object",
          "properties": {
            "max_input_tokens": { "type": "integer" },
            "max_output_tokens": { "type": "integer" },
            "max_cost_cents": { "type": "integer" }
          }
        },
        "prompt_hash": { "type": "string", "description": "SHA256 of prompt for privacy" }
      },
      "required": ["request_id", "latency_class"]
    }
  },
  "required": ["event_id", "event_type", "timestamp", "version", "agent_did", "correlation_id", "payload"]
}
```

#### F.2 model.response.received

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-system.internal/schemas/l04/events/model.response.received.schema.json",
  "title": "Model Response Received Event",
  "type": "object",
  "properties": {
    "event_id": { "type": "string", "format": "uuid" },
    "event_type": { "const": "model.response.received" },
    "timestamp": { "type": "string", "format": "date-time" },
    "version": { "const": "1.0.0" },
    "agent_did": { "type": "string", "pattern": "^did:agent:" },
    "correlation_id": { "type": "string" },
    "payload": {
      "type": "object",
      "properties": {
        "request_id": { "type": "string" },
        "provider": { "type": "string" },
        "model": { "type": "string" },
        "latency_ms": { "type": "integer" },
        "cache_hit": { "type": "boolean" },
        "usage": {
          "type": "object",
          "properties": {
            "prompt_tokens": { "type": "integer" },
            "completion_tokens": { "type": "integer" },
            "total_tokens": { "type": "integer" }
          }
        },
        "status": { "enum": ["success", "error"] },
        "error_code": { "type": "string" }
      },
      "required": ["request_id", "provider", "model", "latency_ms", "cache_hit", "status"]
    }
  },
  "required": ["event_id", "event_type", "timestamp", "version", "agent_did", "correlation_id", "payload"]
}
```

#### F.3 model.cost.incurred

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-system.internal/schemas/l04/events/model.cost.incurred.schema.json",
  "title": "Model Cost Incurred Event",
  "type": "object",
  "properties": {
    "event_id": { "type": "string", "format": "uuid" },
    "event_type": { "const": "model.cost.incurred" },
    "timestamp": { "type": "string", "format": "date-time" },
    "version": { "const": "1.0.0" },
    "agent_did": { "type": "string", "pattern": "^did:agent:" },
    "correlation_id": { "type": "string" },
    "payload": {
      "type": "object",
      "properties": {
        "request_id": { "type": "string" },
        "provider": { "type": "string" },
        "model": { "type": "string" },
        "cost_cents": { "type": "number" },
        "input_tokens": { "type": "integer" },
        "output_tokens": { "type": "integer" },
        "cached_input_tokens": { "type": "integer" },
        "cost_breakdown": {
          "type": "object",
          "properties": {
            "input_cost_cents": { "type": "number" },
            "output_cost_cents": { "type": "number" },
            "cached_input_cost_cents": { "type": "number" }
          }
        }
      },
      "required": ["request_id", "provider", "model", "cost_cents"]
    }
  },
  "required": ["event_id", "event_type", "timestamp", "version", "agent_did", "correlation_id", "payload"]
}
```

#### F.4 model.request.routed

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-system.internal/schemas/l04/events/model.request.routed.schema.json",
  "title": "Model Request Routed Event",
  "type": "object",
  "properties": {
    "event_id": { "type": "string", "format": "uuid" },
    "event_type": { "const": "model.request.routed" },
    "timestamp": { "type": "string", "format": "date-time" },
    "version": { "const": "1.0.0" },
    "agent_did": { "type": "string", "pattern": "^did:agent:" },
    "correlation_id": { "type": "string" },
    "payload": {
      "type": "object",
      "properties": {
        "request_id": { "type": "string" },
        "selected_provider": { "type": "string" },
        "selected_model": { "type": "string" },
        "routing_reason": {
          "type": "string",
          "enum": ["capability_match", "cost_optimized", "latency_optimized", "fallback"]
        },
        "candidates_evaluated": { "type": "integer" },
        "routing_latency_ms": { "type": "integer" }
      },
      "required": ["request_id", "selected_provider", "selected_model", "routing_reason"]
    }
  },
  "required": ["event_id", "event_type", "timestamp", "version", "agent_did", "correlation_id", "payload"]
}
```

#### F.5 model.cache.hit

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-system.internal/schemas/l04/events/model.cache.hit.schema.json",
  "title": "Model Cache Hit Event",
  "type": "object",
  "properties": {
    "event_id": { "type": "string", "format": "uuid" },
    "event_type": { "const": "model.cache.hit" },
    "timestamp": { "type": "string", "format": "date-time" },
    "version": { "const": "1.0.0" },
    "agent_did": { "type": "string", "pattern": "^did:agent:" },
    "correlation_id": { "type": "string" },
    "payload": {
      "type": "object",
      "properties": {
        "request_id": { "type": "string" },
        "cache_type": {
          "type": "string",
          "enum": ["exact", "semantic"]
        },
        "cache_key": { "type": "string" },
        "similarity_score": {
          "type": "number",
          "minimum": 0,
          "maximum": 1,
          "description": "For semantic cache hits, the cosine similarity score"
        },
        "cache_age_seconds": { "type": "integer" },
        "tokens_saved": { "type": "integer" },
        "cost_saved_cents": { "type": "number" }
      },
      "required": ["request_id", "cache_type", "cache_key"]
    }
  },
  "required": ["event_id", "event_type", "timestamp", "version", "agent_did", "correlation_id", "payload"]
}
```

#### F.6 model.cache.miss

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-system.internal/schemas/l04/events/model.cache.miss.schema.json",
  "title": "Model Cache Miss Event",
  "type": "object",
  "properties": {
    "event_id": { "type": "string", "format": "uuid" },
    "event_type": { "const": "model.cache.miss" },
    "timestamp": { "type": "string", "format": "date-time" },
    "version": { "const": "1.0.0" },
    "agent_did": { "type": "string", "pattern": "^did:agent:" },
    "correlation_id": { "type": "string" },
    "payload": {
      "type": "object",
      "properties": {
        "request_id": { "type": "string" },
        "cache_type": {
          "type": "string",
          "enum": ["exact", "semantic"]
        },
        "miss_reason": {
          "type": "string",
          "enum": ["no_match", "expired", "similarity_below_threshold", "cache_disabled"]
        },
        "best_similarity_score": {
          "type": "number",
          "minimum": 0,
          "maximum": 1,
          "description": "For semantic cache misses, the highest similarity found"
        },
        "lookup_latency_ms": { "type": "integer" }
      },
      "required": ["request_id", "cache_type", "miss_reason"]
    }
  },
  "required": ["event_id", "event_type", "timestamp", "version", "agent_did", "correlation_id", "payload"]
}
```

#### F.7 model.rate.limited

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-system.internal/schemas/l04/events/model.rate.limited.schema.json",
  "title": "Model Rate Limited Event",
  "type": "object",
  "properties": {
    "event_id": { "type": "string", "format": "uuid" },
    "event_type": { "const": "model.rate.limited" },
    "timestamp": { "type": "string", "format": "date-time" },
    "version": { "const": "1.0.0" },
    "agent_did": { "type": "string", "pattern": "^did:agent:" },
    "correlation_id": { "type": "string" },
    "payload": {
      "type": "object",
      "properties": {
        "request_id": { "type": "string" },
        "limit_type": {
          "type": "string",
          "enum": ["requests_per_minute", "tokens_per_minute", "concurrent_requests"]
        },
        "limit_value": { "type": "integer" },
        "current_value": { "type": "integer" },
        "rate_limit_tier": { "type": "string" },
        "retry_after_ms": { "type": "integer" },
        "model_requested": { "type": "string" }
      },
      "required": ["request_id", "limit_type", "limit_value", "current_value", "retry_after_ms"]
    }
  },
  "required": ["event_id", "event_type", "timestamp", "version", "agent_did", "correlation_id", "payload"]
}
```

#### F.8 model.budget.exhausted

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-system.internal/schemas/l04/events/model.budget.exhausted.schema.json",
  "title": "Model Budget Exhausted Event",
  "type": "object",
  "properties": {
    "event_id": { "type": "string", "format": "uuid" },
    "event_type": { "const": "model.budget.exhausted" },
    "timestamp": { "type": "string", "format": "date-time" },
    "version": { "const": "1.0.0" },
    "agent_did": { "type": "string", "pattern": "^did:agent:" },
    "correlation_id": { "type": "string" },
    "payload": {
      "type": "object",
      "properties": {
        "request_id": { "type": "string" },
        "budget_type": {
          "type": "string",
          "enum": ["daily_tokens", "daily_cost", "request_tokens", "request_cost"]
        },
        "budget_limit": { "type": "number" },
        "budget_used": { "type": "number" },
        "budget_remaining": { "type": "number" },
        "reset_at": {
          "type": "string",
          "format": "date-time",
          "description": "When daily budget resets, if applicable"
        },
        "project_id": { "type": "string" }
      },
      "required": ["request_id", "budget_type", "budget_limit", "budget_used"]
    }
  },
  "required": ["event_id", "event_type", "timestamp", "version", "agent_did", "correlation_id", "payload"]
}
```

#### F.9 model.provider.failed

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-system.internal/schemas/l04/events/model.provider.failed.schema.json",
  "title": "Model Provider Failed Event",
  "type": "object",
  "properties": {
    "event_id": { "type": "string", "format": "uuid" },
    "event_type": { "const": "model.provider.failed" },
    "timestamp": { "type": "string", "format": "date-time" },
    "version": { "const": "1.0.0" },
    "agent_did": { "type": "string", "pattern": "^did:agent:" },
    "correlation_id": { "type": "string" },
    "payload": {
      "type": "object",
      "properties": {
        "request_id": { "type": "string" },
        "provider": { "type": "string" },
        "model": { "type": "string" },
        "error_type": {
          "type": "string",
          "enum": ["timeout", "rate_limited", "server_error", "auth_error", "network_error", "invalid_response"]
        },
        "error_code": { "type": "string" },
        "error_message": { "type": "string" },
        "request_latency_ms": { "type": "integer" },
        "retry_attempted": { "type": "boolean" },
        "fallback_triggered": { "type": "boolean" }
      },
      "required": ["request_id", "provider", "model", "error_type"]
    }
  },
  "required": ["event_id", "event_type", "timestamp", "version", "agent_did", "correlation_id", "payload"]
}
```

#### F.10 model.circuit.opened

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-system.internal/schemas/l04/events/model.circuit.opened.schema.json",
  "title": "Model Circuit Opened Event",
  "type": "object",
  "properties": {
    "event_id": { "type": "string", "format": "uuid" },
    "event_type": { "const": "model.circuit.opened" },
    "timestamp": { "type": "string", "format": "date-time" },
    "version": { "const": "1.0.0" },
    "agent_did": { "type": "string", "pattern": "^did:agent:" },
    "correlation_id": { "type": "string" },
    "payload": {
      "type": "object",
      "properties": {
        "provider": { "type": "string" },
        "failure_count": { "type": "integer" },
        "failure_threshold": { "type": "integer" },
        "failure_window_seconds": { "type": "integer" },
        "cooldown_seconds": { "type": "integer" },
        "next_retry_at": {
          "type": "string",
          "format": "date-time"
        },
        "recent_errors": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "error_type": { "type": "string" },
              "timestamp": { "type": "string", "format": "date-time" }
            }
          },
          "maxItems": 5
        }
      },
      "required": ["provider", "failure_count", "failure_threshold", "cooldown_seconds"]
    }
  },
  "required": ["event_id", "event_type", "timestamp", "version", "correlation_id", "payload"]
}
```

#### F.11 model.circuit.closed

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-system.internal/schemas/l04/events/model.circuit.closed.schema.json",
  "title": "Model Circuit Closed Event",
  "type": "object",
  "properties": {
    "event_id": { "type": "string", "format": "uuid" },
    "event_type": { "const": "model.circuit.closed" },
    "timestamp": { "type": "string", "format": "date-time" },
    "version": { "const": "1.0.0" },
    "agent_did": { "type": "string", "pattern": "^did:agent:" },
    "correlation_id": { "type": "string" },
    "payload": {
      "type": "object",
      "properties": {
        "provider": { "type": "string" },
        "previous_state": {
          "type": "string",
          "enum": ["OPEN", "HALF_OPEN"]
        },
        "time_in_open_state_seconds": { "type": "integer" },
        "recovery_success_count": {
          "type": "integer",
          "description": "Number of successful requests during HALF_OPEN before closing"
        },
        "recovery_success_threshold": { "type": "integer" }
      },
      "required": ["provider", "previous_state", "time_in_open_state_seconds"]
    }
  },
  "required": ["event_id", "event_type", "timestamp", "version", "correlation_id", "payload"]
}
```


---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.2.0 | January 04, 2026 | Architecture Team | Industry validation integration (D.4): Integrated all 17 findings (3 P1, 9 P2, 5 P3). Added Prompt Safety Filter (P1-001), Response Safety Filter (P1-002), credential compromise detection (P1-003), OTel GenAI conventions (P2-001), adaptive rate limiting (P2-002), router lifecycle hooks (P2-003), request metadata passthrough (P2-004), full capture mode (P2-005), data residency routing (P2-006), provisioned throughput support (P2-007), hierarchical budget management (P2-008), active health probing (P2-009), dynamic pricing (P3-001), multi-region failover (P3-002), streaming metrics (P3-003), cache warming (P3-004), quality-aware routing (P3-005). |
| 1.0.1 | January 04, 2026 | Architecture Team | Validation fixes: Added 8 event schemas (F.4-F.11), explicit Python 3.11+ language decision |
| 1.0.0 | January 04, 2026 | Architecture Team | Initial specification: Merged from Parts 1-3 |

---

## Appendix G: Industry Validation Integration Summary

### G.1 Integration Tracking

All findings from the Industry Standards Validation Report (D.3) have been integrated into this specification.

**P1 (Critical - Security/Reliability):**

| ID | Finding | Section Updated | How Addressed |
|----|---------|-----------------|---------------|
| P1-001 | Prompt injection detection | 2.2, 3.3.4 | Added Prompt Safety Filter component; updated scope note |
| P1-002 | Response content safety scanning | 3.3.5.1 | Added Response Safety Filter component |
| P1-003 | Credential compromise detection | 8.5 | Added T10 threat; credential anomaly detection |

**P2 (Operational Improvement):**

| ID | Finding | Section Updated | How Addressed |
|----|---------|-----------------|---------------|
| P2-001 | OTel GenAI semantic conventions | 9.1 | Added attribute mapping table; updated metric names |
| P2-002 | Adaptive rate limiting | 3.3.5 (Rate Limiter) | Added AdaptiveRateLimiter class; configuration |
| P2-003 | Router lifecycle hooks | 3.3.2 | Added hook registry; 4 lifecycle hooks defined |
| P2-004 | Request metadata passthrough | 4.1.1 | Added metadata field to InferenceRequest/Response |
| P2-005 | Full request/response capture | 9.3.3 | Added FullCaptureLogger; capture configuration |
| P2-006 | Data residency aware routing | 3.3.1, 3.3.2, 4.1.1 | Added regions to model registry; routing filter |
| P2-007 | Provisioned throughput support | 3.3.1 | Added PTU tracking; effective cost calculation |
| P2-008 | Hierarchical budget management | 3.3.5 (Rate Limiter) | Added org/project/agent hierarchy; override API |
| P2-009 | Active provider health probing | 3.3.6 | Added ActiveHealthProber; probe configuration |

**P3 (Future Consideration):**

| ID | Finding | Section Updated | How Addressed |
|----|---------|-----------------|---------------|
| P3-001 | Dynamic pricing integration | 3.3.1 | Added PricingRefresher; model.pricing.updated event |
| P3-002 | Multi-region failover | 3.3.6 | Added RegionalCircuitBreaker; region-aware failover |
| P3-003 | Streaming-specific metrics | 9.1.1 | Added TTFT, ITL, duration metrics |
| P3-004 | Cache warming strategy | 3.3.3 | Added CacheWarmer; warming API endpoint |
| P3-005 | Quality-aware routing | 3.3.2 | Added quality-optimized strategy; quality scores |

### G.2 Standards Compliance Matrix (Updated)

| Standard | Requirement | L04 Compliance | Version |
|----------|-------------|----------------|---------|
| OWASP API Security Top 10 | All 10 categories | Compliant | 1.0+ |
| OpenTelemetry GenAI | Semantic conventions | Compliant | 1.2 |
| OpenTelemetry Tracing | Span propagation | Compliant | 1.0+ |
| OpenTelemetry Metrics | Prometheus format | Compliant | 1.0+ |
| Prometheus Best Practices | Naming, labels | Compliant | 1.0+ |
| Kubernetes Best Practices | Health probes, resource limits | Compliant | 1.0+ |
| 12-Factor App | Config, logging, disposability | Compliant | 1.0+ |
| SRE Principles | SLOs, error budgets | Compliant | 1.0+ |

---

*Document generated by Model Gateway Layer specification project*
*Layer ID: L04*
*Last Modified: January 04, 2026*

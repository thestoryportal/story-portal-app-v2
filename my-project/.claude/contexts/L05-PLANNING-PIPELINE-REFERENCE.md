# L05 Planning Pipeline - Implementation Reference

## Overview

The L05 Planning Pipeline decomposes high-level goals into executable task plans using a hybrid strategy: cache → template → LLM. This document captures all debugging, fixes, and enhancements made to the pipeline.

## Test Command

```bash
python3 -m pytest platform/src/L05_planning/tests --tb=short -q
```

**Expected result**: 248 tests pass

---

## Completed Fixes (Jan 2026)

### P1: DateTime Deprecation Fix

**Problem**: Python 3.14+ deprecates `datetime.utcnow()` - raises errors, not just warnings.

**Solution**: Replace with timezone-aware datetime:
```python
# Before
from datetime import datetime
created_at: datetime = field(default_factory=datetime.utcnow)
self.started_at = datetime.utcnow()

# After
from datetime import datetime, timezone
created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
self.started_at = datetime.now(timezone.utc)
```

**Files Modified**:
- L05 models: `goal.py`, `task.py`, `plan.py`, `agent.py`
- L05 services: `goal_decomposer.py`, `planning_service.py`, `task_orchestrator.py`, `agent_assigner.py`, `execution_monitor.py`, `plan_cache.py`
- L05 adapters: `cli_plan_adapter.py`
- L02 bridges: `model_gateway_bridge.py`, `l01_bridge.py`
- L04 models: `inference_request.py`, `inference_response.py`
- L04 providers: `base.py`, `mock_adapter.py`, `ollama_adapter.py`, `openai_adapter.py`, `anthropic_adapter.py`
- L04 services: `model_gateway.py`, `circuit_breaker.py`, `request_queue.py`, `semantic_cache.py`
- shared: `events.py`

---

### P0: L01 API Authentication Fix

**Problem**: `L01Client` in `shared/clients.py` was making HTTP requests without authentication headers, causing 401 Unauthorized errors when L01 service is running.

**Solution**: Added API key support to L01Client:

```python
# shared/clients.py
class L01Client:
    def __init__(
        self,
        base_url: str = "http://localhost:8002",
        timeout: float = 30.0,
        api_key: Optional[str] = None  # NEW
    ):
        self.api_key = api_key or os.getenv("L01_API_KEY", "dev_key_local_ONLY")

    async def _get_client(self) -> httpx.AsyncClient:
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,  # NEW
        }
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=headers
        )
```

**Files Modified**:
- `platform/src/shared/clients.py` - Added `api_key` parameter and `X-API-Key` header
- `platform/src/L05_planning/integration/l01_bridge.py` - Updated fallback key to `dev_key_local_ONLY`
- `platform/src/L05_planning/tests/conftest.py` - Added `l01_bridge` and `initialized_l01_bridge` fixtures

**Environment Variable**: `L01_API_KEY` (fallback: `dev_key_local_ONLY`)

---

### P2: LLM Response Validation & Retry Fix

**Problem**: LLM sometimes returns markdown-formatted text instead of JSON, causing parse failures:
```
ERROR Failed to parse LLM response as JSON: Expecting value: line 1 column 1 (char 0)
content: 'Here are the decomposed tasks...\n\n**Task 1:**...'
```

**Solution**: Added retry logic and improved JSON extraction in `goal_decomposer.py`:

1. **Retry Logic** (up to 2 retries):
   - First attempt: Standard decomposition prompt
   - Retries: Stricter JSON-only prompt with lower temperature (0.1)

2. **Multi-Strategy JSON Extraction** (`_extract_json_from_content()`):
   - Strategy 1: ````json` code blocks
   - Strategy 2: Generic ``` code blocks
   - Strategy 3: Brace matching for embedded JSON `{...}`
   - Strategy 4: Raw content as JSON

3. **New Methods**:
   - `_build_decomposition_prompt()` - Standard prompt
   - `_build_strict_json_prompt()` - JSON-only prompt for retries
   - `_extract_json_from_content()` - Multi-strategy extraction

**Key Code** (goal_decomposer.py):
```python
async def _decompose_llm(self, goal: Goal, max_retries: int = 2) -> ExecutionPlan:
    for attempt in range(max_retries + 1):
        try:
            if attempt == 0:
                system_prompt = self._build_decomposition_prompt()
            else:
                system_prompt = self._build_strict_json_prompt()

            # Lower temperature on retries
            temperature = 0.1 if attempt > 0 else 0.3

            response = await self.gateway_client.execute(request)
            plan = self._parse_llm_response(goal, response.content, response)
            return plan

        except PlanningError as e:
            if e.error_code == ErrorCode.E5106:  # Parse error
                if attempt < max_retries:
                    continue
            raise
```

---

## Architecture Overview

```
L05 Planning Pipeline Flow:
┌─────────────────────────────────────────────────────────────┐
│  Goal Input                                                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  GoalDecomposer.decompose(goal)                             │
│  ├── 1. Validate goal                                       │
│  ├── 2. Check cache (PlanCache)                             │
│  ├── 3. Try template matching (TemplateRegistry)            │
│  ├── 4. Fall back to LLM (L04 ModelGateway)                │
│  ├── 5. Parse response → ExecutionPlan                      │
│  ├── 6. Sign plan (HMAC-SHA256)                            │
│  └── 7. Cache plan                                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  ExecutionPlan with Tasks                                   │
│  ├── Tasks with dependencies                                │
│  ├── Metadata (strategy, tokens, latency)                   │
│  └── Signature for verification                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Files

| File | Purpose |
|------|---------|
| `L05_planning/services/goal_decomposer.py` | Core decomposition logic with LLM/template hybrid |
| `L05_planning/services/planning_service.py` | High-level planning service orchestration |
| `L05_planning/services/plan_cache.py` | L1 (memory) + L2 (Redis) caching |
| `L05_planning/models/goal.py` | Goal data model |
| `L05_planning/models/task.py` | Task data model with dependencies |
| `L05_planning/models/plan.py` | ExecutionPlan data model |
| `L05_planning/integration/l01_bridge.py` | Bridge to L01 Data Layer |
| `L05_planning/tests/conftest.py` | Test fixtures |
| `shared/clients.py` | L01Client with auth support |

---

## Common Issues & Solutions

### Issue: 401 Unauthorized to L01
**Cause**: Missing API key in L01Client
**Solution**: Set `L01_API_KEY` env var or use default `dev_key_local_ONLY`

### Issue: JSON parse errors from LLM
**Cause**: LLM returns markdown instead of JSON
**Solution**: P2 fix adds retry logic and multi-strategy extraction

### Issue: DeprecationWarning for datetime.utcnow()
**Cause**: Python 3.12+ deprecation
**Solution**: P1 fix replaces with `datetime.now(timezone.utc)`

### Issue: Test failures in L05 after L04 changes
**Cause**: Cross-layer dependencies (L05 → L02 → L04)
**Solution**: Ensure datetime fix applied to all layers in execution chain

---

## Error Codes

| Code | Name | Description |
|------|------|-------------|
| E5004 | INVALID_GOAL | Goal validation failed |
| E5100 | DECOMPOSITION_ERROR | General decomposition failure |
| E5101 | LLM_DECOMPOSITION_FAILED | LLM-based decomposition failed |
| E5102 | NO_TEMPLATE_MATCH | No template matched the goal |
| E5103 | INVALID_STRATEGY | Unknown decomposition strategy |
| E5106 | LLM_PARSE_ERROR | Failed to parse LLM response |

---

## Commits

```
6530174 fix(L05): complete planning pipeline fixes - datetime, auth, LLM validation
3e416fb feat(L05): wire AgentAssigner and ExecutionMonitor to L01 + fix import paths
8dac8d2 fix(L02): correct cross-layer import paths for MCP execution
203eaf3 checkpoint(L05): mark pipeline complete with milestone checkpoint
```

---

## Testing Notes

- Tests run without `-W ignore::DeprecationWarning` flag
- L01 bridge tests use local fallback when L01 service unavailable
- LLM decomposition tests may hit rate limits on external providers
- Integration tests marked with `@pytest.mark.integration` require running services

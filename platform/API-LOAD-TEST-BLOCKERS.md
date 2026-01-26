# API Load Test Blockers - Week 9 Day 3

**Date**: 2026-01-19
**Status**: 🔴 **BLOCKED** - 36.32% failure rate
**Priority**: P0 (Production Blocker)

---

## Executive Summary

Initial smoke test revealed **409 failures out of 1126 requests (36.32% error rate)**, significantly exceeding the 1% threshold. Root cause analysis identified 3 specific L01 Data Layer implementation issues causing 100% failure rates on 4 endpoints.

**Key Finding**: Day 2 API Gateway fix is working correctly - the issue is in L01 endpoint implementations, not routing.

---

## Test Results Summary

```
Total Requests:      1,126
Successful:          717 (63.68%)
Failed:              409 (36.32%) ❌ EXCEEDS 1% THRESHOLD
P95 Response Time:   29.61ms ✅ WITHIN 500ms THRESHOLD
```

**Performance**: Excellent (P95: 29.61ms)
**Reliability**: Unacceptable (36.32% error rate)

---

## Failure Breakdown

### Failed Endpoints (100% Failure Rate)

| Endpoint | Method | Failures | Total | Failure Rate | Error |
|----------|--------|----------|-------|--------------|-------|
| `/api/v1/goals/` | POST | 145 | 145 | 100% | 500 Internal Server Error |
| `/api/v1/tasks/` | POST | 137 | 137 | 100% | 500 Internal Server Error |
| `/api/v1/agents/{id}` | GET | 79 | 79 | 100% | 500 Internal Server Error |
| `/api/v1/agents/{id}` | PATCH | 48 | 48 | 100% | 422 Unprocessable Entity |

### Working Endpoints (0% Failure Rate)

| Endpoint | Method | Requests | Failures | Success Rate |
|----------|--------|----------|----------|--------------|
| `/api/v1/agents/` | POST | 13 | 0 | 100% ✅ |
| `/api/v1/agents/` | GET | 252 | 0 | 100% ✅ |
| `/api/v1/agents/{id}` | DELETE | 21 | 0 | 100% ✅ |
| `/api/v1/goals/` | GET | 279 | 0 | 100% ✅ |

---

## Root Cause Analysis

### Issue 1: POST /api/v1/goals/ - KeyError: 'goal_id'

**File**: `platform/src/L01_data_layer/routers/goals.py:41`

**Error from L01 Logs**:
```
KeyError: 'goal_id'
```

**Root Cause**: Schema mismatch between L01Client and L01 endpoint

**Flow**:
1. L09 API Gateway calls `l01_client.create_goal()` (platform/src/L09_api_gateway/routers/v1/goals.py:54)
2. L01Client sends payload WITHOUT `goal_id` (platform/shared/clients/l01_client.py:307-312):
   ```python
   response = await client.post("/goals/", json={
       "agent_id": str(agent_id),
       "description": description,
       "success_criteria": success_criteria or [],
       "priority": priority,
   })
   ```
3. L01 endpoint expects `goal_id` in payload (platform/src/L01_data_layer/routers/goals.py:41):
   ```python
   row = await conn.fetchrow(
       query,
       goal_data["goal_id"],  # ❌ KeyError - this key doesn't exist!
       goal_data.get("agent_id"),
       ...
   )
   ```

**Expected Behavior**: L01 endpoint should generate `goal_id` using UUID, not expect it from client.

**Fix Required**: Modify L01 goals router to generate goal_id

---

### Issue 2: GET /api/v1/agents/{id} - 500 Internal Server Error

**File**: `platform/src/L01_data_layer/routers/agents.py:30-35`

**Error**: 500 Internal Server Error (need to check agent registry implementation)

**Flow**:
1. L09 calls L01Client.get_agent(agent_id) (platform/shared/clients/l01_client.py:58-63)
2. L01 endpoint delegates to AgentRegistry.get_agent() (platform/src/L01_data_layer/routers/agents.py:32)
3. AgentRegistry.get_agent() is throwing an unhandled exception

**Known Issue**: Day 2 completion report noted: "⚠️ L01 Issue - L09 working, L01 returns 500 error"

**Fix Required**: Debug AgentRegistry.get_agent() implementation or add error handling

---

### Issue 3: PATCH /api/v1/agents/{id} - 422 Unprocessable Entity

**File**: `platform/src/L01_data_layer/routers/agents.py:37-42`

**Error**: 422 Unprocessable Entity (validation error)

**Root Cause**: Payload doesn't match AgentUpdate Pydantic model schema

**Flow**:
1. Load test sends generic update payload (locustfile-api.py:189-193):
   ```python
   payload = {
       "status": random.choice(["active", "inactive", "paused"]),
       "configuration": {"max_tokens": random.randint(100, 2000)}
   }
   ```
2. L01 endpoint expects AgentUpdate model (platform/src/L01_data_layer/routers/agents.py:38):
   ```python
   async def update_agent(agent_id: UUID, agent_data: AgentUpdate, ...):
   ```
3. Pydantic validation rejects payload because fields don't match AgentUpdate schema

**Fix Required**: Either:
- Option A: Check AgentUpdate model and update load test to use valid fields
- Option B: Make L01 endpoint accept generic dict like goals/plans routers

---

### Issue 4: POST /api/v1/tasks/ - 405 Method Not Allowed

**File**: `platform/shared/clients/l01_client.py:375` and `platform/src/L01_data_layer/routers/plans.py`

**Error**: 405 Method Not Allowed

**Root Cause**: L01Client calls non-existent endpoint

**Flow**:
1. L09 calls L01Client.create_task() (platform/src/L09_api_gateway/routers/v1/tasks.py:53-59)
2. L01Client tries to POST to `/plans/tasks` (platform/shared/clients/l01_client.py:375):
   ```python
   response = await client.post("/plans/tasks", json={...})
   ```
3. L01 plans router has NO `/plans/tasks` POST endpoint (only has `/plans/` endpoints)

**Available Endpoints in plans.py**:
- POST /plans/ (line 14)
- GET /plans/{plan_id} (line 59)
- PATCH /plans/{plan_id} (line 71)
- GET /plans/ (line 152)

**Missing**: POST /plans/tasks

**Fix Required**: Either:
- Option A: Add `/plans/tasks` endpoint to plans.py
- Option B: Create separate tasks.py router in L01
- Option C: Update L01Client to use different endpoint structure

---

## Recommended Fixes

### Priority 1: Fix POST /api/v1/goals/ (145 failures)

**File to Modify**: `platform/src/L01_data_layer/routers/goals.py`

**Change Line 41** from:
```python
goal_data["goal_id"],
```

**To**:
```python
str(uuid4()),  # Generate goal_id server-side
```

**Add Import**:
```python
from uuid import uuid4
```

**Also Update L01 Endpoint** to accept simpler schema matching L01Client payload:
- Remove requirement for `goal_id` in payload
- Remove requirement for `agent_did` (can default or derive from agent_id)
- Map `description` field to `goal_text` field in database

---

### Priority 2: Fix POST /api/v1/tasks/ (137 failures)

**Option A (Recommended)**: Add tasks endpoint to plans router

**File**: `platform/src/L01_data_layer/routers/plans.py`

**Add after line 191**:
```python
@router.post("/tasks", status_code=201)
async def create_task(task_data: dict):
    """Create a new task under a plan."""
    query = """
        INSERT INTO tasks (
            task_id, plan_id, agent_id, description, task_type,
            status, input_data, created_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, NOW()
        )
        RETURNING *
    """

    async with db.pool.acquire() as conn:
        task_id = str(uuid4())
        input_data_json = json.dumps(task_data.get("input_data", {}))

        row = await conn.fetchrow(
            query,
            task_id,
            task_data["plan_id"],
            task_data.get("agent_id"),
            task_data["description"],
            task_data.get("task_type", "generic"),
            "pending",
            input_data_json
        )

        return dict(row)
```

---

### Priority 3: Fix GET /api/v1/agents/{id} (79 failures)

**Investigation Required**: Check AgentRegistry.get_agent() implementation

**Possible Fix**: Add error handling in agents router:
```python
@router.get("/{agent_id}", response_model=Agent)
async def get_agent(agent_id: UUID, registry: AgentRegistry = Depends(get_agent_registry)):
    try:
        agent = await registry.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent
    except Exception as e:
        logger.error(f"Failed to get agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
```

---

### Priority 4: Fix PATCH /api/v1/agents/{id} (48 failures)

**Investigation Required**: Check AgentUpdate model schema

**Temporary Fix**: Make endpoint accept dict like other routers:
```python
@router.patch("/{agent_id}", response_model=Agent)
async def update_agent(agent_id: UUID, agent_data: dict, registry: AgentRegistry = Depends(get_agent_registry)):
    # Validate only known fields
    allowed_fields = {"status", "configuration", "metadata"}
    updates = {k: v for k, v in agent_data.items() if k in allowed_fields}

    agent = await registry.update_agent(agent_id, updates)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent
```

---

## Testing Strategy

### After Fixes Applied

1. **Direct L01 Testing** (bypass L09):
   ```bash
   # Test goal creation
   curl -X POST http://localhost:8001/goals/ \
     -H "Content-Type: application/json" \
     -H "X-API-Key: dev_key_CHANGE_IN_PRODUCTION" \
     -d '{
       "agent_id": "test-uuid",
       "description": "Test goal",
       "success_criteria": [],
       "priority": 5
     }'

   # Test task creation
   curl -X POST http://localhost:8001/plans/tasks \
     -H "Content-Type: application/json" \
     -H "X-API-Key: dev_key_CHANGE_IN_PRODUCTION" \
     -d '{
       "plan_id": "test-plan-uuid",
       "agent_id": "test-agent-uuid",
       "description": "Test task"
     }'
   ```

2. **Via L09 Gateway**:
   ```bash
   # Test via API Gateway
   curl -X POST http://localhost:8009/api/v1/goals/ \
     -H "Content-Type: application/json" \
     -H "X-API-Key: 12345678901234567890123456789012" \
     -d '{
       "agent_id": "existing-agent-uuid",
       "description": "Test goal",
       "success_criteria": ["criterion1"],
       "priority": 5
     }'
   ```

3. **Re-run Smoke Test**:
   ```bash
   cd platform/load-tests
   ../.venv-loadtest/bin/locust -f locustfile-api.py \
     --host=http://localhost:8009 \
     --users 20 \
     --spawn-rate 5 \
     --run-time 2m \
     --headless
   ```

4. **Success Criteria**:
   - Error rate < 1% (currently 36.32%)
   - All 4 failing endpoints now have 0% failure rate
   - P95 response time remains < 500ms

---

## Impact Assessment

**Current State**:
- ❌ Cannot proceed with full API load testing
- ❌ Platform not production-ready for API-dependent features
- ✅ API Gateway routing working correctly (Day 2 fix successful)
- ✅ Performance excellent when endpoints work

**After Fixes**:
- ✅ Full API load test suite can proceed
- ✅ All CRUD operations functional
- ✅ Production launch preparation can continue

**Estimated Fix Time**: 2-3 hours
- Priority 1 (goals): 30 minutes
- Priority 2 (tasks): 45 minutes
- Priority 3 (agents GET): 30 minutes
- Priority 4 (agents PATCH): 30 minutes
- Testing: 45 minutes

---

## Files Requiring Changes

1. **platform/src/L01_data_layer/routers/goals.py** (fix goal_id generation)
2. **platform/src/L01_data_layer/routers/plans.py** (add tasks endpoint)
3. **platform/src/L01_data_layer/routers/agents.py** (fix GET/PATCH)
4. **platform/src/L01_data_layer/services/agent_registry.py** (possibly - need to check)

---

## Next Steps

1. ✅ Root cause analysis complete
2. 🔄 Apply fixes to L01 routers
3. ⏳ Test fixes via direct L01 calls
4. ⏳ Test fixes via L09 Gateway
5. ⏳ Re-run smoke test
6. ⏳ Execute full load test suite (47 minutes)
7. ⏳ Document API performance baselines
8. ⏳ Create Week 9 Day 3 completion report

---

**Report Created**: 2026-01-19
**Test Execution**: platform/load-tests/reports/api-smoke-day3.html
**L01 Logs**: docker logs l01-data-layer --tail 200
**Status**: 🔴 BLOCKED - Awaiting L01 fixes

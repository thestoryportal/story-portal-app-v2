# Service 39/44: GoalDecomposer

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L05 (Planning Layer) |
| **Module** | `L05_planning.services.goal_decomposer` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | L04 Model Gateway, PlanCache, TemplateRegistry |
| **Category** | Planning / Decomposition |

## Role in Development Environment

The **GoalDecomposer** transforms high-level goals into executable task plans using a hybrid decomposition strategy. It provides:
- Hybrid decomposition: cache → template → LLM
- Template-based decomposition with pattern matching
- LLM-based decomposition via L04 Model Gateway
- Plan caching for repeated goals
- HMAC-SHA256 plan signing for integrity
- Pattern extraction for goal classification
- Template suggestion based on confidence scores

This is **the goal-to-tasks transformer** - when a goal comes in, GoalDecomposer figures out the best way to break it down into specific, executable tasks.

## Data Model

### Goal (Input)
- `goal_id: str` - Unique goal identifier
- `goal_text: str` - Natural language goal description
- `agent_did: str` - Agent DID for the goal
- `decomposition_strategy: str` - Strategy (hybrid, llm, template)

### ExecutionPlan (Output)
- `plan_id: str` - Unique plan identifier
- `goal_id: str` - Related goal ID
- `tasks: List[Task]` - Decomposed tasks
- `dependency_graph: Dict` - Task dependencies
- `signature: str` - HMAC-SHA256 signature
- `metadata: PlanMetadata` - Decomposition metadata

### Task
- `task_id: str` - Unique task identifier
- `plan_id: str` - Parent plan ID
- `name: str` - Task name
- `description: str` - Task description
- `task_type: TaskType` - Type (atomic, compound, tool_call, llm_call)
- `dependencies: List[TaskDependency]` - Task dependencies
- `inputs: Dict` - Required inputs
- `timeout_seconds: int` - Execution timeout

### DecompositionStrategy
- `hybrid` - Try template first, fall back to LLM (recommended)
- `template` - Template-only, fails if no match
- `llm` - LLM-only, always uses L04 gateway

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `cache` | PlanCache() | Plan cache instance |
| `template_registry` | TemplateRegistry() | Template registry |
| `gateway_client` | None | L04 Model Gateway client |
| `hmac_secret` | "L05-planning-secret-key" | Secret for plan signing |
| `max_goal_length` | 100,000 | Maximum goal text length |
| `default_strategy` | "hybrid" | Default decomposition strategy |

## API Methods

| Method | Description |
|--------|-------------|
| `decompose(goal)` | Decompose goal into execution plan |
| `verify_plan_signature(plan)` | Verify plan integrity |
| `extract_pattern(goal)` | Extract reusable pattern from goal |
| `suggest_template(goal)` | Suggest matching template |
| `get_stats()` | Get decomposer statistics |
| `get_health_status()` | Get health status |

## Use Cases in Your Workflow

### 1. Initialize Goal Decomposer
```python
from L05_planning.services.goal_decomposer import GoalDecomposer
from L04_model_gateway.services.model_gateway import ModelGateway

# Default initialization (template-only)
decomposer = GoalDecomposer()

# With LLM support
gateway = ModelGateway()
decomposer = GoalDecomposer(
    gateway_client=gateway,
    default_strategy="hybrid"
)
```

### 2. Decompose Goal with Hybrid Strategy
```python
from L05_planning.models import Goal

# Create goal
goal = Goal.create(
    agent_did="did:agent:abc123",
    goal_text="Create a REST API for user management",
    decomposition_strategy="hybrid"
)

# Decompose
plan = await decomposer.decompose(goal)

print(f"Plan ID: {plan.plan_id}")
print(f"Strategy used: {plan.metadata.decomposition_strategy}")
print(f"Tasks created: {len(plan.tasks)}")
for task in plan.tasks:
    print(f"  - {task.name} ({task.task_type.value})")
```

### 3. Force Template-Only Decomposition
```python
# Create goal with template strategy
goal = Goal.create(
    agent_did="did:agent:abc123",
    goal_text="Deploy application to production",
    decomposition_strategy="template"
)

try:
    plan = await decomposer.decompose(goal)
    print(f"Template used: {plan.metadata.tags}")
except PlanningError as e:
    print(f"No matching template found: {e.message}")
```

### 4. Force LLM Decomposition
```python
# Create goal with LLM strategy
goal = Goal.create(
    agent_did="did:agent:abc123",
    goal_text="Implement a novel recommendation algorithm",
    decomposition_strategy="llm"
)

plan = await decomposer.decompose(goal)

print(f"LLM model used: {plan.metadata.llm_model}")
print(f"Tokens used: {plan.metadata.total_tokens_used}")
```

### 5. Verify Plan Signature
```python
# Create and sign plan
plan = await decomposer.decompose(goal)

# Later, verify integrity
is_valid = decomposer.verify_plan_signature(plan)

if is_valid:
    print("Plan signature valid - plan unmodified")
else:
    print("Plan signature invalid - plan may be tampered")
```

### 6. Extract Goal Pattern
```python
# Extract reusable pattern from goal
pattern = await decomposer.extract_pattern(goal)

print(f"Goal type: {pattern['goal_type']}")
print(f"Entities: {pattern['entities']}")
print(f"Action verbs: {pattern['action_verbs']}")
print(f"Complexity: {pattern['complexity']}")
```

### 7. Suggest Template
```python
# Get template suggestion for goal
suggestion = await decomposer.suggest_template(goal)

if suggestion:
    print(f"Template: {suggestion['template_name']}")
    print(f"Confidence: {suggestion['confidence']:.2f}")
    print(f"Recommended: {suggestion['recommended']}")
    print(f"Extracted params: {suggestion['extracted_params']}")
else:
    print("No matching template found")
```

### 8. Get Decomposer Statistics
```python
stats = decomposer.get_stats()

print(f"Total decompositions: {stats['decompositions_total']}")
print(f"Cache hits: {stats['cache_hits']}")
print(f"Cache hit rate: {stats['cache_hit_rate']:.1%}")
print(f"Template decompositions: {stats['template_decompositions']}")
print(f"LLM decompositions: {stats['llm_decompositions']}")
print(f"Failures: {stats['decomposition_failures']}")
print(f"Failure rate: {stats['failure_rate']:.1%}")
```

### 9. Check Health Status
```python
health = decomposer.get_health_status()

print(f"Healthy: {health['healthy']}")
print(f"Template count: {health['template_count']}")
print(f"Gateway available: {health['gateway_available']}")
print(f"Cache available: {health['cache_available']}")
```

### 10. Custom Template Registration
```python
from L05_planning.templates import TaskTemplate, TemplateRegistry

# Create custom template
template = TaskTemplate(
    template_id="custom-api-template",
    name="API Endpoint Template",
    pattern=r"create.*api.*endpoint",
    tasks=[
        {"name": "Define schema", "type": "atomic"},
        {"name": "Implement handler", "type": "atomic"},
        {"name": "Add validation", "type": "atomic"},
        {"name": "Write tests", "type": "atomic"},
    ]
)

# Register with decomposer
decomposer.template_registry.register(template)
```

## Service Interactions

```
+------------------+
|  GoalDecomposer  | <--- L05 Planning Layer
|      (L05)       |
+--------+---------+
         |
   Uses:
         |
+--------+--------+--------+
|        |        |        |
v        v        v        v
Template PlanCache L04      HMAC
Registry          Gateway   Signer
(Match)  (Cache)  (LLM)    (Sign)
```

**Integration Points:**
- **PlanCache (L05)**: Caches decomposed plans
- **TemplateRegistry (L05)**: Pattern-matched templates
- **ModelGateway (L04)**: LLM-based decomposition
- **PlanningService (L05)**: Uses decomposer for goals

## Decomposition Strategies

### Hybrid Strategy (Recommended)
```
1. Check cache for exact/similar goal
   └─> If hit: return cached plan

2. Try template matching
   └─> If confidence > 0.85: use template

3. Fall back to LLM
   └─> Generate tasks via L04 gateway

4. Sign and cache result
```

### Template Strategy
```
1. Check cache for exact/similar goal
   └─> If hit: return cached plan

2. Try template matching
   └─> If match found: use template
   └─> Else: raise E5102 error

3. Sign and cache result
```

### LLM Strategy
```
1. Check cache for exact/similar goal
   └─> If hit: return cached plan

2. Generate via LLM
   └─> Send goal to L04 gateway
   └─> Parse JSON response
   └─> Build task graph

3. Sign and cache result
```

## LLM Decomposition

### Prompt Structure
```
System: You are a task planning assistant. Your job is to
decompose high-level goals into specific, executable tasks.

For each task, provide:
- id: unique identifier
- name: brief task name
- description: detailed description
- type: one of [atomic, compound, tool_call, llm_call]
- dependencies: list of task IDs this depends on
- inputs: required inputs
- timeout_seconds: estimated timeout

Output JSON format:
{
  "tasks": [...]
}

User: Decompose this goal into executable tasks:

{goal_text}
```

### Response Parsing
- Extracts JSON from markdown code blocks
- Maps LLM task IDs to UUIDs
- Builds dependency graph
- Creates Task objects

## Plan Signing

### HMAC-SHA256 Signature
```python
# Message structure
message = "|".join([
    plan.plan_id,
    plan.goal_id,
    json.dumps([t.task_id for t in plan.tasks]),
    json.dumps(plan.dependency_graph),
    str(int(plan.created_at.timestamp() * 1000))
])

# Compute signature
signature = hmac.new(secret, message, sha256).hexdigest()
```

## Error Codes

| Code | Description | Retryable |
|------|-------------|-----------|
| E5004 | Invalid goal | No |
| E5100 | General decomposition error | Maybe |
| E5101 | LLM decomposition failed | Yes |
| E5102 | No template match | No |
| E5103 | Invalid strategy | No |
| E5106 | LLM response parse error | Yes |

## Execution Examples

```python
# Complete goal decomposition workflow
from L05_planning.services.goal_decomposer import GoalDecomposer
from L05_planning.services.plan_cache import PlanCache
from L05_planning.models import Goal, PlanningError
from L04_model_gateway.services.model_gateway import ModelGateway

# Initialize with full capabilities
cache = PlanCache()
gateway = ModelGateway()

decomposer = GoalDecomposer(
    cache=cache,
    gateway_client=gateway,
    default_strategy="hybrid",
    hmac_secret="my-secure-secret"
)

# 1. Create a goal
goal = Goal.create(
    agent_did="did:agent:developer",
    goal_text="""
    Implement user authentication:
    1. Create login endpoint
    2. Implement JWT token generation
    3. Add password hashing
    4. Create logout endpoint
    5. Add rate limiting
    """,
    decomposition_strategy="hybrid"
)

print(f"Goal: {goal.goal_id}")

# 2. Check for template suggestion
suggestion = await decomposer.suggest_template(goal)
if suggestion:
    print(f"\nTemplate suggestion: {suggestion['template_name']}")
    print(f"Confidence: {suggestion['confidence']:.2f}")
    print(f"Recommended: {suggestion['recommended']}")

# 3. Extract pattern
pattern = await decomposer.extract_pattern(goal)
print(f"\nGoal pattern:")
print(f"  Type: {pattern['goal_type']}")
print(f"  Complexity: {pattern['complexity']}")
print(f"  Actions: {pattern['action_verbs']}")

# 4. Decompose goal
try:
    plan = await decomposer.decompose(goal)

    print(f"\nPlan created: {plan.plan_id}")
    print(f"Strategy: {plan.metadata.decomposition_strategy}")
    print(f"Tasks: {len(plan.tasks)}")

    for task in plan.tasks:
        deps = [d.task_id[:8] for d in task.dependencies]
        print(f"  [{task.task_id[:8]}] {task.name}")
        print(f"       Type: {task.task_type.value}")
        if deps:
            print(f"       Depends on: {deps}")

    print(f"\nLatency: {plan.metadata.decomposition_latency_ms:.0f}ms")

except PlanningError as e:
    print(f"Decomposition failed: {e.message}")
    print(f"Code: {e.code}")

# 5. Verify plan signature
is_valid = decomposer.verify_plan_signature(plan)
print(f"\nSignature valid: {is_valid}")

# 6. Decompose same goal again (should hit cache)
plan2 = await decomposer.decompose(goal)
print(f"\nSecond decomposition:")
print(f"  Cache hit: {plan2.metadata.cache_hit}")

# 7. Get statistics
stats = decomposer.get_stats()
print(f"\nDecomposer stats:")
print(f"  Total: {stats['decompositions_total']}")
print(f"  Cache hits: {stats['cache_hits']}")
print(f"  Cache hit rate: {stats['cache_hit_rate']:.1%}")
print(f"  Template: {stats['template_decompositions']}")
print(f"  LLM: {stats['llm_decompositions']}")
```

## Implementation Status

| Component | Status |
|-----------|--------|
| GoalDecomposer class | Complete |
| decompose() | Complete |
| Hybrid strategy | Complete |
| Template strategy | Complete |
| LLM strategy | Complete |
| Plan signing | Complete |
| Signature verification | Complete |
| Pattern extraction | Complete |
| Template suggestion | Complete |
| Cache integration | Complete |
| L04 integration | Complete |
| Statistics | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Template learning | High | Auto-create templates from successful LLM decompositions |
| Semantic caching | Medium | Cache based on goal similarity, not exact match |
| Multi-step decomposition | Medium | Iteratively refine complex goals |
| Confidence calibration | Low | Tune template confidence thresholds |
| Custom LLM prompts | Low | Allow per-goal prompt customization |
| Async template loading | Low | Load templates asynchronously |

## Strengths

- **Hybrid approach** - Best of templates and LLM
- **Fast for known patterns** - Template matching is instant
- **Flexible fallback** - LLM handles novel goals
- **Plan integrity** - HMAC signing prevents tampering
- **Caching** - Avoids redundant decomposition
- **Pattern extraction** - Analyzes goal structure

## Weaknesses

- **Secret management** - HMAC secret should come from vault
- **No template learning** - Doesn't auto-create templates
- **Fixed confidence threshold** - 0.85 may not be optimal
- **Single LLM call** - No iterative refinement
- **JSON parsing fragility** - Depends on LLM JSON format
- **No semantic cache** - Exact match only

## Best Practices

### Strategy Selection
Choose strategy based on goal type:
```python
# Well-known patterns (deploy, test, build)
goal.decomposition_strategy = "template"

# Novel or complex goals
goal.decomposition_strategy = "llm"

# Best for most cases (default)
goal.decomposition_strategy = "hybrid"
```

### Template Design
Create reusable templates:
```python
TaskTemplate(
    template_id="unique-id",
    name="Descriptive name",
    pattern=r"regex.*pattern",  # Match goal text
    tasks=[
        {"name": "Clear name", "type": "atomic"},
        # Include all common steps
    ]
)
```

### Error Handling
Handle decomposition failures:
```python
try:
    plan = await decomposer.decompose(goal)
except PlanningError as e:
    if e.code == ErrorCode.E5101:  # LLM failed
        # Retry with different model
        pass
    elif e.code == ErrorCode.E5102:  # No template
        # Fall back to LLM
        goal.decomposition_strategy = "llm"
        plan = await decomposer.decompose(goal)
```

### Signature Verification
Always verify before execution:
```python
if not decomposer.verify_plan_signature(plan):
    raise SecurityError("Plan signature invalid")
```

## Source Files

- Service: `platform/src/L05_planning/services/goal_decomposer.py`
- Templates: `platform/src/L05_planning/templates/`
- Cache: `platform/src/L05_planning/services/plan_cache.py`
- Models: `platform/src/L05_planning/models/`
- Spec: L05 Planning Layer specification

## Related Services

- PlanningService (L05) - Uses decomposer for goals
- PlanCache (L05) - Caches decomposed plans
- TemplateRegistry (L05) - Template management
- DependencyResolver (L05) - Resolves task dependencies
- PlanValidator (L05) - Validates decomposed plans
- ModelGateway (L04) - LLM inference for decomposition

---
*Generated: 2026-01-24 | Platform Services Documentation*

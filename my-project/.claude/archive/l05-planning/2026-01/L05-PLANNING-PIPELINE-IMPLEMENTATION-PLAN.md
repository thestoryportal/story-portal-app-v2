# L05 Planning Pipeline - Definitive Implementation Plan

**Purpose:** Provide Claude CLI with a failproof implementation plan to finally build a usable L05 Planning Pipeline
**Generated:** 2026-01-26
**Status:** Ready for implementation

---

## Executive Summary

The L05 Planning Pipeline has a well-designed architecture but **THREE CRITICAL EXECUTION GAPS** prevent it from working:

| Gap | Root Cause | Fix Required |
|-----|------------|--------------|
| **Gap 1: Execution Method Missing** | `execute_plan(plan_id)` raises E5002 | Implement OR add `execute_plan_direct` to MCP catalog |
| **Gap 2: Data Loss Between Gates** | Only `plan_id` stored, full `ExecutionPlan` lost | Serialize and persist full plan object |
| **Gap 3: MCP Catalog Incomplete** | Only 2 methods exposed, 6 services missing | Update service catalog with all methods |

**This plan uses a validation-first approach:** Every atomic unit has acceptance criteria that MUST be verified before proceeding.

---

## PHASE 0: PRE-FLIGHT VALIDATION (MANDATORY)

Before writing ANY code, Claude MUST complete these verification steps:

### 0.1 Verify Current State

```bash
# Run these commands and capture output
cd /Volumes/Extreme\ SSD/projects/story-portal-app/platform

# Check L05 services exist
ls -la src/L05_planning/services/

# Check parsers exist  
ls -la src/L05_planning/parsers/

# Check current catalog
cat ../my-project/L12_nl_interface/data/service_catalog.json | grep -A5 "PlanningService"

# Check hook files exist
ls -la ../my-project/.claude/hooks/
```

**Acceptance Criteria:**
- [ ] All service files exist
- [ ] All parser files exist  
- [ ] Catalog shows PlanningService with 2 methods
- [ ] Hook files exist (plan-mode-l05-hook.cjs, l05-bridge.py)

### 0.2 Verify Test Infrastructure

```bash
# Run existing L05 tests
cd /Volumes/Extreme\ SSD/projects/story-portal-app/platform
python -m pytest src/L05_planning/tests/ -v --tb=short 2>&1 | head -100
```

**Acceptance Criteria:**
- [ ] Tests run without import errors
- [ ] Record baseline: X tests passing, Y tests failing

### 0.3 Create Implementation Checkpoint

```bash
# Create backup before any changes
cd /Volumes/Extreme\ SSD/projects/story-portal-app
git stash push -m "pre-l05-implementation-$(date +%Y%m%d-%H%M%S)"
git log --oneline -1  # Record commit hash
```

**Acceptance Criteria:**
- [ ] Backup created
- [ ] Commit hash recorded: ________________

---

## PHASE 1: FIX CRITICAL GAP 1 - Execution Method

**Goal:** Make L05 execution actually work when called

### Unit 1.1: Implement execute_plan_direct in PlanningService

**File:** `platform/src/L05_planning/services/planning_service.py`

**Current Problem:** Only `execute_plan(plan_id)` exists, which tries to look up plan from cache and fails with E5002.

**Fix:** Add `execute_plan_direct(execution_plan: ExecutionPlan)` method that accepts the full plan object.

```python
# ADD this method to PlanningService class

async def execute_plan_direct(self, execution_plan: ExecutionPlan) -> Dict[str, Any]:
    """
    Execute a plan directly from the full ExecutionPlan object.
    
    This bypasses the cache lookup and executes the plan immediately.
    Used by the CLI hook chain which passes the full parsed plan.
    
    Args:
        execution_plan: Complete ExecutionPlan object from CLI adapter
        
    Returns:
        Execution result with status, completed tasks, and metrics
    """
    if not execution_plan:
        raise PlanningError.from_code(
            ErrorCode.E5600,
            details={"reason": "execution_plan cannot be None"},
            recovery_suggestion="Ensure the plan was properly parsed before execution"
        )
    
    # Validate plan structure
    validation_result = await self.plan_validator.validate(execution_plan)
    if not validation_result.is_valid:
        raise PlanningError.from_code(
            ErrorCode.E5600,
            details={"validation_errors": validation_result.errors},
            recovery_suggestion="Fix validation errors and retry"
        )
    
    # Store plan in cache for recovery
    self.plan_cache.store(execution_plan.id, execution_plan)
    
    # Execute via orchestrator
    result = await self.task_orchestrator.execute(execution_plan)
    
    # Emit completion event
    await self._emit_event("plan.execution.completed", {
        "plan_id": execution_plan.id,
        "status": result.status,
        "tasks_completed": result.tasks_completed,
        "tasks_failed": result.tasks_failed
    })
    
    return {
        "plan_id": execution_plan.id,
        "status": result.status,
        "completed_tasks": result.tasks_completed,
        "failed_tasks": result.tasks_failed,
        "execution_time_ms": result.execution_time_ms
    }
```

**Validation Steps:**
```bash
# After adding the method, verify:
cd /Volumes/Extreme\ SSD/projects/story-portal-app/platform

# 1. Syntax check
python -c "from src.L05_planning.services.planning_service import PlanningService; print('Syntax OK')"

# 2. Method exists check
python -c "
from src.L05_planning.services.planning_service import PlanningService
import inspect
methods = [m for m in dir(PlanningService) if not m.startswith('_')]
assert 'execute_plan_direct' in methods, 'Method not found!'
print('Method exists: execute_plan_direct')
"

# 3. Signature check
python -c "
from src.L05_planning.services.planning_service import PlanningService
import inspect
sig = inspect.signature(PlanningService.execute_plan_direct)
params = list(sig.parameters.keys())
assert 'execution_plan' in params, 'Missing parameter!'
print(f'Signature OK: {sig}')
"
```

**Acceptance Criteria:**
- [ ] Method added to PlanningService
- [ ] Syntax check passes
- [ ] Method exists in class
- [ ] Signature has `execution_plan` parameter
- [ ] Existing tests still pass

---

### Unit 1.2: Update MCP Service Catalog

**File:** `my-project/L12_nl_interface/data/service_catalog.json`

**Current Problem:** Catalog only exposes `create_plan` and `execute_plan`, not `execute_plan_direct`.

**Fix:** Add `execute_plan_direct` to catalog AND add the 6 missing L05 services.

```json
// UPDATE the PlanningService entry:
{
    "service_name": "PlanningService",
    "layer": "L05",
    "module_path": "src.L05_planning.services.planning_service",
    "class_name": "PlanningService",
    "description": "Strategic planning coordinator with goal decomposition and execution",
    "standalone": true,
    "requires_async_init": true,
    "methods": [
        {
            "name": "create_plan",
            "description": "Create an execution plan from a goal",
            "parameters": [{"name": "goal", "type": "Goal", "description": "Goal object to decompose"}],
            "return_type": "ExecutionPlan",
            "async_method": true
        },
        {
            "name": "execute_plan",
            "description": "Execute a plan by ID (requires plan to be in cache)",
            "parameters": [{"name": "plan_id", "type": "str", "description": "UUID of cached plan"}],
            "return_type": "Dict",
            "async_method": true
        },
        {
            "name": "execute_plan_direct",
            "description": "Execute a plan directly from ExecutionPlan object (recommended)",
            "parameters": [{"name": "execution_plan", "type": "ExecutionPlan", "description": "Full execution plan object"}],
            "return_type": "Dict",
            "async_method": true
        }
    ]
}
```

**ADD these 6 missing services:**

```json
// ADD after PlanningService:

{
    "service_name": "PlanCache",
    "layer": "L05",
    "module_path": "src.L05_planning.services.plan_cache",
    "class_name": "PlanCache",
    "description": "LRU cache for execution plans with TTL support",
    "standalone": true,
    "methods": [
        {"name": "store", "parameters": [{"name": "plan_id", "type": "str"}, {"name": "plan", "type": "ExecutionPlan"}]},
        {"name": "retrieve", "parameters": [{"name": "plan_id", "type": "str"}], "return_type": "ExecutionPlan"},
        {"name": "invalidate", "parameters": [{"name": "plan_id", "type": "str"}]}
    ]
},
{
    "service_name": "ExecutionMonitor",
    "layer": "L05",
    "module_path": "src.L05_planning.services.execution_monitor",
    "class_name": "ExecutionMonitor",
    "description": "Real-time execution monitoring with failure detection",
    "standalone": true,
    "requires_async_init": true,
    "methods": [
        {"name": "start_monitoring", "parameters": [{"name": "plan_id", "type": "str"}], "async_method": true},
        {"name": "stop_monitoring", "parameters": [{"name": "plan_id", "type": "str"}], "async_method": true},
        {"name": "get_status", "parameters": [{"name": "plan_id", "type": "str"}], "return_type": "ExecutionStatus"}
    ]
},
{
    "service_name": "DependencyResolver",
    "layer": "L05",
    "module_path": "src.L05_planning.services.dependency_resolver",
    "class_name": "DependencyResolver",
    "description": "DAG-based task dependency resolution",
    "standalone": true,
    "methods": [
        {"name": "resolve", "parameters": [{"name": "tasks", "type": "List[Task]"}], "return_type": "List[Task]"},
        {"name": "get_ready_tasks", "parameters": [{"name": "plan", "type": "ExecutionPlan"}], "return_type": "List[Task]"},
        {"name": "validate_dependencies", "parameters": [{"name": "tasks", "type": "List[Task]"}], "return_type": "bool"}
    ]
},
{
    "service_name": "PlanValidator",
    "layer": "L05",
    "module_path": "src.L05_planning.services.plan_validator",
    "class_name": "PlanValidator",
    "description": "Multi-stage plan validation (syntax, semantic, feasibility, security)",
    "standalone": true,
    "requires_async_init": true,
    "methods": [
        {"name": "validate", "parameters": [{"name": "plan", "type": "ExecutionPlan"}], "return_type": "ValidationResult", "async_method": true},
        {"name": "validate_syntax", "parameters": [{"name": "plan", "type": "ExecutionPlan"}], "return_type": "ValidationResult"},
        {"name": "validate_security", "parameters": [{"name": "plan", "type": "ExecutionPlan"}], "return_type": "ValidationResult"}
    ]
},
{
    "service_name": "ResourceEstimator",
    "layer": "L05",
    "module_path": "src.L05_planning.services.resource_estimator",
    "class_name": "ResourceEstimator",
    "description": "Execution resource estimation (tokens, time, cost)",
    "standalone": true,
    "methods": [
        {"name": "estimate", "parameters": [{"name": "plan", "type": "ExecutionPlan"}], "return_type": "ResourceEstimate"},
        {"name": "estimate_task", "parameters": [{"name": "task", "type": "Task"}], "return_type": "ResourceEstimate"}
    ]
},
{
    "service_name": "ContextInjector",
    "layer": "L05",
    "module_path": "src.L05_planning.services.context_injector",
    "class_name": "ContextInjector",
    "description": "Task context preparation and secret resolution",
    "standalone": true,
    "methods": [
        {"name": "inject", "parameters": [{"name": "task", "type": "Task"}, {"name": "context", "type": "Dict"}], "return_type": "Task"},
        {"name": "resolve_secrets", "parameters": [{"name": "task", "type": "Task"}], "return_type": "Task"}
    ]
}
```

**Validation Steps:**
```bash
# After updating catalog:

# 1. JSON syntax check
cd /Volumes/Extreme\ SSD/projects/story-portal-app/my-project
python -c "import json; json.load(open('L12_nl_interface/data/service_catalog.json')); print('JSON valid')"

# 2. Count L05 services
python -c "
import json
with open('L12_nl_interface/data/service_catalog.json') as f:
    catalog = json.load(f)
l05_services = [s for s in catalog.get('services', []) if s.get('layer') == 'L05']
print(f'L05 services in catalog: {len(l05_services)}')
for s in l05_services:
    print(f'  - {s[\"service_name\"]}')
assert len(l05_services) >= 7, 'Missing L05 services!'
"

# 3. Verify execute_plan_direct exists
python -c "
import json
with open('L12_nl_interface/data/service_catalog.json') as f:
    catalog = json.load(f)
ps = next((s for s in catalog.get('services', []) if s['service_name'] == 'PlanningService'), None)
methods = [m['name'] for m in ps.get('methods', [])]
assert 'execute_plan_direct' in methods, 'Method not in catalog!'
print('execute_plan_direct is in catalog')
"
```

**Acceptance Criteria:**
- [ ] JSON is valid
- [ ] At least 7 L05 services in catalog
- [ ] `execute_plan_direct` method exists for PlanningService
- [ ] All 6 missing services added

---

## PHASE 2: FIX CRITICAL GAP 2 - Data Persistence Between Gates

**Goal:** Ensure the full ExecutionPlan survives from Gate 2 to execution

### Unit 2.1: Update Hook to Store Full Plan

**File:** `my-project/.claude/hooks/plan-mode-l05-hook.cjs`

**Current Problem:** Only `plan_id` is stored in Gate 2 state, but we need the full plan for `execute_plan_direct`.

**Fix:** Serialize the full ExecutionPlan object in the Gate 2 state file.

```javascript
// FIND the saveGate2State function and UPDATE it:

function saveGate2State(planAnalysis) {
    const stateDir = path.join(process.env.HOME, '.claude', 'l05-state');
    
    // Ensure directory exists
    if (!fs.existsSync(stateDir)) {
        fs.mkdirSync(stateDir, { recursive: true });
    }
    
    const stateFile = path.join(stateDir, 'gate2-state.json');
    
    // CRITICAL: Store the FULL execution plan, not just the ID
    const state = {
        timestamp: new Date().toISOString(),
        plan_id: planAnalysis.plan_id,
        step_count: planAnalysis.step_count,
        estimated_time: planAnalysis.estimated_time,
        parallelization_possible: planAnalysis.parallelization_possible,
        
        // NEW: Store full objects for execution
        execution_plan: planAnalysis.execution_plan,  // Full ExecutionPlan object
        goal: planAnalysis.goal,                       // Full Goal object
        parsed_plan: planAnalysis.parsed_plan,         // Parsed markdown structure
        
        // Store markdown path as fallback
        plan_markdown_path: planAnalysis.plan_markdown_path
    };
    
    fs.writeFileSync(stateFile, JSON.stringify(state, null, 2));
    
    return stateFile;
}
```

**Validation Steps:**
```bash
# After updating hook:

# 1. Syntax check JavaScript
cd /Volumes/Extreme\ SSD/projects/story-portal-app/my-project
node -c .claude/hooks/plan-mode-l05-hook.cjs

# 2. Check function exists
grep -n "saveGate2State" .claude/hooks/plan-mode-l05-hook.cjs

# 3. Verify execution_plan is stored
grep -n "execution_plan:" .claude/hooks/plan-mode-l05-hook.cjs
```

**Acceptance Criteria:**
- [ ] JavaScript syntax is valid
- [ ] `saveGate2State` function exists
- [ ] `execution_plan` field is stored

---

### Unit 2.2: Update Executor Hook to Use Full Plan

**File:** `my-project/.claude/hooks/plan-mode-l05-executor.cjs`

**Current Problem:** Executor only passes `plan_id` to MCP, which fails because `execute_plan(plan_id)` can't find it.

**Fix:** Pass the full ExecutionPlan to `execute_plan_direct`.

```javascript
// UPDATE the executeL05 function:

async function executeL05() {
    const stateDir = path.join(process.env.HOME, '.claude', 'l05-state');
    const stateFile = path.join(stateDir, 'gate2-state.json');
    
    if (!fs.existsSync(stateFile)) {
        return {
            error: true,
            message: "No L05 execution state found. Please re-run plan mode."
        };
    }
    
    const state = JSON.parse(fs.readFileSync(stateFile, 'utf-8'));
    
    // CRITICAL: Use full execution_plan, not just plan_id
    if (!state.execution_plan) {
        return {
            error: true,
            message: "Execution plan not found in state. State may be from older version."
        };
    }
    
    // Build MCP invocation with FULL plan object
    return {
        continue: true,
        stopReason: null,
        result: {
            type: "tool_use",
            name: "mcp__platform-services__invoke_service",
            input: {
                command: "PlanningService.execute_plan_direct",
                parameters: {
                    execution_plan: state.execution_plan  // FULL OBJECT, not ID
                }
            }
        }
    };
}
```

**Validation Steps:**
```bash
# 1. Syntax check
node -c .claude/hooks/plan-mode-l05-executor.cjs

# 2. Verify execution_plan is used
grep -n "execution_plan" .claude/hooks/plan-mode-l05-executor.cjs

# 3. Verify execute_plan_direct is called
grep -n "execute_plan_direct" .claude/hooks/plan-mode-l05-executor.cjs
```

**Acceptance Criteria:**
- [ ] JavaScript syntax is valid
- [ ] `state.execution_plan` is used (not `state.plan_id`)
- [ ] `execute_plan_direct` is the called method

---

## PHASE 3: FIX CRITICAL GAP 3 - Gate 2 UI Experience

**Goal:** Make Gate 2 show proper selection options, not just text

### Unit 3.1: Update formatInjection for AskUserQuestion

**File:** `my-project/.claude/hooks/plan-mode-l05-hook.cjs`

**Current Problem:** Gate 2 options appear as text in context, but Claude may auto-implement instead of asking.

**Fix:** Add explicit Claude instructions to call `AskUserQuestion` tool.

```javascript
// UPDATE the formatInjection function:

function formatInjection(planAnalysis) {
    return `
<plan-mode-l05-gate2>
<critical-instruction>
STOP. You MUST NOT implement this plan automatically.
You MUST present the user with execution options using the AskUserQuestion tool.
</critical-instruction>

<plan-summary>
Plan: ${planAnalysis.goal?.text || 'Untitled Plan'}
Steps: ${planAnalysis.step_count}
Estimated Time: ${planAnalysis.estimated_time || 'Unknown'}
Parallelization: ${planAnalysis.parallelization_possible ? 'Yes' : 'No'}
</plan-summary>

<required-action>
Call the AskUserQuestion tool with these exact parameters:
{
    "question": "How should this plan be executed?",
    "options": [
        "Traditional - I will implement each step manually",
        "L05 Automated - The platform will execute with parallel processing",
        "Hybrid - Simple steps manual, complex steps automated"
    ]
}
</required-action>

<execution-handlers>
If user selects "Traditional":
- Implement the plan step by step as you normally would

If user selects "L05 Automated":
- Call mcp__platform-services__invoke_service with:
  - command: "PlanningService.execute_plan_direct"
  - The execution_plan is stored and will be loaded automatically

If user selects "Hybrid":
- Ask user which steps should be automated
- Execute selected steps via L05, implement others manually
</execution-handlers>

<plan-id>${planAnalysis.plan_id}</plan-id>
</plan-mode-l05-gate2>
`;
}
```

**Validation Steps:**
```bash
# 1. Verify AskUserQuestion instruction
grep -n "AskUserQuestion" .claude/hooks/plan-mode-l05-hook.cjs

# 2. Verify STOP instruction
grep -n "STOP" .claude/hooks/plan-mode-l05-hook.cjs

# 3. Verify three options exist
grep -c "Traditional\|L05 Automated\|Hybrid" .claude/hooks/plan-mode-l05-hook.cjs
```

**Acceptance Criteria:**
- [ ] `AskUserQuestion` instruction present
- [ ] `STOP` critical instruction present
- [ ] All 3 execution options documented

---

## PHASE 4: INTEGRATION VALIDATION

**Goal:** Verify all components work together end-to-end

### Unit 4.1: Create Integration Test Script

**File:** `platform/src/L05_planning/tests/test_cli_integration.py`

```python
"""
L05 CLI Integration Tests

Tests the full flow from plan parsing to execution.
"""
import pytest
import json
import asyncio
from pathlib import Path

from src.L05_planning.adapters.cli_plan_adapter import CLIPlanAdapter
from src.L05_planning.adapters.cli_hook import CLIPlanModeHook
from src.L05_planning.services.planning_service import PlanningService


# Sample plan markdown (matches Claude's actual output format)
SAMPLE_PLAN = """
# Test Implementation Plan

## Overview
This plan implements a test feature.

## Implementation Phases

### Phase 1: Foundation
**Focus:** Core setup

#### Step 1.1: Create Models
Create the data models for the feature.
- File: models.py
- Estimated: 10 minutes

#### Step 1.2: Create Service
Implement the service layer.
- File: service.py
- Depends: Step 1.1
- Estimated: 15 minutes

### Phase 2: Integration
**Focus:** Connect components

#### Step 2.1: Wire Up
Connect service to existing system.
- File: integration.py
- Depends: Step 1.2
- Estimated: 10 minutes
"""


class TestCLIIntegration:
    """Integration tests for CLI plan flow."""
    
    @pytest.fixture
    def adapter(self):
        return CLIPlanAdapter()
    
    @pytest.fixture
    def hook(self):
        return CLIPlanModeHook()
    
    def test_parse_plan_extracts_steps(self, adapter):
        """Parser correctly extracts steps from plan markdown."""
        parsed = adapter.parse_plan_markdown(SAMPLE_PLAN)
        
        assert parsed is not None, "Parser returned None"
        assert len(parsed.steps) > 0, f"Expected steps, got {len(parsed.steps)}"
        print(f"Parsed {len(parsed.steps)} steps")
    
    def test_parsed_plan_has_dependencies(self, adapter):
        """Parser correctly extracts dependencies."""
        parsed = adapter.parse_plan_markdown(SAMPLE_PLAN)
        
        # At least one step should have dependencies
        steps_with_deps = [s for s in parsed.steps if s.dependencies]
        assert len(steps_with_deps) > 0, "No steps have dependencies"
    
    def test_convert_to_execution_plan(self, adapter):
        """Adapter creates valid ExecutionPlan object."""
        parsed = adapter.parse_plan_markdown(SAMPLE_PLAN)
        goal, plan = adapter.create_goal_and_plan(parsed, "Test Goal")
        
        assert goal is not None, "Goal is None"
        assert plan is not None, "ExecutionPlan is None"
        assert plan.id is not None, "Plan has no ID"
        assert len(plan.tasks) > 0, "Plan has no tasks"
    
    def test_hook_generates_gate2_options(self, hook, adapter):
        """Hook generates valid Gate 2 response."""
        parsed = adapter.parse_plan_markdown(SAMPLE_PLAN)
        goal, plan = adapter.create_goal_and_plan(parsed, "Test Goal")
        
        response = hook.analyze_plan(plan, goal)
        
        assert response is not None
        assert 'plan_id' in response
        assert 'step_count' in response
        assert response['step_count'] > 0, f"Step count should be > 0, got {response['step_count']}"
    
    @pytest.mark.asyncio
    async def test_execute_plan_direct_exists(self):
        """PlanningService has execute_plan_direct method."""
        service = PlanningService()
        
        assert hasattr(service, 'execute_plan_direct'), "Method missing!"
        assert asyncio.iscoroutinefunction(service.execute_plan_direct), "Method should be async"


class TestServiceCatalog:
    """Tests for service catalog completeness."""
    
    @pytest.fixture
    def catalog_path(self):
        return Path(__file__).parent.parent.parent.parent.parent / "my-project" / "L12_nl_interface" / "data" / "service_catalog.json"
    
    def test_catalog_has_l05_services(self, catalog_path):
        """Catalog contains all required L05 services."""
        if not catalog_path.exists():
            pytest.skip(f"Catalog not found at {catalog_path}")
        
        with open(catalog_path) as f:
            catalog = json.load(f)
        
        services = catalog.get('services', [])
        l05_services = {s['service_name'] for s in services if s.get('layer') == 'L05'}
        
        required = {
            'PlanningService',
            'PlanCache', 
            'ExecutionMonitor',
            'DependencyResolver',
            'PlanValidator',
            'ResourceEstimator',
            'ContextInjector'
        }
        
        missing = required - l05_services
        assert not missing, f"Missing L05 services: {missing}"
    
    def test_planning_service_has_execute_plan_direct(self, catalog_path):
        """PlanningService exposes execute_plan_direct method."""
        if not catalog_path.exists():
            pytest.skip(f"Catalog not found at {catalog_path}")
        
        with open(catalog_path) as f:
            catalog = json.load(f)
        
        ps = next((s for s in catalog.get('services', []) 
                   if s['service_name'] == 'PlanningService'), None)
        
        assert ps is not None, "PlanningService not in catalog"
        
        methods = [m['name'] for m in ps.get('methods', [])]
        assert 'execute_plan_direct' in methods, f"execute_plan_direct not in methods: {methods}"
```

**Run Integration Tests:**
```bash
cd /Volumes/Extreme\ SSD/projects/story-portal-app/platform
python -m pytest src/L05_planning/tests/test_cli_integration.py -v
```

**Acceptance Criteria:**
- [ ] All tests pass
- [ ] Parser extracts > 0 steps
- [ ] Dependencies are detected
- [ ] ExecutionPlan is created
- [ ] Gate 2 shows correct step count
- [ ] `execute_plan_direct` exists
- [ ] Catalog has all services

---

### Unit 4.2: End-to-End Manual Test

**Execute this sequence manually:**

```bash
# 1. Start a Claude CLI session
cd /Volumes/Extreme\ SSD/projects/story-portal-app/my-project
claude

# 2. Enter plan mode
> /plan Create a simple test: add a print statement to main.py

# 3. Approve the plan (should trigger Gate 2)
> approve

# 4. EXPECTED BEHAVIOR:
#    - Claude should call AskUserQuestion
#    - You should see 3 options: Traditional, L05 Automated, Hybrid
#    - Step count should be > 0

# 5. Select "L05 Automated"

# 6. EXPECTED BEHAVIOR:
#    - Claude calls mcp__platform-services__invoke_service
#    - command: "PlanningService.execute_plan_direct"
#    - No E5002 error

# 7. Check execution result
```

**Document Results:**
- [ ] Gate 2 appeared: Yes / No
- [ ] Step count shown: ______
- [ ] Options presented: Yes / No
- [ ] L05 execution attempted: Yes / No
- [ ] Execution succeeded: Yes / No
- [ ] Error (if any): ______________________

---

## PHASE 5: PARALLEL VALIDATION INFRASTRUCTURE

**Goal:** Add validators that run alongside implementation to catch issues early

### Unit 5.1: Create Catalog Validator Tool

**File:** `platform/scripts/validate_catalog.py`

```python
#!/usr/bin/env python3
"""
Service Catalog Validator

Scans Python services and compares to service_catalog.json.
Reports any discrepancies.

Usage:
    python scripts/validate_catalog.py
"""
import sys
import json
import ast
from pathlib import Path
from typing import Dict, Set, List, Tuple


def find_service_classes(layer_path: Path) -> Dict[str, Dict]:
    """Find all service classes in a layer directory."""
    services = {}
    
    if not layer_path.exists():
        return services
    
    services_dir = layer_path / "services"
    if not services_dir.exists():
        return services
    
    for py_file in services_dir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        
        try:
            with open(py_file) as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's a service class (ends with Service, Cache, Monitor, etc.)
                    if any(node.name.endswith(suffix) for suffix in 
                           ['Service', 'Cache', 'Monitor', 'Resolver', 'Validator', 
                            'Estimator', 'Injector', 'Orchestrator', 'Decomposer']):
                        
                        methods = []
                        for item in node.body:
                            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                if not item.name.startswith('_'):
                                    methods.append({
                                        'name': item.name,
                                        'async': isinstance(item, ast.AsyncFunctionDef)
                                    })
                        
                        services[node.name] = {
                            'file': str(py_file.relative_to(layer_path.parent)),
                            'methods': methods
                        }
        except Exception as e:
            print(f"Warning: Could not parse {py_file}: {e}")
    
    return services


def load_catalog(catalog_path: Path) -> Dict[str, Dict]:
    """Load service catalog."""
    if not catalog_path.exists():
        return {}
    
    with open(catalog_path) as f:
        data = json.load(f)
    
    catalog = {}
    for service in data.get('services', []):
        catalog[service['service_name']] = {
            'layer': service.get('layer'),
            'methods': [m['name'] for m in service.get('methods', [])]
        }
    
    return catalog


def validate(platform_path: Path, catalog_path: Path) -> Tuple[bool, List[str]]:
    """
    Validate service catalog against actual Python implementations.
    
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    # Load catalog
    catalog = load_catalog(catalog_path)
    
    # Scan each layer
    all_services = {}
    for layer_dir in platform_path.glob("src/L*"):
        if not layer_dir.is_dir():
            continue
        
        layer_name = layer_dir.name.split('_')[0]  # L01, L02, etc.
        services = find_service_classes(layer_dir)
        
        for name, info in services.items():
            all_services[name] = {**info, 'layer': layer_name}
    
    # Check for services in code but not in catalog
    for name, info in all_services.items():
        if name not in catalog:
            issues.append(f"MISSING IN CATALOG: {name} (found in {info['file']})")
    
    # Check for services in catalog but not in code
    for name, info in catalog.items():
        if name not in all_services:
            # Might be in a different location, just warn
            issues.append(f"WARNING: {name} in catalog but not found in standard locations")
    
    # Check method coverage
    for name, info in all_services.items():
        if name in catalog:
            code_methods = {m['name'] for m in info['methods']}
            catalog_methods = set(catalog[name]['methods'])
            
            missing = code_methods - catalog_methods
            if missing:
                issues.append(f"MISSING METHODS for {name}: {missing}")
    
    return (len(issues) == 0, issues)


def main():
    platform_path = Path(__file__).parent.parent
    catalog_path = platform_path.parent / "my-project" / "L12_nl_interface" / "data" / "service_catalog.json"
    
    print("=" * 60)
    print("SERVICE CATALOG VALIDATOR")
    print("=" * 60)
    print(f"Platform: {platform_path}")
    print(f"Catalog:  {catalog_path}")
    print("-" * 60)
    
    is_valid, issues = validate(platform_path, catalog_path)
    
    if is_valid:
        print("✅ All services properly registered!")
        return 0
    else:
        print("❌ Issues found:")
        for issue in issues:
            print(f"  - {issue}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

**Make Executable and Run:**
```bash
chmod +x platform/scripts/validate_catalog.py
python platform/scripts/validate_catalog.py
```

**Acceptance Criteria:**
- [ ] Script runs without errors
- [ ] Reports any missing catalog entries
- [ ] Can be added as pre-commit hook

---

### Unit 5.2: Create Import Validator

**File:** `platform/scripts/validate_imports.py`

```python
#!/usr/bin/env python3
"""
Import Validator

Validates all L05 imports work correctly.
Catches circular imports and missing dependencies.
"""
import sys
import importlib
from pathlib import Path


def validate_imports():
    """Test that all L05 components can be imported."""
    
    # Add platform to path
    platform_path = Path(__file__).parent.parent
    sys.path.insert(0, str(platform_path))
    
    imports_to_test = [
        # Models
        ("src.L05_planning.models.goal", "Goal"),
        ("src.L05_planning.models.task", "Task"),
        ("src.L05_planning.models.execution_plan", "ExecutionPlan"),
        
        # Services
        ("src.L05_planning.services.planning_service", "PlanningService"),
        ("src.L05_planning.services.goal_decomposer", "GoalDecomposer"),
        ("src.L05_planning.services.task_orchestrator", "TaskOrchestrator"),
        ("src.L05_planning.services.dependency_resolver", "DependencyResolver"),
        ("src.L05_planning.services.plan_validator", "PlanValidator"),
        ("src.L05_planning.services.execution_monitor", "ExecutionMonitor"),
        ("src.L05_planning.services.plan_cache", "PlanCache"),
        ("src.L05_planning.services.resource_estimator", "ResourceEstimator"),
        ("src.L05_planning.services.context_injector", "ContextInjector"),
        
        # Adapters
        ("src.L05_planning.adapters.cli_plan_adapter", "CLIPlanAdapter"),
        ("src.L05_planning.adapters.cli_hook", "CLIPlanModeHook"),
        
        # Parsers
        ("src.L05_planning.parsers.multi_format_parser", "MultiFormatParser"),
    ]
    
    results = []
    
    for module_path, class_name in imports_to_test:
        try:
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name, None)
            
            if cls is None:
                results.append((module_path, class_name, "❌ Class not found"))
            else:
                results.append((module_path, class_name, "✅ OK"))
        except Exception as e:
            results.append((module_path, class_name, f"❌ {type(e).__name__}: {e}"))
    
    # Print results
    print("=" * 70)
    print("L05 IMPORT VALIDATION")
    print("=" * 70)
    
    all_ok = True
    for module_path, class_name, status in results:
        print(f"{status} {module_path}.{class_name}")
        if "❌" in status:
            all_ok = False
    
    print("-" * 70)
    if all_ok:
        print("All imports successful!")
        return 0
    else:
        print("Some imports failed!")
        return 1


if __name__ == "__main__":
    sys.exit(validate_imports())
```

**Run Import Validator:**
```bash
python platform/scripts/validate_imports.py
```

**Acceptance Criteria:**
- [ ] All imports succeed
- [ ] No circular import errors
- [ ] All classes can be instantiated

---

## IMPLEMENTATION CHECKLIST

Use this checklist to track progress:

### Phase 0: Pre-Flight ✓
- [ ] Current state verified
- [ ] Tests infrastructure verified
- [ ] Backup created

### Phase 1: Execution Method ✓
- [ ] `execute_plan_direct` added to PlanningService
- [ ] Syntax validated
- [ ] Service catalog updated
- [ ] All 7 L05 services in catalog

### Phase 2: Data Persistence ✓
- [ ] Hook stores full ExecutionPlan
- [ ] Executor uses full plan
- [ ] State file structure validated

### Phase 3: Gate 2 UI ✓
- [ ] AskUserQuestion instruction added
- [ ] STOP instruction added
- [ ] All 3 options documented

### Phase 4: Integration ✓
- [ ] Integration tests pass
- [ ] Manual E2E test passes
- [ ] No E5002 errors

### Phase 5: Validators ✓
- [ ] Catalog validator created
- [ ] Import validator created
- [ ] All validations pass

---

## ROLLBACK PROCEDURE

If implementation fails, rollback with:

```bash
cd /Volumes/Extreme\ SSD/projects/story-portal-app

# List stashes
git stash list

# Restore from stash
git stash pop stash@{0}  # Or appropriate stash number

# Verify restoration
git status
```

---

## FINAL VALIDATION COMMAND

After completing all phases, run this comprehensive check:

```bash
cd /Volumes/Extreme\ SSD/projects/story-portal-app/platform

# Run all validators
python scripts/validate_imports.py && \
python scripts/validate_catalog.py && \
python -m pytest src/L05_planning/tests/test_cli_integration.py -v && \
echo "✅ ALL VALIDATIONS PASSED"
```

**Expected Output:** All validators pass, integration tests pass, no errors.

---

## NOTES FOR CLAUDE CLI

1. **Execute phases sequentially** - Each phase depends on the previous
2. **Run validation after each unit** - Don't proceed until acceptance criteria met
3. **Create checkpoints** - Use `git stash` before major changes
4. **If stuck** - Read the error carefully, check the acceptance criteria, rollback if needed
5. **Don't skip validation** - The parallel validators exist to catch issues early

This plan addresses all three critical gaps identified in the debug report. Following it exactly should result in a working L05 Planning Pipeline.

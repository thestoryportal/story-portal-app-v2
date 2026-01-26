# L05 Planning Pipeline - Complete Debug Report

**Generated:** 2026-01-26
**Pipeline Version:** V2
**Status:** PARTIALLY FUNCTIONAL - Critical gaps identified

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Intended Pipeline Architecture](#intended-pipeline-architecture)
3. [Current Implementation State](#current-implementation-state)
4. [Historical Failure Timeline](#historical-failure-timeline)
5. [Critical Issues Identified](#critical-issues-identified)
6. [Component Analysis](#component-analysis)
7. [MCP Integration Analysis](#mcp-integration-analysis)
8. [Recommendations](#recommendations)

---

## Executive Summary

The L05 Planning Pipeline is a sophisticated plan execution system designed to parse Claude Code's plan markdown, decompose it into atomic units, and execute tasks with parallel processing, automatic recovery, and multi-agent support.

### Current Status

| Component | Status | Notes |
|-----------|--------|-------|
| Plan Parsing | ✅ Working | MultiFormatParser handles 7 formats |
| Gate 1 (Plan Approval) | ✅ Working | CLI plan mode integration |
| Gate 2 (Execution Choice) | ⚠️ Partial | UI shows as text, not selection menu |
| L05 Execution Path | ❌ Broken | `execute_plan(plan_id)` not implemented |
| Traditional Execution | ✅ Working | Claude implements directly |
| MCP Integration | ⚠️ Partial | Only 2 methods exposed |

### Key Finding

**The L05 automated execution path cannot work** because:
1. `PlanningService.execute_plan(plan_id)` raises E5002 (not implemented)
2. MCP only exposes `execute_plan`, not `execute_plan_direct`
3. Only `plan_id` is stored in Gate 2 state, not the full `ExecutionPlan` object

---

## Intended Pipeline Architecture

### Design Vision

```
┌─────────────────────────────────────────────────────────────────┐
│                    L05 PLANNING PIPELINE                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  USER CREATES PLAN (Plan Mode)                                  │
│         │                                                       │
│         ▼                                                       │
│  ┌──────────────┐                                               │
│  │   GATE 1     │  Plan Approval                                │
│  │  (CLI Mode)  │  - User reviews plan                          │
│  └──────┬───────┘  - User approves via ExitPlanMode             │
│         │                                                       │
│         ▼                                                       │
│  ┌──────────────┐                                               │
│  │ L05 Adapter  │  Plan Analysis                                │
│  │              │  - Parse markdown → ParsedPlan                │
│  │              │  - Convert to Goal + ExecutionPlan            │
│  │              │  - Analyze parallelization potential          │
│  └──────┬───────┘  - Build execution options                    │
│         │                                                       │
│         ▼                                                       │
│  ┌──────────────┐                                               │
│  │   GATE 2     │  Execution Method Selection                   │
│  │              │  - Traditional: Claude implements             │
│  │              │  - L05 Automated: Pipeline executes           │
│  └──────┬───────┘  - Hybrid: Mix of both                        │
│         │                                                       │
│    ┌────┴────┬──────────────┐                                   │
│    ▼         ▼              ▼                                   │
│ Traditional  L05          Hybrid                                │
│ (Claude)   Automated    (Mixed)                                 │
│              │                                                  │
│              ▼                                                  │
│  ┌──────────────────────────────────────┐                       │
│  │      PLANNING SERVICE                │                       │
│  │                                      │                       │
│  │  ┌────────────────┐                  │                       │
│  │  │ Goal Decomposer│ → Tasks          │                       │
│  │  └────────────────┘                  │                       │
│  │           │                          │                       │
│  │           ▼                          │                       │
│  │  ┌────────────────┐                  │                       │
│  │  │ Dependency     │ → DAG            │                       │
│  │  │ Resolver       │                  │                       │
│  │  └────────────────┘                  │                       │
│  │           │                          │                       │
│  │           ▼                          │                       │
│  │  ┌────────────────┐                  │                       │
│  │  │ Task           │ → Parallel       │                       │
│  │  │ Orchestrator   │   Execution      │                       │
│  │  └────────────────┘                  │                       │
│  │           │                          │                       │
│  │           ▼                          │                       │
│  │  ┌────────────────┐                  │                       │
│  │  │ L01 Bridge     │ → Persistence    │                       │
│  │  └────────────────┘                  │                       │
│  └──────────────────────────────────────┘                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Core Components

1. **MultiFormatParser** - Parses 7 different plan markdown formats
2. **CLIPlanAdapter** - Converts parsed plan to Goal + ExecutionPlan
3. **CLIPlanModeHook** - Handles Gate 2 option generation
4. **PlanningService** - Main orchestrator
5. **TaskOrchestrator** - Parallel execution engine
6. **L01Bridge** - Persistence layer integration

---

## Current Implementation State

### V1 vs V2 Comparison

| Feature | V1 (Original) | V2 (Current) |
|---------|--------------|--------------|
| Plan Parsing | Single format | 7 formats via MultiFormatParser |
| Decomposition | LLM-based via L04 | CLI adapter + LLM fallback |
| Execution | `execute_plan(plan_id)` | `execute_plan_direct(plan)` |
| Persistence | Assumes L01 storage | Requires full plan object |
| MCP Exposure | 2 methods | 2 methods (unchanged) |
| Gate 2 UI | Text in system reminder | Text in system reminder |

### Files and Their States

```
platform/src/L05_planning/
├── adapters/
│   ├── cli_plan_adapter.py      ✅ Complete - Parses markdown
│   └── cli_hook.py              ✅ Complete - Gate 2 generation
├── parsers/
│   ├── multi_format_parser.py   ✅ Complete - 7 format support
│   ├── format_detector.py       ✅ Complete - Auto-detection
│   └── [5 format parsers]       ✅ Complete
├── services/
│   ├── planning_service.py      ⚠️ Partial - execute_plan NOT IMPLEMENTED
│   ├── task_orchestrator.py     ✅ Complete
│   ├── goal_decomposer.py       ✅ Complete
│   ├── dependency_resolver.py   ✅ Complete
│   └── [others]                 ✅ Complete
└── v2/
    └── mcp_connection.py        ✅ Complete - Health check

my-project/.claude/hooks/
├── plan-mode-l05-hook.cjs       ✅ Works - PostToolUse hook
├── plan-mode-l05-executor.cjs   ✅ Works - UserPromptSubmit hook
└── l05-bridge.py                ✅ Works - Python bridge
```

---

## Historical Failure Timeline

### Timeline of Issues and Resolutions

| Date | Issue | Root Cause | Resolution |
|------|-------|------------|------------|
| 2026-01-24 08:02-08:03 | ETIMEDOUT errors | spawnSync blocking | Identified |
| 2026-01-24 11:57-16:01 | Repeated ETIMEDOUT | 30s timeout too short for Python startup | Multiple retry attempts |
| 2026-01-24 16:01 | spawnSync python3 ETIMEDOUT | Synchronous spawn | Tried direct python3 |
| 2026-01-24 16:02 | spawnSync python3 ETIMEDOUT | Still blocking | Tried with full path |
| 2026-01-24 16:03 | spawnSync /bin/sh ETIMEDOUT | Shell wrapping slow | Tried shell execution |
| 2026-01-24 16:04 | spawnSync /usr/local/bin/python3 ETIMEDOUT | Full path also times out | Tried explicit path |
| 2026-01-24 16:05 | spawnSync /bin/bash ETIMEDOUT | Bash wrapper | Tried wrapper script |
| 2026-01-24 16:07 | Python bridge timed out | 30s timeout exceeded | **Switched to async spawn** |
| 2026-01-24 16:15 | ✅ First success | Async spawn works | **FIXED: Async spawn with child_process** |
| 2026-01-24 17:32 | ✅ Success | Working | |
| 2026-01-24 18:00 | "0 steps" parsed | Plan format not recognized | Parser needs update |
| 2026-01-24 18:14 | "0 steps" parsed | Same issue | |
| 2026-01-26 18:54 | "0 steps" parsed | Plan format issue | |
| 2026-01-26 19:37 | ✅ Success (4 steps) | Working | |
| 2026-01-26 20:20 | "2 steps - skip" | Below threshold | Auto-skip for small plans |
| 2026-01-26 20:26-20:31 | ✅ Success (2 steps) | Working | |

### Key Resolution: Synchronous to Asynchronous Spawn

**Problem:** `spawnSync` was blocking and timing out because:
1. Python startup time on external SSD is slow (~2-5s)
2. Module imports in l05-bridge.py take time
3. 30s timeout was sometimes not enough under load

**Solution:** Changed from:
```javascript
// OLD - Blocking
const result = spawnSync('/usr/local/bin/python3', [script, ...args], { timeout: 30000 });
```

To:
```javascript
// NEW - Async with Promise
const child = spawn('/usr/local/bin/python3', [script, ...args], { stdio: ['ignore', 'pipe', 'pipe'] });
// ... handle with events and Promise
```

### "0 Steps" Parsing Failures

**Problem:** Some plan formats resulted in "0 steps" being parsed.

**Root Causes:**
1. MultiFormatParser didn't recognize certain Claude plan formats
2. Fallback legacy parser expected specific markers not present

**Resolutions (Commit efbdb98):**
- Added support for SIMPLE_STEPS format
- Added PHASED format support
- Improved format detection heuristics

---

## Critical Issues Identified

### Issue #1: `execute_plan(plan_id)` Not Implemented

**Location:** `planning_service.py:249-277`

```python
async def execute_plan(self, plan_id: str) -> Dict[str, Any]:
    # TODO: Load plan from persistence
    # For now, assume plan is passed directly via execute_plan_direct

    raise PlanningError.from_code(
        ErrorCode.E5002,
        details={"plan_id": plan_id},
        recovery_suggestion="Use execute_plan_direct() with plan object",
    )
```

**Impact:** When user selects "L05 Automated Execution", the executor hook tells Claude to call:
```
mcp__platform-services__invoke_service
command="PlanningService.execute_plan"
parameters={"plan_id": "uuid"}
```

This will ALWAYS fail with E5002.

**Required Fix:** Either:
1. Implement plan storage in L01 and retrieval by ID
2. Serialize full ExecutionPlan in Gate 2 state
3. Re-parse markdown when L05 is selected

### Issue #2: Gate 2 UI Shows as Text, Not Selection Menu

**Current State:** Gate 2 options appear as system-reminder text:
```
<plan-mode-l05-gate2>
**Choose how to execute:**
● **Traditional (Claude implements)** **(Recommended)**
○ **L05 Automated Execution**
Respond with: "L05", "traditional", or "hybrid"
</plan-mode-l05-gate2>
```

**Expected:** Selection menu below chat field (like plan approval).

**Root Cause:** Claude Code hooks can only inject text context via `additionalContext`. They cannot trigger the native CLI selection UI.

**Proposed Fix:** Have hook instruct Claude to call `AskUserQuestion` with Gate 2 options. This renders as a proper selection menu.

### Issue #3: Claude Auto-Implements Instead of Waiting

**Current State:** When ExitPlanMode completes:
1. Tool result says "You can now start coding"
2. Gate 2 options appear in system reminder
3. Claude sees "start coding" and proceeds to implement

**Expected:** Claude should wait for user to select execution method.

**Root Cause:** ExitPlanMode result takes precedence over hook-injected context.

**Proposed Fix:** Inject explicit STOP instruction in hook output telling Claude to NOT implement and to call AskUserQuestion instead.

### Issue #4: MCP Method Exposure Gap

**Service Catalog exposes:**
- `PlanningService.create_plan`
- `PlanningService.execute_plan`

**Not exposed:**
- `PlanningService.execute_plan_direct` (the working method!)

**Impact:** Even if Claude tried to call the correct method, MCP would reject it.

---

## Component Analysis

### Hook Chain Analysis

```
ExitPlanMode Tool Called
        │
        ▼
plan-mode-l05-hook.cjs (PostToolUse)
├── Trigger: tool_name === "ExitPlanMode"
├── Action: Find plan file, spawn l05-bridge.py
├── Output: JSON with hookSpecificOutput.additionalContext
└── State: Saves to .gate2-pending.json
        │
        ▼
User Responds with choice ("L05", "traditional", etc.)
        │
        ▼
plan-mode-l05-executor.cjs (UserPromptSubmit)
├── Trigger: .gate2-pending.json exists with awaiting_choice=true
├── Action: Detect choice via regex patterns
├── Output: Execution instructions
└── State: Updates .gate2-pending.json with choice_made
```

### Data Flow Analysis

```
Plan Markdown (string)
        │
        ▼ (l05-bridge.py)
CLIPlanAdapter.parse_plan_markdown()
        │
        ▼
ParsedPlan
├── goal: str
├── steps: List[ParsedStep]
├── session_id: str (hash)
└── raw_markdown: str
        │
        ▼ (CLIPlanAdapter)
┌───────┴───────┐
▼               ▼
Goal            ExecutionPlan
├── goal_id     ├── plan_id
├── goal_text   ├── goal_id
└── metadata    ├── tasks: List[Task]
                └── metadata
        │
        ▼ (CLIPlanModeHook.on_plan_approved)
Gate2Response
├── plan_id ←── ONLY THIS IS SAVED
├── goal_id
├── options
└── analysis
        │
        ▼ (plan-mode-l05-hook.cjs)
.gate2-pending.json
├── plan_id ←── Lost ExecutionPlan object!
├── goal_id
├── options
└── awaiting_choice: true
```

**Critical Data Loss:** The full `ExecutionPlan` object is created but only `plan_id` is persisted. When user selects L05, we can't retrieve the plan.

---

## MCP Integration Analysis

### Service Catalog Entry

```json
"PlanningService": {
    "service_name": "PlanningService",
    "layer": "L05",
    "module_path": "src.L05_planning.services.planning_service",
    "class_name": "PlanningService",
    "description": "Strategic planning coordinator",
    "standalone": true,
    "requires_async_init": true,
    "methods": [
        {
            "name": "create_plan",
            "parameters": [{"name": "goal", "type": "Goal"}],
            "async_method": true
        },
        {
            "name": "execute_plan",
            "parameters": [{"name": "plan_id", "type": "str"}],
            "async_method": true
        }
    ]
}
```

### MCP Invocation Flow

```
Claude calls: mcp__platform-services__invoke_service
        │
        ▼
MCPServer.invoke_service()
├── command: "PlanningService.execute_plan"
├── parameters: {"plan_id": "uuid"}
        │
        ▼
CommandRouter.route_request()
├── Match service: "PlanningService"
├── Validate method: "execute_plan" ✅ exists in catalog
        │
        ▼
ServiceFactory.create_service()
├── Instantiate: PlanningService()
├── Initialize: await service.initialize()
        │
        ▼
_invoke_method(service, "execute_plan", {"plan_id": "uuid"})
        │
        ▼
PlanningService.execute_plan("uuid")
        │
        ▼
❌ RAISES E5002: Not Implemented
```

---

## Recommendations

### Priority 1: Fix L05 Execution Path

**Option A: Store Full ExecutionPlan (Recommended)**

Modify `plan-mode-l05-hook.cjs` to serialize and store the full ExecutionPlan:

```javascript
// In saveGate2State()
const state = {
    // ... existing fields
    execution_plan: adapterResult.execution_plan,  // Full object
    goal: adapterResult.goal,                       // Full object
};
```

Then modify executor hook to pass full plan to a new endpoint.

**Option B: Implement Plan Storage in L01**

Implement `execute_plan(plan_id)` to:
1. Query L01 for plan by ID
2. Reconstruct ExecutionPlan
3. Call `execute_plan_direct(plan)`

**Option C: Re-parse on Execution**

Store markdown path in Gate 2 state, re-parse when L05 selected.

### Priority 2: Fix Gate 2 UI

Modify `formatInjection()` to output instructions for Claude to call `AskUserQuestion`:

```markdown
CRITICAL: Do NOT implement this plan.
You MUST call AskUserQuestion with these options:
- question: "How should this plan be executed?"
- options:
  1. Traditional (Claude implements)
  2. L05 Automated Execution
  3. Hybrid

Based on user selection:
- "Traditional": Implement the plan step by step
- "L05": Call mcp__platform-services__invoke_service with...
- "Hybrid": ...
```

### Priority 3: Update MCP Catalog

Add `execute_plan_direct` to service catalog OR implement `execute_plan(plan_id)`.

### Priority 4: Add Claude Stop Instruction

Ensure the hook-injected context contains explicit instruction preventing auto-implementation:

```
<plan-mode-l05-gate2-instruction>
STOP. Do NOT implement this plan automatically.
Wait for user to select execution method.
Use AskUserQuestion to present options.
</plan-mode-l05-gate2-instruction>
```

---

## Test Results Summary

### Unit Tests

All L05 unit tests pass (models, services, parsers).

### Integration Tests

| Test | Status | Notes |
|------|--------|-------|
| Plan parsing | ✅ Pass | 7 formats supported |
| Gate 1 flow | ✅ Pass | ExitPlanMode triggers hook |
| Gate 2 injection | ✅ Pass | Options appear in context |
| L05 execution | ❌ Fail | E5002 not implemented |
| Traditional execution | ✅ Pass | Claude implements correctly |

### Hook Execution Stats (from debug log)

| Metric | Value |
|--------|-------|
| Total hook invocations | 26 |
| Timeout errors | 14 (early sessions) |
| Successful completions | 12 (recent sessions) |
| "0 steps" parses | 4 |
| Successful Gate 2 | 8 |

---

## Appendix: Error Codes

| Code | Name | Description |
|------|------|-------------|
| E5000 | PLAN_CACHE_ERROR | Plan cache access failed |
| E5001 | PLAN_CACHE_MISS | Plan not found in cache |
| E5002 | PLAN_NOT_FOUND | Plan not found (execute_plan uses this) |
| E5100 | DECOMPOSITION_FAILED | Goal decomposition failed |
| E5200 | ORCHESTRATION_FAILED | Task orchestration failed |
| E5300 | DEPENDENCY_RESOLUTION_FAILED | Dependency resolution failed |
| E5600 | VALIDATION_FAILED | Plan validation failed |

---

## Conclusion

The L05 Planning Pipeline has a well-designed architecture with complete implementations of parsing, decomposition, orchestration, and monitoring. However, **the critical execution path is broken** due to:

1. Missing implementation of `execute_plan(plan_id)`
2. Data loss between Gate 2 state and execution (only IDs stored)
3. MCP catalog not exposing the working method

**The fix requires:** Either implementing plan persistence and retrieval, or modifying the hook chain to preserve and pass the full ExecutionPlan object when L05 execution is selected.

The timeout issues have been resolved by switching to async spawn. The parsing issues have been resolved by adding multi-format support. The remaining issues are architectural gaps in the execution path.

---

*Report generated by Claude Code debugging workflow*

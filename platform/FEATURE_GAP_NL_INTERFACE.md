# CRITICAL FEATURE GAP: Natural Language Interface to Platform

**Status:** 🔴 NOT IMPLEMENTED
**Priority:** HIGH
**Impact:** Users cannot easily interact with platform features
**Date Created:** 2026-01-15

## Problem Statement

The platform has rich orchestration capabilities (PlanningService, TaskOrchestrator, QAOrchestrator, SagaOrchestrator, GoalDecomposer, etc.) but **NO natural language interface** for users to interact with these features.

**Current State:**
- All platform features require programmatic Python API usage
- No CLI commands to invoke platform capabilities
- No natural language goal submission
- No slash commands for common operations
- Users (like developers/operators) must write Python code to use platform features

**Desired State:**
- Type natural language commands in Claude CLI
- Use `/` commands for platform operations
- Direct interface to all L01-L11 layer capabilities
- Seamless goal submission and execution monitoring

## Gap Analysis

### What EXISTS Today

**L01-L11 Architecture:** ✅
- L01: Data Layer (PostgreSQL + Redis)
- L02: Runtime Layer (agent lifecycle)
- L03: Tool Execution Layer
- L04: Model Gateway (LLM routing)
- L05: Planning Layer (PlanningService, GoalDecomposer)
- L06: Evaluation Layer
- L07: Learning Layer
- L08: Memory Layer
- L09: API Gateway
- L10: Human Interface (web dashboard only)
- L11: Integration Layer

**HTTP Interfaces:** ⚠️ PARTIAL
- L10 Dashboard: `/api/agents`, `/api/goals` (read-only views)
- L09 API Gateway: `/api/v1/agents`, `/api/v1/goals`, `/api/v1/tasks` (CRUD only)
- **Missing:** No planning, orchestration, or workflow endpoints

**Platform Features:** ✅
- PlanningService (goal decomposition)
- GoalDecomposer (template + LLM-based)
- TaskOrchestrator (execution coordination)
- QAOrchestrator (test coordination)
- SagaOrchestrator (distributed transactions)
- RequestOrchestrator (cross-layer routing)
- LifecycleManager (agent management)
- AgentAssigner (capability matching)
- ToolComposer (workflow composition)

### What is MISSING

**Natural Language Interface:** ❌ NONE
- No way to submit goals in natural language
- No parsing of user intent
- No command interpretation layer

**Slash Commands:** ❌ NONE
- No `/plan <goal>` command
- No `/deploy <agent>` command
- No `/status` command
- No `/execute <workflow>` command

**CLI Integration:** ❌ NONE
- No integration between Claude CLI and platform
- Claude Code is external development tool, not connected to platform
- Platform has no CLI entry point

**User Intent Processing:** ❌ NONE
- No natural language → Goal conversion
- No command routing layer
- No context management for conversations

## Feature Requirements

### 1. Natural Language Goal Submission

**User Experience:**
```
User: "Plan a comprehensive testing strategy for the platform"
System: [Creates Goal, invokes PlanningService, returns ExecutionPlan]

User: "Deploy 5 data processing agents with high throughput configuration"
System: [Invokes LifecycleManager, returns agent deployment status]

User: "What's the status of my testing workflow?"
System: [Queries L01 for goal/plan status, returns summary]
```

**Components Needed:**
- Intent parser (NLU or LLM-based)
- Goal constructor (natural language → Goal object)
- Command router (maps intent to L01-L11 operations)
- Response formatter (platform output → natural language)

### 2. Slash Command System

**Proposed Commands:**

**Planning & Goals:**
- `/plan <goal_description>` - Create and decompose goal using PlanningService
- `/goals` - List all goals and their status
- `/goal <goal_id>` - Get detailed goal information
- `/execute <goal_id>` - Execute a decomposed plan

**Agent Management:**
- `/agents` - List all agents
- `/deploy <agent_type> [config]` - Deploy new agent
- `/agent <agent_id>` - Get agent details
- `/shutdown <agent_id>` - Shutdown agent

**Orchestration:**
- `/orchestrate <workflow_type>` - Start orchestrated workflow
- `/saga <saga_definition>` - Execute distributed saga
- `/status [entity_id]` - Get execution status

**System Operations:**
- `/health` - Platform health check
- `/metrics` - System metrics summary
- `/events [filter]` - Stream L01 events

**Query & Inspection:**
- `/query <entity_type> [filters]` - Query L01 data
- `/inspect <entity_id>` - Deep inspection of entity
- `/trace <trace_id>` - Follow execution trace

### 3. CLI Integration Architecture

**Option A: HTTP Proxy Layer**
```
User in Claude CLI → L12 NL Interface Layer (FastAPI)
                      ↓
                   Intent Parser → Command Router
                      ↓
                   L01-L11 Platform Services
```

**Option B: MCP Server Pattern**
```
User in Claude CLI → Claude MCP Server
                      ↓
                   Platform MCP Tools
                      ↓
                   L01-L11 Platform Services
```

**Option C: Embedded CLI Agent**
```
User → Platform CLI Tool → Platform Agent (with NL capabilities)
                            ↓
                         L01-L11 Services
```

### 4. Context Management

**Session Context:**
- User identity/tenant tracking
- Conversation history
- Active goals/workflows
- Execution traces

**Platform State:**
- Real-time L01 event subscription
- Agent registry awareness
- Resource availability
- Execution queue status

## Implementation Plan

### Phase 1: HTTP Interface Layer (L12)

**Create:** `src/L12_nl_interface/`
- `app.py` - FastAPI application
- `intent_parser.py` - Natural language → intent
- `command_router.py` - Intent → platform operations
- `response_formatter.py` - Platform output → NL
- `session_manager.py` - User session tracking

**Endpoints:**
- `POST /nl/query` - Natural language query
- `POST /nl/command` - Slash command execution
- `GET /nl/context` - Get session context
- `WS /nl/stream` - Real-time event stream

### Phase 2: Intent Recognition

**Strategies:**
1. **Pattern Matching** (simple, fast)
   - Regex patterns for common commands
   - Direct mapping to platform operations

2. **LLM-based NLU** (flexible, accurate)
   - Use L04 Model Gateway for intent classification
   - Extract entities (goal descriptions, agent IDs, filters)
   - Handle ambiguity with clarification prompts

3. **Hybrid Approach** (recommended)
   - Pattern matching for slash commands
   - LLM for complex natural language goals

### Phase 3: Platform Integration

**Service Connectors:**
- `PlanningServiceConnector` - L05 integration
- `RuntimeConnector` - L02 integration
- `DataLayerConnector` - L01 queries
- `OrchestrationConnector` - TaskOrchestrator, SagaOrchestrator

**Response Streaming:**
- Subscribe to L01 Redis events
- Stream progress updates to user
- Format events as natural language updates

### Phase 4: Claude CLI Integration

**Options:**

**A) MCP Server (Recommended):**
- Create platform MCP server
- Register with Claude Code
- Tools exposed as native Claude capabilities

**B) HTTP Client Wrapper:**
- Bash script that calls L12 HTTP endpoints
- Integrates with Claude CLI via skills/hooks

**C) Direct Python Client:**
- Python CLI tool that imports platform directly
- Can be invoked from Claude CLI

## Success Criteria

✅ User can submit natural language goals and get execution plans
✅ All slash commands work and route to correct platform services
✅ Real-time streaming of execution progress
✅ Session context maintained across conversation
✅ Errors are handled gracefully with natural language explanations
✅ Integration with Claude CLI feels seamless

## Technical Considerations

**Authentication:**
- API key for L12 access
- User/tenant identification
- Permission checking via L09 patterns

**Error Handling:**
- Graceful degradation when services unavailable
- Clear error messages in natural language
- Retry logic for transient failures

**Performance:**
- Intent parsing < 100ms
- Platform operation routing < 50ms
- Streaming event latency < 500ms

**Security:**
- Input validation on all natural language
- SQL injection prevention in queries
- Rate limiting on L12 endpoints
- Audit logging of all commands

## Related Documents

- [Platform Architecture](/docs/architecture.md)
- [L05 Planning Layer](/src/L05_planning/README.md)
- [L09 API Gateway](/src/L09_api_gateway/README.md)
- [Testing Strategy](/TESTING_REPORT.md)

## Notes

- This feature gap was identified on 2026-01-15 during platform exploration
- User expectation was to interact with PlanningService via natural language
- Current workaround: Write Python scripts that import services directly
- High-value feature for platform adoption and usability

## TODO Checklist

**High Priority:**
- [ ] Create L12_nl_interface layer structure
- [ ] Implement basic slash command system
- [ ] Build intent parser (pattern-based + LLM fallback)
- [ ] Create command router with L01-L11 connectors
- [ ] Add `/plan` command for PlanningService access
- [ ] Add `/goals` and `/agents` commands
- [ ] Implement session context management

**Medium Priority:**
- [ ] Response formatting (platform output → natural language)
- [ ] Real-time event streaming via WebSocket
- [ ] Complex goal parsing (multi-step workflows)
- [ ] MCP server integration for Claude CLI

**Low Priority:**
- [ ] Voice interface consideration
- [ ] Multi-language support
- [ ] Advanced context tracking (conversation memory)
- [ ] Proactive suggestions based on platform state

---

**REMINDER:** This feature gap blocks intuitive platform usage. Every time you interact with the platform, you'll need to write Python code or use low-level HTTP APIs. Prioritize L12 NL Interface Layer implementation.

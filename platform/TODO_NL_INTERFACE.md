# TODO: Natural Language Interface Implementation

**Quick Reference Card for Feature Work**

## 🎯 GOAL
Enable natural language interaction with platform features via Claude CLI

## ⚡ Quick Start Commands (FUTURE)
```bash
# What you WANT to be able to do:
/plan "Create comprehensive testing strategy"
/deploy agent type=qa count=3
/goals status=active
/execute plan_id=abc123
/status
```

## 📋 Implementation Checklist

### Week 1: Foundation
- [ ] **Create L12 layer structure** (`src/L12_nl_interface/`)
  - [ ] `app.py` - FastAPI server
  - [ ] `models.py` - Request/response models
  - [ ] `config/settings.py` - Configuration
  - [ ] `tests/` - Test suite

- [ ] **Basic HTTP endpoints**
  - [ ] `POST /nl/command` - Execute slash commands
  - [ ] `POST /nl/query` - Natural language queries
  - [ ] `GET /health` - Health check
  - [ ] `WS /nl/stream` - Event stream

### Week 2: Command System
- [ ] **Implement slash command parser**
  - [ ] Pattern matching for commands
  - [ ] Argument extraction
  - [ ] Validation

- [ ] **Command handlers** (start with these 5):
  - [ ] `/plan <goal>` → PlanningService.create_plan()
  - [ ] `/goals` → L01Client.list_goals()
  - [ ] `/agents` → L01Client.list_agents()
  - [ ] `/status` → Multi-layer status aggregation
  - [ ] `/execute <plan_id>` → PlanningService.execute_plan()

### Week 3: Natural Language
- [ ] **Intent parser**
  - [ ] Pattern-based intent recognition
  - [ ] L04 LLM fallback for complex queries
  - [ ] Entity extraction (IDs, filters, configs)

- [ ] **Goal constructor**
  - [ ] Natural language → Goal object
  - [ ] GoalConstraints inference
  - [ ] Validation

### Week 4: Integration
- [ ] **Platform service connectors**
  - [ ] PlanningServiceConnector (L05)
  - [ ] RuntimeConnector (L02)
  - [ ] DataLayerConnector (L01)
  - [ ] OrchestrationConnector (TaskOrchestrator)

- [ ] **Event streaming**
  - [ ] Subscribe to L01 Redis events
  - [ ] Filter relevant events per session
  - [ ] Format as natural language updates

### Week 5: Claude CLI Integration
- [ ] **MCP Server** (recommended approach)
  - [ ] Create platform MCP server package
  - [ ] Define tools for each command
  - [ ] Register with Claude Code config
  - [ ] Test end-to-end flow

- [ ] **Documentation**
  - [ ] User guide for slash commands
  - [ ] API documentation for L12
  - [ ] Integration guide for Claude CLI

## 🔧 Technical Stack

**L12 NL Interface:**
- FastAPI (HTTP server)
- Pydantic (models)
- httpx (L01-L11 HTTP clients)
- Redis (session management)
- L04 Model Gateway (intent parsing)

**Claude CLI Integration:**
- MCP Server protocol
- WebSocket (real-time streaming)
- Skills/hooks (alternative approach)

## 📝 Example Usage (Target UX)

### Natural Language Goal Submission
```
You: "Plan a comprehensive testing strategy covering unit tests,
      integration tests, and load tests for all layers"

System: ✓ Goal created: test-strategy-2026-01-15
        ✓ PlanningService decomposing...
        ✓ ExecutionPlan ready with 15 tasks

        Summary:
        - 4 tasks for unit testing (L01-L04)
        - 3 tasks for integration testing
        - 2 tasks for load testing
        - 3 tasks for E2E validation
        - 3 tasks for reporting

        Ready to execute? [y/n]
```

### Slash Command Execution
```
You: /plan "Deploy production monitoring agents"

System: Creating goal and planning...
        Goal ID: mon-agents-f7a3b2
        Plan ID: plan-f7a3b2

        Decomposed into 8 tasks:
        1. Provision infrastructure
        2. Deploy collector agents (x5)
        3. Configure metrics pipeline
        4. Set up alerting rules
        5. Deploy dashboard
        6. Integration testing
        7. Smoke tests
        8. Production cutover

        Execute now? [y/n]
```

### Status Monitoring
```
You: /status mon-agents-f7a3b2

System: Goal: mon-agents-f7a3b2
        Status: IN_PROGRESS
        Plan: plan-f7a3b2
        Progress: 5/8 tasks completed (62%)

        Currently executing:
        - Task 6: Integration testing
          Started: 2 minutes ago
          Agent: test-runner-42

        Completed:
        ✓ Task 1: Provision infrastructure (2m 13s)
        ✓ Task 2: Deploy collector agents (5m 47s)
        ✓ Task 3: Configure metrics pipeline (1m 32s)
        ✓ Task 4: Set up alerting rules (0m 45s)
        ✓ Task 5: Deploy dashboard (3m 18s)
```

## 🚨 REMINDER TRIGGERS

**When starting any Claude CLI session:**
→ Check if L12_nl_interface exists yet

**When writing platform integration code:**
→ Consider: "Could this be exposed via slash command?"

**When adding new platform features:**
→ Add corresponding command to L12 command registry

**When user asks "how do I use X feature":**
→ Remind: "L12 NL Interface not implemented yet. See TODO_NL_INTERFACE.md"

## 🎯 Success Metrics

- [ ] User can submit goal in natural language
- [ ] Goal gets decomposed and executed automatically
- [ ] Real-time progress updates stream to CLI
- [ ] All 10+ slash commands work reliably
- [ ] < 2 second end-to-end latency
- [ ] Error messages are clear and actionable

## 🔗 References

- **Feature Specification:** `/platform/FEATURE_GAP_NL_INTERFACE.md`
- **PlanningService API:** `/src/L05_planning/services/planning_service.py`
- **L01 Client:** `/src/L01_data_layer/client.py`
- **MCP Documentation:** https://modelcontextprotocol.io

---

**CURRENT STATUS:** 🔴 NOT STARTED
**NEXT ACTION:** Create `src/L12_nl_interface/` directory structure
**BLOCKING:** User cannot easily interact with platform features

# Platform Services - MCP Tools Quick Reference

**Alternative to `/platform` command**

Since the `/platform` slash command doesn't load on ExFAT filesystems, use these MCP tools directly. They provide 100% of the functionality with no filesystem dependencies.

---

## Quick Start

### 1. Browse All Services
```javascript
mcp__platform-services__browse_services()
```
Returns all 44 services organized by 11 functional categories.

### 2. Search for Services
```javascript
mcp__platform-services__search_services({ query: "planning" })
```
Natural language search across service names and descriptions.

### 3. List All Workflows
```javascript
mcp__platform-services__list_workflows()
```
Shows 6 pre-defined workflow templates (testing, deployment, data pipelines, monitoring).

---

## Common Operations

### Get Service Details
```javascript
mcp__platform-services__get_service_info({
  service_name: "PlanningService"
})
```

### List Service Methods
```javascript
mcp__platform-services__list_methods({
  service_name: "PlanningService"
})
```

### Invoke a Service Method
```javascript
mcp__platform-services__invoke_service({
  command: "PlanningService.create_plan",
  parameters: {
    goal: "Implement user authentication feature",
    constraints: ["Must support OAuth 2.0", "Complete within 2 weeks"],
    context: "Existing system uses JWT tokens"
  }
})
```

---

## Workflow Execution

### Get Workflow Details
```javascript
mcp__platform-services__get_workflow_info({
  workflow_name: "testing.unit"
})
```

### Execute a Workflow
```javascript
mcp__platform-services__execute_workflow({
  workflow_name: "testing.unit",
  parameters: {
    test_path: "tests/unit/",
    verbose: true
  }
})
```

---

## Available Workflows

1. **testing.unit** - Run unit tests
   ```javascript
   mcp__platform-services__execute_workflow({
     workflow_name: "testing.unit",
     parameters: { test_path: "tests/unit/" }
   })
   ```

2. **testing.integration** - Integration tests with setup
   ```javascript
   mcp__platform-services__execute_workflow({
     workflow_name: "testing.integration",
     parameters: {
       test_path: "tests/integration/",
       environment: "staging"
     }
   })
   ```

3. **deployment.standard** - Build, test, deploy
   ```javascript
   mcp__platform-services__execute_workflow({
     workflow_name: "deployment.standard",
     parameters: {
       environment: "production",
       version: "1.0.0"
     }
   })
   ```

4. **deployment.canary** - Gradual rollout
   ```javascript
   mcp__platform-services__execute_workflow({
     workflow_name: "deployment.canary",
     parameters: {
       environment: "production",
       canary_percentage: 10
     }
   })
   ```

5. **data_pipeline.etl** - Extract, transform, load
   ```javascript
   mcp__platform-services__execute_workflow({
     workflow_name: "data_pipeline.etl",
     parameters: {
       source: "postgresql://localhost/source_db",
       destination: "s3://bucket/data/"
     }
   })
   ```

6. **monitoring.health_check** - System health check
   ```javascript
   mcp__platform-services__execute_workflow({
     workflow_name: "monitoring.health_check",
     parameters: {}
   })
   ```

---

## Service Categories

### Data & Storage (12 services)
- AgentRegistry, ConfigStore, DatasetService, DocumentStore
- EvaluationStore, EventStore, FeedbackStore, GoalStore
- PlanStore, SessionService, ToolRegistry, TrainingExampleService

### Agent Management (4 services)
- AgentAssigner, AgentExecutor, FleetManager, LifecycleManager

### Resource & Infrastructure (3 services)
- ResourceManager, SandboxManager, StateManager

### Workflow & Orchestration (4 services)
- RequestOrchestrator, SagaOrchestrator, TaskOrchestrator, WorkflowEngine

### Planning & Strategy (2 services)
- GoalDecomposer, PlanningService

### Tool Execution (2 services)
- ToolComposer, ToolExecutor

### AI & Models (3 services)
- LLMRouter, ModelGateway, SemanticCache

### Evaluation & Monitoring (3 services)
- AlertManager, EvaluationService, MetricsEngine

### Learning & Training (3 services)
- DatasetCurator, FineTuningEngine, LearningService

### Security & Access (2 services)
- AuthenticationHandler, AuthorizationEngine

### Integration & Communication (3 services)
- EventBusManager, RequestRouter, ServiceRegistry

### User Interface (3 services)
- ControlService, DashboardService, WebSocketGateway

---

## Advanced Usage

### Filter Services by Search
```javascript
mcp__platform-services__browse_services({
  search: "deployment"
})
```

### Check Session Info
```javascript
mcp__platform-services__get_session_info()
```

### Search Workflows
```javascript
mcp__platform-services__search_workflows({
  query: "deployment"
})
```

### Filter Workflows by Category
```javascript
mcp__platform-services__list_workflows({
  category: "testing"
})
```

---

## Example: Planning a Feature

```javascript
// 1. Search for planning services
mcp__platform-services__search_services({ query: "planning" })

// 2. Get details on PlanningService
mcp__platform-services__get_service_info({
  service_name: "PlanningService"
})

// 3. List available methods
mcp__platform-services__list_methods({
  service_name: "PlanningService"
})

// 4. Create a plan
mcp__platform-services__invoke_service({
  command: "PlanningService.create_plan",
  parameters: {
    goal: "Build user dashboard with real-time metrics",
    constraints: [
      "Must load in under 2 seconds",
      "Support 1000+ concurrent users",
      "Mobile responsive design"
    ],
    context: "Existing React app with Redux state management"
  }
})
```

---

## Example: Running Tests

```javascript
// 1. List testing workflows
mcp__platform-services__list_workflows({ category: "testing" })

// 2. Get workflow details
mcp__platform-services__get_workflow_info({
  workflow_name: "testing.unit"
})

// 3. Execute tests
mcp__platform-services__execute_workflow({
  workflow_name: "testing.unit",
  parameters: {
    test_path: "tests/unit/",
    verbose: true,
    coverage: true
  }
})
```

---

## Tips

1. **Start with browse_services** to discover what's available
2. **Use search_services** when you know what you're looking for
3. **Pre-defined workflows** save time for common operations
4. **Get workflow details** before executing to understand parameters
5. **Check session_info** to verify MCP server status

---

## Requirements

- Platform services MCP server must be running
- Some features require Redis (WebSocket, Command History)
- Semantic search requires Ollama (falls back to keyword search)
- Workflow execution may take seconds to minutes depending on complexity

---

## Troubleshooting

### "MCP server not found" error
```bash
# Check MCP server configuration
cat ~/.claude/mcp.json

# Verify platform-services server is listed
# Should have entry for "platform-services"
```

### Tools not showing up
```javascript
// List all available MCP tools
// Look for "mcp__platform-services__*" tools
```

### Workflow execution fails
```javascript
// Check workflow parameters first
mcp__platform-services__get_workflow_info({
  workflow_name: "testing.unit"
})

// Verify all required parameters are provided
```

---

## Comparison to `/platform` Command

| Feature | `/platform` Command | MCP Tools Direct |
|---------|---------------------|------------------|
| Browse services | ✅ Menu-driven | ✅ Function call |
| Search services | ✅ Interactive | ✅ Function call |
| Execute workflows | ✅ Step-by-step | ✅ Single call |
| Service details | ✅ Interactive | ✅ Function call |
| Filesystem dependency | ❌ ExFAT issues | ✅ No dependency |
| Requires restart | ✅ Yes | ❌ No |
| User-friendly | ✅✅ Very | ⚠️ Moderate |
| Reliability | ⚠️ ExFAT issues | ✅✅ Always works |

---

## Summary

MCP tools provide **100% of the functionality** of the `/platform` command with **no filesystem dependencies**. They work reliably on all systems, including ExFAT drives where the slash command fails.

**Recommended workflow:**
1. Browse or search to discover services
2. Get details on interesting services
3. Invoke methods or execute workflows directly
4. No command files needed

This approach is actually **more powerful** than the command interface because you can:
- Chain operations programmatically
- Pass complex parameters as JSON
- Get structured output for further processing
- No menu navigation needed (faster)

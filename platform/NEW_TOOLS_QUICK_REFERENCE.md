# Platform Services - New Tools Quick Reference

After restarting Claude CLI, these 5 NEW tools are available:

## 1. browse_services 🆕
Browse all services organized by functional category (not layer-based).

**Usage**:
```
browse_services()
browse_services(search="planning")
```

**Returns**: Services grouped by 12 categories:
- Data & Storage
- Agent Management
- Resource & Infrastructure
- Workflow & Orchestration
- Planning & Strategy
- Tool Execution
- AI & Models
- Evaluation & Monitoring
- Learning & Training
- Security & Access
- Integration & Communication
- User Interface

---

## 2. list_workflows 🆕
List available workflow templates for common operations.

**Usage**:
```
list_workflows()
list_workflows(category="testing")
list_workflows(category="deployment")
```

**Categories**: testing, deployment, data_pipeline, monitoring

**Returns**: 6 pre-defined workflows:
- `testing.unit` - Run unit tests
- `testing.integration` - Run integration tests with environment setup
- `deployment.standard` - Build, test, and deploy
- `deployment.canary` - Canary deployment with gradual rollout
- `data_pipeline.etl` - Extract, transform, load pipeline
- `monitoring.health_check` - Comprehensive health check

---

## 3. get_workflow_info 🆕
Get detailed information about a specific workflow.

**Usage**:
```
get_workflow_info(workflow_name="testing.unit")
```

**Returns**: Steps, parameters, dependencies, and execution flow

---

## 4. execute_workflow 🆕
Execute a multi-service workflow with custom parameters.

**Usage**:
```
execute_workflow(
  workflow_name="testing.unit",
  parameters={"test_path": "tests/unit/"}
)
```

**Returns**: Step-by-step execution results

---

## 5. search_workflows 🆕
Search for workflows by name, description, or tags.

**Usage**:
```
search_workflows(query="deployment")
search_workflows(query="testing")
```

**Returns**: Matching workflow templates

---

## Existing Tools (Still Available)

- `invoke_service` - Execute a service method
- `search_services` - Search services (now with semantic matching!)
- `list_services` - List all services
- `get_service_info` - Get service details
- `list_methods` - List service methods
- `get_session_info` - Get session info

---

## Quick Examples

### Discover Services by What They Do
```
browse_services()  # See all categories
browse_services(search="planning")  # Find planning-related services
```

### Run Pre-Defined Workflows
```
list_workflows()  # See all workflows
execute_workflow(workflow_name="testing.unit", parameters={"test_path": "tests/"})
```

### Search for Workflows
```
search_workflows(query="deployment")  # Find deployment workflows
```

---

## Troubleshooting

If you don't see these tools:
1. ✅ Quit Claude CLI completely (Cmd+Q on Mac)
2. ✅ Restart Claude CLI
3. ✅ Type `/mcp` to verify "platform-services" is loaded
4. ✅ Try using one of the new tools

**Note**: The server name changed from "l12-platform" to "platform-services"

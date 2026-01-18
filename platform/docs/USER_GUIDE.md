# Platform Control Center - User Guide

**Version**: 2.0.0
**Last Updated**: January 17, 2026

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Dashboard](#dashboard)
3. [Agent Management](#agent-management)
4. [Service Explorer](#service-explorer)
5. [Workflow Management](#workflow-management)
6. [Goals & Planning](#goals--planning)
7. [System Monitoring](#system-monitoring)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)

---

## Getting Started

### Accessing the Platform

1. Open your web browser
2. Navigate to **http://localhost:3000**
3. The dashboard will load automatically

### Navigation

The Platform Control Center uses a sidebar navigation menu:

- **Dashboard** - System overview and real-time metrics
- **Agents** - Create and manage execution agents
- **Services** - Browse and invoke platform services
- **Workflows** - Build and execute multi-step workflows
- **Goals** - Strategic planning and goal tracking
- **Monitoring** - System health and performance analytics

### Connection Status

- **Green dot** - Connected to platform backend
- **Yellow dot** - Connecting/reconnecting
- **Red dot** - Disconnected (check services)

---

## Dashboard

The dashboard provides a real-time overview of your platform.

### Statistics Cards

#### Active Agents
- Shows running agents vs. total agents
- Click to navigate to Agents page

#### Services Available
- Total count of platform services
- Access to L01-L12 layers

#### System Health
- Overall platform status
- "healthy", "degraded", or "unhealthy"

#### Success Rate
- Percentage of successful API requests
- Updated every 5 seconds

### Resource Usage

**CPU Usage**: Platform compute resource utilization
- Blue progress bar
- Updates every 5 seconds

**Memory Usage**: Platform memory consumption
- Green progress bar
- Shows percentage of allocated memory

**Avg Response Time**: API latency metrics
- Measured in milliseconds
- Lower is better

**Total Requests**: Cumulative request count
- All platform API calls
- Since service start

### Recent Events

Real-time event stream from the platform:
- Agent state changes
- Service invocations
- Workflow executions
- System alerts

Events display:
- Event type (e.g., "agent.started", "workflow.completed")
- Payload preview
- Timestamp

### Active Agents Table

Shows up to 5 most recently active agents:
- Agent ID (truncated)
- Agent type
- Status badge (running, paused, terminated)
- Capabilities list

---

## Agent Management

Agents are autonomous execution units that perform tasks on the platform.

### Viewing Agents

The Agents page displays all platform agents in a table:

**Columns**:
- **Agent ID**: Unique identifier (12-char preview)
- **Type**: developer, researcher, qa, general
- **Status**: idle, running, paused, terminated, failed
- **Capabilities**: Agent skills (max 2 shown, truncated)
- **Created**: Timestamp of agent creation
- **Actions**: Control buttons

### Creating an Agent

1. Click **"Create Agent"** button
2. Fill in the form:
   - **Agent Type**: Select from dropdown
     - Developer: Code writing and analysis
     - Researcher: Information gathering
     - QA: Testing and quality assurance
     - General Purpose: Multi-purpose agent
   - **Capabilities**: Add skills (e.g., "python", "testing", "analysis")
     - Click "+ Add Capability"
     - Enter capability name
     - Repeat for multiple capabilities
   - **Resource Limits**:
     - CPU Limit: e.g., "1.0" (1 core)
     - Memory Limit: e.g., "2Gi" (2 gigabytes)
3. Click **"Create Agent"**
4. Agent will appear in the table

### Controlling Agents

**Pause Agent** (⏸️):
- Suspends agent execution
- Preserves agent state
- Can be resumed later

**Resume Agent** (▶️):
- Restarts a paused agent
- Continues from last state

**Terminate Agent** (⏹️):
- Permanently stops agent
- Cleans up resources
- Cannot be restarted

### Agent Status Badges

- 🟢 **Running**: Agent is actively executing
- 🟡 **Paused**: Agent is suspended
- ⚫ **Terminated**: Agent has been stopped
- 🔴 **Failed**: Agent encountered an error

---

## Service Explorer

Browse and invoke all 44 platform services across 9 layers.

### Browsing Services

Services are organized by layer:

**L01: Data Layer** (12 services)
- AgentRegistry, EventBus, ConfigStore, etc.

**L02: Runtime** (4 services)
- AgentRuntime, Sandbox, ResourceManager, etc.

**L03: Tool Execution** (5 services)
- ToolCatalog, ToolExecutor, Cache, etc.

**L04: Model Gateway** (4 services)
- ModelRouter, Cache, RateLimiter, etc.

**L05: Planning** (4 services)
- GoalDecomposer, TaskPlanner, etc.

**L06: Evaluation** (3 services)
- QualityMetrics, TrainingEvaluator, etc.

**L07: Learning** (3 services)
- TrainingManager, ModelFinetuner, etc.

**L10: Human Interface** (4 services)
- Dashboard, WebSocketManager, etc.

**L11: Integration** (4 services)
- SagaOrchestrator, CircuitBreaker, etc.

### Searching Services

1. Use the search bar at the top
2. Enter keywords (e.g., "agent", "plan", "workflow")
3. Fuzzy matching finds relevant services
4. Results show match score and reason

### Invoking a Service

1. Click on a service card
2. The invocation panel appears:
   - **Service Name**: Auto-filled
   - **Method Name**: Enter method (e.g., "list_agents")
   - **Parameters**: Enter JSON object
     ```json
     {"status": "running", "limit": 10}
     ```
3. Click **"Invoke"**
4. Results appear below:
   - **Success**: Green box with JSON result
   - **Error**: Red box with error message

**Example Invocations**:

```json
// List all agents
Service: AgentRegistry
Method: list_agents
Parameters: {}

// Create a goal
Service: GoalStore
Method: create_goal
Parameters: {
  "description": "Implement user authentication",
  "priority": "high"
}

// Search services
Service: ServiceRegistry
Method: search
Parameters: {
  "query": "agent orchestration",
  "threshold": 0.7
}
```

---

## Workflow Management

Create and execute multi-step workflows that chain services together.

### Viewing Workflows

The Workflows page shows all defined workflows in a grid:
- Workflow name
- Description
- Number of steps
- Execute button

### Creating a Workflow

1. Click **"Create Workflow"** button
2. Fill in the form:
   - **Workflow ID**: Unique identifier (e.g., "testing.unit")
   - **Workflow Name**: Human-readable name (e.g., "Run Unit Tests")
   - **Description**: What the workflow does
   - **Workflow Steps**: Add service invocations
     - Click "+ Add Step"
     - Enter service name (e.g., "TestRunner")
     - Enter method name (e.g., "run_tests")
     - Steps execute in order
3. Click **"Create Workflow"**

**Example Workflow**:
```
Workflow ID: code.quality.check
Name: Code Quality Check
Description: Run linting, type checking, and tests

Steps:
1. CodeLinter.lint → parameters: {"path": "src/"}
2. TypeChecker.check → parameters: {"strict": true}
3. TestRunner.run_all → parameters: {"coverage": true}
```

### Executing a Workflow

1. Click on a workflow card or click "Execute →"
2. The execution panel appears
3. Enter parameters (JSON):
   ```json
   {
     "test_path": "tests/unit/",
     "coverage_threshold": 80
   }
   ```
4. Click **"Execute"**
5. Execution starts and appears in history table

### Execution History

The history table shows past workflow runs:
- **Execution ID**: Unique identifier
- **Workflow**: Which workflow was run
- **Status**: pending, running, completed, failed
- **Started**: Timestamp
- **Duration**: How long it took

**Status Icons**:
- ✅ **Completed**: Workflow finished successfully
- ❌ **Failed**: Workflow encountered an error
- 🔄 **Running**: Workflow is currently executing
- ⏱️ **Pending**: Workflow is queued

---

## Goals & Planning

Strategic planning with goal decomposition and task tracking.

### Creating a Goal

1. Click **"Create Goal"** button
2. Fill in the form:
   - **Goal Description**: What you want to achieve
     - Be specific and measurable
     - Example: "Implement user authentication with OAuth 2.0"
   - **Priority**: low, medium, or high
3. Click **"Create Goal"**

**Priority Levels**:
- 🔴 **High**: Critical, urgent
- 🟡 **Medium**: Important, normal timeline
- 🟢 **Low**: Nice-to-have, flexible timeline

### Viewing Goals

Goals are displayed in a grid with:
- Priority indicator
- Status badge (pending, in_progress, completed, failed)
- Goal description
- Goal ID and creation date

Click on a goal to view associated plans.

### Creating a Plan

1. Click **"Create Plan"** button
2. Fill in the form:
   - **Goal ID**: Enter the goal this plan addresses
   - **Strategy**: High-level approach to achieve the goal
     - Example: "Use FastAPI for backend, React for frontend"
   - **Tasks**: Break down into executable tasks
     - Click "+ Add Task"
     - Enter task ID and description
     - Add multiple tasks
3. Click **"Create Plan"**

**Example Plan**:
```
Goal ID: goal_12345
Strategy: Implement OAuth 2.0 using Auth0 service

Tasks:
1. setup_auth0 → Create Auth0 account and configure application
2. backend_integration → Add Auth0 SDK to FastAPI backend
3. frontend_integration → Add Auth0 React SDK to frontend
4. test_auth_flow → Test login, logout, and token refresh
5. deploy_changes → Deploy to staging and production
```

### Task Status Tracking

Each task in a plan shows:
- Status icon (⏱️ pending, 🔄 in_progress, ✅ completed, ❌ failed)
- Task ID
- Description
- Dependencies (if any)

---

## System Monitoring

Comprehensive system health and performance monitoring.

### System Health Status

Top status indicator shows:
- 🟢 **Healthy**: All systems operational
- 🟡 **Degraded**: Some issues detected
- 🔴 **Unhealthy**: Critical problems

### System Statistics

Four primary metrics:

**CPU Usage**: Platform compute utilization
- Shows percentage and trend
- Normal: < 70%
- Warning: 70-90%
- Critical: > 90%

**Memory Usage**: Platform memory consumption
- Shows percentage and trend
- Normal: < 80%
- Warning: 80-95%
- Critical: > 95%

**Avg Response Time**: API latency
- Measured in milliseconds
- Good: < 100ms
- Acceptable: 100-500ms
- Slow: > 500ms

**Error Rate**: Failed request percentage
- Lower is better
- Good: < 1%
- Warning: 1-5%
- Critical: > 5%

### Performance Metrics

**Total Requests**: Cumulative API calls
**Success Rate**: Percentage of successful requests
**Total Cost**: Estimated infrastructure cost
**Token Usage**: LLM token consumption

### Recent Alerts

Real-time alert feed showing:
- Error events
- Failed operations
- High severity events

**Alert Severity**:
- 🔴 **Critical**: Immediate action required
- 🟡 **Medium**: Needs attention
- 🟢 **Low**: Informational

### Service Health

Shows health of all platform layers:
- L01-L12 service status
- Response time (latency)
- Health badge (healthy/unhealthy)

### Event Log

Comprehensive event log with:
- Timestamp
- Event type
- Source
- Severity
- Payload

Filter by time range: 1h, 24h, 7d, 30d

### Cost Analytics

**Estimated Daily Cost**: Cost per day based on current usage
**Estimated Monthly Cost**: Projected monthly infrastructure cost
**Cost per Request**: Average cost per API call

---

## Troubleshooting

### Common Issues

#### UI Not Loading
**Symptoms**: Blank page or loading spinner
**Solutions**:
1. Check browser console for errors (F12)
2. Verify platform-ui container is running:
   ```bash
   docker ps | grep platform-ui
   ```
3. Check nginx logs:
   ```bash
   docker logs platform-ui
   ```
4. Restart the UI container:
   ```bash
   docker-compose -f docker-compose.app.yml restart platform-ui
   ```

#### WebSocket Disconnected
**Symptoms**: Red connection indicator, no real-time updates
**Solutions**:
1. Check L10 Human Interface is running:
   ```bash
   docker ps | grep l10-human-interface
   ```
2. Verify WebSocket endpoint:
   ```bash
   curl -I http://localhost:8010/ws/
   ```
3. Refresh the browser page
4. Check browser console for WebSocket errors

#### Services Not Loading
**Symptoms**: Empty service list, "Loading services..." stuck
**Solutions**:
1. Check L12 Service Hub is healthy:
   ```bash
   curl http://localhost:8012/health
   ```
2. Verify L01 Data Layer is running:
   ```bash
   curl http://localhost:8001/health/live
   ```
3. Check API Gateway routing:
   ```bash
   curl http://localhost:8009/health/live
   ```

#### Agent Creation Fails
**Symptoms**: Error message when creating agent
**Solutions**:
1. Verify resource limits are valid (e.g., "1.0", "2Gi")
2. Check L02 Runtime is healthy:
   ```bash
   curl http://localhost:8002/health/live
   ```
3. Review error message for specific issues
4. Check agent type is valid (developer, researcher, qa, general)

### Getting Help

If issues persist:
1. Check Docker container logs:
   ```bash
   docker-compose -f docker-compose.app.yml logs platform-ui
   ```
2. Check backend service logs:
   ```bash
   docker-compose -f docker-compose.app.yml logs l09-api-gateway
   docker-compose -f docker-compose.app.yml logs l10-human-interface
   ```
3. Verify all containers are healthy:
   ```bash
   docker-compose -f docker-compose.app.yml ps
   ```

---

## Best Practices

### Agent Management
- ✅ Use descriptive agent types
- ✅ Assign specific capabilities for better tracking
- ✅ Set appropriate resource limits (avoid overallocation)
- ✅ Terminate unused agents to free resources
- ✅ Monitor agent status regularly
- ❌ Don't create excessive agents simultaneously
- ❌ Don't use generic capabilities (be specific)

### Workflow Design
- ✅ Keep workflows focused (single responsibility)
- ✅ Use clear, descriptive names
- ✅ Add detailed descriptions
- ✅ Test workflows with sample parameters first
- ✅ Monitor execution history for failures
- ❌ Don't create overly complex workflows
- ❌ Don't hardcode parameters (use workflow params)

### Service Invocation
- ✅ Review service documentation before invoking
- ✅ Validate JSON parameters before submission
- ✅ Start with small test invocations
- ✅ Check for errors in response
- ❌ Don't invoke services without understanding what they do
- ❌ Don't use production data for testing

### Goal & Plan Management
- ✅ Create measurable, specific goals
- ✅ Break goals into small, actionable tasks
- ✅ Set realistic priorities
- ✅ Update goal status as work progresses
- ✅ Document strategy clearly
- ❌ Don't create vague or unmeasurable goals
- ❌ Don't skip task breakdown (plans without tasks)

### Monitoring
- ✅ Check dashboard regularly (daily)
- ✅ Set up alerts for critical metrics
- ✅ Review event log for patterns
- ✅ Monitor resource usage trends
- ✅ Track cost analytics
- ❌ Don't ignore degraded health status
- ❌ Don't dismiss recurring errors

---

## Keyboard Shortcuts

### Navigation
- `Alt + D` - Dashboard
- `Alt + A` - Agents
- `Alt + S` - Services
- `Alt + W` - Workflows
- `Alt + G` - Goals
- `Alt + M` - Monitoring

### Actions
- `Ctrl + N` - Create new (context-aware)
- `Ctrl + R` - Refresh current page
- `Esc` - Close modals/panels
- `Tab` - Navigate form fields
- `Enter` - Submit forms

---

## Support & Feedback

### Documentation
- **User Guide**: This document
- **API Reference**: `/docs/API_REFERENCE.md`
- **Workflow Guide**: `/docs/WORKFLOW_GUIDE.md`
- **Developer Guide**: `/docs/DEVELOPER_GUIDE.md`

### Platform Information
- **Version**: 2.0.0
- **Release Date**: January 17, 2026
- **Technology**: React 18 + TypeScript
- **Architecture**: Microservices (L01-L12)

---

**Last Updated**: January 17, 2026
**Document Version**: 1.0.0

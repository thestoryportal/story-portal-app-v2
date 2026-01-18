# Platform API Reference

**Version**: 2.0.0
**Last Updated**: January 17, 2026

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Agent Management API](#agent-management-api)
4. [Service Discovery API](#service-discovery-api)
5. [Workflow API](#workflow-api)
6. [Goals & Planning API](#goals--planning-api)
7. [Events API](#events-api)
8. [Context Management API](#context-management-api)
9. [Metrics & Health API](#metrics--health-api)
10. [WebSocket API](#websocket-api)
11. [Error Handling](#error-handling)

---

## Overview

The Platform API provides programmatic access to all platform capabilities. All APIs are accessible through the L09 API Gateway on port 8009.

### Base URL

```
http://localhost:8009
```

### Request Format

All requests use JSON format:

```http
POST /l01/agents
Content-Type: application/json

{
  "type": "developer",
  "capabilities": ["python", "testing"]
}
```

### Response Format

All responses return JSON:

```json
{
  "data": { ... },
  "message": "Success",
  "timestamp": "2026-01-17T22:00:00Z"
}
```

---

## Authentication

**Status**: Not implemented in V2 (planned for future release)

Current Version:
- No authentication required
- All endpoints are publicly accessible
- Rate limiting: 100 requests/minute per IP

Future Version:
- JWT token authentication
- API key support
- Role-based access control (RBAC)

---

## Agent Management API

Manage platform agents through L01 (data) and L02 (runtime) services.

### List Agents

Get all agents with optional filtering.

**Endpoint**: `GET /l01/agents`

**Query Parameters**:
- `status` (optional): Filter by status (idle, running, paused, terminated, failed)
- `type` (optional): Filter by agent type (developer, researcher, qa, general)

**Example Request**:
```bash
curl "http://localhost:8009/l01/agents?status=running&type=developer"
```

**Example Response**:
```json
[
  {
    "agent_id": "agent_abc123",
    "type": "developer",
    "status": "running",
    "capabilities": ["python", "testing", "code-review"],
    "created_at": "2026-01-17T20:00:00Z",
    "updated_at": "2026-01-17T22:00:00Z",
    "resource_usage": {
      "cpu": 0.5,
      "memory": 512.0
    },
    "metadata": {
      "owner": "system",
      "priority": "normal"
    }
  }
]
```

### Get Agent

Retrieve a specific agent by ID.

**Endpoint**: `GET /l01/agents/{agent_id}`

**Example Request**:
```bash
curl "http://localhost:8009/l01/agents/agent_abc123"
```

**Example Response**:
```json
{
  "agent_id": "agent_abc123",
  "type": "developer",
  "status": "running",
  "capabilities": ["python", "testing"],
  "created_at": "2026-01-17T20:00:00Z",
  "updated_at": "2026-01-17T22:00:00Z",
  "resource_usage": {
    "cpu": 0.5,
    "memory": 512.0
  }
}
```

### Create Agent

Spawn a new agent on the platform.

**Endpoint**: `POST /l02/runtime/spawn`

**Request Body**:
```json
{
  "type": "developer",
  "capabilities": ["python", "testing", "code-review"],
  "resource_limits": {
    "cpu": "1.0",
    "memory": "2Gi"
  },
  "metadata": {
    "owner": "user123",
    "project": "story-portal"
  }
}
```

**Example Request**:
```bash
curl -X POST http://localhost:8009/l02/runtime/spawn \
  -H "Content-Type: application/json" \
  -d '{
    "type": "developer",
    "capabilities": ["python", "testing"],
    "resource_limits": {"cpu": "1.0", "memory": "2Gi"}
  }'
```

**Example Response**:
```json
{
  "agent_id": "agent_xyz789",
  "type": "developer",
  "status": "idle",
  "capabilities": ["python", "testing"],
  "created_at": "2026-01-17T22:15:00Z"
}
```

### Pause Agent

Suspend agent execution.

**Endpoint**: `POST /l10/control/pause`

**Request Body**:
```json
{
  "agent_id": "agent_abc123"
}
```

**Example Request**:
```bash
curl -X POST http://localhost:8009/l10/control/pause \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "agent_abc123"}'
```

**Example Response**:
```json
{
  "status": "success",
  "agent_id": "agent_abc123",
  "new_status": "paused"
}
```

### Resume Agent

Resume a paused agent.

**Endpoint**: `POST /l10/control/resume`

**Request Body**:
```json
{
  "agent_id": "agent_abc123"
}
```

**Example Request**:
```bash
curl -X POST http://localhost:8009/l10/control/resume \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "agent_abc123"}'
```

**Example Response**:
```json
{
  "status": "success",
  "agent_id": "agent_abc123",
  "new_status": "running"
}
```

### Terminate Agent

Permanently stop an agent.

**Endpoint**: `POST /l10/control/stop`

**Request Body**:
```json
{
  "agent_id": "agent_abc123"
}
```

**Example Request**:
```bash
curl -X POST http://localhost:8009/l10/control/stop \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "agent_abc123"}'
```

**Example Response**:
```json
{
  "status": "success",
  "agent_id": "agent_abc123",
  "new_status": "terminated"
}
```

---

## Service Discovery API

Discover and invoke platform services through L12 Service Hub.

### List Services

Get all available services.

**Endpoint**: `GET /v1/services`

**Query Parameters**:
- `layer` (optional): Filter by layer (L01, L02, ..., L12)

**Example Request**:
```bash
curl "http://localhost:8009/v1/services?layer=L01"
```

**Example Response**:
```json
[
  {
    "service_name": "AgentRegistry",
    "layer": "L01",
    "description": "Registry for agent metadata management",
    "keywords": ["agent", "registry", "metadata"],
    "module_path": "L01_data_layer.services.agent_registry",
    "class_name": "AgentRegistry",
    "methods": [
      {
        "name": "list_agents",
        "description": "List all agents with optional filtering",
        "parameters": {
          "status": "str (optional)",
          "type": "str (optional)"
        }
      }
    ]
  }
]
```

### Search Services

Fuzzy search for services by keywords.

**Endpoint**: `GET /v1/services/search`

**Query Parameters**:
- `q`: Search query (required)
- `threshold`: Match threshold 0.0-1.0 (default: 0.7)

**Example Request**:
```bash
curl "http://localhost:8009/v1/services/search?q=agent%20orchestration&threshold=0.7"
```

**Example Response**:
```json
[
  {
    "service_name": "AgentRegistry",
    "layer": "L01",
    "description": "Registry for agent metadata management",
    "keywords": ["agent", "registry"],
    "score": 0.85,
    "match_reason": "Matched keywords: agent"
  },
  {
    "service_name": "AgentRuntime",
    "layer": "L02",
    "description": "Agent execution runtime and lifecycle management",
    "keywords": ["agent", "runtime", "orchestration"],
    "score": 0.92,
    "match_reason": "Matched keywords: agent, orchestration"
  }
]
```

### Invoke Service

Execute a service method with parameters.

**Endpoint**: `POST /v1/services/invoke`

**Request Body**:
```json
{
  "service_name": "AgentRegistry",
  "method_name": "list_agents",
  "parameters": {
    "status": "running",
    "limit": 10
  },
  "session_id": "session_123" // optional
}
```

**Example Request**:
```bash
curl -X POST http://localhost:8009/v1/services/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "service_name": "AgentRegistry",
    "method_name": "list_agents",
    "parameters": {"status": "running"}
  }'
```

**Example Response**:
```json
{
  "result": [
    {"agent_id": "agent_abc123", "type": "developer", "status": "running"}
  ],
  "execution_time_ms": 45,
  "session_id": "session_456"
}
```

---

## Workflow API

Create and execute multi-step workflows.

### List Workflows

Get all defined workflows.

**Endpoint**: `GET /v1/workflows`

**Example Request**:
```bash
curl "http://localhost:8009/v1/workflows"
```

**Example Response**:
```json
[
  {
    "workflow_id": "testing.unit",
    "name": "Run Unit Tests",
    "description": "Execute unit test suite",
    "steps": [
      {
        "step_id": "step_1",
        "service_name": "TestRunner",
        "method_name": "run_tests",
        "parameters": {"path": "tests/unit/"},
        "depends_on": []
      }
    ],
    "created_at": "2026-01-17T20:00:00Z",
    "status": "active"
  }
]
```

### Get Workflow

Retrieve a specific workflow.

**Endpoint**: `GET /v1/workflows/{workflow_id}`

**Example Request**:
```bash
curl "http://localhost:8009/v1/workflows/testing.unit"
```

**Example Response**:
```json
{
  "workflow_id": "testing.unit",
  "name": "Run Unit Tests",
  "description": "Execute unit test suite",
  "steps": [
    {
      "step_id": "step_1",
      "service_name": "TestRunner",
      "method_name": "run_tests",
      "parameters": {"path": "tests/unit/"},
      "depends_on": []
    }
  ],
  "created_at": "2026-01-17T20:00:00Z",
  "status": "active"
}
```

### Create Workflow

Define a new workflow.

**Endpoint**: `POST /v1/workflows`

**Request Body**:
```json
{
  "workflow_id": "code.quality",
  "name": "Code Quality Check",
  "description": "Run linting and testing",
  "steps": [
    {
      "step_id": "lint",
      "service_name": "CodeLinter",
      "method_name": "lint",
      "parameters": {"path": "src/"},
      "depends_on": []
    },
    {
      "step_id": "test",
      "service_name": "TestRunner",
      "method_name": "run_all",
      "parameters": {"coverage": true},
      "depends_on": ["lint"]
    }
  ]
}
```

**Example Request**:
```bash
curl -X POST http://localhost:8009/v1/workflows \
  -H "Content-Type: application/json" \
  -d @workflow.json
```

**Example Response**:
```json
{
  "workflow_id": "code.quality",
  "name": "Code Quality Check",
  "created_at": "2026-01-17T22:00:00Z",
  "status": "active"
}
```

### Execute Workflow

Run a workflow with parameters.

**Endpoint**: `POST /v1/workflows/{workflow_id}/execute`

**Request Body**:
```json
{
  "test_path": "tests/unit/",
  "coverage_threshold": 80
}
```

**Example Request**:
```bash
curl -X POST http://localhost:8009/v1/workflows/testing.unit/execute \
  -H "Content-Type: application/json" \
  -d '{"test_path": "tests/unit/"}'
```

**Example Response**:
```json
{
  "execution_id": "exec_xyz789",
  "workflow_id": "testing.unit",
  "status": "running",
  "started_at": "2026-01-17T22:15:00Z"
}
```

### Get Workflow Execution

Check execution status and results.

**Endpoint**: `GET /v1/workflows/executions/{execution_id}`

**Example Request**:
```bash
curl "http://localhost:8009/v1/workflows/executions/exec_xyz789"
```

**Example Response**:
```json
{
  "execution_id": "exec_xyz789",
  "workflow_id": "testing.unit",
  "status": "completed",
  "started_at": "2026-01-17T22:15:00Z",
  "completed_at": "2026-01-17T22:16:30Z",
  "results": {
    "tests_passed": 45,
    "tests_failed": 2,
    "coverage": 87.5
  }
}
```

### List Workflow Executions

Get all workflow execution history.

**Endpoint**: `GET /v1/workflows/executions`

**Example Request**:
```bash
curl "http://localhost:8009/v1/workflows/executions"
```

**Example Response**:
```json
[
  {
    "execution_id": "exec_xyz789",
    "workflow_id": "testing.unit",
    "status": "completed",
    "started_at": "2026-01-17T22:15:00Z",
    "completed_at": "2026-01-17T22:16:30Z"
  }
]
```

---

## Goals & Planning API

Strategic planning with goals and execution plans.

### List Goals

Get all goals with optional filtering.

**Endpoint**: `GET /l01/goals`

**Query Parameters**:
- `status` (optional): Filter by status (pending, in_progress, completed, failed)

**Example Request**:
```bash
curl "http://localhost:8009/l01/goals?status=in_progress"
```

**Example Response**:
```json
[
  {
    "goal_id": "goal_abc123",
    "description": "Implement user authentication",
    "priority": "high",
    "status": "in_progress",
    "created_at": "2026-01-17T20:00:00Z",
    "constraints": {
      "deadline": "2026-01-31",
      "budget": 5000
    }
  }
]
```

### Create Goal

Define a new goal.

**Endpoint**: `POST /l01/goals`

**Request Body**:
```json
{
  "description": "Implement user authentication with OAuth 2.0",
  "priority": "high",
  "constraints": {
    "deadline": "2026-01-31",
    "technologies": ["FastAPI", "Auth0", "React"]
  }
}
```

**Example Request**:
```bash
curl -X POST http://localhost:8009/l01/goals \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Implement user authentication",
    "priority": "high"
  }'
```

**Example Response**:
```json
{
  "goal_id": "goal_xyz789",
  "description": "Implement user authentication",
  "priority": "high",
  "status": "pending",
  "created_at": "2026-01-17T22:00:00Z"
}
```

### Get Goal

Retrieve a specific goal.

**Endpoint**: `GET /l01/goals/{goal_id}`

**Example Request**:
```bash
curl "http://localhost:8009/l01/goals/goal_abc123"
```

**Example Response**:
```json
{
  "goal_id": "goal_abc123",
  "description": "Implement user authentication",
  "priority": "high",
  "status": "in_progress",
  "created_at": "2026-01-17T20:00:00Z"
}
```

### Create Plan

Generate execution plan for a goal.

**Endpoint**: `POST http://localhost:8005/plans`

**Request Body**:
```json
{
  "goal_id": "goal_abc123",
  "strategy": "Use Auth0 for OAuth 2.0 implementation",
  "tasks": [
    {
      "task_id": "task_1",
      "description": "Set up Auth0 account",
      "dependencies": []
    },
    {
      "task_id": "task_2",
      "description": "Integrate Auth0 SDK in backend",
      "dependencies": ["task_1"]
    },
    {
      "task_id": "task_3",
      "description": "Add login UI to frontend",
      "dependencies": ["task_2"]
    }
  ]
}
```

**Example Request**:
```bash
curl -X POST http://localhost:8005/plans \
  -H "Content-Type: application/json" \
  -d @plan.json
```

**Example Response**:
```json
{
  "plan_id": "plan_xyz789",
  "goal_id": "goal_abc123",
  "strategy": "Use Auth0 for OAuth 2.0 implementation",
  "tasks": [ ... ],
  "status": "draft",
  "created_at": "2026-01-17T22:00:00Z"
}
```

### List Plans

Get all plans for a goal.

**Endpoint**: `GET /l01/plans`

**Query Parameters**:
- `goal_id` (optional): Filter by goal ID

**Example Request**:
```bash
curl "http://localhost:8009/l01/plans?goal_id=goal_abc123"
```

**Example Response**:
```json
[
  {
    "plan_id": "plan_xyz789",
    "goal_id": "goal_abc123",
    "strategy": "Use Auth0 for OAuth 2.0",
    "tasks": [ ... ],
    "status": "executing",
    "created_at": "2026-01-17T22:00:00Z"
  }
]
```

---

## Events API

Query platform events and activity logs.

### List Events

Get events with pagination.

**Endpoint**: `GET /l01/events`

**Query Parameters**:
- `limit` (optional): Number of events (default: 100, max: 1000)
- `offset` (optional): Pagination offset (default: 0)

**Example Request**:
```bash
curl "http://localhost:8009/l01/events?limit=50&offset=0"
```

**Example Response**:
```json
[
  {
    "event_id": "evt_abc123",
    "event_type": "agent.started",
    "payload": {
      "agent_id": "agent_abc123",
      "type": "developer"
    },
    "timestamp": "2026-01-17T22:00:00Z",
    "source": "L02_runtime",
    "severity": "info"
  },
  {
    "event_id": "evt_def456",
    "event_type": "workflow.completed",
    "payload": {
      "execution_id": "exec_xyz789",
      "workflow_id": "testing.unit",
      "duration_ms": 45000
    },
    "timestamp": "2026-01-17T22:01:30Z",
    "source": "L12_service_hub",
    "severity": "info"
  }
]
```

---

## Context Management API

Manage execution contexts and variables.

### List Contexts

Get all contexts.

**Endpoint**: `GET /l01/contexts`

**Example Request**:
```bash
curl "http://localhost:8009/l01/contexts"
```

**Example Response**:
```json
[
  {
    "context_id": "ctx_abc123",
    "name": "production_env",
    "variables": {
      "DATABASE_URL": "postgresql://...",
      "API_KEY": "***"
    },
    "created_at": "2026-01-17T20:00:00Z",
    "updated_at": "2026-01-17T22:00:00Z"
  }
]
```

### Create Context

Define a new execution context.

**Endpoint**: `POST /l01/contexts`

**Request Body**:
```json
{
  "name": "staging_env",
  "variables": {
    "DATABASE_URL": "postgresql://staging.db",
    "DEBUG": true
  }
}
```

**Example Request**:
```bash
curl -X POST http://localhost:8009/l01/contexts \
  -H "Content-Type: application/json" \
  -d '{"name": "staging_env", "variables": {"DEBUG": true}}'
```

**Example Response**:
```json
{
  "context_id": "ctx_xyz789",
  "name": "staging_env",
  "variables": {"DEBUG": true},
  "created_at": "2026-01-17T22:00:00Z"
}
```

### Update Context

Modify context variables.

**Endpoint**: `PATCH /l01/contexts/{context_id}`

**Request Body**:
```json
{
  "variables": {
    "DEBUG": false,
    "LOG_LEVEL": "info"
  }
}
```

**Example Request**:
```bash
curl -X PATCH http://localhost:8009/l01/contexts/ctx_abc123 \
  -H "Content-Type: application/json" \
  -d '{"variables": {"DEBUG": false}}'
```

**Example Response**:
```json
{
  "context_id": "ctx_abc123",
  "name": "staging_env",
  "variables": {
    "DEBUG": false,
    "LOG_LEVEL": "info"
  },
  "updated_at": "2026-01-17T22:15:00Z"
}
```

### Delete Context

Remove a context.

**Endpoint**: `DELETE /l01/contexts/{context_id}`

**Example Request**:
```bash
curl -X DELETE http://localhost:8009/l01/contexts/ctx_abc123
```

**Example Response**:
```json
{
  "status": "success",
  "context_id": "ctx_abc123",
  "deleted_at": "2026-01-17T22:15:00Z"
}
```

---

## Metrics & Health API

Monitor system health and performance.

### Get System Metrics

Retrieve current system metrics.

**Endpoint**: `GET /l10/metrics`

**Example Request**:
```bash
curl "http://localhost:8009/l10/metrics"
```

**Example Response**:
```json
{
  "agents": {
    "total": 15,
    "active": 8,
    "idle": 5,
    "failed": 2
  },
  "resources": {
    "cpu_usage": 45.2,
    "memory_usage": 68.5,
    "total_memory": 16384
  },
  "requests": {
    "total": 15420,
    "success_rate": 0.987,
    "avg_response_time_ms": 125
  }
}
```

### Check Health

Get overall platform health status.

**Endpoint**: `GET /health`

**Example Request**:
```bash
curl "http://localhost:8009/health"
```

**Example Response**:
```json
{
  "status": "healthy",
  "services": [
    {
      "name": "L01 Data Layer",
      "status": "healthy",
      "url": "http://l01-data-layer:8001",
      "response_time_ms": 12
    },
    {
      "name": "L02 Runtime",
      "status": "healthy",
      "url": "http://l02-runtime:8002",
      "response_time_ms": 34
    }
  ],
  "timestamp": "2026-01-17T22:00:00Z"
}
```

---

## WebSocket API

Real-time event streaming via WebSocket.

### Connection

**Endpoint**: `ws://localhost:8010/ws/`

**Protocol**: Socket.IO

**Example Client (JavaScript)**:
```javascript
import io from 'socket.io-client'

const socket = io('ws://localhost:8010', {
  transports: ['websocket'],
  reconnection: true,
  reconnectionAttempts: 5,
  reconnectionDelay: 1000,
})

socket.on('connect', () => {
  console.log('Connected to platform')
})

socket.on('event', (data) => {
  console.log('Event:', data)
  // data = {
  //   event_id: "evt_abc123",
  //   event_type: "agent.started",
  //   payload: {...},
  //   timestamp: "2026-01-17T22:00:00Z",
  //   source: "L02_runtime"
  // }
})

socket.on('disconnect', () => {
  console.log('Disconnected from platform')
})
```

### Event Types

**Agent Events**:
- `agent.created`
- `agent.started`
- `agent.paused`
- `agent.resumed`
- `agent.terminated`
- `agent.failed`

**Workflow Events**:
- `workflow.created`
- `workflow.started`
- `workflow.step_completed`
- `workflow.completed`
- `workflow.failed`

**System Events**:
- `system.health_degraded`
- `system.health_recovered`
- `system.resource_alert`
- `system.error`

---

## Error Handling

### Error Response Format

All errors return JSON with standard format:

```json
{
  "error": "Agent not found",
  "code": "AGENT_NOT_FOUND",
  "details": {
    "agent_id": "agent_invalid"
  },
  "timestamp": "2026-01-17T22:00:00Z"
}
```

### HTTP Status Codes

- `200 OK` - Request succeeded
- `201 Created` - Resource created
- `400 Bad Request` - Invalid request parameters
- `404 Not Found` - Resource not found
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error
- `502 Bad Gateway` - Backend service unavailable
- `503 Service Unavailable` - Service temporarily unavailable

### Common Error Codes

**Agent Errors**:
- `AGENT_NOT_FOUND` - Agent ID does not exist
- `AGENT_ALREADY_PAUSED` - Cannot pause already paused agent
- `AGENT_ALREADY_TERMINATED` - Cannot operate on terminated agent
- `AGENT_RESOURCE_LIMIT_EXCEEDED` - Resource limits exceeded

**Service Errors**:
- `SERVICE_NOT_FOUND` - Service name does not exist
- `METHOD_NOT_FOUND` - Method name not available on service
- `INVALID_PARAMETERS` - Parameters do not match method signature
- `INVOCATION_FAILED` - Service invocation failed

**Workflow Errors**:
- `WORKFLOW_NOT_FOUND` - Workflow ID does not exist
- `EXECUTION_FAILED` - Workflow execution failed
- `INVALID_WORKFLOW_DEFINITION` - Workflow steps have errors

**General Errors**:
- `VALIDATION_ERROR` - Request validation failed
- `TIMEOUT` - Request timed out
- `RATE_LIMIT_EXCEEDED` - Too many requests

---

## Rate Limiting

**Current Limits**:
- 100 requests/minute per IP
- 1000 requests/hour per IP
- 10,000 requests/day per IP

**Rate Limit Headers**:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1705529400
```

**Rate Limit Exceeded Response**:
```json
{
  "error": "Rate limit exceeded",
  "code": "RATE_LIMIT_EXCEEDED",
  "details": {
    "limit": 100,
    "window": "1 minute",
    "reset_at": "2026-01-17T22:01:00Z"
  }
}
```

---

## API Versioning

The API uses URL-based versioning:
- `/v1/...` - Version 1 (current)
- `/v2/...` - Version 2 (future)

Breaking changes will introduce new versions. Old versions supported for 6 months after new version release.

---

**Last Updated**: January 17, 2026
**API Version**: 1.0.0
**Document Version**: 1.0.0

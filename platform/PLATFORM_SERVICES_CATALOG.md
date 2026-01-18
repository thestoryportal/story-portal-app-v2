# Platform Services Catalog

**Last Updated**: January 17, 2026
**Version**: V2
**Total Services**: 44 across 9 layers

## Overview

This catalog documents all services available in the Agentic Platform V2. Services are organized by layer (L01-L11) and provide comprehensive functionality for agent orchestration, data management, planning, evaluation, learning, and system integration.

### Access Methods

Services can be accessed through multiple interfaces:
- **HTTP REST API**: Via L09 API Gateway (`http://localhost:8009/{layer}/{service}`)
- **L12 Service Hub**: Natural language interface (`http://localhost:8012/v1/services/{ServiceName}`)
- **Direct Layer Access**: Internal service-to-service calls
- **WebSocket**: Real-time event streaming via L10 (`ws://localhost:8010`)

---

## L01: Data Layer (12 services)

**Purpose**: Persistent storage, event sourcing, and data management
**Port**: 8001
**Base URL**: `http://localhost:8001`

### AgentRegistry
**Description**: Registry for agent metadata management and lifecycle tracking

**Key Methods**:
- `register_agent(agent_id, metadata)` - Register new agent
- `get_agent(agent_id)` - Retrieve agent metadata
- `list_agents(filters)` - List agents with filtering
- `update_agent_status(agent_id, status)` - Update agent status
- `deregister_agent(agent_id)` - Remove agent from registry

**Endpoints**:
- `POST /agents` - Register agent
- `GET /agents/{agent_id}` - Get agent details
- `GET /agents` - List all agents
- `PATCH /agents/{agent_id}` - Update agent
- `DELETE /agents/{agent_id}` - Deregister agent

**Usage Example**:
```bash
curl -X POST http://localhost:8001/agents \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent-123",
    "type": "developer",
    "capabilities": ["code_generation", "testing"]
  }'
```

---

### ConfigStore
**Description**: Configuration key-value store with versioning support

**Key Methods**:
- `set_config(key, value, version)` - Set configuration value
- `get_config(key)` - Retrieve configuration
- `list_configs(namespace)` - List configurations by namespace
- `delete_config(key)` - Remove configuration

**Endpoints**:
- `POST /config` - Set configuration
- `GET /config/{key}` - Get configuration
- `GET /configs` - List all configurations
- `DELETE /config/{key}` - Delete configuration

**Usage Example**:
```bash
curl -X POST http://localhost:8001/config \
  -H "Content-Type: application/json" \
  -d '{"key": "llm.default_model", "value": "claude-3-sonnet", "version": 1}'
```

---

### DatasetService
**Description**: Training dataset CRUD operations and split management

**Key Methods**:
- `create_dataset(name, description)` - Create new dataset
- `add_examples(dataset_id, examples)` - Add training examples
- `split_dataset(dataset_id, train_ratio, val_ratio)` - Split into train/val/test
- `get_dataset(dataset_id)` - Retrieve dataset metadata

**Endpoints**:
- `POST /datasets` - Create dataset
- `POST /datasets/{id}/examples` - Add examples
- `POST /datasets/{id}/split` - Split dataset
- `GET /datasets/{id}` - Get dataset

---

### DocumentStore
**Description**: Document persistence and retrieval service

**Key Methods**:
- `store_document(doc_id, content, metadata)` - Store document
- `retrieve_document(doc_id)` - Retrieve document
- `search_documents(query, filters)` - Search with filtering
- `delete_document(doc_id)` - Delete document

**Endpoints**:
- `POST /documents` - Store document
- `GET /documents/{id}` - Retrieve document
- `GET /documents/search` - Search documents
- `DELETE /documents/{id}` - Delete document

---

### EventStore
**Description**: Event sourcing store for audit trails and replay

**Key Methods**:
- `emit_event(event_type, payload)` - Emit new event
- `get_events(filters)` - Query events with filtering
- `replay_events(from_timestamp, to_timestamp)` - Replay event stream
- `subscribe_to_events(event_types, callback)` - Subscribe to event stream

**Endpoints**:
- `POST /events` - Emit event
- `GET /events` - Query events
- `POST /events/replay` - Replay events
- `WS /events/stream` - WebSocket event stream

**Usage Example**:
```bash
curl -X POST http://localhost:8001/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "agent.spawned",
    "payload": {"agent_id": "agent-123", "timestamp": "2026-01-17T21:00:00Z"}
  }'
```

---

### EvaluationStore
**Description**: Evaluation results storage and analysis

**Key Methods**:
- `store_evaluation(eval_id, results)` - Store evaluation results
- `get_evaluation(eval_id)` - Retrieve evaluation
- `aggregate_evaluations(filters)` - Aggregate metrics

---

### FeedbackStore
**Description**: Feedback and correction storage for learning

**Key Methods**:
- `store_feedback(feedback_id, content)` - Store feedback
- `get_feedback(feedback_id)` - Retrieve feedback
- `query_feedback(filters)` - Query feedback with filters

---

### GoalStore
**Description**: Goal and objective persistence service

**Key Methods**:
- `create_goal(description, constraints)` - Create new goal
- `get_goal(goal_id)` - Retrieve goal
- `update_goal_status(goal_id, status)` - Update goal status
- `list_goals(filters)` - List goals with filtering

---

### PlanStore
**Description**: Execution plan storage and retrieval

**Key Methods**:
- `store_plan(plan_id, tasks)` - Store execution plan
- `get_plan(plan_id)` - Retrieve plan
- `update_plan_progress(plan_id, task_id, status)` - Update task status

---

### SessionService
**Description**: Session lifecycle management and tracking

**Key Methods**:
- `create_session(session_id, metadata)` - Create new session
- `get_session(session_id)` - Retrieve session
- `update_session(session_id, data)` - Update session data
- `end_session(session_id)` - Terminate session

---

### ToolRegistry
**Description**: Tool definition and metadata registry

**Key Methods**:
- `register_tool(tool_name, definition)` - Register new tool
- `get_tool(tool_name)` - Retrieve tool definition
- `list_tools(category)` - List tools by category
- `search_tools(query)` - Search tools

---

### TrainingExampleService
**Description**: Training example CRUD operations and management

**Key Methods**:
- `add_example(example_data)` - Add training example
- `get_example(example_id)` - Retrieve example
- `query_examples(filters)` - Query examples with filters

---

## L02: Agent Runtime (7 services)

**Purpose**: Agent lifecycle management, execution, and resource control
**Port**: 8002
**Base URL**: `http://localhost:8002`

### AgentExecutor
**Description**: Code execution engine with tool support and sandboxing

**Key Methods**:
- `execute_code(agent_id, code, context)` - Execute agent code
- `invoke_tool(tool_name, parameters)` - Invoke tool from agent
- `get_execution_result(execution_id)` - Get execution result

**Endpoints**:
- `POST /execute` - Execute code
- `POST /tools/invoke` - Invoke tool
- `GET /executions/{id}` - Get execution result

---

### FleetManager
**Description**: Agent fleet scaling orchestration and autoscaling

**Key Methods**:
- `scale_fleet(target_count)` - Scale agent fleet
- `get_fleet_status()` - Get current fleet status
- `configure_autoscaling(policy)` - Configure autoscaling policy

**Endpoints**:
- `POST /fleet/scale` - Scale fleet
- `GET /fleet/status` - Get fleet status
- `POST /fleet/autoscaling` - Configure autoscaling

---

### LifecycleManager
**Description**: Agent spawn, terminate, and recovery management

**Key Methods**:
- `spawn_agent(config)` - Spawn new agent
- `terminate_agent(agent_id)` - Terminate agent
- `pause_agent(agent_id)` - Pause agent execution
- `resume_agent(agent_id)` - Resume paused agent
- `recover_agent(agent_id)` - Recover failed agent

**Endpoints**:
- `POST /runtime/spawn` - Spawn agent
- `DELETE /runtime/{agent_id}` - Terminate agent
- `POST /runtime/{agent_id}/pause` - Pause agent
- `POST /runtime/{agent_id}/resume` - Resume agent
- `POST /runtime/{agent_id}/recover` - Recover agent

**Usage Example**:
```bash
curl -X POST http://localhost:8002/runtime/spawn \
  -H "Content-Type: application/json" \
  -d '{
    "type": "developer",
    "capabilities": ["python", "testing"],
    "resource_limits": {"cpu": "1.0", "memory": "2Gi"}
  }'
```

---

### ResourceManager
**Description**: CPU and memory quota enforcement with monitoring

**Key Methods**:
- `allocate_resources(agent_id, limits)` - Allocate resources
- `monitor_usage(agent_id)` - Monitor resource usage
- `adjust_quota(agent_id, new_limits)` - Adjust resource quota

---

### SandboxManager
**Description**: Runtime sandbox configuration and isolation

**Key Methods**:
- `create_sandbox(agent_id, config)` - Create execution sandbox
- `destroy_sandbox(sandbox_id)` - Destroy sandbox
- `get_sandbox_status(sandbox_id)` - Get sandbox status

---

### StateManager
**Description**: Checkpoint and recovery state management

**Key Methods**:
- `save_checkpoint(agent_id, state)` - Save agent state checkpoint
- `load_checkpoint(agent_id, checkpoint_id)` - Load checkpoint
- `list_checkpoints(agent_id)` - List available checkpoints

---

### WorkflowEngine
**Description**: Graph-based workflow execution engine

**Key Methods**:
- `execute_workflow(workflow_def, inputs)` - Execute workflow
- `get_workflow_status(execution_id)` - Get workflow status
- `pause_workflow(execution_id)` - Pause workflow
- `resume_workflow(execution_id)` - Resume workflow

---

## L03: Tool Execution (2 services)

**Purpose**: Secure tool invocation with composition and caching
**Port**: 8003
**Base URL**: `http://localhost:8003`

### ToolComposer
**Description**: Multi-tool workflow composition and chaining

**Key Methods**:
- `compose_workflow(tool_chain)` - Compose multi-tool workflow
- `execute_composed(workflow_id, inputs)` - Execute composed workflow

---

### ToolExecutor
**Description**: Sandboxed tool execution engine with result caching

**Key Methods**:
- `execute_tool(tool_name, parameters)` - Execute tool
- `get_cached_result(cache_key)` - Get cached result
- `list_available_tools()` - List all available tools

**Endpoints**:
- `POST /tools/execute` - Execute tool
- `GET /tools/cache/{key}` - Get cached result
- `GET /tools` - List available tools

---

## L04: Model Gateway (3 services)

**Purpose**: LLM routing, caching, and model management
**Port**: 8004
**Base URL**: `http://localhost:8004`

### ModelGateway
**Description**: Main LLM gateway orchestrator with routing and caching

**Key Methods**:
- `generate(prompt, model, parameters)` - Generate completion
- `embed(text)` - Generate embeddings
- `get_models()` - List available models

**Endpoints**:
- `POST /generate` - Generate completion
- `POST /embed` - Generate embeddings
- `GET /models` - List models

---

### LLMRouter
**Description**: Capability-aware model routing and selection

**Key Methods**:
- `route_request(request_spec)` - Route to appropriate model
- `get_capabilities(model_name)` - Get model capabilities

---

### SemanticCache
**Description**: Embedding-based LLM result caching

**Key Methods**:
- `cache_result(key, result)` - Cache LLM result
- `get_similar(query_embedding, threshold)` - Get similar cached results

---

## L05: Planning (4 services)

**Purpose**: Strategic planning, goal decomposition, and task orchestration
**Port**: 8005
**Base URL**: `http://localhost:8005`

### PlanningService
**Description**: Strategic planning coordinator for goal decomposition and execution

**Key Methods**:
- `create_plan(goal, constraints)` - Create execution plan
- `refine_plan(plan_id, feedback)` - Refine existing plan
- `execute_plan(plan_id)` - Execute plan

**Endpoints**:
- `POST /plans` - Create plan
- `PATCH /plans/{id}` - Refine plan
- `POST /plans/{id}/execute` - Execute plan

---

### GoalDecomposer
**Description**: Goal-to-plan decomposition using cache, templates, and LLM

**Key Methods**:
- `decompose_goal(goal_description)` - Decompose goal into tasks
- `validate_decomposition(plan)` - Validate task decomposition

---

### TaskOrchestrator
**Description**: Parallel task execution and coordination

**Key Methods**:
- `execute_tasks(tasks, execution_mode)` - Execute tasks (serial/parallel)
- `get_task_status(task_id)` - Get task execution status
- `cancel_task(task_id)` - Cancel running task

---

### AgentAssigner
**Description**: Task-to-agent assignment engine with capability matching

**Key Methods**:
- `assign_task(task, agent_pool)` - Assign task to capable agent
- `reassign_task(task_id, new_agent_id)` - Reassign task to different agent

---

## L06: Evaluation (3 services)

**Purpose**: Quality assessment, metrics, and monitoring
**Port**: 8006
**Base URL**: `http://localhost:8006`

### EvaluationService
**Description**: Quality assessment and metrics aggregation orchestrator

**Key Methods**:
- `evaluate(artifact, criteria)` - Evaluate artifact quality
- `aggregate_metrics(eval_ids)` - Aggregate evaluation metrics

---

### MetricsEngine
**Description**: Time-windowed statistics aggregation engine

**Key Methods**:
- `record_metric(metric_name, value, labels)` - Record metric
- `query_metrics(metric_name, time_range)` - Query metrics

---

### AlertManager
**Description**: Multi-channel alert routing and delivery

**Key Methods**:
- `send_alert(alert_type, message, channels)` - Send alert
- `acknowledge_alert(alert_id)` - Acknowledge alert

---

## L07: Learning (3 services)

**Purpose**: Model training, fine-tuning, and continuous learning
**Port**: 8007
**Base URL**: `http://localhost:8007`

### LearningService
**Description**: Model training and optimization orchestrator

**Key Methods**:
- `train_model(dataset_id, config)` - Train model
- `get_training_status(job_id)` - Get training status

---

### FineTuningEngine
**Description**: LoRA-based supervised fine-tuning engine

**Key Methods**:
- `finetune(base_model, dataset_id, config)` - Fine-tune model
- `evaluate_finetuned(model_id, test_dataset)` - Evaluate fine-tuned model

---

### DatasetCurator
**Description**: Training dataset curation and quality filtering

**Key Methods**:
- `curate_dataset(raw_data, quality_criteria)` - Curate dataset
- `filter_low_quality(dataset_id, threshold)` - Filter low-quality examples

---

## L09: API Gateway (3 services)

**Purpose**: Authentication, authorization, and request routing
**Port**: 8009
**Base URL**: `http://localhost:8009`

### AuthenticationHandler
**Description**: Multi-method authentication (API key, OAuth 2.0, SAML)

**Key Methods**:
- `authenticate(credentials)` - Authenticate user
- `validate_token(token)` - Validate authentication token
- `revoke_token(token)` - Revoke authentication token

---

### AuthorizationEngine
**Description**: RBAC and ABAC authorization enforcement

**Key Methods**:
- `authorize(user, resource, action)` - Check authorization
- `grant_permission(user, resource, action)` - Grant permission
- `revoke_permission(user, resource, action)` - Revoke permission

---

### RequestRouter
**Description**: Glob-pattern path routing to backend services

**Key Methods**:
- `route_request(request)` - Route request to backend
- `add_route(pattern, backend)` - Add routing rule
- `remove_route(pattern)` - Remove routing rule

---

## L10: Human Interface (3 services)

**Purpose**: Web dashboard, control interfaces, and real-time updates
**Port**: 8010
**Base URL**: `http://localhost:8010`

### DashboardService
**Description**: Real-time system state aggregation for web dashboard

**Key Methods**:
- `get_system_overview()` - Get system overview
- `get_agent_metrics()` - Get agent metrics
- `get_resource_usage()` - Get resource usage

**Endpoints**:
- `GET /dashboard/overview` - System overview
- `GET /dashboard/agents` - Agent metrics
- `GET /dashboard/resources` - Resource usage

---

### ControlService
**Description**: Agent operation controls (start, stop, pause, resume)

**Key Methods**:
- `start_agent(agent_id)` - Start agent
- `stop_agent(agent_id)` - Stop agent
- `pause_agent(agent_id)` - Pause agent
- `resume_agent(agent_id)` - Resume agent

**Endpoints**:
- `POST /control/start` - Start agent
- `POST /control/stop` - Stop agent
- `POST /control/pause` - Pause agent
- `POST /control/resume` - Resume agent

---

### WebSocketGateway
**Description**: Real-time client updates via WebSocket connections

**Key Methods**:
- `connect(client_id)` - Establish WebSocket connection
- `broadcast(event)` - Broadcast event to all clients
- `send_to_client(client_id, message)` - Send message to specific client

**Endpoints**:
- `WS /ws` - WebSocket endpoint

---

## L11: Integration (4 services)

**Purpose**: Cross-layer orchestration, event bus, and service discovery
**Port**: 8011
**Base URL**: `http://localhost:8011`

### SagaOrchestrator
**Description**: Multi-step saga orchestration with compensation

**Key Methods**:
- `execute_saga(saga_definition)` - Execute saga
- `compensate(saga_id)` - Execute compensation logic
- `get_saga_status(saga_id)` - Get saga execution status

---

### RequestOrchestrator
**Description**: Cross-layer request routing and orchestration

**Key Methods**:
- `orchestrate_request(request)` - Orchestrate cross-layer request
- `get_orchestration_status(request_id)` - Get orchestration status

---

### EventBusManager
**Description**: Redis Pub/Sub event broker for cross-layer communication

**Key Methods**:
- `publish(topic, message)` - Publish message to topic
- `subscribe(topic, callback)` - Subscribe to topic
- `unsubscribe(topic, callback)` - Unsubscribe from topic

---

### ServiceRegistry
**Description**: Layer service discovery and health tracking

**Key Methods**:
- `register_service(service_name, endpoint)` - Register service
- `discover_service(service_name)` - Discover service endpoint
- `health_check(service_name)` - Check service health

---

## Service Categories

Services are categorized by functional purpose:

1. **Data & Storage** (12): L01 services for persistence
2. **Agent Runtime** (7): L02 services for agent lifecycle
3. **Tool Management** (2): L03 services for tool execution
4. **Model Management** (3): L04 services for LLM access
5. **Planning & Orchestration** (4): L05 services for strategic planning
6. **Quality & Monitoring** (3): L06 services for evaluation
7. **Learning & Training** (3): L07 services for model improvement
8. **Gateway & Auth** (3): L09 services for security and routing
9. **Human Interface** (3): L10 services for dashboards and control
10. **Integration** (4): L11 services for cross-layer coordination

---

## Usage Patterns

### Creating an Agent Workflow

```bash
# 1. Create goal in L01
curl -X POST http://localhost:8001/goals \
  -d '{"description": "Build user authentication feature"}'

# 2. Decompose goal into plan (L05)
curl -X POST http://localhost:8005/plans \
  -d '{"goal_id": "goal-123"}'

# 3. Spawn agent (L02)
curl -X POST http://localhost:8002/runtime/spawn \
  -d '{"type": "developer", "capabilities": ["python"]}'

# 4. Execute tasks
curl -X POST http://localhost:8005/tasks/execute \
  -d '{"plan_id": "plan-456", "agent_id": "agent-789"}'

# 5. Monitor via dashboard (L10)
curl http://localhost:8010/dashboard/agents/agent-789
```

### Invoking Tools

```bash
# Direct tool execution (L03)
curl -X POST http://localhost:8003/tools/execute \
  -d '{"tool_name": "bash", "parameters": {"command": "ls -la"}}'

# Via service hub (L12)
curl -X POST http://localhost:8012/v1/services/invoke \
  -d '{
    "service_name": "ToolExecutor",
    "method_name": "execute_tool",
    "parameters": {"tool_name": "bash", "parameters": {"command": "pwd"}}
  }'
```

### Real-Time Monitoring

```javascript
// Connect to WebSocket (L10)
const ws = new WebSocket('ws://localhost:8010/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data.event_type, data.payload);
};

// Subscribe to agent events
ws.send(JSON.stringify({
  action: 'subscribe',
  topics: ['agent.spawned', 'agent.terminated', 'task.completed']
}));
```

---

## See Also

- **L12 Service Hub Documentation**: `platform/src/L12_nl_interface/README.md`
- **API Reference**: OpenAPI specs in each layer's `docs/` directory
- **User Guide**: `platform/docs/USER_GUIDE.md`
- **Architecture**: `platform/docs/ARCHITECTURE.md`

---

**Last Updated**: January 17, 2026

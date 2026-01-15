Implement L01 Data Layer and integrate with all deployed layers.

ENVIRONMENT CONSTRAINTS

Working directory: /Volumes/Extreme SSD/projects/story-portal-app/platform
PostgreSQL: localhost:5432
Redis: localhost:6379
Ollama: localhost:11434
MCP Services: PM2 managed (DO NOT MODIFY)
DO NOT create docker-compose or venv
Use: pip3 install package --break-system-packages

DEPLOYED LAYERS REQUIRING INTEGRATION

L02 Agent Runtime
L03 Tool Execution
L04 Model Gateway
L05 Planning
L06 Evaluation
L07 Learning
L09 API Gateway
L10 Human Interface
L11 Integration

PROTECTED SERVICES - DO NOT MODIFY

MCP Context Orchestrator (PM2)
MCP Document Consolidator (PM2)

These MCP services use stdio transport. L01 should provide data services they can optionally consume, not replace them.

SPECIFICATION REFERENCE

Read: /mnt/project/agentic-data-layer-master-specification-v4_0-final-ASCII.md

PART 1: L01 DATA LAYER IMPLEMENTATION

Create: src/L01_data_layer/

Structure:

L01_data_layer/
    __init__.py
    main.py
    database.py
    redis_client.py
    models/
        __init__.py
        event.py
        agent.py
        config.py
        document.py
        session.py
        tool.py
        goal.py
        plan.py
        evaluation.py
        feedback.py
        error_codes.py
    services/
        __init__.py
        event_store.py
        agent_registry.py
        config_store.py
        document_store.py
        session_service.py
        tool_registry.py
        goal_store.py
        plan_store.py
        evaluation_store.py
        feedback_store.py
    routers/
        __init__.py
        health.py
        events.py
        agents.py
        config.py
        documents.py
        sessions.py
        tools.py
        goals.py
        plans.py
        evaluations.py
        feedback.py

Database Schema:

-- Core event sourcing
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(255) NOT NULL,
    aggregate_type VARCHAR(100) NOT NULL,
    aggregate_id UUID NOT NULL,
    payload JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    version INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_events_aggregate ON events(aggregate_type, aggregate_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);

-- L02 Agent Runtime
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    did VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    agent_type VARCHAR(100) DEFAULT 'general',
    status VARCHAR(50) DEFAULT 'created',
    configuration JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    resource_limits JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- L03 Tool Execution
CREATE TABLE IF NOT EXISTS tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    tool_type VARCHAR(100) DEFAULT 'function',
    schema_def JSONB NOT NULL,
    permissions JSONB DEFAULT '{}',
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tool_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id UUID REFERENCES tools(id),
    agent_id UUID REFERENCES agents(id),
    input_params JSONB,
    output_result JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- L04 Model Gateway
CREATE TABLE IF NOT EXISTS model_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id),
    model_provider VARCHAR(100) NOT NULL,
    model_name VARCHAR(255) NOT NULL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    latency_ms INTEGER,
    cost_estimate DECIMAL(10,6),
    created_at TIMESTAMP DEFAULT NOW()
);

-- L05 Planning
CREATE TABLE IF NOT EXISTS goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id),
    description TEXT NOT NULL,
    success_criteria JSONB DEFAULT '[]',
    status VARCHAR(50) DEFAULT 'pending',
    priority INTEGER DEFAULT 5,
    parent_goal_id UUID REFERENCES goals(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID REFERENCES goals(id),
    agent_id UUID REFERENCES agents(id),
    plan_type VARCHAR(100) DEFAULT 'sequential',
    steps JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'draft',
    current_step INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID REFERENCES plans(id),
    agent_id UUID REFERENCES agents(id),
    description TEXT NOT NULL,
    task_type VARCHAR(100),
    input_data JSONB DEFAULT '{}',
    output_data JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    sequence_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- L06 Evaluation
CREATE TABLE IF NOT EXISTS evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id),
    task_id UUID REFERENCES tasks(id),
    evaluation_type VARCHAR(100) NOT NULL,
    score DECIMAL(5,4),
    metrics JSONB DEFAULT '{}',
    feedback TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- L07 Learning
CREATE TABLE IF NOT EXISTS feedback_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id),
    task_id UUID REFERENCES tasks(id),
    feedback_type VARCHAR(100) NOT NULL,
    rating INTEGER,
    content TEXT,
    metadata JSONB DEFAULT '{}',
    processed BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Configuration store
CREATE TABLE IF NOT EXISTS configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    namespace VARCHAR(100) NOT NULL,
    key VARCHAR(255) NOT NULL,
    value JSONB NOT NULL,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(namespace, key)
);

-- Documents (Phase 15)
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    content TEXT,
    content_type VARCHAR(100) DEFAULT 'text/plain',
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Sessions (Phase 16)
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id),
    session_type VARCHAR(100) DEFAULT 'conversation',
    status VARCHAR(50) DEFAULT 'active',
    context JSONB DEFAULT '{}',
    checkpoint JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

L01 API Endpoints:

Health:
GET /health/live
GET /health/ready

Events:
POST /events
GET /events
GET /events/{id}

Agents (L02):
GET /agents
GET /agents/{id}
POST /agents
PATCH /agents/{id}
DELETE /agents/{id}

Tools (L03):
GET /tools
GET /tools/{id}
POST /tools
PATCH /tools/{id}
POST /tool-executions
GET /tool-executions/{id}

Model Usage (L04):
POST /model-usage
GET /model-usage
GET /model-usage/stats

Goals (L05):
GET /goals
GET /goals/{id}
POST /goals
PATCH /goals/{id}

Plans (L05):
GET /plans
GET /plans/{id}
POST /plans
PATCH /plans/{id}

Tasks (L05):
GET /tasks
GET /tasks/{id}
POST /tasks
PATCH /tasks/{id}

Evaluations (L06):
GET /evaluations
GET /evaluations/{id}
POST /evaluations
GET /evaluations/agent/{agent_id}/stats

Feedback (L07):
GET /feedback
GET /feedback/{id}
POST /feedback
GET /feedback/unprocessed

Config:
GET /config/{namespace}/{key}
PUT /config/{namespace}/{key}
GET /config/{namespace}

Documents:
GET /documents
GET /documents/{id}
POST /documents
PATCH /documents/{id}
DELETE /documents/{id}

Sessions:
GET /sessions
GET /sessions/{id}
POST /sessions
PATCH /sessions/{id}

Event Publishing:

On every write operation, publish to Redis:
Channel: l01:events
Payload: {"event_type": "...", "aggregate_type": "...", "aggregate_id": "...", "payload": {...}}

Error Codes: E1000-E1999

PART 2: CREATE L01 CLIENT LIBRARY

Create: src/L01_data_layer/client.py

Shared client for all layers to import:

class L01Client:
    def __init__(self, base_url="http://localhost:8002"):
        self.base_url = base_url
    
    # Agent methods
    async def create_agent(self, name, agent_type, config) -> dict
    async def get_agent(self, agent_id) -> dict
    async def list_agents(self, status=None, limit=100) -> list
    async def update_agent(self, agent_id, updates) -> dict
    async def delete_agent(self, agent_id) -> bool
    
    # Event methods
    async def publish_event(self, event_type, aggregate_type, aggregate_id, payload) -> dict
    async def query_events(self, aggregate_id=None, event_type=None, limit=100) -> list
    
    # Tool methods
    async def register_tool(self, name, schema_def, description) -> dict
    async def get_tool(self, tool_id) -> dict
    async def list_tools(self) -> list
    async def record_tool_execution(self, tool_id, agent_id, input_params, output_result, status) -> dict
    
    # Goal methods
    async def create_goal(self, agent_id, description, success_criteria) -> dict
    async def get_goal(self, goal_id) -> dict
    async def update_goal(self, goal_id, updates) -> dict
    
    # Plan methods
    async def create_plan(self, goal_id, agent_id, steps) -> dict
    async def get_plan(self, plan_id) -> dict
    async def update_plan(self, plan_id, updates) -> dict
    
    # Task methods
    async def create_task(self, plan_id, agent_id, description, task_type) -> dict
    async def update_task(self, task_id, updates) -> dict
    
    # Evaluation methods
    async def record_evaluation(self, agent_id, task_id, evaluation_type, score, metrics) -> dict
    async def get_agent_stats(self, agent_id) -> dict
    
    # Feedback methods
    async def record_feedback(self, agent_id, task_id, feedback_type, rating, content) -> dict
    async def get_unprocessed_feedback(self, limit=100) -> list
    
    # Model usage methods
    async def record_model_usage(self, agent_id, provider, model, tokens_in, tokens_out, latency, cost) -> dict
    
    # Config methods
    async def get_config(self, namespace, key) -> dict
    async def set_config(self, namespace, key, value) -> dict

PART 3: PATCH L02 AGENT RUNTIME

File: src/L02_agent_runtime/integrations/l01_client.py
- Import L01Client from src.L01_data_layer.client

Files to patch (find and update):
- Agent creation: Use l01_client.create_agent()
- Agent status updates: Use l01_client.update_agent()
- Event emission: Use l01_client.publish_event()

Pattern:
from src.L01_data_layer.client import L01Client
l01 = L01Client()

# On agent spawn
agent = await l01.create_agent(name, agent_type, config)
await l01.publish_event("agent.spawned", "agent", agent["id"], {"name": name})

PART 4: PATCH L03 TOOL EXECUTION

Files to patch:
- Tool registration: Use l01_client.register_tool()
- Tool execution logging: Use l01_client.record_tool_execution()
- Event emission: Use l01_client.publish_event()

Pattern:
# On tool registration
tool = await l01.register_tool(name, schema, description)

# On tool execution
result = execute_tool(...)
await l01.record_tool_execution(tool_id, agent_id, input, result, status)
await l01.publish_event("tool.executed", "tool", tool_id, {"agent_id": agent_id})

PART 5: PATCH L04 MODEL GATEWAY

Files to patch:
- Usage tracking: Use l01_client.record_model_usage()
- Config loading: Use l01_client.get_config()

Pattern:
# After each completion
await l01.record_model_usage(
    agent_id=agent_id,
    provider="anthropic",
    model="claude-3",
    tokens_in=usage.input_tokens,
    tokens_out=usage.output_tokens,
    latency=latency_ms,
    cost=calculated_cost
)

PART 6: PATCH L05 PLANNING

Files to patch:
- Goal creation: Use l01_client.create_goal()
- Plan creation: Use l01_client.create_plan()
- Task management: Use l01_client.create_task(), update_task()

Pattern:
# On goal submission
goal = await l01.create_goal(agent_id, description, criteria)
await l01.publish_event("goal.created", "goal", goal["id"], {"agent_id": agent_id})

# On plan generation
plan = await l01.create_plan(goal_id, agent_id, steps)

# On task execution
await l01.update_task(task_id, {"status": "completed", "output_data": result})

PART 7: PATCH L06 EVALUATION

Files to patch:
- Evaluation recording: Use l01_client.record_evaluation()
- Stats retrieval: Use l01_client.get_agent_stats()

Pattern:
# After evaluating output
await l01.record_evaluation(
    agent_id=agent_id,
    task_id=task_id,
    evaluation_type="quality",
    score=0.85,
    metrics={"accuracy": 0.9, "relevance": 0.8}
)

PART 8: PATCH L07 LEARNING

Files to patch:
- Feedback storage: Use l01_client.record_feedback()
- Feedback retrieval: Use l01_client.get_unprocessed_feedback()

Pattern:
# On feedback received
await l01.record_feedback(
    agent_id=agent_id,
    task_id=task_id,
    feedback_type="human",
    rating=4,
    content="Good response but could be more concise"
)

PART 9: PATCH L09 API GATEWAY

Files to patch:
- src/L09_api_gateway/routers/v1/agents.py
- src/L09_api_gateway/routers/v1/goals.py
- src/L09_api_gateway/routers/v1/tasks.py
- src/L09_api_gateway/main.py

Replace stub returns with L01 calls:

# agents.py
@router.post("/")
async def create_agent(request: Request, body: CreateAgentRequest):
    from src.L01_data_layer.client import L01Client
    l01 = L01Client()
    agent = await l01.create_agent(body.name, body.agent_type, body.configuration)
    return agent

@router.get("/")
async def list_agents(request: Request):
    l01 = L01Client()
    agents = await l01.list_agents()
    return {"items": agents, "total": len(agents)}

PART 10: PATCH L10 HUMAN INTERFACE

Files to patch:
- Dashboard data fetching
- WebSocket event subscription
- Static HTML dashboard

Add Redis subscription for real-time events:

import redis.asyncio as redis

async def subscribe_to_events():
    r = redis.from_url("redis://localhost:6379")
    pubsub = r.pubsub()
    await pubsub.subscribe("l01:events")
    async for message in pubsub.listen():
        if message["type"] == "message":
            await broadcast_to_websockets(message["data"])

Update dashboard queries to use L01:

@router.get("/dashboard/agents")
async def get_dashboard_agents():
    l01 = L01Client()
    agents = await l01.list_agents()
    return {"agents": agents, "count": len(agents)}

@router.get("/dashboard/stats")
async def get_dashboard_stats():
    l01 = L01Client()
    agents = await l01.list_agents()
    events = await l01.query_events(limit=100)
    return {
        "agent_count": len(agents),
        "event_count": len(events),
        "agents_by_status": count_by_status(agents)
    }

PART 11: PATCH L11 INTEGRATION

Files to patch:
- Event subscription service
- Cross-layer event routing

Subscribe to L01 events and route:

async def event_router():
    r = redis.from_url("redis://localhost:6379")
    pubsub = r.pubsub()
    await pubsub.subscribe("l01:events")
    
    async for message in pubsub.listen():
        if message["type"] == "message":
            event = json.loads(message["data"])
            await route_event(event)

async def route_event(event):
    event_type = event.get("event_type", "")
    
    if event_type.startswith("agent."):
        await notify_agent_subscribers(event)
    elif event_type.startswith("tool."):
        await notify_tool_subscribers(event)
    elif event_type.startswith("goal."):
        await notify_planning_subscribers(event)

PART 12: ADD FUNCTIONAL DASHBOARD UI

Create: src/L10_human_interface/static/

Create: src/L10_human_interface/static/index.html

Functional dashboard that:
- Displays agent count and list
- Shows real-time event stream via WebSocket
- Shows system health status
- Provides Create Agent button
- Auto-refreshes every 10 seconds
- Connects to ws://localhost:8001/ws/events

Update L10 main.py:
- Mount static files: app.mount("/static", StaticFiles(directory="..."))
- Serve index.html at root

VERIFICATION SEQUENCE

Step 1: Create database
psql -h localhost -U postgres -c "CREATE DATABASE agentic;" 2>/dev/null || true

Step 2: Start L01
uvicorn src.L01_data_layer.main:app --host 0.0.0.0 --port 8002 &
sleep 3
curl http://localhost:8002/health/ready

Step 3: Verify tables created
psql -h localhost -U postgres -d agentic -c "\dt"

Step 4: Test L01 directly
curl -X POST http://localhost:8002/agents -H "Content-Type: application/json" -d '{"name":"test-agent","agent_type":"general"}'
curl http://localhost:8002/agents

Step 5: Start L09
uvicorn src.L09_api_gateway.main:app --host 0.0.0.0 --port 8000 &
sleep 3

Step 6: Test L09 integration
curl -X POST http://localhost:8000/api/v1/agents -H "X-API-Key: test-key-12345678901234567890123456789012" -H "Content-Type: application/json" -d '{"name":"api-agent"}'
curl http://localhost:8002/agents

Step 7: Start L10
uvicorn src.L10_human_interface.main:app --host 0.0.0.0 --port 8001 &
sleep 3

Step 8: Open dashboard
open http://localhost:8001

Step 9: Verify full flow
- Dashboard shows agents
- Create agent via dashboard
- Event stream shows activity
- Check database has records

SUCCESS CRITERIA

L01 starts and creates all tables
All CRUD endpoints work
Events publish to Redis on writes
L02-L07 can import and use L01Client
L09 persists real data via L01
L10 displays real agent data
L10 event stream shows real events
WebSocket receives live updates
MCP services unaffected (not modified)

COMPLETION

Stage all changes:
git add src/L01_data_layer/
git add src/L02_agent_runtime/
git add src/L03_tool_execution/
git add src/L04_model_gateway/
git add src/L05_planning/
git add src/L06_evaluation/
git add src/L07_learning/
git add src/L09_api_gateway/
git add src/L10_human_interface/
git add src/L11_integration/

Do NOT commit - await review

Begin implementation.
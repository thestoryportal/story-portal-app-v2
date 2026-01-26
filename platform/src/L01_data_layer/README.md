# L01: Data Layer

> Foundation layer providing event sourcing, persistent storage, and Redis pub/sub for the Story Portal Platform

**Port:** 8001
**Pattern:** Event Sourcing + CQRS
**Database:** PostgreSQL 15
**Cache:** Redis 7
**Status:** ✅ Production Ready

---

## Overview

The L01 Data Layer is the foundation of the Story Portal Platform, implementing:

- **Event Sourcing:** All state changes captured as immutable events
- **CQRS Pattern:** Separate read and write models
- **PostgreSQL:** Persistent storage for all entities and events
- **Redis Pub/Sub:** Real-time event distribution to other layers
- **REST API:** FastAPI-based endpoints for CRUD operations
- **Authentication:** Bearer token validation via L01Bridge

### Key Responsibilities

1. **Persistent Storage:** Store all platform entities (agents, goals, plans, tasks, etc.)
2. **Event Stream:** Publish events to Redis for real-time updates
3. **Data Integrity:** Enforce schema validation and constraints
4. **Query API:** Provide efficient read access to all entities
5. **Health Monitoring:** Expose health check endpoints

---

## Architecture

### Event Sourcing Pattern

```
Command → Validation → State Change → Event → Persist → Publish
```

**Example:** Creating an Agent

1. **Command:** `POST /api/agents` with agent data
2. **Validation:** Check required fields, validate schema
3. **State Change:** Insert into `agents` table
4. **Event:** Create `AgentCreated` event
5. **Persist:** Store event in `events` table
6. **Publish:** Publish to Redis channel `events:agent_created`

### Database Schema

#### Core Entities

**Agents** (`agents` table)
```sql
CREATE TABLE agents (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    agent_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    capabilities JSONB,
    configuration JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Goals** (`goals` table)
```sql
CREATE TABLE goals (
    id UUID PRIMARY KEY,
    agent_id UUID REFERENCES agents(id),
    description TEXT NOT NULL,
    priority INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
```

**Plans** (`plans` table)
```sql
CREATE TABLE plans (
    id UUID PRIMARY KEY,
    goal_id UUID REFERENCES goals(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'draft',
    steps JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Events** (`events` table)
```sql
CREATE TABLE events (
    id UUID PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    payload JSONB NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_events_type (event_type),
    INDEX idx_events_entity (entity_type, entity_id)
);
```

#### Additional Entities

- `sessions` - User/agent sessions
- `documents` - Knowledge documents
- `models` - ML models
- `tools` - Execution tools
- `datasets` - Training data
- `training_examples` - ML examples
- `evaluations` - Model evaluations
- `feedback` - User feedback
- `metrics` - Performance metrics
- `anomalies` - Detected anomalies
- `alerts` - System alerts
- `quality_scores` - Quality metrics
- `compliance_results` - Compliance checks
- `api_requests` - API request logs
- `rate_limit_events` - Rate limiting events
- `authentication_events` - Auth events
- `circuit_breaker_events` - Circuit breaker state
- `service_registry_events` - Service discovery events
- `user_interactions` - User interaction logs
- `saga_executions` - Distributed transaction orchestration
- `saga_steps` - Individual saga steps
- `control_operations` - System control operations

---

## API Endpoints

### Health Checks

```bash
# Liveness probe (always returns 200 if service is up)
GET /health/live
Response: {"status": "healthy", "timestamp": "2026-01-18T..."}

# Readiness probe (checks database and Redis connections)
GET /health/ready
Response: {
  "status": "healthy",
  "checks": {
    "database": "healthy",
    "redis": "healthy"
  },
  "timestamp": "2026-01-18T..."
}
```

### Agents

```bash
# List all agents
GET /api/agents
Response: [{"id": "...", "name": "Agent 1", ...}]

# Get specific agent
GET /api/agents/{agent_id}
Response: {"id": "...", "name": "Agent 1", ...}

# Create agent
POST /api/agents
Body: {"name": "Agent 1", "agent_type": "reasoning", ...}
Response: {"id": "...", "name": "Agent 1", ...}

# Update agent
PUT /api/agents/{agent_id}
Body: {"name": "Updated Name", ...}
Response: {"id": "...", "name": "Updated Name", ...}

# Delete agent
DELETE /api/agents/{agent_id}
Response: {"message": "Agent deleted successfully"}
```

### Goals

```bash
# List all goals
GET /api/goals

# Get specific goal
GET /api/goals/{goal_id}

# Create goal
POST /api/goals
Body: {"agent_id": "...", "description": "...", "priority": 1}

# Update goal
PUT /api/goals/{goal_id}

# Delete goal
DELETE /api/goals/{goal_id}

# List goals for specific agent
GET /api/agents/{agent_id}/goals
```

### Plans

```bash
# List all plans
GET /api/plans

# Get specific plan
GET /api/plans/{plan_id}

# Create plan
POST /api/plans
Body: {"goal_id": "...", "name": "...", "steps": [...]}

# Update plan
PUT /api/plans/{plan_id}

# Delete plan
DELETE /api/plans/{plan_id}

# List plans for specific goal
GET /api/goals/{goal_id}/plans
```

### Events

```bash
# List all events (paginated)
GET /api/events?limit=100&offset=0

# Filter events by type
GET /api/events?event_type=agent_created

# Filter events by entity
GET /api/events?entity_type=agent&entity_id={agent_id}

# Get specific event
GET /api/events/{event_id}
```

### Sessions

```bash
# List sessions
GET /api/sessions

# Create session
POST /api/sessions

# Get session
GET /api/sessions/{session_id}

# Delete session
DELETE /api/sessions/{session_id}
```

### Documents, Models, Tools, etc.

Similar CRUD patterns for all other entities. See `routers/` directory for complete endpoint definitions.

---

## Authentication

### L01Bridge Pattern

All L01 API requests require authentication via bearer token:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8001/api/agents
```

### Token Validation

The L01 Data Layer validates tokens using the L01Bridge pattern:

1. **Extract Token:** Parse `Authorization: Bearer <token>` header
2. **Validate Format:** Check token format
3. **Verify Signature:** Validate token signature (future: JWT)
4. **Check Expiration:** Ensure token is not expired (future)
5. **Allow/Deny:** Proceed with request or return 401

### Default Tokens (Development)

```python
# Default development tokens (do NOT use in production)
VALID_TOKENS = [
    "test_token_123",
    "dev_key_local_ONLY"
]
```

**Production:** Set `L01_API_KEY` environment variable:

```bash
export L01_API_KEY="your_secure_production_key_here"
```

---

## Redis Pub/Sub

### Event Publishing

When entities are created, updated, or deleted, events are published to Redis channels:

```python
# Example: Publishing agent creation event
await redis_client.publish(
    channel="events:agent_created",
    message=json.dumps({
        "event_type": "agent_created",
        "entity_id": str(agent.id),
        "payload": agent.dict(),
        "timestamp": datetime.utcnow().isoformat()
    })
)
```

### Channel Naming Convention

```
events:{event_type}
events:agent_created
events:goal_updated
events:plan_completed
events:task_started
```

### Subscribing to Events

Other layers can subscribe to these channels:

```python
import redis.asyncio as aioredis

redis = await aioredis.from_url("redis://localhost:6379")
pubsub = redis.pubsub()
await pubsub.subscribe("events:agent_created")

async for message in pubsub.listen():
    if message["type"] == "message":
        event = json.loads(message["data"])
        # Process event
```

---

## Local Development

### Prerequisites

- Python 3.11+
- PostgreSQL 15 (via Docker)
- Redis 7 (via Docker)
- Dependencies: `pip install -r requirements.txt`

### Setup

1. **Start dependencies:**
   ```bash
   docker-compose up -d postgres redis
   ```

2. **Configure environment:**
   ```bash
   export DATABASE_URL="postgresql://storyportal:storyportal@localhost:5432/storyportal"
   export REDIS_URL="redis://localhost:6379/0"
   export L01_API_KEY="dev_key_local_ONLY"
   ```

3. **Run database migrations:**
   ```bash
   # TODO: Add migration commands when implemented
   # For now, tables are created automatically via SQLAlchemy
   ```

4. **Start L01 service:**
   ```bash
   cd /path/to/platform/src/L01_data_layer
   python main.py
   ```

5. **Verify health:**
   ```bash
   curl http://localhost:8001/health/live
   ```

### Development Workflow

1. **Make changes** to routers, models, or services
2. **Restart service** (auto-reload enabled in dev mode)
3. **Test endpoint:**
   ```bash
   curl -H "Authorization: Bearer test_token_123" \
        http://localhost:8001/api/agents
   ```
4. **Check logs** for errors
5. **Query database** to verify changes:
   ```bash
   docker-compose exec postgres psql -U storyportal -d storyportal
   SELECT * FROM agents;
   ```

### Adding New Entities

1. **Define model** in `models/<entity>.py`:
   ```python
   from sqlalchemy import Column, String, UUID
   from .base import Base

   class MyEntity(Base):
       __tablename__ = "my_entities"
       id = Column(UUID, primary_key=True)
       name = Column(String(255), nullable=False)
   ```

2. **Create repository** in `repositories/<entity>.py`:
   ```python
   from .base import BaseRepository
   from models.my_entity import MyEntity

   class MyEntityRepository(BaseRepository[MyEntity]):
       pass
   ```

3. **Create router** in `routers/<entity>.py`:
   ```python
   from fastapi import APIRouter, Depends
   from repositories.my_entity import MyEntityRepository

   router = APIRouter(prefix="/api/my_entities", tags=["my_entities"])

   @router.get("/")
   async def list_entities():
       return await MyEntityRepository().list()
   ```

4. **Register router** in `main.py`:
   ```python
   from routers import my_entity
   app.include_router(my_entity.router)
   ```

---

## Database Migrations

### Current Approach

Tables are created automatically via SQLAlchemy ORM on first startup. This is sufficient for local development.

### Future: Alembic Migrations

For production deployments, we will implement Alembic migrations:

```bash
# Initialize Alembic (future)
alembic init migrations

# Create migration
alembic revision --autogenerate -m "Add new table"

# Apply migration
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

---

## Testing

### Unit Tests

```bash
# Run L01 unit tests
pytest tests/unit/test_l01_data.py

# Test specific component
pytest tests/unit/test_l01_data.py::test_create_agent
```

### Integration Tests

```bash
# Run L01 integration tests (requires running database)
pytest tests/integration/test_l01_data.py

# Test authentication
pytest tests/integration/test_authentication.py
```

### Manual Testing

```bash
# Health check
curl http://localhost:8001/health/live

# List agents (with auth)
curl -H "Authorization: Bearer test_token_123" \
     http://localhost:8001/api/agents

# Create agent
curl -X POST \
     -H "Authorization: Bearer test_token_123" \
     -H "Content-Type: application/json" \
     -d '{"name": "Test Agent", "agent_type": "reasoning"}' \
     http://localhost:8001/api/agents

# Get agent
curl -H "Authorization: Bearer test_token_123" \
     http://localhost:8001/api/agents/{agent_id}
```

---

## Dependencies

### Python Packages

```
fastapi>=0.104.1          # Web framework
uvicorn[standard]>=0.24.0 # ASGI server
sqlalchemy>=2.0.23        # ORM
asyncpg>=0.29.0          # PostgreSQL driver
redis>=5.0.1             # Redis client
pydantic>=2.5.0          # Data validation
python-jose>=3.3.0       # JWT handling (future)
```

See `requirements.txt` for complete list.

### External Services

- **PostgreSQL 15+** - Primary database
- **Redis 7+** - Pub/sub and caching

---

## Troubleshooting

### Database Connection Errors

**Error:** `FATAL: password authentication failed`

**Solution:**
```bash
# Check DATABASE_URL environment variable
echo $DATABASE_URL

# Verify PostgreSQL is running
docker-compose ps postgres

# Test connection
docker-compose exec postgres psql -U storyportal -d storyportal -c "SELECT 1;"
```

### Redis Connection Errors

**Error:** `Error connecting to Redis`

**Solution:**
```bash
# Check REDIS_URL environment variable
echo $REDIS_URL

# Verify Redis is running
docker-compose ps redis

# Test connection
docker-compose exec redis redis-cli PING
```

### Authentication Errors

**Error:** `401 Unauthorized`

**Solution:**
```bash
# Ensure Authorization header is present
curl -H "Authorization: Bearer test_token_123" \
     http://localhost:8001/api/agents

# Check L01_API_KEY environment variable
echo $L01_API_KEY

# Verify token is valid (check logs)
docker-compose logs l01_data_layer | grep "Unauthorized"
```

### Table Not Found Errors

**Error:** `relation "agents" does not exist`

**Solution:**
```bash
# Tables are created automatically on startup
# Restart L01 service to trigger table creation
docker-compose restart l01_data_layer

# Verify tables exist
docker-compose exec postgres psql -U storyportal -d storyportal -c "\dt"
```

### Event Not Publishing

**Problem:** Events not appearing in Redis

**Solution:**
```bash
# Check Redis connection
docker-compose exec redis redis-cli PING

# Monitor Redis pub/sub
docker-compose exec redis redis-cli MONITOR

# Check L01 logs for publish errors
docker-compose logs l01_data_layer | grep "publish"

# Verify Redis URL is correct
echo $REDIS_URL
```

---

## Performance Considerations

### Database Indexing

Key indexes for performance:

```sql
-- Event queries
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_entity ON events(entity_type, entity_id);
CREATE INDEX idx_events_created ON events(created_at DESC);

-- Agent queries
CREATE INDEX idx_agents_status ON agents(status);
CREATE INDEX idx_agents_type ON agents(agent_type);

-- Goal queries
CREATE INDEX idx_goals_agent ON goals(agent_id);
CREATE INDEX idx_goals_status ON goals(status);
```

### Connection Pooling

SQLAlchemy connection pool configuration:

```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,          # Max connections
    max_overflow=10,       # Additional connections
    pool_pre_ping=True,    # Verify connections
    pool_recycle=3600      # Recycle after 1 hour
)
```

### Query Optimization

- Use pagination for large result sets (`limit` and `offset`)
- Filter events by type or entity to reduce data transfer
- Use Redis for frequently accessed data (future: caching layer)

---

## Security

### API Key Management

**Development:**
```bash
export L01_API_KEY="dev_key_local_ONLY"
```

**Production:**
```bash
export L01_API_KEY="$(openssl rand -base64 32)"
```

### Input Validation

All inputs validated via Pydantic models:

```python
from pydantic import BaseModel, Field, validator

class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    agent_type: str = Field(..., regex="^(reasoning|execution|coordination)$")

    @validator("name")
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v
```

### SQL Injection Prevention

Using SQLAlchemy ORM prevents SQL injection:

```python
# Safe - parameterized query
agent = await session.execute(
    select(Agent).where(Agent.id == agent_id)
)

# NEVER do this - vulnerable to SQL injection
# query = f"SELECT * FROM agents WHERE id = '{agent_id}'"
```

---

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@host:port/database

# Redis
REDIS_URL=redis://host:port/db

# Authentication
L01_API_KEY=your_api_key_here

# Server
L01_HOST=0.0.0.0
L01_PORT=8001

# Logging
LOG_LEVEL=INFO
```

### Service Configuration

See `config/` directory for additional configuration options.

---

## Next Steps

1. **Read** [Main Platform README](../../README.md)
2. **Follow** [Quick Start Guide](../../../docs/QUICK_START.md)
3. **Explore** API endpoints with curl or Postman
4. **Check** [Troubleshooting Guide](../../../docs/TROUBLESHOOTING.md) if issues occur
5. **Review** other layer documentation (L02-L12)

---

**Last Updated:** 2026-01-18
**Maintained By:** Development Team
**Status:** ✅ Production Ready

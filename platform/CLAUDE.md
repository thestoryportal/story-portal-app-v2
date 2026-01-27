# Platform Backend

## Quick Reference

| Port | Layer | Purpose |
|------|-------|---------|
| 8001 | L01 | Data Layer (PostgreSQL, Redis, event sourcing) |
| 8004 | L04 | Model Gateway (LLM routing, adapters) |
| 8005 | L05 | Planning (goal decomposition, orchestration) |
| 8009 | L09 | API Gateway (external entry, rate limiting) |
| 8012 | L12 | NL Interface (MCP server, service discovery) |

```bash
docker-compose -f docker-compose.app.yml up -d  # Start services
curl http://localhost:8009/health               # Health check
```

## Stack

- **Python**: 3.11+ / FastAPI 0.109+ / SQLAlchemy 2.0
- **Database**: PostgreSQL 15 with pgvector (vector search)
- **Cache**: Redis 7 (pub/sub, caching, session state)
- **LLM**: Claude Code (default), Ollama (local development)
- **Validation**: Pydantic v2 for all models
- **Testing**: pytest with layer markers
- **Containers**: Docker Compose (multiple HA variants)

**Architecture**: Async-first microservices with event sourcing via L01.

## Layer Architecture (14 Layers)

| Layer | Port | Status | Purpose |
|-------|------|--------|---------|
| L00 | 8000 | Planned | Secrets Management (Vault integration) |
| L01 | 8001 | **Production** | Data Layer - event sourcing, PostgreSQL |
| L02 | 8002 | Complete | Runtime - agent lifecycle management |
| L03 | 8003 | Complete | Tool Execution - sandboxed tool runner |
| L04 | 8004 | Complete | Model Gateway - LLM routing, adapters |
| L05 | 8005 | Complete | Planning - goal decomposition, task orchestration |
| L06 | 8006 | Complete | Evaluation - quality scoring, metrics |
| L07 | 8007 | Complete | Learning - training data, feedback loops |
| L08 | 8008 | Planned | Supervision - ABAC policies, oversight |
| L09 | 8009 | **Production** | API Gateway - external entry, rate limiting |
| L10 | 8010 | Complete | Human Interface - WebSocket, dashboard |
| L11 | 8011 | Complete | Integration - event bus, sagas |
| L12 | 8012 | **Production** | NL Interface - MCP server, 60+ services |
| L13 | 8013 | Complete | Role Management - role classification |
| L14 | 8014 | Complete | Skill Library - skill definitions |

**Production Ready**: L01, L09, L12 (full test coverage, monitoring)

## Critical Rules

1. **ClaudeCodeAdapter is the default LLM provider**
   - Configured in L04 Model Gateway (`providers/claude_code_adapter.py`)
   - Fallback: Ollama for local development without API keys

2. **Validate ALL LLM output before code execution**
   - L05 validates decomposed plans via `PlanValidator`
   - L03 validates tool parameters before execution

3. **Use L01 EventStore for audit trails**
   - All state changes emit events to Redis pub/sub
   - Events persisted to PostgreSQL `events` table
   - Pattern: Command -> Validation -> State Change -> Event -> Persist -> Publish

4. **API responses must complete within 500ms**
   - Use async/await patterns everywhere
   - L04 SemanticCache for LLM response caching

5. **Never import across layers directly**
   - Use bridge classes: `L04Bridge`, `L01Bridge`
   - Bridges handle auth, retries, circuit breaking

6. **L01 authentication is REQUIRED**
   - All L01 API requests need Bearer token
   - Dev token: `dev_key_local_ONLY`
   - Production: Set `L01_API_KEY` environment variable

## Inter-Layer Communication

### Bridge Pattern (Required)
```python
# CORRECT: Use bridges for cross-layer communication
from L05_planning.integration.l04_bridge import L04Bridge
from L05_planning.integration.l01_bridge import L01Bridge

bridge = L04Bridge(base_url="http://localhost:8004")
response = await bridge.generate(prompt="...", model="claude-opus-4-5-20251101")

# WRONG: Never import across layers directly
# from L04_model_gateway.services import ModelGateway  # Don't do this
```

### Event Bus (L11 via Redis)
```python
# Publish events
await redis.publish("events:agent_created", json.dumps(event))

# Subscribe (wildcard supported)
await pubsub.subscribe("events:*")
```

## Authentication

### L01 Data Layer (Implemented)
```bash
# All L01 API requests require Bearer token
curl -H "Authorization: Bearer dev_key_local_ONLY" \
     http://localhost:8001/api/agents
```

### Development Tokens
```python
VALID_TOKENS = ["test_token_123", "dev_key_local_ONLY"]
```

### Production
Generate secure token: `openssl rand -base64 32`
Set environment variable: `L01_API_KEY`

### L09 API Gateway
Full JWT + RBAC authentication planned (see L08 Supervision layer).

## Error Code Ranges

| Layer | Range | Example |
|-------|-------|---------|
| L01 | E1000-E1999 | E1001: DB connection failed |
| L02 | E2000-E2999 | E2001: Agent spawn failed |
| L03 | E3000-E3999 | E3001: Tool not found |
| L04 | E4000-E4999 | E4001: Model not found |
| L05 | E5000-E5999 | E5001: Plan validation failed |
| L06 | E6000-E6999 | E6001: Evaluation failed |
| L07 | E7000-E7999 | E7001: Training job failed |
| L09 | E9000-E9999 | E9001: Rate limit exceeded |
| L10 | E10000-E10999 | E10001: WebSocket error |
| L11 | E11000-E11999 | E11001: Saga compensation failed |
| L12 | E12000-E12999 | E12001: Service not found |
| L13 | E13000-E13999 | E13001: Role assignment failed |
| L14 | E14000-E14999 | E14001: Skill validation failed |

## Session Infrastructure

### MCP Servers (configured in `.mcp.json`)
| Server | Purpose |
|--------|---------|
| `platform-services` | L12 service invocation (10 MCP tools) |
| `document-consolidator` | Document management, overlap detection |
| `context-orchestrator` | Task context, checkpoints, recovery |

### Roles (`.claude/roles/`)
11 role definitions (YAML):
- architect, backend-developer, code-reviewer
- database-engineer, debugger, devops-engineer
- documentation-writer, frontend-developer
- security-analyst, software-engineer, test-engineer

### Skills (`.claude/skills/`)
47 skill definitions (YAML): python, fastapi, docker, kubernetes,
testing, debugging, security_analysis, code_review, etc.

### Contexts (`.claude/contexts/`)
- `_hot_context.json` - Current session state
- `_registry.json` - Document index
- `handoffs/` - Role transition artifacts
- `quality/` - Quality checkpoint data

## Test Conventions

### Markers
```python
@pytest.mark.l01           # Layer marker
@pytest.mark.l05           # Layer marker
@pytest.mark.integration   # Integration test (requires services)
@pytest.mark.slow          # Long-running test (>30s)
@pytest.mark.unit          # Unit test (no external deps)
```

### Running Tests
```bash
# Layer-specific tests
pytest platform/src/L05_planning/tests/ -v

# By marker
pytest -m "l05 and not slow" -v

# With coverage
pytest --cov=src --cov-report=html
```

## Common Commands

### Docker Compose Variants
```bash
# Full application stack
docker-compose -f docker-compose.app.yml up -d

# HA PostgreSQL cluster
docker-compose -f docker-compose.postgres-ha.yml up -d

# HA Redis cluster
docker-compose -f docker-compose.redis-ha.yml up -d

# Service discovery (Consul)
docker-compose -f docker-compose.consul.yml up -d
```

### Utility Scripts
```bash
./backup.sh           # Database backup
./restore.sh          # Database restore
./run_l12_mcp.sh      # Start L12 MCP server (stdio)
./security-audit.sh   # Run security scan
./start_dashboard.sh  # Start monitoring dashboard (port 3000)
```

## Environment Configuration

### Critical Variables
```bash
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/agentic_platform

# Redis
REDIS_URL=redis://localhost:6379/0

# Authentication
L01_API_KEY=dev_key_local_ONLY
VITE_API_KEY=dev_key_local_ONLY  # Frontend access

# LLM Providers (choose based on setup)
ANTHROPIC_API_KEY=...           # For Claude API
OLLAMA_URL=http://localhost:11434  # For local Ollama
```

See `.env.example` (188 lines) for complete configuration template.

## Key Documentation

| Topic | Location |
|-------|----------|
| **Architecture** | `docs/PLATFORM-LAYER-SUMMARY.md` |
| **API Reference** | `docs/API_REFERENCE.md` |
| **User Guide** | `docs/USER_GUIDE.md` |
| **Security** | `SECURITY.md` |
| **High Availability** | `HIGH-AVAILABILITY.md` |
| **Service Catalog** | `PLATFORM_SERVICES_CATALOG.md` |

### Layer READMEs
```
src/L01_data_layer/README.md    - Event sourcing, PostgreSQL, auth
src/L04_model_gateway/README.md - LLM routing, provider adapters
src/L05_planning/README.md      - Goal decomposition, orchestration
src/L09_api_gateway/README.md   - Rate limiting, circuit breaker
src/L12_nl_interface/README.md  - MCP server, 60+ services
```

### Service Documentation
```
docs/services/001-020*.md       - Detailed service specifications
docs/adr/                       - Architecture Decision Records
```

## See Also

- Root CLAUDE.md: `../CLAUDE.md`
- Frontend CLAUDE.md: `../my-project/CLAUDE.md`
- Documentation Authority: `../docs/DOCUMENTATION-AUTHORITY.md`

# Development Guide - Story Portal Platform V2

**Version:** 2.0.0
**Last Updated:** 2026-01-18

---

## Table of Contents

1. [Architecture Philosophy](#architecture-philosophy)
2. [Development Environment Setup](#development-environment-setup)
3. [HTTP-First Design](#http-first-design)
4. [Working with Services](#working-with-services)
5. [Testing](#testing)
6. [Debugging](#debugging)
7. [Contributing](#contributing)

---

## Architecture Philosophy

The Story Portal Platform V2 is built on several core principles:

### 1. HTTP-First, No CLI Entry Points (Intentional)

**Design Decision:** Each layer is designed as a **microservice**, not a standalone CLI application.

#### Why No CLI Entry Points?

The absence of CLI entry points (like `__main__.py` or `cli.py`) in each layer is **intentional** and reflects our architectural philosophy:

**Microservices Architecture:**
- Each layer (L01-L12) is a **service**, not a command-line tool
- Services communicate via HTTP/REST APIs
- This enables independent scaling, deployment, and monitoring
- No need for CLI when services interact programmatically

**API-Driven Development:**
- All functionality is exposed through RESTful APIs
- Consistent interface across all layers
- Easy integration with any programming language or tool
- Better suited for containerized, orchestrated deployments

**Cloud-Native Design:**
- Designed for Docker, Kubernetes, and cloud platforms
- Health checks, metrics, and logging built-in
- Horizontal scaling without CLI complexity
- Load balancing and service discovery support

**Separation of Concerns:**
- Service logic separate from user interface
- L09 API Gateway handles external access
- L10 Human Interface provides web UI
- Clear boundaries between layers

### 2. Why This Matters

**For Developers:**
- Interact with services via HTTP requests (curl, httpie, Postman)
- No need to learn layer-specific CLI commands
- Consistent patterns across all layers
- Easy to write client libraries in any language

**For Operations:**
- Standard monitoring and health checks
- Container-friendly (no TTY required)
- Easy to integrate with CI/CD pipelines
- Works with service meshes and API gateways

**For Users:**
- Web UI (L10) for human interaction
- API Gateway (L09) for programmatic access
- Future CLI can be a thin wrapper around HTTP endpoints
- No installation of layer-specific tools required

---

## Development Environment Setup

### Prerequisites

- **Docker** 20.10+ and Docker Compose 2.x
- **Python** 3.11+ (for local development)
- **Git**
- **curl** or **httpie** (for API testing)
- **PostgreSQL** 16 (via Docker)
- **Redis** 7 (via Docker)

### Quick Start

1. **Clone the Repository**
   ```bash
   git clone https://github.com/your-org/story-portal-app.git
   cd story-portal-app
   ```

2. **Start Infrastructure**
   ```bash
   # Start PostgreSQL and Redis
   docker-compose -f docker-compose.v2.yml up postgres redis -d
   ```

3. **Start Application Layers**
   ```bash
   # Start all application layers
   docker-compose -f platform/docker-compose.app.yml up -d
   ```

4. **Verify Services**
   ```bash
   # Check health of all services
   for port in 8001 8002 8003 8004 8005 8006 8007 8009 8010 8011 8012; do
     curl -s http://localhost:$port/health | jq
   done
   ```

---

## HTTP-First Design

### How to Interact with Services

Since there are no CLI entry points, all interaction is via HTTP. Here's how:

#### Using curl (Built-in)

```bash
# Check health
curl http://localhost:8001/health

# Get all agents (L01 Data Layer)
curl http://localhost:8001/agents

# Create a new agent
curl -X POST http://localhost:8001/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "MyAgent",
    "description": "A test agent",
    "model": "llama3.2"
  }'

# Execute agent (L02 Runtime)
curl -X POST http://localhost:8002/execute \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent_123",
    "task": "Generate a Python function to calculate factorial"
  }'

# Get available models (L04 Model Gateway)
curl http://localhost:8004/models
```

#### Using httpie (Cleaner Syntax)

```bash
# Install httpie
pip install httpie

# Check health
http GET localhost:8001/health

# Create agent
http POST localhost:8001/agents \
  name="MyAgent" \
  description="A test agent" \
  model="llama3.2"

# Execute agent
http POST localhost:8002/execute \
  agent_id=agent_123 \
  task="Generate a Python function to calculate factorial"
```

#### Using Python requests

```python
import requests

# Check health
response = requests.get("http://localhost:8001/health")
print(response.json())

# Create agent
agent_data = {
    "name": "MyAgent",
    "description": "A test agent",
    "model": "llama3.2"
}
response = requests.post("http://localhost:8001/agents", json=agent_data)
print(response.json())

# Execute agent
execution_data = {
    "agent_id": "agent_123",
    "task": "Generate a Python function to calculate factorial"
}
response = requests.post("http://localhost:8002/execute", json=execution_data)
print(response.json())
```

#### Using the Web UI (L10)

For non-programmatic use, access the web dashboard:

```bash
# Open browser to
http://localhost:8010/

# Or via API Gateway (with authentication)
http://localhost:8009/
```

---

## Working with Services

### Service Architecture

Each layer exposes these standard endpoints:

#### Health Check Endpoints (All Layers)

```bash
# Basic health status
GET /health
Response: {"status": "healthy", "service": "l01-data-layer", "version": "2.0.0"}

# Liveness probe (for Kubernetes)
GET /health/live
Response: {"status": "alive"}

# Readiness probe (checks dependencies)
GET /health/ready
Response: {"status": "ready", "database": "up", "redis": "up"}

# Detailed diagnostics (if available)
GET /health/detailed
Response: {comprehensive health information}
```

### Layer-Specific Endpoints

#### L01 Data Layer (Port 8001)
```bash
# Agents
GET    /agents              # List all agents
POST   /agents              # Create agent
GET    /agents/{id}         # Get agent details
PUT    /agents/{id}         # Update agent
DELETE /agents/{id}         # Delete agent

# Tasks
GET    /tasks               # List tasks
POST   /tasks               # Create task
GET    /tasks/{id}          # Get task details

# Runs
GET    /runs                # List runs
GET    /runs/{id}           # Get run details
POST   /runs/{id}/cancel    # Cancel run
```

#### L02 Runtime (Port 8002)
```bash
# Execution
POST   /execute             # Execute agent
GET    /status/{run_id}     # Check execution status
POST   /terminate/{run_id}  # Stop execution
GET    /logs/{run_id}       # Get execution logs
```

#### L04 Model Gateway (Port 8004)
```bash
# Models
GET    /models              # List available models
POST   /chat/completions    # Chat completion (OpenAI-compatible)
POST   /embeddings          # Generate embeddings
```

#### L09 API Gateway (Port 8009)
```bash
# Authentication
POST   /auth/token          # Get JWT token
POST   /auth/refresh        # Refresh token
POST   /auth/logout         # Logout

# Proxied endpoints (all L01-L07 endpoints available here with authentication)
GET    /api/v1/agents
POST   /api/v1/agents
...
```

### Development Workflow

1. **Start Services:**
   ```bash
   docker-compose -f platform/docker-compose.app.yml up -d
   ```

2. **Check Logs:**
   ```bash
   # All services
   docker-compose -f platform/docker-compose.app.yml logs -f

   # Specific service
   docker logs -f l01-data-layer
   ```

3. **Make Code Changes:**
   - Edit files in `platform/src/L0X_*/`
   - Services will auto-reload if running with `--reload` flag

4. **Rebuild Service:**
   ```bash
   # Rebuild specific layer
   docker-compose -f platform/docker-compose.app.yml build l01-data-layer

   # Restart service
   docker-compose -f platform/docker-compose.app.yml restart l01-data-layer
   ```

5. **Test Changes:**
   ```bash
   # Test endpoint
   curl http://localhost:8001/health

   # Run tests
   pytest platform/src/L01_data_layer/tests/
   ```

---

## Testing

### Unit Tests

Each layer should have unit tests in `tests/` directory:

```bash
# Run all tests
pytest

# Run tests for specific layer
pytest platform/src/L01_data_layer/tests/

# Run with coverage
pytest --cov=platform/src/L01_data_layer --cov-report=html
```

### Integration Tests

Test layer-to-layer communication:

```bash
# Ensure all services are running
docker-compose -f platform/docker-compose.app.yml up -d

# Run integration tests
pytest tests/integration/

# Test specific integration
pytest tests/integration/test_agent_execution.py
```

### API Testing

Use curl or httpie for manual API testing:

```bash
# Test L01 → L02 flow
# 1. Create agent
AGENT_ID=$(curl -X POST http://localhost:8001/agents \
  -H "Content-Type: application/json" \
  -d '{"name": "TestAgent", "model": "llama3.2"}' | jq -r '.id')

# 2. Execute agent
RUN_ID=$(curl -X POST http://localhost:8002/execute \
  -H "Content-Type: application/json" \
  -d "{\"agent_id\": \"$AGENT_ID\", \"task\": \"Hello\"}" | jq -r '.run_id')

# 3. Check status
curl http://localhost:8002/status/$RUN_ID
```

---

## Debugging

### Viewing Logs

```bash
# Real-time logs (all services)
docker-compose -f platform/docker-compose.app.yml logs -f

# Logs for specific service
docker logs -f l01-data-layer

# Last 100 lines
docker logs --tail 100 l01-data-layer

# Follow with timestamps
docker logs -f --timestamps l01-data-layer
```

### Accessing Container

```bash
# Interactive shell
docker exec -it l01-data-layer /bin/bash

# Run Python shell
docker exec -it l01-data-layer python

# Check process
docker exec l01-data-layer ps aux
```

### Database Debugging

```bash
# Access PostgreSQL
docker exec -it agentic-postgres psql -U postgres -d agentic_platform

# Common queries
\dt                      # List tables
\d agents                # Describe agents table
SELECT * FROM agents;    # Query agents

# Check slow queries (after enabling pg_stat_statements)
SELECT query, calls, total_exec_time, mean_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### Redis Debugging

```bash
# Access Redis CLI
docker exec -it agentic-redis redis-cli

# Common commands
KEYS *                   # List all keys
GET key_name             # Get key value
TTL key_name             # Check key expiration
INFO                     # Redis info
```

### Monitoring

Access monitoring dashboards:

- **Prometheus:** http://localhost:9090
- **Grafana:** http://localhost:3000 (admin/admin)

### Common Issues

**Service not starting:**
```bash
# Check logs
docker logs l01-data-layer

# Check health
curl http://localhost:8001/health

# Restart service
docker-compose -f platform/docker-compose.app.yml restart l01-data-layer
```

**Database connection issues:**
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Test connection
docker exec agentic-postgres pg_isready -U postgres

# Check connection from layer
docker exec l01-data-layer nc -zv postgres 5432
```

**Port conflicts:**
```bash
# Check what's using port 8001
lsof -i :8001

# Use different port (update docker-compose.yml)
ports:
  - "18001:8001"
```

---

## Contributing

### Code Style

- **Python:** PEP 8, Black formatter, isort for imports
- **Docstrings:** Google style
- **Type hints:** Required for all functions

```python
def create_agent(name: str, model: str) -> dict:
    """Create a new agent.

    Args:
        name: Agent name
        model: Model identifier (e.g., "llama3.2")

    Returns:
        Agent data with ID

    Raises:
        ValueError: If name is invalid
    """
    ...
```

### Commit Messages

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Example:
```
feat(l01): Add agent tagging support

- Add tags field to Agent model
- Add /agents/{id}/tags endpoints
- Update database schema migration

Closes #123
```

### Pull Request Process

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes and add tests
3. Ensure tests pass: `pytest`
4. Commit changes following commit message format
5. Push branch: `git push origin feature/my-feature`
6. Create Pull Request on GitHub
7. Address review comments
8. Merge after approval

---

## Future: CLI Wrapper (Planned)

While the current architecture is HTTP-only, a future CLI tool is planned:

### Proposed CLI (V2.1+)

```bash
# CLI will be a thin wrapper around HTTP endpoints

# Install CLI
pip install story-portal-cli

# Configure endpoint
story-portal config set endpoint http://localhost:8009

# Authenticate
story-portal auth login

# Use CLI commands (wraps HTTP calls)
story-portal agents list
story-portal agents create --name MyAgent --model llama3.2
story-portal agents execute agent_123 --task "Generate code"
story-portal runs status run_456
```

### Why Future CLI is Optional

The CLI will be:
- **Optional:** HTTP APIs are the primary interface
- **Thin:** Just wraps HTTP endpoints, no business logic
- **Convenience:** For users who prefer CLI over HTTP
- **Compatible:** Works with any API Gateway endpoint

The platform will **always** support direct HTTP access as the primary interface.

---

## Additional Resources

- **Architecture Documentation:** [`docs/ARCHITECTURE.md`](./ARCHITECTURE.md)
- **API Documentation:** [`docs/API.md`](./API.md) (if exists)
- **Deployment Guide:** [`docs/DEPLOYMENT.md`](./DEPLOYMENT.md) (if exists)
- **Security Guide:** [`SECURITY.md`](../SECURITY.md) (if exists)

---

## Getting Help

- **GitHub Issues:** https://github.com/your-org/story-portal-app/issues
- **Documentation:** Check `docs/` directory
- **Health Status:** `curl http://localhost:8012/health` (L12 Service Hub)

---

**Document Version:** 1.0.0
**Author:** Story Portal Platform Team
**Last Review:** 2026-01-18

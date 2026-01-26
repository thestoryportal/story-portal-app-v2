# Story Portal Platform V2

> Multi-agent autonomous system for goal decomposition, planning, and execution

## Quick Start

Get the platform running in 5 minutes:

```bash
# 1. Set up environment
cp .env.example .env

# 2. Start all services
docker-compose up -d

# 3. Wait for health checks (30-60 seconds)
docker-compose ps

# 4. Open dashboard
open http://localhost:3000
```

**Default Credentials:**
- Username: `admin`
- Password: `admin`

See [Quick Start Guide](../docs/QUICK_START.md) for detailed setup instructions.

---

## Architecture Overview

The Story Portal Platform is a 12-layer autonomous agent system built for local development and extensibility:

### Core Layers

| Layer | Port | Purpose | Status |
|-------|------|---------|--------|
| **L01: Data Layer** | 8001 | Event sourcing, PostgreSQL, Redis pub/sub | ✅ Production Ready |
| **L02: Memory** | 8002 | Vector store, embeddings, semantic search | ✅ Implemented |
| **L03: Reasoning** | 8003 | Goal decomposition, planning, decision-making | ✅ Implemented |
| **L04: Execution** | 8004 | Task execution, OpenAI provider | ⚠️ Stub Implementation |
| **L05: Monitoring** | 8005 | Performance tracking, metrics | ✅ Implemented |
| **L06: Communication** | 8006 | Inter-agent messaging | ✅ Implemented |
| **L07: Knowledge** | 8007 | Domain knowledge, ontologies | ✅ Implemented |
| **L08: Learning** | 8008 | Pattern recognition, adaptation | ✅ Implemented |
| **L09: API Gateway** | 8009 | Request routing, rate limiting | ✅ Implemented |
| **L10: Human Interface** | 8010 | WebSocket, task management | ✅ Implemented |
| **L11: System Health** | 8011 | Health checks, diagnostics | ✅ Implemented |
| **L12: Security** | 8012 | Authentication, authorization | ✅ Implemented |

### Frontend

| Component | Port | Purpose |
|-----------|------|---------|
| **Dashboard UI** | 3000 | React-based monitoring and control panel |

---

## Common Commands

### Service Management

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f [service_name]

# Restart a service
docker-compose restart [service_name]

# Check service health
curl http://localhost:8001/health/live
```

### Database

```bash
# Access PostgreSQL shell
docker-compose exec postgres psql -U storyportal -d storyportal

# Run migrations (when implemented)
# TODO: Add migration commands

# View database logs
docker-compose logs postgres
```

### Redis

```bash
# Access Redis CLI
docker-compose exec redis redis-cli

# Monitor Redis pub/sub
docker-compose exec redis redis-cli MONITOR

# Check Redis status
docker-compose exec redis redis-cli PING
```

### Development

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install UI dependencies
cd ui && npm install

# Run tests
pytest tests/

# Run type checking
mypy src/

# Format code
black src/
```

---

## Documentation

### Getting Started
- [Quick Start Guide](../docs/QUICK_START.md) - 5-minute platform setup
- [Troubleshooting](../docs/TROUBLESHOOTING.md) - Common issues and solutions
- [Development Guide](../docs/DEVELOPMENT.md) - Local development workflow

### Architecture
- [Architecture Overview](../docs/ARCHITECTURE.md) - System design and patterns
- [Monitoring Guide](../docs/MONITORING.md) - Prometheus, Grafana, alerts

### Layer Documentation
- [L01: Data Layer](src/L01_data_layer/README.md) - Event sourcing, database schema
- [L02: Memory](src/L02_memory_and_context/README.md) - Vector store, embeddings
- [L03: Reasoning](src/L03_reasoning_and_planning/README.md) - Goal decomposition
- [L04: Execution](src/L04_execution_and_tools/README.md) - Task execution
- [L05: Monitoring](src/L05_monitoring_and_observability/README.md) - Metrics, traces
- [L06: Communication](src/L06_communication_and_coordination/README.md) - Messaging
- [L07: Knowledge](src/L07_knowledge_and_ontology/README.md) - Domain knowledge
- [L08: Learning](src/L08_learning_and_adaptation/README.md) - ML, adaptation
- [L09: API Gateway](src/L09_api_gateway/README.md) - Request routing
- [L10: Human Interface](src/L10_human_interface/README.md) - WebSocket, UI
- [L11: System Health](src/L11_system_health/README.md) - Health checks
- [L12: Security](src/L12_security_and_compliance/README.md) - Auth, compliance

### Operations
- [Production Deployment](../docs/PRODUCTION-DEPLOYMENT-CHECKLIST.md) - Production checklist
- [Rollback Procedures](../docs/ROLLBACK-PROCEDURES.md) - Emergency procedures
- [Backup & Recovery](scripts/RECOVERY.md) - Backup and restore

---

## Technology Stack

### Backend
- **Language:** Python 3.11+
- **Framework:** FastAPI (async REST APIs)
- **Database:** PostgreSQL 15 (event sourcing)
- **Cache:** Redis 7 (pub/sub, caching)
- **API:** OpenAI GPT-4 (optional)

### Frontend
- **Framework:** React 18 + TypeScript
- **Build:** Vite
- **UI:** Tailwind CSS, Headless UI
- **Charts:** Recharts
- **State:** React Query

### Infrastructure
- **Container:** Docker + Docker Compose
- **Monitoring:** Prometheus + Grafana
- **Logging:** Structured JSON logs
- **Testing:** pytest, React Testing Library

---

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker Desktop 4.0+
- 8GB RAM minimum
- 10GB disk space

### Setup

1. **Clone repository:**
   ```bash
   git clone <repo-url>
   cd story-portal-app/platform
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Start platform:**
   ```bash
   docker-compose up -d
   ```

4. **Verify health:**
   ```bash
   # Check all services
   ./scripts/health-check.sh

   # Or manually
   curl http://localhost:8001/health/live
   curl http://localhost:8009/health/live
   curl http://localhost:8010/health/live
   ```

5. **Access dashboard:**
   Open http://localhost:3000

### Development Workflow

1. **Make changes** to Python/TypeScript code
2. **Restart service** (changes auto-reload in dev mode)
3. **Test changes** with curl or dashboard
4. **Run tests** before committing
5. **Check logs** if issues occur

---

## Running Tests

### Unit Tests

```bash
# Run all tests
pytest

# Run specific layer tests
pytest tests/unit/test_l01_data.py

# Run with coverage
pytest --cov=src --cov-report=html
```

### Integration Tests

```bash
# Run integration tests (requires running services)
pytest tests/integration/

# Test specific integration
pytest tests/integration/test_authentication.py
```

### Smoke Tests

```bash
# Quick smoke test of all endpoints
pytest tests/smoke/

# Test from outside container
./scripts/smoke-test.sh
```

---

## Project Structure

```
platform/
├── src/                      # Source code (12 layers)
│   ├── L01_data_layer/      # Event sourcing, DB
│   ├── L02_memory_and_context/
│   ├── L03_reasoning_and_planning/
│   ├── L04_execution_and_tools/
│   ├── L05_monitoring_and_observability/
│   ├── L06_communication_and_coordination/
│   ├── L07_knowledge_and_ontology/
│   ├── L08_learning_and_adaptation/
│   ├── L09_api_gateway/
│   ├── L10_human_interface/
│   ├── L11_system_health/
│   └── L12_security_and_compliance/
├── ui/                       # React dashboard
├── tests/                    # Test suite
│   ├── unit/
│   ├── integration/
│   └── smoke/
├── scripts/                  # Utility scripts
├── monitoring/              # Prometheus, Grafana configs
├── migrations/              # Database migrations
├── docker-compose.yml       # Service orchestration
├── .env.example            # Environment template
└── README.md               # This file
```

---

## Environment Variables

Key environment variables (see `.env.example` for full list):

```bash
# Database
DATABASE_URL=postgresql://user:pass@postgres:5432/storyportal

# Redis
REDIS_URL=redis://redis:6379/0

# API Keys (set these for production)
L01_API_KEY=your_api_key_here
VITE_API_KEY=your_api_key_here
OPENAI_API_KEY=your_openai_key_here  # Optional

# Security
JWT_SECRET=your_jwt_secret_here
```

---

## Troubleshooting

### Services won't start
```bash
# Check Docker resources
docker system df

# Clean up old containers
docker-compose down -v
docker system prune -a

# Restart Docker Desktop
```

### Database connection errors
```bash
# Check PostgreSQL status
docker-compose logs postgres

# Verify connection
docker-compose exec postgres psql -U storyportal -d storyportal -c "SELECT 1;"
```

### Dashboard shows no data
```bash
# Check L01 Data Layer health
curl http://localhost:8001/health/live

# Check API Gateway health
curl http://localhost:8009/health/live

# Verify authentication
curl -H "Authorization: Bearer test_token_123" http://localhost:8001/api/agents
```

See [Troubleshooting Guide](../docs/TROUBLESHOOTING.md) for more solutions.

---

## Contributing

### Code Style
- **Python:** Black formatter, MyPy type checking
- **TypeScript:** ESLint, Prettier
- **Commits:** Conventional commits format

### Pull Request Process
1. Create feature branch
2. Make changes with tests
3. Run full test suite
4. Update documentation
5. Submit PR with description

---

## License

[Add license information]

---

## Support

- **Issues:** [GitHub Issues]
- **Docs:** [Documentation Site]
- **Chat:** [Discord/Slack]

---

## Current Status

**Version:** 2.0.0-dev
**Phase:** Local Development
**Production Ready:** No (see [Production Checklist](../docs/PRODUCTION-DEPLOYMENT-CHECKLIST.md))

### Known Limitations
- L04 Execution Layer is stub implementation
- No CI/CD pipeline configured
- Limited to single-developer local workflow
- Not tested for 300+ concurrent users
- No high-availability configuration

### Roadmap
- **V2.1:** Complete L04 Execution Layer
- **V2.2:** Add CI/CD pipeline
- **V3.0:** Production deployment features
- **V3.1:** High availability support
- **V3.2:** Auto-scaling capabilities

---

**Last Updated:** 2026-01-18
**Maintained By:** Development Team

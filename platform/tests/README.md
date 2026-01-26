# Story Portal Platform V2 - Test Suite

**Test Framework:** pytest
**Coverage Target:** 80%
**Test Types:** Unit, Integration, Smoke

## Overview

This test suite provides comprehensive testing for the Story Portal Platform V2, including integration tests for all services and unit tests for critical components.

## Test Structure

```
platform/tests/
├── __init__.py
├── README.md                    # This file
├── conftest.py                  # Global fixtures
├── integration/                 # Integration tests (require running services)
│   ├── __init__.py
│   ├── conftest.py             # Integration test fixtures
│   ├── test_health.py          # Health check tests (✅ IMPLEMENTED)
│   ├── test_l01_data.py        # L01 Data Layer tests
│   ├── test_l09_gateway.py     # L09 API Gateway tests
│   ├── test_authentication.py  # Auth flow tests
│   └── test_end_to_end.py      # E2E workflows
└── unit/                        # Unit tests (fast, isolated)
    ├── __init__.py
    ├── test_models.py
    ├── test_services.py
    └── test_utils.py
```

## Running Tests

### All Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run with HTML coverage report
pytest --cov --cov-report=html
open htmlcov/index.html
```

### By Test Type

```bash
# Run integration tests only
pytest -m integration

# Run unit tests only
pytest -m unit

# Run smoke tests (critical paths)
pytest -m smoke

# Run health checks
pytest -m health
```

### By Service Layer

```bash
# Test specific layer
pytest -m l01  # L01 Data Layer
pytest -m l09  # L09 API Gateway
pytest -m l10  # L10 Human Interface
pytest -m l12  # L12 Service Hub
```

### Specific Tests

```bash
# Run specific test file
pytest platform/tests/integration/test_health.py

# Run specific test class
pytest platform/tests/integration/test_health.py::TestHealthEndpoints

# Run specific test function
pytest platform/tests/integration/test_health.py::TestHealthEndpoints::test_l01_health

# Run tests matching pattern
pytest -k "health"
```

### Performance Options

```bash
# Run tests in parallel (requires pytest-xdist)
pytest -n auto

# Show slowest 10 tests
pytest --durations=10

# Run with verbose output
pytest -vv

# Run with minimal output
pytest -q
```

## Test Markers

Tests are categorized using markers for flexible test execution:

### Test Type Markers
- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests (require services)
- `@pytest.mark.smoke` - Smoke tests (critical path)
- `@pytest.mark.slow` - Slow tests (can be skipped in CI)
- `@pytest.mark.e2e` - End-to-end tests

### Layer Markers
- `@pytest.mark.l01` - L01 Data Layer tests
- `@pytest.mark.l02` - L02 Runtime Layer tests
- `@pytest.mark.l03` - L03 Tool Execution tests
- `@pytest.mark.l04` - L04 Model Gateway tests
- `@pytest.mark.l05` - L05 Planning tests
- `@pytest.mark.l06` - L06 Evaluation tests
- `@pytest.mark.l07` - L07 Learning tests
- `@pytest.mark.l09` - L09 API Gateway tests
- `@pytest.mark.l10` - L10 Human Interface tests
- `@pytest.mark.l11` - L11 Integration Layer tests
- `@pytest.mark.l12` - L12 Service Hub tests

### Component Markers
- `@pytest.mark.database` - Database tests
- `@pytest.mark.redis` - Redis tests
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.auth` - Authentication tests
- `@pytest.mark.security` - Security tests
- `@pytest.mark.performance` - Performance tests
- `@pytest.mark.health` - Health check tests

## Test Fixtures

### HTTP Client Fixtures

```python
@pytest.mark.asyncio
async def test_example(http_client: httpx.AsyncClient):
    """Example test using HTTP client fixture"""
    response = await http_client.get("http://localhost:8001/health")
    assert response.status_code == 200
```

### Service Client Fixtures

```python
@pytest.mark.asyncio
async def test_l01(l01_client):
    """Example test using L01 client fixture"""
    response = await l01_client.health()
    assert response.status_code == 200
```

### Database Fixtures

```python
def test_database(db_connection_string):
    """Example test using database connection"""
    from sqlalchemy import create_engine
    engine = create_engine(db_connection_string)
    # ... test code
```

### Redis Fixtures

```python
def test_redis(redis_url):
    """Example test using Redis connection"""
    import redis
    client = redis.from_url(redis_url)
    # ... test code
```

## Writing Tests

### Integration Test Example

```python
import pytest
import httpx

pytestmark = [pytest.mark.integration, pytest.mark.l01]


@pytest.mark.asyncio
class TestL01DataLayer:
    """Integration tests for L01 Data Layer"""

    async def test_create_agent(self, l01_client):
        """Test creating an agent"""
        agent_data = {
            "name": "TestAgent",
            "type": "task",
            "description": "Test agent"
        }

        response = await l01_client.create_agent(agent_data)
        assert response.status_code == 201

        data = response.json()
        assert data["name"] == "TestAgent"
        assert "id" in data

    async def test_get_agents(self, l01_client):
        """Test retrieving agents"""
        response = await l01_client.get_agents()
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
```

### Unit Test Example

```python
import pytest
from platform.src.L01_data_layer.models import Agent

pytestmark = pytest.mark.unit


class TestAgentModel:
    """Unit tests for Agent model"""

    def test_agent_creation(self):
        """Test creating an Agent instance"""
        agent = Agent(
            name="TestAgent",
            type="task",
            description="Test"
        )

        assert agent.name == "TestAgent"
        assert agent.type == "task"

    def test_agent_validation(self):
        """Test Agent model validation"""
        with pytest.raises(ValueError):
            Agent(name="", type="invalid")
```

## Coverage Requirements

The test suite maintains a minimum of 80% code coverage:

```bash
# Check coverage
pytest --cov --cov-fail-under=80

# Generate coverage report
pytest --cov --cov-report=html
open htmlcov/index.html
```

### Coverage by Component

Target coverage by component:
- **L01 Data Layer:** 85%+ (critical data operations)
- **L09 API Gateway:** 90%+ (public API surface)
- **L10 Human Interface:** 80%+ (UI backend)
- **L12 Service Hub:** 85%+ (service coordination)
- **Other Services:** 80%+

## Continuous Integration

Tests run automatically in CI/CD pipeline:

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: |
          docker-compose up -d
          pytest --cov --cov-fail-under=80
```

## Test Data Management

### Fixtures

Test data is managed through fixtures in `conftest.py`:

```python
@pytest.fixture
def sample_agent():
    return {
        "name": "TestAgent",
        "type": "task",
        "description": "Test agent for integration tests"
    }
```

### Test Database

Integration tests use the development database. For production-like testing:

```bash
# Set up test database
docker-compose -f docker-compose.test.yml up -d

# Run tests against test database
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/agentic_platform_test \
  pytest -m integration
```

## Troubleshooting

### Services Not Available

If integration tests fail with connection errors:

```bash
# Check services are running
docker ps

# Check service logs
docker logs l01-data-layer
docker logs l09-api-gateway

# Restart services
docker-compose restart
```

### Database Connection Issues

```bash
# Verify PostgreSQL is accessible
docker exec agentic-postgres psql -U postgres -c "SELECT 1"

# Check connection string
echo $DATABASE_URL
```

### Redis Connection Issues

```bash
# Verify Redis is accessible
docker exec agentic-redis redis-cli ping

# Check Redis URL
echo $REDIS_URL
```

## Test Development Guidelines

### 1. Test Naming

- Test files: `test_*.py` or `*_test.py`
- Test classes: `Test*`
- Test functions: `test_*`

### 2. Test Organization

- Group related tests in classes
- Use descriptive test names
- One assertion per test (when possible)
- Use parametrize for similar tests

### 3. Async Tests

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result == expected
```

### 4. Test Independence

- Tests should not depend on each other
- Use fixtures for setup/teardown
- Clean up after tests (database, Redis)

### 5. Markers

Always mark tests appropriately:

```python
pytestmark = [pytest.mark.integration, pytest.mark.l01, pytest.mark.database]
```

## Performance Testing

### Load Testing

```python
@pytest.mark.performance
@pytest.mark.slow
async def test_concurrent_requests(http_client):
    """Test service under concurrent load"""
    import asyncio

    async def make_request():
        return await http_client.get("http://localhost:8001/health")

    # Send 100 concurrent requests
    tasks = [make_request() for _ in range(100)]
    responses = await asyncio.gather(*tasks)

    # All requests should succeed
    assert all(r.status_code == 200 for r in responses)
```

### Benchmarking

```python
@pytest.mark.performance
def test_query_performance(benchmark, db_connection):
    """Benchmark database query performance"""
    def query_agents():
        return db_connection.execute("SELECT * FROM agents LIMIT 100")

    result = benchmark(query_agents)
    assert len(result) > 0
```

## Dependencies

Required packages (install via `pip install -r requirements-test.txt`):

```
pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-cov>=4.0.0
pytest-xdist>=3.0.0  # Parallel execution
pytest-timeout>=2.1.0  # Test timeouts
pytest-benchmark>=4.0.0  # Performance testing
httpx>=0.24.0  # Async HTTP client
pytest-mock>=3.10.0  # Mocking support
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_PASSWORD: postgres
        ports:
          - 5432:5432

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt

      - name: Start services
        run: docker-compose up -d

      - name: Wait for services
        run: sleep 30

      - name: Run tests
        run: |
          pytest --cov --cov-report=xml --cov-fail-under=80

      - name: Upload coverage
        uses: codecov/codecov-action@v2
        with:
          file: ./coverage.xml
```

## References

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [HTTPX Documentation](https://www.python-httpx.org/)
- [Coverage.py](https://coverage.readthedocs.io/)

---

**Last Updated:** 2026-01-18
**Test Suite Version:** 2.0.0
**Minimum Coverage:** 80%

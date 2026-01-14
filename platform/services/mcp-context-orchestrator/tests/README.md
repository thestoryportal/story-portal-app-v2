# MCP Context Orchestrator Test Suite

This directory contains comprehensive tests for the MCP Context Orchestrator service, organized into three levels following the testing pyramid pattern.

## Test Structure

```
tests/
├── unit/                     # Unit tests (fast, isolated)
│   ├── config.test.ts       # Configuration loading
│   ├── tools.test.ts        # Tool input validation & logic
│   ├── cache.test.ts        # Cache operations
│   └── recovery.test.ts     # Recovery engine logic
├── integration/              # Integration tests (database, external services)
│   └── database.test.ts     # Database operations
└── e2e/                      # End-to-end tests (full workflows)
    ├── context-lifecycle.test.ts       # Full context lifecycle
    ├── workflow-integration.mjs        # Complete workflow test
    └── mcp-tools-integration.mjs       # MCP protocol tool tests
```

## Test Types

### Unit Tests (`tests/unit/`)

Fast, isolated tests that verify individual components work correctly:

- **config.test.ts**: Configuration loading from environment variables
- **tools.test.ts**: Tool input schemas and execution logic
- **cache.test.ts**: Redis cache operations (mocked)
- **recovery.test.ts**: Recovery engine logic and checkpoint management

**Run unit tests:**
```bash
npm run test:unit
```

### Integration Tests (`tests/integration/`)

Tests that verify components work together with real external services:

- **database.test.ts**: PostgreSQL database operations, schema interactions
- **context-lifecycle.test.ts**: Task context creation, checkpoints, recovery workflows

**Run integration tests:**
```bash
npm run test:integration
```

**Requirements:**
- PostgreSQL running with `mcp_contexts` schema
- Proper DATABASE_URL or POSTGRES_* environment variables

### End-to-End Tests (`tests/e2e/`)

Complete workflow tests that verify the entire system works from end to end:

- **workflow-integration.mjs**: Full MCP workflow with stdio transport
- **mcp-tools-integration.mjs**: MCP tool invocation over JSON-RPC

**Run E2E tests:**
```bash
npm run test:e2e
```

**Requirements:**
- PostgreSQL running
- Redis running
- Built server (`npm run build`)

## Running Tests

### All Tests
```bash
npm test
```

### With Coverage
```bash
npm test -- --coverage
```

### Watch Mode
```bash
npm test -- --watch
```

### Specific Test File
```bash
npm test tests/unit/config.test.ts
```

## Test Configuration

Tests are configured via `vitest.config.ts`:

- **Timeout**: 10 seconds per test
- **Environment**: Node.js
- **Coverage**: v8 provider
- **Globals**: Enabled for describe/it/expect

## Mocking Strategy

### Unit Tests
- Mock all external dependencies (database, cache, HTTP clients)
- Use Vitest's `vi.mock()` for module mocking
- Focus on logic verification

### Integration Tests
- Use real database connections (test schema)
- Mock external HTTP APIs
- Verify data persistence and retrieval

### E2E Tests
- Use real infrastructure (database, cache, server)
- Test complete user workflows
- Verify MCP protocol compliance

## Best Practices

1. **Isolation**: Each test should be independent
2. **Cleanup**: Use `beforeEach`/`afterEach` for setup/teardown
3. **Assertions**: Use descriptive expect messages
4. **Naming**: Use clear, descriptive test names
5. **Coverage**: Aim for >80% code coverage

## Debugging Tests

### Debug Single Test
```bash
npm test -- --reporter=verbose tests/unit/config.test.ts
```

### Debug with Inspector
```bash
node --inspect-brk node_modules/.bin/vitest run tests/unit/config.test.ts
```

### View Coverage Report
```bash
npm test -- --coverage
open coverage/index.html
```

## CI/CD Integration

Tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run Tests
  run: |
    npm run build
    npm test -- --coverage
  env:
    DATABASE_URL: postgresql://test:test@localhost:5432/test_db
    REDIS_URL: redis://localhost:6379
```

## Adding New Tests

When adding new functionality:

1. **Start with unit tests** - Test the logic in isolation
2. **Add integration tests** - Verify database/cache interactions
3. **Create E2E tests** - Test complete user workflows

Example:
```typescript
// tests/unit/new-feature.test.ts
import { describe, it, expect } from 'vitest';

describe('NewFeature', () => {
  it('should do something correctly', () => {
    expect(true).toBe(true);
  });
});
```

## Troubleshooting

### Tests Timeout
- Increase timeout in `vitest.config.ts`
- Check database/cache connectivity
- Verify environment variables

### Database Connection Errors
- Ensure PostgreSQL is running
- Verify `mcp_contexts` schema exists
- Check connection credentials

### Mock Import Errors
- Ensure mocks are defined before imports
- Use `vi.resetModules()` between tests
- Check import paths match file structure

## Resources

- [Vitest Documentation](https://vitest.dev/)
- [Testing Best Practices](https://github.com/goldbergyoni/javascript-testing-best-practices)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)

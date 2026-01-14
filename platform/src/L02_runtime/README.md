# L02 Agent Runtime Layer

Production-grade agent execution and orchestration layer for the Agentic Platform.

## Overview

The L02 Agent Runtime Layer provides lifecycle management, resource control, and execution orchestration for AI agents. This implementation follows the [Agent Runtime Layer Specification v1.2](../../specs/agent-runtime-layer-specification-v1.2-final-ASCII.md).

## Implementation Status

### ✅ Phase 1: Foundation (Completed)

**Components:**
- **Data Models**: Complete type-safe models for agents, configurations, and state
- **RuntimeBackend Protocol**: Abstraction layer for pluggable backends
- **LocalRuntime**: Docker-based backend for local development
- **KubernetesRuntime**: Stub for production K8s deployment
- **Sandbox Manager**: Trust level mapping and isolation configuration
- **Lifecycle Manager**: Agent spawn, terminate, suspend, resume operations

**Architecture Highlights:**
- Abstracted runtime backend supports both local (Docker) and production (K8s) environments
- Trust-level based sandbox selection (trusted → runc, untrusted → kata)
- Resource limit enforcement (CPU, memory, token budgets)
- Network policy configuration (isolated, restricted, allow_egress)

### 🚧 Future Phases (Planned)

- **Phase 2**: Agent Executor, Resource Manager, ModelBridge
- **Phase 3**: State Manager, Enhanced SessionBridge
- **Phase 4**: DocumentBridge (Phase 15 integration)
- **Phase 5**: Fleet Manager, Warm Pool
- **Phase 6**: Health Monitor, Observability
- **Phase 7**: Workflow Engine (LangGraph pattern)
- **Phase 8**: Security hardening, performance tuning

## Quick Start

### Prerequisites

- Python 3.11+
- Docker Desktop running (for LocalRuntime)
- PostgreSQL 16 (for future State Manager)
- Redis 7 (for future hot state)

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# For development with tests
pip install -r requirements.txt
```

### Basic Usage

```python
from L02_runtime import AgentRuntime, AgentConfig, TrustLevel

# Create runtime
runtime = AgentRuntime()
await runtime.initialize()

# Spawn an agent
config = AgentConfig(
    agent_id="my-agent",
    trust_level=TrustLevel.STANDARD
)

result = await runtime.spawn(config)
print(f"Agent spawned: {result.agent_id}")

# Get agent state
state = await runtime.get_state("my-agent")
print(f"Agent state: {state.value}")

# Terminate agent
await runtime.terminate("my-agent", reason="completed")

# Cleanup
await runtime.cleanup()
```

### Configuration

Edit `config/default_config.yaml` to configure:

- **Backend selection**: `local` (Docker) or `kubernetes`
- **Resource limits**: Default CPU, memory, token budgets
- **Lifecycle policies**: Spawn timeouts, restart limits
- **Sandbox settings**: Available runtime classes

Example:

```yaml
runtime:
  backend: "local"  # or "kubernetes"

sandbox:
  default_runtime_class: "runc"
  default_cpu: "2"
  default_memory: "2Gi"
  default_tokens_per_hour: 100000

lifecycle:
  spawn_timeout_seconds: 60
  enable_suspend: true
```

## Architecture

### Runtime Backend Abstraction

```
┌─────────────────────────────────────────┐
│         AgentRuntime API                │
│  (spawn, terminate, suspend, resume)    │
└──────────────┬──────────────────────────┘
               │
       ┌───────┴────────┐
       │                │
       v                v
┌──────────────┐  ┌──────────────┐
│ LocalRuntime │  │   K8sRuntime │
│   (Docker)   │  │    (stub)    │
└──────────────┘  └──────────────┘
```

### Component Layering

```
┌────────────────────────────────────────┐
│          AgentRuntime                  │  ← Public API
├────────────────────────────────────────┤
│  LifecycleManager  │  SandboxManager   │  ← Orchestration
├────────────────────────────────────────┤
│       RuntimeBackend Protocol          │  ← Abstraction
├────────────────────────────────────────┤
│  LocalRuntime   │   KubernetesRuntime  │  ← Implementations
└────────────────────────────────────────┘
```

### Trust Level Mapping

| Trust Level | Runtime Class | Network Policy | Use Case |
|-------------|---------------|----------------|----------|
| TRUSTED | runc | allow_egress | Verified first-party code |
| STANDARD | gvisor | restricted | Audited third-party code |
| UNTRUSTED | kata | isolated | Unknown code |
| CONFIDENTIAL | kata-cc | isolated | Sensitive data processing |

## Testing

### Run Unit Tests

```bash
# Run all tests
pytest platform/src/L02_runtime/tests/

# Run specific test file
pytest platform/src/L02_runtime/tests/test_models.py -v

# Run with coverage
pytest platform/src/L02_runtime/tests/ --cov=L02_runtime
```

### Run Integration Tests

Integration tests require Docker:

```bash
# Run integration tests
pytest platform/src/L02_runtime/tests/test_integration_local.py -v -m integration

# Skip integration tests
pytest platform/src/L02_runtime/tests/ -m "not integration"
```

### Manual Integration Test

```bash
cd platform/src/L02_runtime/tests
python test_integration_local.py
```

## Development

### Directory Structure

```
L02_runtime/
├── models/               # Data models
│   ├── agent_models.py
│   ├── checkpoint_models.py
│   ├── health_models.py
│   ├── workflow_models.py
│   ├── fleet_models.py
│   └── resource_models.py
├── backends/             # Runtime backends
│   ├── protocol.py       # RuntimeBackend protocol
│   ├── local_runtime.py  # Docker implementation
│   └── kubernetes_runtime.py  # K8s stub
├── services/             # Core services
│   ├── sandbox_manager.py
│   └── lifecycle_manager.py
├── config/               # Configuration
│   └── default_config.yaml
├── tests/                # Test suite
│   ├── test_models.py
│   ├── test_sandbox_manager.py
│   ├── test_lifecycle_manager.py
│   └── test_integration_local.py
├── runtime.py            # Main AgentRuntime class
└── __init__.py           # Public API
```

### Adding a New Backend

To add a new runtime backend (e.g., AWS ECS, Azure Container Instances):

1. Implement the `RuntimeBackend` protocol in `backends/`
2. Register in `backends/__init__.py`
3. Add configuration in `config/default_config.yaml`
4. Update `runtime.py` to instantiate your backend

Example:

```python
from ..backends.protocol import RuntimeBackend

class MyCustomRuntime:
    """Custom runtime implementation"""

    async def initialize(self) -> None:
        """Connect to runtime"""
        pass

    async def spawn_container(self, config, sandbox, ...):
        """Spawn agent"""
        pass

    # Implement other RuntimeBackend methods...
```

## Integration Points

### Phase 15: MCP document-consolidator

```python
# Future: DocumentBridge for document queries during execution
from L02_runtime.bridges import DocumentBridge

doc_bridge = DocumentBridge(mcp_url="http://localhost:3000")
docs = await doc_bridge.query("user authentication flows")
```

### Phase 16: MCP context-orchestrator

```python
# Future: SessionBridge for state persistence
from L02_runtime.bridges import SessionBridge

session_bridge = SessionBridge(mcp_url="http://localhost:3001")
await session_bridge.save_context_snapshot(agent_id, context)
```

### L04: Model Gateway

```python
# Future: ModelBridge for LLM routing
from L02_runtime.bridges import ModelBridge

model_bridge = ModelBridge(gateway_url="http://localhost:8080")
response = await model_bridge.complete(prompt, model="claude-sonnet-4")
```

## Error Codes

Phase 1 error codes:

| Code | Name | Description |
|------|------|-------------|
| E2020 | SPAWN_FAILED | Agent spawn failed |
| E2021 | SPAWN_TIMEOUT | Spawn exceeded timeout |
| E2022 | TERMINATE_FAILED | Clean termination failed |
| E2023 | SUSPEND_FAILED | Suspend operation failed |
| E2024 | RESUME_FAILED | Resume from suspend failed |
| E2025 | RESTART_LIMIT_EXCEEDED | Max restarts reached |
| E2040 | SANDBOX_UNAVAILABLE | RuntimeClass not available |
| E2041 | INVALID_CPU_LIMIT | CPU limit out of range |
| E2042 | INVALID_MEMORY_LIMIT | Memory limit out of range |
| E2043 | INVALID_TOKEN_LIMIT | Token limit invalid |
| E2044 | SECURITY_VIOLATION | Security context violation |

## Performance Considerations

### LocalRuntime (Docker)

- **Spawn time**: ~2-5 seconds (cold start)
- **Suspend/resume**: ~100ms (docker pause/unpause)
- **Resource overhead**: ~50MB per container
- **Concurrent agents**: Limited by Docker daemon (typically 100-200)

### KubernetesRuntime (Production)

- **Spawn time**: ~5-10 seconds (pod scheduling + image pull)
- **Suspend/resume**: Varies by checkpoint method
- **Resource overhead**: K8s pod overhead (~10MB)
- **Concurrent agents**: Scalable (1000s with proper cluster sizing)

## Security

### Sandbox Isolation Levels

1. **runc** (TRUSTED): Standard OCI runtime, namespace isolation
2. **gVisor** (STANDARD): User-space kernel, application sandbox
3. **Kata Containers** (UNTRUSTED): Lightweight VM, strong isolation
4. **Kata-CC** (CONFIDENTIAL): Kata + confidential computing (SGX/SEV)

### Security Context

All agents run with:
- Non-root user (UID 65534)
- Read-only root filesystem (writable `/tmp` only)
- Dropped capabilities (CAP_DROP ALL)
- Seccomp profile (RuntimeDefault)
- No privilege escalation

## Monitoring

### Metrics (Future: Phase 6)

```python
# Prometheus metrics endpoint
from L02_runtime.observability import MetricsCollector

metrics = MetricsCollector()
await metrics.start_server(port=9090)

# Metrics available:
# - agent_spawn_total
# - agent_spawn_duration_seconds
# - agent_state_total{state="running|suspended|terminated"}
# - resource_usage_cpu_seconds
# - resource_usage_memory_bytes
```

## Roadmap

- [x] **v0.1.0**: Phase 1 Foundation (LocalRuntime, Lifecycle Manager)
- [ ] **v0.2.0**: Phase 2 Core Execution (Agent Executor, Resource Manager)
- [ ] **v0.3.0**: Phase 3 State Management (Checkpoints, SessionBridge)
- [ ] **v0.4.0**: Phase 4 Document Integration (DocumentBridge)
- [ ] **v0.5.0**: Phase 5 Fleet Operations (Scaling, Warm Pool)
- [ ] **v0.6.0**: Phase 6 Observability (Health Monitor, Metrics)
- [ ] **v0.7.0**: Phase 7 Workflows (Workflow Engine, Multi-Agent)
- [ ] **v1.0.0**: Phase 8 Production Hardening

## Contributing

Phase 1 is complete. For Phase 2+ contributions:

1. Review the [specification](../../specs/agent-runtime-layer-specification-v1.2-final-ASCII.md)
2. Check the implementation order in Section 11.2
3. Follow the existing patterns for error handling and async operations
4. Add tests for all new functionality

## License

Internal platform component - not for external distribution.

## References

- [Agent Runtime Layer Specification v1.2](../../specs/agent-runtime-layer-specification-v1.2-final-ASCII.md)
- [Data Layer v4.0 Specification](../../specs/agentic-data-layer-*.md)
- [Model Gateway Specification](../../specs/model-gateway-*.md)
- [MCP Context Orchestrator](../../services/mcp-context-orchestrator/)
- [MCP Document Consolidator](../../services/mcp-document-consolidator/)

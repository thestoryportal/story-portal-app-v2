# Service 2/44: ConfigStore

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L01 (Data Layer) |
| **Module** | `L01_data_layer.services.config_store` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | PostgreSQL |
| **Category** | Data & Storage |

## Role in Development Environment

The **ConfigStore** is a namespaced key-value store for persistent configuration management. It provides **versioned configuration storage** with automatic version tracking on every update.

**Key Features:**
- Namespaced organization (group configs by service/feature)
- Automatic version incrementing on updates
- JSON value storage for complex configurations
- Upsert semantics (insert or update)
- Timestamp tracking for created/updated times

## Data Model

### Configuration Fields
- `id: UUID` - Unique identifier
- `namespace: str` - Logical grouping (e.g., "agents", "models", "ui")
- `key: str` - Configuration key within namespace
- `value: Dict[str, Any]` - JSON value blob
- `version: int` - Auto-incremented on each update (starts at 1)
- `created_at: datetime` - Initial creation time
- `updated_at: datetime` - Last modification time

### Namespace + Key Uniqueness
The combination of `(namespace, key)` is unique. Setting a value for an existing key triggers an upsert that increments the version.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/config/{namespace}/{key}` | Get specific config value |
| `PUT` | `/config/{namespace}/{key}` | Set/update config value (upsert) |
| `GET` | `/config/{namespace}` | List all configs in namespace |

## Use Cases in Your Workflow

### 1. Store Model Configuration
```bash
curl -X PUT http://localhost:8011/config/models/claude-opus \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "claude-opus-4-5-20251101",
    "max_tokens": 8192,
    "temperature": 0.7,
    "enabled": true
  }'
```

### 2. Feature Flags
```bash
# Set feature flag
curl -X PUT http://localhost:8011/config/features/dark-mode \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "beta": false}'

# Check feature flag
curl http://localhost:8011/config/features/dark-mode
```

### 3. Service-Specific Settings
```bash
# Store agent configuration
curl -X PUT http://localhost:8011/config/agents/explore-agent \
  -H "Content-Type: application/json" \
  -d '{
    "thoroughness": "medium",
    "max_depth": 5,
    "timeout_seconds": 120
  }'

# List all agent configs
curl http://localhost:8011/config/agents
```

### 4. Environment-Specific Configuration
```bash
# Development settings
curl -X PUT http://localhost:8011/config/env/development \
  -H "Content-Type: application/json" \
  -d '{
    "debug": true,
    "log_level": "DEBUG",
    "hot_reload": true
  }'
```

## Service Interactions

```
+------------------+
|   ConfigStore    | <--- L01 Data Layer (PostgreSQL)
|     (L01)        |
+--------+---------+
         |
   Used by all layers for:
         |
         v
+------------------+     +-------------------+     +------------------+
|  ModelGateway    |     |  PlanningService  |     |    FleetManager  |
|     (L04)        |     |      (L05)        |     |       (L02)      |
+------------------+     +-------------------+     +------------------+
         |
         v
+------------------+     +-------------------+
|  DashboardService|     |   WebSocketGateway|
|     (L10)        |     |       (L10)       |
+------------------+     +-------------------+
```

**Common consumers:**
- **ModelGateway (L04)**: Model routing preferences, API keys
- **PlanningService (L05)**: Planning strategy defaults
- **FleetManager (L02)**: Scaling thresholds
- **DashboardService (L10)**: UI preferences
- **Any service**: Feature flags, environment config

## Version Tracking

Each update automatically increments the version:

```bash
# First set - version 1
curl -X PUT http://localhost:8011/config/test/example \
  -H "Content-Type: application/json" \
  -d '{"setting": "initial"}'
# Response: {"version": 1, ...}

# Update - version 2
curl -X PUT http://localhost:8011/config/test/example \
  -H "Content-Type: application/json" \
  -d '{"setting": "updated"}'
# Response: {"version": 2, ...}
```

This enables:
- Change detection (check if version changed)
- Audit trail (when was it last modified)
- Conflict detection (optimistic locking patterns)

## Execution Examples

```bash
# Get a specific configuration
curl http://localhost:8011/config/models/claude-opus

# Set a configuration (creates or updates)
curl -X PUT http://localhost:8011/config/platform/settings \
  -H "Content-Type: application/json" \
  -d '{
    "max_concurrent_agents": 10,
    "default_timeout": 30000,
    "logging": {
      "level": "INFO",
      "format": "json"
    }
  }'

# List all configurations in a namespace
curl http://localhost:8011/config/platform

# Check if a config exists (returns 404 if not)
curl -I http://localhost:8011/config/missing/key
```

## Implementation Status

| Component | Status |
|-----------|--------|
| Get Config | Complete |
| Set Config (Upsert) | Complete |
| List by Namespace | Complete |
| Version Tracking | Complete |
| PostgreSQL Integration | Complete |
| API Routes | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Delete Config | Medium | Add delete endpoint for removing configs |
| Version History | Low | Store previous versions for rollback |
| Config Validation | Low | Schema validation for known namespaces |
| Config Watch | Low | WebSocket/SSE for config change notifications |
| Bulk Operations | Low | Set/get multiple configs at once |
| Encryption | Low | Encrypt sensitive config values at rest |

## Strengths

- **Simple API** - Familiar key-value semantics
- **Namespacing** - Clean organization by service/feature
- **Version tracking** - Built-in change auditing
- **Upsert semantics** - No need to check existence before setting
- **JSON values** - Store complex nested configuration

## Weaknesses

- **No delete operation** - Cannot remove configs (only update)
- **No history** - Old versions are overwritten, not stored
- **No caching** - Every read hits PostgreSQL
- **No validation** - Any JSON value is accepted
- **No notifications** - Services must poll for changes

## Best Practices

### Namespace Conventions
Use consistent namespace naming:
- `services/*` - Service-specific settings
- `features/*` - Feature flags
- `models/*` - Model configurations
- `env/*` - Environment settings
- `users/*` - User preferences

### Key Naming
Use descriptive, hierarchical keys:
- `claude-opus` - Model identifier
- `rate-limits` - Feature area
- `default-timeout` - Specific setting

### Value Structure
Keep values self-contained:
```json
{
  "enabled": true,
  "settings": {
    "timeout": 30000,
    "retries": 3
  },
  "metadata": {
    "updated_by": "admin",
    "reason": "Performance tuning"
  }
}
```

## Source Files

- Service: `platform/src/L01_data_layer/services/config_store.py`
- Models: `platform/src/L01_data_layer/models/config.py`
- Routes: `platform/src/L01_data_layer/routers/config.py`

## Related Services

- AgentRegistry (L01) - Agent metadata (different from agent config)
- EventStore (L01) - Event sourcing for audit trails
- StateManager (L02) - Runtime state (different from persistent config)
- SemanticCache (L04) - Caching layer (could cache configs)

---
*Generated: 2026-01-24 | Platform Services Documentation*

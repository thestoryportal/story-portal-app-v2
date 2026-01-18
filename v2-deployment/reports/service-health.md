# Service Health Report
Generated: $(date)

## Infrastructure Services

| Service | Port | Status |
|---------|------|--------|
| PostgreSQL | 5432 | ✓ Running |
| Redis | 6379 | ✓ Running |
| Ollama | 11434 | ✓ Running |

## Application Layers

| Layer | Port | Status |
|-------|------|--------|
| L01 Data Layer | 8001 | ✗ Not Deployed |
| L02 Runtime | 8002 | ✗ Not Deployed |
| L03 Tool Execution | 8003 | ✗ Not Deployed |
| L04 Model Gateway | 8004 | ✗ Not Deployed |
| L05 Planning | 8005 | ✗ Not Deployed |
| L06 Evaluation | 8006 | ✗ Not Deployed |
| L07 Learning | 8007 | ✗ Not Deployed |
| L09 API Gateway | 8009 | ✗ Not Deployed |
| L10 Human Interface | 8010 | ✗ Not Deployed |
| L11 Integration | 8011 | ✗ Not Deployed |

## Monitoring

| Service | Port | Status |
|---------|------|--------|
| Prometheus | 9090 | ✗ Not Started |
| Grafana | 3000 | ✗ Not Started |

## Notes

- Infrastructure services (PostgreSQL, Redis, Ollama) are running
- Application layers not yet implemented (missing main.py files)
- Docker Compose build failed due to macOS extended attributes (._ files)
- Fallback startup script created at: v2-deployment/scripts/start-services.sh

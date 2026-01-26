# Monitoring Stack Validation

## Prometheus
Prometheus Server is Healthy.

### Prometheus Targets
Active Targets: 4/16
  - cadvisor: up
  - l01-data-layer: down
  - l02-runtime: down
  - l03-tool-execution: down
  - l04-model-gateway: down
  - l05-planning: down
  - l06-evaluation: down
  - l07-learning: down
  - l09-api-gateway: down
  - l10-human-interface: down

## Grafana
{
  "database": "ok",
  "version": "12.3.1",
  "commit": "3a1c80ca7ce612f309fdc99338dd3c5e486339be"
}
## Exporters
### Postgres Exporter (9187)
# HELP go_gc_duration_seconds A summary of the wall-time pause (stop-the-world) duration in garbage collection cycles.
# TYPE go_gc_duration_seconds summary

### Redis Exporter (9121)
# HELP process_cpu_seconds_total Total user and system CPU time spent in seconds.
# TYPE process_cpu_seconds_total counter

## Monitoring Containers
NAMES                       STATUS
agentic-node-exporter       Restarting (2) 14 seconds ago
agentic-grafana             Up 33 minutes
agentic-prometheus          Up 33 minutes
agentic-redis-exporter      Up 33 minutes
agentic-cadvisor            Up 33 minutes (healthy)
agentic-postgres-exporter   Up 33 minutes

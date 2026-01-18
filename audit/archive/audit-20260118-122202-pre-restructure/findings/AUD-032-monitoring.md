# Monitoring Stack Validation
## Prometheus
Prometheus Server is Healthy.

### Prometheus Targets
Active Targets: 5/5
  - cadvisor: up
  - node-exporter: up
  - postgres: up
  - prometheus: up
  - redis: up

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
go_gc_duration_seconds{quantile="0"} 3.7854e-05
go_gc_duration_seconds{quantile="0.25"} 0.000227317
go_gc_duration_seconds{quantile="0.5"} 0.000430627

### Redis Exporter (9121)
# HELP process_cpu_seconds_total Total user and system CPU time spent in seconds.
# TYPE process_cpu_seconds_total counter
process_cpu_seconds_total 3.32
# HELP process_max_fds Maximum number of open file descriptors.
# TYPE process_max_fds gauge

### cAdvisor (8080)
# HELP cadvisor_version_info A metric with a constant '1' value labeled by kernel version, OS version, docker version, cadvisor version & cadvisor revision.
# TYPE cadvisor_version_info gauge
cadvisor_version_info{cadvisorRevision="f5bec374",cadvisorVersion="v0.55.1",dockerVersion="",kernelVersion="6.12.54-linuxkit",osVersion="Alpine Linux v3.22"} 1
# HELP container_blkio_device_usage_total Blkio Device bytes usage
# TYPE container_blkio_device_usage_total counter

## Monitoring Containers
NAMES                       STATUS
agentic-redis-exporter      Up 54 minutes
agentic-postgres-exporter   Up 54 minutes
agentic-grafana             Up 54 minutes
agentic-prometheus          Up 54 minutes
agentic-cadvisor            Up 54 minutes (healthy)
agentic-node-exporter       Up 54 minutes

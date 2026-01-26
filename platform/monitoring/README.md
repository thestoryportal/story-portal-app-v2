# Monitoring & Alerting Configuration

## Overview

This directory contains Prometheus and Alertmanager configurations for monitoring the V2 platform.

## Files

- `prometheus-alerts.yml` - Alert rules for all platform components
- `alertmanager-config.yml` - Alert routing and notification configuration
- `alert-templates.tmpl` - Notification templates for Slack, email, and PagerDuty

## Quick Start

### 1. Set Environment Variables

```bash
# Create .env file for secrets
cat > platform/monitoring/.env << EOF
SMTP_PASSWORD=your-smtp-password
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
PAGERDUTY_SERVICE_KEY_CRITICAL=your-pagerduty-key
PAGERDUTY_SERVICE_KEY_SECURITY=your-security-pagerduty-key
EOF
```

### 2. Deploy Prometheus with Alerts

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

# Load alert rules
rule_files:
  - '/etc/prometheus/prometheus-alerts.yml'

# Alertmanager configuration
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - 'alertmanager:9093'

# Scrape configs for all services
scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'l01-data-layer'
    static_configs:
      - targets: ['l01-data-layer:8001']

  # ... add all other services
```

### 3. Deploy Alertmanager

```bash
# Create Docker volume for Alertmanager data
docker volume create alertmanager-data

# Run Alertmanager
docker run -d \
  --name alertmanager \
  -p 9093:9093 \
  -v $(pwd)/alertmanager-config.yml:/etc/alertmanager/alertmanager.yml \
  -v $(pwd)/alert-templates.tmpl:/etc/alertmanager/templates/default.tmpl \
  -v alertmanager-data:/alertmanager \
  --env-file .env \
  prom/alertmanager:latest \
  --config.file=/etc/alertmanager/alertmanager.yml \
  --storage.path=/alertmanager
```

### 4. Verify Configuration

```bash
# Check Prometheus alerts
curl http://localhost:9090/api/v1/rules | jq

# Check Alertmanager config
curl http://localhost:9093/api/v1/status | jq

# Test alert routing
curl -X POST http://localhost:9093/api/v1/alerts -d '[{
  "labels": {
    "alertname": "TestAlert",
    "severity": "warning"
  },
  "annotations": {
    "summary": "This is a test alert"
  }
}]'
```

## Alert Categories

### Critical Alerts
- **Severity:** critical
- **Response Time:** Immediate (< 5 minutes)
- **Notification:** PagerDuty + Slack + Email
- **Examples:** ServiceDown, CriticalAPIErrorRate, PostgreSQLDown

### High Priority Alerts
- **Severity:** warning
- **Response Time:** < 30 minutes
- **Notification:** Slack + Email
- **Examples:** HighAPILatency, HighDatabaseConnections, HighCPUUsage

### Info Alerts
- **Severity:** info
- **Response Time:** Best effort
- **Notification:** Slack only
- **Examples:** HighAPITraffic, RateLimitExceeded

## Alert Routing

### By Severity
- **Critical** → PagerDuty + #platform-critical + oncall@example.com
- **Warning** → #platform-warnings
- **Info** → #platform-info

### By Category
- **database** → #database-alerts + database-team@example.com
- **security** → PagerDuty + #security-alerts + security@example.com
- **infrastructure** → #ops-alerts + ops@example.com
- **performance** → #performance-alerts
- **business** → #product-metrics + product@example.com

## Notification Channels

### Slack
Configure webhook URLs in environment variables:
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

Channels:
- `#platform-critical` - Critical alerts requiring immediate action
- `#platform-alerts` - All general alerts
- `#platform-warnings` - Warning-level alerts
- `#platform-info` - Informational alerts
- `#database-alerts` - Database-specific alerts
- `#security-alerts` - Security-specific alerts
- `#ops-alerts` - Infrastructure alerts
- `#performance-alerts` - Performance metrics
- `#product-metrics` - Business metrics

### PagerDuty
Configure service keys for different alert types:
```bash
PAGERDUTY_SERVICE_KEY_CRITICAL=your-critical-service-key
PAGERDUTY_SERVICE_KEY_SECURITY=your-security-service-key
```

Integration URL: `https://events.pagerduty.com/v2/enqueue`

### Email
Configure SMTP settings:
```bash
SMTP_PASSWORD=your-smtp-password
```

Recipients:
- `oncall@example.com` - Critical alerts
- `database-team@example.com` - Database alerts
- `security@example.com` - Security alerts
- `ops@example.com` - Infrastructure alerts
- `product@example.com` - Business metrics

## Alert Inhibition

Alertmanager automatically suppresses redundant alerts:

1. **Warning suppressed when Critical fires** for the same alert
2. **API latency warnings suppressed** when service is down
3. **Database connection warnings suppressed** when database is down
4. **Container resource alerts suppressed** when container is restarting

## Time-Based Muting

### Business Hours
Monday-Friday 9am-5pm EST
- Full alerting enabled
- All severities trigger notifications

### Off Hours
Nights and weekends
- Only critical alerts trigger pages
- Warnings go to Slack only

### Maintenance Window
Sunday 2am-4am EST
- All alerts muted except critical
- Notifications queued until maintenance completes

## Alert Metrics

View alert statistics in Prometheus:
```promql
# Firing alerts by severity
ALERTS{alertstate="firing"} by (severity)

# Alert firing duration
ALERTS_FOR_STATE{alertstate="firing"}

# Alerts by job
ALERTS{alertstate="firing"} by (job)
```

## Testing Alerts

### Test Individual Alert
```bash
# Trigger a test alert
amtool alert add \
  alertname="TestAlert" \
  severity="warning" \
  summary="This is a test" \
  description="Testing alert routing" \
  --alertmanager.url=http://localhost:9093
```

### Test Alert Routing
```bash
# Check which receiver will handle an alert
amtool config routes test \
  --config.file=alertmanager-config.yml \
  severity=critical category=database
```

### Silence Alerts
```bash
# Silence all alerts for maintenance
amtool silence add \
  alertname=.* \
  --duration=2h \
  --comment="Planned maintenance" \
  --alertmanager.url=http://localhost:9093

# Silence specific alert
amtool silence add \
  alertname=HighCPUUsage \
  instance=server-01 \
  --duration=1h \
  --alertmanager.url=http://localhost:9093
```

## Runbook Links

Each alert includes a runbook_url annotation. Create runbooks at:
- https://docs.example.com/runbooks/service-down
- https://docs.example.com/runbooks/high-latency
- https://docs.example.com/runbooks/high-error-rate
- https://docs.example.com/runbooks/postgresql-down
- https://docs.example.com/runbooks/redis-down
- https://docs.example.com/runbooks/high-db-connections
- https://docs.example.com/runbooks/replication-lag
- https://docs.example.com/runbooks/failed-logins
- https://docs.example.com/runbooks/brute-force
- https://docs.example.com/runbooks/high-cpu
- https://docs.example.com/runbooks/high-memory
- https://docs.example.com/runbooks/high-disk
- https://docs.example.com/runbooks/container-restart
- https://docs.example.com/runbooks/container-oom
- https://docs.example.com/runbooks/consul-down
- https://docs.example.com/runbooks/etcd-down
- https://docs.example.com/runbooks/backup-failed

## Dashboard Links

Each alert includes a dashboard_url annotation. Create dashboards in Grafana:
- https://grafana.example.com/d/services - Service overview
- https://grafana.example.com/d/api - API metrics
- https://grafana.example.com/d/database - Database metrics
- https://grafana.example.com/d/infrastructure - Infrastructure metrics
- https://grafana.example.com/d/security - Security metrics

## Troubleshooting

### Alerts Not Firing

1. Check Prometheus is evaluating rules:
```bash
curl http://localhost:9090/api/v1/rules | jq '.data.groups[] | select(.name=="service_availability")'
```

2. Check for syntax errors:
```bash
promtool check rules prometheus-alerts.yml
```

3. Verify scrape targets are up:
```bash
curl http://localhost:9090/api/v1/targets | jq
```

### Alerts Not Routing

1. Check Alertmanager config:
```bash
amtool config routes --config.file=alertmanager-config.yml
```

2. Check active silences:
```bash
amtool silence query --alertmanager.url=http://localhost:9093
```

3. Check Alertmanager logs:
```bash
docker logs alertmanager
```

### Too Many Alerts

1. Review and adjust thresholds in `prometheus-alerts.yml`
2. Add inhibition rules to suppress related alerts
3. Increase evaluation intervals for non-critical alerts
4. Use time-based muting during known high-load periods

## Alert Tuning

### Adjusting Thresholds

Edit `prometheus-alerts.yml` and modify expressions:

```yaml
# Original: 500ms threshold
expr: histogram_quantile(0.95, ...) > 0.5

# Adjusted: 1 second threshold
expr: histogram_quantile(0.95, ...) > 1.0
```

### Changing Notification Frequency

Edit `alertmanager-config.yml`:

```yaml
# Original: repeat every 4 hours
repeat_interval: 4h

# Adjusted: repeat every 12 hours
repeat_interval: 12h
```

### Adding New Alerts

1. Add alert rule to `prometheus-alerts.yml`
2. Test with `promtool check rules prometheus-alerts.yml`
3. Reload Prometheus: `curl -X POST http://localhost:9090/-/reload`
4. Verify in UI: http://localhost:9090/alerts

## Best Practices

1. **Keep alerts actionable** - Every alert should require human action
2. **Avoid alert fatigue** - Too many alerts = ignored alerts
3. **Set appropriate thresholds** - Balance between false positives and missed issues
4. **Include context** - Summary, description, and runbook links
5. **Test regularly** - Verify alert routing works before you need it
6. **Review and tune** - Adjust thresholds based on actual behavior
7. **Document runbooks** - Clear steps for resolving each alert
8. **Use inhibition** - Suppress redundant alerts automatically

## Metrics to Monitor

### Service Metrics
- `up` - Service availability (0 = down, 1 = up)
- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request latency

### Database Metrics
- `pg_up` - PostgreSQL availability
- `pg_stat_activity_count` - Active connections
- `pg_replication_lag` - Replication lag in seconds

### Infrastructure Metrics
- `node_cpu_seconds_total` - CPU usage
- `node_memory_MemAvailable_bytes` - Available memory
- `node_filesystem_avail_bytes` - Available disk space

### Business Metrics
- `active_users_count` - Active user sessions
- `tasks_total` - Total tasks created
- `tasks_failed_total` - Failed tasks

## Support

For questions or issues with monitoring:
- **Documentation:** https://docs.example.com/monitoring
- **Slack:** #platform-monitoring
- **Email:** monitoring@example.com
- **On-call:** Use PagerDuty escalation

---

**Last Updated:** 2026-01-18
**Version:** 2.0

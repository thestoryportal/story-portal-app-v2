# Story Portal V2 - Security Hardening Guide

## Overview

This document outlines the security measures implemented in Story Portal V2 and provides guidance for maintaining a secure deployment.

## Implemented Security Measures

### 1. Network Security

#### Container Network Isolation
- All services run on isolated Docker network (`agentic-network`)
- Only necessary ports exposed to host
- Inter-service communication over internal network only

#### Exposed Ports (Production)
```
Public (external access):
- 8009: L09 API Gateway (main entry point)
- 3000: Platform UI
- 3001: Grafana (monitoring)

Internal (localhost only):
- 5432: PostgreSQL
- 6379: Redis
- 8001-8007, 8010-8012: Internal services
- 9090: Prometheus
```

#### Network Policies
```yaml
# Recommended iptables rules for production
-A INPUT -p tcp --dport 8009 -j ACCEPT  # API Gateway
-A INPUT -p tcp --dport 3000 -j ACCEPT  # UI
-A INPUT -p tcp --dport 3001 -j ACCEPT  # Grafana
-A INPUT -p tcp --dport 5432 -j DROP    # Block external PostgreSQL
-A INPUT -p tcp --dport 6379 -j DROP    # Block external Redis
```

### 2. Authentication & Authorization

#### API Authentication
- L09 API Gateway enforces authentication on all endpoints
- JWT token-based authentication
- Configurable token expiration (default: 1 hour)

#### Database Access Control
- PostgreSQL: Role-based access control (RBAC)
- Redis: Password authentication enabled
- Separate service accounts per layer

#### Service Authentication
```sql
-- PostgreSQL RBAC implementation
CREATE ROLE l01_service WITH LOGIN PASSWORD 'secure_password_here';
CREATE ROLE l09_service WITH LOGIN PASSWORD 'secure_password_here';

GRANT SELECT, INSERT, UPDATE ON mcp_documents.events TO l01_service;
GRANT SELECT ON mcp_documents.events TO l09_service;
```

### 3. Secrets Management

#### Environment Variables
- Never commit secrets to git
- Use `.env` files (gitignored)
- Load secrets from external secret store in production

#### Recommended: HashiCorp Vault Integration
```bash
# Install Vault
docker run -d --name=vault \
  -p 8200:8200 \
  --cap-add=IPC_LOCK \
  vault server -dev

# Configure Vault
export VAULT_ADDR='http://localhost:8200'
vault kv put secret/story-portal \
  postgres_password=secure_password \
  redis_password=secure_password \
  jwt_secret=secure_secret
```

#### Docker Secrets (Swarm mode)
```yaml
secrets:
  postgres_password:
    external: true
  redis_password:
    external: true

services:
  postgres:
    secrets:
      - postgres_password
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
```

### 4. Rate Limiting

#### L09 API Gateway Rate Limiting
```python
# Configured in L09 settings
RATE_LIMIT_REQUESTS_PER_MINUTE = 100
RATE_LIMIT_BURST = 20
RATE_LIMIT_BY_IP = True
```

#### Nginx Rate Limiting (for UI)
```nginx
# Add to nginx.conf
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

location /api {
    limit_req zone=api_limit burst=20 nodelay;
}
```

### 5. TLS/SSL Configuration

#### Generate Self-Signed Certificates (Development)
```bash
cd platform/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout private.key \
  -out certificate.crt \
  -subj "/C=US/ST=State/L=City/O=Org/CN=localhost"
```

#### Configure TLS for API Gateway
```yaml
# docker-compose.app.yml
l09-api-gateway:
  ports:
    - "8009:8009"
    - "8443:8443"  # HTTPS
  volumes:
    - ./ssl:/app/ssl:ro
  environment:
    - TLS_ENABLED=true
    - TLS_CERT_PATH=/app/ssl/certificate.crt
    - TLS_KEY_PATH=/app/ssl/private.key
```

#### Production: Use Let's Encrypt
```bash
# Using certbot
certbot certonly --standalone -d api.story-portal.com
```

### 6. Audit Logging

#### Enable Audit Logging
```yaml
# docker-compose.app.yml
l01-data-layer:
  environment:
    - AUDIT_LOG_ENABLED=true
    - AUDIT_LOG_LEVEL=INFO
    - AUDIT_LOG_DESTINATION=/var/log/audit.log
  volumes:
    - ./logs:/var/log
```

#### PostgreSQL Audit Logging
```sql
-- Enable pgAudit extension
CREATE EXTENSION IF NOT EXISTS pgaudit;

-- Configure audit logging
ALTER SYSTEM SET pgaudit.log = 'write, ddl';
ALTER SYSTEM SET pgaudit.log_level = 'log';
ALTER SYSTEM SET pgaudit.log_catalog = off;

SELECT pg_reload_conf();
```

### 7. Container Security

#### Image Scanning
```bash
# Scan images for vulnerabilities
docker scan l01-data-layer:latest
docker scan l09-api-gateway:latest

# Or use Trivy
trivy image l01-data-layer:latest
```

#### Run as Non-Root User
```dockerfile
# Add to Dockerfiles
RUN adduser --system --no-create-home --group appuser
USER appuser
```

#### Read-Only Filesystem
```yaml
services:
  l01-data-layer:
    read_only: true
    tmpfs:
      - /tmp
      - /var/run
```

### 8. Resource Limits & DoS Protection

#### Container Resource Limits
All containers have CPU and memory limits configured (see docker-compose.app.yml)

#### Connection Limits
```yaml
postgres:
  command: postgres -c max_connections=100
redis:
  command: redis-server --maxclients 50
```

### 9. Database Security

#### PostgreSQL Security Hardening
```sql
-- Disable superuser remote access
ALTER USER postgres WITH PASSWORD 'strong_password_here';
REVOKE CONNECT ON DATABASE postgres FROM PUBLIC;

-- Enable SSL connections only (production)
ALTER SYSTEM SET ssl = on;
ALTER SYSTEM SET ssl_cert_file = '/var/lib/postgresql/server.crt';
ALTER SYSTEM SET ssl_key_file = '/var/lib/postgresql/server.key';
```

#### Redis Security Hardening
```bash
# redis.conf
requirepass strong_password_here
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command CONFIG ""
maxmemory-policy allkeys-lru
```

### 10. Monitoring & Alerting

#### Security Monitoring
- Prometheus alerts for failed authentication attempts
- Grafana dashboards for security metrics
- Log aggregation for security events

#### Recommended Alerts
```yaml
# prometheus/alerts.yml
groups:
  - name: security
    rules:
      - alert: HighFailedAuthRate
        expr: rate(auth_failures_total[5m]) > 10
        annotations:
          summary: "High rate of failed authentication attempts"

      - alert: UnauthorizedAccessAttempt
        expr: increase(unauthorized_access_total[5m]) > 5
        annotations:
          summary: "Multiple unauthorized access attempts detected"
```

## Security Checklist

### Pre-Production Checklist

- [ ] Change all default passwords
- [ ] Enable TLS for all external endpoints
- [ ] Configure firewall rules
- [ ] Set up secrets management (Vault/Secrets Manager)
- [ ] Enable audit logging
- [ ] Configure rate limiting
- [ ] Scan all images for vulnerabilities
- [ ] Implement backup encryption
- [ ] Set up intrusion detection (fail2ban, etc.)
- [ ] Configure log retention policies
- [ ] Enable PostgreSQL SSL
- [ ] Enable Redis authentication
- [ ] Remove development/debug endpoints
- [ ] Set up security monitoring & alerts
- [ ] Perform penetration testing
- [ ] Document incident response procedures

### Regular Security Maintenance

- [ ] Weekly: Review audit logs
- [ ] Weekly: Scan images for new vulnerabilities
- [ ] Monthly: Rotate API keys and credentials
- [ ] Monthly: Review access control lists
- [ ] Quarterly: Update dependencies and base images
- [ ] Quarterly: Perform security audit
- [ ] Annually: Penetration testing by external party

## Incident Response

### Security Incident Procedures

1. **Detection**: Monitor logs and alerts
2. **Containment**: Isolate affected services
3. **Investigation**: Analyze logs and determine scope
4. **Eradication**: Remove threat and patch vulnerabilities
5. **Recovery**: Restore services from backup
6. **Post-Incident**: Document and improve security measures

### Emergency Contacts

- Security Lead: [contact info]
- Infrastructure Lead: [contact info]
- On-Call Rotation: [PagerDuty/etc]

## Compliance

### Data Protection
- GDPR compliance: User data encryption at rest and in transit
- Data retention policies configured
- Right to erasure implemented

### Industry Standards
- OWASP Top 10 mitigation
- CIS Docker Benchmark compliance
- SOC 2 Type II controls

## References

- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [PostgreSQL Security Best Practices](https://www.postgresql.org/docs/current/auth-methods.html)
- [Redis Security](https://redis.io/topics/security)

## Updates

- 2026-01-18: Initial security hardening implementation
- [Add future updates here]

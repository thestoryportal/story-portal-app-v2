# Security Policy - Story Portal Platform V2

**Version:** 2.0.0
**Last Updated:** 2026-01-18

---

## Table of Contents

1. [Reporting Security Vulnerabilities](#reporting-security-vulnerabilities)
2. [Security Hardening Checklist](#security-hardening-checklist)
3. [Authentication & Authorization](#authentication--authorization)
4. [Network Security](#network-security)
5. [Data Security](#data-security)
6. [Container Security](#container-security)
7. [Secrets Management](#secrets-management)
8. [Monitoring & Incident Response](#monitoring--incident-response)

---

## Reporting Security Vulnerabilities

If you discover a security vulnerability in the Story Portal Platform, please report it responsibly:

**DO NOT** create a public GitHub issue for security vulnerabilities.

### Reporting Process

1. **Email:** security@your-org.com
2. **Include:**
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
   - Suggested remediation (if available)

3. **Expected Response Time:**
   - Acknowledgment: Within 48 hours
   - Initial assessment: Within 7 days
   - Resolution timeline: Depends on severity

### Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.0.x   | ✅ Yes             |
| 1.x     | ❌ No (deprecated) |

---

## Security Hardening Checklist

### Production Deployment Checklist

- [ ] **Authentication**
  - [ ] JWT secrets are strong random values (256-bit minimum)
  - [ ] API keys are UUID v4 or similar cryptographic strength
  - [ ] Token expiration configured (access: 15min, refresh: 7 days)
  - [ ] Rate limiting enabled on L09 API Gateway

- [ ] **Network Security**
  - [ ] TLS/HTTPS enabled (Let's Encrypt or valid certificate)
  - [ ] Internal Docker network isolated from public
  - [ ] Only L09 (Gateway) and L10 (UI) exposed externally
  - [ ] Firewall rules restrict access to ports 8001-8012

- [ ] **Database Security**
  - [ ] PostgreSQL password is strong (not default "postgres")
  - [ ] Database accessible only from Docker network
  - [ ] SSL/TLS connections enforced for PostgreSQL
  - [ ] Regular backups configured (daily minimum)

- [ ] **Redis Security**
  - [ ] Redis password configured (requirepass)
  - [ ] Redis accessible only from Docker network
  - [ ] Dangerous commands disabled (FLUSHDB, FLUSHALL, KEYS)

- [ ] **Container Security**
  - [ ] Containers run as non-root user
  - [ ] Resource limits configured (CPU, memory)
  - [ ] Read-only root filesystems where possible
  - [ ] Security updates applied regularly

- [ ] **Secrets Management**
  - [ ] No secrets in docker-compose.yml or source code
  - [ ] Environment variables from Docker secrets or vault
  - [ ] .env files in .gitignore
  - [ ] Secrets rotation policy in place

- [ ] **Monitoring**
  - [ ] Security event logging enabled
  - [ ] Failed authentication attempts monitored
  - [ ] Unusual traffic patterns detected
  - [ ] Security metrics in Grafana dashboards

---

## Authentication & Authorization

### JWT Authentication (L09 API Gateway)

**Token Generation:**
```bash
# Get JWT token
curl -X POST http://localhost:8009/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "password"}'
```

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "Bearer",
  "expires_in": 900
}
```

**Using Token:**
```bash
curl -H "Authorization: Bearer eyJhbGc..." \
  http://localhost:8009/api/v1/agents
```

### API Key Authentication

**Generate API Key:**
```bash
curl -X POST http://localhost:8009/auth/api-keys \
  -H "Authorization: Bearer <admin-token>" \
  -d '{"name": "my-app", "scopes": ["read:agents", "write:tasks"]}'
```

**Use API Key:**
```bash
curl -H "X-API-Key: <api-key>" \
  http://localhost:8009/api/v1/agents
```

### Role-Based Access Control (RBAC)

**Roles:**
- `admin`: Full access to all resources
- `developer`: Read/write agents, tasks, runs
- `viewer`: Read-only access
- `service`: Inter-service communication (internal)

**Configuring Roles:**
Edit `/platform/src/L09_api_gateway/config/rbac.yml`

---

## Network Security

### Docker Network Isolation

**Internal Network (agentic-network):**
- L01-L07: Backend services (not exposed externally)
- PostgreSQL, Redis: Data stores (internal only)
- Prometheus, Grafana: Monitoring (restrict access)

**External Access:**
- L09 API Gateway: Port 8009 (HTTPS only in production)
- L10 Human Interface: Port 8010 (HTTPS only in production)

### TLS/HTTPS Configuration

**Production Setup:**

1. **Obtain SSL Certificate:**
   ```bash
   # Using Let's Encrypt
   certbot certonly --standalone -d api.yourdomain.com
   certbot certonly --standalone -d portal.yourdomain.com
   ```

2. **Configure Nginx (Reverse Proxy):**
   ```nginx
   server {
       listen 443 ssl;
       server_name api.yourdomain.com;

       ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

       location / {
           proxy_pass http://localhost:8009;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

3. **Force HTTPS Redirect:**
   ```nginx
   server {
       listen 80;
       server_name api.yourdomain.com;
       return 301 https://$server_name$request_uri;
   }
   ```

### Firewall Rules

**Recommended iptables rules:**
```bash
# Allow SSH (if needed)
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# Allow HTTPS
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Block direct access to application ports
iptables -A INPUT -p tcp --dport 8001:8012 -j DROP

# Allow established connections
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
```

---

## Data Security

### Database Encryption

**At-Rest Encryption:**
- Use encrypted volumes for PostgreSQL data
- Enable PostgreSQL `ssl` mode for connections

**In-Transit Encryption:**
```bash
# PostgreSQL SSL configuration
docker exec agentic-postgres psql -U postgres -c "ALTER SYSTEM SET ssl = on;"
docker restart agentic-postgres
```

**Connection String with SSL:**
```
postgresql://user:pass@postgres:5432/db?sslmode=require
```

### Sensitive Data Handling

**DO:**
- Hash passwords with bcrypt (cost factor ≥ 12)
- Encrypt API keys before storing
- Use parameterized queries (SQL injection prevention)
- Sanitize all user inputs

**DON'T:**
- Store plain-text passwords
- Log sensitive data (passwords, tokens, PII)
- Return sensitive errors to clients
- Trust client-side validation

### Data Backup Security

```bash
# Encrypted backup
pg_dump -U postgres agentic_platform | gpg --encrypt --recipient backup@your-org.com > backup.sql.gpg

# Secure transfer
scp backup.sql.gpg backup-server:/backups/
```

---

## Container Security

### Run as Non-Root User

**Dockerfile example:**
```dockerfile
FROM python:3.11-slim

# Create non-root user
RUN useradd -m -u 1000 appuser

# Install dependencies as root
COPY requirements.txt .
RUN pip install -r requirements.txt

# Switch to non-root user
USER appuser

# Copy application
COPY --chown=appuser:appuser . /app
WORKDIR /app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### Resource Limits

**Already configured in docker-compose.v2.yml** ✅

### Security Scanning

```bash
# Scan images for vulnerabilities
docker scan l01-data-layer:latest

# Use Trivy for comprehensive scanning
trivy image l01-data-layer:latest
```

---

## Secrets Management

### ✅ P1-04: Secrets Management Implementation (2026-01-18)

**Status:** COMPLETE - All secrets have been removed from version control and documented.

### Environment Configuration Template

A comprehensive `.env.example` template has been created at `platform/.env.example` with:
- All configuration variables documented
- Placeholder values for secrets (CHANGE_ME)
- Instructions for generating strong secrets
- Separate sections for different service types

**Setup Process:**
```bash
# 1. Copy example configuration
cp platform/.env.example platform/.env

# 2. Generate secure secrets
openssl rand -hex 32  # For JWT_SECRET (256 bits)
openssl rand -hex 32  # For API_KEY_SECRET
openssl rand -hex 32  # For SESSION_SECRET

# 3. Update .env with generated secrets
# Edit platform/.env and replace all CHANGE_ME values

# 4. Verify .env is in .gitignore
git check-ignore platform/.env  # Should output: platform/.env
```

### Environment Variables (Development)

For local development, use `.env` file (NEVER commit to git):

```bash
# Database
POSTGRES_PASSWORD=<strong-password>
DATABASE_URL=postgresql://postgres:<password>@localhost:5432/agentic_platform

# Authentication
JWT_SECRET=<64-hex-chars>
API_KEY_SECRET=<64-hex-chars>
SESSION_SECRET=<64-hex-chars>

# Redis
REDIS_PASSWORD=<strong-password>  # Optional for dev

# Monitoring
GF_SECURITY_ADMIN_PASSWORD=<strong-password>
```

### Docker Secrets (Production - Recommended)

For production deployments using Docker Swarm:

```bash
# Create secrets
echo "strong-jwt-secret" | docker secret create jwt_secret -
echo "strong-db-password" | docker secret create postgres_password -
echo "strong-api-key" | docker secret create api_key_secret -

# Use in docker-compose.yml
secrets:
  jwt_secret:
    external: true
  postgres_password:
    external: true

services:
  l09-api-gateway:
    secrets:
      - jwt_secret
    environment:
      - JWT_SECRET_FILE=/run/secrets/jwt_secret

  postgres:
    secrets:
      - postgres_password
    environment:
      - POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password
```

### HashiCorp Vault (Production - Enterprise)

For production deployments with HashiCorp Vault:

```bash
# Store secrets in Vault
vault kv put secret/story-portal/postgres password="<strong-password>"
vault kv put secret/story-portal/jwt secret="<strong-jwt-secret>"
vault kv put secret/story-portal/api-keys l09="<api-key>"

# Retrieve in application
import hvac
client = hvac.Client(url='http://vault:8200', token='<token>')
postgres_password = client.secrets.kv.v2.read_secret_version(
    path='postgres',
    mount_point='secret/story-portal'
)['data']['data']['password']
```

### AWS Secrets Manager (Production - AWS)

For AWS deployments:

```python
import boto3
from botocore.exceptions import ClientError

def get_secret(secret_name):
    client = boto3.client('secretsmanager', region_name='us-west-2')
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    except ClientError as e:
        raise e

# Usage
secrets = get_secret('story-portal/database')
DATABASE_URL = f"postgresql://{secrets['username']}:{secrets['password']}@{secrets['host']}:5432/agentic_platform"
```

### Secrets Rotation Policy

- **JWT Secrets:** Rotate quarterly (every 90 days)
- **Database Passwords:** Rotate quarterly (every 90 days)
- **API Keys:** Rotate on compromise or annually
- **SSL/TLS Certificates:** Auto-renewal (Let's Encrypt 90 days)
- **Monitoring Passwords:** Rotate bi-annually

**Rotation Procedure:**
```bash
# 1. Generate new secret
NEW_SECRET=$(openssl rand -hex 32)

# 2. Update secrets manager
docker secret create postgres_password_v2 - <<< "$NEW_SECRET"

# 3. Update service configuration
docker service update --secret-rm postgres_password --secret-add postgres_password_v2 postgres

# 4. Verify service health
docker ps | grep postgres

# 5. Remove old secret (after verification period)
docker secret rm postgres_password
```

### Security Best Practices

**✅ Implemented:**
- `.env.example` template with no real secrets
- `.gitignore` updated to exclude all secret files
- SSL private keys excluded from version control
- Comprehensive secrets documentation

**⚠️ For Production:**
- Use secrets manager (Vault, AWS Secrets Manager, Docker Secrets)
- Enable secret rotation automation
- Implement secret access auditing
- Use different secrets per environment (dev/staging/prod)

---

## Monitoring & Incident Response

### Security Event Logging

**Key Events to Log:**
- Failed authentication attempts
- Unauthorized access attempts (401, 403 errors)
- Unusual API usage patterns
- Privilege escalation attempts
- Database connection failures

**Centralized Logging:**
```bash
# Configure structured logging in all services
import structlog

logger = structlog.get_logger()
logger.info("authentication_failed", username="user", ip="1.2.3.4", reason="invalid_password")
```

### Intrusion Detection

**Monitor for:**
- Brute force attacks (>10 failed logins in 5 minutes)
- SQL injection patterns in logs
- Unusual geographic locations
- Sudden spike in API requests

**Alert Configuration (Prometheus):**
```yaml
groups:
  - name: security_alerts
    rules:
      - alert: HighFailedAuthRate
        expr: rate(failed_auth_total[5m]) > 10
        annotations:
          summary: "High rate of failed authentication attempts"
```

### Incident Response Plan

1. **Detection:** Automated alerts + monitoring
2. **Containment:** Isolate affected services
3. **Analysis:** Review logs, identify attack vector
4. **Eradication:** Patch vulnerability, rotate secrets
5. **Recovery:** Restore services, verify integrity
6. **Post-Mortem:** Document incident, improve defenses

---

## Security Updates

### Update Strategy

```bash
# Regular updates (weekly)
docker-compose pull
docker-compose up -d

# Security patches (immediate)
docker build --no-cache -t l01-data-layer:latest platform/src/L01_data_layer
docker-compose up -d l01-data-layer
```

### Dependency Scanning

```bash
# Python dependencies
pip install safety
safety check -r requirements.txt

# Docker base images
docker pull python:3.11-slim
```

---

## Compliance

### GDPR Considerations

- User data retention policies
- Right to deletion implementation
- Data export functionality
- Privacy by design

### SOC 2 Compliance

- Access control logging
- Encryption at rest and in transit
- Regular security audits
- Incident response procedures

---

## Additional Resources

- **OWASP Top 10:** https://owasp.org/www-project-top-ten/
- **Docker Security:** https://docs.docker.com/engine/security/
- **PostgreSQL Security:** https://www.postgresql.org/docs/current/security.html
- **FastAPI Security:** https://fastapi.tiangolo.com/tutorial/security/

---

**Document Version:** 1.0.0
**Last Review:** 2026-01-18
**Next Review:** 2026-04-18

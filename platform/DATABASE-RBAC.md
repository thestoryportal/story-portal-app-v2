# PostgreSQL Role-Based Access Control (RBAC)

**Last Updated:** 2026-01-18
**Database:** agentic_platform
**PostgreSQL Version:** 16.11

## Overview

This document describes the Role-Based Access Control (RBAC) implementation for the Story Portal Platform PostgreSQL database. RBAC provides least-privilege access control, ensuring services only have the permissions they need.

## Security Principles

1. **Least Privilege:** Services only get minimum required permissions
2. **Role Separation:** Different roles for different access levels
3. **Defense in Depth:** Multiple layers of security
4. **Audit Trail:** All role actions can be logged
5. **Regular Review:** Quarterly access reviews recommended

## Database Roles

### 1. app_read (Read-Only Access)

**Purpose:** For services that only need to query data (analytics, reporting, read-only APIs)

**Permissions:**
- `CONNECT` to agentic_platform database
- `USAGE` on all schemas (public, l02_runtime, mcp_contexts, mcp_documents, shared)
- `SELECT` on all current and future tables
- `SELECT` on all current and future sequences

**Use Cases:**
- L02-L07 services (query only, no direct writes)
- L10 Human Interface (UI backend queries)
- L12 Service Hub (service discovery queries)
- Reporting and analytics tools
- Read-only dashboard applications

**Limitations:**
- ❌ Cannot INSERT, UPDATE, or DELETE data
- ❌ Cannot create or modify tables
- ❌ Cannot create or drop schemas
- ❌ Cannot manage roles or permissions

**Connection String:**
```
postgresql://app_read:<password>@postgres:5432/agentic_platform
```

### 2. app_write (Read-Write Access)

**Purpose:** For application services that need to modify data

**Permissions:**
- All permissions from `app_read` (inherits role)
- `INSERT`, `UPDATE`, `DELETE` on all current and future tables
- `USAGE`, `UPDATE` on all sequences (for auto-increment columns)

**Use Cases:**
- L01 Data Layer (primary data access layer)
- L11 Integration (cross-service data synchronization)
- Application services that manage user data
- Background jobs that process and update data

**Limitations:**
- ❌ Cannot create or modify table schemas
- ❌ Cannot drop tables or databases
- ❌ Cannot manage roles or permissions
- ❌ Cannot execute DDL statements (CREATE TABLE, ALTER TABLE, etc.)

**Connection String:**
```
postgresql://app_write:<password>@postgres:5432/agentic_platform
```

### 3. app_admin (Administrative Access)

**Purpose:** For database migrations, schema changes, maintenance operations

**Permissions:**
- `ALL PRIVILEGES` on agentic_platform database
- `ALL PRIVILEGES` on all schemas
- `ALL PRIVILEGES` on all current and future tables
- `ALL PRIVILEGES` on all current and future sequences
- `CREATEROLE` privilege (can create new roles)

**Use Cases:**
- Database migrations (Alembic, Flyway, etc.)
- Schema changes (CREATE TABLE, ALTER TABLE, etc.)
- Index creation and optimization
- Database maintenance operations
- Emergency database operations

**Limitations:**
- ⚠️ Should not be used for routine application operations
- ⚠️ Use with caution - has full database control
- ⚠️ Recommend time-limited access for production

**Connection String:**
```
postgresql://app_admin:<password>@postgres:5432/agentic_platform
```

## Role Hierarchy

```
postgres (Superuser)
    ↓
app_admin (Full DB control, DDL operations)
    ↓
app_write (INSERT, UPDATE, DELETE)
    ↓
app_read (SELECT only)
```

Role inheritance:
- `app_write` inherits all permissions from `app_read`
- `app_read` is the base role with minimum privileges

## Service-to-Role Mapping

### Recommended Assignments

| Service | Role | Rationale |
|---------|------|-----------|
| L01 Data Layer | app_write | Primary data access layer, needs write access |
| L02 Runtime | app_read | Queries runtime state, no direct writes |
| L03 Tool Execution | app_read | Queries tool definitions, execution via L01 |
| L04 Model Gateway | app_read | Queries model config, no direct writes |
| L05 Planning | app_read | Queries plans, updates via L01 |
| L06 Evaluation | app_read | Queries results, writes via L01 |
| L07 Learning | app_read | Queries learning data, writes via L01 |
| L09 API Gateway | app_read | Routing only, no database access typically |
| L10 Human Interface | app_read | UI backend, reads data for display |
| L11 Integration | app_write | Cross-service sync, needs write access |
| L12 Service Hub | app_read | Service discovery, reads service registry |
| Database Migrations | app_admin | Schema changes, DDL operations |
| Backup Scripts | app_read | Read-only for pg_dump |

### Configuration Examples

#### L01 Data Layer (app_write)

```python
# platform/src/L01_data_layer/config.py
import os

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://app_write:<password>@postgres:5432/agentic_platform'
)
```

#### L02-L07 Services (app_read)

```python
# platform/src/L02_runtime/config.py
import os

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://app_read:<password>@postgres:5432/agentic_platform'
)
```

#### Database Migrations (app_admin)

```bash
# migrations/.env
DATABASE_URL=postgresql://app_admin:<password>@postgres:5432/agentic_platform
```

## Setup Instructions

### Initial Setup

1. **Run RBAC Setup Script:**

```bash
cd /Volumes/Extreme\ SSD/projects/story-portal-app
docker exec -i agentic-postgres psql -U postgres -d agentic_platform < platform/scripts/setup-rbac.sql
```

2. **Generate Strong Passwords:**

```bash
# Generate passwords for each role
APP_READ_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
APP_WRITE_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
APP_ADMIN_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)

echo "app_read password: $APP_READ_PASSWORD"
echo "app_write password: $APP_WRITE_PASSWORD"
echo "app_admin password: $APP_ADMIN_PASSWORD"
```

3. **Update Role Passwords:**

```sql
-- Connect as postgres superuser
ALTER ROLE app_read WITH PASSWORD '<generated_password>';
ALTER ROLE app_write WITH PASSWORD '<generated_password>';
ALTER ROLE app_admin WITH PASSWORD '<generated_password>';
```

4. **Store Passwords Securely:**

```bash
# Using Docker Secrets (recommended)
echo "$APP_READ_PASSWORD" | docker secret create db_app_read_password -
echo "$APP_WRITE_PASSWORD" | docker secret create db_app_write_password -
echo "$APP_ADMIN_PASSWORD" | docker secret create db_app_admin_password -

# Or update .env file (development only)
echo "DB_APP_READ_PASSWORD=$APP_READ_PASSWORD" >> platform/.env
echo "DB_APP_WRITE_PASSWORD=$APP_WRITE_PASSWORD" >> platform/.env
echo "DB_APP_ADMIN_PASSWORD=$APP_ADMIN_PASSWORD" >> platform/.env
```

5. **Update Service Configurations:**

Update each service's DATABASE_URL to use the appropriate role:

```yaml
# docker-compose.app.yml
environment:
  - DATABASE_URL=postgresql://app_write:${DB_APP_WRITE_PASSWORD}@postgres:5432/agentic_platform  # For L01
  - DATABASE_URL=postgresql://app_read:${DB_APP_READ_PASSWORD}@postgres:5432/agentic_platform   # For L02-L07
```

### Verification

```bash
# 1. Verify roles exist
docker exec agentic-postgres psql -U postgres -c "\du"

# 2. Test app_read connection
docker exec agentic-postgres psql -U app_read -d agentic_platform -c "SELECT 1;"

# 3. Test app_write connection
docker exec agentic-postgres psql -U app_write -d agentic_platform -c "SELECT 1;"

# 4. Verify app_read cannot write
docker exec agentic-postgres psql -U app_read -d agentic_platform -c \
  "CREATE TABLE test_table (id INT);"  # Should fail with permission denied

# 5. Verify app_write can write
docker exec agentic-postgres psql -U app_write -d agentic_platform -c \
  "CREATE TEMP TABLE test_table (id INT);"  # Should succeed (temp tables allowed)
```

## Permission Details

### app_read Permissions

```sql
-- Schemas
GRANT USAGE ON SCHEMA public TO app_read;
GRANT USAGE ON SCHEMA l02_runtime TO app_read;
GRANT USAGE ON SCHEMA mcp_contexts TO app_read;
GRANT USAGE ON SCHEMA mcp_documents TO app_read;
GRANT USAGE ON SCHEMA shared TO app_read;

-- Tables (current and future)
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO app_read;

-- Sequences (current and future)
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO app_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON SEQUENCES TO app_read;
```

### app_write Additional Permissions

```sql
-- Tables (current and future)
GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_write;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT INSERT, UPDATE, DELETE ON TABLES TO app_write;

-- Sequences (current and future)
GRANT USAGE, UPDATE ON ALL SEQUENCES IN SCHEMA public TO app_write;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, UPDATE ON SEQUENCES TO app_write;
```

### app_admin Permissions

```sql
-- Full control over database
GRANT ALL PRIVILEGES ON DATABASE agentic_platform TO app_admin;
GRANT ALL PRIVILEGES ON SCHEMA public TO app_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO app_admin;

-- Can create new roles
GRANT CREATEROLE TO app_admin;
```

## Security Best Practices

### 1. Password Management

- ✅ Use strong, unique passwords for each role (32+ characters)
- ✅ Store passwords in secrets manager (Docker Secrets, Vault, AWS Secrets Manager)
- ✅ Never commit passwords to version control
- ✅ Rotate passwords quarterly
- ✅ Use different passwords for dev/staging/prod

### 2. Connection Security

- ✅ Use SSL/TLS for database connections
- ✅ Restrict network access to PostgreSQL (Docker network only)
- ✅ Configure pg_hba.conf for IP-based access control
- ✅ Use connection pooling (PgBouncer) to limit connections

### 3. Privilege Escalation Prevention

- ✅ Never use `postgres` superuser for application access
- ✅ Limit `app_admin` usage to migrations only
- ✅ Use `app_read` by default unless write access is required
- ✅ Review role memberships regularly

### 4. Auditing

- ✅ Enable PostgreSQL query logging
- ✅ Monitor for privilege escalation attempts
- ✅ Log all DDL statements (CREATE, ALTER, DROP)
- ✅ Track role usage by service

## Troubleshooting

### Permission Denied Errors

```sql
-- Check role permissions
SELECT grantee, privilege_type, table_schema, table_name
FROM information_schema.table_privileges
WHERE grantee = 'app_read'
LIMIT 10;

-- Check role memberships
SELECT r.rolname AS role, m.rolname AS member
FROM pg_roles r
JOIN pg_auth_members am ON r.oid = am.roleid
JOIN pg_roles m ON am.member = m.oid
WHERE r.rolname = 'app_write';
```

### Cannot Connect

```bash
# Verify role exists
docker exec agentic-postgres psql -U postgres -c "\du app_read"

# Test connection
docker exec agentic-postgres psql -U app_read -d agentic_platform -c "SELECT 1;"

# Check pg_hba.conf
docker exec agentic-postgres cat /var/lib/postgresql/data/pg_hba.conf
```

### Permissions Not Applied to New Tables

```sql
-- Grant permissions on existing tables
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_read;

-- Ensure default privileges are set for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO app_read;

-- Verify default privileges
SELECT
    defaclrole::regrole AS grantor,
    defaclnamespace::regnamespace AS schema,
    defaclobjtype AS object_type,
    defaclacl AS privileges
FROM pg_default_acl;
```

## Monitoring

### Role Usage Tracking

```sql
-- Track connections by role
SELECT
    usename,
    application_name,
    client_addr,
    COUNT(*) AS connection_count
FROM pg_stat_activity
WHERE usename IN ('app_read', 'app_write', 'app_admin')
GROUP BY usename, application_name, client_addr;

-- Track query patterns by role
SELECT
    usename,
    query,
    state,
    query_start
FROM pg_stat_activity
WHERE usename IN ('app_read', 'app_write', 'app_admin')
ORDER BY query_start DESC
LIMIT 20;
```

### Security Auditing

```sql
-- Log all DDL operations (requires logging configuration)
ALTER SYSTEM SET log_statement = 'ddl';
SELECT pg_reload_conf();

-- Track role changes
SELECT
    usename,
    valuntil AS password_expiry
FROM pg_user
WHERE usename IN ('app_read', 'app_write', 'app_admin');
```

## Maintenance

### Quarterly Tasks

- [ ] Review role assignments
- [ ] Rotate role passwords
- [ ] Audit access logs
- [ ] Remove unused roles
- [ ] Update documentation

### Annual Tasks

- [ ] Full security audit
- [ ] Penetration testing
- [ ] Compliance review (SOC 2, GDPR)
- [ ] Update RBAC policies

## Related Documentation

- Secrets Management: `SECURITY.md`
- Backup & Recovery: `platform/scripts/RECOVERY.md`
- Database Configuration: `platform/docker-compose.app.yml`
- Connection Pooling: `platform/docs/pgbouncer.md` (if implemented)

## References

- [PostgreSQL Roles and Privileges](https://www.postgresql.org/docs/current/user-manag.html)
- [PostgreSQL Default Privileges](https://www.postgresql.org/docs/current/sql-alterdefaultprivileges.html)
- [PostgreSQL pg_hba.conf](https://www.postgresql.org/docs/current/auth-pg-hba-conf.html)

---

**Document Version:** 1.0.0
**Last Review:** 2026-01-18
**Next Review:** 2026-04-18 (Quarterly)

-- Story Portal Platform V2 - PostgreSQL RBAC Setup
-- Creates role-based access control roles for database security

-- ============================================================================
-- 1. READ-ONLY ROLE (app_read)
-- ============================================================================
-- For services that only need to query data (reporting, analytics, read-only APIs)

-- Drop if exists (for rerun)
DROP ROLE IF EXISTS app_read;

-- Create role
CREATE ROLE app_read WITH LOGIN PASSWORD 'CHANGE_ME_app_read_password';

-- Grant database connection
GRANT CONNECT ON DATABASE agentic_platform TO app_read;

-- Grant schema usage
GRANT USAGE ON SCHEMA public TO app_read;
GRANT USAGE ON SCHEMA l02_runtime TO app_read;
GRANT USAGE ON SCHEMA mcp_contexts TO app_read;
GRANT USAGE ON SCHEMA mcp_documents TO app_read;
GRANT USAGE ON SCHEMA shared TO app_read;

-- Grant SELECT on all existing tables
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_read;
GRANT SELECT ON ALL TABLES IN SCHEMA l02_runtime TO app_read;
GRANT SELECT ON ALL TABLES IN SCHEMA mcp_contexts TO app_read;
GRANT SELECT ON ALL TABLES IN SCHEMA mcp_documents TO app_read;
GRANT SELECT ON ALL TABLES IN SCHEMA shared TO app_read;

-- Grant SELECT on all existing sequences
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO app_read;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA l02_runtime TO app_read;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA mcp_contexts TO app_read;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA mcp_documents TO app_read;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA shared TO app_read;

-- Grant SELECT on future tables automatically
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO app_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA l02_runtime GRANT SELECT ON TABLES TO app_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA mcp_contexts GRANT SELECT ON TABLES TO app_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA mcp_documents GRANT SELECT ON TABLES TO app_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA shared GRANT SELECT ON TABLES TO app_read;

-- Grant SELECT on future sequences automatically
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON SEQUENCES TO app_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA l02_runtime GRANT SELECT ON SEQUENCES TO app_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA mcp_contexts GRANT SELECT ON SEQUENCES TO app_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA mcp_documents GRANT SELECT ON SEQUENCES TO app_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA shared GRANT SELECT ON SEQUENCES TO app_read;

-- ============================================================================
-- 2. WRITE ROLE (app_write)
-- ============================================================================
-- For application services that need to insert, update, delete data
-- Inherits all read permissions from app_read

-- Drop if exists (for rerun)
DROP ROLE IF EXISTS app_write;

-- Create role
CREATE ROLE app_write WITH LOGIN PASSWORD 'CHANGE_ME_app_write_password';

-- Inherit read permissions
GRANT app_read TO app_write;

-- Grant INSERT, UPDATE, DELETE on all existing tables
GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_write;
GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA l02_runtime TO app_write;
GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA mcp_contexts TO app_write;
GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA mcp_documents TO app_write;
GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA shared TO app_write;

-- Grant USAGE and UPDATE on sequences (for INSERT operations)
GRANT USAGE, UPDATE ON ALL SEQUENCES IN SCHEMA public TO app_write;
GRANT USAGE, UPDATE ON ALL SEQUENCES IN SCHEMA l02_runtime TO app_write;
GRANT USAGE, UPDATE ON ALL SEQUENCES IN SCHEMA mcp_contexts TO app_write;
GRANT USAGE, UPDATE ON ALL SEQUENCES IN SCHEMA mcp_documents TO app_write;
GRANT USAGE, UPDATE ON ALL SEQUENCES IN SCHEMA shared TO app_write;

-- Grant permissions on future tables automatically
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT INSERT, UPDATE, DELETE ON TABLES TO app_write;
ALTER DEFAULT PRIVILEGES IN SCHEMA l02_runtime GRANT INSERT, UPDATE, DELETE ON TABLES TO app_write;
ALTER DEFAULT PRIVILEGES IN SCHEMA mcp_contexts GRANT INSERT, UPDATE, DELETE ON TABLES TO app_write;
ALTER DEFAULT PRIVILEGES IN SCHEMA mcp_documents GRANT INSERT, UPDATE, DELETE ON TABLES TO app_write;
ALTER DEFAULT PRIVILEGES IN SCHEMA shared GRANT INSERT, UPDATE, DELETE ON TABLES TO app_write;

-- Grant permissions on future sequences automatically
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, UPDATE ON SEQUENCES TO app_write;
ALTER DEFAULT PRIVILEGES IN SCHEMA l02_runtime GRANT USAGE, UPDATE ON SEQUENCES TO app_write;
ALTER DEFAULT PRIVILEGES IN SCHEMA mcp_contexts GRANT USAGE, UPDATE ON SEQUENCES TO app_write;
ALTER DEFAULT PRIVILEGES IN SCHEMA mcp_documents GRANT USAGE, UPDATE ON SEQUENCES TO app_write;
ALTER DEFAULT PRIVILEGES IN SCHEMA shared GRANT USAGE, UPDATE ON SEQUENCES TO app_write;

-- ============================================================================
-- 3. ADMIN ROLE (app_admin)
-- ============================================================================
-- For database migrations, schema changes, maintenance operations
-- Full control over database objects

-- Drop if exists (for rerun)
DROP ROLE IF EXISTS app_admin;

-- Create role with CREATEROLE privilege
CREATE ROLE app_admin WITH LOGIN PASSWORD 'CHANGE_ME_app_admin_password' CREATEROLE;

-- Grant all privileges on database
GRANT ALL PRIVILEGES ON DATABASE agentic_platform TO app_admin;

-- Grant all privileges on schemas
GRANT ALL PRIVILEGES ON SCHEMA public TO app_admin;
GRANT ALL PRIVILEGES ON SCHEMA l02_runtime TO app_admin;
GRANT ALL PRIVILEGES ON SCHEMA mcp_contexts TO app_admin;
GRANT ALL PRIVILEGES ON SCHEMA mcp_documents TO app_admin;
GRANT ALL PRIVILEGES ON SCHEMA shared TO app_admin;

-- Grant all privileges on all existing tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA l02_runtime TO app_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA mcp_contexts TO app_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA mcp_documents TO app_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA shared TO app_admin;

-- Grant all privileges on all existing sequences
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO app_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA l02_runtime TO app_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA mcp_contexts TO app_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA mcp_documents TO app_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA shared TO app_admin;

-- Grant all privileges on future tables automatically
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO app_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA l02_runtime GRANT ALL PRIVILEGES ON TABLES TO app_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA mcp_contexts GRANT ALL PRIVILEGES ON TABLES TO app_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA mcp_documents GRANT ALL PRIVILEGES ON TABLES TO app_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA shared GRANT ALL PRIVILEGES ON TABLES TO app_admin;

-- Grant all privileges on future sequences automatically
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO app_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA l02_runtime GRANT ALL PRIVILEGES ON SEQUENCES TO app_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA mcp_contexts GRANT ALL PRIVILEGES ON SEQUENCES TO app_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA mcp_documents GRANT ALL PRIVILEGES ON SEQUENCES TO app_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA shared GRANT ALL PRIVILEGES ON SEQUENCES TO app_admin;

-- ============================================================================
-- 4. VERIFICATION
-- ============================================================================

-- List all roles
SELECT 'Roles created:' AS message;
SELECT rolname AS role_name, rolcanlogin AS can_login
FROM pg_roles
WHERE rolname IN ('app_read', 'app_write', 'app_admin')
ORDER BY rolname;

-- Show role memberships
SELECT 'Role memberships:' AS message;
SELECT r.rolname AS role, m.rolname AS member
FROM pg_roles r
JOIN pg_auth_members am ON r.oid = am.roleid
JOIN pg_roles m ON am.member = m.oid
WHERE r.rolname IN ('app_read', 'app_write', 'app_admin')
   OR m.rolname IN ('app_read', 'app_write', 'app_admin');

-- Show privileges for public schema
SELECT 'Privileges on public schema:' AS message;
SELECT
    grantee,
    string_agg(privilege_type, ', ') AS privileges
FROM information_schema.table_privileges
WHERE table_schema = 'public'
  AND grantee IN ('app_read', 'app_write', 'app_admin')
GROUP BY grantee
ORDER BY grantee;

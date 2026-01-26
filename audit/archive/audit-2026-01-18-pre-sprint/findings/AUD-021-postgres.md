## PostgreSQL Configuration
### Connection Test
(eval):1: command not found: pg_isready
### Connection Test
/var/run/postgresql:5432 - accepting connections
### Extensions
  extname  | extversion 
-----------+------------
 plpgsql   | 1.0
 uuid-ossp | 1.1
 vector    | 0.8.1
 pg_trgm   | 1.6
(4 rows)

### Database Size
 pg_size_pretty 
----------------
 17 MB
(1 row)

### Table Sizes
  schemaname   |        tablename        |  size   
---------------+-------------------------+---------
 mcp_documents | tool_definitions        | 1240 kB
 mcp_documents | sections                | 1224 kB
 mcp_documents | documents               | 1192 kB
 mcp_documents | claims                  | 1080 kB
 mcp_documents | entities                | 1000 kB
 mcp_documents | tool_executions         | 80 kB
 mcp_documents | tool_invocations        | 80 kB
 mcp_documents | model_usage             | 80 kB
 mcp_documents | api_requests            | 72 kB
 mcp_documents | alerts                  | 64 kB
 mcp_documents | anomalies               | 64 kB
 mcp_documents | plans                   | 64 kB
 mcp_documents | goals                   | 64 kB
 mcp_documents | compliance_results      | 64 kB
 mcp_documents | tasks                   | 64 kB
 mcp_documents | metrics                 | 64 kB
 mcp_documents | control_operations      | 56 kB
 mcp_documents | quality_scores          | 56 kB
 mcp_documents | service_registry_events | 48 kB
 mcp_documents | rate_limit_events       | 48 kB
(20 rows)

### Active Connections
 connections 
-------------
           7
(1 row)

### pgvector Status
 extversion 
------------
 0.8.1
(1 row)

### Database List
                                                          List of databases
       Name       |  Owner   | Encoding | Locale Provider |  Collate   |   Ctype    | ICU Locale | ICU Rules |   Access privileges   
------------------+----------+----------+-----------------+------------+------------+------------+-----------+-----------------------
 agentic          | postgres | UTF8     | libc            | en_US.utf8 | en_US.utf8 |            |           | 
 agentic_platform | postgres | UTF8     | libc            | en_US.utf8 | en_US.utf8 |            |           | 
 postgres         | postgres | UTF8     | libc            | en_US.utf8 | en_US.utf8 |            |           | 
 template0        | postgres | UTF8     | libc            | en_US.utf8 | en_US.utf8 |            |           | =c/postgres          +
                  |          |          |                 |            |            |            |           | postgres=CTc/postgres
 template1        | postgres | UTF8     | libc            | en_US.utf8 | en_US.utf8 |            |           | =c/postgres          +
                  |          |          |                 |            |            |            |           | postgres=CTc/postgres
(5 rows)

### Configuration Parameters
         name         | setting | unit 
----------------------+---------+------
 effective_cache_size | 524288  | 8kB
 maintenance_work_mem | 65536   | kB
 max_connections      | 100     | 
 max_wal_size         | 1024    | MB
 shared_buffers       | 16384   | 8kB
 wal_level            | replica | 
 work_mem             | 4096    | kB
(7 rows)


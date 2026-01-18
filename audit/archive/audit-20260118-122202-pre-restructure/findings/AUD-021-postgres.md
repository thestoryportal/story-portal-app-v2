## PostgreSQL Configuration
### Connection Test
(eval):1: command not found: pg_isready
/var/run/postgresql:5432 - accepting connections
### Extensions
      extname       | extversion 
--------------------+------------
 plpgsql            | 1.0
 uuid-ossp          | 1.1
 vector             | 0.8.1
 pg_trgm            | 1.6
 pg_stat_statements | 1.10
(5 rows)

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

### PostgreSQL Tuning Parameters
         name         | setting | unit 
----------------------+---------+------
 effective_cache_size | 524288  | 8kB
 max_connections      | 100     | 
 shared_buffers       | 65536   | 8kB
 work_mem             | 32768   | kB
(4 rows)


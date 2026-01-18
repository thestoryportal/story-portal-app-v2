# Service Discovery Findings

## Infrastructure Services
### PostgreSQL (5432)
/var/run/postgresql:5432 - accepting connections
Status: RUNNING
### Redis (6379)
PONG
Status: RUNNING
### Ollama (11434)
{"version":"0.14.2"} Status: RUNNING
## Application Layer Health
### Port 8001
{"error":"authentication_required","message":"Missing API key. Provide X-API-Key header or Authorization: Bearer token.","details":{"supported_methods":["X-API-Key","Authorization Bearer"]}}
HTTP_CODE:401
### Port 8002
{"detail":"Not Found"}
HTTP_CODE:404
### Port 8003
{"detail":"Not Found"}
HTTP_CODE:404
### Port 8004
{"detail":"Not Found"}
HTTP_CODE:404
### Port 8005
{"detail":"Not Found"}
HTTP_CODE:404
### Port 8006
{"detail":"Not Found"}
HTTP_CODE:404
### Port 8007
{"detail":"Not Found"}
HTTP_CODE:404
### Port 8009
{'error': {'code': 'E9103', 'message': 'Missing authentication credentials', 'timestamp': 1768757276556, 'trace_id': '506426a04b434aa49f7a0d5bedbece2e', 'request_id': '53c4f48e-38f7-45df-95da-cef27d92278d', 'details': {'supported_methods': ['api_key', 'oauth_jwt', 'mtls']}}}
HTTP_CODE:401
### Port 8010
{"detail":"Not Found"}
HTTP_CODE:404
### Port 8011
{"detail":"Not Found"}
HTTP_CODE:404
### Port 8012
{"status":"healthy","version":"1.0.0","services_loaded":44,"active_sessions":0}
HTTP_CODE:200
## MCP Services (PM2)
┌────┬──────────────────────────────┬─────────────┬─────────┬─────────┬──────────┬────────┬──────┬───────────┬──────────┬──────────┬──────────┬──────────┐
│ id │ name                         │ namespace   │ version │ mode    │ pid      │ uptime │ ↺    │ status    │ cpu      │ mem      │ user     │ watching │
├────┼──────────────────────────────┼─────────────┼─────────┼─────────┼──────────┼────────┼──────┼───────────┼──────────┼──────────┼──────────┼──────────┤
│ [1m[36m1[39m[22m  │ mcp-context-orchestrator     │ default     │ N/A     │ [7m[1mfork[22m[27m    │ N/A      │ 17h    │ 0    │ [32m[1monline[22m[39m    │ 0%       │ 0b       │ [1mrob… │ [90mdisabled[39m │
│ [1m[36m0[39m[22m  │ mcp-document-consolidator    │ default     │ N/A     │ [7m[1mfork[22m[27m    │ N/A      │ 17h    │ 0    │ [32m[1monline[22m[39m    │ 0%       │ 0b       │ [1mrob… │ [90mdisabled[39m │
└────┴──────────────────────────────┴─────────────┴─────────┴─────────┴──────────┴────────┴──────┴───────────┴──────────┴──────────┴──────────┴──────────┘

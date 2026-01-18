# Initial State Assessment
Generated: $(date)

## Infrastructure Services
### PostgreSQL
(eval):1: command not found: pg_isready
NOT AVAILABLE

### Redis
PONG

### Ollama
{"models":[{"name":"llama3.1:8b","model":"llama3.1:8b","modified_at":"2026-01-15T12:25:06.360165979-07:00","size":4920753328,"digest":"46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e","details":{"parent_model":"","format":"gguf","family":"llama","families":["llama"],"parameter_size":"8.0B","quantization_level":"Q4_K_M"}},{"name":"llama3.2:latest","model":"llama3.2:latest","modified_at":"2026-01-15T12:07:25.6542457-07:00","size":2019393189,"digest":"a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72","details":{"parent_model":"","format":"gguf","family":"llama","families":["llama"],"parameter_size":"3.2B","quantization_level":"Q4_K_M"}},{"name":"llama3.2:3b","model":"llama3.2:3b","modified_at":"2026-01-14T10:44:00.652294216-07:00","size":2019393189,"digest":"a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72","details":{"parent_model":"","format":"gguf","family":"llama","families":["llama"],"parameter_size":"3.2B","quantization_level":"Q4_K_M"}},{"name":"llama3.2:1b","model":"llama3.2:1b","modified_at":"2026-01-09T12:11:26.19704509-07:00","size":1321098329,"digest":"baf6a787fdffd633537aa2eb51cfd54cb93ff08e28040095462bb63daf552878","details":{"parent_model":"","format":"gguf","family":"llama","families":["llama"],"parameter_size":"1.2B","quantization_level":"Q8_0"}},{"name":"llava-llama3:latest","model":"llava-llama3:latest","modified_at":"2025-12-26T00:56:22.554671593-07:00","size":5545682182,"digest":"44c161b1f46523301da9c0cc505afa4a4a0cc62f580581d98a430bb21acd46de","details":{"parent_model":"","format":"gguf","family":"llama","families":["llama","clip"],"parameter_size":"8B","quantization_level":"Q4_K_M"}}]}
### Docker
CONTAINER ID   IMAGE                    COMMAND                  CREATED       STATUS                 PORTS                                         NAMES
5c07fb324c88   ollama/ollama:latest     "/bin/ollama serve"      2 hours ago   Up 2 hours             11434/tcp                                     awesome_hypatia
dd7417c1bf08   redis:7-alpine           "docker-entrypoint.s…"   3 days ago    Up 2 hours (healthy)   0.0.0.0:6379->6379/tcp, [::]:6379->6379/tcp   agentic-redis
9e82ceda21c7   pgvector/pgvector:pg16   "docker-entrypoint.s…"   3 days ago    Up 2 hours (healthy)   0.0.0.0:5432->5432/tcp, [::]:5432->5432/tcp   agentic-postgres

### PM2/MCP Services
┌────┬──────────────────────────────┬─────────────┬─────────┬─────────┬──────────┬────────┬──────┬───────────┬──────────┬──────────┬──────────┬──────────┐
│ id │ name                         │ namespace   │ version │ mode    │ pid      │ uptime │ ↺    │ status    │ cpu      │ mem      │ user     │ watching │
├────┼──────────────────────────────┼─────────────┼─────────┼─────────┼──────────┼────────┼──────┼───────────┼──────────┼──────────┼──────────┼──────────┤
│ [1m[36m1[39m[22m  │ mcp-context-orchestrator     │ default     │ N/A     │ [7m[1mfork[22m[27m    │ N/A      │ 3h     │ 0    │ [32m[1monline[22m[39m    │ 0%       │ 0b       │ [1mrob… │ [90mdisabled[39m │
│ [1m[36m0[39m[22m  │ mcp-document-consolidator    │ default     │ N/A     │ [7m[1mfork[22m[27m    │ N/A      │ 3h     │ 0    │ [32m[1monline[22m[39m    │ 0%       │ 0b       │ [1mrob… │ [90mdisabled[39m │
│ [1m[36m2[39m[22m  │ ollama                       │ default     │ N/A     │ [7m[1mfork[22m[27m    │ 52536    │ 0s     │ 111… │ [32m[1monline[22m[39m    │ 0%       │ 0b       │ [1mrob… │ [90mdisabled[39m │
└────┴──────────────────────────────┴─────────────┴─────────┴─────────┴──────────┴────────┴──────┴───────────┴──────────┴──────────┴──────────┴──────────┘

### Application Ports
Port 8001: 000DOWN
Port 8002: 000DOWN
Port 8003: 000DOWN
Port 8004: 000DOWN
Port 8005: 000DOWN
Port 8006: 000DOWN
Port 8007: 000DOWN
Port 8009: 000DOWN
Port 8010: 000DOWN
Port 8011: 000DOWN

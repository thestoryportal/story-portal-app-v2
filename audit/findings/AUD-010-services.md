# Service Discovery Findings

## Infrastructure Services
### PostgreSQL (5432)
/var/run/postgresql:5432 - accepting connections
Status: RUNNING

### Redis (6379)

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
{'error': {'code': 'E9103', 'message': 'Missing authentication credentials', 'timestamp': 1768764832349, 'trace_id': '40fc92fe94b44b208a00b6e730fc6144', 'request_id': 'b6cdf0a6-513e-4892-bfe9-d28fa0d1e4b7', 'details': {'supported_methods': ['api_key', 'oauth_jwt', 'mtls']}}}
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

PONG
Status: RUNNING

### Ollama (11434)
{"version":"0.14.2"}Status: RUNNING

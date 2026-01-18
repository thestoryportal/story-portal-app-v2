# Network/TLS Audit
## TLS Certificates
./platform/ssl/private.key
./platform/ssl/certificate.crt
./platform/.venv/lib/python3.12/site-packages/pip/_vendor/certifi/cacert.pem
./platform/.venv/lib/python3.12/site-packages/certifi/cacert.pem
./platform/services/mcp-document-consolidator/python/venv/lib/python3.12/site-packages/pip/_vendor/certifi/cacert.pem
./platform/services/mcp-document-consolidator/python/venv/lib/python3.12/site-packages/certifi/cacert.pem
## Internal HTTPS Usage
Found 4 internal HTTPS references
## Exposed Docker Ports
platform-ui: 0.0.0.0:3000->80/tcp, [::]:3000->80/tcp
l06-evaluation: 0.0.0.0:8006->8006/tcp, [::]:8006->8006/tcp
l12-service-hub: 0.0.0.0:8012->8012/tcp, [::]:8012->8012/tcp
l05-planning: 0.0.0.0:8005->8005/tcp, [::]:8005->8005/tcp
l02-runtime: 0.0.0.0:8002->8002/tcp, [::]:8002->8002/tcp
l11-integration: 0.0.0.0:8011->8011/tcp, [::]:8011->8011/tcp
l10-human-interface: 0.0.0.0:8010->8010/tcp, [::]:8010->8010/tcp
l03-tool-execution: 0.0.0.0:8003->8003/tcp, [::]:8003->8003/tcp
l07-learning: 0.0.0.0:8007->8007/tcp, [::]:8007->8007/tcp
l04-model-gateway: 0.0.0.0:8004->8004/tcp, [::]:8004->8004/tcp
l09-api-gateway: 0.0.0.0:8009->8009/tcp, [::]:8009->8009/tcp
agentic-db-tools: 5432/tcp
l01-data-layer: 0.0.0.0:8001->8001/tcp, [::]:8001->8001/tcp
agentic-redis-exporter: 0.0.0.0:9121->9121/tcp, [::]:9121->9121/tcp
agentic-postgres-exporter: 0.0.0.0:9187->9187/tcp, [::]:9187->9187/tcp
agentic-grafana: 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp
agentic-redis: 0.0.0.0:6379->6379/tcp, [::]:6379->6379/tcp
agentic-postgres: 0.0.0.0:5432->5432/tcp, [::]:5432->5432/tcp
agentic-prometheus: 0.0.0.0:9090->9090/tcp, [::]:9090->9090/tcp
agentic-cadvisor: 0.0.0.0:8080->8080/tcp, [::]:8080->8080/tcp
agentic-node-exporter: 0.0.0.0:9100->9100/tcp, [::]:9100->9100/tcp

# Container Infrastructure Audit

## All Containers
NAMES                       STATUS                                  PORTS
agentic-node-exporter       Restarting (2) Less than a second ago   
agentic-grafana             Up 33 minutes                           0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp
agentic-prometheus          Up 33 minutes                           0.0.0.0:9090->9090/tcp, [::]:9090->9090/tcp
agentic-redis-exporter      Up 33 minutes                           0.0.0.0:9121->9121/tcp, [::]:9121->9121/tcp
agentic-cadvisor            Up 33 minutes (healthy)                 0.0.0.0:8080->8080/tcp, [::]:8080->8080/tcp
agentic-postgres-exporter   Up 33 minutes                           0.0.0.0:9187->9187/tcp, [::]:9187->9187/tcp
agentic-db-tools            Up 35 minutes                           5432/tcp
l01-data-layer              Up 43 minutes (healthy)                 0.0.0.0:8001->8001/tcp, [::]:8001->8001/tcp
agentic-redis               Up 46 minutes (healthy)                 0.0.0.0:6379->6379/tcp, [::]:6379->6379/tcp
agentic-postgres            Up 46 minutes (healthy)                 0.0.0.0:5432->5432/tcp, [::]:5432->5432/tcp
l09-api-gateway             Up 58 minutes (healthy)                 0.0.0.0:8009->8009/tcp, [::]:8009->8009/tcp
platform-ui                 Up About an hour (healthy)              0.0.0.0:3000->80/tcp, [::]:3000->80/tcp
l12-service-hub             Up 4 hours (healthy)                    0.0.0.0:8012->8012/tcp, [::]:8012->8012/tcp
l07-learning                Up 5 hours (healthy)                    0.0.0.0:8007->8007/tcp, [::]:8007->8007/tcp
l10-human-interface         Up 5 hours (healthy)                    0.0.0.0:8010->8010/tcp, [::]:8010->8010/tcp
l05-planning                Up 5 hours (healthy)                    0.0.0.0:8005->8005/tcp, [::]:8005->8005/tcp
l06-evaluation              Up 5 hours (healthy)                    0.0.0.0:8006->8006/tcp, [::]:8006->8006/tcp
l03-tool-execution          Up 5 hours (healthy)                    0.0.0.0:8003->8003/tcp, [::]:8003->8003/tcp
l02-runtime                 Up 5 hours (healthy)                    0.0.0.0:8002->8002/tcp, [::]:8002->8002/tcp
l11-integration             Up 5 hours (healthy)                    0.0.0.0:8011->8011/tcp, [::]:8011->8011/tcp
l04-model-gateway           Up 5 hours (healthy)                    0.0.0.0:8004->8004/tcp, [::]:8004->8004/tcp

## Container Count
Total Containers: 21
Healthy Containers: 15

## Container Health Status
agentic-node-exporter: Restarting (2) 1 second ago
agentic-grafana: Up 33 minutes
agentic-prometheus: Up 33 minutes
agentic-redis-exporter: Up 33 minutes
agentic-postgres-exporter: Up 33 minutes
agentic-db-tools: Up 35 minutes

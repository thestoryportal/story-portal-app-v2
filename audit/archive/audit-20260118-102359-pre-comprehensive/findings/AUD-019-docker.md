## Container Inventory
NAMES                       IMAGE                                          STATUS                       PORTS
agentic-node-exporter       prom/node-exporter:latest                      Up 27 minutes                0.0.0.0:9100->9100/tcp, [::]:9100->9100/tcp
agentic-grafana             grafana/grafana:latest                         Up About an hour             0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp
agentic-prometheus          prom/prometheus:latest                         Up 25 minutes                0.0.0.0:9090->9090/tcp, [::]:9090->9090/tcp
agentic-redis-exporter      oliver006/redis_exporter:latest                Up About an hour             0.0.0.0:9121->9121/tcp, [::]:9121->9121/tcp
agentic-cadvisor            gcr.io/cadvisor/cadvisor:latest                Up About an hour (healthy)   0.0.0.0:8080->8080/tcp, [::]:8080->8080/tcp
agentic-postgres-exporter   prometheuscommunity/postgres-exporter:latest   Up About an hour             0.0.0.0:9187->9187/tcp, [::]:9187->9187/tcp
agentic-db-tools            postgres:16                                    Up About an hour             5432/tcp
l01-data-layer              l01-data-layer:latest                          Up About an hour (healthy)   0.0.0.0:8001->8001/tcp, [::]:8001->8001/tcp
agentic-redis               redis:7-alpine                                 Up About an hour (healthy)   0.0.0.0:6379->6379/tcp, [::]:6379->6379/tcp
agentic-postgres            pgvector/pgvector:pg16                         Up About an hour (healthy)   0.0.0.0:5432->5432/tcp, [::]:5432->5432/tcp
l09-api-gateway             l09-api-gateway:latest                         Up 2 hours (healthy)         0.0.0.0:8009->8009/tcp, [::]:8009->8009/tcp
platform-ui                 platform-ui:latest                             Up 2 hours (healthy)         0.0.0.0:3000->80/tcp, [::]:3000->80/tcp
l12-service-hub             l12-service-hub:latest                         Up 5 hours (healthy)         0.0.0.0:8012->8012/tcp, [::]:8012->8012/tcp
l07-learning                l07-learning:latest                            Up 6 hours (healthy)         0.0.0.0:8007->8007/tcp, [::]:8007->8007/tcp
l10-human-interface         l10-human-interface:latest                     Up 6 hours (healthy)         0.0.0.0:8010->8010/tcp, [::]:8010->8010/tcp
l05-planning                l05-planning:latest                            Up 6 hours (healthy)         0.0.0.0:8005->8005/tcp, [::]:8005->8005/tcp
l06-evaluation              l06-evaluation:latest                          Up 6 hours (healthy)         0.0.0.0:8006->8006/tcp, [::]:8006->8006/tcp
l03-tool-execution          l03-tool-execution:latest                      Up 6 hours (healthy)         0.0.0.0:8003->8003/tcp, [::]:8003->8003/tcp
l02-runtime                 l02-runtime:latest                             Up 6 hours (healthy)         0.0.0.0:8002->8002/tcp, [::]:8002->8002/tcp
l11-integration             l11-integration:latest                         Up 6 hours (healthy)         0.0.0.0:8011->8011/tcp, [::]:8011->8011/tcp
l04-model-gateway           l04-model-gateway:latest                       Up 6 hours (healthy)         0.0.0.0:8004->8004/tcp, [::]:8004->8004/tcp
practical_chebyshev         postgres:15-alpine                             Exited (1) 8 hours ago       
awesome_hypatia             ollama/ollama:latest                           Exited (0) 7 hours ago       
## Resource Limits
/agentic-node-exporter: Memory=134217728 CPU=250000000
/agentic-grafana: Memory=536870912 CPU=500000000
/agentic-prometheus: Memory=1073741824 CPU=1000000000
/agentic-redis-exporter: Memory=134217728 CPU=250000000
/agentic-cadvisor: Memory=268435456 CPU=500000000
/agentic-postgres-exporter: Memory=134217728 CPU=250000000
/agentic-db-tools: Memory=0 CPU=0
/l01-data-layer: Memory=1073741824 CPU=1000000000
/agentic-redis: Memory=536870912 CPU=1000000000
/agentic-postgres: Memory=2147483648 CPU=2000000000
/l09-api-gateway: Memory=0 CPU=0
/platform-ui: Memory=0 CPU=0
/l12-service-hub: Memory=0 CPU=0
/l07-learning: Memory=0 CPU=0
/l10-human-interface: Memory=0 CPU=0
/l05-planning: Memory=0 CPU=0
/l06-evaluation: Memory=0 CPU=0
/l03-tool-execution: Memory=0 CPU=0
/l02-runtime: Memory=0 CPU=0
/l11-integration: Memory=0 CPU=0
/l04-model-gateway: Memory=0 CPU=0
## Image Versions
REPOSITORY                              TAG         SIZE
l01-data-layer                          latest      307MB
l09-api-gateway                         latest      378MB
platform-ui                             latest      94.5MB
l12-service-hub                         latest      259MB
l07-learning                            latest      403MB
l10-human-interface                     latest      430MB
l06-evaluation                          latest      306MB
l05-planning                            latest      306MB
l03-tool-execution                      latest      310MB
l11-integration                         latest      276MB
l11-integration                         test        276MB
l09-api-gateway                         test        378MB
l07-learning                            test        306MB
l04-model-gateway                       latest      306MB
l04-model-gateway                       test        306MB
l03-tool-execution                      test        306MB
l02-runtime                             test        284MB
l02-runtime                             latest      284MB
story-portal-app-l10-human-interface    latest      430MB
story-portal-app-l09-api-gateway        latest      378MB
story-portal-app-l02-runtime            latest      283MB
story-portal-app-l06-evaluation         latest      306MB
story-portal-app-l05-planning           latest      306MB
story-portal-app-l04-model-gateway      latest      306MB
story-portal-app-l01-data-layer         latest      307MB
story-portal-app-l03-tool-execution     latest      306MB
story-portal-app-l07-learning           latest      306MB
story-portal-app-l11-integration        latest      276MB
ollama/ollama                           latest      8.97GB
postgres                                16          641MB
prom/prometheus                         latest      503MB
gcr.io/cadvisor/cadvisor                latest      107MB
grafana/grafana                         latest      994MB
postgres                                16-alpine   395MB
postgres                                15-alpine   392MB
oliver006/redis_exporter                latest      14.6MB
pgvector/pgvector                       pg16        723MB
redis                                   7-alpine    61.2MB
prom/node-exporter                      latest      41.6MB
prometheuscommunity/postgres-exporter   latest      37.2MB
grafana/grafana                         10.0.0      446MB
prom/prometheus                         v2.45.0     334MB
## Volumes
/agentic-node-exporter: /proc->/host/proc /sys->/host/sys /->/rootfs 
/agentic-grafana: /var/lib/docker/volumes/platform_grafana_data/_data->/var/lib/grafana /Volumes/Extreme SSD/projects/story-portal-app/platform/monitoring/grafana/provisioning->/etc/grafana/provisioning 
/agentic-prometheus: /var/lib/docker/volumes/platform_prometheus_data/_data->/prometheus /host_mnt/Volumes/Extreme SSD/projects/story-portal-app/platform/monitoring/prometheus.yml->/etc/prometheus/prometheus.yml 
/agentic-redis-exporter: 
/agentic-cadvisor: /->/rootfs /host_mnt/private/var/run->/var/run /sys->/sys /var/lib/docker->/var/lib/docker /dev/disk->/dev/disk 
/agentic-postgres-exporter: 
/agentic-db-tools: /var/lib/docker/volumes/bdab2d16fa07a366dd10a86e6851bb3ced8a4db244f65862f9bd1e27b71f72ec/_data->/var/lib/postgresql/data 
/l01-data-layer: 
/agentic-redis: /var/lib/docker/volumes/platform_redis_data/_data->/data 
/agentic-postgres: /var/lib/docker/volumes/platform_postgres_data/_data->/var/lib/postgresql/data 
/l09-api-gateway: 
/platform-ui: 
/l12-service-hub: 
/l07-learning: 
/l10-human-interface: 
/l05-planning: 
/l06-evaluation: 
/l03-tool-execution: 
/l02-runtime: 
/l11-integration: 
/l04-model-gateway: 
## Networks
NETWORK ID     NAME                       DRIVER    SCOPE
15411f4df8b5   bridge                     bridge    local
e2d5da56be46   host                       host      local
5ae8fb19a0fd   none                       null      local
81ca4d82e432   platform_agentic-network   bridge    local
## Compose Validation
INVALID or NOT FOUND

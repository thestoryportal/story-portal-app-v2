# Infrastructure Layer Specification

**Layer ID:** L00  
**Version:** 1.2.0  
**Status:** Final (Industry Validated)  
**Date:** January 4, 2025

## Document Information

| Attribute | Value |
|-----------|-------|
| Layer Name | Infrastructure Layer |
| Abbreviation | INFRA |
| Position | L00 (Foundation) |
| Dependencies | Cloud Providers (AWS/GCP/Azure) |
| Dependents | All layers (L01-L11) |
| Specification Method | Research -> Gap Analysis -> Specification -> Validation |
| Complexity | Medium (M) |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
   - 1.1 Purpose
   - 1.2 Key Capabilities
   - 1.3 Position in Stack
   - 1.4 Design Principles
   - 1.5 Technology Decisions

2. [Scope Definition](#2-scope-definition)
   - 2.1 In Scope
   - 2.2 Out of Scope
   - 2.3 Assumptions and Constraints
   - 2.4 Future Considerations

3. [Architecture](#3-architecture)
   - 3.1 Component Overview
   - 3.2 Cluster Manager
   - 3.3 Network Controller
   - 3.4 Secrets Operator
   - 3.5 Resource Scaler
   - 3.6 Certificate Manager
   - 3.7 Observability Stack
   - 3.8 Deployment Topologies

4. [Interfaces](#4-interfaces)
   - 4.1 Cluster Provisioning API
   - 4.2 Resource Request Interface
   - 4.3 Network Policy API
   - 4.4 Secrets Access API
   - 4.5 Service Registration API
   - 4.6 Monitoring API
   - 4.7 Error Codes

5. [Data Model](#5-data-model)
   - 5.1 Cluster Configuration
   - 5.2 Resource Quota
   - 5.3 Network Policy
   - 5.4 Secret Reference
   - 5.5 Service Registration
   - 5.6 Health Check Configuration
   - 5.7 Storage Specifications

6. [Integration with Data Layer](#6-integration-with-data-layer)
   - 6.1 Storage Provisioning
   - 6.2 Network Isolation
   - 6.3 Secrets Management
   - 6.4 Service Discovery
   - 6.5 Backup Infrastructure
   - 6.6 Integration Patterns

7. [Reliability and Scalability](#7-reliability-and-scalability)
   - 7.1 High Availability Strategy
   - 7.2 Disaster Recovery
   - 7.3 Autoscaling Mechanisms
   - 7.4 Resource Optimization
   - 7.5 Capacity Planning
   - 7.6 Edge Deployment

8. [Security](#8-security)
   - 8.1 Cluster Hardening
   - 8.2 Network Security
   - 8.3 Secrets Management
   - 8.4 RBAC and Access Control
   - 8.5 Compliance
   - 8.6 Threat Model
   - 8.7 Supply Chain Security

9. [Observability](#9-observability)
   - 9.1 Metrics Collection
   - 9.2 Log Aggregation
   - 9.3 Distributed Tracing
   - 9.4 Alerting
   - 9.5 Dashboards
   - 9.6 Cost Tracking

10. [Configuration](#10-configuration)
    - 10.1 Infrastructure-as-Code
    - 10.2 GitOps Workflow
    - 10.3 Environment Management
    - 10.4 Configuration Validation
    - 10.5 Secrets Configuration
    - 10.6 Feature Flags

11. [Implementation Guide](#11-implementation-guide)
    - 11.1 Prerequisites
    - 11.2 Bootstrap Process
    - 11.3 Component Installation
    - 11.4 Network Setup
    - 11.5 Security Hardening
    - 11.6 Validation Steps

12. [Testing Strategy](#12-testing-strategy)
    - 12.1 Unit Testing
    - 12.2 Integration Testing
    - 12.3 Chaos Engineering
    - 12.4 Performance Testing
    - 12.5 Security Testing
    - 12.6 Compliance Testing

13. [Migration and Deployment](#13-migration-and-deployment)
    - 13.1 Migration Strategy
    - 13.2 Blue-Green Deployment
    - 13.3 Rollback Procedures
    - 13.4 Data Migration
    - 13.5 Zero-Downtime Upgrades
    - 13.6 Risk Mitigation

14. [Open Questions and Decisions](#14-open-questions-and-decisions)
    - 14.1 Resolved Decisions
    - 14.2 Deferred Questions
    - 14.3 Design Trade-offs
    - 14.4 Future Research Areas

15. [References and Appendices](#15-references-and-appendices)
    - 15.1 External References
    - 15.2 Internal References
    - 15.3 Glossary
    - 15.4 Appendix A: Kubernetes Resource Examples
    - 15.5 Appendix B: Terraform Module Examples
    - 15.6 Appendix C: Runbook Index
    - 15.7 Appendix D: Configuration File Locations

---

## 1. Executive Summary

### 1.1 Purpose

The Infrastructure Layer provides the foundational deployment substrate upon which the entire Agentic AI Workforce stack executes. This layer abstracts cloud provider specifics, manages container orchestration, provisions compute resources, establishes network topology, handles secrets management, and enables service discovery across all workloads.

Infrastructure exists as a distinct layer to enforce separation between platform capabilities and application concerns. Application layers (L01-L11) declare their resource requirements through standard Kubernetes interfaces; Infrastructure satisfies those requirements without exposing provider-specific implementation details. This separation enables workload portability, operational consistency, and centralized policy enforcement.

The layer delivers three key value propositions: substrate independence through Kubernetes abstraction, operational consistency via GitOps-driven configuration management, and cost optimization through intelligent resource scheduling and spot instance utilization.

### 1.2 Key Capabilities

| Capability | Description |
|------------|-------------|
| Container Orchestration | Kubernetes cluster lifecycle management including provisioning, upgrades, node pool configuration, and namespace isolation for multi-tenant agent deployments |
| Compute Resource Management | Provisioning and scaling CPU, memory, GPU, and storage resources based on workload demands with cost-aware scheduling |
| Network Infrastructure | Service mesh (Cilium), ingress controllers, DNS, load balancing, and network policies for east-west and north-south traffic |
| Secrets Management | Integration with HashiCorp Vault via External Secrets Operator for secure credential storage, rotation, and injection |
| Service Discovery | Kubernetes-native service registry, DNS-based resolution, and health checking for dynamic service-to-service communication |
| Infrastructure Observability | Prometheus, Grafana, and Loki deployment and management for infrastructure-level metrics, logs, and dashboards |

### 1.3 Position in Stack

```
+=====================================================================+
|                        EXTERNAL CLIENTS                              |
|                    (Users, External Services)                        |
+=====================================================================+
                                  |
                                  v
+---------------------------------------------------------------------+
|                     L09/L10: API GATEWAY / UI                        |
|                  (Ingress, Authentication, Routing)                  |
+---------------------------------------------------------------------+
                                  |
                                  v
+=====================================================================+
|                     APPLICATION LAYERS (L02-L08, L11)                |
|       Runtime | Tools | Model | Planning | Eval | Learn | Human     |
+=====================================================================+
                                  |
                                  v
+=====================================================================+
||                      DATA LAYER (L01)                              ||
||                      [x] v3.2.1 COMPLETE                           ||
||   Identity | Events | Storage | Context | Coordination            ||
+=====================================================================+
                                  |
                                  v
+---------------------------------------------------------------------+
|                                                                     |
|          >>>  INFRASTRUCTURE LAYER (L00) -- THIS DOCUMENT  <<<      |
|                                                                     |
|  +---------------+  +---------------+  +---------------+            |
|  | Cluster       |  | Network       |  | Secrets       |            |
|  | Manager       |  | Controller    |  | Operator      |            |
|  +---------------+  +---------------+  +---------------+            |
|                                                                     |
|  +---------------+  +---------------+  +---------------+            |
|  | Resource      |  | Certificate   |  | Observability |            |
|  | Scaler        |  | Manager       |  | Stack         |            |
|  +---------------+  +---------------+  +---------------+            |
|                                                                     |
+---------------------------------------------------------------------+
                                  |
                                  v
+=====================================================================+
|                    CLOUD PROVIDER / BARE METAL                       |
|              (AWS / GCP / Azure / On-Premises Hardware)              |
+=====================================================================+
```

### 1.4 Design Principles

| Principle | Description | Enforcement |
|-----------|-------------|-------------|
| Substrate Independence | Abstract cloud provider specifics behind Kubernetes-native interfaces; workloads use PVCs, Services, and Secrets without cloud-specific annotations | Terraform modules encapsulate provider logic; Kubernetes API is the contract |
| Declarative Configuration | All infrastructure state defined in Git; GitOps controllers reconcile cluster state to declared manifests | ArgoCD enforces drift detection; manual kubectl changes trigger alerts |
| Horizontal Scalability | Each component scales independently; no single points of failure in the control path | Karpenter provisions nodes on-demand; HPA/KEDA scale pods horizontally |
| Defense in Depth | Multiple security layers: network policies, RBAC, secrets encryption, pod security standards | Cilium enforces L3/L4/L7 policies; OPA Gatekeeper validates admission |
| Observable by Default | All infrastructure components emit metrics, logs, and traces without opt-in configuration | Prometheus scrapes by annotation; all pods log to stdout for Loki collection |
| Cost Awareness | Resource tagging, right-sizing recommendations, spot instance utilization for non-critical workloads | OpenCost tracks spend; Karpenter prefers spot for batch workloads |
| Immutable Infrastructure | Node pools are replaced, not patched; cluster upgrades use rolling replacement | Karpenter provisions fresh nodes; cordoned nodes drain and terminate |

### 1.5 Technology Decisions

| Decision | Selection | Rationale |
|----------|-----------|-----------|
| Container Orchestration | Kubernetes 1.28+ (EKS/GKE/AKS) | Industry standard with GPU support and ecosystem maturity |
| Service Mesh | Cilium (eBPF-native) | 0.5ms latency overhead versus 2-5ms for Istio; native Kubernetes NetworkPolicy support |
| Node Autoscaler | Karpenter (primary), Cluster Autoscaler (fallback) | Just-in-time provisioning with 60% faster scale-up; 40% cost reduction via bin-packing |
| Secrets Backend | External Secrets Operator + HashiCorp Vault | Kubernetes-native abstraction decoupled from provider-specific secrets managers |
| Infrastructure-as-Code | Terraform | Mature multi-cloud ecosystem; state management; module registry |
| GitOps Controller | ArgoCD | CNCF graduated; multi-cluster support; ApplicationSet for fleet management |
| GPU Sharing | MIG (production), time-slicing (development) | Memory isolation prevents noisy neighbor; MIG instances appear as discrete GPUs |
| Deployment Model | Single-cloud, multi-region | Operational simplicity; DR to alternate cloud as cold standby |

---

## 2. Scope Definition

### 2.1 In Scope

The Infrastructure Layer owns the following capabilities:

| Capability | Description | Key Deliverables |
|------------|-------------|------------------|
| Cluster Lifecycle | Provisioning Kubernetes clusters, managing control plane upgrades, node pool configuration, and cluster deletion | Terraform modules for EKS/GKE/AKS; upgrade runbooks; node pool definitions |
| Network Infrastructure | Service mesh deployment, ingress controller configuration, DNS management, load balancer provisioning, network policy templates | Cilium Helm values; NGINX Ingress config; NetworkPolicy templates; ExternalDNS operator |
| Compute Scheduling | CPU, memory, and GPU resource allocation; node autoscaling; pod vertical scaling; bin-packing optimization | Karpenter Provisioners; VPA configurations; ResourceQuota templates; MIG profiles |
| Secrets Management | External secrets synchronization from Vault, secret rotation triggers, CSI secret store configuration | External Secrets Operator CRDs; SecretStore definitions; Reloader annotations |
| Certificate Management | TLS certificate automation, CA integration, certificate renewal, wildcard certificate provisioning | cert-manager ClusterIssuers; Certificate CRDs; Vault PKI integration |
| Infrastructure Observability | Prometheus deployment, Grafana provisioning, Loki log aggregation, Alertmanager routing, infrastructure dashboards | Prometheus Helm values; Grafana dashboard JSON; Loki configuration; alert rules |
| Multi-Region Topology | Cross-region cluster federation, failover procedures, global load balancing configuration | Multi-region Terraform modules; Route53/Cloud DNS failover; DR runbooks |
| Cost Management | Resource tagging standards, cost allocation labels, spot instance configuration, right-sizing recommendations | OpenCost deployment; Kubecost integration; cost attribution labels |
| Namespace Management | Namespace provisioning, default quotas, limit ranges, label standards | Namespace templates; ResourceQuota defaults; LimitRange configurations |

### 2.2 Out of Scope

| Excluded Item | Owning Layer | Boundary Rationale |
|---------------|--------------|-------------------|
| Application Kubernetes manifests | Each application layer | Infrastructure provides platform; layers define their own Deployments, Services, ConfigMaps |
| Agent sandbox isolation (gVisor/Firecracker) | L02 Agent Runtime | Runtime-specific security boundary; L02 selects and configures sandbox technology |
| LLM provider credentials | L04 Model Gateway | Business relationship management; L04 owns provider rotation and failover |
| API authentication/authorization | L09 API Gateway | Application-level security policy; L09 defines auth flows and token validation |
| Database schemas and migrations | L01 Data Layer | Infrastructure provides storage volumes; Data Layer owns schema structure |
| OPA policy content | L01 Data Layer (ABAC) | Infrastructure deploys OPA Gatekeeper; Data Layer defines Rego policies |
| Application-level metrics | Each application layer | Infrastructure provides collection infrastructure; layers define their metrics |
| Workflow state machines | L01 Data Layer (Coordination) | Infrastructure provides reliable storage; Coordination owns state transitions |
| Model serving configuration | L04 Model Gateway | Infrastructure provides GPU scheduling; Model Gateway owns inference optimization |
| Human approval workflows | L11 Human-in-Loop | Infrastructure provides notification channels; L11 owns approval logic |

### 2.3 Boundary Decisions

| Decision | Boundary Definition | Rationale |
|----------|---------------------|-----------|
| OPA Deployment vs Policy | L00 deploys OPA Gatekeeper as admission controller; L01 provides ConstraintTemplates and Constraints | Separation of mechanism (how policies execute) from policy (what rules apply); enables policy updates without infrastructure changes |
| GPU Scheduling vs Consumption | L00 configures NVIDIA device plugin, MIG partitioning, and node labels; L02/L04 request GPU resources via standard resource requests | Resource management is infrastructure concern; consumption patterns are application decisions |
| Network Policy Templates vs Application | L00 provides baseline NetworkPolicy templates (default-deny, DNS egress); application layers apply namespace-specific policies | Platform establishes security baseline; applications customize for their communication patterns |
| Storage Classes vs PVC Provisioning | L00 defines StorageClasses (performance tiers, encryption); L01 provisions PVCs using those classes | Storage tiers are infrastructure capability; data ownership and sizing are application decisions |
| Secret Mechanism vs Secret Content | L00 provides ExternalSecret CRDs and SecretStore connections; application layers define which secrets to sync and where to mount them | Secret infrastructure is centralized; secret usage is decentralized by design |
| Ingress Controller vs Ingress Resources | L00 deploys and configures NGINX Ingress Controller; L09 defines Ingress resources for routing rules | Load balancer infrastructure is shared; routing decisions are API Gateway responsibility |
| Observability Collection vs Instrumentation | L00 deploys Prometheus, Loki, Tempo collectors; application layers instrument code with OpenTelemetry SDKs | Collection infrastructure is centralized; instrumentation is application-specific |
| Node Pools vs Pod Scheduling | L00 defines node pool topology (system, general, GPU, high-memory, spot); application layers use nodeSelector/tolerations to target pools | Hardware provisioning is infrastructure; workload placement is application decision |

### 2.4 Interface Boundaries

```
+------------------------------------------------------------------+
|                    BOUNDARY: L00 <-> L01 (Data Layer)            |
+------------------------------------------------------------------+
|                                                                  |
|  L00 PROVIDES:                      L01 CONSUMES:                |
|  +----------------------------+     +---------------------------+|
|  | StorageClass: ssd-high-iops| --> | PVC for Event Store       ||
|  | StorageClass: ssd-standard | --> | PVC for SQLite databases  ||
|  | StorageClass: ssd-encrypted| --> | PVC for Identity keys     ||
|  | SecretStore: vault-backend | --> | ExternalSecret for KEK    ||
|  | Namespace: data-layer      | --> | All L01 workloads         ||
|  | NetworkPolicy: default-deny| --> | Baseline isolation        ||
|  +----------------------------+     +---------------------------+|
|                                                                  |
|  L01 OWNS:                          L00 DOES NOT TOUCH:          |
|  +----------------------------+     +---------------------------+|
|  | OPA Constraint definitions |     | Rego policy content       ||
|  | Event schema versions      |     | Schema registry data      ||
|  | PVC size requests          |     | Actual data stored        ||
|  | Service definitions        |     | Application endpoints     ||
|  +----------------------------+     +---------------------------+|
|                                                                  |
+------------------------------------------------------------------+

+------------------------------------------------------------------+
|                    BOUNDARY: L00 <-> L02 (Agent Runtime)         |
+------------------------------------------------------------------+
|                                                                  |
|  L00 PROVIDES:                      L02 CONSUMES:                |
|  +----------------------------+     +---------------------------+|
|  | Namespace: agent-pool-*    | --> | Per-pool isolation        ||
|  | ResourceQuota per namespace| --> | CPU/memory/GPU limits     ||
|  | NetworkPolicy templates    | --> | Sandbox network isolation ||
|  | GPU node pool with MIG     | --> | nvidia.com/mig-* requests ||
|  | Spot node pool             | --> | Batch evaluation jobs     ||
|  +----------------------------+     +---------------------------+|
|                                                                  |
|  L02 OWNS:                          L00 DOES NOT TOUCH:          |
|  +----------------------------+     +---------------------------+|
|  | gVisor/Kata runtime config |     | Sandbox implementation    ||
|  | Agent pod specifications   |     | Container images          ||
|  | Tool execution policies    |     | Tool definitions          ||
|  | Session lifecycle          |     | Agent state               ||
|  +----------------------------+     +---------------------------+|
|                                                                  |
+------------------------------------------------------------------+

+------------------------------------------------------------------+
|                    BOUNDARY: L00 <-> L04 (Model Gateway)         |
+------------------------------------------------------------------+
|                                                                  |
|  L00 PROVIDES:                      L04 CONSUMES:                |
|  +----------------------------+     +---------------------------+|
|  | GPU node pool (A100/H100)  | --> | Inference workloads       ||
|  | Egress NetworkPolicy       | --> | LLM provider access       ||
|  | High-bandwidth CNI         | --> | Model weight transfer     ||
|  | SecretStore for API keys   | --> | Provider credential sync  ||
|  +----------------------------+     +---------------------------+|
|                                                                  |
|  L04 OWNS:                          L00 DOES NOT TOUCH:          |
|  +----------------------------+     +---------------------------+|
|  | LLM provider selection     |     | Which models to call      ||
|  | Request routing logic      |     | Load balancing strategy   ||
|  | Semantic cache policies    |     | Cache invalidation        ||
|  | Rate limit configuration   |     | Per-provider limits       ||
|  +----------------------------+     +---------------------------+|
|                                                                  |
+------------------------------------------------------------------+

+------------------------------------------------------------------+
|                    BOUNDARY: L00 <-> L09 (API Gateway)           |
+------------------------------------------------------------------+
|                                                                  |
|  L00 PROVIDES:                      L09 CONSUMES:                |
|  +----------------------------+     +---------------------------+|
|  | NGINX Ingress Controller   | --> | Ingress resource targets  ||
|  | TLS certificates (wildcard)| --> | HTTPS termination         ||
|  | External load balancer     | --> | Public endpoint           ||
|  | ExternalDNS operator       | --> | DNS record automation     ||
|  +----------------------------+     +---------------------------+|
|                                                                  |
|  L09 OWNS:                          L00 DOES NOT TOUCH:          |
|  +----------------------------+     +---------------------------+|
|  | Ingress routing rules      |     | Path/host mappings        ||
|  | Authentication middleware  |     | Token validation          ||
|  | Rate limiting policies     |     | Per-client limits         ||
|  | API versioning strategy    |     | /v1, /v2 routing          ||
|  +----------------------------+     +---------------------------+|
|                                                                  |
+------------------------------------------------------------------+
```

---

## 3. Architecture

### 3.1 Component Diagram

```
+===========================================================================+
|                        INFRASTRUCTURE LAYER (L00)                          |
+===========================================================================+
|                                                                           |
|  EXTERNAL DEPENDENCIES                                                    |
|  +------------------+  +------------------+  +------------------+          |
|  | Cloud Provider   |  | HashiCorp Vault  |  | Git Repository   |          |
|  | APIs (AWS/GCP)   |  | (Secrets)        |  | (GitOps Source)  |          |
|  +--------+---------+  +--------+---------+  +--------+---------+          |
|           |                     |                     |                   |
|           v                     v                     v                   |
|  +--------+---------------------+---------------------+--------+          |
|  |                                                             |          |
|  |                     CLUSTER MANAGER                         |          |
|  |  +------------------+  +------------------+                  |          |
|  |  | Terraform Runner |  | ArgoCD Server    |                  |          |
|  |  | (IaC Execution)  |  | (GitOps Sync)    |                  |          |
|  |  +------------------+  +------------------+                  |          |
|  |                                                             |          |
|  +-----+-----------------------+-------------------------------+          |
|        |                       |                                          |
|        v                       v                                          |
|  +-----+-------+  +------------+------------+  +-------------------+       |
|  |             |  |                         |  |                   |       |
|  |  NETWORK    |  |    RESOURCE SCALER      |  |  SECRETS          |       |
|  |  CONTROLLER |  |                         |  |  OPERATOR         |       |
|  |             |  |  +-------+  +-------+   |  |                   |       |
|  | +---------+ |  |  |Karpen-|  | KEDA  |   |  | +-------------+   |       |
|  | | Cilium  | |  |  |ter    |  |       |   |  | | External    |   |       |
|  | | Agent   | |  |  +-------+  +-------+   |  | | Secrets Op  |   |       |
|  | +---------+ |  |                         |  | +-------------+   |       |
|  | +---------+ |  |  +-------+  +-------+   |  |                   |       |
|  | | NGINX   | |  |  | VPA   |  | HPA   |   |  | +-------------+   |       |
|  | | Ingress | |  |  +-------+  +-------+   |  | | Reloader    |   |       |
|  | +---------+ |  |                         |  | +-------------+   |       |
|  |             |  |                         |  |                   |       |
|  +------+------+  +------------+------------+  +---------+---------+       |
|         |                      |                         |                |
|         v                      v                         v                |
|  +------+----------------------+-------------------------+---------+      |
|  |                                                                 |      |
|  |                    CERTIFICATE MANAGER                          |      |
|  |  +------------------+  +------------------+                      |      |
|  |  | cert-manager     |  | ClusterIssuers   |                      |      |
|  |  | Controller       |  | (Let's Encrypt,  |                      |      |
|  |  |                  |  |  Vault PKI)      |                      |      |
|  |  +------------------+  +------------------+                      |      |
|  |                                                                 |      |
|  +-----------------------------------------------------------------+      |
|                                    |                                      |
|                                    v                                      |
|  +-----------------------------------------------------------------+      |
|  |                                                                 |      |
|  |                    OBSERVABILITY STACK                          |      |
|  |  +------------+  +------------+  +------------+  +------------+ |      |
|  |  | Prometheus |  | Grafana    |  | Loki       |  | Tempo      | |      |
|  |  | + Thanos   |  |            |  |            |  | (Tracing)  | |      |
|  |  +------------+  +------------+  +------------+  +------------+ |      |
|  |                                                                 |      |
|  |  +------------+  +------------+  +------------+                 |      |
|  |  | Alertman-  |  | OpenCost   |  | DCGM       |                 |      |
|  |  | ager       |  |            |  | Exporter   |                 |      |
|  |  +------------+  +------------+  +------------+                 |      |
|  |                                                                 |      |
|  +-----------------------------------------------------------------+      |
|                                                                           |
+===========================================================================+
                                    |
                                    v
                    +-------------------------------+
                    |      TO ALL LAYERS (L01-L11)  |
                    |  - Storage Classes            |
                    |  - Network Policies           |
                    |  - Secret Injection           |
                    |  - Resource Quotas            |
                    |  - TLS Certificates           |
                    |  - Metrics Collection         |
                    +-------------------------------+
```

### 3.2 Component Inventory

| Component | Type | Purpose | Stateful | Scaling Model | Technology |
|-----------|------|---------|----------|---------------|------------|
| Cluster Manager | Controller | Kubernetes lifecycle, IaC execution, GitOps sync | Yes (Terraform state, ArgoCD state) | N/A (external) | Terraform, ArgoCD |
| Network Controller | DaemonSet + Deployment | Service mesh, ingress, DNS, network policies | No | Horizontal (ingress), per-node (Cilium) | Cilium, NGINX Ingress |
| Secrets Operator | Deployment | Secret synchronization from Vault to Kubernetes | No | Horizontal | External Secrets Operator |
| Resource Scaler | Deployment | Node and pod autoscaling, bin-packing | No | Horizontal | Karpenter, KEDA, VPA |
| Certificate Manager | Deployment | TLS certificate automation | Yes (certificate state) | Horizontal | cert-manager |
| Observability Stack | StatefulSet + Deployment | Metrics, logs, traces, alerting | Yes (TSDB, log storage) | Horizontal (queries), Vertical (storage) | Prometheus, Loki, Tempo, Grafana |

### 3.3 Component Specifications

#### 3.3.1 Cluster Manager

**Purpose:** Provisions and maintains Kubernetes clusters across regions, executes infrastructure-as-code changes, and synchronizes workload deployments from Git repositories.

**Subcomponents:**

| Subcomponent | Function | Deployment |
|--------------|----------|------------|
| Terraform Runner | Executes cluster provisioning and updates | CI/CD pipeline (GitHub Actions, GitLab CI) |
| ArgoCD Server | Watches Git repos, syncs Kubernetes manifests | In-cluster Deployment (HA: 3 replicas) |
| ArgoCD ApplicationSet | Generates Applications for multi-cluster/multi-env | In-cluster CRD |
| ArgoCD Notifications | Sends deployment alerts to Slack/PagerDuty | In-cluster Deployment |

**Configuration Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cluster.kubernetes_version` | string | `1.28` | Target Kubernetes version |
| `cluster.region` | string | required | Primary cloud region |
| `cluster.dr_region` | string | optional | Disaster recovery region |
| `argocd.sync_policy` | enum | `automated` | `manual`, `automated`, `automated-prune` |
| `argocd.self_heal` | bool | `true` | Auto-revert manual changes |
| `terraform.state_backend` | string | `s3` | State storage: `s3`, `gcs`, `azurerm` |

**Dependencies:**

| Type | Dependency | Purpose |
|------|------------|---------|
| External | Cloud Provider API | Node provisioning, networking, storage |
| External | Git Repository | Source of truth for manifests |
| External | Terraform State Backend | IaC state persistence |
| Internal | Observability Stack | Deployment metrics and alerts |

**Terraform Module Structure:**

```
terraform/
|-- modules/
|   |-- eks-cluster/
|   |   |-- main.tf
|   |   |-- variables.tf
|   |   |-- outputs.tf
|   |   |-- node-pools.tf
|   |   |-- iam.tf
|   |-- gke-cluster/
|   |-- aks-cluster/
|   |-- networking/
|   |   |-- vpc.tf
|   |   |-- subnets.tf
|   |   |-- nat-gateway.tf
|   |-- observability/
|-- environments/
|   |-- production/
|   |   |-- us-west-2/
|   |   |-- us-east-1/
|   |-- staging/
|   |-- development/
|-- terragrunt.hcl
```

---

#### 3.3.2 Network Controller

**Purpose:** Manages service mesh connectivity, ingress traffic routing, DNS resolution, and network policy enforcement across all namespaces.

**Subcomponents:**

| Subcomponent | Function | Deployment |
|--------------|----------|------------|
| Cilium Agent | eBPF-based networking, L3/L4/L7 policy enforcement | DaemonSet (every node) |
| Cilium Operator | Manages Cilium CRDs, IPAM | Deployment (2 replicas) |
| NGINX Ingress Controller | HTTP/HTTPS ingress, TLS termination | Deployment (3+ replicas, HPA) |
| ExternalDNS | Syncs Ingress/Service to Route53/CloudDNS | Deployment (1 replica) |
| CoreDNS | Cluster-internal DNS resolution | Deployment (managed by Kubernetes) |

**Configuration Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cilium.tunnel_mode` | enum | `vxlan` | `vxlan`, `geneve`, `disabled` (native routing) |
| `cilium.enable_hubble` | bool | `true` | Enable Hubble observability |
| `cilium.policy_enforcement` | enum | `default` | `default`, `always`, `never` |
| `ingress.replica_count` | int | `3` | NGINX Ingress replicas |
| `ingress.service_type` | enum | `LoadBalancer` | `LoadBalancer`, `NodePort` |
| `ingress.rate_limit_rps` | int | `100` | Default requests per second per client |
| `ingress.rate_limit_connections` | int | `50` | Max concurrent connections per client |
| `ingress.rate_limit_burst` | int | `200` | Burst capacity for rate limiting |
| `externaldns.provider` | string | `aws` | DNS provider: `aws`, `google`, `azure` |
| `externaldns.txt_owner_id` | string | required | Unique identifier for DNS records |

**NGINX Ingress Rate Limiting Configuration:**

L00 Infrastructure provides global rate limiting defaults. L09 API Gateway applies per-route overrides via Ingress annotations.

```yaml
# L00 Helm values for NGINX Ingress rate limiting
# charts/infrastructure/nginx-ingress/values.yaml
controller:
  config:
    # Global rate limiting defaults
    limit-req-status-code: "429"
    limit-conn-status-code: "429"
    
  # ConfigMap with rate limiting zones
  addHeaders:
    X-RateLimit-Limit: "$limit_req_status"
    
# Rate limiting ConfigMap
kind: ConfigMap
metadata:
  name: nginx-ingress-rate-limit-config
  namespace: ingress-nginx
data:
  # Limit zones defined at L00 level
  http-snippet: |
    # Per-client rate limiting zone (10MB shared memory)
    limit_req_zone $binary_remote_addr zone=global_rate_limit:10m rate={{ .Values.ingress.rate_limit_rps }}r/s;
    # Per-client connection limiting
    limit_conn_zone $binary_remote_addr zone=global_conn_limit:10m;
    
  server-snippet: |
    # Apply global rate limit by default
    limit_req zone=global_rate_limit burst={{ .Values.ingress.rate_limit_burst }} nodelay;
    limit_conn global_conn_limit {{ .Values.ingress.rate_limit_connections }};
```

**L09 API Gateway Rate Limit Override Pattern:**

L09 can override L00 defaults using Ingress annotations:

```yaml
# L09 applies per-route rate limits via annotations
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-gateway-ingress
  namespace: api-gateway
  annotations:
    # Override L00 defaults for specific routes
    nginx.ingress.kubernetes.io/limit-rps: "500"
    nginx.ingress.kubernetes.io/limit-burst-multiplier: "5"
    nginx.ingress.kubernetes.io/limit-connections: "100"
    # Custom rate limit response
    nginx.ingress.kubernetes.io/server-snippet: |
      limit_req zone=api_gateway_zone burst=1000 delay=500;
spec:
  ingressClassName: nginx
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: api-gateway
                port:
                  number: 8080
```

**Rate Limiting Metrics (exported to Prometheus):**

| Metric | Description | Labels |
|--------|-------------|--------|
| `nginx_ingress_controller_requests_total` | Total requests | status, host |
| `nginx_ingress_controller_request_duration_seconds` | Request latency | host, path |
| `nginx_ingress_controller_response_size_bytes` | Response size | host |
| Custom: `nginx_rate_limit_rejected_total` | Requests rejected by rate limit | zone, host |

**Network Policy Templates:**

```yaml
# Default deny-all ingress for namespace isolation
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: "{{ namespace }}"
spec:
  podSelector: {}
  policyTypes:
    - Ingress

---
# Allow DNS egress (required for all namespaces)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns-egress
  namespace: "{{ namespace }}"
spec:
  podSelector: {}
  policyTypes:
    - Egress
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
```

---

#### 3.3.3 Secrets Operator

**Purpose:** Synchronizes secrets from HashiCorp Vault to Kubernetes Secrets, handles rotation triggers, and provides CSI-based secret mounting.

**Subcomponents:**

| Subcomponent | Function | Deployment |
|--------------|----------|------------|
| External Secrets Operator | Watches ExternalSecret CRDs, syncs to K8s Secrets | Deployment (2 replicas) |
| SecretStore Controller | Manages Vault connections per namespace | Part of ESO |
| Reloader | Triggers pod rollouts on Secret/ConfigMap changes | Deployment (1 replica) |
| Secrets Store CSI Driver | Mounts secrets as volumes (optional) | DaemonSet |

**Configuration Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `vault.address` | string | required | Vault server URL |
| `vault.auth_method` | enum | `kubernetes` | `kubernetes`, `approle`, `token` |
| `vault.kubernetes_role` | string | required | Vault role for K8s auth |
| `eso.refresh_interval` | duration | `1h` | Default secret refresh interval |
| `eso.retry_interval` | duration | `10s` | Retry interval on sync failure |
| `reloader.enabled` | bool | `true` | Enable automatic pod rollouts |

**SecretStore Definition:**

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: vault-backend
spec:
  provider:
    vault:
      server: "https://vault.example.com"
      path: "secret"
      version: "v2"
      auth:
        kubernetes:
          mountPath: "kubernetes"
          role: "external-secrets"
          serviceAccountRef:
            name: "external-secrets"
            namespace: "infrastructure"
```

**ExternalSecret Example:**

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: database-credentials
  namespace: data-layer
spec:
  refreshInterval: "1h"
  secretStoreRef:
    name: vault-backend
    kind: ClusterSecretStore
  target:
    name: database-credentials
    creationPolicy: Owner
  data:
    - secretKey: username
      remoteRef:
        key: secret/data/data-layer/database
        property: username
    - secretKey: password
      remoteRef:
        key: secret/data/data-layer/database
        property: password
```

---

#### 3.3.4 Resource Scaler

**Purpose:** Manages node-level autoscaling via Karpenter, pod-level scaling via HPA/VPA/KEDA, and GPU resource scheduling with MIG support.

**Subcomponents:**

| Subcomponent | Function | Deployment |
|--------------|----------|------------|
| Karpenter Controller | Just-in-time node provisioning | Deployment (2 replicas) |
| KEDA Operator | Event-driven pod autoscaling | Deployment (2 replicas) |
| VPA Recommender | Vertical pod autoscaling recommendations | Deployment (1 replica) |
| VPA Updater | Applies VPA recommendations | Deployment (1 replica) |
| NVIDIA Device Plugin | GPU resource advertisement | DaemonSet (GPU nodes) |
| DCGM Exporter | GPU metrics for Prometheus | DaemonSet (GPU nodes) |

**Configuration Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `karpenter.instance_types` | list | provider-specific | Allowed EC2/GCE instance types |
| `karpenter.spot_enabled` | bool | `true` | Enable spot/preemptible instances |
| `karpenter.ttl_seconds_after_empty` | int | `30` | Node termination delay after empty |
| `keda.polling_interval` | int | `30` | Seconds between scale checks |
| `vpa.update_mode` | enum | `Auto` | `Off`, `Initial`, `Recreate`, `Auto` |
| `gpu.mig_strategy` | enum | `mixed` | `none`, `single`, `mixed` |

**Karpenter Provisioner:**

```yaml
apiVersion: karpenter.sh/v1alpha5
kind: Provisioner
metadata:
  name: default
spec:
  requirements:
    - key: karpenter.sh/capacity-type
      operator: In
      values: ["on-demand", "spot"]
    - key: kubernetes.io/arch
      operator: In
      values: ["amd64"]
    - key: node.kubernetes.io/instance-type
      operator: In
      values:
        - m5.large
        - m5.xlarge
        - m5.2xlarge
        - m5.4xlarge
  limits:
    resources:
      cpu: 1000
      memory: 2000Gi
  providerRef:
    name: default
  ttlSecondsAfterEmpty: 30
  ttlSecondsUntilExpired: 604800  # 7 days

---
apiVersion: karpenter.sh/v1alpha5
kind: Provisioner
metadata:
  name: gpu-inference
spec:
  requirements:
    - key: karpenter.sh/capacity-type
      operator: In
      values: ["on-demand"]
    - key: node.kubernetes.io/instance-type
      operator: In
      values:
        - g5.xlarge
        - g5.2xlarge
        - p4d.24xlarge
  taints:
    - key: nvidia.com/gpu
      value: "true"
      effect: NoSchedule
  labels:
    node-pool: gpu-inference
  limits:
    resources:
      nvidia.com/gpu: 20
  providerRef:
    name: default
```

**KEDA ScaledObject Example:**

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: agent-pool-scaler
  namespace: agent-pool-default
spec:
  scaleTargetRef:
    name: agent-worker
  minReplicaCount: 2
  maxReplicaCount: 50
  pollingInterval: 30
  triggers:
    - type: prometheus
      metadata:
        serverAddress: http://prometheus.infrastructure:9090
        metricName: agent_queue_depth
        threshold: "10"
        query: |
          sum(agent_pending_tasks{namespace="agent-pool-default"})
```

**PriorityClasses:**

Infrastructure Layer defines PriorityClasses to ensure critical workloads are scheduled before optional ones during resource contention. These classes apply cluster-wide and are referenced by pods in their spec.

```yaml
# PriorityClass for critical infrastructure components (CNI, CSI, DNS)
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: system-critical
  labels:
    layer: l00
value: 1000000000
globalDefault: false
description: "Critical infrastructure components that must run (CNI, CSI, CoreDNS)"
---
# PriorityClass for infrastructure services (observability, secrets)
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: infrastructure-high
  labels:
    layer: l00
value: 100000000
globalDefault: false
description: "L00 infrastructure services (Prometheus, Vault, cert-manager)"
---
# PriorityClass for core platform services (Data Layer, Model Gateway)
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: platform-high
  labels:
    layer: l00
value: 10000000
globalDefault: false
description: "Core platform services (L01 Data Layer, L04 Model Gateway)"
---
# Default PriorityClass for application workloads
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: application-default
  labels:
    layer: l00
value: 0
globalDefault: true
description: "Default for application workloads"
---
# PriorityClass for batch and evaluation workloads
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: batch-low
  labels:
    layer: l00
value: -100
globalDefault: false
description: "Batch processing, evaluation, and training workloads"
preemptionPolicy: Never
```

**PriorityClass Usage by Layer:**

| Layer | Recommended PriorityClass | Rationale |
|-------|---------------------------|-----------|
| L00 Infrastructure | system-critical, infrastructure-high | Must run for cluster health |
| L01 Data Layer | platform-high | Core data services |
| L02 Agent Runtime | application-default | Standard agent workloads |
| L04 Model Gateway | platform-high | LLM access critical path |
| L06 Evaluation | batch-low | Can be preempted for prod |
| L07 Learning | batch-low | Background optimization |
| L09 API Gateway | platform-high | External traffic entry |

---

**Purpose:** Automates TLS certificate issuance and renewal using Let's Encrypt or Vault PKI, manages ClusterIssuers, and provisions certificates for Ingress resources.

**Subcomponents:**

| Subcomponent | Function | Deployment |
|--------------|----------|------------|
| cert-manager Controller | Watches Certificate CRDs, issues/renews certs | Deployment (2 replicas) |
| cert-manager Webhook | Validates Certificate resources | Deployment (2 replicas) |
| cert-manager CAInjector | Injects CA bundles into webhooks | Deployment (1 replica) |

**Configuration Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `certmanager.default_issuer` | string | `letsencrypt-prod` | Default ClusterIssuer name |
| `certmanager.acme_email` | string | required | Email for Let's Encrypt registration |
| `certmanager.dns_provider` | string | `route53` | DNS-01 challenge provider |
| `certmanager.renewal_before` | duration | `720h` | Renew certificates 30 days before expiry |

**ClusterIssuer Definitions:**

```yaml
# Production Let's Encrypt with DNS-01 challenge
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: platform-team@example.com
    privateKeySecretRef:
      name: letsencrypt-prod-account-key
    solvers:
      - dns01:
          route53:
            region: us-west-2
            hostedZoneID: Z1234567890ABC

---
# Vault PKI for internal certificates
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: vault-pki
spec:
  vault:
    server: https://vault.example.com
    path: pki/sign/internal
    auth:
      kubernetes:
        mountPath: /v1/auth/kubernetes
        role: cert-manager
        serviceAccountRef:
          name: cert-manager
          namespace: infrastructure
```

**Certificate Example:**

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: wildcard-example-com
  namespace: infrastructure
spec:
  secretName: wildcard-example-com-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
    - "*.example.com"
    - "example.com"
  duration: 2160h    # 90 days
  renewBefore: 720h  # 30 days
```

---

#### 3.3.6 Observability Stack

**Purpose:** Deploys and manages infrastructure-level metrics collection, log aggregation, distributed tracing, and alerting for all L00 components and Kubernetes infrastructure.

**Subcomponents:**

| Subcomponent | Function | Deployment |
|--------------|----------|------------|
| Prometheus | Metrics collection and storage | StatefulSet (2 replicas, HA) |
| Thanos Sidecar | Long-term metrics storage to S3/GCS | Sidecar to Prometheus |
| Thanos Query | Federated metrics queries | Deployment (2 replicas) |
| Grafana | Visualization and dashboards | Deployment (2 replicas) |
| Loki | Log aggregation | StatefulSet (3 replicas) |
| Promtail | Log collection agent | DaemonSet |
| Tempo | Distributed tracing backend | StatefulSet (3 replicas) |
| Alertmanager | Alert routing and deduplication | StatefulSet (3 replicas, HA) |
| OpenCost | Cost attribution and tracking | Deployment (1 replica) |

**Configuration Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prometheus.retention` | duration | `15d` | Local metric retention |
| `prometheus.storage_size` | string | `100Gi` | PVC size for Prometheus |
| `thanos.bucket` | string | required | S3/GCS bucket for long-term storage |
| `loki.retention` | duration | `30d` | Log retention period |
| `loki.storage_size` | string | `200Gi` | PVC size for Loki |
| `tempo.retention` | duration | `7d` | Trace retention period |
| `grafana.admin_password` | secret | required | Grafana admin password (from Vault) |
| `alertmanager.slack_webhook` | secret | optional | Slack notification webhook |
| `alertmanager.pagerduty_key` | secret | optional | PagerDuty integration key |

**Prometheus ServiceMonitor:**

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: infrastructure-components
  namespace: infrastructure
spec:
  selector:
    matchLabels:
      app.kubernetes.io/part-of: infrastructure
  endpoints:
    - port: metrics
      interval: 30s
      path: /metrics
```

**Alertmanager Route Configuration:**

```yaml
apiVersion: monitoring.coreos.com/v1alpha1
kind: AlertmanagerConfig
metadata:
  name: infrastructure-alerts
  namespace: infrastructure
spec:
  route:
    groupBy: ['alertname', 'severity']
    groupWait: 30s
    groupInterval: 5m
    repeatInterval: 4h
    receiver: 'infrastructure-team'
    routes:
      - match:
          severity: critical
        receiver: 'pagerduty-critical'
      - match:
          severity: warning
        receiver: 'slack-warnings'
  receivers:
    - name: 'infrastructure-team'
      slackConfigs:
        - channel: '#infrastructure-alerts'
          sendResolved: true
    - name: 'pagerduty-critical'
      pagerdutyConfigs:
        - serviceKey:
            name: pagerduty-secret
            key: service-key
    - name: 'slack-warnings'
      slackConfigs:
        - channel: '#infrastructure-warnings'
```

---

### 3.4 Node Pool Architecture

Infrastructure Layer defines five node pools optimized for agent workload diversity:

| Pool Name | Instance Types | Min/Max | Taints | Labels | Target Workloads |
|-----------|---------------|---------|--------|--------|------------------|
| system | m5.large, m5.xlarge | 3/3 | `node-role.kubernetes.io/system:NoSchedule` | `node-pool=system` | CoreDNS, kube-proxy, metrics-server, ArgoCD |
| general | m5.xlarge, m5.2xlarge, m5.4xlarge | 2/20 | None | `node-pool=general` | Data Layer, Planning Layer, stateless services |
| gpu-inference | g5.xlarge, g5.2xlarge, p4d.24xlarge | 0/10 | `nvidia.com/gpu=true:NoSchedule` | `node-pool=gpu-inference`, `nvidia.com/mig-strategy=mixed` | Model Gateway, local inference |
| high-memory | r5.4xlarge, r5.8xlarge | 0/5 | `memory=high:NoSchedule` | `node-pool=high-memory` | Context assembly, large document processing |
| spot-batch | Mixed (m5, c5, r5) | 0/50 | `lifecycle=spot:NoSchedule` | `node-pool=spot-batch`, `karpenter.sh/capacity-type=spot` | Evaluation jobs, batch analytics, training prep |

**Node Pool Diagram:**

```
+===========================================================================+
|                         KUBERNETES CLUSTER                                 |
+===========================================================================+
|                                                                           |
|  SYSTEM POOL (Fixed: 3 nodes)                                             |
|  +-------+  +-------+  +-------+                                          |
|  | m5.lg |  | m5.lg |  | m5.lg |  Taints: system:NoSchedule               |
|  | node-1|  | node-2|  | node-3|  Workloads: CoreDNS, ArgoCD, monitoring  |
|  +-------+  +-------+  +-------+                                          |
|                                                                           |
|  GENERAL POOL (Autoscale: 2-20 nodes)                                     |
|  +--------+  +--------+  +--------+  +--------+                           |
|  | m5.xl  |  | m5.2xl |  | m5.4xl |  | ...    |  No taints                |
|  | node-1 |  | node-2 |  | node-3 |  |        |  Workloads: L01-L11      |
|  +--------+  +--------+  +--------+  +--------+                           |
|                                                                           |
|  GPU-INFERENCE POOL (Autoscale: 0-10 nodes)                               |
|  +------------+  +------------+  +------------+                           |
|  | g5.xlarge  |  | g5.2xlarge |  | p4d.24xl   |  Taints: gpu:NoSchedule  |
|  | A10G (1)   |  | A10G (1)   |  | A100 (8)   |  MIG: 3g.40gb profile    |
|  | MIG: 4x    |  | MIG: 4x    |  | MIG: 3x ea |  Workloads: Model GW     |
|  +------------+  +------------+  +------------+                           |
|                                                                           |
|  HIGH-MEMORY POOL (Autoscale: 0-5 nodes)                                  |
|  +------------+  +------------+                                           |
|  | r5.4xlarge |  | r5.8xlarge |  Taints: memory=high:NoSchedule          |
|  | 128GB RAM  |  | 256GB RAM  |  Workloads: Context assembly             |
|  +------------+  +------------+                                           |
|                                                                           |
|  SPOT-BATCH POOL (Autoscale: 0-50 nodes)                                  |
|  +--------+  +--------+  +--------+  +--------+  +--------+               |
|  | m5.xl  |  | c5.2xl |  | r5.xl  |  | m5.2xl |  | ...    |  SPOT        |
|  | spot   |  | spot   |  | spot   |  | spot   |  |        |  INSTANCES   |
|  +--------+  +--------+  +--------+  +--------+  +--------+               |
|  Taints: lifecycle=spot:NoSchedule                                        |
|  Workloads: Evaluation, batch jobs, training data prep                    |
|                                                                           |
+===========================================================================+
```

**GPU MIG Configuration:**

| GPU Type | MIG Profile | Instances | Memory/Instance | Use Case |
|----------|-------------|-----------|-----------------|----------|
| A100 80GB | 3g.40gb | 2 | 40GB | Large model inference |
| A100 80GB | 2g.20gb | 4 | 20GB | Medium model inference |
| A100 80GB | 1g.10gb | 7 | 10GB | Small model inference |
| A10G 24GB | 1g.6gb | 4 | 6GB | Development/staging |
| H100 80GB | 3g.40gb | 2 | 40GB | High-throughput inference |

---

### 3.5 Namespace Strategy

Infrastructure Layer provisions and manages namespaces with tiered resource policies:

**Namespace Hierarchy:**

```
Namespaces:
|
|-- kube-system                    [SYSTEM - Kubernetes core]
|   |-- coredns
|   |-- kube-proxy
|   |-- metrics-server
|
|-- infrastructure                 [PLATFORM - L00 components]
|   |-- argocd
|   |-- prometheus
|   |-- loki
|   |-- cert-manager
|   |-- external-secrets
|   |-- karpenter
|
|-- data-layer                     [APPLICATION - L01]
|   |-- event-store
|   |-- identity-service
|   |-- coordination-service
|
|-- agent-pool-default             [AGENT - L02 default pool]
|-- agent-pool-research            [AGENT - L02 research pool]
|-- agent-pool-coding              [AGENT - L02 coding pool]
|
|-- model-gateway                  [APPLICATION - L04]
|-- planning-layer                 [APPLICATION - L05]
|-- evaluation-layer               [APPLICATION - L06]
|-- api-gateway                    [APPLICATION - L09]
|-- ui-layer                       [APPLICATION - L10]
```

**Namespace Tier Definitions:**

| Tier | Namespaces | Default CPU Quota | Default Memory Quota | Default GPU Quota | Default PVC Quota |
|------|------------|-------------------|----------------------|-------------------|-------------------|
| SYSTEM | kube-system | Unlimited | Unlimited | 0 | 50Gi |
| PLATFORM | infrastructure | 50 cores | 100Gi | 0 | 500Gi |
| APPLICATION | data-layer, model-gateway, api-gateway, etc. | 20 cores | 50Gi | 4 | 200Gi |
| AGENT | agent-pool-* | 10 cores | 20Gi | 2 | 50Gi |

**ResourceQuota Template:**

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: default-quota
  namespace: "{{ namespace }}"
spec:
  hard:
    requests.cpu: "{{ cpu_request_quota }}"
    requests.memory: "{{ memory_request_quota }}"
    limits.cpu: "{{ cpu_limit_quota }}"
    limits.memory: "{{ memory_limit_quota }}"
    requests.nvidia.com/gpu: "{{ gpu_quota }}"
    persistentvolumeclaims: "{{ pvc_count_quota }}"
    requests.storage: "{{ storage_quota }}"
    pods: "{{ pod_quota }}"
    services: "{{ service_quota }}"
    secrets: "{{ secret_quota }}"
    configmaps: "{{ configmap_quota }}"
```

**LimitRange Template:**

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: default-limits
  namespace: "{{ namespace }}"
spec:
  limits:
    - type: Container
      default:
        cpu: "500m"
        memory: "512Mi"
      defaultRequest:
        cpu: "100m"
        memory: "128Mi"
      max:
        cpu: "4"
        memory: "8Gi"
      min:
        cpu: "50m"
        memory: "64Mi"
    - type: PersistentVolumeClaim
      max:
        storage: "100Gi"
      min:
        storage: "1Gi"
```

**Namespace Labels Standard:**

| Label | Required | Values | Purpose |
|-------|----------|--------|---------|
| `layer` | Yes | `l00`, `l01`, `l02`, ... `l11` | Layer ownership |
| `tier` | Yes | `system`, `platform`, `application`, `agent` | Resource policy tier |
| `cost-center` | Yes | Team identifier | Cost attribution |
| `environment` | Yes | `production`, `staging`, `development` | Environment classification |
| `managed-by` | Yes | `argocd`, `terraform`, `manual` | Change management |

---

## 4. Interfaces

### 4.1 Provided Interfaces

Infrastructure Layer exposes the following interfaces to dependent layers (L01-L11):

#### 4.1.1 Storage Provisioning Interface

| Attribute | Value |
|-----------|-------|
| Consumer(s) | All layers (L01-L11) |
| Protocol | Kubernetes API (PersistentVolumeClaim) |
| Auth Required | RBAC (namespace-scoped) |
| Rate Limited | No (cloud provider limits apply) |

**Operations:**

| Operation | Input | Output | Description |
|-----------|-------|--------|-------------|
| Provision Volume | PVC spec | Bound PVC | Create storage volume from StorageClass |
| Expand Volume | PVC with increased size | Expanded PVC | Resize existing volume (if supported) |
| Delete Volume | PVC deletion | Released PV | Remove storage and reclaim resources |
| Snapshot Volume | VolumeSnapshot spec | VolumeSnapshot | Point-in-time backup (CSI driver dependent) |

**Contract:**

```python
from typing import Protocol, Literal
from dataclasses import dataclass

StorageClassName = Literal[
    "ssd-high-iops",    # 16000 IOPS, Event Store, hot data
    "ssd-standard",     # 3000 IOPS, SQLite, general workloads
    "ssd-encrypted",    # 3000 IOPS, encryption at rest, identity keys
    "hdd-archive"       # 500 IOPS, cold archives, backups
]

@dataclass
class PersistentVolumeClaimSpec:
    name: str
    namespace: str
    storage_class: StorageClassName
    size_gb: int
    access_modes: list[Literal["ReadWriteOnce", "ReadWriteMany", "ReadOnlyMany"]]

@dataclass
class PersistentVolumeClaim:
    name: str
    namespace: str
    status: Literal["Pending", "Bound", "Lost"]
    volume_name: str | None
    capacity_gb: int

class StorageProvisioner(Protocol):
    """
    L00 provides StorageClasses; layers request storage via PVC.
    
    Infrastructure Layer owns StorageClass definitions and CSI driver
    configuration. Application layers create PVCs referencing these
    classes and receive provisioned volumes.
    """
    
    def list_storage_classes(self) -> list[StorageClassName]:
        """
        Return available storage tiers.
        
        Returns:
            List of StorageClass names available in the cluster.
        """
        ...
    
    def provision_volume(self, spec: PersistentVolumeClaimSpec) -> PersistentVolumeClaim:
        """
        Provision storage volume for a layer.
        
        Args:
            spec: PVC specification including size, class, and access mode.
            
        Returns:
            Bound PVC with volume details.
            
        Raises:
            E0001: Quota exceeded for namespace.
            E0002: Invalid StorageClass name.
            E0003: Requested size exceeds maximum for class.
        """
        ...
    
    def expand_volume(self, name: str, namespace: str, new_size_gb: int) -> PersistentVolumeClaim:
        """
        Expand existing volume (online expansion if supported).
        
        Args:
            name: PVC name.
            namespace: PVC namespace.
            new_size_gb: New size (must be larger than current).
            
        Returns:
            Updated PVC with new capacity.
            
        Raises:
            E0004: Volume shrink not supported.
            E0005: StorageClass does not support expansion.
        """
        ...
```

**StorageClass Definitions:**

| Class Name | Provisioner | IOPS | Throughput | Encryption | Expansion | Use Case |
|------------|-------------|------|------------|------------|-----------|----------|
| `ssd-high-iops` | ebs.csi.aws.com | 16000 | 1000 MB/s | Optional | Yes | Event Store segments, hot data |
| `ssd-standard` | ebs.csi.aws.com | 3000 | 125 MB/s | Optional | Yes | SQLite databases, general workloads |
| `ssd-encrypted` | ebs.csi.aws.com | 3000 | 125 MB/s | Required | Yes | Identity keys, credential storage |
| `hdd-archive` | ebs.csi.aws.com | 500 | 500 MB/s | Optional | Yes | Cold archives, backup storage |

**StorageClass Manifest:**

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ssd-high-iops
  annotations:
    storageclass.kubernetes.io/is-default-class: "false"
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "16000"
  throughput: "1000"
  fsType: ext4
reclaimPolicy: Delete
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer

---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ssd-encrypted
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "3000"
  encrypted: "true"
  kmsKeyId: alias/infrastructure-storage-key
  fsType: ext4
reclaimPolicy: Retain
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
```

---

#### 4.1.2 Secrets Injection Interface

| Attribute | Value |
|-----------|-------|
| Consumer(s) | All layers (L01-L11) |
| Protocol | Kubernetes API (ExternalSecret CRD) |
| Auth Required | RBAC (namespace-scoped) |
| Rate Limited | Yes (Vault API limits) |

**Operations:**

| Operation | Input | Output | Description |
|-----------|-------|--------|-------------|
| Create ExternalSecret | ExternalSecret spec | Synced K8s Secret | Define secret sync from Vault |
| Get Secret | Secret name, namespace | Secret data | Retrieve synced Kubernetes Secret |
| Force Refresh | ExternalSecret name | Updated Secret | Trigger immediate sync |
| List Secrets | Namespace | Secret list | Enumerate available secrets |

**Contract:**

```python
from typing import Protocol, Literal
from dataclasses import dataclass
from datetime import timedelta

@dataclass
class SecretReference:
    vault_path: str           # e.g., "secret/data/data-layer/database"
    property_name: str        # e.g., "password"
    target_key: str           # Key name in K8s Secret

@dataclass
class ExternalSecretSpec:
    name: str
    namespace: str
    secret_store: str         # ClusterSecretStore or SecretStore name
    target_secret_name: str   # Name of resulting K8s Secret
    refresh_interval: timedelta
    data: list[SecretReference]

@dataclass 
class SyncedSecret:
    name: str
    namespace: str
    status: Literal["SecretSynced", "SecretSyncError", "SecretDeleted"]
    last_sync: str            # ISO timestamp
    keys: list[str]           # Available keys in secret

class SecretsProvider(Protocol):
    """
    L00 syncs secrets from Vault; layers reference as K8s Secrets.
    
    Infrastructure Layer owns SecretStore configuration and ESO deployment.
    Application layers create ExternalSecret CRDs to define which secrets
    to sync and where to mount them.
    """
    
    def create_external_secret(self, spec: ExternalSecretSpec) -> SyncedSecret:
        """
        Define secret synchronization from Vault to Kubernetes.
        
        Args:
            spec: ExternalSecret specification with Vault paths and refresh interval.
            
        Returns:
            SyncedSecret with status and available keys.
            
        Raises:
            E0200: SecretStore not found.
            E0201: Vault path not accessible (permission denied).
            E0202: Invalid refresh interval (minimum 1m).
        """
        ...
    
    def get_secret(self, name: str, namespace: str) -> dict[str, bytes]:
        """
        Retrieve synced Kubernetes Secret data.
        
        Args:
            name: Secret name.
            namespace: Secret namespace.
            
        Returns:
            Dictionary of secret keys to values (base64 decoded).
            
        Raises:
            E0203: Secret not found.
            E0204: Secret sync pending (not yet available).
        """
        ...
    
    def force_refresh(self, external_secret_name: str, namespace: str) -> SyncedSecret:
        """
        Trigger immediate secret refresh from Vault.
        
        Args:
            external_secret_name: Name of ExternalSecret CRD.
            namespace: Namespace of ExternalSecret.
            
        Returns:
            Updated SyncedSecret with new sync timestamp.
            
        Raises:
            E0205: ExternalSecret not found.
            E0206: Vault unavailable.
            E0207: Vault token renewal failed.
        """
        ...
```

**Available SecretStores:**

| SecretStore | Type | Scope | Backend | Use Case |
|-------------|------|-------|---------|----------|
| `vault-backend` | ClusterSecretStore | All namespaces | Vault KV v2 | General secrets |
| `vault-pki` | ClusterSecretStore | All namespaces | Vault PKI | Certificate private keys |
| `aws-secrets-manager` | ClusterSecretStore | All namespaces | AWS SM | Cloud-native secrets |

---

#### 4.1.3 Network Policy Interface

| Attribute | Value |
|-----------|-------|
| Consumer(s) | All layers (L01-L11) |
| Protocol | Kubernetes API (NetworkPolicy) |
| Auth Required | RBAC (namespace-scoped) |
| Rate Limited | No |

**Operations:**

| Operation | Input | Output | Description |
|-----------|-------|--------|-------------|
| Apply Namespace Isolation | Namespace | NetworkPolicy | Default deny-all for namespace |
| Allow Egress | Source, destination, ports | NetworkPolicy | Permit outbound traffic |
| Allow Ingress | Source, destination, ports | NetworkPolicy | Permit inbound traffic |
| Allow LLM Egress | Namespace | CiliumNetworkPolicy | Permit egress to LLM providers |

**Contract:**

```python
from typing import Protocol, Literal
from dataclasses import dataclass

@dataclass
class NetworkPolicySpec:
    name: str
    namespace: str
    pod_selector: dict[str, str]  # Label selector for target pods
    policy_types: list[Literal["Ingress", "Egress"]]

@dataclass
class EgressRule:
    to_namespace: str | None      # None = external
    to_cidr: str | None           # e.g., "10.0.0.0/8"
    to_fqdn: str | None           # e.g., "api.openai.com" (Cilium only)
    ports: list[int]
    protocol: Literal["TCP", "UDP"]

@dataclass
class IngressRule:
    from_namespace: str | None    # None = any namespace
    from_pod_labels: dict[str, str] | None
    ports: list[int]
    protocol: Literal["TCP", "UDP"]

class NetworkPolicyProvider(Protocol):
    """
    L00 provides NetworkPolicy templates; layers apply policies.
    
    Infrastructure Layer provides baseline policies (default-deny, DNS egress).
    Application layers apply additional policies for their communication patterns.
    """
    
    def apply_namespace_isolation(self, namespace: str) -> NetworkPolicySpec:
        """
        Apply default deny-all ingress policy to namespace.
        
        Args:
            namespace: Target namespace for isolation.
            
        Returns:
            Applied NetworkPolicy specification.
            
        Raises:
            E0100: Namespace not found.
            E0101: Policy already exists (idempotent, returns existing).
        """
        ...
    
    def allow_egress(
        self, 
        namespace: str, 
        name: str,
        rules: list[EgressRule]
    ) -> NetworkPolicySpec:
        """
        Allow specific egress from namespace.
        
        Args:
            namespace: Source namespace.
            name: Policy name.
            rules: List of egress rules.
            
        Returns:
            Applied NetworkPolicy specification.
            
        Raises:
            E0102: Invalid CIDR format.
            E0103: FQDN egress requires Cilium (not available with vanilla NetworkPolicy).
        """
        ...
    
    def allow_ingress(
        self,
        namespace: str,
        name: str,
        rules: list[IngressRule]
    ) -> NetworkPolicySpec:
        """
        Allow specific ingress to namespace.
        
        Args:
            namespace: Target namespace.
            name: Policy name.
            rules: List of ingress rules.
            
        Returns:
            Applied NetworkPolicy specification.
            
        Raises:
            E0104: Source namespace not found.
        """
        ...
```

**Baseline Network Policies (Applied by L00):**

| Policy | Namespace | Effect |
|--------|-----------|--------|
| `default-deny-ingress` | All application namespaces | Deny all inbound traffic by default |
| `allow-dns-egress` | All namespaces | Allow UDP/TCP 53 to kube-system |
| `allow-prometheus-scrape` | All namespaces | Allow ingress from infrastructure namespace on metrics port |
| `allow-apiserver` | All namespaces | Allow egress to Kubernetes API server |

**LLM Provider Egress Policy (Cilium):**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-llm-egress
  namespace: model-gateway
spec:
  endpointSelector:
    matchLabels:
      app: model-gateway
  egress:
    - toFQDNs:
        - matchName: "api.openai.com"
        - matchName: "api.anthropic.com"
        - matchName: "generativelanguage.googleapis.com"
        - matchPattern: "*.azure.com"
      toPorts:
        - ports:
            - port: "443"
              protocol: TCP
```

---

#### 4.1.4 Resource Quota Interface

| Attribute | Value |
|-----------|-------|
| Consumer(s) | Platform operators, ArgoCD |
| Protocol | Kubernetes API (ResourceQuota, LimitRange) |
| Auth Required | RBAC (cluster-admin for quota changes) |
| Rate Limited | No |

**Operations:**

| Operation | Input | Output | Description |
|-----------|-------|--------|-------------|
| Set Namespace Quota | Namespace, limits | ResourceQuota | Define resource limits for namespace |
| Get Quota Usage | Namespace | Quota status | Current usage vs limits |
| Set Limit Range | Namespace, defaults | LimitRange | Define default/max container resources |

**Contract:**

```python
from typing import Protocol
from dataclasses import dataclass

@dataclass
class ResourceQuotaSpec:
    namespace: str
    cpu_requests: str         # e.g., "10" (cores)
    cpu_limits: str
    memory_requests: str      # e.g., "20Gi"
    memory_limits: str
    gpu_requests: int         # nvidia.com/gpu count
    pvc_count: int
    storage_requests: str     # e.g., "100Gi"
    pod_count: int

@dataclass
class QuotaUsage:
    namespace: str
    cpu_used: str
    cpu_limit: str
    memory_used: str
    memory_limit: str
    gpu_used: int
    gpu_limit: int
    storage_used: str
    storage_limit: str
    pods_used: int
    pods_limit: int

class ResourceQuotaProvider(Protocol):
    """
    L00 enforces quotas; layers operate within limits.
    
    Infrastructure Layer defines namespace quotas based on tier.
    Application layers request resources within their quota allocation.
    """
    
    def set_namespace_quota(self, spec: ResourceQuotaSpec) -> ResourceQuotaSpec:
        """
        Set resource limits for namespace.
        
        Args:
            spec: Quota specification with CPU, memory, GPU, storage limits.
            
        Returns:
            Applied ResourceQuota specification.
            
        Raises:
            E0300: Namespace not found.
            E0301: Quota exceeds cluster capacity.
            E0302: Invalid resource format.
        """
        ...
    
    def get_quota_usage(self, namespace: str) -> QuotaUsage:
        """
        Get current resource usage vs quota limits.
        
        Args:
            namespace: Target namespace.
            
        Returns:
            Current usage and limits for all resource types.
            
        Raises:
            E0303: Namespace not found.
            E0304: Quota not configured for namespace.
        """
        ...
```

---

#### 4.1.5 Certificate Provisioning Interface

| Attribute | Value |
|-----------|-------|
| Consumer(s) | L09 API Gateway, application layers requiring TLS |
| Protocol | Kubernetes API (Certificate CRD) |
| Auth Required | RBAC (namespace-scoped) |
| Rate Limited | Yes (Let's Encrypt rate limits) |

**Operations:**

| Operation | Input | Output | Description |
|-----------|-------|--------|-------------|
| Request Certificate | Certificate spec | TLS Secret | Issue certificate via ClusterIssuer |
| Get Certificate Status | Certificate name | Certificate status | Check issuance/renewal status |
| List Certificates | Namespace | Certificate list | Enumerate certificates in namespace |

**Contract:**

```python
from typing import Protocol, Literal
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CertificateSpec:
    name: str
    namespace: str
    secret_name: str              # Name of resulting TLS Secret
    issuer_ref: str               # ClusterIssuer name
    dns_names: list[str]          # e.g., ["*.example.com", "example.com"]
    duration_hours: int           # Certificate validity period
    renew_before_hours: int       # Trigger renewal this many hours before expiry

@dataclass
class CertificateStatus:
    name: str
    namespace: str
    ready: bool
    status: Literal["Issuing", "Ready", "Failed"]
    not_before: datetime | None
    not_after: datetime | None
    renewal_time: datetime | None
    failure_reason: str | None

class CertificateProvider(Protocol):
    """
    L00 automates TLS certificates; layers request via Certificate CRD.
    
    Infrastructure Layer owns ClusterIssuer configuration and cert-manager
    deployment. Application layers create Certificate resources to request
    TLS certificates for their Ingress or internal mTLS.
    """
    
    def request_certificate(self, spec: CertificateSpec) -> CertificateStatus:
        """
        Request TLS certificate issuance.
        
        Args:
            spec: Certificate specification with DNS names and issuer.
            
        Returns:
            Certificate status (may be Issuing initially).
            
        Raises:
            E0400: ClusterIssuer not found.
            E0401: DNS name validation failed.
            E0402: Rate limit exceeded (Let's Encrypt).
        """
        ...
    
    def get_certificate_status(self, name: str, namespace: str) -> CertificateStatus:
        """
        Check certificate issuance or renewal status.
        
        Args:
            name: Certificate name.
            namespace: Certificate namespace.
            
        Returns:
            Current certificate status including expiry.
            
        Raises:
            E0403: Certificate not found.
        """
        ...
```

**Available ClusterIssuers:**

| Issuer | Type | Use Case | Rate Limits |
|--------|------|----------|-------------|
| `letsencrypt-prod` | ACME (DNS-01) | Public-facing TLS | 50 certs/domain/week |
| `letsencrypt-staging` | ACME (DNS-01) | Testing | Higher limits |
| `vault-pki` | Vault PKI | Internal mTLS | No external limits |
| `self-signed` | Self-signed | Development | None |

---

### 4.2 Required Interfaces (External Dependencies)

Infrastructure Layer consumes the following external interfaces:

| Interface | Provider | Protocol | Purpose | Failure Handling |
|-----------|----------|----------|---------|------------------|
| Cloud Compute API | AWS EC2 / GCP GCE | REST | Node provisioning, instance management | Retry with exponential backoff; fall back to existing capacity |
| Cloud Storage API | AWS EBS / GCP PD | REST | Volume provisioning, snapshots | Retry; alert on persistent failure |
| Cloud Networking API | AWS VPC / GCP VPC | REST | Load balancers, security groups | Cached configuration; manual intervention |
| Cloud IAM API | AWS IAM / GCP IAM | REST | Service account management | Pre-provisioned credentials; alert on rotation failure |
| Vault API | HashiCorp Vault | REST (HTTPS) | Secret retrieval, PKI | Circuit breaker; cached secrets (stale reads) |
| Git Repository | GitHub / GitLab | HTTPS / SSH | GitOps manifest source | ArgoCD retries; manual sync available |
| Container Registry | ECR / GCR / ACR | HTTPS | Image pulls | Retry; image pull backoff; alert on ImagePullBackOff |
| DNS Provider | Route53 / Cloud DNS | REST | External DNS record management | ExternalDNS retries; cached DNS (TTL) |
| Let's Encrypt | ACME | HTTPS | Certificate issuance | Retry with backoff; fallback to existing cert |

**Vault API Integration:**

```
+------------------------------------------------------------------+
|                    VAULT INTEGRATION FLOW                         |
+------------------------------------------------------------------+
|                                                                  |
|  Kubernetes                Vault                  ESO            |
|  Service Account           Server                 Controller     |
|       |                       |                       |          |
|       |--- JWT token -------->|                       |          |
|       |                       |                       |          |
|       |<-- Vault token -------|                       |          |
|       |                       |                       |          |
|       |                       |<-- Read secret -------|          |
|       |                       |                       |          |
|       |                       |--- Secret data ------>|          |
|       |                       |                       |          |
|       |                       |                       |-- Create |
|       |                       |                       |   K8s    |
|       |                       |                       |   Secret |
|       |                       |                       |          |
+------------------------------------------------------------------+

Authentication: Kubernetes Auth Method
- ESO uses ServiceAccount JWT to authenticate to Vault
- Vault validates JWT against Kubernetes API
- Returns Vault token scoped to allowed paths
```

---

### 4.3 Events Published

Infrastructure Layer publishes the following events (consumed by observability, alerting, and audit systems):

| Event Type | Trigger | Payload Schema | Consumers |
|------------|---------|----------------|-----------|
| `infra.node.provisioned` | Karpenter provisions new node | See below | Observability, Cost tracking |
| `infra.node.terminated` | Node removed (scale-down or preemption) | See below | Observability, Capacity planning |
| `infra.node.cordoned` | Node marked unschedulable | See below | Alerting |
| `infra.secret.synced` | ESO successfully syncs secret | See below | Audit |
| `infra.secret.sync_failed` | ESO fails to sync secret | See below | Alerting |
| `infra.certificate.issued` | cert-manager issues certificate | See below | Audit |
| `infra.certificate.renewed` | cert-manager renews certificate | See below | Audit |
| `infra.certificate.expiring` | Certificate approaching expiry | See below | Alerting |
| `infra.scaling.triggered` | HPA/VPA/KEDA scales workload | See below | Observability |
| `infra.scaling.failed` | Scaling blocked (quota, capacity) | See below | Alerting |
| `infra.alert.fired` | Alertmanager fires alert | See below | Alerting, Incident management |
| `infra.alert.resolved` | Alert condition cleared | See below | Alerting |
| `infra.deployment.synced` | ArgoCD syncs application | See below | Audit, Observability |
| `infra.deployment.failed` | ArgoCD sync fails | See below | Alerting |

**Event Payload Schemas:**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-system.internal/schemas/infra/node-provisioned.schema.json",
  "title": "NodeProvisionedEvent",
  "type": "object",
  "required": ["event_type", "timestamp", "node_id", "instance_type", "node_pool"],
  "properties": {
    "event_type": { "const": "infra.node.provisioned" },
    "timestamp": { "type": "string", "format": "date-time" },
    "node_id": { "type": "string" },
    "instance_type": { "type": "string" },
    "node_pool": { "type": "string" },
    "capacity_type": { "enum": ["on-demand", "spot"] },
    "zone": { "type": "string" },
    "provisioner": { "type": "string" },
    "trigger_reason": { "type": "string" }
  }
}
```

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-system.internal/schemas/infra/secret-synced.schema.json",
  "title": "SecretSyncedEvent",
  "type": "object",
  "required": ["event_type", "timestamp", "secret_name", "namespace"],
  "properties": {
    "event_type": { "const": "infra.secret.synced" },
    "timestamp": { "type": "string", "format": "date-time" },
    "secret_name": { "type": "string" },
    "namespace": { "type": "string" },
    "external_secret_name": { "type": "string" },
    "secret_store": { "type": "string" },
    "keys_synced": { "type": "array", "items": { "type": "string" } },
    "version": { "type": "string" }
  }
}
```

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-system.internal/schemas/infra/scaling-triggered.schema.json",
  "title": "ScalingTriggeredEvent",
  "type": "object",
  "required": ["event_type", "timestamp", "target_name", "namespace", "direction"],
  "properties": {
    "event_type": { "const": "infra.scaling.triggered" },
    "timestamp": { "type": "string", "format": "date-time" },
    "target_name": { "type": "string" },
    "target_kind": { "enum": ["Deployment", "StatefulSet", "ReplicaSet"] },
    "namespace": { "type": "string" },
    "scaler": { "enum": ["HPA", "VPA", "KEDA", "Karpenter"] },
    "direction": { "enum": ["scale-up", "scale-down"] },
    "previous_replicas": { "type": "integer" },
    "new_replicas": { "type": "integer" },
    "trigger_metric": { "type": "string" },
    "trigger_value": { "type": "number" }
  }
}
```

**Event Publishing Mechanism:**

Events are published via Kubernetes Events API and scraped by Prometheus for metrics. Critical events also trigger Alertmanager notifications.

```yaml
# Prometheus rule to convert events to metrics
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: infrastructure-events
  namespace: infrastructure
spec:
  groups:
    - name: infra.events
      rules:
        - record: infra_nodes_provisioned_total
          expr: |
            count(kube_node_created_timestamp_seconds) by (node)
        - record: infra_scaling_events_total
          expr: |
            sum(increase(kube_hpa_status_current_replicas[5m])) by (namespace, hpa)
```

---

### 4.4 Kubernetes CRD Interfaces

Infrastructure Layer watches and manages the following Custom Resource Definitions:

| CRD | API Group | Controller | Purpose | Layer Interaction |
|-----|-----------|------------|---------|-------------------|
| `ExternalSecret` | external-secrets.io/v1beta1 | ESO | Secret sync definitions | Layers create to sync secrets |
| `SecretStore` | external-secrets.io/v1beta1 | ESO | Per-namespace Vault connection | L00 creates; layers reference |
| `ClusterSecretStore` | external-secrets.io/v1beta1 | ESO | Cluster-wide Vault connection | L00 creates; layers reference |
| `Certificate` | cert-manager.io/v1 | cert-manager | TLS certificate requests | Layers create to request certs |
| `ClusterIssuer` | cert-manager.io/v1 | cert-manager | CA/ACME configuration | L00 creates; layers reference |
| `Issuer` | cert-manager.io/v1 | cert-manager | Namespace-scoped CA config | Layers create if needed |
| `Provisioner` | karpenter.sh/v1alpha5 | Karpenter | Node provisioning rules | L00 creates |
| `AWSNodeTemplate` | karpenter.k8s.aws/v1alpha1 | Karpenter | AWS-specific node config | L00 creates |
| `ScaledObject` | keda.sh/v1alpha1 | KEDA | Event-driven scaling | Layers create to scale |
| `TriggerAuthentication` | keda.sh/v1alpha1 | KEDA | Scaler authentication | Layers create if needed |
| `CiliumNetworkPolicy` | cilium.io/v2 | Cilium | L7 network policies | Layers create for FQDN egress |
| `CiliumClusterwideNetworkPolicy` | cilium.io/v2 | Cilium | Cluster-wide policies | L00 creates for baselines |
| `VerticalPodAutoscaler` | autoscaling.k8s.io/v1 | VPA | Vertical scaling config | Layers create to right-size |
| `PodDisruptionBudget` | policy/v1 | Kubernetes | Availability during disruptions | Layers create for HA |

**CRD Ownership Matrix:**

```
+------------------------------------------------------------------+
|                    CRD OWNERSHIP MATRIX                           |
+------------------------------------------------------------------+
|                                                                  |
|  CRD                    CREATED BY       REFERENCED BY           |
|  ---                    ----------       -------------           |
|  ClusterSecretStore     L00              L01, L02, L04, L09      |
|  SecretStore            L00 or Layer     Same namespace          |
|  ExternalSecret         Layer            N/A (leaf resource)     |
|                                                                  |
|  ClusterIssuer          L00              L09, all layers         |
|  Certificate            Layer            N/A (produces Secret)   |
|                                                                  |
|  Provisioner            L00              Karpenter (internal)    |
|  AWSNodeTemplate        L00              Provisioner             |
|                                                                  |
|  ScaledObject           Layer            N/A (leaf resource)     |
|  VerticalPodAutoscaler  Layer            N/A (leaf resource)     |
|  PodDisruptionBudget    Layer            N/A (leaf resource)     |
|                                                                  |
|  CiliumNetworkPolicy    Layer            N/A (leaf resource)     |
|  CiliumClusterwideNP    L00              N/A (cluster baseline)  |
|                                                                  |
+------------------------------------------------------------------+
```

---

## 5. Data Model

### 5.1 Owned Entities

Infrastructure Layer owns configuration and operational state for platform components. Application data resides in L01 Data Layer; L00 owns only infrastructure metadata.

| Entity | Storage Location | Purpose | Retention | Owner |
|--------|------------------|---------|-----------|-------|
| Cluster Configuration | Terraform state (S3/GCS) | Cluster definition, node pools, networking | Permanent (versioned) | Cluster Manager |
| ArgoCD Applications | etcd (in-cluster) | Deployment state, sync status | Permanent | Cluster Manager |
| Prometheus Metrics | Prometheus TSDB + Thanos (S3) | Infrastructure metrics | 15d local, 1y remote | Observability Stack |
| Loki Logs | Loki + S3 | Infrastructure and application logs | 30d | Observability Stack |
| Tempo Traces | Tempo + S3 | Distributed traces | 7d | Observability Stack |
| Alert State | Alertmanager | Active alerts, silences | Transient | Observability Stack |
| Certificate State | etcd (cert-manager) | Certificate status, renewal times | Permanent | Certificate Manager |
| Secret Metadata | etcd (ESO) | ExternalSecret sync status | Permanent | Secrets Operator |
| Node State | Karpenter | Provisioner decisions, node lifecycle | Transient | Resource Scaler |
| Cost Data | OpenCost | Resource cost attribution | 90d | Observability Stack |

**Entity Relationship Diagram:**

```
+===========================================================================+
|                    INFRASTRUCTURE DATA MODEL                               |
+===========================================================================+
|                                                                           |
|  TERRAFORM STATE (S3)              KUBERNETES ETCD                        |
|  +-------------------------+       +--------------------------------+     |
|  | ClusterConfiguration    |       | ArgoCD Application             |     |
|  | +---------------------+ |       | +----------------------------+ |     |
|  | | name                 | |       | | metadata.name              | |     |
|  | | region               | |       | | spec.source.repoURL        | |     |
|  | | kubernetes_version   | |       | | spec.destination.namespace | |     |
|  | | node_pools[]         | |       | | status.sync.status         | |     |
|  | | network_config       | |       | | status.health.status       | |     |
|  | +---------------------+ |       | +----------------------------+ |     |
|  +-------------------------+       |                                |     |
|            |                       | ExternalSecret                 |     |
|            | provisions            | +----------------------------+ |     |
|            v                       | | metadata.name              | |     |
|  +-------------------------+       | | spec.secretStoreRef        | |     |
|  | NodePool                |       | | spec.target.name           | |     |
|  | +---------------------+ |       | | status.syncedResourceVer   | |     |
|  | | name                 | |       | +----------------------------+ |     |
|  | | instance_types[]     | |       |                                |     |
|  | | min_size / max_size  | |       | Certificate                    |     |
|  | | taints[]             | |       | +----------------------------+ |     |
|  | | labels{}             | |       | | metadata.name              | |     |
|  | | gpu_config           | |       | | spec.dnsNames[]            | |     |
|  | +---------------------+ |       | | spec.issuerRef             | |     |
|  +-------------------------+       | | status.notAfter            | |     |
|                                    | +----------------------------+ |     |
|                                    +--------------------------------+     |
|                                                                           |
|  PROMETHEUS TSDB                   LOKI                                   |
|  +-------------------------+       +--------------------------------+     |
|  | Metric                  |       | LogStream                      |     |
|  | +---------------------+ |       | +----------------------------+ |     |
|  | | __name__             | |       | | namespace                  | |     |
|  | | labels{}             | |       | | pod                        | |     |
|  | | value                | |       | | container                  | |     |
|  | | timestamp            | |       | | log_line                   | |     |
|  | +---------------------+ |       | | timestamp                  | |     |
|  +-------------------------+       | +----------------------------+ |     |
|                                    +--------------------------------+     |
|                                                                           |
+===========================================================================+
```

### 5.2 Configuration Schemas

#### 5.2.1 Cluster Configuration Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-system.internal/schemas/infra/cluster-config.schema.json",
  "title": "ClusterConfiguration",
  "description": "Terraform-managed Kubernetes cluster configuration",
  "type": "object",
  "required": ["name", "region", "kubernetes_version", "node_pools", "network"],
  "properties": {
    "name": {
      "type": "string",
      "pattern": "^[a-z][a-z0-9-]{2,62}$",
      "description": "Cluster name (DNS-compatible)"
    },
    "region": {
      "type": "string",
      "description": "Primary cloud region (e.g., us-west-2)"
    },
    "dr_region": {
      "type": "string",
      "description": "Disaster recovery region (optional)"
    },
    "kubernetes_version": {
      "type": "string",
      "pattern": "^1\\.(2[8-9]|[3-9][0-9])(\\.\\d+)?$",
      "description": "Kubernetes version (minimum 1.28)"
    },
    "cloud_provider": {
      "enum": ["aws", "gcp", "azure"],
      "description": "Cloud provider"
    },
    "node_pools": {
      "type": "array",
      "items": { "$ref": "#/$defs/NodePool" },
      "minItems": 2,
      "description": "Node pool definitions (minimum: system + general)"
    },
    "network": { "$ref": "#/$defs/NetworkConfig" },
    "observability": { "$ref": "#/$defs/ObservabilityConfig" },
    "secrets": { "$ref": "#/$defs/SecretsConfig" },
    "labels": {
      "type": "object",
      "properties": {
        "environment": { "enum": ["production", "staging", "development"] },
        "cost-center": { "type": "string" },
        "team": { "type": "string" }
      },
      "required": ["environment", "cost-center"]
    }
  },
  "$defs": {
    "NodePool": {
      "type": "object",
      "required": ["name", "instance_types", "min_size", "max_size"],
      "properties": {
        "name": {
          "type": "string",
          "pattern": "^[a-z][a-z0-9-]{1,30}$"
        },
        "instance_types": {
          "type": "array",
          "items": { "type": "string" },
          "minItems": 1,
          "description": "Allowed instance types for this pool"
        },
        "min_size": {
          "type": "integer",
          "minimum": 0
        },
        "max_size": {
          "type": "integer",
          "minimum": 1
        },
        "capacity_type": {
          "enum": ["on-demand", "spot", "mixed"],
          "default": "on-demand"
        },
        "taints": {
          "type": "array",
          "items": { "$ref": "#/$defs/Taint" }
        },
        "labels": {
          "type": "object",
          "additionalProperties": { "type": "string" }
        },
        "gpu": { "$ref": "#/$defs/GPUConfig" }
      }
    },
    "Taint": {
      "type": "object",
      "required": ["key", "effect"],
      "properties": {
        "key": { "type": "string" },
        "value": { "type": "string" },
        "effect": { "enum": ["NoSchedule", "PreferNoSchedule", "NoExecute"] }
      }
    },
    "GPUConfig": {
      "type": "object",
      "properties": {
        "enabled": { "type": "boolean", "default": false },
        "type": {
          "type": "string",
          "description": "GPU type (e.g., nvidia-tesla-a100)"
        },
        "count_per_node": {
          "type": "integer",
          "minimum": 1,
          "maximum": 8
        },
        "mig_strategy": {
          "enum": ["none", "single", "mixed"],
          "default": "none",
          "description": "MIG partitioning strategy"
        },
        "mig_profile": {
          "type": "string",
          "description": "MIG profile (e.g., 3g.40gb)"
        }
      }
    },
    "NetworkConfig": {
      "type": "object",
      "required": ["vpc_cidr", "pod_cidr", "service_cidr"],
      "properties": {
        "vpc_cidr": {
          "type": "string",
          "format": "ipv4-cidr",
          "description": "VPC CIDR block"
        },
        "pod_cidr": {
          "type": "string",
          "format": "ipv4-cidr",
          "description": "Pod network CIDR"
        },
        "service_cidr": {
          "type": "string",
          "format": "ipv4-cidr",
          "description": "Service network CIDR"
        },
        "service_mesh": {
          "enum": ["cilium", "istio", "none"],
          "default": "cilium"
        },
        "ingress_controller": {
          "enum": ["nginx", "traefik", "kong"],
          "default": "nginx"
        },
        "enable_network_policies": {
          "type": "boolean",
          "default": true
        }
      }
    },
    "ObservabilityConfig": {
      "type": "object",
      "properties": {
        "prometheus_retention_days": {
          "type": "integer",
          "default": 15,
          "minimum": 1,
          "maximum": 90
        },
        "prometheus_storage_gb": {
          "type": "integer",
          "default": 100,
          "minimum": 50
        },
        "loki_retention_days": {
          "type": "integer",
          "default": 30,
          "minimum": 7,
          "maximum": 365
        },
        "tempo_retention_days": {
          "type": "integer",
          "default": 7,
          "minimum": 1,
          "maximum": 30
        },
        "thanos_bucket": {
          "type": "string",
          "description": "S3/GCS bucket for long-term metrics"
        },
        "enable_gpu_metrics": {
          "type": "boolean",
          "default": true
        }
      }
    },
    "SecretsConfig": {
      "type": "object",
      "required": ["vault_address"],
      "properties": {
        "vault_address": {
          "type": "string",
          "format": "uri",
          "description": "HashiCorp Vault server URL"
        },
        "vault_auth_method": {
          "enum": ["kubernetes", "approle"],
          "default": "kubernetes"
        },
        "vault_kubernetes_role": {
          "type": "string",
          "description": "Vault role for Kubernetes auth"
        },
        "secret_refresh_interval": {
          "type": "string",
          "pattern": "^\\d+[smh]$",
          "default": "1h",
          "description": "ESO refresh interval"
        }
      }
    }
  },
  "_schema_metadata": {
    "version": "1.0.0",
    "layer": "infrastructure"
  }
}
```

#### 5.2.2 Namespace Configuration Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://agent-system.internal/schemas/infra/namespace-config.schema.json",
  "title": "NamespaceConfiguration",
  "description": "Namespace provisioning configuration with quotas and policies",
  "type": "object",
  "required": ["name", "tier", "labels"],
  "properties": {
    "name": {
      "type": "string",
      "pattern": "^[a-z][a-z0-9-]{1,62}$"
    },
    "tier": {
      "enum": ["system", "platform", "application", "agent"],
      "description": "Determines default quotas and network policies"
    },
    "resource_quota": { "$ref": "#/$defs/ResourceQuota" },
    "limit_range": { "$ref": "#/$defs/LimitRange" },
    "network_policy": { "$ref": "#/$defs/NetworkPolicyConfig" },
    "labels": {
      "type": "object",
      "required": ["layer", "cost-center", "environment"],
      "properties": {
        "layer": {
          "type": "string",
          "pattern": "^l(0[0-9]|1[0-1])$",
          "description": "Layer identifier (l00-l11)"
        },
        "cost-center": { "type": "string" },
        "team": { "type": "string" },
        "environment": { "enum": ["production", "staging", "development"] },
        "managed-by": { "enum": ["argocd", "terraform", "manual"] }
      }
    },
    "annotations": {
      "type": "object",
      "additionalProperties": { "type": "string" }
    }
  },
  "$defs": {
    "ResourceQuota": {
      "type": "object",
      "properties": {
        "cpu_requests": {
          "type": "string",
          "pattern": "^\\d+(\\.\\d+)?$",
          "description": "CPU cores"
        },
        "cpu_limits": { "type": "string" },
        "memory_requests": {
          "type": "string",
          "pattern": "^\\d+(Gi|Mi)$"
        },
        "memory_limits": { "type": "string" },
        "gpu_requests": {
          "type": "integer",
          "minimum": 0
        },
        "pvc_count": {
          "type": "integer",
          "minimum": 0
        },
        "storage_requests": {
          "type": "string",
          "pattern": "^\\d+(Gi|Ti)$"
        },
        "pod_count": {
          "type": "integer",
          "minimum": 1
        },
        "service_count": {
          "type": "integer",
          "minimum": 0
        },
        "secret_count": {
          "type": "integer",
          "minimum": 0
        },
        "configmap_count": {
          "type": "integer",
          "minimum": 0
        }
      }
    },
    "LimitRange": {
      "type": "object",
      "properties": {
        "container_default_cpu": {
          "type": "string",
          "default": "500m"
        },
        "container_default_memory": {
          "type": "string",
          "default": "512Mi"
        },
        "container_default_request_cpu": {
          "type": "string",
          "default": "100m"
        },
        "container_default_request_memory": {
          "type": "string",
          "default": "128Mi"
        },
        "container_max_cpu": {
          "type": "string",
          "default": "4"
        },
        "container_max_memory": {
          "type": "string",
          "default": "8Gi"
        },
        "container_min_cpu": {
          "type": "string",
          "default": "50m"
        },
        "container_min_memory": {
          "type": "string",
          "default": "64Mi"
        },
        "pvc_max_storage": {
          "type": "string",
          "default": "100Gi"
        },
        "pvc_min_storage": {
          "type": "string",
          "default": "1Gi"
        }
      }
    },
    "NetworkPolicyConfig": {
      "type": "object",
      "properties": {
        "default_deny_ingress": {
          "type": "boolean",
          "default": true
        },
        "default_deny_egress": {
          "type": "boolean",
          "default": false
        },
        "allow_dns_egress": {
          "type": "boolean",
          "default": true
        },
        "allow_prometheus_scrape": {
          "type": "boolean",
          "default": true
        },
        "allowed_ingress_namespaces": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Namespaces allowed to send traffic to this namespace"
        },
        "allowed_egress_namespaces": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Namespaces this namespace can send traffic to"
        },
        "allowed_egress_cidrs": {
          "type": "array",
          "items": {
            "type": "string",
            "format": "ipv4-cidr"
          },
          "description": "External CIDRs allowed for egress"
        }
      }
    }
  },
  "_schema_metadata": {
    "version": "1.0.0",
    "layer": "infrastructure"
  }
}
```

#### 5.2.3 Tier Default Quotas

| Tier | CPU Requests | Memory Requests | GPU | PVCs | Storage | Pods |
|------|-------------|-----------------|-----|------|---------|------|
| system | Unlimited | Unlimited | 0 | 20 | 50Gi | 100 |
| platform | 50 | 100Gi | 0 | 50 | 500Gi | 200 |
| application | 20 | 50Gi | 4 | 30 | 200Gi | 100 |
| agent | 10 | 20Gi | 2 | 10 | 50Gi | 50 |

### 5.3 Data Flows

#### 5.3.1 Secret Injection Flow

```
SECRET INJECTION DATA FLOW
==========================

Vault                    ESO Controller           K8s Secret              Pod
  |                           |                        |                   |
  |                           |                        |                   |
  |<--- Poll (1h interval) ---|                        |                   |
  |                           |                        |                   |
  |--- Secret value --------->|                        |                   |
  |    (encrypted TLS)        |                        |                   |
  |                           |                        |                   |
  |                           |--- Create/Update ----->|                   |
  |                           |    Secret              |                   |
  |                           |                        |                   |
  |                           |--- Emit Event -------->|                   |
  |                           |    (secret.synced)     |                   |
  |                           |                        |                   |
  |                           |                        |<-- Mount volume --|
  |                           |                        |    (secretRef)    |
  |                           |                        |                   |
  |                           |                        |--- Inject as ---->|
  |                           |                        |    env/file       |
  |                           |                        |                   |
  |                           |                        |                   |
  |                    Reloader                        |                   |
  |                       |                            |                   |
  |                       |<-- Watch Secret changes ---|                   |
  |                       |                            |                   |
  |                       |--- Trigger rollout --------|------------------>|
  |                       |    (annotation change)     |    (new Pod)      |
  |                       |                            |                   |

Data Format:
- Vault -> ESO: JSON (via Vault API, TLS encrypted)
- ESO -> K8s: base64-encoded Secret (via K8s API)
- K8s -> Pod: Mounted file or environment variable
```

#### 5.3.2 Node Provisioning Flow

```
NODE PROVISIONING DATA FLOW
===========================

Pending Pod          Karpenter            Cloud API           Node
    |                    |                    |                  |
    |                    |                    |                  |
    |-- Unschedulable -->|                    |                  |
    |   (pending)        |                    |                  |
    |                    |                    |                  |
    |                    |-- Evaluate ------->|                  |
    |                    |   requirements     |                  |
    |                    |   (CPU, mem, GPU,  |                  |
    |                    |    taints, labels) |                  |
    |                    |                    |                  |
    |                    |-- Select instance->|                  |
    |                    |   type (bin-pack)  |                  |
    |                    |                    |                  |
    |                    |                    |-- Launch ------->|
    |                    |                    |   instance       |
    |                    |                    |                  |
    |                    |                    |<-- Instance -----|
    |                    |                    |   ready          |
    |                    |                    |                  |
    |                    |<-- Node joined ----|------------------|
    |                    |                    |                  |
    |                    |-- Emit Event ----->|                  |
    |                    |   (node.provisioned)                  |
    |                    |                    |                  |
    |<-- Scheduled ------|                    |                  |
    |   (bound to node)  |                    |                  |
    |                    |                    |                  |

Timing:
- Pod pending detection: <5s
- Instance selection: <2s
- Instance launch (on-demand): 60-90s
- Instance launch (spot): 30-60s
- Node join + ready: 30-60s
- Total: 2-3 minutes typical
```

#### 5.3.3 Certificate Issuance Flow

```
CERTIFICATE ISSUANCE DATA FLOW
==============================

Certificate CRD      cert-manager         ACME/Vault          DNS Provider
      |                   |                    |                    |
      |                   |                    |                    |
      |-- Create -------->|                    |                    |
      |   Certificate     |                    |                    |
      |                   |                    |                    |
      |                   |-- Request cert --->|                    |
      |                   |   (CSR)            |                    |
      |                   |                    |                    |
      |                   |<-- Challenge ------|                    |
      |                   |   (DNS-01)         |                    |
      |                   |                    |                    |
      |                   |-- Create TXT ------|-------------------->|
      |                   |   record           |                    |
      |                   |                    |                    |
      |                   |                    |<-- Verify DNS -----|
      |                   |                    |                    |
      |                   |<-- Certificate ----|                    |
      |                   |   issued           |                    |
      |                   |                    |                    |
      |                   |-- Create Secret -->|                    |
      |                   |   (tls.crt,        |                    |
      |                   |    tls.key)        |                    |
      |                   |                    |                    |
      |<-- Update status -|                    |                    |
      |   (Ready=True)    |                    |                    |
      |                   |                    |                    |

Timing (Let's Encrypt):
- Challenge creation: <10s
- DNS propagation: 30-120s
- Validation: <30s
- Certificate issuance: <10s
- Total: 1-3 minutes typical
```

#### 5.3.4 Metrics Collection Flow

```
METRICS COLLECTION DATA FLOW
============================

Application Pod      Prometheus           Thanos Sidecar       S3/GCS
      |                   |                    |                  |
      |                   |                    |                  |
      |<-- Scrape --------|                    |                  |
      |   /metrics (30s)  |                    |                  |
      |                   |                    |                  |
      |-- Metrics ------->|                    |                  |
      |   (Prometheus     |                    |                  |
      |    exposition)    |                    |                  |
      |                   |                    |                  |
      |                   |-- Store locally -->|                  |
      |                   |   (TSDB, 15d)      |                  |
      |                   |                    |                  |
      |                   |                    |-- Upload blocks->|
      |                   |                    |   (2h compaction)|
      |                   |                    |                  |
      |                   |                    |                  |
Thanos Query         Thanos Store             |                  |
      |                   |                    |                  |
      |-- Query recent -->|                    |                  |
      |   (Prometheus)    |                    |                  |
      |                   |                    |                  |
      |-- Query historic--|-------------------------------------->|
      |   (S3/GCS)        |                    |                  |
      |                   |                    |                  |

Data Retention:
- Local (Prometheus): 15 days
- Remote (Thanos/S3): 1 year
- Compaction: 2-hour blocks
- Downsampling: 5m resolution after 40h, 1h resolution after 10d
```

### 5.4 Storage Classes

Infrastructure Layer provides four storage classes optimized for different workload patterns:

| Class Name | Backend | IOPS | Throughput | Encryption | Volume Expansion | Reclaim Policy | Binding Mode |
|------------|---------|------|------------|------------|------------------|----------------|--------------|
| `ssd-high-iops` | gp3 (AWS) / pd-ssd (GCP) | 16,000 | 1,000 MB/s | Optional | Yes | Delete | WaitForFirstConsumer |
| `ssd-standard` | gp3 (AWS) / pd-balanced (GCP) | 3,000 | 125 MB/s | Optional | Yes | Delete | WaitForFirstConsumer |
| `ssd-encrypted` | gp3 (AWS) / pd-ssd (GCP) | 3,000 | 125 MB/s | Required (KMS) | Yes | Retain | WaitForFirstConsumer |
| `hdd-archive` | st1 (AWS) / pd-standard (GCP) | 500 | 500 MB/s | Optional | Yes | Delete | WaitForFirstConsumer |

**Usage by Layer:**

| Layer | Primary Storage Class | Use Case |
|-------|----------------------|----------|
| L01 Data Layer | `ssd-high-iops` | Event Store segments, hot data |
| L01 Data Layer | `ssd-standard` | SQLite databases, projections |
| L01 Data Layer | `ssd-encrypted` | Identity keys, DID private keys |
| L02 Agent Runtime | `ssd-standard` | Agent workspace, temporary files |
| L04 Model Gateway | `ssd-standard` | Semantic cache |
| L06 Evaluation | `hdd-archive` | Evaluation datasets, results |
| Observability | `ssd-standard` | Prometheus TSDB, Loki chunks |

**StorageClass Manifests:**

```yaml
# High-IOPS SSD for Event Store
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ssd-high-iops
  labels:
    app.kubernetes.io/part-of: infrastructure
    layer: l00
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "16000"
  throughput: "1000"
  fsType: ext4
reclaimPolicy: Delete
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
mountOptions:
  - noatime
  - nodiratime

---
# Standard SSD for general workloads
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ssd-standard
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
  labels:
    app.kubernetes.io/part-of: infrastructure
    layer: l00
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
  fsType: ext4
reclaimPolicy: Delete
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer

---
# Encrypted SSD for sensitive data
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ssd-encrypted
  labels:
    app.kubernetes.io/part-of: infrastructure
    layer: l00
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
  encrypted: "true"
  kmsKeyId: alias/infrastructure-storage-key
  fsType: ext4
reclaimPolicy: Retain
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer

---
# Archive HDD for cold storage
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: hdd-archive
  labels:
    app.kubernetes.io/part-of: infrastructure
    layer: l00
provisioner: ebs.csi.aws.com
parameters:
  type: st1
  fsType: ext4
reclaimPolicy: Delete
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
```

### 5.5 Data Retention Policies

| Data Type | Retention Period | Storage Location | Deletion Method |
|-----------|------------------|------------------|-----------------|
| Prometheus metrics (local) | 15 days | Prometheus TSDB | Automatic compaction |
| Prometheus metrics (remote) | 1 year | S3/GCS (Thanos) | Lifecycle policy |
| Loki logs | 30 days | S3/GCS | Lifecycle policy |
| Tempo traces | 7 days | S3/GCS | Lifecycle policy |
| Terraform state | Permanent | S3/GCS (versioned) | Manual only |
| ArgoCD application state | Permanent | etcd | Manual only |
| Certificate state | Until expiry + 30d | etcd | Automatic cleanup |
| ExternalSecret state | Permanent | etcd | Manual deletion |
| Cost data (OpenCost) | 90 days | Prometheus | Automatic |

### 5.6 Backup and Recovery

| Entity | Backup Method | Frequency | Recovery RTO | Recovery RPO |
|--------|---------------|-----------|--------------|--------------|
| Terraform state | S3 versioning + cross-region replication | Continuous | 5 minutes | 0 (versioned) |
| etcd (ArgoCD, cert-manager, ESO) | Velero snapshot | 6 hours | 30 minutes | 6 hours |
| Prometheus TSDB | Thanos continuous upload | 2 hours | 15 minutes | 2 hours |
| Loki chunks | Native S3 replication | Continuous | 15 minutes | ~0 |
| Grafana dashboards | GitOps (ArgoCD) | Continuous | 5 minutes | 0 |

**Velero Backup Schedule:**

```yaml
apiVersion: velero.io/v1
kind: Schedule
metadata:
  name: infrastructure-backup
  namespace: velero
spec:
  schedule: "0 */6 * * *"  # Every 6 hours
  template:
    includedNamespaces:
      - infrastructure
      - cert-manager
      - external-secrets
    includedResources:
      - certificates.cert-manager.io
      - clusterissuers.cert-manager.io
      - externalsecrets.external-secrets.io
      - secretstores.external-secrets.io
      - applications.argoproj.io
      - applicationsets.argoproj.io
    storageLocation: default
    ttl: 720h  # 30 days
```

---

# Infrastructure Layer Specification (Continued)

**Layer ID:** L00
**Version:** 1.0.0-draft
**Status:** Draft (Part 2 of 3)
**Date:** January 4, 2025

---

## Table of Contents (Part 2)

6. [Integration with Data Layer](#6-integration-with-data-layer)
7. [Reliability and Scalability](#7-reliability-and-scalability)
8. [Security](#8-security)
9. [Observability](#9-observability)
10. [Configuration](#10-configuration)

---

## 6. Integration with Data Layer

### 6.1 Relationship Model

Infrastructure Layer (L00) occupies a unique position relative to Data Layer (L01). Unlike application layers (L02-L11) that consume Data Layer services, Infrastructure provides foundational services that Data Layer depends upon. This inverted relationship requires clear documentation of what L00 delivers rather than what it consumes.

```
INFRASTRUCTURE -> DATA LAYER RELATIONSHIP
=========================================

+------------------------------------------------------------------+
|  DATA LAYER (L01) - Consumer                                     |
|  +------------------------------------------------------------+  |
|  | Requests:                                                   |  |
|  | - Storage via PersistentVolumeClaim                        |  |
|  | - Secrets via ExternalSecret CRD                           |  |
|  | - Operates within ResourceQuota boundaries                  |  |
|  | - Network isolation via NetworkPolicy templates            |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
                              |
                              | Consumes Services
                              v
+------------------------------------------------------------------+
|  INFRASTRUCTURE LAYER (L00) - Provider                           |
|  +------------------------------------------------------------+  |
|  | Provisions:                                                 |  |
|  | - StorageClasses (ssd-high-iops, ssd-standard, etc.)       |  |
|  | - Secrets synchronization from HashiCorp Vault              |  |
|  | - Namespace resource quotas and limit ranges                |  |
|  | - OPA Gatekeeper runtime (L01 supplies policies)           |  |
|  | - TLS certificates via cert-manager                        |  |
|  | - OpenTelemetry Collector infrastructure                   |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

**Key Distinction:** Infrastructure provides mechanisms; Data Layer provides policies. For example, L00 deploys OPA Gatekeeper but L01 defines the ConstraintTemplates that enforce ABAC rules.

### 6.2 Services Provided to Data Layer

| Service | L00 Component | L01 Consumer | Interface | Gap Reference |
|---------|---------------|--------------|-----------|---------------|
| High-IOPS Storage | Cluster Manager | Event Store | `StorageClass: ssd-high-iops` | G-001 |
| Standard Storage | Cluster Manager | SQLite databases, Projections | `StorageClass: ssd-standard` | G-001 |
| Encrypted Storage | Cluster Manager | Identity keys, DID private keys | `StorageClass: ssd-encrypted` | G-001 |
| Object Storage | Cluster Manager | Blob storage, Archives | S3/GCS bucket via Terraform | G-001 |
| Secret Injection | Secrets Operator | Key Encryption Keys, DB credentials | `ExternalSecret` CRD | - |
| Namespace Isolation | Network Controller | data-layer namespace | `NetworkPolicy` templates | G-006 |
| Resource Limits | Resource Scaler | All L01 pods | `ResourceQuota`, `LimitRange` | G-009 |
| TLS Certificates | Certificate Manager | Internal mTLS, Service endpoints | `Certificate` CRD | G-004 |
| OPA Runtime | Cluster Manager | ABAC enforcement | `Gatekeeper` Deployment | G-003 |
| Telemetry Collection | Observability Stack | Metrics, traces, logs | OTEL Collector endpoints | G-002 |
| Message Queue | Cluster Manager | Handoff Manager, Outbox | Redis/NATS Helm deployment | G-010 |

### 6.3 Data Layer Storage Requirements

Storage provisioning maps Data Layer components to appropriate StorageClasses defined in Section 5.4:

| L01 Component | Storage Class | Access Mode | Typical Size | IOPS Requirement | Latency Target |
|---------------|---------------|-------------|--------------|------------------|----------------|
| Event Store segments | `ssd-high-iops` | ReadWriteOnce | 100GB-1TB | 10,000+ | < 1ms |
| Snapshot store | `ssd-standard` | ReadWriteOnce | 50GB-500GB | 3,000 | < 5ms |
| SQLite databases | `ssd-standard` | ReadWriteOnce | 10GB-100GB | 3,000 | < 5ms |
| Identity key store | `ssd-encrypted` | ReadWriteOnce | 1GB | 1,000 | < 10ms |
| Schema registry | `ssd-standard` | ReadWriteOnce | 5GB | 1,000 | < 10ms |
| Context archive | Object (S3/GCS) | N/A | Unlimited | N/A | < 100ms |

**PVC Template for Data Layer:**

```yaml
# Template for Data Layer PVC requests
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {{ component }}-storage
  namespace: data-layer
  labels:
    layer: l01
    component: {{ component }}
    cost-center: data-platform
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: {{ storage_class }}
  resources:
    requests:
      storage: {{ size }}
```

### 6.4 OPA Gatekeeper Deployment

Infrastructure Layer deploys OPA Gatekeeper as the policy enforcement runtime. Data Layer defines the ConstraintTemplates and Constraints that implement ABAC rules from Phase 07 of the Data Layer specification.

**Deployment Responsibility:**

| Artifact | Owner | Location |
|----------|-------|----------|
| Gatekeeper Helm chart | L00 Infrastructure | `helm/infrastructure/gatekeeper/` |
| Gatekeeper Deployment | L00 Infrastructure | `gatekeeper-system` namespace |
| ConstraintTemplate CRDs | L01 Data Layer | `data-layer` namespace |
| Constraint instances | L01 Data Layer | Per-namespace |
| Audit configuration | L00 Infrastructure | Helm values |

**Gatekeeper CRD Compatibility Matrix:**

| Gatekeeper Version | Kubernetes Min | Kubernetes Max | CRD API Version | Notes |
|--------------------|----------------|----------------|-----------------|-------|
| 3.14.x | 1.25 | 1.29 | constraints.gatekeeper.sh/v1beta1 | Current production |
| 3.15.x | 1.26 | 1.30 | constraints.gatekeeper.sh/v1beta1 | Latest stable |
| 3.16.x | 1.27 | 1.31 | constraints.gatekeeper.sh/v1beta1 | Edge testing |

**Compatibility Notes:**
- Upgrade Gatekeeper before upgrading Kubernetes to ensure CRD compatibility
- ConstraintTemplate CRDs from L01 must target the deployed Gatekeeper API version
- L01 Data Layer must coordinate ConstraintTemplate updates with L00 Gatekeeper upgrades

**Gatekeeper Deployment Configuration:**

```yaml
# L00 deploys Gatekeeper (mechanism)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gatekeeper-controller-manager
  namespace: gatekeeper-system
  labels:
    app.kubernetes.io/name: gatekeeper
    app.kubernetes.io/part-of: infrastructure
    layer: l00
spec:
  replicas: 3
  selector:
    matchLabels:
      app: gatekeeper
  template:
    metadata:
      labels:
        app: gatekeeper
        layer: l00
    spec:
      serviceAccountName: gatekeeper-admin
      containers:
        - name: manager
          image: openpolicyagent/gatekeeper:v3.14.0
          args:
            - --port=8443
            - --logtostderr
            - --exempt-namespace=kube-system
            - --exempt-namespace=gatekeeper-system
            - --operation=webhook
            - --operation=audit
            - --operation=status
            - --operation=mutation-webhook
            - --audit-interval=60
            - --audit-from-cache
            - --audit-chunk-size=500
          ports:
            - containerPort: 8443
              name: webhook
            - containerPort: 8888
              name: metrics
          resources:
            limits:
              cpu: 1000m
              memory: 512Mi
            requests:
              cpu: 100m
              memory: 256Mi
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            runAsNonRoot: true
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    app: gatekeeper
                topologyKey: topology.kubernetes.io/zone
```

**Example ConstraintTemplate (defined by L01, deployed via L00):**

```yaml
# L01 provides ConstraintTemplate (policy definition)
# Deployed through ArgoCD Application targeting data-layer namespace
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8srequiredagentlabels
  annotations:
    description: "Enforces required labels on agent pods per Data Layer ABAC"
spec:
  crd:
    spec:
      names:
        kind: K8sRequiredAgentLabels
      validation:
        openAPIV3Schema:
          type: object
          properties:
            labels:
              type: array
              items:
                type: string
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8srequiredagentlabels
        
        violation[{"msg": msg}] {
          provided := {label | input.review.object.metadata.labels[label]}
          required := {label | label := input.parameters.labels[_]}
          missing := required - provided
          count(missing) > 0
          msg := sprintf("Missing required labels: %v", [missing])
        }
```

### 6.5 Shared Patterns

Infrastructure and Data Layer share common patterns to ensure consistent operation:

| Pattern | L00 Implementation | L01 Usage | Standard |
|---------|-------------------|-----------|----------|
| Event Publishing | Kubernetes Events API | Event Store ingestion from cluster events | Kubernetes API |
| Health Checks | `/healthz`, `/readyz` probes | Liveness/readiness configuration | Kubernetes probes |
| Metrics Format | Prometheus exposition format | OpenTelemetry metrics export | Prometheus/OTLP |
| Error Codes | E0XXX (infrastructure) | E1XXX-E9XXX (application layers) | Specification-defined |
| Trace Context | W3C Trace Context headers | Propagated through service calls | W3C Trace Context |
| Structured Logs | JSON format to stdout | Loki ingestion via Promtail | JSON structured logging |
| Resource Labels | `layer`, `component`, `cost-center` | Applied to all resources | Label taxonomy |

**Error Code Ranges:**

| Range | Layer | Category |
|-------|-------|----------|
| E0001-E0099 | L00 | Cluster Management |
| E0100-E0199 | L00 | Network |
| E0200-E0299 | L00 | Secrets |
| E0300-E0399 | L00 | Scaling |
| E0400-E0499 | L00 | Certificates |
| E0500-E0599 | L00 | Observability |
| E1XXX | L01 | Data Layer (defined in Data Layer spec) |

**Reserved Error Codes:** Codes ending in 99 (E0099, E0199, E0299, E0399, E0499, E0599) are reserved for future use within each category. Do not assign these codes until the preceding range is exhausted.

### 6.6 Integration Points with Other Layers

Beyond Data Layer, Infrastructure provides services to all application layers:

**L02 Agent Runtime Layer:**

| Service | Interface | Configuration |
|---------|-----------|---------------|
| Namespace isolation | `Namespace` per agent pool | `agent-pool-{{ pool_id }}` |
| Resource quotas | `ResourceQuota` | CPU, memory, GPU limits per pool |
| Network policies | `CiliumNetworkPolicy` | OC-1 enforcement (see Section 8.2.2) |
| GPU scheduling | `nvidia.com/gpu` resource | MIG profiles for inference |
| Sandbox runtime | RuntimeClass | gVisor configuration (G-008) |

**L04 Model Gateway Layer:**

| Service | Interface | Configuration |
|---------|-----------|---------------|
| LLM provider egress | `CiliumNetworkPolicy` | FQDN-based allow rules (G-005) |
| GPU/TPU scheduling | Karpenter NodePool | `gpu-inference` pool |
| Semantic cache storage | `StorageClass` | `ssd-standard` |
| API credential injection | `ExternalSecret` | Vault path `secret/data/model-gateway/` |

**L09 API Gateway Layer:**

| Service | Interface | Configuration |
|---------|-----------|---------------|
| Ingress controller | `Ingress` / `Gateway` API | NGINX Ingress Controller |
| TLS termination | `Certificate` CRD | cert-manager with Let's Encrypt |
| External DNS | `ExternalDNS` operator | Route53/Cloud DNS integration (G-013) |
| DDoS protection | Cloud WAF integration | AWS WAF / Cloud Armor rules (G-014) |

### 6.7 Message Queue Infrastructure

Infrastructure provides message queue infrastructure for Data Layer's Handoff Manager and Transactional Outbox patterns. Redis is deployed for simplicity; NATS is an alternative for higher throughput requirements.

**Redis Deployment:**

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis
  namespace: infrastructure
  labels:
    app.kubernetes.io/name: redis
    app.kubernetes.io/part-of: infrastructure
    layer: l00
spec:
  serviceName: redis
  replicas: 3
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
        layer: l00
    spec:
      containers:
        - name: redis
          image: redis:7.2-alpine
          command:
            - redis-server
            - /etc/redis/redis.conf
          ports:
            - containerPort: 6379
              name: redis
            - containerPort: 16379
              name: cluster
          volumeMounts:
            - name: data
              mountPath: /data
            - name: config
              mountPath: /etc/redis
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 1Gi
      volumes:
        - name: config
          configMap:
            name: redis-config
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: ssd-standard
        resources:
          requests:
            storage: 10Gi
```

**Service Exposure:**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: infrastructure
spec:
  type: ClusterIP
  ports:
    - port: 6379
      targetPort: 6379
      name: redis
  selector:
    app: redis
```

**Data Layer Consumption:**

Data Layer components connect to `redis.infrastructure.svc.cluster.local:6379` for:
- Handoff queue operations (Phase 06)
- Transactional outbox polling
- Dead letter queue management

---

## 7. Reliability and Scalability

### 7.1 Availability Targets

| Component | Availability Target | RPO | RTO | Rationale |
|-----------|---------------------|-----|-----|-----------|
| Kubernetes Control Plane | 99.95% | N/A | 5 min | Managed service SLA (EKS/GKE/AKS) |
| Cilium Data Plane | 99.99% | N/A | 30 sec | eBPF in-kernel execution; minimal failure modes |
| Secrets Operator | 99.9% | 0 | 5 min | Cached secrets survive temporary outage |
| Certificate Manager | 99.9% | 0 | 30 min | Certificates valid for days; renewal buffer exists |
| Observability Stack | 99.5% | 2 hours | 15 min | Non-critical path; degraded mode acceptable |
| ArgoCD | 99.9% | 0 | 10 min | GitOps state persists in Git; manual sync fallback |
| Redis (Queue) | 99.9% | 1 min | 5 min | Replicated; persistence enabled |
| Ingress Controller | 99.95% | N/A | 2 min | Multiple replicas; health-checked by load balancer |

**SLA Calculation:**

Overall infrastructure availability is computed as the product of critical path components:
```
Infra_Availability = Control_Plane * Data_Plane * Secrets * Ingress
                   = 0.9995 * 0.9999 * 0.999 * 0.9995
                   = 99.83%
```

This supports a 99.5% SLA for dependent layers with 0.33% margin for application-layer failures.

### 7.2 Scaling Model

#### 7.2.1 Node Scaling (Karpenter)

Karpenter provides just-in-time node provisioning with 60% faster scale-up compared to Cluster Autoscaler:

```
NODE SCALING DECISION FLOW
==========================

Pending Pod                Karpenter                  Cloud API
    |                          |                          |
    |-- unschedulable -------->|                          |
    |   (resource request      |                          |
    |    exceeds capacity)     |                          |
    |                          |                          |
    |                          |-- evaluate NodePool      |
    |                          |   constraints:           |
    |                          |   - instance types       |
    |                          |   - availability zones   |
    |                          |   - capacity type        |
    |                          |   - taints/labels        |
    |                          |                          |
    |                          |-- bin-pack optimization  |
    |                          |   (minimize node count)  |
    |                          |                          |
    |                          |-- launch instance ------>|
    |                          |                          |
    |                          |<-- node ready -----------|
    |                          |   (2-3 minutes)          |
    |                          |                          |
    |<-- pod scheduled --------|                          |

SCALE-DOWN:
- TTL after empty: 30 seconds
- Consolidation: enabled (repack to fewer nodes)
- Disruption budgets: always respected
- Drift detection: replace non-conformant nodes
```

**Karpenter NodePool for General Workloads:**

```yaml
apiVersion: karpenter.sh/v1beta1
kind: NodePool
metadata:
  name: general
spec:
  template:
    metadata:
      labels:
        node-pool: general
        layer: l00
    spec:
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand", "spot"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["m5.xlarge", "m5.2xlarge", "m5.4xlarge", "m6i.xlarge", "m6i.2xlarge"]
        - key: topology.kubernetes.io/zone
          operator: In
          values: ["us-west-2a", "us-west-2b", "us-west-2c"]
      nodeClassRef:
        name: default
  limits:
    cpu: 1000
    memory: 2000Gi
  disruption:
    consolidationPolicy: WhenUnderutilized
    consolidateAfter: 30s
    budgets:
      - nodes: "10%"
```

**Spot Interruption Handling:**

Karpenter requires SQS queue integration for graceful Spot instance termination handling. AWS EventBridge routes EC2 Spot Interruption Warnings to SQS, allowing Karpenter 2-minute notice before termination.

```hcl
# terraform/modules/karpenter/sqs.tf

# SQS queue for Spot interruption events
resource "aws_sqs_queue" "karpenter_interruption" {
  name                      = "${var.cluster_name}-karpenter-interruption"
  message_retention_seconds = 300
  sqs_managed_sse_enabled   = true
  
  tags = merge(var.common_tags, {
    Component = "karpenter"
    Purpose   = "spot-interruption-handling"
  })
}

# Allow EventBridge to send messages to SQS
resource "aws_sqs_queue_policy" "karpenter_interruption" {
  queue_url = aws_sqs_queue.karpenter_interruption.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "events.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.karpenter_interruption.arn
    }]
  })
}

# EventBridge rule for Spot interruption warnings
resource "aws_cloudwatch_event_rule" "spot_interruption" {
  name        = "${var.cluster_name}-spot-interruption"
  description = "Capture EC2 Spot Instance Interruption Warnings for Karpenter"
  
  event_pattern = jsonencode({
    source      = ["aws.ec2"]
    detail-type = ["EC2 Spot Instance Interruption Warning"]
  })
}

resource "aws_cloudwatch_event_target" "spot_interruption" {
  rule      = aws_cloudwatch_event_rule.spot_interruption.name
  target_id = "karpenter-interruption"
  arn       = aws_sqs_queue.karpenter_interruption.arn
}

# EventBridge rule for instance state changes
resource "aws_cloudwatch_event_rule" "instance_state_change" {
  name        = "${var.cluster_name}-instance-state-change"
  description = "Capture EC2 Instance State Changes for Karpenter"
  
  event_pattern = jsonencode({
    source      = ["aws.ec2"]
    detail-type = ["EC2 Instance State-change Notification"]
  })
}

resource "aws_cloudwatch_event_target" "instance_state_change" {
  rule      = aws_cloudwatch_event_rule.instance_state_change.name
  target_id = "karpenter-interruption"
  arn       = aws_sqs_queue.karpenter_interruption.arn
}

# IAM policy for Karpenter to read from SQS
resource "aws_iam_policy" "karpenter_sqs" {
  name = "${var.cluster_name}-karpenter-sqs"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "sqs:DeleteMessage",
        "sqs:GetQueueUrl",
        "sqs:GetQueueAttributes",
        "sqs:ReceiveMessage"
      ]
      Resource = aws_sqs_queue.karpenter_interruption.arn
    }]
  })
}
```

**Karpenter Settings for Interruption Handling:**

```yaml
# helm/infrastructure/karpenter/values.yaml (partial)
settings:
  clusterName: ${CLUSTER_NAME}
  clusterEndpoint: ${CLUSTER_ENDPOINT}
  interruptionQueue: ${CLUSTER_NAME}-karpenter-interruption
  featureGates:
    spotToSpotConsolidation: true
```

#### 7.2.2 Pod Scaling

| Scaler | Trigger | Target Workloads | Configuration |
|--------|---------|------------------|---------------|
| HPA | CPU/Memory utilization | Stateless services | 70% CPU target |
| VPA | Resource recommendation | All pods with history | UpdateMode: Auto |
| KEDA | External metrics | Event-driven workloads | Per-ScaledObject |

**HPA Template:**

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ deployment }}-hpa
  namespace: {{ namespace }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ deployment }}
  minReplicas: 2
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
        - type: Percent
          value: 100
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
```

**KEDA ScaledObject for Queue-Based Workloads:**

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: handoff-processor
  namespace: data-layer
spec:
  scaleTargetRef:
    name: handoff-processor
  minReplicaCount: 1
  maxReplicaCount: 50
  pollingInterval: 15
  cooldownPeriod: 300
  triggers:
    - type: redis
      metadata:
        address: redis.infrastructure.svc.cluster.local:6379
        listName: handoff-queue
        listLength: "10"
        activationListLength: "1"
      authenticationRef:
        name: redis-trigger-auth
```

**KEDA TriggerAuthentication for Queue Access:**

TriggerAuthentication enables KEDA scalers to access secured queue backends. L00 provides the TriggerAuthentication CRD; application layers create instances referencing secrets synced by External Secrets Operator.

```yaml
# TriggerAuthentication for Redis scaler
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: redis-trigger-auth
  namespace: data-layer
spec:
  secretTargetRef:
    - parameter: password
      name: redis-credentials    # Synced by ESO from Vault
      key: password
---
# TriggerAuthentication for SQS scaler (AWS)
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: sqs-trigger-auth
  namespace: agent-pool-tasks
spec:
  podIdentity:
    provider: aws-eks           # Uses IRSA for authentication
---
# TriggerAuthentication for Kafka scaler
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: kafka-trigger-auth
  namespace: data-layer
spec:
  secretTargetRef:
    - parameter: sasl
      name: kafka-credentials
      key: sasl_password
    - parameter: tls
      name: kafka-tls
      key: ca.crt
```

**TriggerAuthentication Patterns:**

| Auth Type | Use Case | Secret Source | KEDA Parameter |
|-----------|----------|---------------|----------------|
| Password | Redis, RabbitMQ | ESO from Vault | `password` |
| IRSA | SQS, Kinesis | Pod identity | `podIdentity.provider` |
| SASL | Kafka | ESO from Vault | `sasl` |
| mTLS | Secure message queues | cert-manager | `tls`, `ca` |

#### 7.2.3 GPU Scaling

| Scenario | Scaling Approach | Node Pool | Time to Scale |
|----------|------------------|-----------|---------------|
| Inference burst | Karpenter provisions GPU nodes | `gpu-inference` | 2-3 minutes |
| Sustained inference | Pre-warmed pool (min_size > 0) | `gpu-inference` | Immediate |
| Batch training | Spot instances, queue-triggered | `spot-gpu-batch` | 3-5 minutes |
| Development | Time-sliced single GPU | `gpu-dev` | Immediate |

**GPU NodePool with MIG:**

```yaml
apiVersion: karpenter.sh/v1beta1
kind: NodePool
metadata:
  name: gpu-inference
spec:
  template:
    metadata:
      labels:
        node-pool: gpu-inference
        nvidia.com/mig.strategy: mixed
    spec:
      requirements:
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["g5.xlarge", "g5.2xlarge", "g5.4xlarge"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      taints:
        - key: nvidia.com/gpu
          value: "true"
          effect: NoSchedule
      nodeClassRef:
        name: gpu-default
  limits:
    nvidia.com/gpu: 20
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 5m
```

### 7.3 High Availability Patterns

#### 7.3.1 Control Plane HA

Managed Kubernetes services (EKS, GKE, AKS) provide control plane HA by default:

```
KUBERNETES CONTROL PLANE HA (Managed)
=====================================

                    +-------------------+
                    | Cloud Load        |
                    | Balancer          |
                    +--------+----------+
                             |
         +-------------------+-------------------+
         |                   |                   |
         v                   v                   v
+--------+--------+ +--------+--------+ +--------+--------+
| API Server      | | API Server      | | API Server      |
| (Zone A)        | | (Zone B)        | | (Zone C)        |
| - Read/Write    | | - Read/Write    | | - Read/Write    |
+-----------------+ +-----------------+ +-----------------+
         |                   |                   |
         +-------------------+-------------------+
                             |
                    +--------v--------+
                    | etcd Cluster    |
                    | (3+ replicas)   |
                    | Multi-AZ        |
                    +-----------------+

Failure Modes:
- Single API server failure: LB routes to healthy instances
- Single etcd failure: Quorum maintained (2/3)
- AZ failure: 2/3 API servers + etcd quorum remain
```

#### 7.3.2 Data Plane HA

| Component | HA Strategy | Replicas | Anti-Affinity | PDB |
|-----------|-------------|----------|---------------|-----|
| Cilium Agent | DaemonSet (per-node) | N (all nodes) | N/A | N/A |
| NGINX Ingress | Deployment | 3+ | Zone spread | minAvailable: 2 |
| External Secrets Operator | Deployment | 2 | Zone spread | minAvailable: 1 |
| cert-manager | Deployment | 2 | Zone spread | minAvailable: 1 |
| Prometheus | StatefulSet (HA pair) | 2 | Zone spread | minAvailable: 1 |
| ArgoCD Server | Deployment | 3 | Zone spread | minAvailable: 2 |
| ArgoCD Repo Server | Deployment | 2 | Zone spread | minAvailable: 1 |
| Gatekeeper Controller | Deployment | 3 | Zone spread | minAvailable: 2 |
| OTEL Collector | DaemonSet + Deployment | N + 2 | Node + Zone | minAvailable: 1 |
| Redis | StatefulSet | 3 | Zone spread | minAvailable: 2 |

**Pod Disruption Budget Template:**

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: {{ component }}-pdb
  namespace: infrastructure
spec:
  minAvailable: {{ min_available }}
  selector:
    matchLabels:
      app.kubernetes.io/name: {{ component }}
```

#### 7.3.3 Zone-Aware Scheduling

```yaml
# Topology spread constraint for zone distribution
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ component }}
spec:
  template:
    spec:
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: {{ component }}
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app: {{ component }}
```

### 7.4 Multi-Region Architecture

#### 7.4.1 Topology

```
MULTI-REGION DEPLOYMENT
=======================

                        +------------------+
                        | Global DNS       |
                        | (Route53/CloudDNS)|
                        | Health-checked   |
                        +--------+---------+
                                 |
                +----------------+----------------+
                |                                 |
                v                                 v
+---------------+---------------+  +---------------+---------------+
| REGION: us-west-2 (Primary)   |  | REGION: us-east-1 (Secondary) |
+-------------------------------+  +-------------------------------+
|                               |  |                               |
| +---------------------------+ |  | +---------------------------+ |
| | Kubernetes Cluster        | |  | | Kubernetes Cluster        | |
| | - Full application stack  | |  | | - Hot standby workloads   | |
| | - Active traffic          | |  | | - Read replicas           | |
| +---------------------------+ |  | +---------------------------+ |
|                               |  |                               |
| +---------------------------+ |  | +---------------------------+ |
| | Data Layer (Primary)      |------>| Data Layer (Replica)      | |
| | - Event Store (write)     | |  | | - Event Store (read)      | |
| | - SQLite (primary)        | Async| - SQLite (replica)        | |
| +---------------------------+ Repl | +---------------------------+ |
|                               |  |                               |
| +---------------------------+ |  | +---------------------------+ |
| | Observability (Local)     | |  | | Observability (Local)     | |
| | - Prometheus              | |  | | - Prometheus              | |
| | - Loki                    | |  | | - Loki                    | |
| +-------------+-------------+ |  | +---------------------------+ |
|               |               |  |                               |
+---------------+---------------+  +-------------------------------+
                |
                v
        +-------+-------+
        | Thanos Query  |
        | (Global View) |
        +---------------+
```

#### 7.4.2 Failover Procedures

| Trigger | Detection Method | Failover Action | RTO | Runbook |
|---------|------------------|-----------------|-----|---------|
| Region outage | Health check failure (3x consecutive) | DNS failover to secondary | 5 min | RB-001 |
| AZ outage | Node NotReady (multiple nodes) | Karpenter provisions in healthy AZs | 3 min | RB-002 |
| Node failure | kubelet heartbeat timeout | Pod rescheduling via scheduler | 1 min | RB-003 |
| Control plane degraded | API server latency > 5s | Escalate to cloud provider | 10 min | RB-004 |

**DNS Failover Configuration (Route53):**

```hcl
resource "aws_route53_health_check" "primary" {
  fqdn              = "api.us-west-2.example.com"
  port              = 443
  type              = "HTTPS"
  resource_path     = "/healthz"
  failure_threshold = "3"
  request_interval  = "30"

  tags = {
    Name = "primary-region-health-check"
  }
}

resource "aws_route53_record" "api" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "api.example.com"
  type    = "A"

  failover_routing_policy {
    type = "PRIMARY"
  }

  set_identifier  = "primary"
  health_check_id = aws_route53_health_check.primary.id

  alias {
    name                   = aws_lb.primary.dns_name
    zone_id                = aws_lb.primary.zone_id
    evaluate_target_health = true
  }
}
```

### 7.5 Capacity Planning

| Resource | Sizing Formula | Headroom | Alert Threshold |
|----------|----------------|----------|-----------------|
| CPU | `(agent_count * 0.5 cores) + (base_services * 2 cores)` | 30% | 70% utilization |
| Memory | `(agent_count * 2GB) + (base_services * 4GB)` | 30% | 70% utilization |
| GPU | `ceil(inference_qps / 50) * MIG_instances` | 20% | 80% utilization |
| Storage | `(event_rate/sec * retention_days * 86400 * avg_event_size) + snapshots` | 40% | 60% capacity |
| Network | `(agent_count * 10 Mbps) + (inference_traffic)` | 50% | 50% capacity |

**Capacity Estimation Example (100 agents):**

| Resource | Calculation | Provisioned |
|----------|-------------|-------------|
| CPU | `(100 * 0.5) + (10 * 2) = 70 cores` | 100 cores (30% headroom) |
| Memory | `(100 * 2GB) + (10 * 4GB) = 240GB` | 350GB (30% headroom) |
| GPU | `ceil(500 qps / 50) = 10 MIG instances` | 12 instances (20% headroom) |
| Storage | `(100 events/sec * 30d * 86400 * 1KB) = 260GB` | 450GB (40% headroom) |

### 7.6 Failure Modes and Recovery

| Failure Mode | Error Code | Detection | Auto-Recovery | Manual Recovery |
|--------------|------------|-----------|---------------|-----------------|
| Node unreachable | E0001 | kubelet heartbeat | Pod rescheduling | Cordon + drain |
| Storage exhausted | E0002 | PVC capacity alert | None | Expand PVC |
| Secret sync failure | E0201 | ExternalSecret status | Retry backoff | Check Vault connectivity |
| Certificate expired | E0401 | cert-manager status | Auto-renewal | Manual renewal |
| Ingress unavailable | E0101 | Health check failure | LB failover | Check Ingress pods |
| OOM kill | E0301 | Container restart | VPA adjustment | Increase limits |
| GPU allocation failure | E0302 | Pending pod | Karpenter scale-up | Check GPU quota |

---

## 8. Security

### 8.1 Security Architecture

Infrastructure security implements defense in depth across four layers:

```
SECURITY LAYERS
===============

+------------------------------------------------------------------+
|  LAYER 1: Network Security                                        |
|  +--------------------------------------------------------------+ |
|  | - Cilium NetworkPolicy (L3/L4 filtering)                     | |
|  | - CiliumNetworkPolicy (L7, FQDN egress control)              | |
|  | - Default deny-all per namespace                             | |
|  | - mTLS between services (Cilium service mesh)                | |
|  +--------------------------------------------------------------+ |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|  LAYER 2: Identity & Authentication                               |
|  +--------------------------------------------------------------+ |
|  | - Kubernetes ServiceAccount tokens (bound tokens)            | |
|  | - Mutual TLS via Cilium identity-aware policies              | |
|  | - Vault Kubernetes Auth for secret access                    | |
|  | - OIDC federation for human access                           | |
|  +--------------------------------------------------------------+ |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|  LAYER 3: Authorization                                           |
|  +--------------------------------------------------------------+ |
|  | - Kubernetes RBAC (namespace-scoped)                         | |
|  | - OPA Gatekeeper (admission control)                         | |
|  | - Vault policies (secret access control)                     | |
|  | - Data Layer ABAC (application-level)                        | |
|  +--------------------------------------------------------------+ |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|  LAYER 4: Data Protection                                         |
|  +--------------------------------------------------------------+ |
|  | - Encryption at rest (EBS/PD encryption with KMS)            | |
|  | - Encryption in transit (mTLS, TLS 1.3)                      | |
|  | - Secrets encryption (Vault envelope encryption)             | |
|  | - Audit logging (all API server operations)                  | |
|  +--------------------------------------------------------------+ |
+------------------------------------------------------------------+
```

**Node Operating System Hardening:**

Per NIST 800-190 Container Security recommendations, worker nodes run container-optimized operating systems with minimal attack surface. These OS images are immutable, automatically updated, and hardened specifically for container workloads.

| Operating System | Provider | Recommendation | Update Mechanism |
|------------------|----------|----------------|------------------|
| Amazon Bottlerocket | AWS EKS | **Primary** | Automatic via SSM |
| Flatcar Container Linux | Multi-cloud | Alternative | Automatic via Nebraska |
| Amazon Linux 2023 | AWS EKS | Acceptable | Manual via AMI |
| Ubuntu 22.04 | Multi-cloud | Acceptable | Manual via package updates |

**Bottlerocket Configuration (Recommended):**

```hcl
# terraform/modules/cluster/nodeclass.tf

resource "aws_eks_node_group" "system" {
  # Use Bottlerocket AMI for enhanced security
  ami_type = "BOTTLEROCKET_x86_64"
  
  # Bottlerocket requires specific launch template
  launch_template {
    id      = aws_launch_template.bottlerocket.id
    version = aws_launch_template.bottlerocket.latest_version
  }
}

resource "aws_launch_template" "bottlerocket" {
  name_prefix = "${var.cluster_name}-bottlerocket-"
  
  # Bottlerocket user data in TOML format
  user_data = base64encode(<<-EOF
    [settings.kubernetes]
    cluster-name = "${var.cluster_name}"
    api-server = "${aws_eks_cluster.main.endpoint}"
    cluster-certificate = "${aws_eks_cluster.main.certificate_authority[0].data}"
    
    [settings.kubernetes.node-labels]
    "node.kubernetes.io/os" = "bottlerocket"
    
    [settings.host-containers.admin]
    enabled = false
    
    [settings.host-containers.control]
    enabled = true
  EOF
  )
}
```

**Karpenter EC2NodeClass for Bottlerocket:**

```yaml
apiVersion: karpenter.k8s.aws/v1beta1
kind: EC2NodeClass
metadata:
  name: bottlerocket
  labels:
    layer: l00
spec:
  amiFamily: Bottlerocket
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: ${CLUSTER_NAME}
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: ${CLUSTER_NAME}
  role: ${KARPENTER_NODE_ROLE}
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 4Gi
        volumeType: gp3
        encrypted: true
    - deviceName: /dev/xvdb
      ebs:
        volumeSize: 50Gi
        volumeType: gp3
        encrypted: true
```

**OS Hardening Benefits:**

| Hardening | Bottlerocket | Standard Linux |
|-----------|--------------|----------------|
| Package manager | None (immutable) | apt/yum (mutable) |
| Shell access | Disabled by default | SSH enabled |
| Auto-updates | Atomic, automatic | Manual intervention |
| Attack surface | Minimal container runtime | Full OS |
| CIS compliance | Built-in | Requires hardening |

#### 8.2.1 Default Network Policies

All application namespaces receive default-deny ingress policies. DNS egress is explicitly allowed.

```yaml
# Applied to all application namespaces by L00
# Template: deny all ingress by default
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: {{ namespace }}
  labels:
    layer: l00
    policy: default
spec:
  podSelector: {}
  policyTypes:
    - Ingress

---
# Allow DNS egress to kube-system
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns-egress
  namespace: {{ namespace }}
  labels:
    layer: l00
    policy: default
spec:
  podSelector: {}
  policyTypes:
    - Egress
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53

---
# Allow Prometheus scraping
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-prometheus-scrape
  namespace: {{ namespace }}
  labels:
    layer: l00
    policy: default
spec:
  podSelector: {}
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: infrastructure
          podSelector:
            matchLabels:
              app: prometheus
      ports:
        - protocol: TCP
          port: 9090
        - protocol: TCP
          port: 8080
```

#### 8.2.2 OC-1 Enforcement (Agent Communication Prohibition)

The Data Layer's OC-1 constraint (Operational Constraint 1: No Direct Agent-to-Agent Communication) is enforced at the network level:

```yaml
# Blocks direct agent-to-agent communication
# Applied to all agent-pool-* namespaces
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: oc1-block-agent-to-agent
  namespace: {{ agent_pool_namespace }}
  labels:
    layer: l00
    policy: oc1
    constraint: agent-isolation
spec:
  description: "OC-1: Agents cannot communicate directly with other agents"
  endpointSelector:
    matchLabels:
      workload-type: agent
  egressDeny:
    - toEndpoints:
        - matchLabels:
            workload-type: agent
    - toEndpoints:
        - matchExpressions:
            - key: io.kubernetes.pod.namespace
              operator: In
              values:
                - agent-pool-1
                - agent-pool-2
                - agent-pool-3
  egress:
    # Agents CAN communicate with Data Layer services
    - toEndpoints:
        - matchLabels:
            layer: l01
      toPorts:
        - ports:
            - port: "8080"
              protocol: TCP
    # Agents CAN communicate with Model Gateway
    - toEndpoints:
        - matchLabels:
            layer: l04
      toPorts:
        - ports:
            - port: "8080"
              protocol: TCP
```

#### 8.2.3 LLM Provider Egress

Model Gateway requires egress to external LLM providers. Cilium FQDN-based policies restrict egress to approved domains only:

```yaml
# Applied to model-gateway namespace
# Addresses Gap G-005
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-llm-provider-egress
  namespace: model-gateway
  labels:
    layer: l00
    policy: egress
spec:
  description: "Allow egress to approved LLM providers only"
  endpointSelector:
    matchLabels:
      app: model-gateway
  egress:
    # Anthropic API
    - toFQDNs:
        - matchName: "api.anthropic.com"
      toPorts:
        - ports:
            - port: "443"
              protocol: TCP
    # OpenAI API
    - toFQDNs:
        - matchName: "api.openai.com"
      toPorts:
        - ports:
            - port: "443"
              protocol: TCP
    # Google AI (Gemini)
    - toFQDNs:
        - matchName: "generativelanguage.googleapis.com"
      toPorts:
        - ports:
            - port: "443"
              protocol: TCP
    # Azure OpenAI (pattern match for regional endpoints)
    - toFQDNs:
        - matchPattern: "*.openai.azure.com"
      toPorts:
        - ports:
            - port: "443"
              protocol: TCP
    # AWS Bedrock
    - toFQDNs:
        - matchPattern: "bedrock-runtime.*.amazonaws.com"
      toPorts:
        - ports:
            - port: "443"
              protocol: TCP
```

### 8.3 Secrets Management

#### 8.3.1 Secret Hierarchy

```
SECRETS ARCHITECTURE
====================

HashiCorp Vault (External)
    |
    |-- secret/data/infrastructure/
    |   |-- cluster-credentials
    |   |-- tls-ca-key
    |   |-- observability-tokens
    |   +-- redis-password
    |
    |-- secret/data/data-layer/
    |   |-- database-credentials
    |   |-- encryption-keys (KEK)
    |   |-- identity-keys (DID signing)
    |   +-- event-store-credentials
    |
    |-- secret/data/model-gateway/
    |   |-- anthropic-api-key
    |   |-- openai-api-key
    |   |-- google-ai-api-key
    |   +-- azure-openai-credentials
    |
    |-- secret/data/api-gateway/
    |   |-- oauth-client-secret
    |   |-- jwt-signing-key
    |   +-- rate-limit-tokens
    |
    +-- secret/data/agent-pools/
        |-- pool-1-credentials
        |-- pool-2-credentials
        +-- shared-tool-credentials

                    |
                    | External Secrets Operator
                    | (ClusterSecretStore)
                    v

Kubernetes Secrets (Synced)
    |
    +-- Each namespace receives secrets from respective Vault path
    +-- Secrets refreshed every 1 hour (default)
    +-- Reloader triggers pod restarts on secret update
```

#### 8.3.2 External Secrets Configuration

**ClusterSecretStore (Vault Backend):**

```yaml
# Addresses Gap G-004 (partially)
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: vault-backend
spec:
  provider:
    vault:
      server: "https://vault.example.com"
      path: "secret"
      version: "v2"
      auth:
        kubernetes:
          mountPath: "kubernetes"
          role: "external-secrets"
          serviceAccountRef:
            name: "external-secrets"
            namespace: "infrastructure"
      caProvider:
        type: ConfigMap
        name: vault-ca
        namespace: infrastructure
        key: ca.crt
```

**ExternalSecret Template:**

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: {{ secret_name }}
  namespace: {{ namespace }}
  labels:
    layer: {{ layer }}
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: ClusterSecretStore
  target:
    name: {{ secret_name }}
    creationPolicy: Owner
    template:
      type: Opaque
      metadata:
        annotations:
          reloader.stakater.com/match: "true"
  data:
    - secretKey: {{ key }}
      remoteRef:
        key: secret/data/{{ vault_path }}
        property: {{ property }}
```

#### 8.3.3 Secret Rotation

| Secret Type | Rotation Frequency | Method | Zero-Downtime |
|-------------|-------------------|--------|---------------|
| LLM API Keys | 90 days | Vault rotation + ESO sync | Yes (Reloader) |
| Database Credentials | 30 days | Vault dynamic secrets | Yes (connection pool refresh) |
| TLS Certificates | 60 days before expiry | cert-manager auto-renewal | Yes (in-place update) |
| Encryption Keys (KEK) | Annual | Manual rotation with re-encryption | Planned downtime window |
| Service Account Tokens | 1 hour | Kubernetes bound tokens | Yes (automatic) |

**Reloader Annotation for Automatic Pod Restart:**

```yaml
metadata:
  annotations:
    reloader.stakater.com/auto: "true"
```

### 8.4 RBAC Configuration

#### 8.4.1 Role Hierarchy

| Role | Scope | Permissions | Principals |
|------|-------|-------------|------------|
| `cluster-admin` | Cluster | Full access | Platform SREs only |
| `infra-admin` | infrastructure namespace | Full namespace access | Infrastructure team |
| `layer-admin` | Per-layer namespace | Full namespace access | Layer maintainers |
| `layer-developer` | Per-layer namespace | Create/update workloads, read secrets | Developers |
| `layer-reader` | Per-layer namespace | Read-only access | Auditors, on-call |
| `agent-pool-operator` | agent-pool-* namespaces | Manage agent pods | Automation service accounts |

#### 8.4.2 ClusterRole Definitions

```yaml
# Layer Admin Role (applied per-namespace)
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: layer-admin
rules:
  - apiGroups: [""]
    resources: ["pods", "services", "configmaps", "secrets", "persistentvolumeclaims"]
    verbs: ["*"]
  - apiGroups: ["apps"]
    resources: ["deployments", "statefulsets", "daemonsets", "replicasets"]
    verbs: ["*"]
  - apiGroups: ["networking.k8s.io"]
    resources: ["networkpolicies", "ingresses"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["external-secrets.io"]
    resources: ["externalsecrets"]
    verbs: ["*"]
  - apiGroups: ["cert-manager.io"]
    resources: ["certificates"]
    verbs: ["*"]

---
# Layer Developer Role
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: layer-developer
rules:
  - apiGroups: [""]
    resources: ["pods", "services", "configmaps"]
    verbs: ["*"]
  - apiGroups: [""]
    resources: ["secrets"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources: ["deployments", "statefulsets"]
    verbs: ["get", "list", "watch", "create", "update", "patch"]
  - apiGroups: [""]
    resources: ["pods/log", "pods/exec"]
    verbs: ["get", "list", "create"]
```

#### 8.4.3 Service Account Bindings

```yaml
# Template for layer service accounts
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {{ layer }}-service
  namespace: {{ layer }}-namespace
  annotations:
    # Vault Kubernetes auth
    vault.hashicorp.com/agent-inject: "true"
    vault.hashicorp.com/role: "{{ layer }}-role"

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: {{ layer }}-service-binding
  namespace: {{ layer }}-namespace
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: layer-developer
subjects:
  - kind: ServiceAccount
    name: {{ layer }}-service
    namespace: {{ layer }}-namespace
```

#### 8.4.4 AWS IAM Integration

**IAM Roles for Service Accounts (IRSA):**

Standard mechanism for pod-level AWS IAM permissions. Requires OIDC provider configured for the EKS cluster.

```yaml
# ServiceAccount with IRSA annotation
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-reader
  namespace: data-layer
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/data-layer-s3-reader
```

**EKS Pod Identity (Kubernetes 1.24+):**

EKS Pod Identity is the newer, simplified alternative to IRSA. It eliminates the need for an OIDC provider and simplifies IAM role configuration. Recommended for new deployments on EKS 1.24+.

| Feature | IRSA | EKS Pod Identity |
|---------|------|------------------|
| Setup complexity | OIDC provider required | No OIDC required |
| IAM trust policy | Complex per-SA | Simplified association |
| Cross-account | Manual trust | Native support |
| Session tags | Not supported | Supported |
| Minimum EKS version | 1.13 | 1.24 |

**EKS Pod Identity Configuration:**

```hcl
# terraform/modules/iam/pod-identity.tf

# Enable EKS Pod Identity Agent addon
resource "aws_eks_addon" "pod_identity" {
  cluster_name  = var.cluster_name
  addon_name    = "eks-pod-identity-agent"
  addon_version = "v1.0.0-eksbuild.1"
}

# Create Pod Identity Association
resource "aws_eks_pod_identity_association" "data_layer_s3" {
  cluster_name    = var.cluster_name
  namespace       = "data-layer"
  service_account = "s3-reader"
  role_arn        = aws_iam_role.data_layer_s3.arn
}

# IAM role (simpler trust policy with Pod Identity)
resource "aws_iam_role" "data_layer_s3" {
  name = "${var.cluster_name}-data-layer-s3"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "pods.eks.amazonaws.com"
      }
      Action = [
        "sts:AssumeRole",
        "sts:TagSession"
      ]
    }]
  })
}
```

**Migration Path:**

Existing IRSA annotations continue to work. New deployments should prefer EKS Pod Identity. Both can coexist during migration.

### 8.5 Pod Security Standards

| Namespace Category | Pod Security Standard | Enforcement Mode |
|--------------------|----------------------|------------------|
| kube-system | Privileged | warn |
| infrastructure | Baseline | enforce |
| gatekeeper-system | Baseline | enforce |
| application layers (L01-L11) | Restricted | enforce |
| agent-pool-* | Restricted | enforce |

**Namespace Label Configuration:**

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: {{ namespace }}
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: latest
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: latest
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: latest
    # Standard labels
    layer: {{ layer }}
    cost-center: {{ cost_center }}
    environment: {{ environment }}
```

**Restricted Pod Security Context:**

```yaml
# Required security context for restricted namespaces
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: {{ container }}
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop:
            - ALL
```

### 8.5.1 RuntimeClass for Sandbox Isolation

Infrastructure Layer provides RuntimeClass resources as hooks for L02 Agent Runtime to enable sandboxed execution environments (gVisor, Kata Containers). L00 provisions the RuntimeClass CRDs; L02 selects appropriate runtime for agent workloads.

**RuntimeClass Definitions:**

```yaml
# L00 provisions RuntimeClass for gVisor
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: gvisor
  labels:
    layer: l00
    component: sandbox
handler: runsc
overhead:
  podFixed:
    memory: "128Mi"
    cpu: "100m"
scheduling:
  nodeSelector:
    sandbox-runtime: gvisor
---
# RuntimeClass for Kata Containers (alternative)
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: kata-containers
  labels:
    layer: l00
    component: sandbox
handler: kata-qemu
overhead:
  podFixed:
    memory: "256Mi"
    cpu: "200m"
scheduling:
  nodeSelector:
    sandbox-runtime: kata
```

**RuntimeClass Responsibility Matrix:**

| Artifact | Owner | Description |
|----------|-------|-------------|
| RuntimeClass CRD | L00 Infrastructure | Defines available sandbox runtimes |
| Node selector labels | L00 Infrastructure | Identifies nodes with sandbox support |
| gVisor/Kata installation | L00 Infrastructure | Installs runtime on designated nodes |
| Pod runtimeClassName | L02 Agent Runtime | Selects appropriate runtime per agent |
| Sandbox policy decision | L02 Agent Runtime | Determines which agents require isolation |

**L02 Usage Pattern:**

```yaml
# L02 Agent Runtime references L00-provided RuntimeClass
apiVersion: v1
kind: Pod
metadata:
  name: agent-execution
  namespace: agent-pool-untrusted
spec:
  runtimeClassName: gvisor  # L00 provides this RuntimeClass
  containers:
    - name: agent
      image: agent-runtime:v1.0
      # L02 defines agent-specific configuration
```

**Node Pool Configuration for Sandbox Runtimes:**

Infrastructure Layer configures dedicated node pools with sandbox runtimes:

| Node Pool | RuntimeClass | Use Case | Node Label |
|-----------|--------------|----------|------------|
| sandbox-gvisor | gvisor | Untrusted code execution | sandbox-runtime=gvisor |
| sandbox-kata | kata-containers | High isolation requirements | sandbox-runtime=kata |
| standard | (none) | Trusted workloads | sandbox-runtime=none |

### 8.6 Certificate Management

#### 8.6.1 cert-manager Deployment

```yaml
# Addresses Gap G-004
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cert-manager
  namespace: cert-manager
  labels:
    app: cert-manager
    layer: l00
spec:
  replicas: 2
  selector:
    matchLabels:
      app: cert-manager
  template:
    metadata:
      labels:
        app: cert-manager
        layer: l00
    spec:
      serviceAccountName: cert-manager
      containers:
        - name: cert-manager
          image: quay.io/jetstack/cert-manager-controller:v1.13.0
          args:
            - --cluster-resource-namespace=$(POD_NAMESPACE)
            - --leader-election-namespace=kube-system
            - --enable-certificate-owner-ref=true
          resources:
            requests:
              cpu: 50m
              memory: 64Mi
            limits:
              cpu: 200m
              memory: 256Mi
```

#### 8.6.2 ClusterIssuers

```yaml
# Production issuer (Let's Encrypt)
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: platform-team@example.com
    privateKeySecretRef:
      name: letsencrypt-prod-account-key
    solvers:
      - http01:
          ingress:
            class: nginx
      - dns01:
          route53:
            region: us-west-2
            hostedZoneID: Z1234567890ABC

---
# Internal CA issuer (Vault PKI)
# Addresses Gap G-018
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: vault-pki
spec:
  vault:
    server: https://vault.example.com
    path: pki/sign/internal
    auth:
      kubernetes:
        role: cert-manager
        mountPath: /v1/auth/kubernetes
        serviceAccountRef:
          name: cert-manager
```

### 8.7 Threat Model

| Threat | Attack Vector | Mitigation | Detection | Error Code |
|--------|---------------|------------|-----------|------------|
| Container escape | Kernel exploit | gVisor runtime (L02), Seccomp profiles | Falco alerts | E0102 |
| Secret exfiltration | Compromised pod | Vault dynamic secrets, short TTL, audit | Vault audit logs | E0202 |
| Lateral movement | Network access | Default-deny NetworkPolicy, mTLS | Hubble flow logs | E0103 |
| Privilege escalation | RBAC misconfiguration | OPA policies, PSS enforcement | Admission audit | E0104 |
| Supply chain attack | Malicious image | Image signing (Cosign), registry scanning | Trivy alerts | E0105 |
| DDoS | Traffic flood | Cloud WAF, pod rate limiting | Traffic anomaly | E0106 |
| Credential stuffing | API brute force | Rate limiting, account lockout (L09) | Auth failure rate | E0107 |
| Data exfiltration | Egress to unauthorized | FQDN egress policies | Hubble DNS logs | E0108 |

### 8.8 Supply Chain Security

#### 8.8.1 Overview

Supply chain security protects against compromised container images, malicious Helm charts, and tampered infrastructure components. The specification targets SLSA Level 2 compliance for all infrastructure components.

```
SUPPLY CHAIN SECURITY ARCHITECTURE
===================================

+-----------------------------------------------------------------------+
|                         BUILD PIPELINE                                 |
|  +------------------+    +------------------+    +------------------+  |
|  | Source Code      | -> | CI Build         | -> | Artifact         |  |
|  | (Signed Commits) |    | (GitHub Actions) |    | Registry (ECR)   |  |
|  +------------------+    +------------------+    +------------------+  |
|           |                       |                       |           |
|           v                       v                       v           |
|  +------------------+    +------------------+    +------------------+  |
|  | Git Signing      |    | SLSA Provenance  |    | Image Signing    |  |
|  | (GPG/SSH)        |    | (slsa-github)    |    | (Cosign)         |  |
|  +------------------+    +------------------+    +------------------+  |
+-----------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------+
|                         ADMISSION CONTROL                              |
|  +------------------+    +------------------+    +------------------+  |
|  | Signature        | -> | SBOM             | -> | Policy           |  |
|  | Verification     |    | Verification     |    | Enforcement      |  |
|  | (Cosign)         |    | (Syft/Grype)     |    | (Kyverno)        |  |
|  +------------------+    +------------------+    +------------------+  |
+-----------------------------------------------------------------------+
```

#### 8.8.2 SLSA Compliance Target

| SLSA Level | Requirements | Implementation | Status |
|------------|--------------|----------------|--------|
| Level 1 | Build provenance exists | GitHub Actions attestation | Implemented |
| Level 2 | Hosted build + signed provenance | slsa-github-generator + Cosign | **Target** |
| Level 3 | Hardened builds, tamper-proof logs | Future consideration | Deferred |

#### 8.8.3 Image Signing with Sigstore Cosign

All container images deployed to the cluster must be signed with Cosign using keyless signing via Sigstore.

**Signing Process (CI Pipeline):**

```yaml
# .github/workflows/build.yaml
name: Build and Sign Image

on:
  push:
    branches: [main]
    
permissions:
  id-token: write    # Required for OIDC keyless signing
  packages: write
  contents: read
  
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build image
        run: |
          docker build -t ${{ env.REGISTRY }}/${{ env.IMAGE }}:${{ github.sha }} .
          
      - name: Install Cosign
        uses: sigstore/cosign-installer@v3
        
      - name: Sign image (keyless)
        run: |
          cosign sign --yes \
            ${{ env.REGISTRY }}/${{ env.IMAGE }}:${{ github.sha }}
            
      - name: Generate and attach SBOM
        run: |
          syft ${{ env.REGISTRY }}/${{ env.IMAGE }}:${{ github.sha }} \
            -o spdx-json > sbom.spdx.json
          cosign attach sbom --sbom sbom.spdx.json \
            ${{ env.REGISTRY }}/${{ env.IMAGE }}:${{ github.sha }}
            
      - name: Attest SBOM
        run: |
          cosign attest --yes --predicate sbom.spdx.json \
            --type spdxjson \
            ${{ env.REGISTRY }}/${{ env.IMAGE }}:${{ github.sha }}
```

**SLSA Provenance Generation:**

```yaml
# .github/workflows/slsa.yaml
name: SLSA Provenance

on:
  workflow_call:
    inputs:
      image:
        required: true
        type: string
        
jobs:
  provenance:
    permissions:
      actions: read
      id-token: write
      packages: write
      
    uses: slsa-framework/slsa-github-generator/.github/workflows/generator_container_slsa3.yml@v1.9.0
    with:
      image: ${{ inputs.image }}
      registry-username: ${{ github.actor }}
    secrets:
      registry-password: ${{ secrets.GITHUB_TOKEN }}
```

#### 8.8.4 Admission Control with Kyverno

Kyverno policies enforce image signature verification at admission time. Unsigned images are rejected.

```yaml
# manifests/security/kyverno-image-policy.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-image-signatures
  labels:
    layer: l00
    component: supply-chain-security
  annotations:
    policies.kyverno.io/title: Verify Image Signatures
    policies.kyverno.io/category: Supply Chain Security
    policies.kyverno.io/severity: high
spec:
  validationFailureAction: Enforce
  background: true
  webhookTimeoutSeconds: 30
  rules:
    - name: verify-cosign-signature
      match:
        any:
          - resources:
              kinds:
                - Pod
      verifyImages:
        - imageReferences:
            - "*.dkr.ecr.*.amazonaws.com/*"
            - "ghcr.io/your-org/*"
          attestors:
            - entries:
                - keyless:
                    subject: "https://github.com/your-org/*"
                    issuer: "https://token.actions.githubusercontent.com"
                    rekor:
                      url: https://rekor.sigstore.dev
          attestations:
            - predicateType: https://spdx.dev/Document
              conditions:
                - all:
                    - key: "{{ creationInfo.created }}"
                      operator: NotEquals
                      value: ""
```

**Policy Exceptions:**

```yaml
# Exceptions for system images
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-image-signatures
spec:
  rules:
    - name: verify-cosign-signature
      exclude:
        any:
          - resources:
              namespaces:
                - kube-system
                - gatekeeper-system
          - resources:
              selector:
                matchLabels:
                  skip-signature-verification: "true"
```

#### 8.8.5 SBOM Generation and Verification

| Tool | Purpose | Integration Point |
|------|---------|-------------------|
| Syft | SBOM generation | CI pipeline |
| Grype | Vulnerability scanning | CI pipeline + admission |
| Cosign | SBOM attestation | CI pipeline |
| Kyverno | SBOM verification | Admission control |

**Vulnerability Gate:**

```yaml
# manifests/security/kyverno-vuln-policy.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: block-critical-vulnerabilities
  labels:
    layer: l00
spec:
  validationFailureAction: Enforce
  rules:
    - name: check-vulnerabilities
      match:
        any:
          - resources:
              kinds:
                - Pod
      verifyImages:
        - imageReferences:
            - "*"
          attestations:
            - predicateType: https://cosign.sigstore.dev/attestation/vuln/v1
              conditions:
                - all:
                    - key: "{{ scanner.result.criticalCount }}"
                      operator: Equals
                      value: "0"
                    - key: "{{ scanner.result.highCount }}"
                      operator: LessThan
                      value: "5"
```

#### 8.8.6 Helm Chart Verification

Helm charts are verified before deployment using Cosign signatures.

```yaml
# ArgoCD configuration for chart verification
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  # Enable OCI chart verification
  helm.valuesFileSchemes: >-
    secrets+gpg-import, secrets+gpg-import-kubernetes,
    secrets+age-import, secrets+age-import-kubernetes
  
  # Cosign verification for OCI charts
  resource.customizations: |
    admissionregistration.k8s.io/ValidatingWebhookConfiguration:
      health.lua: |
        hs = {}
        hs.status = "Healthy"
        return hs
```

**Chart Signing (Publisher Side):**

```bash
#!/bin/bash
# scripts/sign-helm-chart.sh

CHART_NAME=$1
CHART_VERSION=$2

# Package chart
helm package charts/${CHART_NAME} --version ${CHART_VERSION}

# Push to OCI registry
helm push ${CHART_NAME}-${CHART_VERSION}.tgz oci://registry.example.com/charts/

# Sign with Cosign
cosign sign --yes registry.example.com/charts/${CHART_NAME}:${CHART_VERSION}
```

#### 8.8.7 Supply Chain Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `supply_chain_signature_failures_total` | Images rejected due to missing/invalid signature | > 0 |
| `supply_chain_sbom_missing_total` | Images without SBOM attestation | > 0 |
| `supply_chain_critical_vulns_total` | Critical vulnerabilities detected | > 0 |
| `supply_chain_provenance_missing_total` | Images without SLSA provenance | > 0 |

```yaml
# Prometheus alerting rule
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: supply-chain-alerts
  namespace: infrastructure
spec:
  groups:
    - name: supply-chain
      rules:
        - alert: ImageSignatureVerificationFailed
          expr: increase(kyverno_policy_results_total{policy_name="verify-image-signatures",rule_result="fail"}[5m]) > 0
          for: 1m
          labels:
            severity: high
          annotations:
            summary: "Unsigned image deployment attempted"
            runbook_url: "runbooks/supply-chain-failure.md"
```

---

## 9. Observability

### 9.1 Observability Architecture

```
OBSERVABILITY STACK
===================

+------------------------------------------------------------------+
|                         DATA SOURCES                              |
+------------------------------------------------------------------+
|                                                                   |
|  Application Pods         Infrastructure         Cloud Provider   |
|  +--------------+         +--------------+       +--------------+ |
|  | /metrics     |         | Node metrics |       | CloudWatch/  | |
|  | stdout/stderr|         | kubelet      |       | Stackdriver  | |
|  | OTLP traces  |         | cAdvisor     |       +--------------+ |
|  +--------------+         | DCGM (GPU)   |                        |
|         |                 +--------------+                        |
|         |                        |                                |
+---------+------------------------+--------------------------------+
          |                        |
          v                        v
+------------------------------------------------------------------+
|                       COLLECTION LAYER                            |
+------------------------------------------------------------------+
|                                                                   |
|  +----------------+  +----------------+  +-------------------+    |
|  | Prometheus     |  | Promtail       |  | OTEL Collector    |    |
|  | (scrape)       |  | (log ship)     |  | (traces + OTLP)   |    |
|  +-------+--------+  +-------+--------+  +---------+---------+    |
|          |                   |                     |              |
+----------+-------------------+---------------------+--------------+
           |                   |                     |
           v                   v                     v
+------------------------------------------------------------------+
|                        STORAGE LAYER                              |
+------------------------------------------------------------------+
|                                                                   |
|  +----------------+  +----------------+  +-------------------+    |
|  | Prometheus     |  | Loki           |  | Tempo             |    |
|  | TSDB (15d)     |  | (30d)          |  | (7d)              |    |
|  +-------+--------+  +-------+--------+  +---------+---------+    |
|          |                   |                     |              |
|          v                   |                     |              |
|  +----------------+          |                     |              |
|  | Thanos         |          |                     |              |
|  | (1yr archive)  |          |                     |              |
|  | S3/GCS         |          v                     v              |
|  +----------------+  +----------------+  +-------------------+    |
|                      | S3/GCS         |  | S3/GCS            |    |
|                      | (blob storage) |  | (blob storage)    |    |
|                      +----------------+  +-------------------+    |
|                                                                   |
+------------------------------------------------------------------+
           |                   |                     |
           v                   v                     v
+------------------------------------------------------------------+
|                      PRESENTATION LAYER                           |
+------------------------------------------------------------------+
|                                                                   |
|  +----------------+  +----------------+  +-------------------+    |
|  | Grafana        |  | Alertmanager   |  | OpenCost          |    |
|  | (dashboards)   |  | (alerts)       |  | (cost tracking)   |    |
|  +----------------+  +----------------+  +-------------------+    |
|                                                                   |
+------------------------------------------------------------------+
```

### 9.2 OpenTelemetry Collector Deployment

Addresses Gap G-002. OTEL Collector deployment uses a hybrid model: DaemonSet for node-level collection plus Deployment for aggregation.

```yaml
# OTEL Collector DaemonSet (per-node)
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: otel-collector-agent
  namespace: infrastructure
  labels:
    app: otel-collector
    component: agent
    layer: l00
spec:
  selector:
    matchLabels:
      app: otel-collector
      component: agent
  template:
    metadata:
      labels:
        app: otel-collector
        component: agent
        layer: l00
    spec:
      serviceAccountName: otel-collector
      containers:
        - name: otel-collector
          image: otel/opentelemetry-collector-contrib:0.91.0
          args:
            - --config=/etc/otel/config.yaml
          ports:
            - containerPort: 4317
              name: otlp-grpc
              hostPort: 4317
            - containerPort: 4318
              name: otlp-http
              hostPort: 4318
            - containerPort: 8888
              name: metrics
          volumeMounts:
            - name: config
              mountPath: /etc/otel
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
      volumes:
        - name: config
          configMap:
            name: otel-collector-agent-config

---
# OTEL Collector Gateway (aggregator)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: otel-collector-gateway
  namespace: infrastructure
  labels:
    app: otel-collector
    component: gateway
    layer: l00
spec:
  replicas: 2
  selector:
    matchLabels:
      app: otel-collector
      component: gateway
  template:
    metadata:
      labels:
        app: otel-collector
        component: gateway
        layer: l00
    spec:
      containers:
        - name: otel-collector
          image: otel/opentelemetry-collector-contrib:0.91.0
          args:
            - --config=/etc/otel/config.yaml
          ports:
            - containerPort: 4317
              name: otlp-grpc
            - containerPort: 4318
              name: otlp-http
          volumeMounts:
            - name: config
              mountPath: /etc/otel
          resources:
            requests:
              cpu: 200m
              memory: 512Mi
            limits:
              cpu: 1000m
              memory: 2Gi
```

**OTEL Collector Configuration:**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: otel-collector-agent-config
  namespace: infrastructure
data:
  config.yaml: |
    receivers:
      otlp:
        protocols:
          grpc:
            endpoint: 0.0.0.0:4317
          http:
            endpoint: 0.0.0.0:4318
      
      prometheus:
        config:
          scrape_configs:
            - job_name: 'kubernetes-pods'
              kubernetes_sd_configs:
                - role: pod
              relabel_configs:
                - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
                  action: keep
                  regex: true
    
    processors:
      batch:
        timeout: 5s
        send_batch_size: 1000
      
      resource:
        attributes:
          - key: cluster
            value: ${CLUSTER_NAME}
            action: upsert
          - key: environment
            value: ${ENVIRONMENT}
            action: upsert
      
      memory_limiter:
        check_interval: 1s
        limit_mib: 400
        spike_limit_mib: 100
    
    exporters:
      otlp/tempo:
        endpoint: tempo.infrastructure.svc.cluster.local:4317
        tls:
          insecure: true
      
      prometheusremotewrite:
        endpoint: http://prometheus.infrastructure.svc.cluster.local:9090/api/v1/write
      
      loki:
        endpoint: http://loki.infrastructure.svc.cluster.local:3100/loki/api/v1/push
    
    service:
      pipelines:
        traces:
          receivers: [otlp]
          processors: [memory_limiter, batch, resource]
          exporters: [otlp/tempo]
        
        metrics:
          receivers: [otlp, prometheus]
          processors: [memory_limiter, batch, resource]
          exporters: [prometheusremotewrite]
        
        logs:
          receivers: [otlp]
          processors: [memory_limiter, batch, resource]
          exporters: [loki]
```

**Alternative: OpenTelemetry Operator:**

The OpenTelemetry Operator provides Kubernetes-native lifecycle management for Collectors. It supports auto-instrumentation injection and simplifies multi-instance deployments. Consider for environments requiring advanced instrumentation patterns.

| Deployment Method | Complexity | Auto-Instrumentation | Upgrade Path |
|-------------------|------------|---------------------|--------------|
| Helm (Current) | Low | Manual | Helm upgrade |
| OTel Operator | Medium | Automatic injection | CRD-based |

```yaml
# Alternative: OpenTelemetry Operator deployment
apiVersion: opentelemetry.io/v1alpha1
kind: OpenTelemetryCollector
metadata:
  name: otel-collector
  namespace: infrastructure
  labels:
    layer: l00
spec:
  mode: daemonset
  image: otel/opentelemetry-collector-contrib:0.91.0
  serviceAccount: otel-collector
  config: |
    receivers:
      otlp:
        protocols:
          grpc:
            endpoint: 0.0.0.0:4317
          http:
            endpoint: 0.0.0.0:4318
    processors:
      batch:
        timeout: 5s
      k8sattributes:
        extract:
          metadata:
            - k8s.pod.name
            - k8s.namespace.name
            - k8s.deployment.name
    exporters:
      prometheus:
        endpoint: "0.0.0.0:8889"
      otlp/tempo:
        endpoint: tempo.infrastructure.svc:4317
    service:
      pipelines:
        traces:
          receivers: [otlp]
          processors: [batch, k8sattributes]
          exporters: [otlp/tempo]
        metrics:
          receivers: [otlp]
          processors: [batch]
          exporters: [prometheus]
---
# Auto-instrumentation for Java applications
apiVersion: opentelemetry.io/v1alpha1
kind: Instrumentation
metadata:
  name: java-instrumentation
  namespace: data-layer
spec:
  exporter:
    endpoint: http://otel-collector.infrastructure.svc:4317
  propagators:
    - tracecontext
    - baggage
  java:
    image: ghcr.io/open-telemetry/opentelemetry-operator/autoinstrumentation-java:1.30.0
```

**OTel Operator Installation:**

```bash
# Install OTel Operator via Helm
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm install opentelemetry-operator open-telemetry/opentelemetry-operator \
  --namespace infrastructure \
  --set admissionWebhooks.certManager.enabled=true
```

#### 9.3.1 Infrastructure Metrics

| Metric | Type | Labels | Alert Threshold |
|--------|------|--------|-----------------|
| `kube_node_status_condition` | Gauge | node, condition | condition=Ready, status!=True |
| `kube_pod_container_status_restarts_total` | Counter | namespace, pod, container | > 5 in 1h |
| `node_cpu_seconds_total` | Counter | node, mode | > 80% utilization sustained |
| `node_memory_MemAvailable_bytes` | Gauge | node | < 20% available |
| `kubelet_volume_stats_used_bytes` | Gauge | namespace, pvc | > 80% capacity |
| `kube_pod_status_phase` | Gauge | namespace, pod, phase | phase=Pending > 5m |
| `kube_deployment_status_replicas_unavailable` | Gauge | namespace, deployment | > 0 for 5m |
| `DCGM_FI_DEV_GPU_UTIL` | Gauge | gpu, node, modelName | < 20% or > 90% sustained |
| `DCGM_FI_DEV_MEM_COPY_UTIL` | Gauge | gpu, node | > 90% sustained |

#### 9.3.2 Component Metrics

| Component | Key Metrics | Prometheus Job |
|-----------|-------------|----------------|
| Karpenter | `karpenter_nodes_created_total`, `karpenter_provisioner_scheduling_duration_seconds`, `karpenter_nodes_terminated_total` | karpenter |
| Cilium | `cilium_policy_verdict_total`, `cilium_drop_count_total`, `cilium_forward_count_total`, `cilium_endpoint_count` | cilium |
| ESO | `externalsecret_status_condition`, `externalsecret_sync_calls_total`, `externalsecret_reconcile_error_total` | external-secrets |
| cert-manager | `certmanager_certificate_ready_status`, `certmanager_certificate_expiration_timestamp_seconds` | cert-manager |
| ArgoCD | `argocd_app_info`, `argocd_app_sync_total`, `argocd_cluster_api_resource_objects` | argocd |
| Gatekeeper | `gatekeeper_violations`, `gatekeeper_constraint_templates`, `gatekeeper_audit_duration_seconds` | gatekeeper |

#### 9.3.3 ServiceMonitor Configuration

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: infrastructure-components
  namespace: infrastructure
  labels:
    prometheus: main
spec:
  selector:
    matchLabels:
      app.kubernetes.io/part-of: infrastructure
  namespaceSelector:
    matchNames:
      - infrastructure
      - kube-system
      - gatekeeper-system
      - cert-manager
  endpoints:
    - port: metrics
      interval: 30s
      path: /metrics
      relabelings:
        - sourceLabels: [__meta_kubernetes_pod_label_app]
          targetLabel: component
        - sourceLabels: [__meta_kubernetes_namespace]
          targetLabel: namespace
```

### 9.4 Logs

#### 9.4.1 Loki Deployment

Addresses Gap G-007:

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: loki
  namespace: infrastructure
  labels:
    app: loki
    layer: l00
spec:
  serviceName: loki
  replicas: 1
  selector:
    matchLabels:
      app: loki
  template:
    metadata:
      labels:
        app: loki
        layer: l00
    spec:
      containers:
        - name: loki
          image: grafana/loki:2.9.0
          args:
            - -config.file=/etc/loki/config.yaml
          ports:
            - containerPort: 3100
              name: http
          volumeMounts:
            - name: config
              mountPath: /etc/loki
            - name: data
              mountPath: /loki
          resources:
            requests:
              cpu: 200m
              memory: 512Mi
            limits:
              cpu: 1000m
              memory: 2Gi
      volumes:
        - name: config
          configMap:
            name: loki-config
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: ssd-standard
        resources:
          requests:
            storage: 100Gi
```

#### 9.4.2 Log Retention

| Log Type | Retention | Storage | Estimated Volume |
|----------|-----------|---------|------------------|
| Application logs | 30 days | S3/GCS (Loki) | 50GB/day |
| Kubernetes events | 7 days | S3/GCS (Loki) | 1GB/day |
| Audit logs | 90 days | S3/GCS (Loki) | 10GB/day |
| Infrastructure logs | 30 days | S3/GCS (Loki) | 5GB/day |
| Security events | 1 year | S3/GCS (separate bucket) | 2GB/day |

#### 9.4.3 Structured Logging Standard

All components emit logs in JSON format:

```json
{
  "timestamp": "2025-01-04T12:00:00.000Z",
  "level": "info",
  "message": "Request processed",
  "service": "api-gateway",
  "layer": "l09",
  "trace_id": "abc123def456",
  "span_id": "789ghi",
  "attributes": {
    "http.method": "POST",
    "http.status_code": 200,
    "http.path": "/v1/agents",
    "http.duration_ms": 45
  }
}
```

### 9.5 Traces

#### 9.5.1 Trace Sampling

| Environment | Sampling Rate | Strategy | Rationale |
|-------------|---------------|----------|-----------|
| Development | 100% | Always sample | Full visibility for debugging |
| Staging | 10% | Probabilistic | Balance visibility and cost |
| Production | 1% + tail-based | Error + latency sampling | Cost-effective; always capture errors |

**Tail-Based Sampling Configuration:**

```yaml
processors:
  tail_sampling:
    decision_wait: 10s
    num_traces: 100000
    expected_new_traces_per_sec: 1000
    policies:
      - name: errors
        type: status_code
        status_code: {status_codes: [ERROR]}
      - name: slow-traces
        type: latency
        latency: {threshold_ms: 1000}
      - name: probabilistic
        type: probabilistic
        probabilistic: {sampling_percentage: 1}
```

### 9.6 Alerting

#### 9.6.1 Alert Severity Levels

| Severity | Response Time | Notification | Example |
|----------|---------------|--------------|---------|
| Critical | Immediate (page) | PagerDuty | Cluster unreachable, data loss risk |
| High | 15 minutes | PagerDuty + Slack | Node pool exhausted, secrets sync failed |
| Medium | 1 hour | Slack #alerts | Certificate expiring in 7 days |
| Low | Next business day | Slack #alerts | High resource utilization trend |

#### 9.6.2 Infrastructure Alert Rules

Addresses Gap G-016:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: infrastructure-alerts
  namespace: infrastructure
  labels:
    prometheus: main
    layer: l00
spec:
  groups:
    - name: infrastructure.critical
      rules:
        - alert: ClusterNodeNotReady
          expr: |
            kube_node_status_condition{condition="Ready",status="true"} == 0
          for: 5m
          labels:
            severity: critical
            layer: l00
            error_code: E0001
          annotations:
            summary: "Node {{ $labels.node }} is not ready"
            description: "Node has been not ready for more than 5 minutes"
            runbook_url: "https://runbooks.example.com/E0001-node-not-ready"
        
        - alert: PersistentVolumeFillingUp
          expr: |
            (
              kubelet_volume_stats_available_bytes / kubelet_volume_stats_capacity_bytes < 0.15
              and
              predict_linear(kubelet_volume_stats_available_bytes[6h], 24*60*60) < 0
            )
          for: 1h
          labels:
            severity: critical
            layer: l00
            error_code: E0002
          annotations:
            summary: "PVC {{ $labels.persistentvolumeclaim }} will fill within 24h"
            runbook_url: "https://runbooks.example.com/E0002-pvc-filling"
        
        - alert: ControlPlaneComponentDown
          expr: |
            up{job=~"kube-apiserver|kube-controller-manager|kube-scheduler"} == 0
          for: 5m
          labels:
            severity: critical
            layer: l00
            error_code: E0003
          annotations:
            summary: "Control plane component {{ $labels.job }} is down"
            runbook_url: "https://runbooks.example.com/E0003-control-plane"
        
    - name: infrastructure.high
      rules:
        - alert: SecretSyncFailed
          expr: |
            externalsecret_status_condition{condition="Ready",status="False"} == 1
          for: 10m
          labels:
            severity: high
            layer: l00
            error_code: E0201
          annotations:
            summary: "ExternalSecret {{ $labels.name }} sync failed"
            runbook_url: "https://runbooks.example.com/E0201-secret-sync"
        
        - alert: CertificateExpiringSoon
          expr: |
            certmanager_certificate_expiration_timestamp_seconds - time() < 7*24*60*60
          for: 1h
          labels:
            severity: high
            layer: l00
            error_code: E0401
          annotations:
            summary: "Certificate {{ $labels.name }} expires in less than 7 days"
            runbook_url: "https://runbooks.example.com/E0401-cert-expiring"
        
        - alert: HighPodRestartRate
          expr: |
            increase(kube_pod_container_status_restarts_total[1h]) > 5
          for: 5m
          labels:
            severity: high
            layer: l00
            error_code: E0301
          annotations:
            summary: "Pod {{ $labels.namespace }}/{{ $labels.pod }} restarting frequently"
            runbook_url: "https://runbooks.example.com/E0301-pod-restart"
        
        - alert: GPUUtilizationLow
          expr: |
            avg_over_time(DCGM_FI_DEV_GPU_UTIL[30m]) < 20
          for: 1h
          labels:
            severity: high
            layer: l00
            error_code: E0303
          annotations:
            summary: "GPU {{ $labels.gpu }} on {{ $labels.node }} underutilized"
            runbook_url: "https://runbooks.example.com/E0303-gpu-underutilized"
        
    - name: infrastructure.medium
      rules:
        - alert: NodeMemoryPressure
          expr: |
            (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) > 0.8
          for: 15m
          labels:
            severity: medium
            layer: l00
            error_code: E0004
          annotations:
            summary: "Node {{ $labels.node }} memory pressure"
            runbook_url: "https://runbooks.example.com/E0004-memory-pressure"
        
        - alert: GatekeeperViolations
          expr: |
            increase(gatekeeper_violations[1h]) > 10
          for: 5m
          labels:
            severity: medium
            layer: l00
            error_code: E0501
          annotations:
            summary: "High rate of Gatekeeper policy violations"
            runbook_url: "https://runbooks.example.com/E0501-gatekeeper"
```

#### 9.6.3 Alertmanager Routing

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: alertmanager-config
  namespace: infrastructure
data:
  alertmanager.yml: |
    global:
      resolve_timeout: 5m
      slack_api_url: '${SLACK_WEBHOOK_URL}'
    
    route:
      group_by: ['alertname', 'layer', 'namespace']
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 4h
      receiver: 'slack-default'
      routes:
        - match:
            severity: critical
          receiver: 'pagerduty-critical'
          continue: true
        - match:
            severity: critical
          receiver: 'slack-critical'
        - match:
            severity: high
          receiver: 'pagerduty-high'
          continue: true
        - match:
            severity: high
          receiver: 'slack-alerts'
        - match:
            severity: medium
          receiver: 'slack-alerts'
        - match:
            severity: low
          receiver: 'slack-alerts'
    
    receivers:
      - name: 'slack-default'
        slack_configs:
          - channel: '#alerts-infrastructure'
            title: '{{ .GroupLabels.alertname }}'
            text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
      
      - name: 'slack-critical'
        slack_configs:
          - channel: '#alerts-critical'
            title: ':fire: CRITICAL: {{ .GroupLabels.alertname }}'
            text: '{{ range .Alerts }}{{ .Annotations.summary }}\nRunbook: {{ .Annotations.runbook_url }}{{ end }}'
      
      - name: 'slack-alerts'
        slack_configs:
          - channel: '#alerts-infrastructure'
            title: '{{ .GroupLabels.alertname }}'
            text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
      
      - name: 'pagerduty-critical'
        pagerduty_configs:
          - service_key: '${PAGERDUTY_SERVICE_KEY}'
            severity: critical
      
      - name: 'pagerduty-high'
        pagerduty_configs:
          - service_key: '${PAGERDUTY_SERVICE_KEY}'
            severity: warning
```

### 9.7 Dashboards

Addresses Gap G-017:

| Dashboard | Purpose | Key Panels |
|-----------|---------|------------|
| Cluster Overview | Overall health | Node status, resource utilization, pod count by namespace |
| Network Traffic | Traffic patterns | Request rate, error rate, latency percentiles by service |
| GPU Utilization | Inference capacity | GPU util %, memory usage, queue depth, MIG allocation |
| Cost Attribution | Spend tracking | Cost by namespace, layer, environment; trends; spot savings |
| Secrets & Certs | Security posture | Sync status, failed syncs, certificate expiration timeline |
| Scaling Events | Capacity changes | Karpenter provisions, HPA events, node churn |
| Gatekeeper | Policy compliance | Violations by constraint, admission latency, audit results |

### 9.8 Cost Tracking

```yaml
# OpenCost Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: opencost
  namespace: infrastructure
  labels:
    app: opencost
    layer: l00
spec:
  replicas: 1
  selector:
    matchLabels:
      app: opencost
  template:
    metadata:
      labels:
        app: opencost
        layer: l00
    spec:
      containers:
        - name: opencost
          image: ghcr.io/opencost/opencost:1.108.0
          env:
            - name: PROMETHEUS_SERVER_ENDPOINT
              value: "http://prometheus.infrastructure.svc.cluster.local:9090"
            - name: CLOUD_PROVIDER_API_KEY
              valueFrom:
                secretKeyRef:
                  name: opencost-credentials
                  key: api-key
          ports:
            - containerPort: 9003
              name: http
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 1Gi
```

**Cost Attribution Labels:**

| Label | Required | Values | Purpose |
|-------|----------|--------|---------|
| `cost-center` | Yes | Team identifier | Chargeback |
| `layer` | Yes | `l00`-`l11` | Layer attribution |
| `environment` | Yes | `production`, `staging`, `dev` | Environment breakdown |
| `workload-type` | No | `inference`, `batch`, `api`, `background` | Workload categorization |

**Namespace Budget Alerts:**

Budget alerts notify when namespace spend approaches defined limits. Budgets are defined via namespace labels and enforced via Prometheus alerting.

```yaml
# Define budget via namespace label
apiVersion: v1
kind: Namespace
metadata:
  name: data-layer
  labels:
    cost-budget: "5000"    # Monthly budget in USD
    cost-center: "platform-engineering"
    layer: l01
```

```yaml
# Prometheus alerting rules for cost budgets
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: cost-budget-alerts
  namespace: infrastructure
  labels:
    layer: l00
spec:
  groups:
    - name: cost.budgets
      interval: 1h
      rules:
        - alert: NamespaceCostApproachingBudget
          expr: |
            (
              sum by (namespace) (
                opencost_namespace_cpu_cost_hourly{} +
                opencost_namespace_memory_cost_hourly{} +
                opencost_namespace_gpu_cost_hourly{}
              ) * 24 * 30
            ) 
            / on(namespace) group_left()
            (
              kube_namespace_labels{label_cost_budget!=""} 
              * on(namespace) group_left(label_cost_budget)
              (label_replace(kube_namespace_labels, "budget", "$1", "label_cost_budget", "(.*)"))
            ) > 0.8
          for: 1h
          labels:
            severity: warning
          annotations:
            summary: "Namespace {{ $labels.namespace }} at {{ $value | humanizePercentage }} of monthly budget"
            runbook_url: "runbooks/cost-budget.md"
            
        - alert: NamespaceCostExceededBudget
          expr: |
            (
              sum by (namespace) (
                opencost_namespace_cpu_cost_hourly{} +
                opencost_namespace_memory_cost_hourly{}
              ) * 24 * 30
            ) 
            / on(namespace) group_left()
            (
              kube_namespace_labels{label_cost_budget!=""}
            ) > 1.0
          for: 1h
          labels:
            severity: high
          annotations:
            summary: "Namespace {{ $labels.namespace }} EXCEEDED monthly budget"
            
        - alert: SpotSavingsLow
          expr: |
            1 - (
              sum(karpenter_nodes_total{capacity_type="spot"}) 
              / sum(karpenter_nodes_total{})
            ) > 0.7
          for: 24h
          labels:
            severity: low
          annotations:
            summary: "Spot instance utilization below 30% - review Karpenter NodePool config"
```

**Cost Optimization Guidance:**

| Strategy | Implementation | Expected Savings |
|----------|----------------|------------------|
| Spot instances | Karpenter NodePool with spot-to-spot consolidation | 60-70% vs on-demand |
| Right-sizing | VPA recommendations with UpdateMode: Auto | 15-30% |
| Idle detection | OpenCost alerts on < 10% utilization | Variable |
| Reserved capacity | Savings Plans for baseline workloads | 30-40% vs on-demand |

**AWS Savings Plans Strategy:**

For baseline compute capacity (system nodes, core platform services), consider Compute Savings Plans to reduce costs while maintaining flexibility:

| Workload Type | Capacity Strategy | Commitment |
|---------------|-------------------|------------|
| System nodes | Savings Plan (3yr) | High baseline, predictable |
| Platform services (L00-L01) | Savings Plan (1yr) | Moderate baseline |
| Application workloads | Spot + On-Demand | No commitment |
| Burst capacity | Spot instances | No commitment |

---

## 10. Configuration

### 10.1 Configuration Hierarchy

```
CONFIGURATION SOURCES (Priority Order, Highest First)
=====================================================

1. Environment Variables (highest priority)
   |-- Injected by Kubernetes from ConfigMaps/Secrets
   |-- Runtime overrides
   
2. ConfigMaps (namespace-scoped)
   |-- Application configuration
   |-- Feature flags
   
3. Helm Values (deployment-time)
   |-- Component configuration
   |-- Resource limits
   |-- Replica counts
   
4. Terraform Variables (infrastructure-time)
   |-- Cluster configuration
   |-- Node pool definitions
   |-- Network topology
   
5. Default Values (lowest priority)
   |-- Compiled into container images
   |-- Helm chart defaults
```

### 10.2 Terraform Variables

#### 10.2.1 Cluster Configuration

```hcl
# terraform/environments/production/terraform.tfvars

# Cluster Identity
cluster_name           = "agentic-prod-us-west-2"
cluster_version        = "1.28"
region                 = "us-west-2"
dr_region              = "us-east-1"

# Network Configuration
vpc_cidr               = "10.0.0.0/16"
pod_cidr               = "10.1.0.0/16"
service_cidr           = "10.2.0.0/16"
enable_private_endpoint = true
enable_public_endpoint  = false

# Node Pools
node_pools = {
  system = {
    instance_types = ["m5.large"]
    min_size       = 3
    max_size       = 5
    capacity_type  = "ON_DEMAND"
    taints         = [{ key = "node-role", value = "system", effect = "NoSchedule" }]
    labels         = { "node-pool" = "system" }
  }
  
  general = {
    instance_types = ["m5.xlarge", "m5.2xlarge", "m5.4xlarge", "m6i.xlarge", "m6i.2xlarge"]
    min_size       = 2
    max_size       = 50
    capacity_type  = "ON_DEMAND"
    labels         = { "node-pool" = "general" }
  }
  
  gpu_inference = {
    instance_types = ["g5.xlarge", "g5.2xlarge", "g5.4xlarge"]
    min_size       = 0
    max_size       = 20
    capacity_type  = "ON_DEMAND"
    taints         = [{ key = "nvidia.com/gpu", value = "true", effect = "NoSchedule" }]
    labels         = { "node-pool" = "gpu-inference", "nvidia.com/mig.strategy" = "mixed" }
    gpu_config     = { enabled = true, type = "nvidia-a10g", mig_strategy = "mixed" }
  }
  
  spot_batch = {
    instance_types = ["m5.xlarge", "m5.2xlarge", "c5.xlarge", "c5.2xlarge", "r5.xlarge"]
    min_size       = 0
    max_size       = 100
    capacity_type  = "SPOT"
    taints         = [{ key = "lifecycle", value = "spot", effect = "NoSchedule" }]
    labels         = { "node-pool" = "spot-batch" }
  }
  
  high_memory = {
    instance_types = ["r5.2xlarge", "r5.4xlarge", "r6i.2xlarge"]
    min_size       = 0
    max_size       = 10
    capacity_type  = "ON_DEMAND"
    labels         = { "node-pool" = "high-memory" }
  }
}

# Observability
prometheus_retention_days = 15
loki_retention_days       = 30
tempo_retention_days      = 7
enable_tracing            = true
thanos_bucket             = "agentic-prod-thanos-us-west-2"
loki_bucket               = "agentic-prod-loki-us-west-2"

# Secrets
vault_address             = "https://vault.example.com"
vault_kubernetes_role     = "agentic-prod-cluster"

# Tags
common_tags = {
  Environment = "production"
  Project     = "agentic-ai-workforce"
  ManagedBy   = "terraform"
  CostCenter  = "platform-engineering"
}
```

#### 10.2.2 Variable Definitions

```hcl
# terraform/modules/cluster/variables.tf

variable "cluster_name" {
  type        = string
  description = "Name of the Kubernetes cluster"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,62}$", var.cluster_name))
    error_message = "Cluster name must be lowercase alphanumeric with hyphens, 3-63 characters."
  }
}

variable "cluster_version" {
  type        = string
  description = "Kubernetes version"
  default     = "1.28"
  validation {
    condition     = can(regex("^1\\.(2[8-9]|[3-9][0-9])$", var.cluster_version))
    error_message = "Kubernetes version must be 1.28 or higher."
  }
}

variable "region" {
  type        = string
  description = "Primary deployment region"
}

variable "dr_region" {
  type        = string
  description = "Disaster recovery region"
  default     = null
}

variable "node_pools" {
  type = map(object({
    instance_types = list(string)
    min_size       = number
    max_size       = number
    capacity_type  = optional(string, "ON_DEMAND")
    taints = optional(list(object({
      key    = string
      value  = string
      effect = string
    })), [])
    labels     = optional(map(string), {})
    gpu_config = optional(object({
      enabled      = bool
      type         = string
      mig_strategy = string
    }))
  }))
  description = "Node pool configurations"
  
  validation {
    condition     = alltrue([for k, v in var.node_pools : v.min_size <= v.max_size])
    error_message = "min_size must be less than or equal to max_size for all node pools."
  }
}

variable "vpc_cidr" {
  type        = string
  description = "VPC CIDR block"
  default     = "10.0.0.0/16"
  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "Must be a valid CIDR block."
  }
}
```

### 10.3 Helm Values

#### 10.3.1 Cilium Configuration

```yaml
# helm/infrastructure/cilium/values.yaml

cluster:
  name: {{ .Values.global.clusterName }}
  id: {{ .Values.global.clusterId }}

ipam:
  mode: kubernetes

kubeProxyReplacement: true
k8sServiceHost: {{ .Values.global.kubeAPIServer }}
k8sServicePort: 443

hubble:
  enabled: true
  relay:
    enabled: true
    replicas: 2
  ui:
    enabled: true
    replicas: 1
  metrics:
    enabled:
      - dns
      - drop
      - tcp
      - flow
      - port-distribution
      - icmp
      - httpV2:requestDuration

bpf:
  masquerade: true
  hostRouting: true

operator:
  replicas: 2
  podDisruptionBudget:
    enabled: true
    minAvailable: 1

resources:
  limits:
    cpu: 1000m
    memory: 1Gi
  requests:
    cpu: 100m
    memory: 512Mi

prometheus:
  enabled: true
  serviceMonitor:
    enabled: true
```

#### 10.3.2 External Secrets Operator Configuration

```yaml
# helm/infrastructure/external-secrets/values.yaml

replicaCount: 2

podDisruptionBudget:
  enabled: true
  minAvailable: 1

serviceAccount:
  create: true
  name: external-secrets
  annotations:
    eks.amazonaws.com/role-arn: {{ .Values.vault.iamRole }}

env:
  - name: VAULT_ADDR
    value: {{ .Values.vault.address }}

resources:
  limits:
    cpu: 500m
    memory: 256Mi
  requests:
    cpu: 50m
    memory: 128Mi

webhook:
  certManager:
    enabled: true
    cert:
      issuerRef:
        name: vault-pki
        kind: ClusterIssuer

metrics:
  service:
    enabled: true
  serviceMonitor:
    enabled: true
```

#### 10.3.3 ArgoCD Configuration

```yaml
# helm/infrastructure/argocd/values.yaml

global:
  domain: argocd.example.com

server:
  replicas: 2
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 5
  ingress:
    enabled: true
    ingressClassName: nginx
    annotations:
      cert-manager.io/cluster-issuer: letsencrypt-prod
    tls: true

controller:
  replicas: 2
  resources:
    requests:
      cpu: 250m
      memory: 256Mi
    limits:
      cpu: 1000m
      memory: 1Gi

applicationSet:
  enabled: true
  replicas: 2

# ArgoCD Notifications Controller
notifications:
  enabled: true
  argocdUrl: https://argocd.example.com
  
  secret:
    items:
      slack-token: $slack-token
      pagerduty-key: $pagerduty-key
  
  notifiers:
    service.slack: |
      token: $slack-token
      signingSecret: ""
    service.pagerduty: |
      serviceKeys:
        default: $pagerduty-key
  
  subscriptions:
    - recipients:
        - slack:alerts-deployments
      triggers:
        - on-deployed
        - on-health-degraded
        - on-sync-failed
    - recipients:
        - pagerduty:default
      triggers:
        - on-sync-failed
        - on-health-degraded
  
  templates:
    template.app-deployed: |
      message: |
        :white_check_mark: Application {{.app.metadata.name}} deployed successfully.
        Revision: {{.app.status.sync.revision}}
        Environment: {{.app.spec.destination.namespace}}
      slack:
        attachments: |
          [{
            "color": "#18be52",
            "fields": [
              {"title": "Application", "value": "{{.app.metadata.name}}", "short": true},
              {"title": "Namespace", "value": "{{.app.spec.destination.namespace}}", "short": true},
              {"title": "Revision", "value": "{{.app.status.sync.revision | trunc 7}}", "short": true}
            ]
          }]
    
    template.app-sync-failed: |
      message: |
        :x: Application {{.app.metadata.name}} sync failed.
        Error: {{.app.status.operationState.message}}
      slack:
        attachments: |
          [{
            "color": "#E96D76",
            "fields": [
              {"title": "Application", "value": "{{.app.metadata.name}}", "short": true},
              {"title": "Error", "value": "{{.app.status.operationState.message | trunc 100}}"}
            ]
          }]
      pagerduty:
        description: |
          ArgoCD sync failed for {{.app.metadata.name}}
        severity: critical
    
    template.app-health-degraded: |
      message: |
        :warning: Application {{.app.metadata.name}} health degraded.
        Status: {{.app.status.health.status}}
      slack:
        attachments: |
          [{
            "color": "#f4c030",
            "fields": [
              {"title": "Application", "value": "{{.app.metadata.name}}", "short": true},
              {"title": "Health", "value": "{{.app.status.health.status}}", "short": true}
            ]
          }]
  
  triggers:
    trigger.on-deployed: |
      - when: app.status.operationState.phase in ['Succeeded'] and app.status.health.status == 'Healthy'
        send: [app-deployed]
    trigger.on-health-degraded: |
      - when: app.status.health.status == 'Degraded'
        send: [app-health-degraded]
    trigger.on-sync-failed: |
      - when: app.status.operationState.phase in ['Error', 'Failed']
        send: [app-sync-failed]
```

**ArgoCD Notifications Routing:**

| Event | Recipients | Severity |
|-------|------------|----------|
| Sync succeeded | Slack #deployments | Info |
| Sync failed | Slack #alerts + PagerDuty | Critical |
| Health degraded | Slack #alerts | Warning |
| Out of sync > 1h | Slack #alerts | Warning |

### 10.4 Namespace Configuration

#### 10.4.1 Namespace Defaults

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: namespace-defaults
  namespace: infrastructure
data:
  resource-quota.yaml: |
    # Default quota for application namespaces
    cpu_requests: "20"
    cpu_limits: "40"
    memory_requests: "50Gi"
    memory_limits: "100Gi"
    gpu_requests: "4"
    pvc_count: "30"
    storage_requests: "500Gi"
  
  limit-range.yaml: |
    # Default limits for containers
    default_cpu: "500m"
    default_memory: "512Mi"
    default_request_cpu: "100m"
    default_request_memory: "128Mi"
    max_cpu: "8"
    max_memory: "32Gi"
  
  network-policy.yaml: |
    # Default network policy settings
    default_deny_ingress: true
    default_deny_egress: false
    allow_dns_egress: true
    allow_prometheus_scrape: true
```

#### 10.4.2 ResourceQuota Template

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: {{ namespace }}-quota
  namespace: {{ namespace }}
  labels:
    layer: {{ layer }}
spec:
  hard:
    requests.cpu: {{ cpu_requests }}
    limits.cpu: {{ cpu_limits }}
    requests.memory: {{ memory_requests }}
    limits.memory: {{ memory_limits }}
    requests.nvidia.com/gpu: {{ gpu_requests }}
    persistentvolumeclaims: {{ pvc_count }}
    requests.storage: {{ storage_requests }}
    pods: "100"
    services: "20"
    secrets: "50"
    configmaps: "50"
```

#### 10.4.3 LimitRange Template

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: {{ namespace }}-limits
  namespace: {{ namespace }}
  labels:
    layer: {{ layer }}
spec:
  limits:
    - type: Container
      default:
        cpu: {{ default_cpu }}
        memory: {{ default_memory }}
      defaultRequest:
        cpu: {{ default_request_cpu }}
        memory: {{ default_request_memory }}
      max:
        cpu: {{ max_cpu }}
        memory: {{ max_memory }}
    - type: PersistentVolumeClaim
      max:
        storage: 100Gi
      min:
        storage: 1Gi
```

### 10.5 Feature Flags

| Flag | Default | Description | Controlled By |
|------|---------|-------------|---------------|
| `ENABLE_GPU_MIG` | `true` | Enable MIG partitioning on GPU nodes | Terraform |
| `ENABLE_SPOT_NODES` | `true` | Allow spot instances for batch workloads | Terraform |
| `ENABLE_HUBBLE` | `true` | Enable Cilium Hubble observability | Helm |
| `ENABLE_COST_TRACKING` | `true` | Deploy OpenCost for cost attribution | Helm |
| `STRICT_NETWORK_POLICY` | `false` | Default deny egress (stricter mode) | ConfigMap |
| `AUTO_CERTIFICATE_RENEWAL` | `true` | cert-manager automatic renewal | Helm |
| `ENABLE_GVISOR` | `false` | Enable gVisor runtime for agent sandboxing | Terraform |
| `ENABLE_MULTI_REGION` | `false` | Deploy secondary region standby | Terraform |

### 10.6 Environment-Specific Overrides

| Configuration | Development | Staging | Production |
|---------------|-------------|---------|------------|
| Node pool min sizes | 1 | 2 | 3 |
| Prometheus retention | 3d | 7d | 15d |
| Log retention | 7d | 14d | 30d |
| Spot instances | All workloads | General + batch | Batch only |
| GPU MIG | Disabled | Single profile | Mixed profiles |
| TLS issuer | Self-signed | Let's Encrypt staging | Let's Encrypt prod |
| Network policy | Permissive | Baseline | Strict |
| Resource quotas | Relaxed (2x) | Standard | Enforced |
| Replica counts | 1 | 2 | 3+ |
| PDB enabled | No | Yes | Yes |

### 10.7 Configuration Validation

#### 10.7.1 OPA Constraint for Required Labels

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: require-cost-labels
spec:
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Namespace"]
      - apiGroups: ["apps"]
        kinds: ["Deployment", "StatefulSet", "DaemonSet"]
    excludedNamespaces:
      - kube-system
      - kube-public
      - gatekeeper-system
  parameters:
    labels:
      - key: cost-center
      - key: layer
      - key: environment
```

#### 10.7.2 Terraform Validation

```hcl
# Pre-apply validation
resource "null_resource" "validate_config" {
  triggers = {
    always_run = timestamp()
  }

  provisioner "local-exec" {
    command = <<-EOT
      # Validate node pool configuration
      if [ ${var.node_pools.system.min_size} -lt 3 ]; then
        echo "ERROR: System node pool must have at least 3 nodes"
        exit 1
      fi
      
      # Validate CIDR ranges don't overlap
      # ... additional validation
    EOT
  }
}
```

### 10.8 GitOps Configuration Management

ArgoCD manages all infrastructure configuration through GitOps:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: infrastructure-components
  namespace: argocd
spec:
  generators:
    - list:
        elements:
          - name: cilium
            namespace: kube-system
            path: helm/infrastructure/cilium
          - name: external-secrets
            namespace: infrastructure
            path: helm/infrastructure/external-secrets
          - name: cert-manager
            namespace: cert-manager
            path: helm/infrastructure/cert-manager
          - name: prometheus
            namespace: infrastructure
            path: helm/infrastructure/prometheus
          - name: loki
            namespace: infrastructure
            path: helm/infrastructure/loki
          - name: gatekeeper
            namespace: gatekeeper-system
            path: helm/infrastructure/gatekeeper
  template:
    metadata:
      name: '{{name}}'
    spec:
      project: infrastructure
      source:
        repoURL: https://github.com/example/infrastructure.git
        targetRevision: main
        path: '{{path}}'
        helm:
          valueFiles:
            - values.yaml
            - values-{{ .Values.environment }}.yaml
      destination:
        server: https://kubernetes.default.svc
        namespace: '{{namespace}}'
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
          - CreateNamespace=true
```

---

## 11. Implementation Guide

### 11.1 Implementation Phases

The Infrastructure Layer deploys in six sequential phases. Each phase builds upon the previous and produces specific, testable artifacts. Total deployment timeline: 8-10 weeks for production readiness.

| Phase | Name | Duration | Deliverables | Dependencies | Exit Criteria |
|-------|------|----------|--------------|--------------|---------------|
| 0 | Foundation | 2 weeks | Terraform modules, VPC, IAM, S3 buckets | Cloud account, Vault namespace | VPC pingable, IAM roles created |
| 1 | Core Cluster | 2 weeks | EKS/GKE cluster, system node pool, GPU drivers | Phase 0 | kubectl connects, nodes Ready |
| 2 | Networking | 1 week | Cilium CNI, NGINX Ingress, External DNS | Phase 1 | Hubble flows visible, DNS resolves |
| 3 | Security | 1 week | Vault integration, ESO, cert-manager, RBAC | Phase 2 | Secrets sync, certs issue |
| 4 | Observability | 1 week | Prometheus, Loki, Grafana, Alertmanager | Phase 2 | Metrics scraped, logs queryable |
| 5 | GitOps | 1 week | ArgoCD, ApplicationSets, App of Apps | Phase 3, 4 | Sync healthy, drift detected |
| 6 | Validation | 1 week | Load tests, chaos tests, DR drills | Phase 5 | All tests pass, runbooks verified |

### 11.2 Implementation Dependency Graph

```
IMPLEMENTATION DEPENDENCY GRAPH
================================

Phase 0: Foundation
+------------------------------------------+
|  VPC/Network | IAM Roles | S3 Buckets    |
|  KMS Keys    | Vault Namespace           |
+---------------------+--------------------+
                      |
                      v
Phase 1: Core Cluster
+------------------------------------------+
|  EKS/GKE Cluster | Control Plane         |
|  System Node Pool | GPU Drivers          |
|  Storage Classes  | CSI Drivers          |
+---------------------+--------------------+
                      |
         +------------+------------+
         |                         |
         v                         v
Phase 2: Networking           Phase 3: Security
+------------------+          +------------------+
| Cilium CNI       |          | External Secrets |
| NGINX Ingress    |          | cert-manager     |
| External DNS     |          | Gatekeeper       |
| Network Policies |          | RBAC Policies    |
+--------+---------+          +--------+---------+
         |                             |
         +-------------+---------------+
                       |
                       v
Phase 4: Observability
+------------------------------------------+
|  Prometheus | Loki | Grafana             |
|  Alertmanager | OpenCost | DCGM Exporter |
+---------------------+--------------------+
                      |
                      v
Phase 5: GitOps
+------------------------------------------+
|  ArgoCD | ApplicationSets | App of Apps  |
|  Image Updater | Notifications          |
+---------------------+--------------------+
                      |
                      v
Phase 6: Validation
+------------------------------------------+
|  Load Tests | Chaos Tests | DR Drills    |
|  Security Scans | Runbook Verification  |
+------------------------------------------+
```

### 11.3 Component Implementation Details

#### 11.3.1 Cluster Manager

**Terraform Module Structure:**

```
terraform/
+-- modules/
|   +-- cluster/
|   |   +-- main.tf           # EKS/GKE resource definitions
|   |   +-- variables.tf      # Input variables
|   |   +-- outputs.tf        # Cluster endpoint, CA, token
|   |   +-- node_pools.tf     # Node group definitions
|   |   +-- iam.tf            # IRSA/Workload Identity
|   |   +-- addons.tf         # CoreDNS, kube-proxy, VPC-CNI
|   +-- vpc/
|   |   +-- main.tf           # VPC, subnets, NAT gateways
|   |   +-- endpoints.tf      # VPC endpoints for AWS services
|   +-- storage/
|       +-- main.tf           # S3 buckets, EBS settings
|       +-- kms.tf            # Encryption keys
+-- environments/
    +-- production/
    |   +-- main.tf
    |   +-- terraform.tfvars
    +-- staging/
    +-- development/
```

**Implementation Steps:**

1. Create VPC with public/private subnets across 3 AZs (see Section 3.3.1)
2. Deploy managed Kubernetes with private API endpoint
3. Configure node pools per Section 3.4 specification
4. Install NVIDIA device plugin and GPU operator for GPU nodes
5. Create StorageClasses per Section 5.4 specification
6. Enable IRSA/Workload Identity for pod-level IAM

**Validation Criteria:**

| Check | Command | Expected Result |
|-------|---------|-----------------|
| Cluster access | `kubectl get nodes` | All nodes in Ready state |
| GPU availability | `kubectl describe nodes \| grep nvidia.com/gpu` | GPU resources visible |
| Storage provisioning | `kubectl apply -f test-pvc.yaml` | PVC bound within 60s |
| DNS resolution | `kubectl run test --image=busybox -- nslookup kubernetes` | Resolves successfully |

#### 11.3.2 Network Controller

**Helm Installation Order:**

| Order | Component | Chart | Namespace | Wait Condition |
|-------|-----------|-------|-----------|----------------|
| 1 | Cilium | cilium/cilium | kube-system | All agents Running |
| 2 | Hubble | (part of Cilium) | kube-system | Relay Ready |
| 3 | NGINX Ingress | ingress-nginx/ingress-nginx | ingress | LoadBalancer IP assigned |
| 4 | External DNS | external-dns/external-dns | infrastructure | Deployment Ready |

**Implementation Steps:**

1. Install Cilium with `kubeProxyReplacement=true` (replaces kube-proxy)
2. Enable Hubble for network observability with UI
3. Deploy NGINX Ingress Controller with NLB backend (AWS) or L4 LB (GCP)
4. Configure External DNS with Route53/Cloud DNS credentials
5. Apply default NetworkPolicies to all namespaces (deny ingress by default)
6. Deploy CiliumNetworkPolicy for L3/L4/L7 rules

**Validation Criteria:**

| Check | Command | Expected Result |
|-------|---------|-----------------|
| Cilium health | `cilium status` | All components healthy |
| Hubble flows | `hubble observe -f` | Traffic flows visible |
| Ingress LB | `kubectl get svc -n ingress` | External IP assigned |
| DNS records | `dig test.example.com` | A record resolves |

#### 11.3.3 Secrets Operator

**Prerequisites:**

- Vault cluster deployed and accessible from Kubernetes
- Kubernetes auth method enabled in Vault
- Service account token reviewer delegated to Vault

**Implementation Steps:**

1. Deploy External Secrets Operator via Helm
2. Create ClusterSecretStore pointing to Vault backend
3. Configure Vault Kubernetes auth role with bound service accounts
4. Create test ExternalSecret to validate synchronization
5. Deploy Reloader for automatic pod restarts on secret changes
6. Configure SecretStore per namespace for layer isolation

**Validation Criteria:**

| Check | Command | Expected Result |
|-------|---------|-----------------|
| ClusterSecretStore | `kubectl get css vault-backend -o jsonpath='{.status.conditions[0].status}'` | True |
| Secret sync | `kubectl get externalsecret test -o jsonpath='{.status.conditions[0].status}'` | True |
| K8s Secret exists | `kubectl get secret test-secret` | Secret exists with data |
| Rotation trigger | Update Vault secret, check pod restart | Pod restarts within 60s |

#### 11.3.4 Resource Scaler

**Components:**

| Component | Purpose | Installation |
|-----------|---------|--------------|
| Karpenter | Node autoscaling (just-in-time provisioning) | Helm |
| Metrics Server | HPA prerequisite (pod metrics) | Helm |
| VPA | Vertical pod autoscaling (recommendations) | Helm |
| KEDA | Event-driven scaling (queue-based) | Helm |

**Implementation Steps:**

1. Deploy Karpenter with IAM role for EC2/Compute provisioning
2. Create NodePool CRDs per node pool strategy (Section 3.4)
3. Install Metrics Server for HPA resource metrics
4. Deploy VPA in recommendation mode (UpdateMode: "Off") initially
5. Install KEDA for queue-based agent scaling
6. Configure PodDisruptionBudgets for critical workloads

**Validation Criteria:**

| Check | Command | Expected Result |
|-------|---------|-----------------|
| Karpenter provisioning | Create pending pod, wait | Node provisioned < 3 min |
| Node consolidation | Delete pods, wait | Empty node removed < 5 min |
| HPA scaling | Apply load, check replicas | Replicas increase with CPU |
| VPA recommendations | `kubectl describe vpa test` | Recommendations present |

#### 11.3.5 Certificate Manager

**Implementation Steps:**

1. Deploy cert-manager via Helm with CRDs
2. Create ClusterIssuer for Let's Encrypt staging (test first)
3. Create ClusterIssuer for Vault PKI (internal certificates)
4. Test certificate issuance with staging issuer
5. Switch to production Let's Encrypt issuer after validation
6. Configure Certificate resources for infrastructure services

**Validation Criteria:**

| Check | Command | Expected Result |
|-------|---------|-----------------|
| ClusterIssuer ready | `kubectl get clusterissuer -o wide` | Ready=True |
| Certificate issued | `kubectl get certificate test-cert -o wide` | Ready=True |
| Secret created | `kubectl get secret test-cert-tls` | TLS secret exists |
| Auto-renewal | Check cert-manager logs | Renewal scheduled |

#### 11.3.6 Observability Stack

**Deployment Order:**

| Order | Component | Purpose | Storage Backend |
|-------|-----------|---------|-----------------|
| 1 | Prometheus Operator | CRD management | - |
| 2 | Prometheus | Metrics collection | PVC (ssd-standard) |
| 3 | Alertmanager | Alert routing | PVC (ssd-standard) |
| 4 | Grafana | Visualization | PVC (ssd-standard) |
| 5 | Loki | Log aggregation | S3/GCS |
| 6 | Promtail | Log shipping | - |
| 7 | Tempo (optional) | Trace storage | S3/GCS |
| 8 | OpenCost | Cost tracking | - |
| 9 | DCGM Exporter | GPU metrics | - |

**Implementation Steps:**

1. Deploy kube-prometheus-stack Helm chart (includes Prometheus, Alertmanager, Grafana)
2. Configure ServiceMonitors for infrastructure components
3. Deploy Loki with S3/GCS backend for log storage
4. Deploy Promtail DaemonSet for log collection
5. Import infrastructure Grafana dashboards (see Section 9.5)
6. Configure Alertmanager routes for PagerDuty/Slack
7. Deploy OpenCost with cloud provider pricing integration
8. Deploy DCGM Exporter on GPU nodes

**Validation Criteria:**

| Check | Command | Expected Result |
|-------|---------|-----------------|
| Prometheus targets | Query `/api/v1/targets` | All targets healthy |
| Grafana dashboards | Access UI | Dashboards display data |
| Loki logs | `logcli query '{app="nginx"}'` | Logs returned |
| Alertmanager | Trigger test alert | Alert routed correctly |

### 11.4 Code Examples

#### 11.4.1 Terraform: EKS Cluster Module

```hcl
# modules/cluster/main.tf

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version

  vpc_id     = var.vpc_id
  subnet_ids = var.private_subnet_ids

  # Private cluster endpoint
  cluster_endpoint_public_access  = false
  cluster_endpoint_private_access = true

  # Enable IRSA for pod-level IAM
  enable_irsa = true

  # Cluster addons
  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent              = true
      before_compute           = true
      service_account_role_arn = module.vpc_cni_irsa.iam_role_arn
      configuration_values = jsonencode({
        env = {
          ENABLE_PREFIX_DELEGATION = "true"
          WARM_PREFIX_TARGET       = "1"
        }
      })
    }
  }

  # System node group (always-on, HA)
  eks_managed_node_groups = {
    system = {
      name           = "system"
      instance_types = ["m5.large"]
      min_size       = 3
      max_size       = 3
      desired_size   = 3

      labels = {
        "node-pool"   = "system"
        "layer"       = "l00"
        "cost-center" = "infrastructure"
      }

      taints = [{
        key    = "node-role"
        value  = "system"
        effect = "NO_SCHEDULE"
      }]
    }
  }

  # Karpenter manages general, GPU, high-memory, spot pools
  
  tags = merge(var.common_tags, {
    "karpenter.sh/discovery" = var.cluster_name
  })
}

# IRSA for VPC CNI
module "vpc_cni_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.0"

  role_name             = "${var.cluster_name}-vpc-cni"
  attach_vpc_cni_policy = true
  vpc_cni_enable_ipv4   = true

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:aws-node"]
    }
  }
}
```

#### 11.4.2 Karpenter NodePool Configuration

```yaml
# manifests/karpenter/nodepool-general.yaml
apiVersion: karpenter.sh/v1beta1
kind: NodePool
metadata:
  name: general
  labels:
    layer: l00
spec:
  template:
    metadata:
      labels:
        node-pool: general
        layer: l00
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: 
            - m5.xlarge
            - m5.2xlarge
            - m5.4xlarge
            - m6i.xlarge
            - m6i.2xlarge
      nodeClassRef:
        name: default
  limits:
    cpu: 1000
    memory: 2000Gi
  disruption:
    consolidationPolicy: WhenUnderutilized
    consolidateAfter: 30s
    budgets:
      - nodes: "10%"

---
# manifests/karpenter/nodepool-gpu.yaml
apiVersion: karpenter.sh/v1beta1
kind: NodePool
metadata:
  name: gpu-inference
  labels:
    layer: l00
spec:
  template:
    metadata:
      labels:
        node-pool: gpu-inference
        layer: l00
        nvidia.com/mig.strategy: mixed
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values:
            - g5.xlarge
            - g5.2xlarge
            - g5.4xlarge
            - p4d.24xlarge
      taints:
        - key: nvidia.com/gpu
          value: "true"
          effect: NoSchedule
      nodeClassRef:
        name: gpu
  limits:
    nvidia.com/gpu: 40
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 5m  # GPUs are expensive, remove quickly when unused
    budgets:
      - nodes: "0"  # Never consolidate occupied GPU nodes
```

#### 11.4.3 ArgoCD App of Apps Pattern

```yaml
# manifests/argocd/infrastructure-root.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: infrastructure
  namespace: argocd
  labels:
    layer: l00
spec:
  project: infrastructure
  source:
    repoURL: https://github.com/org/agentic-infrastructure.git
    targetRevision: main
    path: manifests/apps
  destination:
    server: https://kubernetes.default.svc
    namespace: argocd
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m

---
# manifests/apps/cilium.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: cilium
  namespace: argocd
  labels:
    layer: l00
    component: network-controller
spec:
  project: infrastructure
  source:
    repoURL: https://helm.cilium.io/
    chart: cilium
    targetRevision: 1.14.x
    helm:
      releaseName: cilium
      valueFiles:
        - $values/helm/infrastructure/cilium/values.yaml
        - $values/helm/infrastructure/cilium/values-production.yaml
  sources:
    - repoURL: https://helm.cilium.io/
      chart: cilium
      targetRevision: 1.14.x
      helm:
        valueFiles:
          - $values/helm/infrastructure/cilium/values.yaml
    - repoURL: https://github.com/org/agentic-infrastructure.git
      targetRevision: main
      ref: values
  destination:
    server: https://kubernetes.default.svc
    namespace: kube-system
  syncPolicy:
    automated:
      prune: false  # CNI requires careful pruning
      selfHeal: true
    syncOptions:
      - ServerSideApply=true
```

#### 11.4.4 External Secrets Operator ClusterSecretStore

```yaml
# manifests/external-secrets/clustersecretstore-vault.yaml
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: vault-backend
  labels:
    layer: l00
spec:
  provider:
    vault:
      server: "https://vault.infrastructure.svc:8200"
      path: "secret"
      version: "v2"
      auth:
        kubernetes:
          mountPath: "kubernetes"
          role: "external-secrets"
          serviceAccountRef:
            name: external-secrets
            namespace: infrastructure
      caProvider:
        type: ConfigMap
        name: vault-ca
        namespace: infrastructure
        key: ca.crt

---
# manifests/external-secrets/example-external-secret.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: data-layer-credentials
  namespace: data-layer
  labels:
    layer: l01
spec:
  refreshInterval: 1h
  secretStoreRef:
    kind: ClusterSecretStore
    name: vault-backend
  target:
    name: data-layer-credentials
    creationPolicy: Owner
  data:
    - secretKey: database-password
      remoteRef:
        key: secret/data/data-layer/database
        property: password
    - secretKey: encryption-key
      remoteRef:
        key: secret/data/data-layer/encryption
        property: kek
```

### 11.5 Error Codes

Infrastructure Layer allocates error codes in the E00XX-E05XX range per Section 5.2.2 of Part 1.

| Code | Name | Category | Description | Resolution |
|------|------|----------|-------------|------------|
| E0001 | CLUSTER_UNREACHABLE | Cluster | Cannot connect to Kubernetes API server | Check VPN connectivity, verify kubeconfig, validate IAM permissions |
| E0002 | NODE_PROVISION_FAILED | Cluster | Karpenter failed to provision requested node | Check EC2/Compute quotas, IAM permissions, subnet capacity |
| E0003 | GPU_DRIVER_MISSING | Cluster | NVIDIA driver not loaded on GPU node | Reinstall GPU operator, verify AMI includes drivers |
| E0004 | STORAGE_PROVISION_FAILED | Cluster | PVC stuck in Pending state | Check StorageClass exists, CSI driver healthy, quota available |
| E0005 | ADDON_INSTALL_FAILED | Cluster | Cluster addon (CoreDNS, VPC-CNI) failed | Check addon logs, verify IRSA role, review addon version |
| E0101 | NETWORK_POLICY_DENIED | Network | Traffic blocked by NetworkPolicy | Review policy with Hubble, check label selectors |
| E0102 | INGRESS_UNHEALTHY | Network | Ingress controller not serving traffic | Check LB health checks, backend pod health, TLS configuration |
| E0103 | DNS_RESOLUTION_FAILED | Network | ExternalDNS not creating records | Check DNS provider credentials, hosted zone permissions |
| E0104 | SERVICE_MESH_DEGRADED | Network | Cilium agents not all healthy | Check Cilium status, kernel version compatibility, CNI conflicts |
| E0201 | SECRET_SYNC_FAILED | Secrets | ExternalSecret not Ready | Check Vault connectivity, auth configuration, secret path |
| E0202 | VAULT_AUTH_FAILED | Secrets | Kubernetes auth to Vault rejected | Verify service account, role binding, Vault policy |
| E0203 | SECRET_ROTATION_STALE | Secrets | Secret not updated after Vault rotation | Check refreshInterval, Reloader annotations, pod restart policy |
| E0207 | VAULT_TOKEN_RENEWAL_FAILED | Secrets | Vault token renewal failed before TTL | Check Vault lease duration, ESO renewal settings, network to Vault |
| E0301 | AUTOSCALER_STUCK | Scaling | Nodes not scaling despite pending pods | Check Karpenter logs, NodePool limits, disruption budgets |
| E0302 | HPA_METRICS_UNAVAILABLE | Scaling | HPA cannot fetch metrics | Verify Metrics Server running, ServiceMonitor configured |
| E0303 | GPU_SCHEDULING_FAILED | Scaling | GPU pod pending due to resource unavailable | Check MIG profiles, GPU quotas, node taints/tolerations |
| E0401 | CERT_ISSUANCE_FAILED | Certificates | Certificate stuck in pending | Check ClusterIssuer, DNS challenge records, rate limits |
| E0402 | CERT_EXPIRED | Certificates | Certificate not renewed before expiry | Review cert-manager logs, check renewal window configuration |
| E0501 | METRICS_SCRAPE_FAILED | Observability | Prometheus target unhealthy | Check ServiceMonitor, network policy, endpoint connectivity |
| E0502 | ALERTMANAGER_UNREACHABLE | Observability | Alerts not routing | Verify Alertmanager pods, check config secret, test receivers |
| E0503 | LOGS_NOT_SHIPPING | Observability | Logs missing from Loki | Check Promtail DaemonSet, verify log path mounts, Loki connectivity |

---

## 12. Testing Strategy

### 12.1 Test Categories

| Category | Purpose | Tools | Frequency | Owner |
|----------|---------|-------|-----------|-------|
| Unit | Terraform module validation, Helm chart linting | `terraform validate`, `tflint`, `helm lint` | Every commit | Developer |
| Integration | Component interaction, API contracts | `pytest`, `kubectl`, `kuttl` | Every PR | CI Pipeline |
| Contract | Interface compliance with Data Layer | JSON Schema validation, OpenAPI tests | Every PR | CI Pipeline |
| Performance | Scaling behavior, throughput limits | `k6`, `locust`, `kube-burner` | Weekly | Platform Team |
| Chaos | Failure resilience, recovery validation | Chaos Mesh, Litmus | Weekly | SRE Team |
| Security | Vulnerability scanning, compliance | `trivy`, `kube-bench`, `kubeaudit` | Daily | Security Team |
| DR | Recovery procedures, failover validation | Manual runbook execution | Monthly | SRE Team |

### 12.2 Unit Tests

#### 12.2.1 Terraform Validation

```hcl
# tests/cluster_test.go (using Terratest)

package test

import (
    "testing"
    "github.com/gruntwork-io/terratest/modules/terraform"
    "github.com/stretchr/testify/assert"
)

func TestClusterModule(t *testing.T) {
    t.Parallel()

    terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
        TerraformDir: "../modules/cluster",
        Vars: map[string]interface{}{
            "cluster_name":       "test-cluster",
            "cluster_version":    "1.28",
            "vpc_id":             "vpc-test123",
            "private_subnet_ids": []string{"subnet-a", "subnet-b", "subnet-c"},
        },
        NoColor: true,
    })

    // Plan only - don't actually create resources in unit test
    terraform.InitAndPlan(t, terraformOptions)

    // Validate plan output
    plan := terraform.InitAndPlanAndShowWithStruct(t, terraformOptions)
    
    // Assert expected resources exist in plan
    assert.NotNil(t, plan.ResourceChangesMap["module.eks.aws_eks_cluster.this[0]"])
    
    // Assert critical configuration
    clusterChange := plan.ResourceChangesMap["module.eks.aws_eks_cluster.this[0]"]
    after := clusterChange.Change.After.(map[string]interface{})
    assert.Equal(t, "test-cluster", after["name"])
    assert.Equal(t, "1.28", after["version"])
}

func TestVPCModule(t *testing.T) {
    t.Parallel()

    terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
        TerraformDir: "../modules/vpc",
        Vars: map[string]interface{}{
            "vpc_cidr":     "10.0.0.0/16",
            "environment":  "test",
            "cluster_name": "test-cluster",
        },
    })

    terraform.InitAndPlan(t, terraformOptions)
    
    // Validate CIDR allocation
    plan := terraform.InitAndPlanAndShowWithStruct(t, terraformOptions)
    vpcChange := plan.ResourceChangesMap["aws_vpc.main"]
    after := vpcChange.Change.After.(map[string]interface{})
    assert.Equal(t, "10.0.0.0/16", after["cidr_block"])
}
```

#### 12.2.2 Helm Chart Validation

```bash
#!/bin/bash
# scripts/validate-charts.sh

set -euo pipefail

CHARTS_DIR="helm/infrastructure"
SCHEMA_DIR="schemas"

echo "=== Helm Chart Validation ==="

for chart in "$CHARTS_DIR"/*/; do
    chart_name=$(basename "$chart")
    echo "Validating $chart_name..."
    
    # Step 1: Lint chart structure
    helm lint "$chart" --strict
    
    # Step 2: Template with test values
    helm template test "$chart" \
        -f "$chart/values.yaml" \
        -f "$chart/values-test.yaml" \
        > /tmp/rendered.yaml
    
    # Step 3: Validate against Kubernetes schemas
    kubeconform \
        -strict \
        -summary \
        -kubernetes-version 1.28.0 \
        /tmp/rendered.yaml
    
    # Step 4: Policy validation with OPA
    conftest test /tmp/rendered.yaml \
        --policy policy/kubernetes/ \
        --all-namespaces
    
    echo "$chart_name: PASSED"
done

echo "=== All charts validated successfully ==="
```

### 12.3 Integration Tests

#### 12.3.1 Component Health Tests

```python
# tests/integration/test_cluster_health.py

import pytest
from kubernetes import client, config
import subprocess
import json
import time

config.load_kube_config()
v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()
custom_api = client.CustomObjectsApi()


class TestClusterHealth:
    """Validate core Kubernetes cluster health."""
    
    def test_all_nodes_ready(self):
        """All cluster nodes must be in Ready state."""
        nodes = v1.list_node()
        assert len(nodes.items) > 0, "No nodes found in cluster"
        
        for node in nodes.items:
            conditions = {c.type: c.status for c in node.status.conditions}
            assert conditions.get("Ready") == "True", \
                f"Node {node.metadata.name} not ready: {conditions}"

    def test_system_pods_running(self):
        """All kube-system pods must be Running."""
        pods = v1.list_namespaced_pod("kube-system")
        
        for pod in pods.items:
            # Skip completed jobs
            if pod.status.phase == "Succeeded":
                continue
            assert pod.status.phase == "Running", \
                f"Pod {pod.metadata.name} in {pod.status.phase} state"

    def test_gpu_nodes_available(self):
        """GPU nodes must advertise nvidia.com/gpu resource."""
        nodes = v1.list_node(label_selector="node-pool=gpu-inference")
        
        # Skip if no GPU nodes (dev environment)
        if len(nodes.items) == 0:
            pytest.skip("No GPU nodes in cluster")
        
        for node in nodes.items:
            allocatable = node.status.allocatable
            assert "nvidia.com/gpu" in allocatable, \
                f"Node {node.metadata.name} missing GPU resource"


class TestCiliumHealth:
    """Validate Cilium CNI and service mesh."""
    
    def test_cilium_agents_ready(self):
        """All Cilium agents must be ready."""
        ds = apps_v1.read_namespaced_daemon_set("cilium", "kube-system")
        assert ds.status.number_ready == ds.status.desired_number_scheduled, \
            f"Cilium agents not ready: {ds.status.number_ready}/{ds.status.desired_number_scheduled}"

    def test_cilium_connectivity(self):
        """Cilium connectivity test must pass."""
        result = subprocess.run(
            ["cilium", "connectivity", "test", "--single-node", "--test", "pod-to-pod"],
            capture_output=True,
            text=True,
            timeout=300
        )
        assert result.returncode == 0, f"Connectivity test failed: {result.stderr}"

    def test_hubble_relay_running(self):
        """Hubble relay must be running for observability."""
        deploy = apps_v1.read_namespaced_deployment("hubble-relay", "kube-system")
        assert deploy.status.ready_replicas == deploy.spec.replicas, \
            "Hubble relay not fully ready"


class TestSecretsIntegration:
    """Validate External Secrets Operator integration with Vault."""
    
    def test_clustersecretstore_ready(self):
        """ClusterSecretStore must be Ready."""
        css = custom_api.get_cluster_custom_object(
            "external-secrets.io", "v1beta1",
            "clustersecretstores", "vault-backend"
        )
        conditions = {c["type"]: c["status"] for c in css["status"]["conditions"]}
        assert conditions.get("Ready") == "True", \
            f"ClusterSecretStore not ready: {conditions}"

    def test_secret_sync(self):
        """ExternalSecret must sync from Vault."""
        # Create test ExternalSecret
        subprocess.run([
            "kubectl", "apply", "-f", "tests/fixtures/test-external-secret.yaml"
        ], check=True)
        
        # Wait for sync
        subprocess.run([
            "kubectl", "wait", "--for=condition=Ready",
            "externalsecret/test-secret", "-n", "default",
            "--timeout=60s"
        ], check=True)
        
        # Verify K8s secret exists
        secret = v1.read_namespaced_secret("test-secret", "default")
        assert secret.data is not None, "Secret has no data"
        
        # Cleanup
        subprocess.run([
            "kubectl", "delete", "-f", "tests/fixtures/test-external-secret.yaml"
        ], check=True)


class TestObservability:
    """Validate observability stack components."""
    
    def test_prometheus_targets_healthy(self):
        """All Prometheus targets must be healthy."""
        result = subprocess.run([
            "kubectl", "exec", "-n", "infrastructure",
            "prometheus-prometheus-0", "-c", "prometheus", "--",
            "wget", "-qO-", "http://localhost:9090/api/v1/targets"
        ], capture_output=True, text=True)
        
        targets = json.loads(result.stdout)
        unhealthy = [
            t["labels"]["job"] for t in targets["data"]["activeTargets"]
            if t["health"] != "up"
        ]
        assert len(unhealthy) == 0, f"Unhealthy Prometheus targets: {unhealthy}"

    def test_grafana_accessible(self):
        """Grafana must respond to health check."""
        result = subprocess.run([
            "kubectl", "exec", "-n", "infrastructure",
            "deploy/grafana", "--",
            "wget", "-qO-", "http://localhost:3000/api/health"
        ], capture_output=True, text=True)
        
        health = json.loads(result.stdout)
        assert health["database"] == "ok", f"Grafana unhealthy: {health}"

    def test_loki_queryable(self):
        """Loki must accept and return log queries."""
        result = subprocess.run([
            "kubectl", "exec", "-n", "infrastructure",
            "deploy/loki", "--",
            "wget", "-qO-",
            'http://localhost:3100/loki/api/v1/query?query={app="loki"}'
        ], capture_output=True, text=True)
        
        response = json.loads(result.stdout)
        assert response["status"] == "success", f"Loki query failed: {response}"
```

### 12.4 Performance Tests

#### 12.4.1 Node Provisioning Benchmark

```yaml
# tests/performance/node-provision-test.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: node-provision-benchmark
  namespace: test
spec:
  template:
    spec:
      containers:
        - name: benchmark
          image: python:3.11-slim
          command:
            - python
            - /scripts/benchmark.py
          env:
            - name: PENDING_POD_COUNT
              value: "10"
            - name: MAX_PROVISION_TIME
              value: "180"  # seconds
          volumeMounts:
            - name: scripts
              mountPath: /scripts
      serviceAccountName: benchmark-sa
      restartPolicy: Never
      volumes:
        - name: scripts
          configMap:
            name: benchmark-scripts
```

```python
# tests/performance/scripts/benchmark.py
"""Node provisioning benchmark - measures Karpenter provisioning time."""

import os
import time
from kubernetes import client, config

config.load_incluster_config()
v1 = client.CoreV1Api()

PENDING_POD_COUNT = int(os.environ.get("PENDING_POD_COUNT", 10))
MAX_PROVISION_TIME = int(os.environ.get("MAX_PROVISION_TIME", 180))

def create_pending_pods(count: int) -> list[str]:
    """Create pods that will trigger node provisioning."""
    pod_names = []
    for i in range(count):
        pod = client.V1Pod(
            metadata=client.V1ObjectMeta(
                name=f"provision-test-{i}",
                namespace="test",
                labels={"benchmark": "node-provision"}
            ),
            spec=client.V1PodSpec(
                containers=[
                    client.V1Container(
                        name="test",
                        image="nginx:latest",
                        resources=client.V1ResourceRequirements(
                            requests={"cpu": "500m", "memory": "512Mi"}
                        )
                    )
                ],
                # Force new node by requesting more than available
                node_selector={"benchmark": "true"}
            )
        )
        v1.create_namespaced_pod("test", pod)
        pod_names.append(f"provision-test-{i}")
    return pod_names

def wait_for_pods_scheduled(pod_names: list[str], timeout: int) -> float:
    """Wait for pods to be scheduled and return elapsed time."""
    start = time.time()
    pending = set(pod_names)
    
    while pending and (time.time() - start) < timeout:
        for name in list(pending):
            pod = v1.read_namespaced_pod(name, "test")
            if pod.status.phase != "Pending":
                pending.remove(name)
        time.sleep(5)
    
    elapsed = time.time() - start
    if pending:
        raise TimeoutError(f"Pods still pending after {timeout}s: {pending}")
    return elapsed

def cleanup(pod_names: list[str]):
    """Delete test pods."""
    for name in pod_names:
        v1.delete_namespaced_pod(name, "test")

if __name__ == "__main__":
    print(f"Creating {PENDING_POD_COUNT} pods to trigger provisioning...")
    pods = create_pending_pods(PENDING_POD_COUNT)
    
    try:
        elapsed = wait_for_pods_scheduled(pods, MAX_PROVISION_TIME)
        print(f"SUCCESS: All pods scheduled in {elapsed:.1f}s")
        print(f"Average provision time: {elapsed/PENDING_POD_COUNT:.1f}s per pod")
        
        # Assert performance target (Section 7.3)
        assert elapsed < MAX_PROVISION_TIME, \
            f"Provisioning exceeded {MAX_PROVISION_TIME}s target"
    finally:
        cleanup(pods)
```

#### 12.4.2 Performance Benchmarks

| Metric | Target | Measurement Method | Acceptable Degraded | Critical Threshold |
|--------|--------|-------------------|--------------------|--------------------|
| Node provision time | < 3 minutes | Time from pending pod to node Ready | < 5 minutes | > 10 minutes |
| Secret sync latency | < 30 seconds | ESO sync duration metric | < 60 seconds | > 2 minutes |
| Ingress latency (p50) | < 10ms | NGINX ingress metrics | < 25ms | > 50ms |
| Ingress latency (p99) | < 50ms | NGINX ingress metrics | < 100ms | > 200ms |
| Certificate issuance | < 2 minutes | cert-manager duration metric | < 5 minutes | > 10 minutes |
| Pod startup (container ready) | < 30 seconds | kubelet container_start_time | < 60 seconds | > 2 minutes |
| HPA scale-out reaction | < 60 seconds | Time from threshold breach to new replica | < 90 seconds | > 3 minutes |
| Prometheus scrape success | > 99.9% | up metric by job | > 99% | < 95% |

### 12.5 Chaos Tests

#### 12.5.1 Chaos Scenarios

| Scenario | Target Component | Chaos Action | Expected Behavior | Recovery Time Target |
|----------|-----------------|--------------|-------------------|---------------------|
| Node termination | Random worker node | Terminate EC2/VM instance | Pods reschedule, Karpenter replaces node | < 5 minutes |
| AZ failure | All nodes in one AZ | Network partition AZ | Workloads fail over to other AZs | < 3 minutes |
| Network partition | Cilium agents | Drop inter-node traffic | Traffic reroutes, Hubble alerts | < 1 minute |
| Vault unavailable | Vault endpoint | Block network to Vault | Cached secrets continue working, sync alerts | N/A (degraded mode) |
| etcd leader loss | Control plane | Kill etcd leader pod | New leader elected, API recovers | < 30 seconds |
| DNS failure | CoreDNS | Kill all CoreDNS pods | Cached DNS continues, PDB limits disruption | < 1 minute |
| Ingress overload | NGINX ingress | 10x traffic spike | HPA scales ingress pods, some 503s acceptable | < 2 minutes |

#### 12.5.2 Chaos Mesh Configuration

```yaml
# tests/chaos/node-failure.yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: AWSChaos
metadata:
  name: node-failure-test
  namespace: chaos-testing
spec:
  action: ec2-stop
  awsRegion: us-west-2
  ec2Instance: "auto"  # Random selection
  secretName: aws-chaos-credentials
  selector:
    labelSelectors:
      "node-pool": "general"
  duration: "5m"

---
# tests/chaos/network-partition.yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: az-partition-test
  namespace: chaos-testing
spec:
  action: partition
  mode: all
  selector:
    namespaces:
      - data-layer
    labelSelectors:
      "topology.kubernetes.io/zone": "us-west-2a"
  direction: both
  target:
    selector:
      namespaces:
        - data-layer
      labelSelectors:
        "topology.kubernetes.io/zone": "us-west-2b"
    mode: all
  duration: "3m"

---
# tests/chaos/pod-kill.yaml  
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata:
  name: coredns-kill-test
  namespace: chaos-testing
spec:
  action: pod-kill
  mode: all
  selector:
    namespaces:
      - kube-system
    labelSelectors:
      "k8s-app": "kube-dns"
  duration: "1m"
  gracePeriod: 0
```

### 12.6 Security Tests

#### 12.6.1 CIS Kubernetes Benchmark

**Automated Compliance Scanning:**

kube-bench runs as a CronJob for continuous CIS benchmark compliance monitoring. Results export to Prometheus for trending and alerting on compliance drift.

```yaml
# manifests/security/kube-bench-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: kube-bench-scan
  namespace: infrastructure
  labels:
    layer: l00
    component: security-compliance
spec:
  schedule: "0 6 * * *"  # Daily at 6 AM UTC
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        spec:
          hostPID: true
          serviceAccountName: kube-bench
          containers:
            - name: kube-bench
              image: aquasec/kube-bench:v0.7.0
              command: ["kube-bench"]
              args:
                - run
                - --targets
                - node,policies
                - --json
                - --outputfile
                - /output/results.json
              volumeMounts:
                - name: var-lib-kubelet
                  mountPath: /var/lib/kubelet
                  readOnly: true
                - name: etc-kubernetes
                  mountPath: /etc/kubernetes
                  readOnly: true
                - name: output
                  mountPath: /output
            - name: exporter
              image: python:3.11-slim
              command: ["python3"]
              args:
                - -c
                - |
                  import json
                  import os
                  from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
                  
                  registry = CollectorRegistry()
                  pass_gauge = Gauge('kubebench_checks_pass_total', 'Passing CIS checks', 
                                     ['target'], registry=registry)
                  fail_gauge = Gauge('kubebench_checks_fail_total', 'Failing CIS checks',
                                     ['target'], registry=registry)
                  warn_gauge = Gauge('kubebench_checks_warn_total', 'Warning CIS checks',
                                     ['target'], registry=registry)
                  
                  with open('/output/results.json') as f:
                      results = json.load(f)
                  
                  for control in results.get('Controls', []):
                      target = control.get('id', 'unknown')
                      totals = control.get('total_pass', 0), control.get('total_fail', 0), control.get('total_warn', 0)
                      pass_gauge.labels(target=target).set(totals[0])
                      fail_gauge.labels(target=target).set(totals[1])
                      warn_gauge.labels(target=target).set(totals[2])
                  
                  push_to_gateway('prometheus-pushgateway.infrastructure:9091', 
                                  job='kube-bench', registry=registry)
              volumeMounts:
                - name: output
                  mountPath: /output
          volumes:
            - name: var-lib-kubelet
              hostPath:
                path: /var/lib/kubelet
            - name: etc-kubernetes
              hostPath:
                path: /etc/kubernetes
            - name: output
              emptyDir: {}
          restartPolicy: OnFailure
          nodeSelector:
            node-role.kubernetes.io/control-plane: ""
          tolerations:
            - key: node-role.kubernetes.io/control-plane
              effect: NoSchedule
```

**kube-bench RBAC:**

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: kube-bench
  namespace: infrastructure
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: kube-bench
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: system:node  # Read access to node configuration
subjects:
  - kind: ServiceAccount
    name: kube-bench
    namespace: infrastructure
```

**CIS Compliance Alerting:**

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: cis-compliance-alerts
  namespace: infrastructure
  labels:
    layer: l00
spec:
  groups:
    - name: cis.compliance
      rules:
        - alert: CISBenchmarkFailures
          expr: sum(kubebench_checks_fail_total) > 0
          for: 1h
          labels:
            severity: high
          annotations:
            summary: "CIS Kubernetes Benchmark has {{ $value }} failing checks"
            runbook_url: "runbooks/cis-remediation.md"
            
        - alert: CISComplianceDrift
          expr: |
            sum(kubebench_checks_fail_total) 
            - sum(kubebench_checks_fail_total offset 24h) > 5
          for: 1h
          labels:
            severity: warning
          annotations:
            summary: "CIS compliance regressed by {{ $value }} checks in 24h"
```

**CIS Compliance Dashboard Metrics:**

| Metric | Type | Labels | Purpose |
|--------|------|--------|---------|
| `kubebench_checks_pass_total` | Gauge | target | Passing checks per category |
| `kubebench_checks_fail_total` | Gauge | target | Failing checks per category |
| `kubebench_checks_warn_total` | Gauge | target | Warning checks per category |
| `kubebench_last_scan_timestamp` | Gauge | - | Scan recency |

**Manual Scan Script:**

```bash
#!/bin/bash
# scripts/security-scan.sh

set -euo pipefail

echo "=== Security Scan Suite ==="
REPORT_DIR="reports/security/$(date +%Y%m%d)"
mkdir -p "$REPORT_DIR"

# 1. CIS Kubernetes Benchmark with kube-bench
echo "Running CIS Kubernetes Benchmark..."
kubectl apply -f https://raw.githubusercontent.com/aquasecurity/kube-bench/main/job.yaml
kubectl wait --for=condition=complete job/kube-bench -n default --timeout=300s
kubectl logs job/kube-bench -n default > "$REPORT_DIR/kube-bench.txt"
kubectl delete job kube-bench -n default

# Parse results
FAILURES=$(grep -c "\[FAIL\]" "$REPORT_DIR/kube-bench.txt" || true)
echo "CIS Benchmark: $FAILURES failures"

# 2. Container image vulnerability scanning with Trivy
echo "Running Trivy cluster scan..."
trivy k8s --report summary --severity HIGH,CRITICAL \
    --output "$REPORT_DIR/trivy-summary.txt" cluster

trivy k8s --report all --format json \
    --output "$REPORT_DIR/trivy-full.json" cluster

# 3. Kubernetes security audit with kubeaudit
echo "Running kubeaudit..."
kubeaudit all -n infrastructure > "$REPORT_DIR/kubeaudit-infra.txt"
kubeaudit all -n data-layer > "$REPORT_DIR/kubeaudit-data.txt"

# 4. Network policy validation
echo "Validating network policies..."
kubectl get networkpolicies -A -o json > "$REPORT_DIR/network-policies.json"

# Check for namespaces without default deny
UNPROTECTED=$(kubectl get ns -o jsonpath='{.items[*].metadata.name}' | tr ' ' '\n' | while read ns; do
    if ! kubectl get networkpolicy -n "$ns" -o name 2>/dev/null | grep -q "default-deny"; then
        echo "$ns"
    fi
done)

if [ -n "$UNPROTECTED" ]; then
    echo "WARNING: Namespaces without default-deny policy: $UNPROTECTED"
fi

echo "=== Security scan complete. Reports in $REPORT_DIR ==="
```

#### 12.6.2 Network Policy Tests

```python
# tests/security/test_network_isolation.py

import pytest
import subprocess
from kubernetes import client, config

config.load_kube_config()
v1 = client.CoreV1Api()


class TestNetworkIsolation:
    """Validate network segmentation per Security Section 8."""
    
    @pytest.fixture(autouse=True)
    def setup_test_pods(self):
        """Create test pods in different namespaces."""
        # Create test namespace if not exists
        for ns in ["agent-pool-a", "agent-pool-b", "data-layer"]:
            try:
                v1.create_namespace(
                    client.V1Namespace(metadata=client.V1ObjectMeta(name=ns))
                )
            except client.exceptions.ApiException as e:
                if e.status != 409:  # Already exists
                    raise
        
        # Deploy test pods
        subprocess.run([
            "kubectl", "apply", "-f", "tests/fixtures/network-test-pods.yaml"
        ], check=True)
        
        # Wait for pods ready
        subprocess.run([
            "kubectl", "wait", "--for=condition=Ready",
            "pod/test-pod", "-n", "agent-pool-a",
            "--timeout=60s"
        ], check=True)
        
        yield
        
        # Cleanup
        subprocess.run([
            "kubectl", "delete", "-f", "tests/fixtures/network-test-pods.yaml"
        ], check=False)

    def test_agent_to_agent_blocked(self):
        """OC-1: Agents cannot communicate directly with each other."""
        result = subprocess.run([
            "kubectl", "exec", "-n", "agent-pool-a",
            "test-pod", "--",
            "curl", "-s", "--max-time", "5", "--connect-timeout", "3",
            "http://test-pod.agent-pool-b.svc:8080"
        ], capture_output=True)
        
        # Connection should fail (timeout or refused)
        assert result.returncode != 0, \
            "Agent-to-agent traffic should be blocked by NetworkPolicy"

    def test_agent_to_data_layer_allowed(self):
        """Agents can reach Data Layer services."""
        result = subprocess.run([
            "kubectl", "exec", "-n", "agent-pool-a",
            "test-pod", "--",
            "curl", "-s", "--max-time", "10",
            "http://event-store.data-layer.svc:8080/health"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, \
            f"Agent to Data Layer should be allowed: {result.stderr}"

    def test_data_layer_to_external_blocked(self):
        """Data Layer cannot reach external internet directly."""
        result = subprocess.run([
            "kubectl", "exec", "-n", "data-layer",
            "test-pod", "--",
            "curl", "-s", "--max-time", "5", "--connect-timeout", "3",
            "http://example.com"
        ], capture_output=True)
        
        # Should fail unless explicitly allowed via egress policy
        assert result.returncode != 0, \
            "Data Layer external egress should be blocked"

    def test_prometheus_scrape_allowed(self):
        """Prometheus can scrape metrics from all namespaces."""
        result = subprocess.run([
            "kubectl", "exec", "-n", "infrastructure",
            "prometheus-prometheus-0", "-c", "prometheus", "--",
            "curl", "-s", "--max-time", "10",
            "http://test-pod.agent-pool-a.svc:9090/metrics"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, \
            f"Prometheus scrape should be allowed: {result.stderr}"
```

### 12.7 Test Environments

| Environment | Purpose | Data Source | Cluster Size | Refresh Frequency |
|-------------|---------|-------------|--------------|-------------------|
| CI | Automated tests on PR | Synthetic fixtures | kind (4 nodes) | Per-run (ephemeral) |
| Dev | Developer testing | Synthetic | EKS (3 nodes) | On-demand |
| Staging | Pre-production validation | Anonymized production | EKS (10 nodes) | Weekly from prod |
| Production | Canary testing only | Real production | EKS (50+ nodes) | N/A |

**CI Environment Configuration:**

```yaml
# .github/workflows/integration-tests.yaml
name: Integration Tests

on:
  pull_request:
    paths:
      - 'terraform/**'
      - 'helm/**'
      - 'manifests/**'

jobs:
  integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Create kind cluster
        uses: helm/kind-action@v1
        with:
          config: tests/kind-config.yaml
          cluster_name: test
      
      - name: Install infrastructure components
        run: |
          helm install cilium cilium/cilium -n kube-system --wait
          helm install prometheus prometheus-community/kube-prometheus-stack -n infrastructure --create-namespace --wait
      
      - name: Run integration tests
        run: |
          pip install pytest kubernetes
          pytest tests/integration/ -v --junitxml=report.xml
      
      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: test-results
          path: report.xml
```

---

## 13. Migration and Deployment

### 13.1 Deployment Strategy

#### 13.1.1 GitOps Workflow

All infrastructure changes flow through Git with ArgoCD reconciliation. Direct `kubectl apply` is prohibited in staging and production.

```
GITOPS DEPLOYMENT FLOW
======================

Developer            Git Repository       ArgoCD             Kubernetes Cluster
    |                      |                 |                        |
    |-- git push --------->|                 |                        |
    |                      |                 |                        |
    |                      |<-- webhook -----|                        |
    |                      |                 |                        |
    |                      |                 |-- detect diff -------->|
    |                      |                 |                        |
    |                      |                 |<-- current state ------|
    |                      |                 |                        |
    |                      |                 |-- sync (apply) ------->|
    |                      |                 |                        |
    |                      |                 |<-- sync result --------|
    |                      |                 |                        |
    |<-- notification -----|-----------------|                        |
    |                      |                 |                        |

SYNC STRATEGIES:
- auto-sync: Development, Staging (immediate reconciliation)
- manual-sync: Production (requires approval, then auto-apply)
```

#### 13.1.2 Environment Promotion Flow

```
ENVIRONMENT PROMOTION
=====================

+------------------+      +------------------+      +------------------+
|   Development    |----->|     Staging      |----->|    Production    |
+------------------+      +------------------+      +------------------+
        |                         |                         |
        v                         v                         v
  Git branch: dev           Git branch: staging       Git branch: main
  Auto-sync: Yes            Auto-sync: Yes            Auto-sync: No
  Approval: None            Approval: None            Approval: Required
  Tests: Unit               Tests: Integration        Tests: Smoke + Canary
```

**Promotion Process:**

| Step | Action | Automation | Gate |
|------|--------|------------|------|
| 1 | Merge PR to `dev` branch | CI runs unit tests | Tests pass |
| 2 | ArgoCD syncs to Development | Automatic | Sync healthy |
| 3 | Create PR from `dev` to `staging` | Manual | Code review |
| 4 | Merge triggers integration tests | CI pipeline | Tests pass |
| 5 | ArgoCD syncs to Staging | Automatic | Sync healthy |
| 6 | Create PR from `staging` to `main` | Manual | Two approvals |
| 7 | Merge triggers production sync | ArgoCD (manual sync) | Approval in ArgoCD |
| 8 | Canary rollout in Production | Argo Rollouts | Metrics healthy |

### 13.2 Upgrade Procedures

#### 13.2.1 Kubernetes Version Upgrade

Kubernetes minor version upgrades (e.g., 1.28 to 1.29) follow a rolling strategy to maintain availability.

| Step | Action | Rollback Point | Duration | Risk |
|------|--------|----------------|----------|------|
| 1 | Update `cluster_version` in Terraform | `git revert` | 5 min | Low |
| 2 | `terraform apply` upgrades control plane | N/A (managed) | 15-30 min | Low |
| 3 | Validate control plane health | N/A | 5 min | N/A |
| 4 | Drain and replace nodes (one AZ at a time) | Stop, uncordon | 10 min/AZ | Medium |
| 5 | Validate workload health | Pause, investigate | 5 min | Medium |
| 6 | Repeat Step 4-5 for remaining AZs | - | 20 min | Medium |
| 7 | Final validation | Emergency rollback | 10 min | Low |

**Upgrade Script:**

```bash
#!/bin/bash
# scripts/upgrade-kubernetes.sh

set -euo pipefail

NEW_VERSION="${1:?Usage: $0 <version>}"
CLUSTER_NAME="${CLUSTER_NAME:-agentic-prod-us-west-2}"
REGION="${AWS_REGION:-us-west-2}"

echo "=== Kubernetes Upgrade to $NEW_VERSION ==="
echo "Cluster: $CLUSTER_NAME"
echo "Region: $REGION"

# Pre-flight checks
echo "Running pre-flight checks..."
kubectl get nodes
kubectl cluster-info

read -p "Proceed with upgrade? (y/n) " -n 1 -r
echo
[[ $REPLY =~ ^[Yy]$ ]] || exit 1

# Step 1: Update control plane via Terraform
echo "Step 1: Upgrading control plane..."
cd terraform/environments/production
terraform plan -var="cluster_version=$NEW_VERSION" -target=module.eks -out=upgrade.plan
terraform apply upgrade.plan

# Step 2: Wait for control plane
echo "Step 2: Waiting for control plane upgrade..."
aws eks wait cluster-active --name "$CLUSTER_NAME" --region "$REGION"
echo "Control plane upgraded. Validating..."
kubectl version

# Step 3: Rolling update nodes by AZ
for az in "${REGION}a" "${REGION}b" "${REGION}c"; do
    echo "Step 3: Upgrading nodes in $az..."
    
    # Get nodes in AZ
    nodes=$(kubectl get nodes -l "topology.kubernetes.io/zone=$az" -o name)
    
    for node in $nodes; do
        node_name=$(echo "$node" | cut -d'/' -f2)
        echo "Draining $node_name..."
        
        kubectl drain "$node_name" \
            --ignore-daemonsets \
            --delete-emptydir-data \
            --force \
            --grace-period=60
        
        # Karpenter provisions new node with updated AMI
        echo "Waiting for replacement node..."
        sleep 30
        
        # Delete old node (Karpenter handles replacement)
        kubectl delete node "$node_name"
        
        # Wait for pending pods to schedule
        echo "Waiting for pods to stabilize..."
        kubectl wait --for=condition=Ready pods --all -A --timeout=300s || true
        sleep 30
    done
    
    echo "AZ $az complete. Validating..."
    kubectl get nodes
    
    # Inter-AZ pause for safety
    sleep 60
done

# Step 4: Final validation
echo "Step 4: Running post-upgrade validation..."
./scripts/validate-cluster.sh

echo "=== Upgrade to $NEW_VERSION complete ==="
```

#### 13.2.2 Component Upgrade Matrix

| Component | Upgrade Method | Downtime | Rollback Strategy | Pre-requisites |
|-----------|---------------|----------|-------------------|----------------|
| Cilium | Helm upgrade (rolling) | Zero | `helm rollback cilium` | Check CNI compatibility |
| External Secrets | Helm upgrade | Zero | `helm rollback external-secrets` | None |
| cert-manager | Helm upgrade | Zero | `helm rollback cert-manager` | Check CRD versions |
| Prometheus | StatefulSet rolling | Brief metric gap | `helm rollback prometheus` | None |
| Loki | StatefulSet rolling | Brief log gap | `helm rollback loki` | Check schema version |
| ArgoCD | Helm upgrade | Brief UI downtime | `helm rollback argocd` | Backup Application CRDs |
| Karpenter | Helm upgrade | Zero | `helm rollback karpenter` | None |
| Gatekeeper | Helm upgrade | Zero | `helm rollback gatekeeper` | Backup ConstraintTemplates |

### 13.3 Rollback Procedures

#### 13.3.1 ArgoCD Application Rollback

```bash
# View sync history
argocd app history <app-name>

# Rollback to previous sync (last known good)
argocd app rollback <app-name>

# Rollback to specific revision
argocd app rollback <app-name> <revision-number>

# Emergency: disable auto-sync and manual rollback
argocd app set <app-name> --sync-policy none
kubectl rollout undo deployment/<deployment-name> -n <namespace>

# Verify rollback
argocd app get <app-name>
kubectl rollout status deployment/<deployment-name> -n <namespace>
```

#### 13.3.2 Terraform State Rollback

```bash
# View state versions (S3 versioning enabled)
aws s3api list-object-versions \
    --bucket terraform-state-bucket \
    --prefix "production/terraform.tfstate" \
    --query 'Versions[*].{Key:Key,VersionId:VersionId,LastModified:LastModified}'

# Restore previous state version
aws s3api get-object \
    --bucket terraform-state-bucket \
    --key "production/terraform.tfstate" \
    --version-id "<version-id>" \
    terraform.tfstate.restored

# Review diff before applying
terraform plan -state=terraform.tfstate.restored

# Apply restored state
cp terraform.tfstate.restored terraform.tfstate
terraform apply

# Alternative: git revert and re-apply
git revert HEAD --no-edit
terraform apply
```

#### 13.3.3 Rollback Decision Matrix

| Symptom | Severity | Rollback Scope | Procedure |
|---------|----------|----------------|-----------|
| Single pod CrashLooping | Low | Deployment only | `kubectl rollout undo` |
| Service unreachable | Medium | Application + config | ArgoCD rollback |
| Cluster API errors | High | Control plane | Terraform rollback |
| Data corruption | Critical | Full cluster | DR failover |
| Networking broken | Critical | CNI component | Helm rollback Cilium |

### 13.4 Multi-Region Deployment

#### 13.4.1 Region Deployment Order

| Order | Region | Role | Cluster Name | Dependencies |
|-------|--------|------|--------------|--------------|
| 1 | us-west-2 | Primary | agentic-prod-usw2 | None |
| 2 | us-east-1 | DR Secondary | agentic-dr-use1 | Primary healthy |
| 3 | eu-west-1 | EU Primary (future) | agentic-prod-euw1 | Primary patterns validated |

#### 13.4.2 Cross-Region Architecture

```
MULTI-REGION DEPLOYMENT
=======================

                     +-------------------+
                     |    Route 53       |
                     |  (Global DNS)     |
                     +---------+---------+
                               |
              +----------------+----------------+
              |                                 |
              v                                 v
+-------------+-------------+     +-------------+-------------+
|     us-west-2 (Primary)   |     |    us-east-1 (DR)         |
+---------------------------+     +---------------------------+
|                           |     |                           |
|  +---------------------+  |     |  +---------------------+  |
|  | EKS Cluster         |  |     |  | EKS Cluster         |  |
|  | (agentic-prod-usw2) |  |     |  | (agentic-dr-use1)   |  |
|  +---------------------+  |     |  +---------------------+  |
|                           |     |                           |
|  +---------------------+  |     |  +---------------------+  |
|  | Vault (Primary)     |  |     |  | Vault (Replica)     |  |
|  +---------------------+  |     |  +---------------------+  |
|            |              |     |            ^              |
|            +--------------+-----+------------+              |
|                    Replication              |               |
|                           |     |                           |
|  +---------------------+  |     |  +---------------------+  |
|  | S3 (Primary)        |  |     |  | S3 (Replica)        |  |
|  +---------------------+  |     |  +---------------------+  |
|            |              |     |            ^              |
|            +--------------+-----+------------+              |
|               Cross-Region Replication       |              |
+---------------------------+     +---------------------------+

TRAFFIC FLOW (Normal):
Route 53 --> us-west-2 (100%)

TRAFFIC FLOW (DR):
Route 53 --> us-east-1 (100%, manual failover)
```

#### 13.4.3 Cross-Region Terraform

```hcl
# terraform/environments/production/cross-region.tf

# Secondary region provider
provider "aws" {
  alias  = "dr"
  region = "us-east-1"
}

# Replicate critical S3 data to DR region
resource "aws_s3_bucket_replication_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  role   = aws_iam_role.replication.arn

  rule {
    id     = "replicate-all"
    status = "Enabled"

    destination {
      bucket        = aws_s3_bucket.terraform_state_dr.arn
      storage_class = "STANDARD"
    }
  }
}

# DR cluster (scaled down when not active)
module "eks_dr" {
  source = "../../modules/cluster"
  providers = {
    aws = aws.dr
  }

  cluster_name    = "agentic-dr-use1"
  cluster_version = var.cluster_version
  
  # DR cluster runs minimal nodes until activated
  node_pools = {
    system = {
      min_size     = 2
      max_size     = 3
      desired_size = 2
    }
    # Other pools scaled to 0
  }
}

# Route53 health check for failover
resource "aws_route53_health_check" "primary" {
  fqdn              = "api.${var.domain}"
  port              = 443
  type              = "HTTPS"
  resource_path     = "/health"
  failure_threshold = 3
  request_interval  = 30

  tags = {
    Name = "primary-health-check"
  }
}

# DNS failover record
resource "aws_route53_record" "api_failover" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "api.${var.domain}"
  type    = "A"

  failover_routing_policy {
    type = "PRIMARY"
  }

  alias {
    name                   = module.eks.ingress_lb_dns
    zone_id                = module.eks.ingress_lb_zone_id
    evaluate_target_health = true
  }

  set_identifier  = "primary"
  health_check_id = aws_route53_health_check.primary.id
}
```

### 13.5 Disaster Recovery

#### 13.5.1 DR Runbook

| Step | Action | Owner | Max Duration | Verification |
|------|--------|-------|--------------|--------------|
| 1 | Detect primary region failure | Automated (PagerDuty) | 0 min | Alert received |
| 2 | Assess failure scope | On-call SRE | 5 min | Incident channel created |
| 3 | Verify DR region health | On-call SRE | 5 min | `kubectl get nodes` succeeds |
| 4 | Scale up DR cluster | On-call SRE | 10 min | Desired node count reached |
| 5 | Verify data replication state | On-call SRE | 5 min | Check S3, Vault replication lag |
| 6 | Update Route53 DNS | On-call SRE | 5 min | DNS propagation started |
| 7 | Verify traffic flowing to DR | On-call SRE | 10 min | Requests hitting DR cluster |
| 8 | Notify stakeholders | On-call SRE | 5 min | Email/Slack sent |
| 9 | Monitor DR performance | On-call SRE | Ongoing | Dashboards green |
| 10 | Begin primary recovery assessment | Platform Team | When available | Post-incident |

**Total RTO Target: 45 minutes**

#### 13.5.2 DR Activation Script

```bash
#!/bin/bash
# scripts/activate-dr.sh

set -euo pipefail

DR_REGION="us-east-1"
DR_CLUSTER="agentic-dr-use1"
PRIMARY_DOMAIN="api.example.com"
DR_DOMAIN="api-dr.example.com"

echo "=== DR ACTIVATION STARTED ==="
echo "Time: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Target Region: $DR_REGION"

# Step 1: Scale up DR cluster
echo "Step 1: Scaling up DR cluster..."
cd terraform/environments/dr
terraform apply -var="dr_active=true" -auto-approve

# Step 2: Wait for nodes
echo "Step 2: Waiting for DR nodes..."
aws eks update-kubeconfig --name "$DR_CLUSTER" --region "$DR_REGION"
kubectl wait --for=condition=Ready nodes --all --timeout=600s

# Step 3: Verify core services
echo "Step 3: Verifying core services..."
kubectl get pods -A | grep -E "(Running|Completed)" | wc -l

# Step 4: Verify data layer
echo "Step 4: Checking data layer health..."
kubectl exec -n data-layer deploy/event-store -- /health

# Step 5: Update DNS (manual confirmation)
echo "Step 5: DNS Update Required"
echo "Execute: aws route53 change-resource-record-sets ..."
read -p "Confirm DNS updated (y/n): " -n 1 -r
[[ $REPLY =~ ^[Yy]$ ]] || exit 1

# Step 6: Verify traffic
echo "Step 6: Verifying traffic..."
for i in {1..10}; do
    curl -s -o /dev/null -w "%{http_code}" "https://$PRIMARY_DOMAIN/health"
    sleep 5
done

echo "=== DR ACTIVATION COMPLETE ==="
echo "Monitor: https://grafana.example.com/d/dr-dashboard"
```

#### 13.5.3 DR Testing Schedule

| Test Type | Frequency | Scope | Duration | Participants |
|-----------|-----------|-------|----------|--------------|
| DNS failover test | Monthly | DNS records only | 30 min | SRE Team |
| Read traffic failover | Quarterly | Read-only workloads to DR | 2 hours | SRE + Platform |
| Write traffic failover | Semi-annually | Subset of write workloads | 4 hours | Full team |
| Full DR activation | Annually | Complete regional failover | 1 day | Company-wide |

### 13.6 Canary Deployments

For high-risk infrastructure changes, use Argo Rollouts canary strategy.

```yaml
# manifests/argocd/canary-rollout-example.yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: ingress-nginx
  namespace: ingress
  labels:
    layer: l00
spec:
  replicas: 5
  strategy:
    canary:
      steps:
        - setWeight: 10
        - pause: { duration: 5m }
        - setWeight: 25
        - pause: { duration: 5m }
        - setWeight: 50
        - pause: { duration: 10m }
        - setWeight: 75
        - pause: { duration: 5m }
      canaryMetadata:
        labels:
          role: canary
      stableMetadata:
        labels:
          role: stable
      trafficRouting:
        nginx:
          stableIngress: ingress-nginx-stable
          additionalIngressAnnotations:
            canary-by-header: X-Canary
      analysis:
        templates:
          - templateName: success-rate
        startingStep: 2
        args:
          - name: service-name
            value: ingress-nginx
  selector:
    matchLabels:
      app: ingress-nginx
  template:
    metadata:
      labels:
        app: ingress-nginx
    spec:
      containers:
        - name: nginx
          image: nginx/nginx-ingress:latest
          ports:
            - containerPort: 80

---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
  namespace: ingress
spec:
  args:
    - name: service-name
  metrics:
    - name: success-rate
      interval: 1m
      successCondition: result[0] >= 0.99
      failureLimit: 3
      provider:
        prometheus:
          address: http://prometheus.infrastructure:9090
          query: |
            sum(rate(nginx_ingress_controller_requests{service="{{args.service-name}}",status!~"5.."}[5m])) /
            sum(rate(nginx_ingress_controller_requests{service="{{args.service-name}}"}[5m]))
```

---

## 14. Open Questions and Decisions

### 14.1 Resolved Questions

#### Q1: Multi-cloud vs Single-cloud Deployment Strategy

| Attribute | Decision | Rationale |
|-----------|----------|-----------|
| **Primary Strategy** | Single-cloud, multi-region | Operational complexity of multi-cloud exceeds benefits at current scale |
| **Cloud Provider** | AWS (primary), GCP (approved alternative) | Team expertise, service maturity, enterprise support |
| **Multi-region Model** | Active-passive (us-west-2 primary, us-east-1 DR) | Sufficient for 99.9% availability target |
| **Future Review** | Re-evaluate multi-cloud at 10x scale | Document abstraction points for portability |

**Abstraction Points for Future Multi-cloud Portability:**

| Component | Abstraction Mechanism |
|-----------|----------------------|
| Compute | Kubernetes API (no cloud-specific CRDs in workloads) |
| Storage | StorageClass abstraction (CSI drivers) |
| Secrets | External Secrets Operator (backend-agnostic) |
| DNS | ExternalDNS (provider-agnostic) |
| IaC | Terraform with provider-specific modules |
| Load Balancing | Kubernetes Service type LoadBalancer |

**Trade-offs Accepted:**

- Higher risk concentration in single provider (mitigated by multi-region)
- Potential vendor lock-in (mitigated by Kubernetes abstraction layer)
- Limited regulatory options for data residency (acceptable for current markets)

#### Q2: GPU Sharing Model for LLM Inference Workloads

| Environment | GPU Sharing Model | GPU Type | Configuration | Rationale |
|-------------|-------------------|----------|---------------|-----------|
| Production | MIG (Multi-Instance GPU) | A100 80GB | Mixed profiles (1g.10gb, 2g.20gb, 3g.40gb) | Memory isolation prevents noisy neighbor; predictable performance |
| Staging | Time-slicing | A10G | 4 replicas per GPU | Cost efficiency; isolation not critical for testing |
| Development | Time-slicing | T4 | 2 replicas per GPU | Minimal GPU needs; shared resources acceptable |
| Batch/Training | Dedicated | A100/H100 | 1:1 pod:GPU on spot | Maximum throughput; preemption acceptable |

**MIG Configuration for A100 80GB:**

```yaml
# Default production MIG profile allocation
nvidia.com/mig.strategy: mixed
profiles:
  - name: 1g.10gb
    count: 4
    description: Small inference requests (<7B parameters)
  - name: 2g.20gb  
    count: 2
    description: Medium inference (7B-13B parameters)
  - name: 3g.40gb
    count: 1
    description: Large inference (>13B parameters)
```

**Resource Request Examples:**

```yaml
# Small model inference
resources:
  limits:
    nvidia.com/mig-1g.10gb: 1

# Medium model inference  
resources:
  limits:
    nvidia.com/mig-2g.20gb: 1

# Large model inference
resources:
  limits:
    nvidia.com/mig-3g.40gb: 1
```

#### Q3: Edge Deployment Requirements

| Attribute | Decision | Rationale |
|-----------|----------|-----------|
| **Scope** | Defer to v2.0 | No immediate edge use cases identified; central deployment sufficient |
| **Future Runtime** | k3s (single binary, GPU support) | Kubernetes-conformant, lightweight, proven at edge |
| **Management** | Fleet (Rancher) for GitOps sync | Scalable fleet management with central control |
| **Sync Model** | Hub-spoke with async event forwarding | Edge operates independently, syncs when connected |

**Edge Workload Suitability (for future reference):**

| Workload | Edge Suitable | Central Required | Rationale |
|----------|---------------|------------------|-----------|
| Input validation | Yes | - | Reduce invalid requests at source |
| Context pre-processing | Yes | - | Local data size reduction |
| Inference cache | Yes | - | Latency optimization |
| Small model (<7B) | Optional | Yes | If edge GPU available |
| Full agent execution | - | Yes | Requires complete Data Layer |
| Event sourcing | - | Yes | Central authority required |

**Prerequisites for Edge (v2.0):**

1. Define specific edge use cases with latency requirements
2. Establish offline operation requirements
3. Determine data synchronization SLAs
4. Evaluate edge hardware standards

### 14.2 Deferred Decisions

| ID | Question | Defer Until | Dependencies | Owner |
|----|----------|-------------|--------------|-------|
| D1 | FinOps integration depth | Post-MVP (Q2) | OpenCost deployment validated in production | Platform Team |
| D2 | Service mesh mutual TLS scope | L02 specification | Agent identity model finalized | Security Team |
| D3 | Bare metal Kubernetes support | Customer request | No current requirement | Platform Team |
| D4 | Windows node pool support | Customer request | No current requirement | Platform Team |
| D5 | GPU time-slicing in production | Performance testing | Validate isolation acceptable | ML Platform Team |

#### 14.2.1 Industry Validation Deferred Items

The following items were identified during D.3 Industry Validation but deferred due to scope or effort:

| ID | Enhancement | Priority | Effort | Target Version | Rationale |
|----|-------------|----------|--------|----------------|-----------|
| SEC-IND-003 | Runtime security (Falco/Tetragon) | P3 | Large | v2.0 | Requires eBPF expertise and operational maturity; evaluate after supply chain security (SEC-IND-001) deployed |
| K8S-IND-004 | Cluster API for declarative cluster management | P3 | Large | v2.0 | Current Terraform approach adequate; Cluster API adds abstraction complexity without immediate benefit |
| K8S-IND-005 | Kueue for batch workload scheduling | P3 | Medium | v1.3 | Evaluate when L06 Evaluation and L07 Learning layer batch workloads increase |
| OBS-IND-002 | SLO/SLI framework (Sloth/Pyrra) | P3 | Medium | v1.3 | Current Prometheus alerting sufficient; formalize SLOs after production traffic patterns established |
| EMRG-IND-001 | Internal Developer Platform (Backstage) | P3 | Large | v2.0 | Requires organizational IDP strategy; defer until platform team capacity available |
| EMRG-IND-002 | AI/ML inference optimization (KServe, Triton) | P3 | Medium | v1.3 | Evaluate when L04 Model Gateway inference latency requirements exceed current capabilities |

**Tracking:** These items are tracked in the product backlog for future releases.

### 14.3 Assumptions

| ID | Assumption | Impact if Invalid | Mitigation Strategy |
|----|------------|-------------------|---------------------|
| A1 | Managed Kubernetes (EKS/GKE) meets 99.9% SLA | Must self-manage control plane | Design workloads for multi-region failover |
| A2 | Vault available as managed service or pre-deployed | Must deploy and operate Vault in-cluster | Document Vault deployment procedure |
| A3 | Team has Kubernetes operational expertise | Extended onboarding required | Include training in Phase 0 |
| A4 | Network bandwidth sufficient for observability | Aggressive sampling required | Configure sampling ratios, pre-aggregation |
| A5 | GPU availability in target regions | Scheduling delays, reduced capacity | Multi-region GPU pools, fallback to CPU |
| A6 | ArgoCD can manage all infrastructure components | Some components require alternative deployment | Document ArgoCD limitations, helm CLI fallback |

### 14.4 Risk Register

| ID | Risk | Probability | Impact | Mitigation | Contingency |
|----|------|-------------|--------|------------|-------------|
| R1 | Karpenter instability during rapid scale events | Low | High | Use PodDisruptionBudgets, limit concurrent scaling | Fallback to Cluster Autoscaler |
| R2 | Cilium eBPF kernel incompatibility | Low | Critical | Pin kernel version in node AMI, test before upgrade | Document CNI fallback to Calico |
| R3 | Vault outage blocks secret rotation | Medium | Medium | Configure long TTL (24h) for cached secrets, alerting | Manual secret injection procedure |
| R4 | GPU instance shortages | Medium | High | Multi-region GPU pools, mixed instance types | Queue workloads, priority scheduling |
| R5 | Cost overrun from autoscaling | Medium | Medium | Budget alerts at 80%, 100%; hard limits in Karpenter | Manual scale-down procedure |
| R6 | ArgoCD sync storms | Low | Medium | Configure sync windows, rate limiting | Manual sync with kubectl |
| R7 | Observability data loss | Low | Medium | Redundant collectors, S3 durability | Accept data gaps, prioritize availability |

### 14.5 Decision Log

| Date | Decision | Context | Alternatives Considered | Decided By | Reference |
|------|----------|---------|------------------------|------------|-----------|
| 2025-01-04 | Cilium over Istio | Service mesh selection | Istio (higher overhead, more features), Linkerd (simpler, fewer L7 features) | Architecture Review | Gap Analysis G-DL-004 |
| 2025-01-04 | Karpenter over Cluster Autoscaler | Node scaling | Cluster Autoscaler (slower, proven), custom scheduler | Performance Testing | Research Finding 1.2 |
| 2025-01-04 | ESO over Vault Agent | Secret injection | Vault Agent (sidecar complexity), CSI driver (less flexible) | Operational Simplicity | Research Finding 4.1 |
| 2025-01-04 | ArgoCD over Flux | GitOps controller | Flux (less UI, similar features), Jenkins X (overkill) | Team Preference | Research Finding 8.2 |
| 2025-01-04 | Single-cloud initial | Deployment model | Multi-cloud (operational complexity), hybrid (insufficient benefit) | Cost/Complexity Analysis | Q1 Resolution |
| 2025-01-04 | MIG for production GPUs | GPU sharing | Time-slicing (no isolation), dedicated (underutilization) | Performance/Isolation | Q2 Resolution |
| 2025-01-04 | Defer edge deployment | Edge strategy | k3s immediate (no use case), cloud edge (immature) | Product Requirements | Q3 Resolution |

---

## 15. References and Appendices

### 15.1 External References

#### 15.1.1 CNCF Projects

| Project | Version | Purpose | Documentation | CNCF Status |
|---------|---------|---------|---------------|-------------|
| Kubernetes | 1.28+ | Container orchestration | https://kubernetes.io/docs/ | Graduated |
| Cilium | 1.14+ | CNI and service mesh | https://docs.cilium.io/ | Graduated |
| Prometheus | 2.45+ | Metrics collection | https://prometheus.io/docs/ | Graduated |
| ArgoCD | 2.8+ | GitOps deployment | https://argo-cd.readthedocs.io/ | Graduated |
| Helm | 3.12+ | Package management | https://helm.sh/docs/ | Graduated |
| OPA/Gatekeeper | 3.14+ | Policy enforcement | https://open-policy-agent.github.io/gatekeeper/ | Graduated |
| cert-manager | 1.13+ | Certificate management | https://cert-manager.io/docs/ | Incubating |
| KEDA | 2.11+ | Event-driven autoscaling | https://keda.sh/docs/ | Incubating |
| External Secrets | 0.9+ | Secret synchronization | https://external-secrets.io/latest/ | Incubating |
| OpenTelemetry | 0.88+ | Observability | https://opentelemetry.io/docs/ | Incubating |
| Karpenter | 0.32+ | Node autoscaling | https://karpenter.sh/docs/ | Sandbox |
| OpenCost | 1.108+ | Cost monitoring | https://www.opencost.io/docs/ | Sandbox |

#### 15.1.2 Cloud Provider Documentation

| Provider | Service | Documentation |
|----------|---------|---------------|
| AWS | EKS | https://docs.aws.amazon.com/eks/ |
| AWS | EC2 (GPU instances) | https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/accelerated-computing-instances.html |
| AWS | IAM Roles for Service Accounts | https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html |
| GCP | GKE | https://cloud.google.com/kubernetes-engine/docs |
| GCP | Workload Identity | https://cloud.google.com/kubernetes-engine/docs/concepts/workload-identity |
| HashiCorp | Vault | https://developer.hashicorp.com/vault/docs |
| HashiCorp | Terraform AWS Provider | https://registry.terraform.io/providers/hashicorp/aws/latest/docs |
| NVIDIA | GPU Operator | https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/ |
| NVIDIA | MIG User Guide | https://docs.nvidia.com/datacenter/tesla/mig-user-guide/ |

#### 15.1.3 Standards and Compliance

| Standard | Application | Reference |
|----------|-------------|-----------|
| CIS Kubernetes Benchmark v1.8 | Security hardening | https://www.cisecurity.org/benchmark/kubernetes |
| NIST SP 800-190 | Container security | https://csrc.nist.gov/publications/detail/sp/800-190/final |
| W3C Trace Context | Distributed tracing | https://www.w3.org/TR/trace-context/ |
| OpenMetrics | Metrics format | https://openmetrics.io/ |
| JSON Schema 2020-12 | Data validation | https://json-schema.org/specification.html |

### 15.2 Internal References

| Document | Location | Relevance |
|----------|----------|-----------|
| Data Layer Specification v3.2.1 | Project KB | Integration patterns, storage requirements |
| Layer Definitions v1.1 | Project KB | Scope boundaries, layer responsibilities |
| Infrastructure Gap Analysis | Project KB | Decision rationale, gap resolution |
| Infrastructure Research Findings | Project KB | Technology evaluation, recommendations |
| Layer Specification Template | Project KB | Document structure |
| Gap Analysis Methodology | Project KB | Analysis approach |

### 15.3 Glossary

| Term | Definition |
|------|------------|
| **AZ** | Availability Zone - isolated location within a cloud region providing fault isolation |
| **CNI** | Container Network Interface - plugin specification for configuring container networking |
| **CRD** | Custom Resource Definition - Kubernetes API extension mechanism |
| **CSI** | Container Storage Interface - plugin specification for storage providers |
| **DaemonSet** | Kubernetes workload type that runs exactly one pod per node |
| **eBPF** | Extended Berkeley Packet Filter - Linux kernel technology for programmable networking and observability |
| **ESO** | External Secrets Operator - Kubernetes operator for synchronizing secrets from external stores |
| **GitOps** | Infrastructure and application delivery using Git as the single source of truth |
| **HPA** | Horizontal Pod Autoscaler - Kubernetes resource that scales pod replicas based on metrics |
| **IRSA** | IAM Roles for Service Accounts - AWS mechanism for pod-level IAM permissions |
| **KEDA** | Kubernetes Event-Driven Autoscaling - scales workloads based on event sources |
| **MIG** | Multi-Instance GPU - NVIDIA technology for partitioning a single GPU into isolated instances |
| **mTLS** | Mutual TLS - bidirectional TLS authentication between client and server |
| **NodePool** | Karpenter resource defining node provisioning constraints |
| **OIDC** | OpenID Connect - identity layer on top of OAuth 2.0 |
| **OPA** | Open Policy Agent - policy engine for cloud-native environments |
| **OTEL** | OpenTelemetry - observability framework for traces, metrics, and logs |
| **PDB** | Pod Disruption Budget - Kubernetes resource controlling voluntary disruptions |
| **PVC** | Persistent Volume Claim - Kubernetes request for storage resources |
| **RBAC** | Role-Based Access Control - Kubernetes authorization mechanism |
| **RTO** | Recovery Time Objective - maximum acceptable time to restore service |
| **RPO** | Recovery Point Objective - maximum acceptable data loss measured in time |
| **StatefulSet** | Kubernetes workload type for stateful applications with stable identities |
| **VPA** | Vertical Pod Autoscaler - adjusts pod resource requests based on usage |
| **Workload Identity** | GCP mechanism for pod-level IAM permissions |
| **SBOM** | Software Bill of Materials - inventory of software components |
| **SLSA** | Supply-chain Levels for Software Artifacts - security framework for build integrity |
| **Cosign** | Container signing tool from Sigstore project |
| **Kyverno** | Kubernetes-native policy engine for admission control |

### 15.4 Standards Compliance Matrix

| Standard | Version | Compliance Level | Evidence | Notes |
|----------|---------|------------------|----------|-------|
| CIS Kubernetes Benchmark | 1.9.0 | Full | Section 12.6 automated scanning | kube-bench CronJob with alerting |
| NIST 800-190 | Final | Full | Sections 8.1, 8.8 | Host OS hardening, supply chain security |
| SLSA Framework | 1.0 | Level 2 | Section 8.8 | Cosign signing, provenance attestation |
| AWS Well-Architected | 2024 | Full | Sections 3, 7, 8, 9 | Multi-AZ, autoscaling, observability |
| OpenTelemetry | 1.x | Full | Section 9.2 | Collector + Operator options |
| GitOps Principles | 1.0 | Full | Section 10 | ArgoCD with notifications |
| FinOps Practices | - | Partial | Section 9.8 | Budget alerts; showback deferred to v1.3 |

**Compliance Certification:**

| Criterion | Status | Validation |
|-----------|--------|------------|
| All P1 industry findings addressed | Complete | SEC-IND-001, K8S-IND-001 |
| Security standards alignment | Full | CIS, NIST 800-190, SLSA L2 |
| Observability standards alignment | Full | OpenTelemetry, Prometheus |
| Operational standards alignment | Full | GitOps, FinOps (partial) |

### 15.5 Appendix A: Complete Terraform Module List

| Module | Path | Purpose | Inputs | Outputs |
|--------|------|---------|--------|---------|
| `vpc` | `terraform/modules/vpc` | VPC, subnets, NAT gateways, VPC endpoints | `vpc_cidr`, `azs`, `cluster_name` | `vpc_id`, `private_subnet_ids`, `public_subnet_ids` |
| `cluster` | `terraform/modules/cluster` | EKS/GKE cluster, control plane, addons | `cluster_name`, `cluster_version`, `vpc_id`, `subnet_ids` | `cluster_endpoint`, `cluster_ca`, `oidc_provider_arn` |
| `node_pools` | `terraform/modules/node_pools` | Managed node groups (system only) | `cluster_name`, `node_pools` | `node_group_arns` |
| `karpenter` | `terraform/modules/karpenter` | Karpenter controller and IAM | `cluster_name`, `cluster_endpoint` | `karpenter_role_arn` |
| `iam` | `terraform/modules/iam` | IAM roles, policies, IRSA | `cluster_name`, `oidc_provider_arn` | `role_arns` |
| `storage` | `terraform/modules/storage` | S3 buckets for state, logs, backups | `environment`, `cluster_name` | `bucket_arns` |
| `kms` | `terraform/modules/kms` | KMS keys for encryption | `environment` | `key_arns`, `key_aliases` |
| `vault` | `terraform/modules/vault` | Vault namespace, Kubernetes auth | `vault_address`, `cluster_name` | `vault_role_name` |

### 15.5 Appendix B: Helm Chart Inventory

| Chart | Repository | Namespace | Version | Purpose |
|-------|------------|-----------|---------|---------|
| `cilium` | https://helm.cilium.io | kube-system | 1.14.x | CNI, service mesh, network policies |
| `ingress-nginx` | https://kubernetes.github.io/ingress-nginx | ingress | 4.8.x | Ingress controller |
| `external-dns` | https://kubernetes-sigs.github.io/external-dns | infrastructure | 1.14.x | DNS record management |
| `external-secrets` | https://charts.external-secrets.io | infrastructure | 0.9.x | Secret synchronization |
| `cert-manager` | https://charts.jetstack.io | cert-manager | 1.13.x | TLS certificate automation |
| `kube-prometheus-stack` | https://prometheus-community.github.io/helm-charts | infrastructure | 54.x | Prometheus, Alertmanager, Grafana |
| `loki` | https://grafana.github.io/helm-charts | infrastructure | 5.x | Log aggregation |
| `tempo` | https://grafana.github.io/helm-charts | infrastructure | 1.x | Trace storage |
| `argo-cd` | https://argoproj.github.io/argo-helm | argocd | 5.x | GitOps controller |
| `argo-rollouts` | https://argoproj.github.io/argo-helm | argocd | 2.x | Progressive delivery |
| `gatekeeper` | https://open-policy-agent.github.io/gatekeeper/charts | gatekeeper-system | 3.14.x | Policy enforcement |
| `keda` | https://kedacore.github.io/charts | keda | 2.12.x | Event-driven autoscaling |
| `opencost` | https://opencost.github.io/opencost-helm-chart | infrastructure | 1.x | Cost tracking |
| `reloader` | https://stakater.github.io/stakater-charts | infrastructure | 1.x | Secret/ConfigMap reload |

### 15.6 Appendix C: Runbook Index

| Runbook | Trigger (Alert) | Severity | Location |
|---------|-----------------|----------|----------|
| Node Not Ready | `ClusterNodeNotReady` | P2 | runbooks/node-not-ready.md |
| Node Disk Pressure | `NodeDiskPressure` | P2 | runbooks/node-disk.md |
| PVC Filling Up | `PersistentVolumeFillingUp` | P3 | runbooks/pvc-capacity.md |
| Secret Sync Failed | `ExternalSecretSyncFailed` | P2 | runbooks/secret-sync.md |
| Certificate Expiring | `CertificateExpiringSoon` | P3 | runbooks/cert-renewal.md |
| Prometheus Target Down | `PrometheusTargetDown` | P3 | runbooks/prometheus-target.md |
| Alertmanager Unreachable | `AlertmanagerUnreachable` | P1 | runbooks/alertmanager.md |
| Ingress High Error Rate | `IngressHighErrorRate` | P2 | runbooks/ingress-errors.md |
| GPU Node Unhealthy | `GPUNodeUnhealthy` | P2 | runbooks/gpu-troubleshooting.md |
| Karpenter Provisioning Failed | `KarpenterProvisioningFailed` | P2 | runbooks/karpenter.md |
| ArgoCD Sync Failed | `ArgoSyncFailed` | P3 | runbooks/argocd-sync.md |
| Cluster Upgrade | Scheduled | N/A | runbooks/cluster-upgrade.md |
| DR Failover | Region failure | P1 | runbooks/dr-failover.md |

### 15.7 Appendix D: Configuration File Locations

| Configuration | Format | Location | Managed By |
|---------------|--------|----------|------------|
| Terraform variables (dev) | HCL | `terraform/environments/development/terraform.tfvars` | Git |
| Terraform variables (staging) | HCL | `terraform/environments/staging/terraform.tfvars` | Git |
| Terraform variables (prod) | HCL | `terraform/environments/production/terraform.tfvars` | Git |
| Terraform state | JSON | `s3://terraform-state-{env}/terraform.tfstate` | Terraform |
| Cilium values | YAML | `helm/infrastructure/cilium/values.yaml` | ArgoCD |
| Prometheus values | YAML | `helm/infrastructure/prometheus/values.yaml` | ArgoCD |
| ArgoCD App of Apps | YAML | `manifests/argocd/infrastructure-root.yaml` | ArgoCD |
| Karpenter NodePools | YAML | `manifests/karpenter/*.yaml` | ArgoCD |
| NetworkPolicies | YAML | `manifests/network-policies/*.yaml` | ArgoCD |
| Alertmanager config | YAML | `helm/infrastructure/prometheus/alertmanager.yaml` | ArgoCD |

### 15.8 Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.2.0 | 2025-01-04 | Infrastructure Team | **Industry Standards Alignment** - Integrated 11 enhancements from D.3 Industry Validation: 2 P1 (Supply Chain Security/SLSA, kube-bench DaemonSet), 7 P2 (Bottlerocket OS, PriorityClasses, Spot interruption SQS, EKS Pod Identity, OTel Operator, ArgoCD notifications, budget alerts), 2 P3 (Savings Plans, analysis runs). 6 items deferred to future versions. |
| 1.1.0 | 2025-01-04 | Infrastructure Team | **Validation Fixes** - Applied 11 fixes from self-validation. |
| 1.0.0 | 2025-01-04 | Infrastructure Team | **Initial Release** - Complete specification across all 15 sections. |

---

## Document Complete

This completes the Infrastructure Layer (L00) Specification v1.2.0.

**Industry Validation Summary:**

| Priority | Total | Integrated | Deferred |
|----------|-------|------------|----------|
| P1 (Mandatory) | 2 | 2 | 0 |
| P2 (Recommended) | 7 | 7 | 0 |
| P3 (Future) | 8 | 2 | 6 |
| **Total** | **17** | **11** | **6** |

**Standards Compliance Achieved:**

- CIS Kubernetes Benchmark: Full (automated scanning)
- NIST 800-190: Full (container security)
- SLSA Framework: Level 2 (supply chain)
- AWS Well-Architected: Full (all pillars)
- OpenTelemetry: Full (with Operator option)
- GitOps Principles: Full (with notifications)
- FinOps: Partial (advanced showback deferred)

**Validation Checklist:**

- [x] All 15 sections complete per template
- [x] ASCII encoding verified (no Unicode)
- [x] All components have interface definitions
- [x] All failure modes have error codes (E0XXX format)
- [x] Kubernetes manifests are valid YAML
- [x] Terraform examples are syntactically correct
- [x] Data Layer integration points documented
- [x] All open questions (Q1-Q3) resolved
- [x] Industry standards alignment verified
- [x] All P1 items integrated
- [x] P2/P3 deferrals documented with rationale
- [x] Version history updated

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.2.0 | 2025-01-04 | Infrastructure Team | **Industry Standards Alignment** - Integrated 11 enhancements from D.3 Industry Validation: 2 P1 (Supply Chain Security with SLSA Level 2, kube-bench automated compliance), 7 P2 (Bottlerocket node OS, PriorityClasses, Spot interruption SQS handling, EKS Pod Identity, OpenTelemetry Operator, ArgoCD notifications, namespace budget alerts), 2 P3 (Savings Plans guidance, analysis runs). 6 P3 items deferred to v1.3/v2.0 with rationale. |
| 1.1.0 | 2025-01-04 | Infrastructure Team | **Validation Fixes** - Applied 11 fixes from self-validation: 2 High (Unicode encoding, duplicate merge artifacts), 4 Medium (E0207 error code, Gatekeeper compatibility, RuntimeClass for gVisor, NGINX rate limiting), 5 Low (TOC corrections, KEDA TriggerAuthentication, cert-manager version, reserved error codes). |
| 1.0.0 | 2025-01-04 | Infrastructure Team | **Initial Release** - Complete specification across all 15 sections. Merged from three parts: Part 1 (Sections 1-5), Part 2 (Sections 6-10), Part 3 (Sections 11-15). Includes comprehensive coverage of container orchestration, compute management, networking, secrets, service discovery, and observability. |
| 0.3.0 | 2025-01-04 | Infrastructure Team | Part 3 (Sections 11-15): Implementation Guide, Testing Strategy, Migration and Deployment, Open Questions, References |
| 0.2.0 | 2025-01-04 | Infrastructure Team | Part 2 (Sections 6-10): Integration with Data Layer, Reliability and Scalability, Security, Observability, Configuration |
| 0.1.0 | 2025-01-04 | Infrastructure Team | Part 1 (Sections 1-5): Executive Summary, Scope Definition, Architecture, Interfaces, Data Model |

---

**Document Status:** Final (Industry Validated)  
**Validation Level:** Self-validated + Industry-validated  
**Next Review:** Upon integration feedback from dependent layers (L01-L11)  
**Change Management:** All modifications require gap analysis against Data Layer (L01) v3.2.1 patterns

---

*End of Infrastructure Layer Specification v1.2.0*

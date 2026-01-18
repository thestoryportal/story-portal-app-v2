# Audit Agent Catalog

## Overview

This package contains 25 specialized audit agents organized into 7 phases.

---

## Phase 0: Infrastructure Discovery

| Agent ID | Name | Purpose | Checks |
|----------|------|---------|--------|
| AUD-019 | Docker/Container | Container configuration, resources, images | ~25 |
| AUD-020 | LLM/Model Inventory | Ollama models, GPU, inference config | ~20 |
| AUD-021 | PostgreSQL Deep | DB config, extensions, migrations | ~25 |

---

## Phase 1: Service Discovery

| Agent ID | Name | Purpose | Checks |
|----------|------|---------|--------|
| AUD-010 | Service Health | Port scanning, health endpoints | ~20 |
| AUD-011 | CLI Tooling | Layer CLI maturity assessment | ~15 |
| AUD-012 | MCP Services | PM2, tool registration | ~15 |
| AUD-013 | Configuration | Env files, config validation | ~20 |

---

## Phase 2: Security & Compliance

| Agent ID | Name | Purpose | Checks |
|----------|------|---------|--------|
| AUD-002 | Security | Auth, authz, input validation | ~50 |
| AUD-014 | Token Management | JWT, API keys, sessions | ~15 |
| AUD-023 | Network/TLS | Certificates, encryption | ~15 |
| AUD-024 | Backup/Recovery | Backup scripts, restore capability | ~15 |

---

## Phase 3: Data & State

| Agent ID | Name | Purpose | Checks |
|----------|------|---------|--------|
| AUD-004 | Database Schema | Tables, indexes, constraints | ~30 |
| AUD-015 | Redis State | Keys, TTLs, pub/sub | ~15 |
| AUD-017 | Event Flow | Event sourcing, CQRS | ~20 |

---

## Phase 4: Integration & API

| Agent ID | Name | Purpose | Checks |
|----------|------|---------|--------|
| AUD-005 | Integration | Cross-layer communication | ~35 |
| AUD-016 | API Endpoints | Route validation, OpenAPI | ~80 |
| AUD-018 | Error Handling | Exception patterns, codes | ~20 |
| AUD-022 | Observability | Metrics, logging, tracing | ~20 |
| AUD-025 | External Dependencies | Third-party APIs, CI/CD | ~15 |

---

## Phase 5: Quality & Experience

| Agent ID | Name | Purpose | Checks |
|----------|------|---------|--------|
| AUD-003 | QA/Test Coverage | Test files, coverage config | ~40 |
| AUD-006 | Performance | Async patterns, pooling, caching | ~25 |
| AUD-007 | Code Quality | Type hints, docstrings, complexity | ~40 |
| AUD-008 | UI/UX | Frontend, accessibility | ~30 |
| AUD-009 | DevEx | Documentation, onboarding | ~25 |

---

## Phase 6: Consolidation

| Agent ID | Name | Purpose | Output |
|----------|------|---------|--------|
| AUD-001 | Orchestrator | Consolidate all findings | V2-SPECIFICATION-INPUTS.md |

---

## Total

| Metric | Value |
|--------|-------|
| Total Agents | 25 |
| Total Checks | ~595 |
| Estimated Duration | 4-6 hours |

---

## Agent Output Format

Each agent produces:

1. **Findings file** (`./audit/findings/AUD-XXX-*.md`)
   - Raw audit data
   - Command outputs
   - Structured observations

2. **Report file** (`./audit/reports/AUD-XXX-*.md`)
   - Analysis of findings
   - Severity classifications
   - Recommendations

---

## Severity Definitions

| Severity | Definition | Response Time |
|----------|------------|---------------|
| Critical | Blocks production deployment, security vulnerability | Immediate |
| High | Significant gap affecting reliability or security | Week 1 |
| Medium | Missing best practice, technical debt | Week 2-4 |
| Low | Enhancement opportunity, polish | Backlog |

---

## Priority Matrix

| Priority | Criteria |
|----------|----------|
| P1 | Security + Critical severity |
| P2 | Reliability + High severity |
| P3 | Functionality + Medium severity |
| P4 | Enhancement + Low severity |

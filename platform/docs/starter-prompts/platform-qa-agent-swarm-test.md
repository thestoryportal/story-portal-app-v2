Deploy QA Agent Swarm for Platform Assessment.

MISSION CONSTRAINT

All agents operate in READ-ONLY assessment mode.
NO agent may modify code, configuration, or data.
All agents produce REPORTS ONLY with findings, recommendations, and plans.

ENVIRONMENT

Platform Base: /Volumes/Extreme SSD/projects/story-portal-app/platform
L01 Data Layer: http://localhost:8002
L09 API Gateway: http://localhost:8000
L10 Dashboard: http://localhost:8001
L11 Integration: Running
API Key: test-key-12345678901234567890123456789012

AGENT SWARM SPECIFICATION

Deploy 8 specialized agents via L09 API.

Agent Roster:

| Agent ID | Name | Specialization | Assessment Target |
|----------|------|----------------|-------------------|
| QA-001 | qa-orchestrator | Campaign Coordinator | All agents, aggregate findings |
| QA-002 | api-tester | API Quality | L09 endpoints, error handling |
| QA-003 | integration-analyst | Layer Communication | L01-L11 data flows |
| QA-004 | ui-ux-assessor | Human Interface | L10 dashboard usability |
| QA-005 | db-analyst | Data Integrity | L01 schema, queries, performance |
| QA-006 | security-auditor | Security Posture | Auth, validation, injection risks |
| QA-007 | dx-evaluator | Developer Experience | Code structure, documentation, APIs |
| QA-008 | performance-analyst | System Performance | Latency, throughput, resource usage |

PHASE 1: DEPLOY AGENTS

Create each agent via L09 API:

for each agent in roster:
    POST http://localhost:8000/api/v1/agents
    Headers:
        X-API-Key: test-key-12345678901234567890123456789012
        Content-Type: application/json
    Body:
        {
            "name": "{agent.name}",
            "agent_type": "qa_assessor",
            "configuration": {
                "specialization": "{agent.specialization}",
                "mode": "read_only",
                "output": "report_only",
                "target": "{agent.target}"
            },
            "metadata": {
                "swarm_id": "qa-swarm-001",
                "deployed_at": "{timestamp}"
            }
        }

Verify deployment:
    GET http://localhost:8000/api/v1/agents
    Expected: 8 agents with status "created"

PHASE 2: ASSIGN ASSESSMENT GOALS

Goal: QA-001 Orchestrator

POST http://localhost:8000/api/v1/goals
{
    "agent_id": "{qa-orchestrator-id}",
    "description": "Coordinate platform QA assessment campaign",
    "success_criteria": [
        "All specialist agents complete assessments",
        "Findings aggregated into master report",
        "Recommendations prioritized by severity",
        "Implementation roadmap produced"
    ],
    "priority": 1
}

Goal: QA-002 API Tester

POST http://localhost:8000/api/v1/goals
{
    "agent_id": "{api-tester-id}",
    "description": "Assess L09 API Gateway quality and completeness",
    "success_criteria": [
        "All endpoints tested for correct responses",
        "Error handling validated for edge cases",
        "Rate limiting behavior verified",
        "Authentication flows tested",
        "Response format consistency checked"
    ],
    "priority": 2
}

Goal: QA-003 Integration Analyst

POST http://localhost:8000/api/v1/goals
{
    "agent_id": "{integration-analyst-id}",
    "description": "Assess layer-to-layer communication integrity",
    "success_criteria": [
        "L01 event propagation verified",
        "All layer integrations with L01 tested",
        "Event subscription mechanisms validated",
        "Data consistency across layers verified",
        "Circuit breaker behavior assessed"
    ],
    "priority": 2
}

Goal: QA-004 UI/UX Assessor

POST http://localhost:8000/api/v1/goals
{
    "agent_id": "{ui-ux-assessor-id}",
    "description": "Assess L10 dashboard usability and completeness",
    "success_criteria": [
        "Dashboard layout and navigation evaluated",
        "Real-time update functionality verified",
        "Data visualization clarity assessed",
        "User workflow efficiency analyzed",
        "Accessibility compliance checked",
        "Missing features identified"
    ],
    "priority": 2
}

Goal: QA-005 Database Analyst

POST http://localhost:8000/api/v1/goals
{
    "agent_id": "{db-analyst-id}",
    "description": "Assess L01 database schema and data integrity",
    "success_criteria": [
        "Schema design evaluated against spec",
        "Index coverage analyzed",
        "Query performance profiled",
        "Foreign key integrity verified",
        "Data type appropriateness assessed",
        "Migration readiness evaluated"
    ],
    "priority": 2
}

Goal: QA-006 Security Auditor

POST http://localhost:8000/api/v1/goals
{
    "agent_id": "{security-auditor-id}",
    "description": "Assess platform security posture",
    "success_criteria": [
        "Authentication mechanisms evaluated",
        "Authorization controls tested",
        "Input validation coverage assessed",
        "SQL injection risks identified",
        "XSS vulnerability scan completed",
        "Secrets management reviewed",
        "OWASP Top 10 checklist applied"
    ],
    "priority": 1
}

Goal: QA-007 Developer Experience Evaluator

POST http://localhost:8000/api/v1/goals
{
    "agent_id": "{dx-evaluator-id}",
    "description": "Assess developer experience and code quality",
    "success_criteria": [
        "Code structure consistency evaluated",
        "Documentation completeness assessed",
        "API discoverability rated",
        "Error message clarity reviewed",
        "Logging adequacy checked",
        "Testing coverage analyzed",
        "Onboarding friction identified"
    ],
    "priority": 3
}

Goal: QA-008 Performance Analyst

POST http://localhost:8000/api/v1/goals
{
    "agent_id": "{performance-analyst-id}",
    "description": "Assess platform performance characteristics",
    "success_criteria": [
        "Endpoint latency profiled",
        "Concurrent request handling tested",
        "Database query performance measured",
        "Memory usage patterns analyzed",
        "WebSocket scalability assessed",
        "Bottlenecks identified"
    ],
    "priority": 2
}

PHASE 3: EXECUTE ASSESSMENTS

Each agent executes its assessment goal using available tools:

API Tester Tools:
- HTTP client for endpoint testing
- Response validator
- Schema comparator

Integration Analyst Tools:
- Event subscriber
- Data flow tracer
- Service health checker

UI/UX Assessor Tools:
- HTTP client for dashboard endpoints
- WebSocket client
- Accessibility checker

Database Analyst Tools:
- SQL query executor (SELECT only)
- EXPLAIN ANALYZE runner
- Schema inspector

Security Auditor Tools:
- Input fuzzer (read-only)
- Auth bypass tester
- Header analyzer

DX Evaluator Tools:
- File system reader
- Documentation scanner
- Test coverage reporter

Performance Analyst Tools:
- Load generator (controlled)
- Latency measurer
- Resource monitor

PHASE 4: REPORT GENERATION

Each agent produces a structured report.

Report Schema:

{
    "report_id": "uuid",
    "agent_id": "agent-uuid",
    "agent_name": "string",
    "specialization": "string",
    "assessment_target": "string",
    "timestamp": "iso-datetime",
    "executive_summary": "string",
    "findings": [
        {
            "id": "F-001",
            "severity": "critical|high|medium|low|info",
            "category": "string",
            "title": "string",
            "description": "string",
            "evidence": "string",
            "location": "string",
            "recommendation": "string",
            "effort_estimate": "S|M|L|XL"
        }
    ],
    "metrics": {
        "items_assessed": 0,
        "issues_found": 0,
        "critical_count": 0,
        "high_count": 0,
        "medium_count": 0,
        "low_count": 0
    },
    "recommendations": [
        {
            "id": "R-001",
            "priority": 1,
            "title": "string",
            "description": "string",
            "rationale": "string",
            "implementation_plan": "string",
            "dependencies": ["R-002"],
            "effort_estimate": "S|M|L|XL"
        }
    ],
    "implementation_roadmap": {
        "phase_1": ["R-001", "R-002"],
        "phase_2": ["R-003"],
        "phase_3": ["R-004", "R-005"]
    }
}

Report Output Location:

/mnt/user-data/outputs/qa-reports/
    qa-001-orchestrator-master-report.md
    qa-002-api-tester-report.md
    qa-003-integration-analyst-report.md
    qa-004-ui-ux-assessor-report.md
    qa-005-db-analyst-report.md
    qa-006-security-auditor-report.md
    qa-007-dx-evaluator-report.md
    qa-008-performance-analyst-report.md

PHASE 5: AGGREGATE FINDINGS

QA-001 Orchestrator aggregates all reports into master assessment:

Master Report Structure:

# Agentic AI Workforce Platform Assessment

## Executive Summary
- Overall platform health score
- Critical issues requiring immediate attention
- Top 5 recommendations

## Assessment Coverage
| Agent | Target | Findings | Critical | High | Medium |
|-------|--------|----------|----------|------|--------|

## Consolidated Findings by Severity

### Critical
[All critical findings from all agents]

### High
[All high findings]

### Medium
[All medium findings]

## Consolidated Recommendations

### Immediate (Week 1)
[Priority 1 recommendations]

### Short-term (Weeks 2-4)
[Priority 2 recommendations]

### Medium-term (Months 2-3)
[Priority 3 recommendations]

## Implementation Roadmap

### Phase 1: Stabilization
- Fix critical issues
- Estimated effort: X hours

### Phase 2: Enhancement
- Address high-priority improvements
- Estimated effort: X hours

### Phase 3: Optimization
- Implement medium-priority items
- Estimated effort: X hours

## Appendices
- Full findings by agent
- Test evidence
- Metrics collected

MONITORING

During execution, observe via L10 Dashboard:

http://localhost:8001

Monitor:
- Agent status transitions
- Goal progress
- Event stream activity
- Task execution
- Report generation events

EXECUTION COMMAND

Run this assessment via Claude CLI:

cd "/Volumes/Extreme SSD/projects/story-portal-app/platform"
claude

Then execute this prompt to deploy and run the swarm.

VERIFICATION CHECKPOINTS

Checkpoint 1: Agents Deployed
- 8 agents visible in L10 dashboard
- All agents in "created" status
- Events logged in L01

Checkpoint 2: Goals Assigned
- 8 goals created and linked
- Orchestrator goal has highest priority
- All agents transition to "running"

Checkpoint 3: Assessments Running
- Events show assessment activity
- Tools being invoked
- Intermediate findings logged

Checkpoint 4: Reports Generated
- 8 individual reports in output directory
- Master report aggregated
- All findings categorized

Checkpoint 5: Campaign Complete
- All agents return to "idle"
- Dashboard shows completion
- Reports available for review

SUCCESS CRITERIA

- All 8 agents deploy successfully
- All 8 assessments complete
- All 8 reports generated
- Master report aggregates all findings
- No agents modified any code or data
- Platform remained stable during assessment
- Findings are actionable and prioritized

OUTPUT ARTIFACTS

1. /mnt/user-data/outputs/qa-reports/*.md (8 individual reports)
2. /mnt/user-data/outputs/qa-reports/master-assessment.md (aggregated)
3. /mnt/user-data/outputs/qa-reports/implementation-roadmap.md (prioritized plan)

Begin swarm deployment and assessment execution.
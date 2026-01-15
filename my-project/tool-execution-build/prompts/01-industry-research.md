**Settings:** Web Search **ON**, Research OFF

# Session: Tool Execution Layer -- Industry Research

## Objective
Research how existing frameworks and platforms implement tool execution, registry patterns, and external API management functionality.

## Context
The Tool Execution Layer (L03) provides a secure, isolated environment for agent tool invocations, maintaining a registry of available tools with capability manifests and enforcing tool-level permissions. It acts as the boundary between agent intent and external system access.

**Key Architectural Constraint (BC-1):** Tool sandboxes are nested within agent sandboxes owned by L02 (Agent Runtime). L03 owns tool-specific isolation but operates within the security boundary established by L02.

**Key Interface (BC-2):** L03 provides `tool.invoke()` consumed by L11 (Integration Layer).

**Infrastructure Context (ADR-002):** PostgreSQL 16 + pgvector for registry, Redis 7 for state/caching, Ollama for local inference, PM2 for MCP service management.

## Checkpoint Protocol

**Exchange limit:** 10 exchanges for this session

**Checkpoint triggers:**
- After each research category (8 categories total)
- When context estimate exceeds 60%

**At each checkpoint:**
1. Save completed findings to file
2. Report: [X] categories complete, [Y] remaining
3. PAUSE - wait for "Continue"

## Research Questions

### Category 1: Tool Registry Patterns
1. How do LangChain, LangGraph, and CrewAI implement tool registries?
2. What patterns exist for tool capability manifests (inputs, outputs, side effects)?
3. How does Model Context Protocol (MCP) define tool discovery and invocation?
4. How do OpenAI function calling and Anthropic tool use define tool schemas?


---

### Category 2: Tool Execution Sandboxing
5. How do Firecracker, gVisor, and nsjail implement nested isolation?
6. What patterns exist for tool-specific network restrictions within broader sandboxes?
7. How do serverless platforms (Lambda, Cloud Functions) implement function isolation?
8. How do platforms handle tool execution timeout enforcement?


---

### Category 3: External API Management
9. How do API gateway patterns handle authentication rotation and refresh?
10. What patterns exist for external API rate limiting and quota management?
11. How do platforms implement retry logic with exponential backoff for external calls?
12. How is credential injection handled securely for tool execution?


---

### Category 4: Circuit Breaker Patterns
13. How do Resilience4j and Polly implement circuit breaker state machines?
14. What patterns exist for health-based circuit decisions vs failure-count?
15. How do platforms handle partial degradation (some external APIs healthy, some not)?
16. What recovery patterns exist for circuit breaker half-open states?


---

### Category 5: Security and Permissions
17. How do capability-based security models apply to tool invocation?
18. What patterns exist for tool-level RBAC/ABAC in agent systems?
19. How do platforms audit tool invocations for compliance?
20. What patterns prevent tool invocations from escalating agent privileges?


---

### Category 6: Emerging Standards
21. What emerging standards exist for agent tool interoperability (MCP, A2A)?
22. How do workflow platforms (n8n, Temporal) implement action/tool execution?
23. What patterns exist for tool versioning and backward compatibility?
24. How do platforms handle tools requiring human approval (HITL integration)?


---

### Category 7: MCP Integration Patterns
25. How do MCP servers expose tools to AI agents via stdio transport?
26. What patterns exist for MCP tool discovery and capability negotiation?
27. How do MCP clients handle tool state persistence across invocations?
28. What error handling patterns exist for MCP JSON-RPC communication?


---

### Category 8: Tool State and Checkpointing
29. What patterns exist for tool state checkpointing during long-running operations?
30. How do agents access documents during tool execution (context injection)?
31. How do platforms handle tool execution resume after failure?
32. What patterns exist for distributed checkpoint storage (Redis vs PostgreSQL)?

## Web Search Guidance
Search for:
- "LangChain tool registry architecture"
- "Model Context Protocol MCP tool specification"
- "agent tool execution sandbox isolation patterns"
- "circuit breaker pattern distributed systems"
- "API gateway credential rotation patterns"
- "capability-based security agent systems"
- "MCP stdio transport tool integration"
- "long-running task checkpointing patterns"

## Output Format
For each finding:

### Finding: [Descriptive Name]

**Source:** [Platform/Project/Paper/Blog]
**Category:** Pattern / Technology / Standard / Practice
**Component:** [Which layer component this applies to]

**Description:**
[2-3 sentences explaining the finding]

**Relevance to Tool Execution Layer:**
[How this applies to our specification]

**Integration Considerations:**
[Any implications for Data Layer, Agent Runtime, Phase 15/16, or other layers]

**Priority:** Critical / High / Medium / Low

## Deliverable
Output as: `tool-execution-research-findings.md`

Structure:
- Executive Summary (3-5 key takeaways)
- Findings by Component
- Technology Recommendations
- MCP Integration Patterns
- Checkpointing Patterns
- Standards to Reference
- Next Steps

## KB Management

### Add to This Project KB
| File | Purpose |
|------|---------|
| `tool-execution-research-findings.md` | Industry research for gap analysis |

### Verification
- [ ] All 8 research categories covered
- [ ] MCP integration patterns documented
- [ ] Checkpointing patterns documented
- [ ] Findings have clear priorities
- [ ] File added to KB before B.2

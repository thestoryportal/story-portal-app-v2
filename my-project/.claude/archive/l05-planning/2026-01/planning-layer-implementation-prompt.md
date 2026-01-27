Implement L05 Planning Layer: Autonomous end-to-end sprint.

## CRITICAL ENVIRONMENT CONSTRAINTS

READ THESE FIRST - DO NOT VIOLATE:

1. DO NOT create docker-compose files - infrastructure ALREADY RUNNING
2. DO NOT create virtual environments (venv) - use system Python
3. DO NOT run docker-compose up - services ALREADY RUNNING
4. ALWAYS use: pip install <package> --break-system-packages
5. CORRECT directory: /Volumes/Extreme SSD/projects/story-portal-app/platform/src/L05_planning/

## Running Infrastructure (DO NOT RECREATE)

| Service | Host | Port | Container/Process |
|---------|------|------|-------------------|
| PostgreSQL | localhost | 5432 | agentic-postgres |
| Redis | localhost | 6379 | agentic-redis |
| Ollama | localhost | 11434 | native process |

Verify with: docker ps | grep agentic

## Specification

Location: /Volumes/Extreme SSD/projects/story-portal-app/platform/specs/planning-layer-specification-v1.2-final-ASCII.md

Read specification Sections 3 (Architecture) and 12 (Implementation Guide) first.

## Completed Layers (Available for Integration)

| Layer | Location | Key Integration |
|-------|----------|-----------------|
| L02 Agent Runtime | platform/src/L02_runtime/ | Task execution dispatch |
| L03 Tool Execution | platform/src/L03_tool_execution/ | Tool references in tasks |
| L04 Model Gateway | platform/src/L04_model_gateway/ | LLM-based goal decomposition |

## Output Location

/Volumes/Extreme SSD/projects/story-portal-app/platform/src/L05_planning/

## Directory Structure

Create these directories and files:

Root: platform/src/L05_planning/
  - __init__.py
  - PROGRESS.md
  - README.md

Subdirectory: platform/src/L05_planning/models/
  - __init__.py
  - goal.py (Goal, GoalType, GoalStatus)
  - task.py (Task, TaskStatus, TaskDependency)
  - plan.py (ExecutionPlan, PlanStatus, PlanMetadata)
  - context.py (ExecutionContext, ContextScope)
  - resource.py (ResourceEstimate, ResourceConstraints)
  - agent.py (AgentCapability, AgentAssignment)
  - error_codes.py (E5000-E5999)

Subdirectory: platform/src/L05_planning/services/
  - __init__.py
  - goal_decomposer.py (LLM and rule-based decomposition)
  - dependency_resolver.py (DAG analysis, cycle detection)
  - task_orchestrator.py (Task state machine, sequencing)
  - context_injector.py (Input binding, secret resolution)
  - resource_estimator.py (CPU, memory, token estimation)
  - plan_validator.py (Syntax, semantic, feasibility checks)
  - agent_assigner.py (Capability matching, load balancing)
  - plan_cache.py (Two-level cache: L1 memory, L2 Redis)
  - execution_monitor.py (Task completion, failure detection)
  - planning_service.py (Main orchestrator)

Subdirectory: platform/src/L05_planning/strategies/
  - __init__.py
  - decomposition_strategies.py (LLM, template, hybrid)
  - routing_strategies.py (Round-robin, capability, load-based)

Subdirectory: platform/src/L05_planning/templates/
  - __init__.py
  - template_registry.py (Predefined decomposition patterns)
  - common_templates.py (File processing, data pipeline, etc.)

Subdirectory: platform/src/L05_planning/tests/
  - __init__.py
  - conftest.py
  - test_models.py
  - test_goal_decomposer.py
  - test_dependency_resolver.py
  - test_task_orchestrator.py
  - test_plan_validator.py
  - test_integration.py

## Implementation Phases

Execute in order per spec Section 12:

### Phase 1: Foundation (Models)

Create data models per spec Section 5.

Goal model:
  - goal_id: str (UUID)
  - agent_did: str (requesting agent)
  - goal_text: str (natural language or structured)
  - goal_type: GoalType (SIMPLE, COMPOUND, RECURSIVE)
  - priority: int (1-10)
  - constraints: GoalConstraints
  - status: GoalStatus (PENDING, DECOMPOSING, READY, FAILED)
  - created_at: datetime
  - metadata: dict

Task model:
  - task_id: str (UUID)
  - plan_id: str (parent plan)
  - name: str
  - description: str
  - task_type: TaskType (ATOMIC, COMPOUND, TOOL_CALL, LLM_CALL)
  - status: TaskStatus (PENDING, READY, EXECUTING, COMPLETED, FAILED, BLOCKED)
  - dependencies: list[TaskDependency]
  - inputs: dict
  - outputs: dict
  - assigned_agent: str | None
  - resource_estimate: ResourceEstimate
  - timeout_seconds: int
  - retry_policy: RetryPolicy

ExecutionPlan model:
  - plan_id: str (UUID)
  - goal_id: str (source goal)
  - tasks: list[Task]
  - dependency_graph: dict (adjacency list)
  - status: PlanStatus (DRAFT, VALIDATED, EXECUTING, COMPLETED, FAILED)
  - resource_budget: ResourceConstraints
  - created_at: datetime
  - validated_at: datetime | None
  - execution_started_at: datetime | None
  - signature: str (plan integrity)

Error codes E5000-E5999 per spec Appendix B.

### Phase 2: Goal Decomposer

Build goal decomposition with two strategies:

LLM-based decomposition:
  - Use L04 Model Gateway for inference
  - Structured output parsing
  - Recursive decomposition for complex goals

Rule-based decomposition:
  - Template matching
  - Predefined patterns for common goal types
  - Lower latency, no LLM cost

Decomposer interface:
  async def decompose(goal: Goal) -> ExecutionPlan:
      # 1. Check plan cache
      # 2. Try template matching
      # 3. Fall back to LLM decomposition
      # 4. Build task graph
      # 5. Cache result
      # 6. Return plan

L04 integration:
  from src.L04_model_gateway.services.model_gateway import ModelGateway
  
  async def llm_decompose(self, goal: Goal) -> list[Task]:
      request = InferenceRequest(
          request_id=str(uuid4()),
          agent_did=goal.agent_did,
          logical_prompt=LogicalPrompt(
              system="You are a task planning assistant...",
              user=f"Decompose this goal into tasks: {goal.goal_text}"
          ),
          requirements=ModelRequirements(capabilities=["tool_use"])
      )
      response = await self.gateway.complete(request)
      return self._parse_tasks(response.content)

### Phase 3: Dependency Resolver

Build DAG analysis per spec Section 3:

Dependency types:
  - BLOCKING: Task B cannot start until Task A completes
  - CONDITIONAL: Task B starts only if Task A succeeds with condition
  - DATA: Task B needs output from Task A

Key algorithms:
  - Topological sort for execution order
  - Cycle detection (Kahn's algorithm or DFS)
  - Critical path analysis

Interface:
  def resolve(tasks: list[Task]) -> DependencyGraph:
      # 1. Build adjacency list
      # 2. Detect cycles (error E5301 if found)
      # 3. Compute topological order
      # 4. Identify parallelizable tasks
      # 5. Return resolved graph

  def get_ready_tasks(graph: DependencyGraph, completed: set[str]) -> list[Task]:
      # Return tasks with all dependencies satisfied

### Phase 4: Task Orchestrator

Implement task state machine per spec Section 3:

States: PENDING -> READY -> EXECUTING -> COMPLETED | FAILED | BLOCKED

Transitions:
  - PENDING -> READY: All dependencies satisfied
  - READY -> EXECUTING: Dispatched to L02
  - EXECUTING -> COMPLETED: Success response
  - EXECUTING -> FAILED: Error or timeout
  - READY -> BLOCKED: Dependency failed

Orchestrator interface:
  async def execute_plan(plan: ExecutionPlan) -> PlanResult:
      # 1. Validate plan
      # 2. Initialize task states
      # 3. Execute ready tasks (parallel where possible)
      # 4. Monitor completions
      # 5. Propagate outputs to dependent tasks
      # 6. Handle failures (retry or abort)
      # 7. Return final result

L02 integration for task dispatch:
  from src.L02_runtime.services.agent_executor import AgentExecutor
  
  async def dispatch_task(task: Task) -> TaskResult:
      # Send task to L02 for execution

### Phase 5: Context Injector

Build context preparation per spec Section 3:

Responsibilities:
  - Resolve input references from prior task outputs
  - Bind secrets (via L00/Vault reference)
  - Inject domain context
  - Enforce access controls (RBAC)

Interface:
  async def inject_context(task: Task, plan: ExecutionPlan) -> ExecutionContext:
      # 1. Resolve input bindings
      # 2. Fetch secrets (masked references)
      # 3. Build scope (agent permissions)
      # 4. Validate access
      # 5. Return context

### Phase 6: Resource Estimator and Plan Validator

Resource estimation:
  - Token count estimation for LLM tasks
  - CPU/memory estimates based on task type
  - Execution time prediction

Plan validation (three levels):
  1. Syntax validation: Task format, field types
  2. Semantic validation: All tasks executable, inputs available
  3. Feasibility validation: Resources available, within budget

Validator interface:
  async def validate(plan: ExecutionPlan) -> ValidationResult:
      errors = []
      errors.extend(self._validate_syntax(plan))
      errors.extend(self._validate_semantics(plan))
      errors.extend(await self._validate_feasibility(plan))
      return ValidationResult(valid=len(errors) == 0, errors=errors)

### Phase 7: Agent Assigner and Plan Cache

Agent assignment:
  - Match task requirements to agent capabilities
  - Load balancing across available agents
  - Affinity rules (prefer same agent for related tasks)

Interface:
  async def assign(task: Task, available_agents: list[Agent]) -> AgentAssignment:
      # 1. Filter by capability
      # 2. Filter by availability
      # 3. Score by load and affinity
      # 4. Return best match

Plan cache (two-level):
  - L1: In-memory LRU cache (hot plans)
  - L2: Redis cache (warm plans)
  - Cache key: Hash of normalized goal text
  - TTL: Configurable (default 1 hour)

### Phase 8: Execution Monitor and Main Service

Execution monitor:
  - Track task completion events
  - Detect failures and timeouts
  - Trigger retries or escalation
  - Emit plan-level events

Main PlanningService:
  class PlanningService:
      def __init__(
          self,
          decomposer: GoalDecomposer,
          resolver: DependencyResolver,
          orchestrator: TaskOrchestrator,
          validator: PlanValidator,
          cache: PlanCache,
          gateway: ModelGateway  # L04 integration
      ): ...
      
      async def create_plan(self, goal: Goal) -> ExecutionPlan:
          # 1. Validate goal input
          # 2. Check cache
          # 3. Decompose goal
          # 4. Resolve dependencies
          # 5. Validate plan
          # 6. Cache plan
          # 7. Return plan
      
      async def execute_plan(self, plan_id: str) -> PlanResult:
          # 1. Load plan
          # 2. Inject contexts
          # 3. Orchestrate execution
          # 4. Monitor progress
          # 5. Return result

### Phase 9: Observability and Hardening

Add metrics, logging, error handling:
  - Plan creation latency
  - Decomposition strategy usage (LLM vs template)
  - Task success/failure rates
  - Cache hit rates
  - Structured logging
  - E5xxx error codes
  - Input validation (goal text sanitization per spec Section 3)

## Error Code Range

L05 uses E5000-E5999:

| Range | Category |
|-------|----------|
| E5000-E5099 | Plan cache and retrieval |
| E5100-E5199 | Goal decomposition |
| E5200-E5299 | Task orchestration |
| E5300-E5399 | Dependency resolution |
| E5400-E5499 | Context management |
| E5500-E5599 | Resource planning |
| E5600-E5699 | Plan validation |
| E5700-E5799 | Execution monitoring |
| E5800-E5899 | Plan persistence |
| E5900-E5999 | Multi-agent coordination |

## Goal Input Validation (SECURITY)

Per spec Section 3, validate goal text:
  - Character whitelist: alphanumeric, spaces, basic punctuation
  - Reject shell metacharacters: < > | & ; $ backticks
  - Reject SQL keywords: DROP, DELETE, INSERT, UPDATE
  - Reject code patterns: eval(, __import__, exec(, <script>
  - Size limit: 100,000 characters max
  - Error: E5004 for invalid input

## Test Configuration

Create tests/conftest.py with:
  - Event loop fixture
  - Cleanup timeout fixture (2 second max)
  - Mock goal fixture
  - Mock plan fixture
  - Mock L04 gateway fixture

## Validation After Each Phase

Run after each phase:
  cd /Volumes/Extreme SSD/projects/story-portal-app/platform
  python3 -m py_compile $(find src/L05_planning -name "*.py")
  python3 -c "from src.L05_planning import *; print('OK')"

## Progress Logging

After each phase append to PROGRESS.md:
  Phase [N] complete: [components] - [timestamp]

## Final Validation

After all phases:
  1. Syntax check all files
  2. Import check main service
  3. Run test suite with 30 second timeout
  4. Test L04 integration (goal decomposition)

Integration test:
  python3 << 'EOF'
  import asyncio
  import sys
  sys.path.insert(0, '.')
  
  async def test():
      from src.L05_planning.services.planning_service import PlanningService
      from src.L05_planning.models.goal import Goal
      
      service = PlanningService()
      await service.initialize()
      
      goal = Goal(
          goal_id="test-1",
          agent_did="did:agent:test",
          goal_text="Create a summary of the project status"
      )
      
      plan = await service.create_plan(goal)
      print(f"Plan created: {plan.plan_id}")
      print(f"Tasks: {len(plan.tasks)}")
      
      await service.cleanup()
  
  asyncio.run(test())
  EOF

## Completion Criteria

Sprint complete when:
  - All 9 phases implemented
  - All files pass syntax validation
  - All imports resolve
  - Tests exist for each component
  - Tests pass with no hangs
  - L04 integration works (LLM decomposition)
  - PROGRESS.md shows all phases complete

## Error Handling

If blocked:
  1. Log blocker to PROGRESS.md
  2. Stub the problematic component with TODO
  3. Continue to next phase
  4. Do not stop the sprint

## Final Steps

1. Create completion summary in PROGRESS.md
2. Stage files: git add platform/src/L05_planning/
3. Do NOT commit - await human review

## REMINDERS

- NO docker-compose
- NO venv
- Use --break-system-packages for pip
- Infrastructure ALREADY RUNNING
- Use L04 Model Gateway for LLM calls
- Follow L02/L03/L04 patterns
- Sanitize goal input (security)

## Begin

Read the specification. Execute all phases. Log progress. Complete end-to-end.
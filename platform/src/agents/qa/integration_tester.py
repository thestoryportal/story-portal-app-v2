"""Integration Tester Agent - Validates layer-to-layer communication."""

from typing import Dict, List, Any
from dataclasses import dataclass, field


@dataclass
class IntegrationTester:
    """
    Tests integration between platform layers.

    Responsibilities:
    - Validate L02 Agent Runtime <-> L03 Tool Execution communication
    - Test L11 event propagation across layers
    - Verify L05 Orchestration <-> L02 Runtime coordination
    - Check L09 API Gateway <-> backend layer routing
    - Validate circuit breaker and retry behavior
    """

    name: str = "integration-tester"
    agent_type: str = "integration_tester"
    version: str = "1.0.0"

    configuration: Dict[str, Any] = field(default_factory=lambda: {
        "goal": "Validate layer-to-layer communication and event flow",
        "integration_points": [
            {
                "name": "L09 -> L02",
                "description": "API Gateway to Agent Runtime",
                "test_flow": "Create agent via API -> Verify runtime instantiation"
            },
            {
                "name": "L02 -> L03",
                "description": "Agent Runtime to Tool Execution",
                "test_flow": "Agent executes -> Tool called -> Result returned"
            },
            {
                "name": "L05 -> L02",
                "description": "Orchestration to Agent Runtime",
                "test_flow": "Workflow created -> Agents coordinated -> Tasks completed"
            },
            {
                "name": "L11 Event Flow",
                "description": "Cross-layer event propagation",
                "test_flow": "Event emitted -> Propagates through L11 -> Subscribers notified"
            },
            {
                "name": "L04 Model Gateway",
                "description": "Agent to LLM communication",
                "test_flow": "Agent requests inference -> L04 routes -> Response returned"
            }
        ],
        "resilience_tests": [
            "circuit_breaker_activation",
            "retry_with_backoff",
            "timeout_handling",
            "partial_failure_recovery"
        ],
        "event_tests": [
            "agent_created_event",
            "goal_assigned_event",
            "task_completed_event",
            "error_event",
            "state_change_event"
        ]
    })

    capabilities: List[str] = field(default_factory=lambda: [
        "integration_testing",
        "event_tracing",
        "circuit_breaker_validation",
        "async_flow_testing",
        "message_queue_validation"
    ])

    test_scenarios: List[Dict[str, Any]] = field(default_factory=lambda: [
        {
            "name": "End-to-End Agent Workflow",
            "description": "Complete agent lifecycle across all layers",
            "steps": [
                {
                    "layer": "L09",
                    "action": "POST /api/v1/agents",
                    "payload": {"name": "test-agent", "agent_type": "generic"},
                    "verify": "201 response with agent_id"
                },
                {
                    "layer": "L02",
                    "action": "Verify agent instantiated in runtime",
                    "verify": "Agent exists and is in 'idle' state"
                },
                {
                    "layer": "L11",
                    "action": "Check event stream",
                    "verify": "agent.created event published"
                },
                {
                    "layer": "L09",
                    "action": "POST /api/v1/goals",
                    "payload": {"agent_id": "{agent_id}", "description": "Execute test task"},
                    "verify": "201 response with goal_id"
                },
                {
                    "layer": "L05",
                    "action": "Verify orchestration picks up goal",
                    "verify": "Goal assigned to agent, plan created"
                },
                {
                    "layer": "L02",
                    "action": "Agent processes goal",
                    "verify": "Agent state changes to 'working'"
                },
                {
                    "layer": "L03",
                    "action": "Agent executes tools",
                    "verify": "Tools executed, results captured"
                },
                {
                    "layer": "L11",
                    "action": "Monitor event stream",
                    "verify": "goal.completed event published"
                },
                {
                    "layer": "L09",
                    "action": "GET /api/v1/goals/{goal_id}",
                    "verify": "Goal status is 'completed'"
                }
            ]
        },
        {
            "name": "Circuit Breaker Activation",
            "description": "Verify circuit breaker protects failing services",
            "steps": [
                {
                    "action": "Simulate L03 tool failure (5 consecutive failures)",
                    "verify": "Circuit breaker opens after threshold"
                },
                {
                    "action": "Attempt tool execution",
                    "verify": "Fast fail without calling failing service"
                },
                {
                    "action": "Wait for half-open state",
                    "verify": "Single test request allowed"
                },
                {
                    "action": "Restore service health",
                    "verify": "Circuit breaker closes, normal operation resumes"
                }
            ]
        },
        {
            "name": "Event Propagation Latency",
            "description": "Measure event flow timing across layers",
            "steps": [
                {
                    "action": "Emit test event in L09",
                    "timestamp": "t0"
                },
                {
                    "action": "Verify L11 receives event",
                    "timestamp": "t1",
                    "verify": "t1 - t0 < 50ms"
                },
                {
                    "action": "Verify all subscribers notified",
                    "timestamp": "t2",
                    "verify": "t2 - t0 < 200ms"
                }
            ]
        },
        {
            "name": "L04 Model Gateway Routing",
            "description": "Test LLM routing and failover",
            "steps": [
                {
                    "action": "Request inference via L02 agent",
                    "payload": {"model": "gpt-4", "prompt": "test"}
                },
                {
                    "action": "Verify L04 routes to correct provider",
                    "verify": "OpenAI provider selected"
                },
                {
                    "action": "Simulate provider failure",
                    "verify": "L04 fails over to fallback provider"
                },
                {
                    "action": "Verify response returned to agent",
                    "verify": "Agent receives inference result"
                }
            ]
        },
        {
            "name": "Concurrent Agent Execution",
            "description": "Test multiple agents working simultaneously",
            "steps": [
                {
                    "action": "Create 10 agents via API",
                    "verify": "All agents created successfully"
                },
                {
                    "action": "Assign goals to all agents",
                    "verify": "All goals accepted"
                },
                {
                    "action": "Monitor concurrent execution",
                    "verify": "All agents progress independently"
                },
                {
                    "action": "Verify no resource contention",
                    "verify": "No deadlocks, no starvation"
                },
                {
                    "action": "Wait for all completions",
                    "verify": "All 10 goals complete within 5 minutes"
                }
            ]
        }
    ])

    def to_api_payload(self) -> Dict[str, Any]:
        """Convert to API request payload for agent creation."""
        return {
            "name": self.name,
            "agent_type": self.agent_type,
            "version": self.version,
            "configuration": self.configuration,
            "capabilities": self.capabilities,
            "metadata": {
                "test_coverage": "layer_integration",
                "execution_mode": "automated",
                "requires_all_layers": True
            }
        }


# Pre-configured instance
integration_tester = IntegrationTester()

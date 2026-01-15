"""API Tester Agent - Validates all L09 API Gateway endpoints."""

from typing import Dict, List, Any
from dataclasses import dataclass, field


@dataclass
class APITester:
    """
    Tests all API endpoints for correctness, performance, and security.

    Responsibilities:
    - Validate L09 API Gateway endpoints
    - Test CRUD operations on agents, goals, contexts
    - Verify authentication and authorization
    - Check rate limiting behavior
    - Measure response times and throughput
    """

    name: str = "api-tester"
    agent_type: str = "api_tester"
    version: str = "1.0.0"

    configuration: Dict[str, Any] = field(default_factory=lambda: {
        "goal": "Validate all L09 API Gateway endpoints",
        "target_endpoints": [
            {"path": "/health/live", "method": "GET", "expected_status": 200},
            {"path": "/health/ready", "method": "GET", "expected_status": 200},
            {"path": "/api/v1/agents", "method": "GET", "expected_status": 200},
            {"path": "/api/v1/agents", "method": "POST", "expected_status": 201},
            {"path": "/api/v1/agents/{id}", "method": "GET", "expected_status": 200},
            {"path": "/api/v1/agents/{id}", "method": "PUT", "expected_status": 200},
            {"path": "/api/v1/agents/{id}", "method": "DELETE", "expected_status": 204},
            {"path": "/api/v1/goals", "method": "POST", "expected_status": 201},
            {"path": "/api/v1/goals/{id}", "method": "GET", "expected_status": 200},
        ],
        "test_scenarios": [
            "happy_path",
            "invalid_input",
            "missing_auth",
            "rate_limiting",
            "concurrent_requests",
            "large_payloads"
        ],
        "performance_thresholds": {
            "max_response_time_ms": 500,
            "min_throughput_rps": 100,
            "max_error_rate_percent": 1.0
        },
        "authentication": {
            "test_invalid_token": True,
            "test_expired_token": True,
            "test_missing_token": True
        }
    })

    capabilities: List[str] = field(default_factory=lambda: [
        "http_testing",
        "authentication_validation",
        "rate_limit_verification",
        "performance_measurement",
        "error_handling_validation"
    ])

    test_cases: List[Dict[str, Any]] = field(default_factory=lambda: [
        {
            "name": "Health Check Validation",
            "description": "Verify all health endpoints return correct status",
            "steps": [
                {"action": "GET /health/live", "assert": "status == 200"},
                {"action": "GET /health/ready", "assert": "status == 200 or 503"},
                {"action": "verify response contains timestamp"},
                {"action": "verify response time < 100ms"}
            ]
        },
        {
            "name": "Agent CRUD Operations",
            "description": "Test complete agent lifecycle",
            "steps": [
                {"action": "POST /api/v1/agents", "payload": "minimal_valid_agent"},
                {"action": "assert response contains agent_id"},
                {"action": "GET /api/v1/agents/{agent_id}"},
                {"action": "assert agent data matches creation payload"},
                {"action": "PUT /api/v1/agents/{agent_id}", "payload": "updated_agent"},
                {"action": "assert update succeeded"},
                {"action": "DELETE /api/v1/agents/{agent_id}"},
                {"action": "assert deletion succeeded"},
                {"action": "GET /api/v1/agents/{agent_id}", "assert": "status == 404"}
            ]
        },
        {
            "name": "Rate Limiting",
            "description": "Verify rate limits activate correctly",
            "steps": [
                {"action": "send 100 requests in 1 second"},
                {"action": "assert some requests receive 429"},
                {"action": "verify Retry-After header present"},
                {"action": "wait for rate limit window"},
                {"action": "verify requests succeed again"}
            ]
        },
        {
            "name": "Authentication Rejection",
            "description": "Verify invalid auth is rejected",
            "steps": [
                {"action": "POST /api/v1/agents without token", "assert": "status == 401"},
                {"action": "POST /api/v1/agents with invalid token", "assert": "status == 401"},
                {"action": "POST /api/v1/agents with expired token", "assert": "status == 401"},
                {"action": "verify error response format is correct"}
            ]
        },
        {
            "name": "Invalid Input Handling",
            "description": "Test API handles bad input gracefully",
            "steps": [
                {"action": "POST /api/v1/agents", "payload": "empty", "assert": "status == 400"},
                {"action": "POST /api/v1/agents", "payload": "invalid_json", "assert": "status == 400"},
                {"action": "POST /api/v1/agents", "payload": "missing_required_fields", "assert": "status == 422"},
                {"action": "verify error messages are descriptive"}
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
                "test_coverage": "api_endpoints",
                "execution_mode": "automated",
                "reporting": "detailed"
            }
        }


# Pre-configured instance
api_tester = APITester()

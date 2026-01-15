"""QA Orchestrator Agent - Coordinates comprehensive platform testing."""

from typing import Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class QAOrchestrator:
    """
    Orchestrates QA testing across the platform.

    Responsibilities:
    - Coordinate test campaigns across multiple QA agents
    - Monitor test progress and aggregate results
    - Identify critical failures and blockers
    - Generate comprehensive test reports
    """

    name: str = "qa-orchestrator"
    agent_type: str = "qa_orchestrator"
    version: str = "1.0.0"

    configuration: Dict[str, Any] = field(default_factory=lambda: {
        "goal": "Coordinate comprehensive platform QA testing",
        "sub_agents": [
            "api-tester",
            "integration-tester",
            "data-validator"
        ],
        "test_suites": [
            "api_endpoints",
            "layer_integration",
            "data_consistency",
            "performance",
            "security"
        ],
        "failure_threshold": 0.05,  # 5% failure rate triggers alert
        "parallel_execution": True,
        "retry_failed_tests": True,
        "max_retries": 3
    })

    capabilities: List[str] = field(default_factory=lambda: [
        "test_orchestration",
        "result_aggregation",
        "failure_analysis",
        "report_generation",
        "sub_agent_coordination"
    ])

    success_criteria: List[str] = field(default_factory=lambda: [
        "All critical endpoints respond within SLA",
        "Zero data consistency violations",
        "All layer integrations validated",
        "No security vulnerabilities detected",
        "Performance metrics within acceptable range"
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
                "created_by": "qa_swarm_deployment",
                "created_at": datetime.utcnow().isoformat(),
                "purpose": "self_test",
                "criticality": "high"
            }
        }

    def create_test_campaign(self) -> Dict[str, Any]:
        """Create a comprehensive test campaign goal."""
        return {
            "description": "Execute comprehensive platform QA",
            "agent_id": None,  # Set after agent creation
            "test_plan": {
                "phases": [
                    {
                        "name": "API Validation",
                        "agent": "api-tester",
                        "targets": [
                            "L09 API Gateway",
                            "L01 Data Layer",
                            "L05 Orchestration"
                        ]
                    },
                    {
                        "name": "Integration Testing",
                        "agent": "integration-tester",
                        "targets": [
                            "L02<->L03 communication",
                            "L11 event propagation",
                            "L05<->L02 orchestration"
                        ]
                    },
                    {
                        "name": "Data Validation",
                        "agent": "data-validator",
                        "targets": [
                            "L01 persistence",
                            "Redis consistency",
                            "PostgreSQL schema integrity"
                        ]
                    }
                ],
                "execution_strategy": "parallel_with_dependencies"
            },
            "success_criteria": self.success_criteria,
            "reporting": {
                "format": "markdown",
                "output_file": "QA_FINDINGS.md",
                "include_metrics": True,
                "include_recommendations": True
            }
        }


# Pre-configured instance for easy import
qa_orchestrator = QAOrchestrator()

"""Service categorization utilities for L12 Natural Language Interface.

This module provides functionality to categorize platform services by their
usage and functional purpose rather than architectural layer.
"""

from typing import Dict, List

from ..models.service_metadata import ServiceMetadata


class ServiceCategorizer:
    """Categorizes services by usage/functional purpose."""

    # Category definitions with descriptions
    CATEGORIES = {
        "data_storage": {
            "name": "Data & Storage",
            "description": "Persistent storage, registries, and data management services",
            "services": [
                "AgentRegistry",
                "ConfigStore",
                "DatasetService",
                "DocumentStore",
                "EvaluationStore",
                "EventStore",
                "FeedbackStore",
                "GoalStore",
                "PlanStore",
                "SessionService",
                "ToolRegistry",
                "TrainingExampleService",
            ],
        },
        "agent_management": {
            "name": "Agent Management",
            "description": "Agent lifecycle, execution, fleet coordination, and task assignment",
            "services": [
                "AgentExecutor",
                "FleetManager",
                "LifecycleManager",
                "AgentAssigner",
            ],
        },
        "resource_infrastructure": {
            "name": "Resource & Infrastructure",
            "description": "Resource quotas, sandboxing, state management, and infrastructure control",
            "services": [
                "ResourceManager",
                "SandboxManager",
                "StateManager",
            ],
        },
        "workflow_orchestration": {
            "name": "Workflow & Orchestration",
            "description": "Multi-step workflow execution, task coordination, and distributed transactions",
            "services": [
                "WorkflowEngine",
                "TaskOrchestrator",
                "RequestOrchestrator",
                "SagaOrchestrator",
            ],
        },
        "planning_strategy": {
            "name": "Planning & Strategy",
            "description": "Goal decomposition, strategic planning, and execution plan generation",
            "services": [
                "PlanningService",
                "GoalDecomposer",
            ],
        },
        "tool_execution": {
            "name": "Tool Execution",
            "description": "Tool invocation, composition, and workflow chaining",
            "services": [
                "ToolExecutor",
                "ToolComposer",
            ],
        },
        "ai_models": {
            "name": "AI & Models",
            "description": "LLM gateway, model routing, caching, and inference orchestration",
            "services": [
                "ModelGateway",
                "LLMRouter",
                "SemanticCache",
            ],
        },
        "evaluation_monitoring": {
            "name": "Evaluation & Monitoring",
            "description": "Quality assessment, metrics aggregation, and alerting",
            "services": [
                "EvaluationService",
                "MetricsEngine",
                "AlertManager",
            ],
        },
        "learning_training": {
            "name": "Learning & Training",
            "description": "Model fine-tuning, dataset curation, and training orchestration",
            "services": [
                "LearningService",
                "FineTuningEngine",
                "DatasetCurator",
            ],
        },
        "security_access": {
            "name": "Security & Access",
            "description": "Authentication, authorization, and access control",
            "services": [
                "AuthenticationHandler",
                "AuthorizationEngine",
            ],
        },
        "integration_communication": {
            "name": "Integration & Communication",
            "description": "Service discovery, event bus, cross-layer routing, and messaging",
            "services": [
                "RequestRouter",
                "EventBusManager",
                "ServiceRegistry",
            ],
        },
        "user_interface": {
            "name": "User Interface",
            "description": "Dashboard, controls, real-time updates, and user-facing services",
            "services": [
                "DashboardService",
                "ControlService",
                "WebSocketGateway",
            ],
        },
    }

    @classmethod
    def get_category_for_service(cls, service_name: str) -> str:
        """Get the category ID for a given service name.

        Args:
            service_name: Name of the service

        Returns:
            Category ID (e.g., "data_storage") or "uncategorized"
        """
        for category_id, category_data in cls.CATEGORIES.items():
            if service_name in category_data["services"]:
                return category_id
        return "uncategorized"

    @classmethod
    def get_category_name(cls, category_id: str) -> str:
        """Get display name for a category.

        Args:
            category_id: Category identifier

        Returns:
            Human-readable category name
        """
        return cls.CATEGORIES.get(category_id, {}).get("name", "Uncategorized")

    @classmethod
    def get_category_description(cls, category_id: str) -> str:
        """Get description for a category.

        Args:
            category_id: Category identifier

        Returns:
            Category description
        """
        return cls.CATEGORIES.get(category_id, {}).get("description", "")

    @classmethod
    def group_services_by_category(
        cls, services: List[ServiceMetadata]
    ) -> Dict[str, List[ServiceMetadata]]:
        """Group services by their functional category.

        Args:
            services: List of ServiceMetadata objects

        Returns:
            Dictionary mapping category_id to list of services
        """
        grouped: Dict[str, List[ServiceMetadata]] = {}

        for service in services:
            category_id = cls.get_category_for_service(service.service_name)
            if category_id not in grouped:
                grouped[category_id] = []
            grouped[category_id].append(service)

        return grouped

    @classmethod
    def format_categorized_services(
        cls, services: List[ServiceMetadata], search_term: str = None
    ) -> str:
        """Format services grouped by category for display.

        Args:
            services: List of ServiceMetadata objects
            search_term: Optional search term to highlight in results

        Returns:
            Formatted string with categorized service listing
        """
        grouped = cls.group_services_by_category(services)

        # Sort categories by predefined order
        category_order = list(cls.CATEGORIES.keys())
        sorted_categories = sorted(
            grouped.keys(), key=lambda x: category_order.index(x) if x in category_order else 999
        )

        output_lines = []

        if search_term:
            output_lines.append(f"🔍 Services matching '{search_term}':\n")
        else:
            output_lines.append(f"📋 All Platform Services ({len(services)} total)\n")

        for category_id in sorted_categories:
            category_services = grouped[category_id]
            category_name = cls.get_category_name(category_id)
            category_desc = cls.get_category_description(category_id)

            output_lines.append(f"\n{'='*70}")
            output_lines.append(f"📦 {category_name} ({len(category_services)} services)")
            output_lines.append(f"   {category_desc}")
            output_lines.append(f"{'='*70}\n")

            for service in sorted(category_services, key=lambda s: s.service_name):
                # Service name and layer
                output_lines.append(f"• {service.service_name} ({service.layer})")

                # Description
                output_lines.append(f"  └─ {service.description}")

                # Keywords
                if service.keywords:
                    keywords_str = ", ".join(service.keywords[:5])  # Limit to 5 keywords
                    output_lines.append(f"  └─ Keywords: {keywords_str}")

                # Method count
                method_count = len(service.methods) if service.methods else 0
                if method_count > 0:
                    output_lines.append(f"  └─ Methods: {method_count} available")

                output_lines.append("")  # Blank line between services

        return "\n".join(output_lines)

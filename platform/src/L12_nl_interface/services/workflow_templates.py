"""Workflow Templates for L12 Natural Language Interface.

This module provides pre-defined multi-service workflows for common platform operations:
- Testing workflows (unit, integration, end-to-end)
- Deployment workflows (build, test, deploy)
- Data pipeline workflows (ETL, validation, processing)
- Monitoring workflows (health checks, metrics collection)

Example:
    >>> from L12_nl_interface.services.workflow_templates import WorkflowTemplates
    >>> templates = WorkflowTemplates(registry, factory)
    >>> workflow = templates.get_template("testing.unit")
    >>> result = await templates.execute_workflow(workflow, {"test_path": "tests/"})
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ..core.service_factory import ServiceFactory
from ..core.service_registry import ServiceRegistry
from ..models.command_models import InvokeRequest, InvocationStatus

logger = logging.getLogger(__name__)


class WorkflowCategory(str, Enum):
    """Workflow category enumeration."""

    TESTING = "testing"
    DEPLOYMENT = "deployment"
    DATA_PIPELINE = "data_pipeline"
    MONITORING = "monitoring"


@dataclass
class WorkflowStep:
    """Individual step in a workflow.

    Attributes:
        service_name: Name of the service to invoke
        method_name: Method to call on the service
        parameters: Parameters for the method call
        depends_on: List of step IDs this step depends on
        step_id: Unique identifier for this step
        on_error: Action to take on error (continue, abort, retry)
        retry_count: Number of retries for this step
        timeout_seconds: Timeout for this step in seconds
    """

    service_name: str
    method_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    step_id: str = ""
    on_error: str = "abort"  # continue, abort, retry
    retry_count: int = 0
    timeout_seconds: Optional[float] = None

    def __post_init__(self):
        """Generate step_id if not provided."""
        if not self.step_id:
            self.step_id = f"{self.service_name}.{self.method_name}"


@dataclass
class WorkflowTemplate:
    """Template for a multi-service workflow.

    Attributes:
        name: Workflow name (e.g., "testing.unit")
        category: Workflow category
        description: Human-readable description
        steps: List of workflow steps
        parameters: Template parameters that can be substituted
        tags: Tags for categorization and search
    """

    name: str
    category: WorkflowCategory
    description: str
    steps: List[WorkflowStep]
    parameters: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass
class WorkflowResult:
    """Result of workflow execution.

    Attributes:
        workflow_name: Name of the executed workflow
        status: Overall workflow status
        started_at: Start timestamp
        completed_at: Completion timestamp
        step_results: Results from each step
        error: Error message if failed
    """

    workflow_name: str
    status: InvocationStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    step_results: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class WorkflowTemplates:
    """Manager for pre-defined workflow templates.

    The WorkflowTemplates service provides:
    1. Pre-defined workflows for common operations
    2. Parameter substitution for customization
    3. Step orchestration with dependency management
    4. Error handling and retry logic

    Attributes:
        registry: ServiceRegistry for service metadata
        factory: ServiceFactory for service instantiation
        templates: Registry of available workflow templates
    """

    def __init__(self, registry: ServiceRegistry, factory: ServiceFactory):
        """Initialize the workflow templates service.

        Args:
            registry: ServiceRegistry instance
            factory: ServiceFactory instance
        """
        self.registry = registry
        self.factory = factory
        self.templates: Dict[str, WorkflowTemplate] = {}

        # Register built-in templates
        self._register_builtin_templates()

        logger.info(
            f"WorkflowTemplates initialized: {len(self.templates)} templates loaded"
        )

    def _register_builtin_templates(self):
        """Register built-in workflow templates."""
        # Testing workflows
        self._register_testing_workflows()

        # Deployment workflows
        self._register_deployment_workflows()

        # Data pipeline workflows
        self._register_data_pipeline_workflows()

        # Monitoring workflows
        self._register_monitoring_workflows()

    def _register_testing_workflows(self):
        """Register testing workflow templates."""
        # Unit testing workflow
        self.register_template(
            WorkflowTemplate(
                name="testing.unit",
                category=WorkflowCategory.TESTING,
                description="Run unit tests for a specific module or path",
                parameters={"test_path": "tests/", "parallel": True},
                tags=["testing", "unit", "ci"],
                steps=[
                    WorkflowStep(
                        step_id="validate_tests",
                        service_name="ValidationService",
                        method_name="validate_test_config",
                        parameters={"test_path": "{test_path}"},
                    ),
                    WorkflowStep(
                        step_id="run_unit_tests",
                        service_name="TestExecutor",
                        method_name="run_tests",
                        parameters={
                            "test_path": "{test_path}",
                            "test_type": "unit",
                            "parallel": "{parallel}",
                        },
                        depends_on=["validate_tests"],
                        retry_count=1,
                    ),
                    WorkflowStep(
                        step_id="generate_report",
                        service_name="ReportGenerator",
                        method_name="generate_test_report",
                        parameters={"test_results": "{run_unit_tests.result}"},
                        depends_on=["run_unit_tests"],
                    ),
                ],
            )
        )

        # Integration testing workflow
        self.register_template(
            WorkflowTemplate(
                name="testing.integration",
                category=WorkflowCategory.TESTING,
                description="Run integration tests with environment setup",
                parameters={"test_path": "tests/integration/", "env": "test"},
                tags=["testing", "integration", "ci"],
                steps=[
                    WorkflowStep(
                        step_id="setup_environment",
                        service_name="EnvironmentService",
                        method_name="setup_test_environment",
                        parameters={"env": "{env}"},
                    ),
                    WorkflowStep(
                        step_id="run_integration_tests",
                        service_name="TestExecutor",
                        method_name="run_tests",
                        parameters={
                            "test_path": "{test_path}",
                            "test_type": "integration",
                        },
                        depends_on=["setup_environment"],
                        retry_count=2,
                    ),
                    WorkflowStep(
                        step_id="cleanup_environment",
                        service_name="EnvironmentService",
                        method_name="cleanup_test_environment",
                        parameters={"env": "{env}"},
                        depends_on=["run_integration_tests"],
                        on_error="continue",
                    ),
                ],
            )
        )

    def _register_deployment_workflows(self):
        """Register deployment workflow templates."""
        # Standard deployment workflow
        self.register_template(
            WorkflowTemplate(
                name="deployment.standard",
                category=WorkflowCategory.DEPLOYMENT,
                description="Standard deployment workflow with build, test, and deploy",
                parameters={"environment": "staging", "version": "latest"},
                tags=["deployment", "cd", "production"],
                steps=[
                    WorkflowStep(
                        step_id="build",
                        service_name="BuildService",
                        method_name="build_application",
                        parameters={"version": "{version}"},
                        timeout_seconds=600,
                    ),
                    WorkflowStep(
                        step_id="test",
                        service_name="TestExecutor",
                        method_name="run_tests",
                        parameters={"test_type": "smoke"},
                        depends_on=["build"],
                        retry_count=1,
                    ),
                    WorkflowStep(
                        step_id="deploy",
                        service_name="DeploymentService",
                        method_name="deploy_application",
                        parameters={
                            "environment": "{environment}",
                            "version": "{version}",
                        },
                        depends_on=["test"],
                        timeout_seconds=300,
                    ),
                    WorkflowStep(
                        step_id="health_check",
                        service_name="HealthMonitor",
                        method_name="check_deployment_health",
                        parameters={"environment": "{environment}"},
                        depends_on=["deploy"],
                        retry_count=3,
                    ),
                ],
            )
        )

        # Canary deployment workflow
        self.register_template(
            WorkflowTemplate(
                name="deployment.canary",
                category=WorkflowCategory.DEPLOYMENT,
                description="Canary deployment with gradual traffic rollout",
                parameters={
                    "environment": "production",
                    "version": "latest",
                    "canary_percent": 10,
                },
                tags=["deployment", "canary", "production"],
                steps=[
                    WorkflowStep(
                        step_id="deploy_canary",
                        service_name="DeploymentService",
                        method_name="deploy_canary",
                        parameters={
                            "environment": "{environment}",
                            "version": "{version}",
                            "traffic_percent": "{canary_percent}",
                        },
                    ),
                    WorkflowStep(
                        step_id="monitor_canary",
                        service_name="HealthMonitor",
                        method_name="monitor_deployment",
                        parameters={
                            "environment": "{environment}",
                            "duration_seconds": 300,
                        },
                        depends_on=["deploy_canary"],
                    ),
                    WorkflowStep(
                        step_id="rollout_full",
                        service_name="DeploymentService",
                        method_name="rollout_full_deployment",
                        parameters={
                            "environment": "{environment}",
                            "version": "{version}",
                        },
                        depends_on=["monitor_canary"],
                    ),
                ],
            )
        )

    def _register_data_pipeline_workflows(self):
        """Register data pipeline workflow templates."""
        # ETL workflow
        self.register_template(
            WorkflowTemplate(
                name="data_pipeline.etl",
                category=WorkflowCategory.DATA_PIPELINE,
                description="Extract, Transform, Load data pipeline",
                parameters={
                    "source": "database",
                    "destination": "warehouse",
                    "batch_size": 1000,
                },
                tags=["data", "etl", "pipeline"],
                steps=[
                    WorkflowStep(
                        step_id="extract",
                        service_name="DataService",
                        method_name="extract_data",
                        parameters={
                            "source": "{source}",
                            "batch_size": "{batch_size}",
                        },
                        timeout_seconds=1800,
                    ),
                    WorkflowStep(
                        step_id="transform",
                        service_name="DataService",
                        method_name="transform_data",
                        parameters={"data": "{extract.result}"},
                        depends_on=["extract"],
                        timeout_seconds=1800,
                    ),
                    WorkflowStep(
                        step_id="validate",
                        service_name="ValidationService",
                        method_name="validate_data",
                        parameters={"data": "{transform.result}"},
                        depends_on=["transform"],
                    ),
                    WorkflowStep(
                        step_id="load",
                        service_name="DataService",
                        method_name="load_data",
                        parameters={
                            "destination": "{destination}",
                            "data": "{transform.result}",
                        },
                        depends_on=["validate"],
                        timeout_seconds=1800,
                    ),
                ],
            )
        )

    def _register_monitoring_workflows(self):
        """Register monitoring workflow templates."""
        # Health check workflow
        self.register_template(
            WorkflowTemplate(
                name="monitoring.health_check",
                category=WorkflowCategory.MONITORING,
                description="Comprehensive health check across all services",
                parameters={"alert_on_failure": True},
                tags=["monitoring", "health", "ops"],
                steps=[
                    WorkflowStep(
                        step_id="check_services",
                        service_name="HealthMonitor",
                        method_name="check_all_services",
                        parameters={},
                    ),
                    WorkflowStep(
                        step_id="check_resources",
                        service_name="ResourceMonitor",
                        method_name="check_resource_usage",
                        parameters={},
                    ),
                    WorkflowStep(
                        step_id="generate_report",
                        service_name="ReportGenerator",
                        method_name="generate_health_report",
                        parameters={
                            "service_health": "{check_services.result}",
                            "resource_health": "{check_resources.result}",
                        },
                        depends_on=["check_services", "check_resources"],
                    ),
                    WorkflowStep(
                        step_id="alert_if_needed",
                        service_name="AlertService",
                        method_name="send_alert",
                        parameters={
                            "alert_on_failure": "{alert_on_failure}",
                            "report": "{generate_report.result}",
                        },
                        depends_on=["generate_report"],
                        on_error="continue",
                    ),
                ],
            )
        )

    def register_template(self, template: WorkflowTemplate):
        """Register a new workflow template.

        Args:
            template: WorkflowTemplate to register
        """
        self.templates[template.name] = template
        logger.debug(f"Registered workflow template: {template.name}")

    def get_template(self, name: str) -> Optional[WorkflowTemplate]:
        """Get a workflow template by name.

        Args:
            name: Template name

        Returns:
            WorkflowTemplate or None if not found
        """
        return self.templates.get(name)

    def list_templates(
        self, category: Optional[WorkflowCategory] = None
    ) -> List[WorkflowTemplate]:
        """List available workflow templates.

        Args:
            category: Optional category filter

        Returns:
            List of workflow templates
        """
        templates = list(self.templates.values())

        if category:
            templates = [t for t in templates if t.category == category]

        return templates

    def search_templates(self, query: str) -> List[WorkflowTemplate]:
        """Search workflow templates by name, description, or tags.

        Args:
            query: Search query

        Returns:
            List of matching templates
        """
        query_lower = query.lower()
        matches = []

        for template in self.templates.values():
            # Check name
            if query_lower in template.name.lower():
                matches.append(template)
                continue

            # Check description
            if query_lower in template.description.lower():
                matches.append(template)
                continue

            # Check tags
            if any(query_lower in tag.lower() for tag in template.tags):
                matches.append(template)
                continue

        return matches

    async def execute_workflow(
        self,
        workflow_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> WorkflowResult:
        """Execute a workflow template.

        Args:
            workflow_name: Name of the workflow to execute
            parameters: Parameters to substitute in the workflow
            session_id: Optional session ID for context

        Returns:
            WorkflowResult with execution details

        Example:
            >>> result = await templates.execute_workflow(
            ...     "testing.unit",
            ...     {"test_path": "tests/unit/"}
            ... )
        """
        template = self.get_template(workflow_name)
        if not template:
            return WorkflowResult(
                workflow_name=workflow_name,
                status=InvocationStatus.FAILED,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                error=f"Workflow template '{workflow_name}' not found",
            )

        # Merge template parameters with provided parameters
        merged_params = {**template.parameters, **(parameters or {})}

        # Start execution
        result = WorkflowResult(
            workflow_name=workflow_name,
            status=InvocationStatus.IN_PROGRESS,
            started_at=datetime.utcnow(),
        )

        try:
            # Execute steps with dependency management
            completed_steps = set()
            step_results = {}

            while len(completed_steps) < len(template.steps):
                # Find steps that can be executed (dependencies met)
                ready_steps = [
                    step
                    for step in template.steps
                    if step.step_id not in completed_steps
                    and all(dep in completed_steps for dep in step.depends_on)
                ]

                if not ready_steps:
                    # Circular dependency or error
                    remaining = [
                        s.step_id
                        for s in template.steps
                        if s.step_id not in completed_steps
                    ]
                    raise Exception(
                        f"Cannot execute remaining steps (circular dependency?): {remaining}"
                    )

                # Execute ready steps in parallel
                tasks = [
                    self._execute_step(
                        step, merged_params, step_results, session_id
                    )
                    for step in ready_steps
                ]

                step_exec_results = await asyncio.gather(*tasks, return_exceptions=True)

                # Process results
                for step, step_result in zip(ready_steps, step_exec_results):
                    if isinstance(step_result, Exception):
                        # Step failed
                        if step.on_error == "abort":
                            raise step_result
                        elif step.on_error == "continue":
                            logger.warning(
                                f"Step {step.step_id} failed but continuing: {step_result}"
                            )
                            step_results[step.step_id] = {
                                "status": "failed",
                                "error": str(step_result),
                            }
                        # retry is handled in _execute_step
                    else:
                        step_results[step.step_id] = step_result

                    completed_steps.add(step.step_id)

            # Workflow completed successfully
            result.status = InvocationStatus.COMPLETED
            result.completed_at = datetime.utcnow()
            result.step_results = step_results

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}", exc_info=True)
            result.status = InvocationStatus.FAILED
            result.completed_at = datetime.utcnow()
            result.error = str(e)
            result.step_results = step_results

        return result

    async def _execute_step(
        self,
        step: WorkflowStep,
        parameters: Dict[str, Any],
        step_results: Dict[str, Any],
        session_id: Optional[str],
    ) -> Dict[str, Any]:
        """Execute a single workflow step.

        Args:
            step: WorkflowStep to execute
            parameters: Workflow parameters
            step_results: Results from previous steps
            session_id: Optional session ID

        Returns:
            Step result dictionary
        """
        # Substitute parameters in step parameters
        substituted_params = self._substitute_parameters(
            step.parameters, parameters, step_results
        )

        # Create invoke request
        request = InvokeRequest(
            service_name=step.service_name,
            method_name=step.method_name,
            parameters=substituted_params,
            session_id=session_id or "workflow",
        )

        # Execute with retry logic
        last_error = None
        for attempt in range(step.retry_count + 1):
            try:
                # Get service instance
                service = self.factory.get_service(step.service_name, session_id)

                # Execute method
                if hasattr(service, step.method_name):
                    method = getattr(service, step.method_name)
                    result = await method(**substituted_params)

                    return {
                        "status": "success",
                        "result": result,
                        "attempt": attempt + 1,
                    }
                else:
                    raise AttributeError(
                        f"Service {step.service_name} has no method {step.method_name}"
                    )

            except Exception as e:
                last_error = e
                if attempt < step.retry_count:
                    logger.warning(
                        f"Step {step.step_id} failed (attempt {attempt + 1}), retrying: {e}"
                    )
                    await asyncio.sleep(1.0 * (attempt + 1))  # Exponential backoff
                else:
                    logger.error(
                        f"Step {step.step_id} failed after {attempt + 1} attempts: {e}"
                    )

        # All retries exhausted
        raise last_error

    def _substitute_parameters(
        self,
        step_params: Dict[str, Any],
        workflow_params: Dict[str, Any],
        step_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Substitute parameters in step parameters.

        Supports:
        - {param_name} - workflow parameter
        - {step_id.result} - result from previous step

        Args:
            step_params: Step parameters with placeholders
            workflow_params: Workflow parameters
            step_results: Results from previous steps

        Returns:
            Parameters with substitutions applied
        """
        substituted = {}

        for key, value in step_params.items():
            if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
                # Extract placeholder name
                placeholder = value[1:-1]

                # Check for step result reference (step_id.result)
                if "." in placeholder:
                    step_id, field = placeholder.split(".", 1)
                    if step_id in step_results:
                        step_result = step_results[step_id]
                        if field == "result" and "result" in step_result:
                            substituted[key] = step_result["result"]
                        else:
                            substituted[key] = step_result.get(field, value)
                    else:
                        substituted[key] = value  # Keep placeholder
                # Check workflow parameters
                elif placeholder in workflow_params:
                    substituted[key] = workflow_params[placeholder]
                else:
                    substituted[key] = value  # Keep placeholder
            else:
                substituted[key] = value

        return substituted

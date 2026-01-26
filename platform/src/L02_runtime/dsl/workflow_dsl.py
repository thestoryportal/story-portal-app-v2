"""
Workflow DSL - Python Decorator-Based Workflow Definition

A domain-specific language for defining workflows using Python decorators.
Workflows defined with this DSL compile to WorkflowDefinitionCreate models
that can be stored in the WorkflowStore.

Example:
    @workflow("data_pipeline", description="Process and validate data")
    class DataPipeline:
        '''Data processing pipeline with validation.'''

        @step("fetch", next="validate")
        async def fetch_data(self, ctx):
            '''Fetch data from source.'''
            return {"data": fetch_from_source(ctx["source_url"])}

        @step("validate", routes={"valid": "transform", "invalid": "report_error"})
        async def validate_data(self, ctx):
            '''Validate fetched data.'''
            is_valid = validate(ctx["data"])
            return {"route": "valid" if is_valid else "invalid"}

        @step("transform", next="save", compensation="rollback_transform")
        async def transform_data(self, ctx):
            '''Transform data with rollback support.'''
            transformed = transform(ctx["data"])
            return {"transformed": transformed}

        @compensation("transform")
        async def rollback_transform(self, ctx):
            '''Undo transformation.'''
            await cleanup_transform(ctx.get("transform_id"))

        @step("save")
        async def save_data(self, ctx):
            '''Save transformed data.'''
            save_id = await save(ctx["transformed"])
            return {"save_id": save_id}

        @step("report_error")
        async def report_error(self, ctx):
            '''Report validation error.'''
            await notify_error(ctx["validation_errors"])

    # Compile to WorkflowDefinitionCreate
    definition = DataPipeline.compile()
"""

import inspect
import logging
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Union,
    Type,
    TypeVar,
    get_type_hints,
)
from functools import wraps
from uuid import uuid4

# Import from L01 models
import sys
import os

# Add platform to path for imports
_platform_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _platform_dir not in sys.path:
    sys.path.insert(0, _platform_dir)

from L01_data_layer.models import (
    NodeType,
    WorkflowParadigm,
    WorkflowVisibility,
    WorkflowNodeDefinition,
    WorkflowEdgeDefinition,
    WorkflowParameter,
    WorkflowRoute,
    WorkflowDefinitionCreate,
    RetryConfig,
    CompensationConfig,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CompilationError(Exception):
    """Error during workflow compilation."""
    pass


@dataclass
class StepDefinition:
    """Internal representation of a workflow step."""
    name: str
    func: Callable
    node_type: NodeType = NodeType.SERVICE
    description: Optional[str] = None

    # Routing
    next_step: Optional[str] = None
    routes: Dict[str, str] = field(default_factory=dict)

    # Service invocation
    service: Optional[str] = None
    method: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)

    # Agent configuration
    agent_id: Optional[str] = None
    agent_config: Dict[str, Any] = field(default_factory=dict)

    # Subworkflow
    subworkflow_id: Optional[str] = None

    # Human approval
    approval_message: Optional[str] = None
    approval_timeout_seconds: Optional[int] = None
    on_approve: Optional[str] = None
    on_reject: Optional[str] = None

    # Parallel execution
    parallel_steps: List[str] = field(default_factory=list)
    join_step: Optional[str] = None

    # Conditional
    condition_expression: Optional[str] = None

    # Compensation
    compensation_step: Optional[str] = None

    # Resilience
    retry_config: Optional[RetryConfig] = None
    timeout_seconds: int = 300

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowMetadata:
    """Metadata for a workflow class."""
    name: str
    description: Optional[str] = None
    version: str = "1.0.0"
    paradigm: WorkflowParadigm = WorkflowParadigm.DAG
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    visibility: WorkflowVisibility = WorkflowVisibility.PRIVATE
    enable_compensation: bool = False
    parameters: List[WorkflowParameter] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkflowBuilder:
    """
    Collects step definitions and compiles them into a workflow.

    This class is attached to workflow classes decorated with @workflow.
    """

    def __init__(self, metadata: WorkflowMetadata):
        self.metadata = metadata
        self.steps: Dict[str, StepDefinition] = {}
        self.compensations: Dict[str, Callable] = {}
        self.entry_step: Optional[str] = None

    def add_step(self, step: StepDefinition) -> None:
        """Add a step definition."""
        if not self.entry_step:
            self.entry_step = step.name
        self.steps[step.name] = step

    def add_compensation(self, step_name: str, func: Callable) -> None:
        """Add a compensation function for a step."""
        self.compensations[step_name] = func

    def compile(self) -> WorkflowDefinitionCreate:
        """Compile all steps into a WorkflowDefinitionCreate."""
        if not self.steps:
            raise CompilationError("Workflow has no steps defined")

        if not self.entry_step:
            raise CompilationError("No entry step defined")

        nodes: List[WorkflowNodeDefinition] = []
        edges: List[WorkflowEdgeDefinition] = []

        # Build nodes and edges from steps
        for step_name, step in self.steps.items():
            node = self._step_to_node(step)
            nodes.append(node)

            # Build edges from routing
            if step.next_step:
                edges.append(WorkflowEdgeDefinition(
                    source_node_id=step_name,
                    target_node_id=step.next_step,
                ))
            elif step.routes:
                for route_label, target in step.routes.items():
                    edges.append(WorkflowEdgeDefinition(
                        source_node_id=step_name,
                        target_node_id=target,
                        condition=route_label,
                        label=route_label,
                    ))

            # Handle approval routing
            if step.node_type == NodeType.HUMAN_APPROVAL:
                if step.on_approve:
                    edges.append(WorkflowEdgeDefinition(
                        source_node_id=step_name,
                        target_node_id=step.on_approve,
                        condition="approved",
                        label="Approved",
                    ))
                if step.on_reject:
                    edges.append(WorkflowEdgeDefinition(
                        source_node_id=step_name,
                        target_node_id=step.on_reject,
                        condition="rejected",
                        label="Rejected",
                    ))

            # Handle parallel routing
            if step.node_type == NodeType.PARALLEL:
                for parallel_step in step.parallel_steps:
                    edges.append(WorkflowEdgeDefinition(
                        source_node_id=step_name,
                        target_node_id=parallel_step,
                    ))

        # Add end node if needed
        terminal_steps = self._find_terminal_steps(edges)
        if terminal_steps:
            end_node = WorkflowNodeDefinition(
                node_id="__end__",
                node_type=NodeType.END,
                name="End",
                description="Workflow completion",
            )
            nodes.append(end_node)
            for step_name in terminal_steps:
                edges.append(WorkflowEdgeDefinition(
                    source_node_id=step_name,
                    target_node_id="__end__",
                ))

        return WorkflowDefinitionCreate(
            name=self.metadata.name,
            description=self.metadata.description or self._extract_docstring(),
            version=self.metadata.version,
            paradigm=self.metadata.paradigm,
            nodes=nodes,
            edges=edges,
            entry_node_id=self.entry_step,
            parameters=self.metadata.parameters,
            category=self.metadata.category,
            tags=self.metadata.tags,
            visibility=self.metadata.visibility,
            metadata=self.metadata.metadata,
        )

    def _step_to_node(self, step: StepDefinition) -> WorkflowNodeDefinition:
        """Convert a StepDefinition to WorkflowNodeDefinition."""
        # Build routes from step routing
        routes = []
        if step.next_step:
            routes.append(WorkflowRoute(
                target_node_id=step.next_step,
            ))
        elif step.routes:
            for label, target in step.routes.items():
                routes.append(WorkflowRoute(
                    target_node_id=target,
                    condition=label,
                    label=label,
                ))

        # Build compensation config
        compensation = None
        if step.compensation_step and step.compensation_step in self.compensations:
            comp_func = self.compensations[step.compensation_step]
            compensation = CompensationConfig(
                service="workflow_compensation",
                method=step.compensation_step,
                parameters={},
            )

        return WorkflowNodeDefinition(
            node_id=step.name,
            node_type=step.node_type,
            name=step.name.replace("_", " ").title(),
            description=step.description or (step.func.__doc__ or "").strip(),
            config=step.metadata,
            routes=routes,
            service=step.service,
            method=step.method,
            parameters=step.parameters,
            agent_id=step.agent_id,
            agent_config=step.agent_config,
            subworkflow_id=step.subworkflow_id,
            approval_message=step.approval_message,
            approval_timeout_seconds=step.approval_timeout_seconds,
            retry_config=step.retry_config,
            timeout_seconds=step.timeout_seconds,
            compensation=compensation,
            metadata=step.metadata,
        )

    def _find_terminal_steps(self, edges: List[WorkflowEdgeDefinition]) -> List[str]:
        """Find steps that have no outgoing edges."""
        sources = {e.source_node_id for e in edges}
        targets = {e.target_node_id for e in edges}
        all_steps = set(self.steps.keys())

        # Steps that are never a source but are targets (or have no edges at all)
        terminal = all_steps - sources
        return list(terminal)

    def _extract_docstring(self) -> str:
        """Extract docstring from workflow class."""
        return ""


# =============================================================================
# Decorators
# =============================================================================

def workflow(
    name: str,
    description: Optional[str] = None,
    version: str = "1.0.0",
    paradigm: WorkflowParadigm = WorkflowParadigm.DAG,
    category: str = "general",
    tags: Optional[List[str]] = None,
    visibility: WorkflowVisibility = WorkflowVisibility.PRIVATE,
    enable_compensation: bool = False,
    parameters: Optional[List[WorkflowParameter]] = None,
    **metadata,
) -> Callable[[Type[T]], Type[T]]:
    """
    Decorator to mark a class as a workflow definition.

    Args:
        name: Unique workflow name
        description: Human-readable description
        version: Semantic version
        paradigm: Execution paradigm (DAG, sequential, etc.)
        category: Category for organization
        tags: Tags for discovery
        visibility: Sharing visibility
        enable_compensation: Enable saga pattern compensation
        parameters: Input parameters definition
        **metadata: Additional metadata

    Example:
        @workflow("my_pipeline", enable_compensation=True)
        class MyPipeline:
            '''Pipeline description.'''

            @step("process", next="validate")
            async def process(self, ctx):
                return {"result": process(ctx["input"])}
    """
    def decorator(cls: Type[T]) -> Type[T]:
        wf_metadata = WorkflowMetadata(
            name=name,
            description=description or (cls.__doc__ or "").strip(),
            version=version,
            paradigm=paradigm,
            category=category,
            tags=tags or [],
            visibility=visibility,
            enable_compensation=enable_compensation,
            parameters=parameters or [],
            metadata=metadata,
        )

        # Attach builder to class
        builder = WorkflowBuilder(wf_metadata)
        cls._workflow_builder = builder

        # Process methods for step definitions
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name, None)
            if attr and hasattr(attr, "_step_definition"):
                step_def: StepDefinition = attr._step_definition
                builder.add_step(step_def)
            elif attr and hasattr(attr, "_compensation_for"):
                comp_target: str = attr._compensation_for
                builder.add_compensation(comp_target, attr)

        # Add compile class method
        @classmethod
        def compile(cls) -> WorkflowDefinitionCreate:
            return cls._workflow_builder.compile()

        cls.compile = compile

        return cls

    return decorator


def step(
    name: str,
    next: Optional[str] = None,
    routes: Optional[Dict[str, str]] = None,
    compensation: Optional[str] = None,
    retry: Optional[RetryConfig] = None,
    timeout_seconds: int = 300,
    **metadata,
) -> Callable:
    """
    Decorator to define a workflow step.

    Args:
        name: Unique step name within the workflow
        next: Name of the next step (for linear flow)
        routes: Conditional routing dict {condition: step_name}
        compensation: Name of compensation function for rollback
        retry: Retry configuration
        timeout_seconds: Execution timeout
        **metadata: Additional metadata

    Example:
        @step("validate", routes={"valid": "process", "invalid": "error"})
        async def validate_data(self, ctx):
            is_valid = validate(ctx["data"])
            return {"route": "valid" if is_valid else "invalid"}
    """
    def decorator(func: Callable) -> Callable:
        step_def = StepDefinition(
            name=name,
            func=func,
            node_type=NodeType.SERVICE,
            description=(func.__doc__ or "").strip(),
            next_step=next,
            routes=routes or {},
            compensation_step=compensation,
            retry_config=retry,
            timeout_seconds=timeout_seconds,
            metadata=metadata,
        )

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        wrapper._step_definition = step_def
        return wrapper

    return decorator


def compensation(step_name: str) -> Callable:
    """
    Decorator to define a compensation function for saga rollback.

    Args:
        step_name: Name of the step this compensates

    Example:
        @compensation("save")
        async def rollback_save(self, ctx):
            await delete(ctx["save_id"])
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        wrapper._compensation_for = step_name
        return wrapper

    return decorator


def approval_step(
    name: str,
    message: str,
    next: Optional[str] = None,
    on_reject: Optional[str] = None,
    timeout_seconds: Optional[int] = None,
    **metadata,
) -> Callable:
    """
    Decorator to define a human approval step.

    Args:
        name: Unique step name
        message: Message to show the approver (supports ${var} interpolation)
        next: Step to proceed to on approval
        on_reject: Step to proceed to on rejection
        timeout_seconds: Approval timeout

    Example:
        @approval_step("approve_order", message="Approve order ${order_id}?",
                       next="fulfill", on_reject="cancel")
        async def request_approval(self, ctx):
            pass
    """
    def decorator(func: Callable) -> Callable:
        step_def = StepDefinition(
            name=name,
            func=func,
            node_type=NodeType.HUMAN_APPROVAL,
            description=(func.__doc__ or "").strip(),
            approval_message=message,
            approval_timeout_seconds=timeout_seconds,
            on_approve=next,
            on_reject=on_reject,
            metadata=metadata,
        )

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        wrapper._step_definition = step_def
        return wrapper

    return decorator


def service_step(
    name: str,
    service: str,
    method: str,
    params: Optional[Dict[str, Any]] = None,
    next: Optional[str] = None,
    routes: Optional[Dict[str, str]] = None,
    retry: Optional[RetryConfig] = None,
    timeout_seconds: int = 300,
    **metadata,
) -> Callable:
    """
    Decorator to define a step that invokes a platform service.

    Args:
        name: Unique step name
        service: Service name to invoke
        method: Method to call
        params: Parameter template (supports ${ctx.var} interpolation)
        next: Next step name
        routes: Conditional routing
        retry: Retry configuration
        timeout_seconds: Execution timeout

    Example:
        @service_step("generate", service="ModelGateway", method="generate",
                      params={"prompt": "${ctx.prompt}", "model": "claude-3"},
                      next="process_result")
        async def invoke_llm(self, ctx):
            pass
    """
    def decorator(func: Callable) -> Callable:
        step_def = StepDefinition(
            name=name,
            func=func,
            node_type=NodeType.SERVICE,
            description=(func.__doc__ or "").strip(),
            service=service,
            method=method,
            parameters=params or {},
            next_step=next,
            routes=routes or {},
            retry_config=retry,
            timeout_seconds=timeout_seconds,
            metadata=metadata,
        )

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        wrapper._step_definition = step_def
        return wrapper

    return decorator


def parallel_step(
    name: str,
    steps: List[str],
    join: Optional[str] = None,
    **metadata,
) -> Callable:
    """
    Decorator to define a parallel execution step.

    Args:
        name: Unique step name
        steps: List of step names to execute in parallel
        join: Step to proceed to after all parallel steps complete

    Example:
        @parallel_step("parallel_process", steps=["step_a", "step_b", "step_c"],
                       join="merge_results")
        async def fork_processing(self, ctx):
            pass
    """
    def decorator(func: Callable) -> Callable:
        step_def = StepDefinition(
            name=name,
            func=func,
            node_type=NodeType.PARALLEL,
            description=(func.__doc__ or "").strip(),
            parallel_steps=steps,
            join_step=join,
            metadata=metadata,
        )

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        wrapper._step_definition = step_def
        return wrapper

    return decorator


def conditional_step(
    name: str,
    expression: str,
    routes: Dict[str, str],
    **metadata,
) -> Callable:
    """
    Decorator to define a conditional routing step.

    Args:
        name: Unique step name
        expression: Condition expression to evaluate
        routes: Dict mapping expression results to step names

    Example:
        @conditional_step("check_amount", expression="ctx.amount > 1000",
                          routes={"true": "large_order", "false": "small_order"})
        async def route_by_amount(self, ctx):
            pass
    """
    def decorator(func: Callable) -> Callable:
        step_def = StepDefinition(
            name=name,
            func=func,
            node_type=NodeType.CONDITIONAL,
            description=(func.__doc__ or "").strip(),
            condition_expression=expression,
            routes=routes,
            metadata=metadata,
        )

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        wrapper._step_definition = step_def
        return wrapper

    return decorator


def subworkflow_step(
    name: str,
    workflow_id: str,
    next: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
    timeout_seconds: int = 3600,
    **metadata,
) -> Callable:
    """
    Decorator to define a step that executes a nested workflow.

    Args:
        name: Unique step name
        workflow_id: ID of the workflow to execute
        next: Step to proceed to after subworkflow completes
        params: Parameters to pass to subworkflow
        timeout_seconds: Execution timeout

    Example:
        @subworkflow_step("run_validation", workflow_id="validation_pipeline",
                          next="process_validated", params={"strict": True})
        async def validate_with_subworkflow(self, ctx):
            pass
    """
    def decorator(func: Callable) -> Callable:
        step_def = StepDefinition(
            name=name,
            func=func,
            node_type=NodeType.SUBWORKFLOW,
            description=(func.__doc__ or "").strip(),
            subworkflow_id=workflow_id,
            next_step=next,
            parameters=params or {},
            timeout_seconds=timeout_seconds,
            metadata=metadata,
        )

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        wrapper._step_definition = step_def
        return wrapper

    return decorator


# =============================================================================
# Utility Functions
# =============================================================================

def compile_workflow(cls: type) -> WorkflowDefinitionCreate:
    """
    Compile a workflow class to WorkflowDefinitionCreate.

    Convenience function for compiling without calling the class method.

    Args:
        cls: Workflow class decorated with @workflow

    Returns:
        WorkflowDefinitionCreate ready for storage

    Example:
        definition = compile_workflow(MyPipeline)
    """
    if not hasattr(cls, "_workflow_builder"):
        raise CompilationError(f"{cls.__name__} is not a workflow class")

    return cls._workflow_builder.compile()


def workflow_from_dict(data: Dict[str, Any]) -> WorkflowDefinitionCreate:
    """
    Create a WorkflowDefinitionCreate from a dictionary.

    Useful for loading workflows from YAML or JSON files.

    Args:
        data: Dictionary with workflow definition

    Returns:
        WorkflowDefinitionCreate
    """
    # Parse nodes
    nodes = []
    for node_data in data.get("nodes", []):
        node = WorkflowNodeDefinition(**node_data)
        nodes.append(node)

    # Parse edges
    edges = []
    for edge_data in data.get("edges", []):
        edge = WorkflowEdgeDefinition(**edge_data)
        edges.append(edge)

    # Parse parameters
    parameters = []
    for param_data in data.get("parameters", []):
        param = WorkflowParameter(**param_data)
        parameters.append(param)

    return WorkflowDefinitionCreate(
        name=data["name"],
        description=data.get("description"),
        version=data.get("version", "1.0.0"),
        paradigm=WorkflowParadigm(data.get("paradigm", "dag")),
        nodes=nodes,
        edges=edges,
        entry_node_id=data["entry_node_id"],
        parameters=parameters,
        category=data.get("category", "general"),
        tags=data.get("tags", []),
        visibility=WorkflowVisibility(data.get("visibility", "private")),
        metadata=data.get("metadata", {}),
    )

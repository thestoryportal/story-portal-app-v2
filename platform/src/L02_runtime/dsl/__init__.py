"""
Workflow DSL Module

Python decorator-based domain-specific language for defining workflows.
Provides a clean, readable syntax for workflow definition that compiles
to WorkflowDefinitionCreate models.
"""

from .workflow_dsl import (
    workflow,
    step,
    compensation,
    approval_step,
    service_step,
    parallel_step,
    conditional_step,
    subworkflow_step,
    WorkflowBuilder,
    StepDefinition,
    CompilationError,
)

__all__ = [
    "workflow",
    "step",
    "compensation",
    "approval_step",
    "service_step",
    "parallel_step",
    "conditional_step",
    "subworkflow_step",
    "WorkflowBuilder",
    "StepDefinition",
    "CompilationError",
]

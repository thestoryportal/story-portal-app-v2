"""
Workflow Data Models

Models for graph-based agent workflows (LangGraph pattern).
Based on Section 4.1.2 of agent-runtime-layer-specification-v1.2-final-ASCII.md
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List
from uuid import uuid4


class NodeType(Enum):
    """Type of workflow node"""
    AGENT = "agent"               # Agent execution node
    CONDITIONAL = "conditional"   # Conditional routing
    PARALLEL = "parallel"         # Parallel execution
    END = "end"                   # Terminal node


class WorkflowState(Enum):
    """Workflow execution state"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SUSPENDED = "suspended"


@dataclass
class WorkflowNode:
    """
    Single node in a workflow graph.

    Supports agent execution, conditional routing, and parallel branches.
    """
    node_id: str
    node_type: NodeType
    config: Dict[str, Any] = field(default_factory=dict)
    edges: List[str] = field(default_factory=list)  # Target node IDs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "config": self.config,
            "edges": self.edges,
        }


@dataclass
class WorkflowGraph:
    """
    Complete workflow graph definition.

    Represents a DAG (or cyclic graph) of agent execution nodes.
    """
    graph_id: str = field(default_factory=lambda: str(uuid4()))
    nodes: List[WorkflowNode] = field(default_factory=list)
    entry_node: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "nodes": [node.to_dict() for node in self.nodes],
            "entry_node": self.entry_node,
        }


@dataclass
class WorkflowExecution:
    """
    Runtime state of a workflow execution.

    Tracks current node and execution state for resumable workflows.
    """
    execution_id: str = field(default_factory=lambda: str(uuid4()))
    graph_id: str = ""
    current_node: str = ""
    state: WorkflowState = WorkflowState.PENDING
    execution_state: Dict[str, Any] = field(default_factory=dict)
    visited_nodes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "graph_id": self.graph_id,
            "current_node": self.current_node,
            "state": self.state.value,
            "execution_state": self.execution_state,
            "visited_nodes": self.visited_nodes,
        }

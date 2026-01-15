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


class ExecutionStatus(Enum):
    """Status of workflow execution"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


@dataclass
class WorkflowEdge:
    """
    Edge connecting two nodes in a workflow graph.

    Supports conditional routing with optional condition expressions.
    """
    source: str                           # Source node ID
    target: str                           # Target node ID
    condition: str = ""                   # Optional condition expression

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "condition": self.condition,
        }


@dataclass
class WorkflowNode:
    """
    Single node in a workflow graph.

    Supports agent execution, conditional routing, and parallel branches.
    """
    node_id: str
    node_type: NodeType
    name: str = ""
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "name": self.name,
            "config": self.config,
        }


@dataclass
class WorkflowGraph:
    """
    Complete workflow graph definition.

    Represents a DAG (or cyclic graph) of agent execution nodes.
    """
    graph_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    nodes: Dict[str, WorkflowNode] = field(default_factory=dict)  # node_id -> WorkflowNode
    edges: List[WorkflowEdge] = field(default_factory=list)       # List of edges
    entry_node: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "name": self.name,
            "nodes": {node_id: node.to_dict() for node_id, node in self.nodes.items()},
            "edges": [edge.to_dict() for edge in self.edges],
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

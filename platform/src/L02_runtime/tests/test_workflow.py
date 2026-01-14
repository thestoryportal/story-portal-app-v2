"""
Tests for Workflow Engine

Basic tests for graph-based workflow execution.
"""

import pytest
import asyncio

from ..services.workflow_engine import WorkflowEngine, WorkflowError
from ..models.workflow_models import (
    WorkflowGraph,
    WorkflowNode,
    WorkflowEdge,
    NodeType,
)


@pytest.fixture
def workflow_engine():
    """Create WorkflowEngine instance"""
    return WorkflowEngine(config={
        "max_graph_depth": 10,
        "max_parallel_branches": 5,
        "cycle_detection": True,
        "checkpoint_on_node_complete": False,  # Disable for tests
        "timeout_seconds": 30,
    })


@pytest.fixture
def simple_graph():
    """Create a simple workflow graph"""
    graph = WorkflowGraph(
        graph_id="test-graph-1",
        name="Simple Test Graph",
        entry_node="start",
    )

    # Add nodes
    start_node = WorkflowNode(
        node_id="start",
        node_type=NodeType.AGENT,
        name="Start Node",
        config={"input": {}, "output_key": "start_result"},
    )

    end_node = WorkflowNode(
        node_id="end",
        node_type=NodeType.END,
        name="End Node",
        config={},
    )

    graph.nodes["start"] = start_node
    graph.nodes["end"] = end_node

    # Add edge
    edge = WorkflowEdge(
        source="start",
        target="end",
    )
    graph.edges.append(edge)

    return graph


@pytest.mark.asyncio
async def test_workflow_engine_initialization(workflow_engine):
    """Test workflow engine initialization"""
    await workflow_engine.initialize()
    assert workflow_engine.max_graph_depth == 10
    assert workflow_engine.max_parallel_branches == 5
    assert workflow_engine.cycle_detection is True


@pytest.mark.asyncio
async def test_register_node_handler(workflow_engine):
    """Test node handler registration"""
    await workflow_engine.initialize()

    async def custom_handler(node, context):
        return {"custom": True}

    workflow_engine.register_node_handler("custom", custom_handler)

    assert "custom" in workflow_engine._node_handlers


@pytest.mark.asyncio
async def test_simple_workflow_execution(workflow_engine, simple_graph):
    """Test execution of simple workflow"""
    await workflow_engine.initialize()

    result = await workflow_engine.execute_workflow(
        workflow_id="test-workflow-1",
        graph=simple_graph,
        initial_state={"input": "test"},
    )

    assert "start_result" in result
    assert result["input"] == "test"


@pytest.mark.asyncio
async def test_workflow_depth_limit(workflow_engine):
    """Test workflow depth limit enforcement"""
    await workflow_engine.initialize()

    # Create a deep graph that exceeds limit
    graph = WorkflowGraph(
        graph_id="deep-graph",
        name="Deep Graph",
        entry_node="node-0",
    )

    # Create chain longer than depth limit
    for i in range(15):  # Exceeds limit of 10
        node = WorkflowNode(
            node_id=f"node-{i}",
            node_type=NodeType.AGENT,
            name=f"Node {i}",
            config={},
        )
        graph.nodes[f"node-{i}"] = node

        if i < 14:
            edge = WorkflowEdge(source=f"node-{i}", target=f"node-{i+1}")
            graph.edges.append(edge)

    with pytest.raises(WorkflowError) as exc_info:
        await workflow_engine.execute_workflow(
            workflow_id="deep-workflow",
            graph=graph,
        )

    assert exc_info.value.code == "E2011"


@pytest.mark.asyncio
async def test_workflow_cycle_detection(workflow_engine):
    """Test cycle detection"""
    await workflow_engine.initialize()

    # Create graph with cycle
    graph = WorkflowGraph(
        graph_id="cycle-graph",
        name="Cycle Graph",
        entry_node="node-1",
    )

    node1 = WorkflowNode(
        node_id="node-1",
        node_type=NodeType.AGENT,
        name="Node 1",
        config={},
    )

    node2 = WorkflowNode(
        node_id="node-2",
        node_type=NodeType.AGENT,
        name="Node 2",
        config={},
    )

    graph.nodes["node-1"] = node1
    graph.nodes["node-2"] = node2

    # Create cycle: node1 -> node2 -> node1
    graph.edges.append(WorkflowEdge(source="node-1", target="node-2"))
    graph.edges.append(WorkflowEdge(source="node-2", target="node-1"))

    with pytest.raises(WorkflowError) as exc_info:
        await workflow_engine.execute_workflow(
            workflow_id="cycle-workflow",
            graph=graph,
        )

    assert exc_info.value.code == "E2010"


@pytest.mark.asyncio
async def test_get_execution_status(workflow_engine, simple_graph):
    """Test execution status retrieval"""
    await workflow_engine.initialize()

    # Start workflow in background
    task = asyncio.create_task(
        workflow_engine.execute_workflow(
            workflow_id="status-workflow",
            graph=simple_graph,
        )
    )

    # Give it a moment to start
    await asyncio.sleep(0.1)

    status = await workflow_engine.get_execution_status("status-workflow")

    # May be None if completed too quickly
    if status:
        assert status["workflow_id"] == "status-workflow"
        assert "started_at" in status

    # Wait for completion
    await task


@pytest.mark.asyncio
async def test_cleanup(workflow_engine):
    """Test workflow engine cleanup"""
    await workflow_engine.initialize()

    await workflow_engine.cleanup()

    assert len(workflow_engine._active_executions) == 0

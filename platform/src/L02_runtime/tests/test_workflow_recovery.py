"""
Tests for Workflow Engine Recovery

Tests for workflow resume from checkpoint.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from ..services.workflow_engine import (
    WorkflowEngine,
    WorkflowError,
    ExecutionContext,
)
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
        "max_graph_depth": 50,
        "checkpoint_on_node_complete": True,
        "timeout_seconds": 60,
    })


@pytest.fixture
def mock_state_manager():
    """Create mock StateManager"""
    manager = MagicMock()
    manager.save_hot_state = AsyncMock()
    manager.load_hot_state = AsyncMock()
    manager.restore_checkpoint = AsyncMock()
    return manager


@pytest.fixture
def simple_graph():
    """Create a simple workflow graph"""
    nodes = {
        "start": WorkflowNode(
            node_id="start",
            node_type=NodeType.AGENT,
            config={"input": "Start task"},
        ),
        "middle": WorkflowNode(
            node_id="middle",
            node_type=NodeType.AGENT,
            config={"input": "Middle task"},
        ),
        "end": WorkflowNode(
            node_id="end",
            node_type=NodeType.END,
            config={},
        ),
    }
    edges = [
        WorkflowEdge(source="start", target="middle"),
        WorkflowEdge(source="middle", target="end"),
    ]
    return WorkflowGraph(
        nodes=nodes,
        edges=edges,
        entry_node="start",
    )


class TestWorkflowRecovery:
    """Tests for workflow recovery functionality"""

    @pytest.mark.asyncio
    async def test_serialize_graph(self, workflow_engine, simple_graph):
        """Test graph serialization for checkpointing"""
        await workflow_engine.initialize()

        serialized = workflow_engine._serialize_graph(simple_graph)

        assert "nodes" in serialized
        assert "edges" in serialized
        assert "entry_node" in serialized
        assert serialized["entry_node"] == "start"
        assert len(serialized["nodes"]) == 3
        assert len(serialized["edges"]) == 2

        # Check node serialization
        assert serialized["nodes"]["start"]["node_type"] == "agent"
        assert serialized["nodes"]["end"]["node_type"] == "end"

    @pytest.mark.asyncio
    async def test_reconstruct_graph(
        self,
        workflow_engine,
        simple_graph,
        mock_state_manager
    ):
        """Test graph reconstruction from checkpoint"""
        await workflow_engine.initialize(state_manager=mock_state_manager)

        # Serialize first
        serialized = workflow_engine._serialize_graph(simple_graph)

        # Create checkpoint data
        checkpoint_data = {"graph": serialized}

        # Reconstruct
        reconstructed = await workflow_engine._reconstruct_graph(
            checkpoint_data,
            "test-workflow"
        )

        assert reconstructed is not None
        assert reconstructed.entry_node == "start"
        assert len(reconstructed.nodes) == 3
        assert len(reconstructed.edges) == 2
        assert reconstructed.nodes["start"].node_type == NodeType.AGENT

    @pytest.mark.asyncio
    async def test_find_resume_node_from_empty_path(
        self,
        workflow_engine,
        simple_graph
    ):
        """Test finding resume node from empty path"""
        await workflow_engine.initialize()

        context = ExecutionContext(
            workflow_id="test",
            graph=simple_graph,
        )

        resume_node = await workflow_engine._find_resume_node(context, [])

        assert resume_node == "start"

    @pytest.mark.asyncio
    async def test_find_resume_node_from_middle(
        self,
        workflow_engine,
        simple_graph
    ):
        """Test finding resume node after partial execution"""
        await workflow_engine.initialize()

        context = ExecutionContext(
            workflow_id="test",
            graph=simple_graph,
            visited_nodes={"start"},
        )

        resume_node = await workflow_engine._find_resume_node(
            context,
            ["start"]
        )

        assert resume_node == "middle"

    @pytest.mark.asyncio
    async def test_find_resume_node_at_end(
        self,
        workflow_engine,
        simple_graph
    ):
        """Test finding resume node when already at end"""
        await workflow_engine.initialize()

        context = ExecutionContext(
            workflow_id="test",
            graph=simple_graph,
            visited_nodes={"start", "middle", "end"},
        )

        # Last node was end node
        resume_node = await workflow_engine._find_resume_node(
            context,
            ["start", "middle", "end"]
        )

        assert resume_node is None

    @pytest.mark.asyncio
    async def test_resume_workflow_from_checkpoint(
        self,
        workflow_engine,
        simple_graph,
        mock_state_manager
    ):
        """Test resuming workflow from checkpoint"""
        await workflow_engine.initialize(state_manager=mock_state_manager)

        # Create checkpoint at "start" node
        serialized_graph = workflow_engine._serialize_graph(simple_graph)
        checkpoint_data = {
            "workflow_id": "test-workflow",
            "state": {"start": {"success": True}},
            "visited_nodes": ["start"],
            "execution_path": ["start"],
            "depth": 1,
            "graph": serialized_graph,
        }

        mock_state_manager.load_hot_state.return_value = checkpoint_data

        # Resume workflow
        result = await workflow_engine.resume_workflow("test-workflow")

        assert result is not None
        # Should have executed middle and end nodes
        assert "middle" in result or "state" in result

    @pytest.mark.asyncio
    async def test_resume_workflow_no_checkpoint(
        self,
        workflow_engine,
        mock_state_manager
    ):
        """Test resume fails when no checkpoint exists"""
        await workflow_engine.initialize(state_manager=mock_state_manager)

        mock_state_manager.load_hot_state.return_value = None

        with pytest.raises(WorkflowError) as exc_info:
            await workflow_engine.resume_workflow("nonexistent")

        assert exc_info.value.code == "E2012"

    @pytest.mark.asyncio
    async def test_checkpoint_includes_graph(
        self,
        workflow_engine,
        simple_graph,
        mock_state_manager
    ):
        """Test that checkpoints include graph data"""
        await workflow_engine.initialize(state_manager=mock_state_manager)

        context = ExecutionContext(
            workflow_id="test-workflow",
            graph=simple_graph,
            state={"key": "value"},
            execution_path=["start"],
        )

        await workflow_engine._checkpoint_workflow(context)

        # Verify checkpoint includes graph
        call_args = mock_state_manager.save_hot_state.call_args
        state_data = call_args.kwargs.get("state_data") or call_args[1].get("state_data")
        assert "graph" in state_data
        assert state_data["graph"]["entry_node"] == "start"

    @pytest.mark.asyncio
    async def test_execute_from_node(
        self,
        workflow_engine,
        simple_graph,
        mock_state_manager
    ):
        """Test executing workflow from a specific node"""
        await workflow_engine.initialize(state_manager=mock_state_manager)

        context = ExecutionContext(
            workflow_id="test-workflow",
            graph=simple_graph,
            state={},
            visited_nodes={"start"},
            execution_path=["start"],
            depth=1,
        )

        result = await workflow_engine._execute_from_node(context, "middle")

        assert result is not None
        # Middle and end nodes should have been executed
        assert "middle" in context.execution_path
        assert "end" in context.execution_path

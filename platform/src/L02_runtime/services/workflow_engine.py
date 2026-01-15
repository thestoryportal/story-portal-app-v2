"""
Workflow Engine

Executes graph-based agent workflows with conditional routing and parallel execution.
Implements state machine patterns inspired by LangGraph.

Based on Section 3.3.2 of agent-runtime-layer-specification-v1.2-final-ASCII.md
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable, Set
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

from ..models.workflow_models import (
    WorkflowGraph,
    WorkflowNode,
    WorkflowEdge,
    WorkflowState,
    NodeType,
    ExecutionStatus,
)


logger = logging.getLogger(__name__)


class WorkflowError(Exception):
    """Workflow execution error"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


@dataclass
class ExecutionContext:
    """Workflow execution context"""
    workflow_id: str
    graph: WorkflowGraph
    state: Dict[str, Any] = field(default_factory=dict)
    visited_nodes: Set[str] = field(default_factory=set)
    execution_path: List[str] = field(default_factory=list)
    depth: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class WorkflowEngine:
    """
    Executes graph-based workflows with state machine logic.

    Responsibilities:
    - Execute workflow graphs
    - Handle conditional routing
    - Support parallel execution
    - Detect cycles and enforce depth limits
    - Checkpoint workflow state
    - Track execution progress
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize WorkflowEngine.

        Args:
            config: Configuration dict with:
                - max_graph_depth: Maximum graph depth
                - max_parallel_branches: Maximum parallel branches
                - cycle_detection: Enable cycle detection
                - checkpoint_on_node_complete: Checkpoint after each node
                - timeout_seconds: Workflow timeout
        """
        self.config = config or {}

        # Configuration
        self.max_graph_depth = self.config.get("max_graph_depth", 100)
        self.max_parallel_branches = self.config.get("max_parallel_branches", 10)
        self.cycle_detection = self.config.get("cycle_detection", True)
        self.checkpoint_on_node_complete = self.config.get(
            "checkpoint_on_node_complete", True
        )
        self.workflow_timeout = self.config.get("timeout_seconds", 3600)

        # Node handlers: node_type -> callable
        self._node_handlers: Dict[str, Callable] = {}

        # Active executions: workflow_id -> ExecutionContext
        self._active_executions: Dict[str, ExecutionContext] = {}

        # Dependencies (to be injected)
        self._agent_executor = None
        self._state_manager = None

        logger.info(
            f"WorkflowEngine initialized: "
            f"max_depth={self.max_graph_depth}, "
            f"max_parallel={self.max_parallel_branches}"
        )

    async def initialize(
        self,
        agent_executor=None,
        state_manager=None
    ) -> None:
        """
        Initialize workflow engine.

        Args:
            agent_executor: AgentExecutor instance
            state_manager: StateManager instance
        """
        self._agent_executor = agent_executor
        self._state_manager = state_manager

        # Register default node handlers
        self.register_node_handler("agent", self._execute_agent_node)
        self.register_node_handler("conditional", self._execute_conditional_node)
        self.register_node_handler("parallel", self._execute_parallel_node)
        self.register_node_handler("end", self._execute_end_node)

        logger.info("WorkflowEngine initialization complete")

    def register_node_handler(
        self,
        node_type: str,
        handler: Callable
    ) -> None:
        """
        Register a handler for a node type.

        Args:
            node_type: Type of node
            handler: Async callable(node, context) -> result
        """
        self._node_handlers[node_type] = handler
        logger.info(f"Registered node handler: {node_type}")

    async def execute_workflow(
        self,
        workflow_id: str,
        graph: WorkflowGraph,
        initial_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a workflow graph.

        Args:
            workflow_id: Workflow identifier
            graph: Workflow graph to execute
            initial_state: Optional initial state

        Returns:
            Final workflow state

        Raises:
            WorkflowError: If execution fails
        """
        logger.info(f"Executing workflow {workflow_id}")

        # Create execution context
        context = ExecutionContext(
            workflow_id=workflow_id,
            graph=graph,
            state=initial_state or {},
            started_at=datetime.now(timezone.utc),
        )

        self._active_executions[workflow_id] = context

        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                self._execute_graph(context),
                timeout=self.workflow_timeout
            )

            context.completed_at = datetime.now(timezone.utc)

            logger.info(
                f"Workflow {workflow_id} completed successfully "
                f"(nodes executed: {len(context.execution_path)})"
            )

            return result

        except asyncio.TimeoutError:
            raise WorkflowError(
                code="E2013",
                message=f"Workflow timeout after {self.workflow_timeout}s"
            )
        except WorkflowError:
            raise
        except Exception as e:
            logger.error(f"Workflow {workflow_id} failed: {e}")
            raise WorkflowError(
                code="E2012",
                message=f"Workflow execution failed: {str(e)}"
            )
        finally:
            if workflow_id in self._active_executions:
                del self._active_executions[workflow_id]

    async def _execute_graph(
        self,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """
        Execute workflow graph starting from entry node.

        Args:
            context: Execution context

        Returns:
            Final state
        """
        # Find entry node
        entry_node = context.graph.entry_node
        if not entry_node:
            raise WorkflowError(
                code="E2012",
                message="No entry node found in graph"
            )

        # Execute from entry node
        await self._execute_node(entry_node, context)

        return context.state

    async def _execute_node(
        self,
        node_id: str,
        context: ExecutionContext
    ) -> Any:
        """
        Execute a single node.

        Args:
            node_id: Node to execute
            context: Execution context

        Returns:
            Node execution result
        """
        # Check depth limit
        if context.depth >= self.max_graph_depth:
            raise WorkflowError(
                code="E2011",
                message=f"Max graph depth ({self.max_graph_depth}) exceeded"
            )

        # Get node
        node = context.graph.nodes.get(node_id)
        if not node:
            raise WorkflowError(
                code="E2012",
                message=f"Node {node_id} not found in graph"
            )

        # Cycle detection
        if self.cycle_detection and node_id in context.visited_nodes:
            logger.warning(f"Cycle detected at node {node_id}")
            raise WorkflowError(
                code="E2010",
                message=f"Graph cycle detected at node {node_id}"
            )

        # Mark as visited
        context.visited_nodes.add(node_id)
        context.execution_path.append(node_id)
        context.depth += 1

        logger.debug(f"Executing node {node_id} (type={node.node_type.value})")

        try:
            # Get handler for node type
            handler = self._node_handlers.get(node.node_type.value)
            if not handler:
                raise WorkflowError(
                    code="E2012",
                    message=f"No handler for node type {node.node_type.value}"
                )

            # Execute node
            result = await handler(node, context)

            # Checkpoint if enabled
            if self.checkpoint_on_node_complete and self._state_manager:
                await self._checkpoint_workflow(context)

            # Continue to next node(s) based on result
            next_nodes = self._get_next_nodes(node, result, context)

            if not next_nodes:
                # End of execution
                return result

            # Execute next nodes
            if len(next_nodes) == 1:
                # Sequential execution
                return await self._execute_node(next_nodes[0], context)
            else:
                # This shouldn't happen in sequential flow
                # Parallel nodes handle their own children
                logger.warning(f"Multiple next nodes from sequential node: {next_nodes}")
                return result

        except WorkflowError:
            raise
        except Exception as e:
            logger.error(f"Node {node_id} execution failed: {e}")
            raise WorkflowError(
                code="E2012",
                message=f"Node execution failed: {str(e)}"
            )
        finally:
            context.depth -= 1

    def _get_next_nodes(
        self,
        node: WorkflowNode,
        result: Any,
        context: ExecutionContext
    ) -> List[str]:
        """
        Get next nodes to execute based on current node and result.

        Args:
            node: Current node
            result: Node execution result
            context: Execution context

        Returns:
            List of next node IDs
        """
        # Get outgoing edges
        edges = [
            edge for edge in context.graph.edges
            if edge.source == node.node_id
        ]

        if not edges:
            return []

        # For conditional nodes, evaluate condition
        if node.node_type == NodeType.CONDITIONAL:
            for edge in edges:
                if edge.condition:
                    # Evaluate condition
                    if self._evaluate_condition(edge.condition, result, context):
                        return [edge.target]
            # No condition matched, use default if available
            default_edges = [e for e in edges if not e.condition]
            if default_edges:
                return [default_edges[0].target]
            return []

        # For other nodes, follow first edge
        return [edges[0].target]

    def _evaluate_condition(
        self,
        condition: str,
        result: Any,
        context: ExecutionContext
    ) -> bool:
        """
        Evaluate a condition string.

        Args:
            condition: Condition expression
            result: Current node result
            context: Execution context

        Returns:
            True if condition is met
        """
        # TODO: Implement proper condition evaluation
        # For now, simple string matching
        if condition == "success":
            return bool(result)
        elif condition == "failure":
            return not bool(result)
        else:
            return False

    async def _execute_agent_node(
        self,
        node: WorkflowNode,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Execute agent node"""
        logger.debug(f"Executing agent node: {node.node_id}")

        # Extract input from state
        input_data = node.config.get("input", {})
        if isinstance(input_data, str):
            # Reference to state key
            input_data = context.state.get(input_data, {})

        # Execute agent (stub)
        # TODO: Integrate with actual agent executor
        result = {
            "node_id": node.node_id,
            "output": f"Agent {node.node_id} executed",
            "success": True,
        }

        # Store result in state
        output_key = node.config.get("output_key", node.node_id)
        context.state[output_key] = result

        return result

    async def _execute_conditional_node(
        self,
        node: WorkflowNode,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Execute conditional node"""
        logger.debug(f"Executing conditional node: {node.node_id}")

        # Evaluate condition based on state
        condition_key = node.config.get("condition_key")
        condition_value = context.state.get(condition_key)

        result = {
            "node_id": node.node_id,
            "condition_key": condition_key,
            "condition_value": condition_value,
        }

        return result

    async def _execute_parallel_node(
        self,
        node: WorkflowNode,
        context: ExecutionContext
    ) -> List[Dict[str, Any]]:
        """Execute parallel node"""
        logger.debug(f"Executing parallel node: {node.node_id}")

        # Get child nodes to execute in parallel
        child_nodes = node.config.get("children", [])

        if len(child_nodes) > self.max_parallel_branches:
            raise WorkflowError(
                code="E2013",
                message=f"Parallel branch limit ({self.max_parallel_branches}) exceeded"
            )

        # Execute children in parallel
        tasks = [
            self._execute_node(child_id, context)
            for child_id in child_nodes
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check for failures
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Parallel branch {child_nodes[i]} failed: {result}")
                raise WorkflowError(
                    code="E2013",
                    message=f"Parallel branch failed: {str(result)}"
                )

        return list(results)

    async def _execute_end_node(
        self,
        node: WorkflowNode,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Execute end node"""
        logger.debug(f"Executing end node: {node.node_id}")

        return {
            "node_id": node.node_id,
            "final_state": context.state,
            "completed": True,
        }

    async def _checkpoint_workflow(
        self,
        context: ExecutionContext
    ) -> None:
        """Save workflow checkpoint"""
        if not self._state_manager:
            return

        try:
            checkpoint_data = {
                "workflow_id": context.workflow_id,
                "state": context.state,
                "visited_nodes": list(context.visited_nodes),
                "execution_path": context.execution_path,
                "depth": context.depth,
            }

            await self._state_manager.save_hot_state(
                agent_id=context.workflow_id,
                state_data=checkpoint_data
            )

        except Exception as e:
            logger.warning(f"Failed to checkpoint workflow: {e}")

    async def get_execution_status(
        self,
        workflow_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get execution status for a workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Status information or None if not found
        """
        context = self._active_executions.get(workflow_id)
        if not context:
            return None

        return {
            "workflow_id": workflow_id,
            "started_at": context.started_at.isoformat() if context.started_at else None,
            "nodes_executed": len(context.execution_path),
            "current_depth": context.depth,
            "execution_path": context.execution_path,
        }

    async def cleanup(self) -> None:
        """Cleanup with timeout protection."""
        logger.info("Cleaning up WorkflowEngine")
        try:
            async with asyncio.timeout(2.0):
                # Clear active executions and handlers
                self._active_executions.clear()
                self._node_handlers.clear()
        except asyncio.TimeoutError:
            logger.warning("WorkflowEngine cleanup timed out")
            pass
        finally:
            # Force clear even on timeout
            self._active_executions.clear()
            self._node_handlers.clear()
        logger.info("WorkflowEngine cleanup complete")

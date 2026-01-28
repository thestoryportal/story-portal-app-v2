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

        Supports multiple condition types:
        - "success" / "failure": Boolean result check
        - "state.key == value": State key comparison
        - "result.key == value": Result key comparison
        - "state.key > value": Numeric comparisons
        - "state.key in [val1, val2]": Membership test

        Args:
            condition: Condition expression
            result: Current node result
            context: Execution context

        Returns:
            True if condition is met
        """
        try:
            # Simple boolean conditions
            if condition == "success":
                if isinstance(result, dict):
                    return result.get("success", True)
                return bool(result)
            elif condition == "failure":
                if isinstance(result, dict):
                    return not result.get("success", True)
                return not bool(result)
            elif condition == "always":
                return True
            elif condition == "never":
                return False

            # State-based conditions: state.key == value
            if condition.startswith("state."):
                return self._evaluate_state_condition(condition, context.state)

            # Result-based conditions: result.key == value
            if condition.startswith("result."):
                return self._evaluate_result_condition(condition, result)

            # Expression-based condition (safe evaluation)
            return self._evaluate_expression(condition, result, context)

        except Exception as e:
            logger.warning(f"Condition evaluation failed: {condition}, error: {e}")
            return False

    def _evaluate_state_condition(
        self,
        condition: str,
        state: Dict[str, Any]
    ) -> bool:
        """Evaluate state-based condition."""
        # Parse condition: state.key op value
        import re

        # Match patterns like: state.key == "value" or state.key > 10
        pattern = r'state\.(\w+(?:\.\w+)*)\s*(==|!=|>|<|>=|<=|in)\s*(.+)'
        match = re.match(pattern, condition)

        if not match:
            return False

        key_path, operator, value_str = match.groups()

        # Get value from state using dot notation
        current = state
        for key in key_path.split('.'):
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return False

        # Parse the comparison value
        try:
            # Try to evaluate as Python literal
            import ast
            target_value = ast.literal_eval(value_str.strip())
        except (ValueError, SyntaxError):
            target_value = value_str.strip().strip('"\'')

        # Perform comparison
        if operator == "==":
            return current == target_value
        elif operator == "!=":
            return current != target_value
        elif operator == ">":
            return current > target_value
        elif operator == "<":
            return current < target_value
        elif operator == ">=":
            return current >= target_value
        elif operator == "<=":
            return current <= target_value
        elif operator == "in":
            return current in target_value

        return False

    def _evaluate_result_condition(
        self,
        condition: str,
        result: Any
    ) -> bool:
        """Evaluate result-based condition."""
        import re

        pattern = r'result\.(\w+(?:\.\w+)*)\s*(==|!=|>|<|>=|<=|in)\s*(.+)'
        match = re.match(pattern, condition)

        if not match:
            return False

        key_path, operator, value_str = match.groups()

        # Get value from result
        if not isinstance(result, dict):
            return False

        current = result
        for key in key_path.split('.'):
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return False

        try:
            import ast
            target_value = ast.literal_eval(value_str.strip())
        except (ValueError, SyntaxError):
            target_value = value_str.strip().strip('"\'')

        if operator == "==":
            return current == target_value
        elif operator == "!=":
            return current != target_value
        elif operator == ">":
            return current > target_value
        elif operator == "<":
            return current < target_value
        elif operator == ">=":
            return current >= target_value
        elif operator == "<=":
            return current <= target_value
        elif operator == "in":
            return current in target_value

        return False

    def _evaluate_expression(
        self,
        condition: str,
        result: Any,
        context: ExecutionContext
    ) -> bool:
        """Safely evaluate an expression condition."""
        # Build a safe evaluation context
        safe_context = {
            "result": result if isinstance(result, dict) else {"value": result},
            "state": context.state,
            "depth": context.depth,
            "visited_count": len(context.visited_nodes),
            "True": True,
            "False": False,
            "None": None,
        }

        # Only allow safe operations
        allowed_names = set(safe_context.keys())

        try:
            import ast

            # Parse the expression
            tree = ast.parse(condition, mode='eval')

            # Check for unsafe operations
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and node.id not in allowed_names:
                    # Allow checking dict keys
                    pass
                elif isinstance(node, (ast.Call, ast.Import, ast.ImportFrom)):
                    # Disallow function calls and imports
                    return False

            # Evaluate safely
            code = compile(tree, '<condition>', 'eval')
            return bool(eval(code, {"__builtins__": {}}, safe_context))

        except Exception:
            return False

    async def _execute_agent_node(
        self,
        node: WorkflowNode,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """
        Execute agent node with actual AgentExecutor integration.

        Supports:
        - Direct agent execution via AgentExecutor
        - Input mapping from workflow state
        - Output storage to workflow state
        - Timeout enforcement
        - Error handling with retry option
        """
        logger.debug(f"Executing agent node: {node.node_id}")

        # Extract input from state
        input_data = node.config.get("input", {})
        if isinstance(input_data, str):
            # Reference to state key
            input_data = context.state.get(input_data, {})
        elif isinstance(input_data, dict):
            # Template substitution from state
            input_data = self._substitute_template(input_data, context.state)

        # Get agent configuration
        agent_id = node.config.get("agent_id", f"workflow_{context.workflow_id}")
        agent_type = node.config.get("agent_type", "generic")
        timeout = node.config.get("timeout_seconds", 300)
        retry_count = node.config.get("retry_count", 0)
        retry_delay = node.config.get("retry_delay_seconds", 5)

        result = None
        last_error = None

        for attempt in range(retry_count + 1):
            try:
                # Execute via AgentExecutor if available
                if self._agent_executor:
                    result = await asyncio.wait_for(
                        self._execute_with_agent_executor(
                            agent_id=agent_id,
                            agent_type=agent_type,
                            input_data=input_data,
                            node_config=node.config,
                            context=context
                        ),
                        timeout=timeout
                    )
                else:
                    # Fallback to simulation mode
                    result = await self._simulate_agent_execution(
                        node=node,
                        input_data=input_data,
                        context=context
                    )

                # Success - break retry loop
                break

            except asyncio.TimeoutError:
                last_error = f"Agent execution timed out after {timeout}s"
                logger.warning(f"Agent node {node.node_id} timeout (attempt {attempt + 1})")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Agent node {node.node_id} failed (attempt {attempt + 1}): {e}")

            # Wait before retry
            if attempt < retry_count:
                await asyncio.sleep(retry_delay)

        # Handle final failure
        if result is None:
            result = {
                "node_id": node.node_id,
                "success": False,
                "error": last_error,
                "attempts": retry_count + 1,
            }

        # Ensure result has required fields
        if isinstance(result, dict):
            result.setdefault("node_id", node.node_id)
            result.setdefault("success", True)
        else:
            result = {
                "node_id": node.node_id,
                "output": result,
                "success": True,
            }

        # Store result in state
        output_key = node.config.get("output_key", node.node_id)
        context.state[output_key] = result

        return result

    async def _execute_with_agent_executor(
        self,
        agent_id: str,
        agent_type: str,
        input_data: Dict[str, Any],
        node_config: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Execute using the actual AgentExecutor."""
        # Build execution request
        task = input_data.get("task", input_data.get("prompt", str(input_data)))

        # Execute via AgentExecutor
        execution_result = await self._agent_executor.execute(
            agent_id=agent_id,
            task=task,
            context={
                "workflow_id": context.workflow_id,
                "execution_path": context.execution_path,
                "state": context.state,
                **node_config.get("context", {})
            }
        )

        return {
            "node_id": node_config.get("node_id"),
            "output": execution_result.get("result", execution_result),
            "success": execution_result.get("success", True),
            "agent_id": agent_id,
            "execution_id": execution_result.get("execution_id"),
        }

    async def _simulate_agent_execution(
        self,
        node: WorkflowNode,
        input_data: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Simulate agent execution for testing."""
        # Simulate processing time
        await asyncio.sleep(0.1)

        return {
            "node_id": node.node_id,
            "output": f"Simulated agent execution for {node.node_id}",
            "input_received": input_data,
            "success": True,
            "simulated": True,
        }

    def _substitute_template(
        self,
        template: Dict[str, Any],
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Substitute template variables from state."""
        result = {}

        for key, value in template.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                # Template variable: ${state_key}
                state_key = value[2:-1]
                result[key] = state.get(state_key, value)
            elif isinstance(value, dict):
                result[key] = self._substitute_template(value, state)
            else:
                result[key] = value

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
        """Save workflow checkpoint with graph for recovery"""
        if not self._state_manager:
            return

        try:
            # Serialize graph for recovery
            graph_data = self._serialize_graph(context.graph)

            checkpoint_data = {
                "workflow_id": context.workflow_id,
                "state": context.state,
                "visited_nodes": list(context.visited_nodes),
                "execution_path": context.execution_path,
                "depth": context.depth,
                "graph": graph_data,
                "checkpoint_time": datetime.now(timezone.utc).isoformat(),
            }

            await self._state_manager.save_hot_state(
                agent_id=context.workflow_id,
                state_data=checkpoint_data
            )

        except Exception as e:
            logger.warning(f"Failed to checkpoint workflow: {e}")

    def _serialize_graph(self, graph: WorkflowGraph) -> Dict[str, Any]:
        """
        Serialize workflow graph for checkpoint storage.

        Args:
            graph: WorkflowGraph to serialize

        Returns:
            Serialized graph data
        """
        nodes_data = {}
        for node_id, node in graph.nodes.items():
            nodes_data[node_id] = {
                "node_id": node.node_id,
                "node_type": node.node_type.value,
                "config": node.config,
            }

        edges_data = []
        for edge in graph.edges:
            edges_data.append({
                "source": edge.source,
                "target": edge.target,
                "condition": edge.condition,
            })

        return {
            "nodes": nodes_data,
            "edges": edges_data,
            "entry_node": graph.entry_node,
        }

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

    async def resume_workflow(
        self,
        workflow_id: str,
        checkpoint_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Resume a workflow from checkpoint.

        Args:
            workflow_id: Workflow to resume
            checkpoint_id: Optional specific checkpoint to resume from

        Returns:
            Final workflow state

        Raises:
            WorkflowError: If resume fails
        """
        logger.info(f"Resuming workflow {workflow_id} from checkpoint")

        if not self._state_manager:
            raise WorkflowError(
                code="E2012",
                message="StateManager required for workflow resume"
            )

        try:
            # Load checkpoint
            if checkpoint_id:
                snapshot = await self._state_manager.restore_checkpoint(checkpoint_id)
            else:
                # Get latest hot state
                hot_state = await self._state_manager.load_hot_state(workflow_id)
                if not hot_state:
                    raise WorkflowError(
                        code="E2012",
                        message=f"No checkpoint found for workflow {workflow_id}"
                    )
                snapshot = hot_state

            # Reconstruct context
            checkpoint_data = snapshot if isinstance(snapshot, dict) else snapshot.context

            # Find the last executed node
            execution_path = checkpoint_data.get("execution_path", [])
            if not execution_path:
                raise WorkflowError(
                    code="E2012",
                    message="Cannot resume: no execution path in checkpoint"
                )

            logger.info(
                f"Resuming workflow {workflow_id} from node {execution_path[-1]} "
                f"(path length: {len(execution_path)})"
            )

            # Reconstruct the graph from checkpoint
            graph = await self._reconstruct_graph(checkpoint_data, workflow_id)
            if not graph:
                raise WorkflowError(
                    code="E2012",
                    message="Cannot resume: graph not found in checkpoint"
                )

            # Create execution context from checkpoint
            context = ExecutionContext(
                workflow_id=workflow_id,
                graph=graph,
                state=checkpoint_data.get("state", {}),
                visited_nodes=set(checkpoint_data.get("visited_nodes", [])),
                execution_path=execution_path.copy(),
                depth=checkpoint_data.get("depth", 0),
                started_at=datetime.now(timezone.utc),
            )

            self._active_executions[workflow_id] = context

            # Find the resume node (next node after last executed)
            resume_node = await self._find_resume_node(context, execution_path)

            if not resume_node:
                # No more nodes to execute, workflow was already complete
                logger.info(f"Workflow {workflow_id} was already complete")
                return checkpoint_data.get("state", {})

            try:
                # Continue execution from resume node
                result = await asyncio.wait_for(
                    self._execute_from_node(context, resume_node),
                    timeout=self.workflow_timeout
                )

                context.completed_at = datetime.now(timezone.utc)

                logger.info(
                    f"Workflow {workflow_id} resumed and completed successfully "
                    f"(total nodes: {len(context.execution_path)})"
                )

                return result

            finally:
                if workflow_id in self._active_executions:
                    del self._active_executions[workflow_id]

        except WorkflowError:
            raise
        except Exception as e:
            logger.error(f"Failed to resume workflow {workflow_id}: {e}")
            raise WorkflowError(
                code="E2012",
                message=f"Workflow resume failed: {str(e)}"
            )

    async def _reconstruct_graph(
        self,
        checkpoint_data: Dict[str, Any],
        workflow_id: str
    ) -> Optional[WorkflowGraph]:
        """
        Reconstruct workflow graph from checkpoint data.

        Args:
            checkpoint_data: Checkpoint data containing graph info
            workflow_id: Workflow identifier

        Returns:
            Reconstructed WorkflowGraph or None
        """
        # Check if graph is embedded in checkpoint
        graph_data = checkpoint_data.get("graph")

        if graph_data:
            # Reconstruct from embedded graph data
            try:
                if isinstance(graph_data, WorkflowGraph):
                    return graph_data

                # Build graph from serialized data
                nodes = {}
                for node_id, node_data in graph_data.get("nodes", {}).items():
                    nodes[node_id] = WorkflowNode(
                        node_id=node_data.get("node_id", node_id),
                        node_type=NodeType(node_data.get("node_type", "agent")),
                        config=node_data.get("config", {}),
                    )

                edges = []
                for edge_data in graph_data.get("edges", []):
                    edges.append(WorkflowEdge(
                        source=edge_data.get("source"),
                        target=edge_data.get("target"),
                        condition=edge_data.get("condition"),
                    ))

                return WorkflowGraph(
                    nodes=nodes,
                    edges=edges,
                    entry_node=graph_data.get("entry_node"),
                )

            except Exception as e:
                logger.warning(f"Failed to reconstruct graph from checkpoint: {e}")

        # Try to load from state manager if available
        if self._state_manager:
            try:
                workflow_data = await self._state_manager.load_hot_state(
                    f"{workflow_id}_graph"
                )
                if workflow_data and "graph" in workflow_data:
                    return await self._reconstruct_graph(
                        {"graph": workflow_data["graph"]},
                        workflow_id
                    )
            except Exception as e:
                logger.warning(f"Failed to load graph from state manager: {e}")

        return None

    async def _find_resume_node(
        self,
        context: ExecutionContext,
        execution_path: List[str]
    ) -> Optional[str]:
        """
        Find the node to resume execution from.

        Args:
            context: Execution context
            execution_path: Executed nodes path

        Returns:
            Node ID to resume from, or None if complete
        """
        if not execution_path:
            # Start from entry node
            return context.graph.entry_node

        # Get the last executed node
        last_node_id = execution_path[-1]
        last_node = context.graph.nodes.get(last_node_id)

        if not last_node:
            logger.warning(f"Last node {last_node_id} not found in graph")
            return None

        # Check if last node was an end node
        if last_node.node_type == NodeType.END:
            return None

        # Find outgoing edges from last node
        outgoing_edges = [
            edge for edge in context.graph.edges
            if edge.source == last_node_id
        ]

        if not outgoing_edges:
            return None

        # For conditional nodes, we need the state to determine which edge
        # For simplicity, take the first edge that wasn't already visited
        for edge in outgoing_edges:
            if edge.target not in context.visited_nodes:
                return edge.target

        # All edges lead to visited nodes (potential cycle or complete)
        return None

    async def _execute_from_node(
        self,
        context: ExecutionContext,
        start_node_id: str
    ) -> Dict[str, Any]:
        """
        Execute workflow starting from a specific node.

        Args:
            context: Execution context
            start_node_id: Node to start from

        Returns:
            Final workflow state
        """
        logger.info(f"Executing workflow from node {start_node_id}")

        # Reset visited nodes for the new execution path
        # Keep the nodes that were already visited before checkpoint
        # but allow revisiting if needed for the new execution

        await self._execute_node(start_node_id, context)

        return context.state

    async def cancel_workflow(
        self,
        workflow_id: str,
        reason: str = "User requested cancellation"
    ) -> bool:
        """
        Cancel an active workflow.

        Args:
            workflow_id: Workflow to cancel
            reason: Cancellation reason

        Returns:
            True if cancelled, False if not found
        """
        context = self._active_executions.get(workflow_id)
        if not context:
            logger.warning(f"Workflow {workflow_id} not found for cancellation")
            return False

        logger.info(f"Cancelling workflow {workflow_id}: {reason}")

        # Save final checkpoint
        if self._state_manager:
            context.state["_cancelled"] = True
            context.state["_cancel_reason"] = reason
            await self._checkpoint_workflow(context)

        # Remove from active executions
        del self._active_executions[workflow_id]

        return True

    def list_active_workflows(self) -> List[Dict[str, Any]]:
        """List all active workflow executions."""
        return [
            {
                "workflow_id": wid,
                "started_at": ctx.started_at.isoformat() if ctx.started_at else None,
                "nodes_executed": len(ctx.execution_path),
                "current_depth": ctx.depth,
            }
            for wid, ctx in self._active_executions.items()
        ]

    def get_health_status(self) -> Dict[str, Any]:
        """Get workflow engine health status."""
        return {
            "healthy": True,
            "active_workflows": len(self._active_executions),
            "registered_handlers": list(self._node_handlers.keys()),
            "config": {
                "max_graph_depth": self.max_graph_depth,
                "max_parallel_branches": self.max_parallel_branches,
                "cycle_detection": self.cycle_detection,
                "checkpoint_enabled": self.checkpoint_on_node_complete,
                "timeout_seconds": self.workflow_timeout,
            },
            "state_manager_available": self._state_manager is not None,
            "agent_executor_available": self._agent_executor is not None,
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get workflow execution metrics."""
        return {
            "active_workflows": len(self._active_executions),
            "workflows_by_depth": {
                wid: ctx.depth
                for wid, ctx in self._active_executions.items()
            },
            "total_nodes_executed": sum(
                len(ctx.execution_path)
                for ctx in self._active_executions.values()
            ),
        }

    async def cleanup(self) -> None:
        """Cleanup with timeout protection."""
        logger.info("Cleaning up WorkflowEngine")
        try:
            async with asyncio.timeout(2.0):
                # Save checkpoints for active workflows
                for workflow_id, context in list(self._active_executions.items()):
                    try:
                        context.state["_cleanup_interrupted"] = True
                        await self._checkpoint_workflow(context)
                    except Exception as e:
                        logger.warning(f"Failed to checkpoint {workflow_id}: {e}")

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

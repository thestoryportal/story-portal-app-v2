"""
Tool Composer Service

Enables tool chaining and parallel execution for complex workflows.
Based on Section 3 architecture and Gap G-020.

Features:
- Sequential tool chaining with data flow
- Parallel tool execution with result aggregation
- Error handling and partial failure recovery
- Execution planning and optimization
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import uuid4

from ..models import (
    ToolInvokeRequest,
    ToolInvokeResponse,
    ToolStatus,
    ToolError,
    ErrorCode,
    ToolExecutionError,
)
from .tool_executor import ToolExecutor

logger = logging.getLogger(__name__)


class ToolComposer:
    """
    Tool composition engine for chaining and parallel execution.

    Orchestrates multi-tool workflows with dependencies and parallelism.
    """

    def __init__(self, tool_executor: ToolExecutor):
        """
        Initialize Tool Composer.

        Args:
            tool_executor: Tool executor instance
        """
        self.tool_executor = tool_executor

    async def execute_chain(
        self,
        requests: List[ToolInvokeRequest],
        propagate_results: bool = True
    ) -> List[ToolInvokeResponse]:
        """
        Execute tools sequentially in a chain.

        Each tool receives output from previous tool if propagate_results=True.

        Args:
            requests: List of tool invocation requests (in order)
            propagate_results: Pass results between tools

        Returns:
            List of tool responses (in order)
        """
        responses = []
        previous_result = None

        for i, request in enumerate(requests):
            try:
                # Inject previous result into parameters if enabled
                if propagate_results and previous_result:
                    request.parameters["_previous_result"] = previous_result

                # Execute tool
                response = await self.tool_executor.execute(request)
                responses.append(response)

                # Check for errors
                if response.status != ToolStatus.SUCCESS:
                    logger.warning(f"Tool chain failed at step {i+1}: {response.error}")
                    break

                # Extract result for next tool
                if response.result:
                    previous_result = response.result.result

            except Exception as e:
                logger.error(f"Tool chain execution failed at step {i+1}: {e}")
                responses.append(ToolInvokeResponse(
                    invocation_id=request.invocation_id,
                    status=ToolStatus.ERROR,
                    error=ToolError(
                        code=ErrorCode.E3108.value,
                        message=str(e),
                        details={"step": i+1, "tool_id": request.tool_id}
                    )
                ))
                break

        return responses

    async def execute_parallel(
        self,
        requests: List[ToolInvokeRequest],
        fail_fast: bool = False
    ) -> List[ToolInvokeResponse]:
        """
        Execute tools in parallel.

        Args:
            requests: List of tool invocation requests
            fail_fast: Stop execution if any tool fails

        Returns:
            List of tool responses (order matches requests)
        """
        tasks = []

        for request in requests:
            task = asyncio.create_task(self.tool_executor.execute(request))
            tasks.append(task)

        if fail_fast:
            # Use wait with FIRST_EXCEPTION
            done, pending = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_EXCEPTION
            )

            # Cancel remaining tasks if any failed
            if any(task.exception() for task in done):
                for task in pending:
                    task.cancel()

            # Gather results
            responses = []
            for task in tasks:
                if task.done():
                    try:
                        responses.append(await task)
                    except Exception as e:
                        logger.error(f"Parallel tool execution failed: {e}")
                        responses.append(ToolInvokeResponse(
                            invocation_id=uuid4(),
                            status=ToolStatus.ERROR,
                            error=ToolError(
                                code=ErrorCode.E3108.value,
                                message=str(e)
                            )
                        ))
                else:
                    # Task was cancelled
                    responses.append(ToolInvokeResponse(
                        invocation_id=uuid4(),
                        status=ToolStatus.CANCELLED
                    ))

            return responses

        else:
            # Wait for all tasks to complete
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # Convert exceptions to error responses
            result_responses = []
            for i, response in enumerate(responses):
                if isinstance(response, Exception):
                    logger.error(f"Parallel tool execution failed: {response}")
                    result_responses.append(ToolInvokeResponse(
                        invocation_id=requests[i].invocation_id,
                        status=ToolStatus.ERROR,
                        error=ToolError(
                            code=ErrorCode.E3108.value,
                            message=str(response),
                            details={"tool_id": requests[i].tool_id}
                        )
                    ))
                else:
                    result_responses.append(response)

            return result_responses

    async def execute_dag(
        self,
        workflow: Dict[str, Any]
    ) -> Dict[str, ToolInvokeResponse]:
        """
        Execute tools in a directed acyclic graph (DAG) workflow.

        Workflow format:
        {
            "nodes": {
                "tool1": {"request": ToolInvokeRequest, "depends_on": []},
                "tool2": {"request": ToolInvokeRequest, "depends_on": ["tool1"]},
            }
        }

        Args:
            workflow: DAG workflow specification

        Returns:
            Dictionary of node_id -> ToolInvokeResponse
        """
        nodes = workflow.get("nodes", {})
        results = {}
        completed = set()

        # Topological sort and execution
        async def execute_node(node_id: str):
            if node_id in completed:
                return

            node = nodes[node_id]
            dependencies = node.get("depends_on", [])

            # Wait for dependencies
            dep_tasks = []
            for dep_id in dependencies:
                if dep_id not in completed:
                    dep_tasks.append(execute_node(dep_id))

            if dep_tasks:
                await asyncio.gather(*dep_tasks)

            # Execute current node
            request = node["request"]

            # Inject dependency results
            for dep_id in dependencies:
                if dep_id in results and results[dep_id].result:
                    request.parameters[f"_dep_{dep_id}"] = results[dep_id].result.result

            # Execute tool
            response = await self.tool_executor.execute(request)
            results[node_id] = response
            completed.add(node_id)

        # Execute all nodes
        tasks = [execute_node(node_id) for node_id in nodes.keys()]
        await asyncio.gather(*tasks)

        return results

    def validate_workflow(self, workflow: Dict[str, Any]) -> bool:
        """
        Validate workflow DAG for cycles and missing dependencies.

        Args:
            workflow: DAG workflow specification

        Returns:
            True if valid, False otherwise
        """
        nodes = workflow.get("nodes", {})

        # Check for missing dependencies
        for node_id, node in nodes.items():
            dependencies = node.get("depends_on", [])
            for dep_id in dependencies:
                if dep_id not in nodes:
                    logger.error(f"Missing dependency {dep_id} for node {node_id}")
                    return False

        # Check for cycles using DFS
        visited = set()
        rec_stack = set()

        def has_cycle(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)

            node = nodes[node_id]
            dependencies = node.get("depends_on", [])

            for dep_id in dependencies:
                if dep_id not in visited:
                    if has_cycle(dep_id):
                        return True
                elif dep_id in rec_stack:
                    return True

            rec_stack.remove(node_id)
            return False

        for node_id in nodes.keys():
            if node_id not in visited:
                if has_cycle(node_id):
                    logger.error(f"Cycle detected in workflow at node {node_id}")
                    return False

        return True

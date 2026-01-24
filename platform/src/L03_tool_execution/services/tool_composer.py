"""
Tool Composer Service

Enables tool chaining and parallel execution for complex workflows.
Based on Section 3 architecture and Gap G-020.

Features:
- Sequential tool chaining with data flow
- Parallel tool execution with result aggregation
- Error handling and partial failure recovery
- Execution planning and optimization
- Conditional branching with expression evaluation
- Result caching for repeated compositions
"""

import asyncio
import logging
import hashlib
import json
from typing import List, Dict, Any, Optional, Callable, Union
from datetime import datetime, timezone
from uuid import uuid4
from dataclasses import dataclass, field
from functools import lru_cache

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


@dataclass
class CompositionResult:
    """Result of a tool composition execution."""
    composition_id: str
    status: str  # success, partial_failure, failed
    responses: List[ToolInvokeResponse]
    cached: bool = False
    execution_time_ms: float = 0.0
    error: Optional[str] = None


@dataclass
class ConditionalBranch:
    """Conditional branch definition for workflow branching."""
    condition: str  # Expression to evaluate
    then_requests: List[ToolInvokeRequest]
    else_requests: Optional[List[ToolInvokeRequest]] = None


@dataclass
class CacheEntry:
    """Cache entry for composition results."""
    result: CompositionResult
    created_at: datetime
    ttl_seconds: int
    hit_count: int = 0


class ToolComposer:
    """
    Tool composition engine for chaining and parallel execution.

    Orchestrates multi-tool workflows with dependencies and parallelism.
    Includes conditional branching and result caching for optimization.
    """

    def __init__(
        self,
        tool_executor: ToolExecutor,
        cache_enabled: bool = True,
        cache_ttl_seconds: int = 300,
        max_cache_entries: int = 1000
    ):
        """
        Initialize Tool Composer.

        Args:
            tool_executor: Tool executor instance
            cache_enabled: Enable result caching
            cache_ttl_seconds: Default cache TTL
            max_cache_entries: Maximum cache entries
        """
        self.tool_executor = tool_executor
        self.cache_enabled = cache_enabled
        self.cache_ttl_seconds = cache_ttl_seconds
        self.max_cache_entries = max_cache_entries

        # Result cache
        self._cache: Dict[str, CacheEntry] = {}
        self._cache_hits = 0
        self._cache_misses = 0

        # Metrics
        self._total_compositions = 0
        self._successful_compositions = 0
        self._failed_compositions = 0

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

    async def execute_conditional(
        self,
        branch: ConditionalBranch,
        context: Dict[str, Any]
    ) -> CompositionResult:
        """
        Execute conditional branching based on context evaluation.

        Args:
            branch: ConditionalBranch with condition and requests
            context: Context dictionary for condition evaluation

        Returns:
            CompositionResult with executed branch responses
        """
        start_time = datetime.now(timezone.utc)
        composition_id = str(uuid4())

        logger.info(f"Evaluating conditional branch: {branch.condition}")

        try:
            # Evaluate condition
            condition_met = self._evaluate_condition(branch.condition, context)
            logger.debug(f"Condition '{branch.condition}' evaluated to: {condition_met}")

            # Select appropriate branch
            if condition_met:
                requests = branch.then_requests
                branch_name = "then"
            else:
                requests = branch.else_requests or []
                branch_name = "else"

            if not requests:
                logger.info(f"No requests in {branch_name} branch, returning empty result")
                return CompositionResult(
                    composition_id=composition_id,
                    status="success",
                    responses=[],
                    execution_time_ms=0.0
                )

            # Execute the selected branch as a chain
            responses = await self.execute_chain(requests, propagate_results=True)

            # Determine status
            failed_count = sum(1 for r in responses if r.status != ToolStatus.SUCCESS)
            if failed_count == 0:
                status = "success"
                self._successful_compositions += 1
            elif failed_count < len(responses):
                status = "partial_failure"
            else:
                status = "failed"
                self._failed_compositions += 1

            self._total_compositions += 1

            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            return CompositionResult(
                composition_id=composition_id,
                status=status,
                responses=responses,
                execution_time_ms=execution_time
            )

        except Exception as e:
            logger.error(f"Conditional execution failed: {e}")
            self._failed_compositions += 1
            self._total_compositions += 1

            return CompositionResult(
                composition_id=composition_id,
                status="failed",
                responses=[],
                error=str(e)
            )

    def _evaluate_condition(
        self,
        condition: str,
        context: Dict[str, Any]
    ) -> bool:
        """
        Safely evaluate a condition expression.

        Supports simple expressions like:
        - "status == 'success'"
        - "count > 10"
        - "enabled == true"
        - "error is None"

        Args:
            condition: Condition expression string
            context: Context dictionary with variables

        Returns:
            Boolean result of condition evaluation
        """
        try:
            # Simple expression parser (safe subset)
            # Replace common patterns
            safe_condition = condition

            # Handle 'is None' / 'is not None'
            safe_condition = safe_condition.replace(" is not None", " != None")
            safe_condition = safe_condition.replace(" is None", " == None")

            # Handle 'true'/'false' literals
            safe_condition = safe_condition.replace("true", "True")
            safe_condition = safe_condition.replace("false", "False")

            # Create safe evaluation namespace
            safe_globals = {"__builtins__": {}, "None": None, "True": True, "False": False}
            safe_locals = dict(context)

            # Evaluate the condition
            result = eval(safe_condition, safe_globals, safe_locals)
            return bool(result)

        except Exception as e:
            logger.warning(f"Condition evaluation failed: {condition}, error: {e}")
            return False

    async def execute_cached(
        self,
        requests: List[ToolInvokeRequest],
        cache_key: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
        execution_mode: str = "chain"
    ) -> CompositionResult:
        """
        Execute tool composition with caching.

        Args:
            requests: List of tool requests
            cache_key: Optional custom cache key (auto-generated if not provided)
            ttl_seconds: Cache TTL (uses default if not provided)
            execution_mode: 'chain', 'parallel', or 'dag'

        Returns:
            CompositionResult (potentially from cache)
        """
        if not self.cache_enabled:
            return await self._execute_uncached(requests, execution_mode)

        # Generate cache key
        key = cache_key or self._generate_cache_key(requests, execution_mode)
        ttl = ttl_seconds or self.cache_ttl_seconds

        # Check cache
        cached_result = self._get_from_cache(key)
        if cached_result:
            self._cache_hits += 1
            logger.debug(f"Cache hit for composition: {key[:16]}...")
            cached_result.cached = True
            return cached_result

        self._cache_misses += 1

        # Execute and cache
        result = await self._execute_uncached(requests, execution_mode)

        # Only cache successful results
        if result.status == "success":
            self._add_to_cache(key, result, ttl)

        return result

    async def _execute_uncached(
        self,
        requests: List[ToolInvokeRequest],
        execution_mode: str
    ) -> CompositionResult:
        """
        Execute composition without caching.

        Args:
            requests: Tool requests
            execution_mode: Execution mode

        Returns:
            CompositionResult
        """
        start_time = datetime.now(timezone.utc)
        composition_id = str(uuid4())

        try:
            if execution_mode == "chain":
                responses = await self.execute_chain(requests)
            elif execution_mode == "parallel":
                responses = await self.execute_parallel(requests)
            else:
                raise ValueError(f"Unsupported execution mode: {execution_mode}")

            # Determine status
            failed_count = sum(1 for r in responses if r.status != ToolStatus.SUCCESS)
            if failed_count == 0:
                status = "success"
                self._successful_compositions += 1
            elif failed_count < len(responses):
                status = "partial_failure"
            else:
                status = "failed"
                self._failed_compositions += 1

            self._total_compositions += 1

            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            return CompositionResult(
                composition_id=composition_id,
                status=status,
                responses=responses,
                execution_time_ms=execution_time
            )

        except Exception as e:
            logger.error(f"Composition execution failed: {e}")
            self._failed_compositions += 1
            self._total_compositions += 1

            return CompositionResult(
                composition_id=composition_id,
                status="failed",
                responses=[],
                error=str(e)
            )

    def _generate_cache_key(
        self,
        requests: List[ToolInvokeRequest],
        execution_mode: str
    ) -> str:
        """
        Generate cache key from requests.

        Args:
            requests: Tool requests
            execution_mode: Execution mode

        Returns:
            Cache key string
        """
        key_parts = [execution_mode]

        for req in requests:
            key_parts.append(req.tool_id)
            # Sort parameters for consistent hashing
            params_str = json.dumps(req.parameters, sort_keys=True, default=str)
            key_parts.append(params_str)

        key_string = "|".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()

    def _get_from_cache(self, key: str) -> Optional[CompositionResult]:
        """
        Get result from cache if valid.

        Args:
            key: Cache key

        Returns:
            Cached result or None
        """
        entry = self._cache.get(key)
        if not entry:
            return None

        # Check TTL
        age = (datetime.now(timezone.utc) - entry.created_at).total_seconds()
        if age > entry.ttl_seconds:
            del self._cache[key]
            return None

        entry.hit_count += 1
        return entry.result

    def _add_to_cache(
        self,
        key: str,
        result: CompositionResult,
        ttl_seconds: int
    ) -> None:
        """
        Add result to cache.

        Args:
            key: Cache key
            result: Composition result
            ttl_seconds: TTL in seconds
        """
        # Evict oldest entries if at capacity
        if len(self._cache) >= self.max_cache_entries:
            self._evict_oldest_entries(count=self.max_cache_entries // 10)

        self._cache[key] = CacheEntry(
            result=result,
            created_at=datetime.now(timezone.utc),
            ttl_seconds=ttl_seconds
        )

    def _evict_oldest_entries(self, count: int) -> None:
        """
        Evict oldest cache entries.

        Args:
            count: Number of entries to evict
        """
        if not self._cache:
            return

        # Sort by creation time
        sorted_keys = sorted(
            self._cache.keys(),
            key=lambda k: self._cache[k].created_at
        )

        # Remove oldest
        for key in sorted_keys[:count]:
            del self._cache[key]

        logger.debug(f"Evicted {count} cache entries")

    def clear_cache(self) -> int:
        """
        Clear all cached results.

        Returns:
            Number of entries cleared
        """
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cleared {count} cache entries")
        return count

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Cache statistics dictionary
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0.0

        return {
            "enabled": self.cache_enabled,
            "entries": len(self._cache),
            "max_entries": self.max_cache_entries,
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "hit_rate_percent": round(hit_rate, 2),
            "default_ttl_seconds": self.cache_ttl_seconds
        }

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get composer metrics.

        Returns:
            Metrics dictionary
        """
        success_rate = (
            self._successful_compositions / self._total_compositions * 100
            if self._total_compositions > 0 else 0.0
        )

        return {
            "total_compositions": self._total_compositions,
            "successful_compositions": self._successful_compositions,
            "failed_compositions": self._failed_compositions,
            "success_rate_percent": round(success_rate, 2),
            "cache": self.get_cache_stats()
        }

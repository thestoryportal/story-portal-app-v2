"""
L03 Tool Execution Observability

Provides metrics collection and structured logging for the tool execution layer.
"""

from .metrics import (
    TOOL_INVOCATIONS_TOTAL,
    TOOL_EXECUTION_DURATION,
    ACTIVE_EXECUTIONS,
    CACHE_HITS_TOTAL,
    CACHE_MISSES_TOTAL,
    SEMANTIC_SEARCH_DURATION,
    ASYNC_TASKS_TOTAL,
    ASYNC_TASKS_IN_PROGRESS,
    L02_REQUESTS_TOTAL,
    L02_REQUEST_DURATION,
    record_tool_invocation,
    record_cache_access,
    record_semantic_search,
    record_async_task,
    record_l02_request,
)

__all__ = [
    # Metrics
    "TOOL_INVOCATIONS_TOTAL",
    "TOOL_EXECUTION_DURATION",
    "ACTIVE_EXECUTIONS",
    "CACHE_HITS_TOTAL",
    "CACHE_MISSES_TOTAL",
    "SEMANTIC_SEARCH_DURATION",
    "ASYNC_TASKS_TOTAL",
    "ASYNC_TASKS_IN_PROGRESS",
    "L02_REQUESTS_TOTAL",
    "L02_REQUEST_DURATION",
    # Helper functions
    "record_tool_invocation",
    "record_cache_access",
    "record_semantic_search",
    "record_async_task",
    "record_l02_request",
]

"""
L03 Tool Execution Metrics

Prometheus metrics for monitoring tool execution performance and behavior.
Based on Phase 4 observability requirements.
"""

import time
from contextlib import contextmanager
from typing import Optional

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# ==================== Tool Execution Metrics ====================

TOOL_INVOCATIONS_TOTAL = Counter(
    "l03_tool_invocations_total",
    "Total number of tool invocations",
    ["tool_id", "status", "execution_mode"]
)

TOOL_EXECUTION_DURATION = Histogram(
    "l03_tool_execution_duration_seconds",
    "Tool execution duration in seconds",
    ["tool_id"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
)

ACTIVE_EXECUTIONS = Gauge(
    "l03_active_executions",
    "Number of currently executing tools",
    ["agent_did"]
)

# ==================== Cache Metrics ====================

CACHE_HITS_TOTAL = Counter(
    "l03_cache_hits_total",
    "Total number of cache hits",
    ["tool_id", "cache_type"]
)

CACHE_MISSES_TOTAL = Counter(
    "l03_cache_misses_total",
    "Total number of cache misses",
    ["tool_id", "cache_type"]
)

# ==================== Semantic Search Metrics ====================

SEMANTIC_SEARCH_DURATION = Histogram(
    "l03_semantic_search_duration_seconds",
    "Semantic search latency in seconds",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

SEMANTIC_SEARCH_RESULTS = Histogram(
    "l03_semantic_search_results_count",
    "Number of results returned by semantic search",
    buckets=[0, 1, 5, 10, 20, 50, 100]
)

# ==================== Async Task Metrics ====================

ASYNC_TASKS_TOTAL = Counter(
    "l03_async_tasks_total",
    "Total number of async tasks created",
    ["tool_id", "final_status"]
)

ASYNC_TASKS_IN_PROGRESS = Gauge(
    "l03_async_tasks_in_progress",
    "Number of async tasks currently in progress"
)

ASYNC_TASK_DURATION = Histogram(
    "l03_async_task_duration_seconds",
    "Async task duration from creation to completion",
    ["tool_id"],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0]
)

# ==================== L02 Integration Metrics ====================

L02_REQUESTS_TOTAL = Counter(
    "l03_l02_requests_total",
    "Total requests to L02 Runtime",
    ["operation", "status"]
)

L02_REQUEST_DURATION = Histogram(
    "l03_l02_request_duration_seconds",
    "L02 request duration in seconds",
    ["operation"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# ==================== Error Metrics ====================

ERRORS_TOTAL = Counter(
    "l03_errors_total",
    "Total number of errors",
    ["error_code", "tool_id"]
)

# ==================== Helper Functions ====================


@contextmanager
def record_tool_invocation(
    tool_id: str,
    execution_mode: str = "sync",
    agent_did: Optional[str] = None
):
    """
    Context manager to record tool invocation metrics.

    Args:
        tool_id: Tool identifier
        execution_mode: "sync" or "async"
        agent_did: Agent DID for tracking active executions

    Usage:
        with record_tool_invocation("my-tool", "sync", "did:agent:123") as record:
            result = await execute_tool()
            record.set_status("success")
    """
    start_time = time.time()
    status = "error"  # Default to error if not set

    class RecordContext:
        def set_status(self, new_status: str):
            nonlocal status
            status = new_status

    record = RecordContext()

    # Track active executions
    if agent_did:
        ACTIVE_EXECUTIONS.labels(agent_did=agent_did).inc()

    try:
        yield record
    finally:
        duration = time.time() - start_time

        # Record metrics
        TOOL_INVOCATIONS_TOTAL.labels(
            tool_id=tool_id,
            status=status,
            execution_mode=execution_mode
        ).inc()

        TOOL_EXECUTION_DURATION.labels(tool_id=tool_id).observe(duration)

        if agent_did:
            ACTIVE_EXECUTIONS.labels(agent_did=agent_did).dec()


def record_cache_access(
    tool_id: str,
    hit: bool,
    cache_type: str = "result"
):
    """
    Record cache access (hit or miss).

    Args:
        tool_id: Tool identifier
        hit: Whether cache hit occurred
        cache_type: Type of cache ("result", "idempotency")
    """
    if hit:
        CACHE_HITS_TOTAL.labels(tool_id=tool_id, cache_type=cache_type).inc()
    else:
        CACHE_MISSES_TOTAL.labels(tool_id=tool_id, cache_type=cache_type).inc()


@contextmanager
def record_semantic_search():
    """
    Context manager to record semantic search metrics.

    Usage:
        with record_semantic_search() as record:
            results = await search_tools(query)
            record.set_results_count(len(results))
    """
    start_time = time.time()
    results_count = 0

    class RecordContext:
        def set_results_count(self, count: int):
            nonlocal results_count
            results_count = count

    record = RecordContext()

    try:
        yield record
    finally:
        duration = time.time() - start_time
        SEMANTIC_SEARCH_DURATION.observe(duration)
        SEMANTIC_SEARCH_RESULTS.observe(results_count)


def record_async_task(
    tool_id: str,
    action: str,
    final_status: Optional[str] = None
):
    """
    Record async task metrics.

    Args:
        tool_id: Tool identifier
        action: "created", "started", "completed"
        final_status: Final status for completed tasks ("success", "error", "cancelled", "timeout")
    """
    if action == "created":
        ASYNC_TASKS_IN_PROGRESS.inc()
    elif action == "completed":
        ASYNC_TASKS_IN_PROGRESS.dec()
        if final_status:
            ASYNC_TASKS_TOTAL.labels(tool_id=tool_id, final_status=final_status).inc()


@contextmanager
def record_l02_request(operation: str):
    """
    Context manager to record L02 request metrics.

    Args:
        operation: Operation type ("get_document", "search_documents", "create_checkpoint", etc.)

    Usage:
        with record_l02_request("get_document") as record:
            result = await l02_client.get_document(doc_id)
            record.set_status("success" if result else "not_found")
    """
    start_time = time.time()
    status = "error"

    class RecordContext:
        def set_status(self, new_status: str):
            nonlocal status
            status = new_status

    record = RecordContext()

    try:
        yield record
    finally:
        duration = time.time() - start_time

        L02_REQUESTS_TOTAL.labels(operation=operation, status=status).inc()
        L02_REQUEST_DURATION.labels(operation=operation).observe(duration)


def record_error(error_code: str, tool_id: str = "unknown"):
    """
    Record an error occurrence.

    Args:
        error_code: Error code (e.g., "E3001")
        tool_id: Tool identifier
    """
    ERRORS_TOTAL.labels(error_code=error_code, tool_id=tool_id).inc()


def get_metrics() -> bytes:
    """
    Generate Prometheus metrics output.

    Returns:
        Metrics in Prometheus text format
    """
    return generate_latest()


def get_metrics_content_type() -> str:
    """
    Get content type for Prometheus metrics.

    Returns:
        Content type string
    """
    return CONTENT_TYPE_LATEST

"""
L01Client - Client library for interacting with L01 Data Layer.

This client provides a typed interface for all other layers to interact with L01.
"""

import httpx
from typing import Dict, Any, List, Optional
from uuid import UUID
import logging

logger = logging.getLogger(__name__)


class L01Client:
    """Client for L01 Data Layer API."""

    def __init__(self, base_url: str = "http://localhost:8002", timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
        return self._client

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    # Agent methods
    async def create_agent(self, name: str, agent_type: str = "general",
                          configuration: Optional[Dict[str, Any]] = None,
                          metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new agent."""
        client = await self._get_client()
        response = await client.post("/agents/", json={
            "name": name,
            "agent_type": agent_type,
            "configuration": configuration or {},
            "metadata": metadata or {},
        })
        response.raise_for_status()
        return response.json()

    async def get_agent(self, agent_id: UUID) -> Dict[str, Any]:
        """Get agent by ID."""
        client = await self._get_client()
        response = await client.get(f"/agents/{agent_id}")
        response.raise_for_status()
        return response.json()

    async def list_agents(self, status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """List agents."""
        client = await self._get_client()
        params = {"limit": limit}
        if status:
            params["status"] = status
        response = await client.get("/agents/", params=params)
        response.raise_for_status()
        return response.json()

    async def update_agent(self, agent_id: UUID, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update agent."""
        client = await self._get_client()
        response = await client.patch(f"/agents/{agent_id}", json=updates)
        response.raise_for_status()
        return response.json()

    async def delete_agent(self, agent_id: UUID) -> bool:
        """Delete agent."""
        client = await self._get_client()
        response = await client.delete(f"/agents/{agent_id}")
        return response.status_code == 204

    # Event methods
    async def publish_event(self, event_type: str, aggregate_type: str,
                           aggregate_id: UUID, payload: Dict[str, Any],
                           metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Publish an event."""
        client = await self._get_client()
        response = await client.post("/events/", json={
            "event_type": event_type,
            "aggregate_type": aggregate_type,
            "aggregate_id": str(aggregate_id),
            "payload": payload,
            "metadata": metadata or {},
        })
        response.raise_for_status()
        return response.json()

    async def query_events(self, aggregate_id: Optional[UUID] = None,
                          event_type: Optional[str] = None,
                          limit: int = 100) -> List[Dict[str, Any]]:
        """Query events."""
        client = await self._get_client()
        params = {"limit": limit}
        if aggregate_id:
            params["aggregate_id"] = str(aggregate_id)
        if event_type:
            params["event_type"] = event_type
        response = await client.get("/events/", params=params)
        response.raise_for_status()
        return response.json()

    # Tool methods
    async def register_tool(self, name: str, schema_def: Dict[str, Any],
                           description: Optional[str] = None,
                           tool_type: str = "function") -> Dict[str, Any]:
        """Register a tool."""
        client = await self._get_client()
        response = await client.post("/tools/", json={
            "name": name,
            "description": description,
            "tool_type": tool_type,
            "schema_def": schema_def,
        })
        response.raise_for_status()
        return response.json()

    async def get_tool(self, tool_id: UUID) -> Dict[str, Any]:
        """Get tool by ID."""
        client = await self._get_client()
        response = await client.get(f"/tools/{tool_id}")
        response.raise_for_status()
        return response.json()

    async def list_tools(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """List tools."""
        client = await self._get_client()
        response = await client.get("/tools/", params={"enabled_only": enabled_only})
        response.raise_for_status()
        return response.json()

    async def record_tool_execution(
        self,
        invocation_id: UUID,
        tool_name: str,
        input_params: Dict[str, Any],
        tool_id: Optional[UUID] = None,
        tool_version: Optional[str] = None,
        agent_id: Optional[UUID] = None,
        agent_did: Optional[str] = None,
        tenant_id: Optional[str] = None,
        session_id: Optional[str] = None,
        parent_sandbox_id: Optional[str] = None,
        status: str = "pending",
        async_mode: bool = False,
        priority: int = 5,
        idempotency_key: Optional[str] = None,
        require_approval: bool = False,
        cpu_millicore_limit: Optional[int] = None,
        memory_mb_limit: Optional[int] = None,
        timeout_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """Record a tool execution with rich metadata."""
        client = await self._get_client()
        payload = {
            "invocation_id": str(invocation_id),
            "tool_name": tool_name,
            "input_params": input_params,
            "status": status,
            "async_mode": async_mode,
            "priority": priority,
            "require_approval": require_approval,
        }
        if tool_id:
            payload["tool_id"] = str(tool_id)
        if tool_version:
            payload["tool_version"] = tool_version
        if agent_id:
            payload["agent_id"] = str(agent_id)
        if agent_did:
            payload["agent_did"] = agent_did
        if tenant_id:
            payload["tenant_id"] = tenant_id
        if session_id:
            payload["session_id"] = session_id
        if parent_sandbox_id:
            payload["parent_sandbox_id"] = parent_sandbox_id
        if idempotency_key:
            payload["idempotency_key"] = idempotency_key
        if cpu_millicore_limit:
            payload["cpu_millicore_limit"] = cpu_millicore_limit
        if memory_mb_limit:
            payload["memory_mb_limit"] = memory_mb_limit
        if timeout_seconds:
            payload["timeout_seconds"] = timeout_seconds

        response = await client.post("/tools/tool-executions", json=payload)
        response.raise_for_status()
        return response.json()

    async def get_tool_execution_by_invocation(self, invocation_id: UUID) -> Dict[str, Any]:
        """Get tool execution by invocation ID."""
        client = await self._get_client()
        response = await client.get(f"/tools/executions/by-invocation/{invocation_id}")
        response.raise_for_status()
        return response.json()

    async def update_tool_execution(
        self,
        invocation_id: UUID,
        status: Optional[str] = None,
        output_result: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        retryable: Optional[bool] = None,
        duration_ms: Optional[int] = None,
        cpu_used_millicore_seconds: Optional[int] = None,
        memory_peak_mb: Optional[int] = None,
        network_bytes_sent: Optional[int] = None,
        network_bytes_received: Optional[int] = None,
        documents_accessed: Optional[List[str]] = None,
        checkpoints_created: Optional[List[str]] = None,
        checkpoint_ref: Optional[str] = None,
        started_at: Optional[str] = None,
        completed_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update tool execution with results and metadata."""
        client = await self._get_client()
        updates = {}
        if status is not None:
            updates["status"] = status
        if output_result is not None:
            updates["output_result"] = output_result
        if error_code is not None:
            updates["error_code"] = error_code
        if error_message is not None:
            updates["error_message"] = error_message
        if error_details is not None:
            updates["error_details"] = error_details
        if retryable is not None:
            updates["retryable"] = retryable
        if duration_ms is not None:
            updates["duration_ms"] = duration_ms
        if cpu_used_millicore_seconds is not None:
            updates["cpu_used_millicore_seconds"] = cpu_used_millicore_seconds
        if memory_peak_mb is not None:
            updates["memory_peak_mb"] = memory_peak_mb
        if network_bytes_sent is not None:
            updates["network_bytes_sent"] = network_bytes_sent
        if network_bytes_received is not None:
            updates["network_bytes_received"] = network_bytes_received
        if documents_accessed is not None:
            updates["documents_accessed"] = documents_accessed
        if checkpoints_created is not None:
            updates["checkpoints_created"] = checkpoints_created
        if checkpoint_ref is not None:
            updates["checkpoint_ref"] = checkpoint_ref
        if started_at is not None:
            updates["started_at"] = started_at
        if completed_at is not None:
            updates["completed_at"] = completed_at

        response = await client.patch(f"/tools/executions/{invocation_id}", json=updates)
        response.raise_for_status()
        return response.json()

    async def list_tool_executions(
        self,
        agent_id: Optional[UUID] = None,
        tool_name: Optional[str] = None,
        session_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List tool executions with filters."""
        client = await self._get_client()
        params = {"limit": limit, "offset": offset}
        if agent_id:
            params["agent_id"] = str(agent_id)
        if tool_name:
            params["tool_name"] = tool_name
        if session_id:
            params["session_id"] = session_id
        if tenant_id:
            params["tenant_id"] = tenant_id
        if status:
            params["status"] = status

        response = await client.get("/tools/executions", params=params)
        response.raise_for_status()
        return response.json()

    # Goal methods
    async def create_goal(self, agent_id: UUID, description: str,
                         success_criteria: Optional[List[Dict[str, Any]]] = None,
                         priority: int = 5) -> Dict[str, Any]:
        """Create a goal."""
        client = await self._get_client()
        response = await client.post("/goals/", json={
            "agent_id": str(agent_id),
            "description": description,
            "success_criteria": success_criteria or [],
            "priority": priority,
        })
        response.raise_for_status()
        return response.json()

    async def get_goal(self, goal_id: UUID) -> Dict[str, Any]:
        """Get goal by ID."""
        client = await self._get_client()
        response = await client.get(f"/goals/{goal_id}")
        response.raise_for_status()
        return response.json()

    async def update_goal(self, goal_id: UUID, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update goal."""
        client = await self._get_client()
        response = await client.patch(f"/goals/{goal_id}", json=updates)
        response.raise_for_status()
        return response.json()

    # Plan methods
    async def create_plan(self, goal_id: UUID, agent_id: UUID,
                         steps: List[Dict[str, Any]],
                         plan_type: str = "sequential") -> Dict[str, Any]:
        """Create a plan."""
        client = await self._get_client()
        response = await client.post("/plans/", json={
            "goal_id": str(goal_id),
            "agent_id": str(agent_id),
            "plan_type": plan_type,
            "steps": steps,
        })
        response.raise_for_status()
        return response.json()

    async def get_plan(self, plan_id: UUID) -> Dict[str, Any]:
        """Get plan by ID."""
        client = await self._get_client()
        response = await client.get(f"/plans/{plan_id}")
        response.raise_for_status()
        return response.json()

    async def update_plan(self, plan_id: UUID, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update plan."""
        client = await self._get_client()
        response = await client.patch(f"/plans/{plan_id}", json=updates)
        response.raise_for_status()
        return response.json()

    # Task methods
    async def create_task(self, plan_id: UUID, agent_id: UUID,
                         description: str, task_type: Optional[str] = None,
                         input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a task."""
        client = await self._get_client()
        response = await client.post("/plans/tasks", json={
            "plan_id": str(plan_id),
            "agent_id": str(agent_id),
            "description": description,
            "task_type": task_type,
            "input_data": input_data or {},
        })
        response.raise_for_status()
        return response.json()

    async def update_task(self, task_id: UUID, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update task."""
        client = await self._get_client()
        response = await client.patch(f"/plans/tasks/{task_id}", json=updates)
        response.raise_for_status()
        return response.json()

    # Evaluation methods
    async def record_evaluation(self, agent_id: UUID, evaluation_type: str,
                               score: Optional[float] = None,
                               metrics: Optional[Dict[str, Any]] = None,
                               task_id: Optional[UUID] = None,
                               feedback: Optional[str] = None) -> Dict[str, Any]:
        """Record an evaluation."""
        client = await self._get_client()
        payload = {
            "agent_id": str(agent_id),
            "evaluation_type": evaluation_type,
            "score": score,
            "metrics": metrics or {},
            "feedback": feedback,
        }
        if task_id:
            payload["task_id"] = str(task_id)
        response = await client.post("/evaluations/", json=payload)
        response.raise_for_status()
        return response.json()

    async def get_agent_stats(self, agent_id: UUID) -> Dict[str, Any]:
        """Get agent evaluation statistics."""
        client = await self._get_client()
        response = await client.get(f"/evaluations/agent/{agent_id}/stats")
        response.raise_for_status()
        return response.json()

    # Feedback methods
    async def record_feedback(self, agent_id: UUID, feedback_type: str,
                             content: str, rating: Optional[int] = None,
                             task_id: Optional[UUID] = None,
                             metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Record feedback."""
        client = await self._get_client()
        payload = {
            "agent_id": str(agent_id),
            "feedback_type": feedback_type,
            "content": content,
            "rating": rating,
            "metadata": metadata or {},
        }
        if task_id:
            payload["task_id"] = str(task_id)
        response = await client.post("/feedback/", json=payload)
        response.raise_for_status()
        return response.json()

    async def get_unprocessed_feedback(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get unprocessed feedback."""
        client = await self._get_client()
        response = await client.get("/feedback/unprocessed", params={"limit": limit})
        response.raise_for_status()
        return response.json()

    # Model usage methods
    async def record_model_usage(
        self,
        request_id: str,
        model_provider: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        agent_id: Optional[UUID] = None,
        agent_did: Optional[str] = None,
        tenant_id: Optional[str] = None,
        session_id: Optional[str] = None,
        model_id: Optional[str] = None,
        cached_tokens: int = 0,
        total_tokens: Optional[int] = None,
        latency_ms: Optional[int] = None,
        cached: bool = False,
        cost_estimate: Optional[float] = None,
        cost_input_cents: Optional[float] = None,
        cost_output_cents: Optional[float] = None,
        cost_cached_cents: Optional[float] = None,
        finish_reason: Optional[str] = None,
        error_message: Optional[str] = None,
        response_status: str = "success",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Record model usage with rich metadata."""
        client = await self._get_client()

        payload = {
            "request_id": request_id,
            "model_provider": model_provider,
            "model_name": model_name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cached_tokens": cached_tokens,
            "total_tokens": total_tokens if total_tokens is not None else (input_tokens + output_tokens),
            "cached": cached,
            "response_status": response_status,
            "metadata": metadata or {},
        }

        if agent_id:
            payload["agent_id"] = str(agent_id)
        if agent_did:
            payload["agent_did"] = agent_did
        if tenant_id:
            payload["tenant_id"] = tenant_id
        if session_id:
            payload["session_id"] = session_id
        if model_id:
            payload["model_id"] = model_id
        if latency_ms is not None:
            payload["latency_ms"] = latency_ms
        if cost_estimate is not None:
            payload["cost_estimate"] = cost_estimate
        if cost_input_cents is not None:
            payload["cost_input_cents"] = cost_input_cents
        if cost_output_cents is not None:
            payload["cost_output_cents"] = cost_output_cents
        if cost_cached_cents is not None:
            payload["cost_cached_cents"] = cost_cached_cents
        if finish_reason:
            payload["finish_reason"] = finish_reason
        if error_message:
            payload["error_message"] = error_message

        response = await client.post("/models/usage", json=payload)
        response.raise_for_status()
        return response.json()

    # L05 Planning methods
    async def record_goal(
        self,
        goal_id: str,
        agent_did: str,
        goal_text: str,
        agent_id: Optional[UUID] = None,
        goal_type: str = "compound",
        status: str = "pending",
        constraints: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        parent_goal_id: Optional[str] = None,
        decomposition_strategy: Optional[str] = None
    ) -> Dict[str, Any]:
        """Record a goal with constraints and metadata."""
        client = await self._get_client()

        payload = {
            "goal_id": goal_id,
            "agent_did": agent_did,
            "goal_text": goal_text,
            "goal_type": goal_type,
            "status": status,
            "metadata": metadata or {}
        }

        if agent_id:
            payload["agent_id"] = str(agent_id)
        if constraints:
            payload["constraints"] = constraints
        if parent_goal_id:
            payload["parent_goal_id"] = parent_goal_id
        if decomposition_strategy:
            payload["decomposition_strategy"] = decomposition_strategy

        response = await client.post("/goals/", json=payload)
        response.raise_for_status()
        return response.json()

    async def update_goal_status(
        self,
        goal_id: str,
        status: str,
        decomposition_strategy: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update goal status."""
        client = await self._get_client()

        payload = {"status": status}
        if decomposition_strategy:
            payload["decomposition_strategy"] = decomposition_strategy

        response = await client.patch(f"/goals/{goal_id}", json=payload)
        response.raise_for_status()
        return response.json()

    async def record_plan(
        self,
        plan_id: str,
        goal_id: str,
        agent_id: Optional[UUID] = None,
        tasks: Optional[list] = None,
        dependency_graph: Optional[Dict[str, list]] = None,
        status: str = "draft",
        resource_budget: Optional[Dict[str, Any]] = None,
        decomposition_strategy: str = "hybrid",
        decomposition_latency_ms: Optional[float] = None,
        cache_hit: bool = False,
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None,
        total_tokens_used: int = 0,
        validation_time_ms: Optional[float] = None,
        tags: Optional[list] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Record an execution plan with metadata."""
        client = await self._get_client()

        payload = {
            "plan_id": plan_id,
            "goal_id": goal_id,
            "tasks": tasks or [],
            "dependency_graph": dependency_graph or {},
            "status": status,
            "decomposition_strategy": decomposition_strategy,
            "cache_hit": cache_hit,
            "total_tokens_used": total_tokens_used,
            "metadata": metadata or {}
        }

        if agent_id:
            payload["agent_id"] = str(agent_id)
        if resource_budget:
            payload["resource_budget"] = resource_budget
        if decomposition_latency_ms is not None:
            payload["decomposition_latency_ms"] = decomposition_latency_ms
        if llm_provider:
            payload["llm_provider"] = llm_provider
        if llm_model:
            payload["llm_model"] = llm_model
        if validation_time_ms is not None:
            payload["validation_time_ms"] = validation_time_ms
        if tags:
            payload["tags"] = tags

        response = await client.post("/plans/", json=payload)
        response.raise_for_status()
        return response.json()

    async def update_plan_status(
        self,
        plan_id: str,
        status: str,
        validated_at: Optional[str] = None,
        execution_started_at: Optional[str] = None,
        execution_completed_at: Optional[str] = None,
        execution_time_ms: Optional[float] = None,
        parallelism_achieved: Optional[int] = None,
        error: Optional[str] = None,
        completed_task_count: Optional[int] = None,
        failed_task_count: Optional[int] = None
    ) -> Dict[str, Any]:
        """Update plan status and execution details."""
        client = await self._get_client()

        payload = {"status": status}
        if validated_at:
            payload["validated_at"] = validated_at
        if execution_started_at:
            payload["execution_started_at"] = execution_started_at
        if execution_completed_at:
            payload["execution_completed_at"] = execution_completed_at
        if execution_time_ms is not None:
            payload["execution_time_ms"] = execution_time_ms
        if parallelism_achieved is not None:
            payload["parallelism_achieved"] = parallelism_achieved
        if error:
            payload["error"] = error
        if completed_task_count is not None:
            payload["completed_task_count"] = completed_task_count
        if failed_task_count is not None:
            payload["failed_task_count"] = failed_task_count

        response = await client.patch(f"/plans/{plan_id}", json=payload)
        response.raise_for_status()
        return response.json()

    async def get_plan(self, plan_id: str) -> Dict[str, Any]:
        """Get plan by ID."""
        client = await self._get_client()
        response = await client.get(f"/plans/{plan_id}")
        response.raise_for_status()
        return response.json()

    # Config methods
    async def get_config(self, namespace: str, key: str) -> Dict[str, Any]:
        """Get configuration."""
        client = await self._get_client()
        response = await client.get(f"/config/{namespace}/{key}")
        response.raise_for_status()
        return response.json()

    async def set_config(self, namespace: str, key: str, value: Dict[str, Any]) -> Dict[str, Any]:
        """Set configuration."""
        client = await self._get_client()
        response = await client.put(f"/config/{namespace}/{key}", json=value)
        response.raise_for_status()
        return response.json()

    # Session methods
    async def create_session(
        self,
        agent_id: UUID,
        session_type: str = "runtime",
        context: Optional[Dict[str, Any]] = None,
        runtime_backend: Optional[str] = None,
        runtime_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new session."""
        client = await self._get_client()
        response = await client.post("/sessions/", json={
            "agent_id": str(agent_id),
            "session_type": session_type,
            "context": context or {},
            "runtime_backend": runtime_backend,
            "runtime_metadata": runtime_metadata or {},
        })
        response.raise_for_status()
        return response.json()

    async def get_session(self, session_id: UUID) -> Dict[str, Any]:
        """Get session by ID."""
        client = await self._get_client()
        response = await client.get(f"/sessions/{session_id}")
        response.raise_for_status()
        return response.json()

    async def update_session(
        self,
        session_id: UUID,
        status: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        checkpoint: Optional[Dict[str, Any]] = None,
        runtime_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update session."""
        client = await self._get_client()
        update_data = {}
        if status is not None:
            update_data["status"] = status
        if context is not None:
            update_data["context"] = context
        if checkpoint is not None:
            update_data["checkpoint"] = checkpoint
        if runtime_metadata is not None:
            update_data["runtime_metadata"] = runtime_metadata

        response = await client.patch(f"/sessions/{session_id}", json=update_data)
        response.raise_for_status()
        return response.json()

    async def list_sessions(
        self,
        agent_id: Optional[UUID] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List sessions."""
        client = await self._get_client()
        params = {"limit": limit}
        if agent_id:
            params["agent_id"] = str(agent_id)
        response = await client.get("/sessions/", params=params)
        response.raise_for_status()
        return response.json()

    # Training Example methods (L07 Learning)
    async def create_training_example(
        self,
        input_text: str,
        execution_id: Optional[str] = None,
        task_id: Optional[str] = None,
        agent_id: Optional[UUID] = None,
        source_type: str = "execution_trace",
        output_text: str = "",
        expected_actions: Optional[List[Dict[str, Any]]] = None,
        final_answer: str = "",
        quality_score: float = 0.0,
        confidence: float = 0.0,
        labels: Optional[List[str]] = None,
        domain: str = "general",
        task_type: str = "single_step",
        difficulty: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new training example."""
        client = await self._get_client()
        response = await client.post("/training-examples/", json={
            "execution_id": execution_id,
            "task_id": task_id,
            "agent_id": str(agent_id) if agent_id else None,
            "source_type": source_type,
            "input_text": input_text,
            "output_text": output_text,
            "expected_actions": expected_actions or [],
            "final_answer": final_answer,
            "quality_score": quality_score,
            "confidence": confidence,
            "labels": labels or [],
            "domain": domain,
            "task_type": task_type,
            "difficulty": difficulty,
            "metadata": metadata or {},
        })
        response.raise_for_status()
        return response.json()

    async def get_training_example(self, example_id: UUID) -> Dict[str, Any]:
        """Get training example by ID."""
        client = await self._get_client()
        response = await client.get(f"/training-examples/{example_id}")
        response.raise_for_status()
        return response.json()

    async def list_training_examples(
        self,
        agent_id: Optional[UUID] = None,
        domain: Optional[str] = None,
        min_quality: Optional[float] = None,
        source_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List training examples with optional filters."""
        client = await self._get_client()
        params = {"limit": limit, "offset": offset}
        if agent_id:
            params["agent_id"] = str(agent_id)
        if domain:
            params["domain"] = domain
        if min_quality is not None:
            params["min_quality"] = min_quality
        if source_type:
            params["source_type"] = source_type
        response = await client.get("/training-examples/", params=params)
        response.raise_for_status()
        return response.json()

    async def update_training_example(
        self,
        example_id: UUID,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update training example."""
        client = await self._get_client()
        response = await client.patch(f"/training-examples/{example_id}", json=updates)
        response.raise_for_status()
        return response.json()

    async def delete_training_example(self, example_id: UUID) -> bool:
        """Delete training example."""
        client = await self._get_client()
        response = await client.delete(f"/training-examples/{example_id}")
        return response.status_code == 204

    async def get_training_example_statistics(self) -> Dict[str, Any]:
        """Get training example statistics."""
        client = await self._get_client()
        response = await client.get("/training-examples/statistics")
        response.raise_for_status()
        return response.json()

    # Dataset methods (L07 Learning)
    async def create_dataset(
        self,
        name: str,
        version: str = "1.0.0",
        description: str = "",
        tags: Optional[List[str]] = None,
        split_ratios: Optional[Dict[str, float]] = None,
        statistics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new dataset."""
        client = await self._get_client()
        response = await client.post("/datasets/", json={
            "name": name,
            "version": version,
            "description": description,
            "tags": tags or [],
            "split_ratios": split_ratios or {"train": 0.8, "validation": 0.1, "test": 0.1},
            "statistics": statistics or {},
        })
        response.raise_for_status()
        return response.json()

    async def get_dataset(self, dataset_id: UUID) -> Dict[str, Any]:
        """Get dataset by ID."""
        client = await self._get_client()
        response = await client.get(f"/datasets/{dataset_id}")
        response.raise_for_status()
        return response.json()

    async def list_datasets(
        self,
        name_filter: Optional[str] = None,
        tag_filter: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List datasets with optional filters."""
        client = await self._get_client()
        params = {"limit": limit, "offset": offset}
        if name_filter:
            params["name_filter"] = name_filter
        if tag_filter:
            params["tag_filter"] = tag_filter
        response = await client.get("/datasets/", params=params)
        response.raise_for_status()
        return response.json()

    async def update_dataset(
        self,
        dataset_id: UUID,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update dataset metadata."""
        client = await self._get_client()
        response = await client.patch(f"/datasets/{dataset_id}", json=updates)
        response.raise_for_status()
        return response.json()

    async def delete_dataset(self, dataset_id: UUID) -> bool:
        """Delete dataset."""
        client = await self._get_client()
        response = await client.delete(f"/datasets/{dataset_id}")
        return response.status_code == 204

    async def add_example_to_dataset(
        self,
        dataset_id: UUID,
        example_id: UUID,
        split: str = "train"
    ) -> Dict[str, Any]:
        """Add training example to dataset with split assignment."""
        client = await self._get_client()
        response = await client.post(
            f"/datasets/{dataset_id}/examples/{example_id}",
            params={"split": split}
        )
        response.raise_for_status()
        return response.json()

    async def remove_example_from_dataset(
        self,
        dataset_id: UUID,
        example_id: UUID
    ) -> bool:
        """Remove training example from dataset."""
        client = await self._get_client()
        response = await client.delete(f"/datasets/{dataset_id}/examples/{example_id}")
        return response.status_code == 204

    async def get_dataset_examples(
        self,
        dataset_id: UUID,
        split: Optional[str] = None
    ) -> List[UUID]:
        """Get example IDs for a dataset, optionally filtered by split."""
        client = await self._get_client()
        params = {}
        if split:
            params["split"] = split
        response = await client.get(f"/datasets/{dataset_id}/examples", params=params)
        response.raise_for_status()
        return [UUID(id_str) for id_str in response.json()]

    async def get_dataset_split_counts(self, dataset_id: UUID) -> Dict[str, int]:
        """Get count of examples in each split."""
        client = await self._get_client()
        response = await client.get(f"/datasets/{dataset_id}/split-counts")
        response.raise_for_status()
        return response.json()

    async def get_dataset_statistics(self) -> Dict[str, Any]:
        """Get dataset service statistics."""
        client = await self._get_client()
        response = await client.get("/datasets/statistics")
        response.raise_for_status()
        return response.json()

    # L06 Evaluation methods

    async def record_quality_score(
        self,
        score_id: str,
        agent_did: str,
        tenant_id: str,
        timestamp: str,
        overall_score: float,
        assessment: str,
        dimensions: Dict[str, Any],
        agent_id: Optional[UUID] = None,
        data_completeness: float = 1.0,
        cached: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Record a quality score with multi-dimensional evaluation."""
        client = await self._get_client()

        payload = {
            "score_id": score_id,
            "agent_did": agent_did,
            "tenant_id": tenant_id,
            "timestamp": timestamp,
            "overall_score": overall_score,
            "assessment": assessment,
            "dimensions": dimensions,
            "data_completeness": data_completeness,
            "cached": cached,
            "metadata": metadata or {}
        }

        if agent_id:
            payload["agent_id"] = str(agent_id)

        response = await client.post("/quality-scores/", json=payload)
        response.raise_for_status()
        return response.json()

    async def get_quality_score(self, score_id: str) -> Dict[str, Any]:
        """Get quality score by ID."""
        client = await self._get_client()
        response = await client.get(f"/quality-scores/{score_id}")
        response.raise_for_status()
        return response.json()

    async def record_metric(
        self,
        metric_name: str,
        value: float,
        timestamp: str,
        metric_type: str = "gauge",
        labels: Optional[Dict[str, str]] = None,
        agent_id: Optional[UUID] = None,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Record a time-series metric point."""
        client = await self._get_client()

        payload = {
            "metric_name": metric_name,
            "value": value,
            "timestamp": timestamp,
            "metric_type": metric_type,
            "labels": labels or {}
        }

        if agent_id:
            payload["agent_id"] = str(agent_id)
        if tenant_id:
            payload["tenant_id"] = tenant_id

        response = await client.post("/metrics/", json=payload)
        response.raise_for_status()
        return response.json()

    async def query_metrics(
        self,
        metric_name: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        agent_id: Optional[UUID] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Query metrics with filters."""
        client = await self._get_client()

        params = {
            "metric_name": metric_name,
            "limit": limit
        }

        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        if agent_id:
            params["agent_id"] = str(agent_id)
        if labels:
            params["labels"] = labels

        response = await client.get("/metrics/", params=params)
        response.raise_for_status()
        return response.json()

    async def record_anomaly(
        self,
        anomaly_id: str,
        metric_name: str,
        severity: str,
        baseline_value: float,
        current_value: float,
        z_score: float,
        detected_at: str,
        agent_id: Optional[UUID] = None,
        agent_did: Optional[str] = None,
        tenant_id: Optional[str] = None,
        deviation_percent: Optional[float] = None,
        confidence: float = 0.95,
        status: str = "alerting",
        alert_sent: bool = False
    ) -> Dict[str, Any]:
        """Record a detected anomaly."""
        client = await self._get_client()

        payload = {
            "anomaly_id": anomaly_id,
            "metric_name": metric_name,
            "severity": severity,
            "baseline_value": baseline_value,
            "current_value": current_value,
            "z_score": z_score,
            "detected_at": detected_at,
            "confidence": confidence,
            "status": status,
            "alert_sent": alert_sent
        }

        if agent_id:
            payload["agent_id"] = str(agent_id)
        if agent_did:
            payload["agent_did"] = agent_did
        if tenant_id:
            payload["tenant_id"] = tenant_id
        if deviation_percent is not None:
            payload["deviation_percent"] = deviation_percent

        response = await client.post("/anomalies/", json=payload)
        response.raise_for_status()
        return response.json()

    async def get_anomaly(self, anomaly_id: str) -> Dict[str, Any]:
        """Get anomaly by ID."""
        client = await self._get_client()
        response = await client.get(f"/anomalies/{anomaly_id}")
        response.raise_for_status()
        return response.json()

    async def update_anomaly_status(
        self,
        anomaly_id: str,
        status: str,
        resolved_at: Optional[str] = None,
        alert_sent: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Update anomaly status and resolution."""
        client = await self._get_client()

        payload = {
            "status": status
        }

        if resolved_at:
            payload["resolved_at"] = resolved_at
        if alert_sent is not None:
            payload["alert_sent"] = alert_sent

        response = await client.patch(f"/anomalies/{anomaly_id}", json=payload)
        response.raise_for_status()
        return response.json()

    async def record_compliance_result(
        self,
        result_id: str,
        execution_id: str,
        agent_did: str,
        tenant_id: str,
        timestamp: str,
        compliant: bool,
        violations: List[Dict[str, Any]],
        constraints_checked: List[Dict[str, Any]],
        agent_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Record a compliance validation result."""
        client = await self._get_client()

        payload = {
            "result_id": result_id,
            "execution_id": execution_id,
            "agent_did": agent_did,
            "tenant_id": tenant_id,
            "timestamp": timestamp,
            "compliant": compliant,
            "violations": violations,
            "constraints_checked": constraints_checked
        }

        if agent_id:
            payload["agent_id"] = str(agent_id)

        response = await client.post("/compliance-results/", json=payload)
        response.raise_for_status()
        return response.json()

    async def get_compliance_result(self, result_id: str) -> Dict[str, Any]:
        """Get compliance result by ID."""
        client = await self._get_client()
        response = await client.get(f"/compliance-results/{result_id}")
        response.raise_for_status()
        return response.json()

    async def record_alert(
        self,
        alert_id: str,
        timestamp: str,
        severity: str,
        alert_type: str,
        metric: str,
        message: str,
        channels: List[str],
        agent_id: Optional[UUID] = None,
        agent_did: Optional[str] = None,
        tenant_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Record an alert."""
        client = await self._get_client()

        payload = {
            "alert_id": alert_id,
            "timestamp": timestamp,
            "severity": severity,
            "type": alert_type,
            "metric": metric,
            "message": message,
            "channels": channels,
            "metadata": metadata or {}
        }

        if agent_id:
            payload["agent_id"] = str(agent_id)
        if agent_did:
            payload["agent_did"] = agent_did
        if tenant_id:
            payload["tenant_id"] = tenant_id

        response = await client.post("/alerts/", json=payload)
        response.raise_for_status()
        return response.json()

    async def update_alert_delivery(
        self,
        alert_id: str,
        delivery_attempts: int,
        delivered: bool,
        last_attempt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update alert delivery tracking."""
        client = await self._get_client()

        payload = {
            "delivery_attempts": delivery_attempts,
            "delivered": delivered
        }

        if last_attempt:
            payload["last_attempt"] = last_attempt

        response = await client.patch(f"/alerts/{alert_id}", json=payload)
        response.raise_for_status()
        return response.json()

    async def get_alert(self, alert_id: str) -> Dict[str, Any]:
        """Get alert by ID."""
        client = await self._get_client()
        response = await client.get(f"/alerts/{alert_id}")
        response.raise_for_status()
        return response.json()

    # ===================================================================
    # L09 API Gateway Methods
    # ===================================================================

    async def record_api_request(
        self,
        request_id: str,
        trace_id: str,
        span_id: str,
        timestamp: str,
        method: str,
        path: str,
        status_code: int,
        latency_ms: float,
        consumer_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        authenticated: bool = False,
        auth_method: Optional[str] = None,
        request_size_bytes: Optional[int] = None,
        response_size_bytes: Optional[int] = None,
        rate_limit_tier: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        idempotent_cache_hit: bool = False,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None,
        query_params: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Record an API request."""
        client = await self._get_client()

        payload = {
            "request_id": request_id,
            "trace_id": trace_id,
            "span_id": span_id,
            "timestamp": timestamp,
            "method": method,
            "path": path,
            "status_code": status_code,
            "latency_ms": latency_ms,
            "authenticated": authenticated,
            "idempotent_cache_hit": idempotent_cache_hit
        }

        if consumer_id:
            payload["consumer_id"] = consumer_id
        if tenant_id:
            payload["tenant_id"] = tenant_id
        if auth_method:
            payload["auth_method"] = auth_method
        if request_size_bytes is not None:
            payload["request_size_bytes"] = request_size_bytes
        if response_size_bytes is not None:
            payload["response_size_bytes"] = response_size_bytes
        if rate_limit_tier:
            payload["rate_limit_tier"] = rate_limit_tier
        if idempotency_key:
            payload["idempotency_key"] = idempotency_key
        if error_code:
            payload["error_code"] = error_code
        if error_message:
            payload["error_message"] = error_message
        if client_ip:
            payload["client_ip"] = client_ip
        if user_agent:
            payload["user_agent"] = user_agent
        if headers:
            payload["headers"] = headers
        if query_params:
            payload["query_params"] = query_params
        if metadata:
            payload["metadata"] = metadata

        response = await client.post("/api-requests/", json=payload)
        response.raise_for_status()
        return response.json()

    async def record_authentication_event(
        self,
        event_id: str,
        timestamp: str,
        auth_method: str,
        success: bool,
        consumer_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        failure_reason: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Record an authentication event."""
        client = await self._get_client()

        payload = {
            "event_id": event_id,
            "timestamp": timestamp,
            "auth_method": auth_method,
            "success": success
        }

        if consumer_id:
            payload["consumer_id"] = consumer_id
        if tenant_id:
            payload["tenant_id"] = tenant_id
        if failure_reason:
            payload["failure_reason"] = failure_reason
        if client_ip:
            payload["client_ip"] = client_ip
        if user_agent:
            payload["user_agent"] = user_agent
        if metadata:
            payload["metadata"] = metadata

        response = await client.post("/authentication-events/", json=payload)
        response.raise_for_status()
        return response.json()

    async def record_rate_limit_event(
        self,
        event_id: str,
        timestamp: str,
        consumer_id: str,
        rate_limit_tier: str,
        tokens_remaining: int,
        tokens_limit: int,
        window_start: str,
        window_end: str,
        tenant_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        tokens_requested: int = 1,
        exceeded: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Record a rate limit event."""
        client = await self._get_client()

        payload = {
            "event_id": event_id,
            "timestamp": timestamp,
            "consumer_id": consumer_id,
            "rate_limit_tier": rate_limit_tier,
            "tokens_requested": tokens_requested,
            "tokens_remaining": tokens_remaining,
            "tokens_limit": tokens_limit,
            "window_start": window_start,
            "window_end": window_end,
            "exceeded": exceeded
        }

        if tenant_id:
            payload["tenant_id"] = tenant_id
        if endpoint:
            payload["endpoint"] = endpoint
        if metadata:
            payload["metadata"] = metadata

        response = await client.post("/rate-limit-events/", json=payload)
        response.raise_for_status()
        return response.json()

    # ===================================================================
    # L10 Human Interface Methods
    # ===================================================================

    async def record_user_interaction(
        self,
        interaction_id: str,
        timestamp: str,
        interaction_type: str,
        action: str,
        user_id: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        result: Optional[str] = None,
        error_message: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Record a user interaction."""
        client = await self._get_client()

        payload = {
            "interaction_id": interaction_id,
            "timestamp": timestamp,
            "interaction_type": interaction_type,
            "action": action
        }

        if user_id:
            payload["user_id"] = user_id
        if target_type:
            payload["target_type"] = target_type
        if target_id:
            payload["target_id"] = target_id
        if parameters:
            payload["parameters"] = parameters
        if result:
            payload["result"] = result
        if error_message:
            payload["error_message"] = error_message
        if client_ip:
            payload["client_ip"] = client_ip
        if user_agent:
            payload["user_agent"] = user_agent
        if session_id:
            payload["session_id"] = session_id
        if metadata:
            payload["metadata"] = metadata

        response = await client.post("/user-interactions/", json=payload)
        response.raise_for_status()
        return response.json()

    async def record_control_operation(
        self,
        operation_id: str,
        timestamp: str,
        user_id: str,
        operation_type: str,
        command: str,
        target_agent_id: Optional[UUID] = None,
        target_agent_did: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        status: str = "pending",
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        executed_at: Optional[str] = None,
        completed_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Record a control operation."""
        client = await self._get_client()

        payload = {
            "operation_id": operation_id,
            "timestamp": timestamp,
            "user_id": user_id,
            "operation_type": operation_type,
            "command": command,
            "status": status
        }

        if target_agent_id:
            payload["target_agent_id"] = str(target_agent_id)
        if target_agent_did:
            payload["target_agent_did"] = target_agent_did
        if parameters:
            payload["parameters"] = parameters
        if result:
            payload["result"] = result
        if error_message:
            payload["error_message"] = error_message
        if executed_at:
            payload["executed_at"] = executed_at
        if completed_at:
            payload["completed_at"] = completed_at
        if metadata:
            payload["metadata"] = metadata

        response = await client.post("/control-operations/", json=payload)
        response.raise_for_status()
        return response.json()

    async def update_control_operation(
        self,
        operation_id: str,
        status: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        executed_at: Optional[str] = None,
        completed_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update a control operation status."""
        client = await self._get_client()

        payload = {}
        if status:
            payload["status"] = status
        if result:
            payload["result"] = result
        if error_message:
            payload["error_message"] = error_message
        if executed_at:
            payload["executed_at"] = executed_at
        if completed_at:
            payload["completed_at"] = completed_at

        response = await client.patch(f"/control-operations/{operation_id}", json=payload)
        response.raise_for_status()
        return response.json()

    # ===================================================================
    # L11 Integration Layer Methods
    # ===================================================================

    async def record_saga_execution(
        self,
        saga_id: str,
        saga_name: str,
        started_at: str,
        steps_total: int,
        status: str = "running",
        steps_completed: int = 0,
        steps_failed: int = 0,
        current_step: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        compensation_mode: bool = False,
        completed_at: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Record a saga execution."""
        client = await self._get_client()

        payload = {
            "saga_id": saga_id,
            "saga_name": saga_name,
            "started_at": started_at,
            "steps_total": steps_total,
            "status": status,
            "steps_completed": steps_completed,
            "steps_failed": steps_failed,
            "compensation_mode": compensation_mode
        }

        if current_step:
            payload["current_step"] = current_step
        if context:
            payload["context"] = context
        if completed_at:
            payload["completed_at"] = completed_at
        if error_message:
            payload["error_message"] = error_message
        if metadata:
            payload["metadata"] = metadata

        response = await client.post("/saga-executions/", json=payload)
        response.raise_for_status()
        return response.json()

    async def update_saga_execution(
        self,
        saga_id: str,
        status: Optional[str] = None,
        steps_completed: Optional[int] = None,
        steps_failed: Optional[int] = None,
        current_step: Optional[str] = None,
        compensation_mode: Optional[bool] = None,
        completed_at: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update a saga execution status."""
        client = await self._get_client()

        payload = {}
        if status:
            payload["status"] = status
        if steps_completed is not None:
            payload["steps_completed"] = steps_completed
        if steps_failed is not None:
            payload["steps_failed"] = steps_failed
        if current_step:
            payload["current_step"] = current_step
        if compensation_mode is not None:
            payload["compensation_mode"] = compensation_mode
        if completed_at:
            payload["completed_at"] = completed_at
        if error_message:
            payload["error_message"] = error_message

        response = await client.patch(f"/saga-executions/{saga_id}", json=payload)
        response.raise_for_status()
        return response.json()

    async def record_saga_step(
        self,
        step_id: str,
        saga_id: str,
        step_name: str,
        step_index: int,
        service_id: str,
        status: str = "pending",
        started_at: Optional[str] = None,
        completed_at: Optional[str] = None,
        request: Optional[Dict[str, Any]] = None,
        response: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        compensation_executed: bool = False,
        compensation_result: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Record a saga step."""
        client = await self._get_client()

        payload = {
            "step_id": step_id,
            "saga_id": saga_id,
            "step_name": step_name,
            "step_index": step_index,
            "service_id": service_id,
            "status": status,
            "compensation_executed": compensation_executed,
            "retry_count": retry_count
        }

        if started_at:
            payload["started_at"] = started_at
        if completed_at:
            payload["completed_at"] = completed_at
        if request:
            payload["request"] = request
        if response:
            payload["response"] = response
        if error_message:
            payload["error_message"] = error_message
        if compensation_result:
            payload["compensation_result"] = compensation_result
        if metadata:
            payload["metadata"] = metadata

        response = await client.post("/saga-steps/", json=payload)
        response.raise_for_status()
        return response.json()

    async def update_saga_step(
        self,
        step_id: str,
        status: Optional[str] = None,
        started_at: Optional[str] = None,
        completed_at: Optional[str] = None,
        response: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        compensation_executed: Optional[bool] = None,
        compensation_result: Optional[Dict[str, Any]] = None,
        retry_count: Optional[int] = None
    ) -> Dict[str, Any]:
        """Update a saga step."""
        client = await self._get_client()

        payload = {}
        if status:
            payload["status"] = status
        if started_at:
            payload["started_at"] = started_at
        if completed_at:
            payload["completed_at"] = completed_at
        if response:
            payload["response"] = response
        if error_message:
            payload["error_message"] = error_message
        if compensation_executed is not None:
            payload["compensation_executed"] = compensation_executed
        if compensation_result:
            payload["compensation_result"] = compensation_result
        if retry_count is not None:
            payload["retry_count"] = retry_count

        response = await client.patch(f"/saga-steps/{step_id}", json=payload)
        response.raise_for_status()
        return response.json()

    async def record_circuit_breaker_event(
        self,
        event_id: str,
        timestamp: str,
        service_id: str,
        circuit_name: str,
        event_type: str,
        state_to: str,
        state_from: Optional[str] = None,
        failure_count: Optional[int] = None,
        success_count: Optional[int] = None,
        failure_threshold: Optional[int] = None,
        timeout_seconds: Optional[int] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Record a circuit breaker event."""
        client = await self._get_client()

        payload = {
            "event_id": event_id,
            "timestamp": timestamp,
            "service_id": service_id,
            "circuit_name": circuit_name,
            "event_type": event_type,
            "state_to": state_to
        }

        if state_from:
            payload["state_from"] = state_from
        if failure_count is not None:
            payload["failure_count"] = failure_count
        if success_count is not None:
            payload["success_count"] = success_count
        if failure_threshold is not None:
            payload["failure_threshold"] = failure_threshold
        if timeout_seconds is not None:
            payload["timeout_seconds"] = timeout_seconds
        if error_message:
            payload["error_message"] = error_message
        if metadata:
            payload["metadata"] = metadata

        response = await client.post("/circuit-breaker-events/", json=payload)
        response.raise_for_status()
        return response.json()

    async def record_service_registry_event(
        self,
        event_id: str,
        timestamp: str,
        service_id: str,
        event_type: str,
        layer: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        health_status: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Record a service registry event."""
        client = await self._get_client()

        payload = {
            "event_id": event_id,
            "timestamp": timestamp,
            "service_id": service_id,
            "event_type": event_type
        }

        if layer:
            payload["layer"] = layer
        if host:
            payload["host"] = host
        if port is not None:
            payload["port"] = port
        if health_status:
            payload["health_status"] = health_status
        if capabilities:
            payload["capabilities"] = capabilities
        if metadata:
            payload["metadata"] = metadata

        response = await client.post("/service-registry-events/", json=payload)
        response.raise_for_status()
        return response.json()

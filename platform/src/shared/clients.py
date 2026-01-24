"""
Shared API Clients for Cross-Layer Communication.

This module provides HTTP clients for communicating between platform layers.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx

logger = logging.getLogger(__name__)


class L01Client:
    """
    HTTP client for L01 Data Layer API.

    Provides methods for recording and retrieving data from L01,
    used by bridges in L02-L11 layers.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8002",
        timeout: float = 30.0
    ):
        """Initialize L01 client.

        Args:
            base_url: Base URL for L01 Data Layer API
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        logger.debug(f"L01Client initialized with base_url={base_url}")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
            logger.debug("L01Client closed")

    # =========================================================================
    # Tool Execution Methods
    # =========================================================================

    async def record_tool_execution(
        self,
        invocation_id: UUID,
        tool_name: str,
        input_params: Optional[Dict[str, Any]] = None,
        tool_version: Optional[str] = None,
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
        timeout_seconds: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Record a tool execution in L01.

        Args:
            invocation_id: Unique invocation ID
            tool_name: Name of the tool
            input_params: Input parameters
            tool_version: Tool version
            agent_did: Agent DID
            tenant_id: Tenant ID
            session_id: Session ID
            parent_sandbox_id: Parent sandbox ID
            status: Execution status
            async_mode: Whether execution is async
            priority: Execution priority
            idempotency_key: Idempotency key
            require_approval: Whether approval is required
            cpu_millicore_limit: CPU limit in millicores
            memory_mb_limit: Memory limit in MB
            timeout_seconds: Timeout in seconds
            **kwargs: Additional fields

        Returns:
            Created execution record
        """
        client = await self._get_client()

        payload = {
            "invocation_id": str(invocation_id),
            "tool_name": tool_name,
            "input_params": input_params or {},
            "tool_version": tool_version,
            "agent_did": agent_did,
            "tenant_id": tenant_id,
            "session_id": session_id,
            "parent_sandbox_id": parent_sandbox_id,
            "status": status,
            "async_mode": async_mode,
            "priority": priority,
            "idempotency_key": idempotency_key,
            "require_approval": require_approval,
            "cpu_millicore_limit": cpu_millicore_limit,
            "memory_mb_limit": memory_mb_limit,
            "timeout_seconds": timeout_seconds,
            **kwargs
        }

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        response = await client.post("/tools/tool-executions", json=payload)
        response.raise_for_status()
        return response.json()

    async def update_tool_execution(
        self,
        invocation_id: UUID,
        **updates
    ) -> Dict[str, Any]:
        """Update a tool execution in L01.

        Args:
            invocation_id: Invocation ID to update
            **updates: Fields to update

        Returns:
            Updated execution record
        """
        client = await self._get_client()

        # Convert UUID values to strings
        payload = {}
        for key, value in updates.items():
            if isinstance(value, UUID):
                payload[key] = str(value)
            elif value is not None:
                payload[key] = value

        response = await client.patch(
            f"/tools/executions/{invocation_id}",
            json=payload
        )
        response.raise_for_status()
        return response.json()

    async def get_tool_execution_by_invocation(
        self,
        invocation_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get tool execution by invocation ID.

        Args:
            invocation_id: Invocation ID

        Returns:
            Execution record or None if not found
        """
        client = await self._get_client()

        try:
            response = await client.get(
                f"/tools/executions/by-invocation/{invocation_id}"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    # =========================================================================
    # Goal Methods
    # =========================================================================

    async def record_goal(
        self,
        goal_id: str,
        agent_did: str,
        goal_text: str,
        agent_id: Optional[str] = None,
        goal_type: str = "compound",
        status: str = "pending",
        constraints: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        parent_goal_id: Optional[str] = None,
        decomposition_strategy: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Record a goal in L01.

        Args:
            goal_id: Goal ID
            agent_did: Agent DID
            goal_text: Goal description text
            agent_id: Agent ID
            goal_type: Type of goal
            status: Goal status
            constraints: Goal constraints
            metadata: Additional metadata
            parent_goal_id: Parent goal ID for sub-goals
            decomposition_strategy: Strategy used for decomposition
            **kwargs: Additional fields

        Returns:
            Created goal record
        """
        client = await self._get_client()

        payload = {
            "goal_id": goal_id,
            "agent_did": agent_did,
            "goal_text": goal_text,
            "agent_id": agent_id,
            "goal_type": goal_type,
            "status": status,
            "constraints": constraints or {},
            "metadata": metadata or {},
            "parent_goal_id": parent_goal_id,
            "decomposition_strategy": decomposition_strategy,
            **kwargs
        }

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        response = await client.post("/goals/", json=payload)
        response.raise_for_status()
        return response.json()

    async def update_goal_status(
        self,
        goal_id: str,
        status: str,
        decomposition_strategy: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Update goal status in L01.

        Args:
            goal_id: Goal ID to update
            status: New status
            decomposition_strategy: Decomposition strategy
            **kwargs: Additional fields to update

        Returns:
            Updated goal record
        """
        client = await self._get_client()

        payload = {"status": status}
        if decomposition_strategy:
            payload["decomposition_strategy"] = decomposition_strategy
        payload.update(kwargs)

        response = await client.patch(f"/goals/{goal_id}", json=payload)
        response.raise_for_status()
        return response.json()

    async def get_goal(self, goal_id: str) -> Optional[Dict[str, Any]]:
        """Get goal by ID.

        Args:
            goal_id: Goal ID

        Returns:
            Goal record or None if not found
        """
        client = await self._get_client()

        try:
            response = await client.get(f"/goals/{goal_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    # =========================================================================
    # Plan Methods
    # =========================================================================

    async def record_plan(
        self,
        plan_id: str,
        goal_id: str,
        agent_id: Optional[str] = None,
        tasks: Optional[List[Dict[str, Any]]] = None,
        dependency_graph: Optional[Dict[str, Any]] = None,
        status: str = "pending",
        resource_budget: Optional[Dict[str, Any]] = None,
        decomposition_strategy: Optional[str] = None,
        decomposition_latency_ms: Optional[float] = None,
        cache_hit: bool = False,
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None,
        total_tokens_used: Optional[int] = None,
        validation_time_ms: Optional[float] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Record an execution plan in L01.

        Args:
            plan_id: Plan ID
            goal_id: Associated goal ID
            agent_id: Agent ID
            tasks: List of task definitions
            dependency_graph: Task dependency graph
            status: Plan status
            resource_budget: Resource budget constraints
            decomposition_strategy: Strategy used for decomposition
            decomposition_latency_ms: Time to decompose in ms
            cache_hit: Whether plan was from cache
            llm_provider: LLM provider used
            llm_model: LLM model used
            total_tokens_used: Total tokens used
            validation_time_ms: Validation time in ms
            tags: Plan tags
            metadata: Additional metadata
            **kwargs: Additional fields

        Returns:
            Created plan record
        """
        client = await self._get_client()

        payload = {
            "plan_id": plan_id,
            "goal_id": goal_id,
            "agent_id": agent_id,
            "tasks": tasks or [],
            "dependency_graph": dependency_graph or {},
            "status": status,
            "resource_budget": resource_budget,
            "decomposition_strategy": decomposition_strategy,
            "decomposition_latency_ms": decomposition_latency_ms,
            "cache_hit": cache_hit,
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "total_tokens_used": total_tokens_used,
            "validation_time_ms": validation_time_ms,
            "tags": tags or [],
            "metadata": metadata or {},
            **kwargs
        }

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

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
        failed_task_count: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Update plan status in L01.

        Args:
            plan_id: Plan ID to update
            status: New status
            validated_at: Validation timestamp (ISO format)
            execution_started_at: Start timestamp (ISO format)
            execution_completed_at: Completion timestamp (ISO format)
            execution_time_ms: Total execution time in ms
            parallelism_achieved: Number of parallel tasks
            error: Error message if failed
            completed_task_count: Number of completed tasks
            failed_task_count: Number of failed tasks
            **kwargs: Additional fields

        Returns:
            Updated plan record
        """
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

        payload.update(kwargs)

        response = await client.patch(f"/plans/{plan_id}", json=payload)
        response.raise_for_status()
        return response.json()

    async def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get plan by ID.

        Args:
            plan_id: Plan ID

        Returns:
            Plan record or None if not found
        """
        client = await self._get_client()

        try:
            response = await client.get(f"/plans/{plan_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    # =========================================================================
    # Agent Methods
    # =========================================================================

    async def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent by ID.

        Args:
            agent_id: Agent ID

        Returns:
            Agent record or None if not found
        """
        client = await self._get_client()

        try:
            response = await client.get(f"/agents/{agent_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    async def list_agents(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List agents with optional filters.

        Args:
            status: Filter by status
            limit: Maximum number of results
            offset: Result offset

        Returns:
            List of agent records
        """
        client = await self._get_client()

        params = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status

        response = await client.get("/agents/", params=params)
        response.raise_for_status()
        return response.json()

    # =========================================================================
    # Session Methods
    # =========================================================================

    async def create_session(
        self,
        agent_id: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new session.

        Args:
            agent_id: Agent ID
            user_id: User ID
            metadata: Session metadata

        Returns:
            Created session record
        """
        client = await self._get_client()

        payload = {
            "agent_id": agent_id,
            "user_id": user_id,
            "metadata": metadata or {}
        }

        response = await client.post("/sessions/", json=payload)
        response.raise_for_status()
        return response.json()

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID.

        Args:
            session_id: Session ID

        Returns:
            Session record or None if not found
        """
        client = await self._get_client()

        try:
            response = await client.get(f"/sessions/{session_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    # =========================================================================
    # Event Methods
    # =========================================================================

    async def record_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        source: str,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Record an event in L01.

        Args:
            event_type: Type of event
            payload: Event payload
            source: Event source
            correlation_id: Correlation ID
            metadata: Event metadata

        Returns:
            Created event record
        """
        client = await self._get_client()

        event_data = {
            "event_type": event_type,
            "payload": payload,
            "source": source,
            "correlation_id": correlation_id,
            "metadata": metadata or {}
        }

        response = await client.post("/events/", json=event_data)
        response.raise_for_status()
        return response.json()

"""
L05 Planning Layer - Agent Assigner Service.

Assigns tasks to qualified agents based on:
- Capability matching
- Availability
- Load balancing
- Affinity (prefer same agent for related tasks)
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import uuid4

from ..models import (
    Task,
    Agent,
    AgentCapability,
    AgentAssignment,
    AssignmentStatus,
    CapabilityType,
    PlanningError,
    ErrorCode,
)

logger = logging.getLogger(__name__)


class AgentAssigner:
    """
    Assigns tasks to agents based on capabilities and load.

    Strategies:
    - Capability matching: Find agents with required capabilities
    - Load balancing: Distribute tasks across agents
    - Affinity: Prefer same agent for related tasks
    """

    def __init__(
        self,
        agent_registry_client=None,  # L02 Agent Registry client
        l01_client=None,  # L01 Data Layer client for agent fetching
        load_balance_strategy: str = "least_loaded",  # "least_loaded", "round_robin"
        affinity_enabled: bool = True,
    ):
        """
        Initialize Agent Assigner.

        Args:
            agent_registry_client: Client for L02 Agent Registry
            l01_client: L01 Data Layer client (shared.clients.L01Client)
            load_balance_strategy: Load balancing strategy
            affinity_enabled: Enable task affinity
        """
        self.agent_registry_client = agent_registry_client
        self.l01_client = l01_client
        self.load_balance_strategy = load_balance_strategy
        self.affinity_enabled = affinity_enabled

        # Agent tracking
        self._agent_cache: Dict[str, Agent] = {}
        self._affinity_map: Dict[str, str] = {}  # plan_id -> agent_did

        # Metrics
        self.assignments_made = 0
        self.assignment_failures = 0
        self.affinity_hits = 0

        logger.info(f"AgentAssigner initialized (strategy: {load_balance_strategy})")

    async def assign(
        self,
        task: Task,
        plan_id: str,
        available_agents: Optional[List[Agent]] = None,
    ) -> AgentAssignment:
        """
        Assign task to appropriate agent.

        Args:
            task: Task to assign
            plan_id: Plan ID for affinity tracking
            available_agents: Optional list of available agents (fetches if None)

        Returns:
            AgentAssignment with assigned agent

        Raises:
            PlanningError: If no suitable agent found
        """
        try:
            # Get available agents
            if available_agents is None:
                available_agents = await self._get_available_agents()

            if not available_agents:
                raise PlanningError.from_code(
                    ErrorCode.E5901,
                    details={"task_id": task.task_id},
                    recovery_suggestion="Ensure agents are registered and available",
                )

            # Determine required capabilities for task
            required_capabilities = self._get_required_capabilities(task)

            # Filter agents by capability
            capable_agents = [
                agent
                for agent in available_agents
                if self._has_required_capabilities(agent, required_capabilities)
            ]

            if not capable_agents:
                raise PlanningError.from_code(
                    ErrorCode.E5902,
                    details={
                        "task_id": task.task_id,
                        "required_capabilities": [c.value for c in required_capabilities],
                    },
                    recovery_suggestion="Register agents with required capabilities",
                )

            # Filter agents that can accept more work
            available_capable = [
                agent for agent in capable_agents if agent.can_accept_task()
            ]

            if not available_capable:
                raise PlanningError.from_code(
                    ErrorCode.E5901,
                    details={
                        "task_id": task.task_id,
                        "reason": "All capable agents at max load",
                    },
                    recovery_suggestion="Wait for agents to complete current tasks",
                )

            # Select agent using strategy
            selected_agent = self._select_agent(available_capable, task, plan_id)

            # Create assignment
            assignment = AgentAssignment(
                assignment_id=str(uuid4()),
                task_id=task.task_id,
                agent_did=selected_agent.agent_did,
                plan_id=plan_id,
                status=AssignmentStatus.ASSIGNED,
                assigned_at=datetime.utcnow(),
                affinity_score=self._calculate_affinity(selected_agent, plan_id),
                load_score=selected_agent.get_load_ratio(),
            )

            # Update agent load
            selected_agent.current_load += 1

            # Track affinity
            if self.affinity_enabled:
                self._affinity_map[plan_id] = selected_agent.agent_did

            self.assignments_made += 1
            logger.info(
                f"Assigned task {task.name} to agent {selected_agent.agent_did} "
                f"(load: {selected_agent.get_load_ratio():.2f})"
            )

            return assignment

        except PlanningError:
            self.assignment_failures += 1
            raise
        except Exception as e:
            self.assignment_failures += 1
            logger.error(f"Agent assignment failed: {e}")
            raise PlanningError.from_code(
                ErrorCode.E5903,
                details={"task_id": task.task_id, "error": str(e)},
            )

    def _get_required_capabilities(self, task: Task) -> List[CapabilityType]:
        """
        Determine required capabilities for task.

        Args:
            task: Task to analyze

        Returns:
            List of required capabilities
        """
        capabilities = []

        if task.task_type == "llm_call":
            capabilities.append(CapabilityType.LLM_INFERENCE)
            capabilities.append(CapabilityType.REASONING)

        elif task.task_type == "tool_call":
            capabilities.append(CapabilityType.TOOL_EXECUTION)

            # Specific tool capabilities
            if task.tool_name:
                if "file" in task.tool_name.lower():
                    capabilities.append(CapabilityType.FILE_OPERATIONS)
                if "network" in task.tool_name.lower():
                    capabilities.append(CapabilityType.NETWORK_ACCESS)

        elif task.task_type == "compound":
            # Compound tasks need general capabilities
            capabilities.append(CapabilityType.REASONING)
            capabilities.append(CapabilityType.TOOL_EXECUTION)

        else:
            # Atomic tasks
            capabilities.append(CapabilityType.CODE_EXECUTION)

        return capabilities

    def _has_required_capabilities(
        self,
        agent: Agent,
        required_capabilities: List[CapabilityType],
    ) -> bool:
        """
        Check if agent has all required capabilities.

        Args:
            agent: Agent to check
            required_capabilities: Required capabilities

        Returns:
            True if agent has all capabilities, False otherwise
        """
        agent_capability_types = {cap.capability_type for cap in agent.capabilities}

        for required in required_capabilities:
            if required not in agent_capability_types:
                return False

        return True

    def _select_agent(
        self,
        agents: List[Agent],
        task: Task,
        plan_id: str,
    ) -> Agent:
        """
        Select best agent using configured strategy.

        Args:
            agents: List of capable, available agents
            task: Task to assign
            plan_id: Plan ID for affinity

        Returns:
            Selected agent
        """
        # Check affinity first (prefer same agent for plan)
        if self.affinity_enabled and plan_id in self._affinity_map:
            affinity_agent_did = self._affinity_map[plan_id]
            affinity_agent = next(
                (a for a in agents if a.agent_did == affinity_agent_did), None
            )
            if affinity_agent:
                self.affinity_hits += 1
                logger.debug(f"Affinity match: using agent {affinity_agent_did}")
                return affinity_agent

        # Apply load balancing strategy
        if self.load_balance_strategy == "least_loaded":
            return min(agents, key=lambda a: a.get_load_ratio())

        elif self.load_balance_strategy == "round_robin":
            # Simple round-robin (rotate through agents)
            return agents[self.assignments_made % len(agents)]

        else:
            # Default: first available
            return agents[0]

    def _calculate_affinity(self, agent: Agent, plan_id: str) -> float:
        """
        Calculate affinity score for assignment.

        Args:
            agent: Selected agent
            plan_id: Plan ID

        Returns:
            Affinity score (0.0-1.0)
        """
        if self.affinity_enabled and plan_id in self._affinity_map:
            if self._affinity_map[plan_id] == agent.agent_did:
                return 1.0  # Perfect affinity
        return 0.0  # No affinity

    # Mapping from L01 capability strings to L05 CapabilityType
    _L01_CAPABILITY_MAP = {
        "data_processing": CapabilityType.DATA_PROCESSING,
        "task_execution": CapabilityType.TOOL_EXECUTION,
        "analysis": CapabilityType.REASONING,
        "reporting": CapabilityType.LLM_INFERENCE,
        "file_operations": CapabilityType.FILE_OPERATIONS,
        "code_execution": CapabilityType.CODE_EXECUTION,
        "llm_inference": CapabilityType.LLM_INFERENCE,
        "reasoning": CapabilityType.REASONING,
        "tool_execution": CapabilityType.TOOL_EXECUTION,
        "network_access": CapabilityType.NETWORK_ACCESS,
    }

    def _convert_l01_agent(self, l01_agent: Dict[str, Any]) -> Agent:
        """
        Convert L01 agent response to L05 Agent model.

        Args:
            l01_agent: Agent data from L01 (dict with id, did, status, configuration)

        Returns:
            L05 Agent model instance
        """
        # Extract capabilities from configuration
        config = l01_agent.get("configuration", {})
        l01_capabilities = config.get("capabilities", [])

        # Map L01 capability strings to L05 CapabilityType
        capabilities = []
        for cap_str in l01_capabilities:
            cap_type = self._L01_CAPABILITY_MAP.get(cap_str.lower())
            if cap_type:
                capabilities.append(AgentCapability(cap_type))

        # Default capabilities if none mapped
        if not capabilities:
            capabilities = [AgentCapability(CapabilityType.TOOL_EXECUTION)]

        # Determine availability from status
        is_available = l01_agent.get("status", "").lower() == "active"

        return Agent(
            agent_did=l01_agent.get("did", f"agent:{l01_agent.get('id', 'unknown')}"),
            capabilities=capabilities,
            current_load=0,  # L01 doesn't track load yet
            max_concurrent_tasks=5,  # Default
            is_available=is_available,
        )

    def _get_mock_agents(self) -> List[Agent]:
        """
        Get mock agents for fallback when L01 is unavailable.

        Returns:
            List of mock Agent objects
        """
        return [
            Agent(
                agent_did="did:agent:general-1",
                capabilities=[
                    AgentCapability(CapabilityType.TOOL_EXECUTION),
                    AgentCapability(CapabilityType.LLM_INFERENCE),
                    AgentCapability(CapabilityType.REASONING),
                    AgentCapability(CapabilityType.FILE_OPERATIONS),
                ],
                current_load=0,
                max_concurrent_tasks=5,
                is_available=True,
            ),
            Agent(
                agent_did="did:agent:general-2",
                capabilities=[
                    AgentCapability(CapabilityType.TOOL_EXECUTION),
                    AgentCapability(CapabilityType.LLM_INFERENCE),
                    AgentCapability(CapabilityType.REASONING),
                ],
                current_load=0,
                max_concurrent_tasks=5,
                is_available=True,
            ),
        ]

    async def _get_available_agents(self) -> List[Agent]:
        """
        Get list of available agents from L01 or fallback to mock.

        Returns:
            List of Agent objects
        """
        # Try L01 client first
        if self.l01_client:
            try:
                logger.debug("Fetching available agents from L01")
                l01_agents = await self.l01_client.list_agents(status="active")
                if l01_agents:
                    agents = [self._convert_l01_agent(a) for a in l01_agents]
                    # Filter to only available agents
                    available = [a for a in agents if a.is_available]
                    if available:
                        logger.info(f"Fetched {len(available)} agents from L01")
                        return available
                logger.debug("L01 returned no agents, falling back to mock")
            except Exception as e:
                logger.warning(f"L01 unavailable, using mock agents: {e}")

        # Fallback to mock agents
        logger.debug("Using mock agents")
        return self._get_mock_agents()

    def release_assignment(self, assignment: AgentAssignment) -> None:
        """
        Release agent assignment (task completed).

        Args:
            assignment: Assignment to release
        """
        # Find agent and decrease load
        if assignment.agent_did in self._agent_cache:
            agent = self._agent_cache[assignment.agent_did]
            agent.current_load = max(0, agent.current_load - 1)
            logger.debug(f"Released assignment for agent {assignment.agent_did}")

    def get_stats(self) -> Dict[str, Any]:
        """Get assigner statistics."""
        return {
            "assignments_made": self.assignments_made,
            "assignment_failures": self.assignment_failures,
            "affinity_hits": self.affinity_hits,
            "affinity_hit_rate": self.affinity_hits / max(1, self.assignments_made),
            "failure_rate": self.assignment_failures / max(1, self.assignments_made),
        }

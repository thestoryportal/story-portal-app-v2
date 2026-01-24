"""
Handoff Coordinator

Manages cross-agent artifact handoffs for multi-role orchestration.
Enables sequential and parallel workflow patterns with artifact passing between roles.

Based on multi-agent orchestration patterns for complex task decomposition.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable, Protocol
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4


logger = logging.getLogger(__name__)


class HandoffError(Exception):
    """Handoff operation error"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class HandoffStatus(Enum):
    """Status of a handoff artifact"""
    PENDING = "pending"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    REJECTED = "rejected"


class ArtifactType(Enum):
    """Types of artifacts that can be handed off between roles"""
    DESIGN_DOC = "design_doc"
    API_CONTRACT = "api_contract"
    CODE_REVIEW = "code_review"
    TEST_RESULTS = "test_results"
    IMPLEMENTATION = "implementation"
    REQUIREMENTS = "requirements"
    SPECIFICATION = "specification"
    ANALYSIS = "analysis"
    FEEDBACK = "feedback"
    APPROVAL = "approval"
    CUSTOM = "custom"


@dataclass
class HandoffArtifact:
    """
    Artifact passed between roles during orchestration.

    Represents a unit of work output that can be consumed by another role.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    source_role_id: str = ""
    target_role_id: str = ""
    artifact_type: str = "custom"
    content: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    delivered_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "id": self.id,
            "source_role_id": self.source_role_id,
            "target_role_id": self.target_role_id,
            "artifact_type": self.artifact_type,
            "content": self.content,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HandoffArtifact":
        """Create from dictionary representation"""
        return cls(
            id=data.get("id", str(uuid4())),
            source_role_id=data.get("source_role_id", ""),
            target_role_id=data.get("target_role_id", ""),
            artifact_type=data.get("artifact_type", "custom"),
            content=data.get("content", {}),
            status=data.get("status", "pending"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc),
            delivered_at=datetime.fromisoformat(data["delivered_at"]) if data.get("delivered_at") else None,
            acknowledged_at=datetime.fromisoformat(data["acknowledged_at"]) if data.get("acknowledged_at") else None,
            metadata=data.get("metadata", {}),
        )


@dataclass
class OrchestrationResult:
    """
    Result of a multi-role orchestration workflow.

    Contains results from each role execution and collected artifacts.
    """
    results: List[Dict[str, Any]] = field(default_factory=list)
    artifacts: List[HandoffArtifact] = field(default_factory=list)
    total_duration_ms: int = 0
    success: bool = True
    workflow_id: str = field(default_factory=lambda: str(uuid4()))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    role_sequence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "workflow_id": self.workflow_id,
            "results": self.results,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "total_duration_ms": self.total_duration_ms,
            "success": self.success,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "role_sequence": self.role_sequence,
        }


class ContextBuilder(Protocol):
    """Protocol for context building dependency"""
    async def build_context(self, role_id: str, task: Dict[str, Any], artifacts: List[HandoffArtifact]) -> Dict[str, Any]:
        """Build execution context for a role"""
        ...


class CheckpointHandler(Protocol):
    """Protocol for checkpoint handling dependency"""
    async def save_checkpoint(self, workflow_id: str, state: Dict[str, Any]) -> str:
        """Save workflow checkpoint"""
        ...

    async def load_checkpoint(self, checkpoint_id: str) -> Dict[str, Any]:
        """Load workflow checkpoint"""
        ...


@dataclass
class RoleExecution:
    """Tracks a single role execution within a workflow"""
    role_id: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    artifacts_produced: List[HandoffArtifact] = field(default_factory=list)
    success: bool = False
    error: Optional[str] = None


class HandoffCoordinator:
    """
    Coordinates cross-agent artifact handoffs for multi-role orchestration.

    Supports two orchestration patterns:
    1. Sequential Chain: [Architect] -> [Developer] -> [Reviewer] -> [QA]
    2. Parallel Specialists: Fork to multiple roles, then merge results

    Responsibilities:
    - Execute roles in sequence, passing artifacts between them
    - Handle parallel execution and result merging
    - Process STOP checkpoints
    - Manage handoff lifecycle (create, deliver, acknowledge, reject)
    - Track artifact provenance
    """

    def __init__(
        self,
        context_builder: Optional[ContextBuilder] = None,
        checkpoint_handler: Optional[CheckpointHandler] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize HandoffCoordinator.

        Args:
            context_builder: Builds execution context for roles
            checkpoint_handler: Handles workflow checkpointing
            config: Configuration dict with:
                - role_timeout_seconds: Timeout for role execution
                - max_parallel_roles: Maximum concurrent role executions
                - checkpoint_on_handoff: Checkpoint after each handoff
                - retry_on_failure: Retry failed role executions
                - max_retries: Maximum retry attempts
        """
        self.context_builder = context_builder
        self.checkpoint_handler = checkpoint_handler
        self.config = config or {}

        # Configuration
        self.role_timeout = self.config.get("role_timeout_seconds", 300)
        self.max_parallel_roles = self.config.get("max_parallel_roles", 5)
        self.checkpoint_on_handoff = self.config.get("checkpoint_on_handoff", True)
        self.retry_on_failure = self.config.get("retry_on_failure", True)
        self.max_retries = self.config.get("max_retries", 3)

        # Role executors: role_id -> callable
        self._role_executors: Dict[str, Callable] = {}

        # Active handoffs: handoff_id -> HandoffArtifact
        self._handoffs: Dict[str, HandoffArtifact] = {}

        # Active workflows: workflow_id -> OrchestrationResult
        self._active_workflows: Dict[str, OrchestrationResult] = {}

        # Execution semaphore for parallel role control
        self._execution_semaphore = asyncio.Semaphore(self.max_parallel_roles)

        logger.info(
            f"HandoffCoordinator initialized: "
            f"role_timeout={self.role_timeout}s, "
            f"max_parallel_roles={self.max_parallel_roles}"
        )

    async def initialize(self) -> None:
        """Initialize the coordinator"""
        logger.info("HandoffCoordinator initialization complete")

    def register_role_executor(
        self,
        role_id: str,
        executor: Callable
    ) -> None:
        """
        Register an executor for a role.

        Args:
            role_id: Role identifier
            executor: Async callable(task, context) -> result dict
        """
        self._role_executors[role_id] = executor
        logger.info(f"Registered role executor: {role_id}")

    def unregister_role_executor(self, role_id: str) -> None:
        """
        Unregister a role executor.

        Args:
            role_id: Role identifier
        """
        if role_id in self._role_executors:
            del self._role_executors[role_id]
            logger.info(f"Unregistered role executor: {role_id}")

    async def orchestrate_workflow(
        self,
        task: Dict[str, Any],
        role_sequence: List[str],
        initial_context: Optional[Dict[str, Any]] = None
    ) -> OrchestrationResult:
        """
        Execute roles in sequence, passing artifacts between them.

        Sequential Chain Pattern:
        Each role receives artifacts from the previous role and produces
        artifacts for the next role in the sequence.

        Args:
            task: The task to be executed across roles
            role_sequence: Ordered list of role IDs to execute
            initial_context: Optional initial context for first role

        Returns:
            OrchestrationResult with all role results and artifacts

        Raises:
            HandoffError: If orchestration fails
        """
        workflow_id = str(uuid4())
        started_at = datetime.now(timezone.utc)

        logger.info(
            f"Starting sequential workflow {workflow_id} with roles: {role_sequence}"
        )

        result = OrchestrationResult(
            workflow_id=workflow_id,
            started_at=started_at,
            role_sequence=role_sequence,
        )
        self._active_workflows[workflow_id] = result

        try:
            # Track accumulated artifacts
            accumulated_artifacts: List[HandoffArtifact] = []
            context = initial_context or {}

            for i, role_id in enumerate(role_sequence):
                logger.debug(f"Executing role {i+1}/{len(role_sequence)}: {role_id}")

                # Build context with artifacts from previous roles
                if self.context_builder:
                    context = await self.context_builder.build_context(
                        role_id=role_id,
                        task=task,
                        artifacts=accumulated_artifacts
                    )
                else:
                    context = {
                        "task": task,
                        "artifacts": [a.to_dict() for a in accumulated_artifacts],
                        "role_position": i,
                        "total_roles": len(role_sequence),
                        "previous_role": role_sequence[i-1] if i > 0 else None,
                        "next_role": role_sequence[i+1] if i < len(role_sequence) - 1 else None,
                    }

                # Execute the role
                role_result = await self.execute_role(role_id, task, context)
                result.results.append(role_result)

                # Check for failure
                if not role_result.get("success", True):
                    result.success = False
                    result.error = role_result.get("error", f"Role {role_id} failed")
                    break

                # Extract artifacts from this role's output
                new_artifacts = self.extract_artifacts(role_result)

                # Set source and target roles for artifacts
                for artifact in new_artifacts:
                    artifact.source_role_id = role_id
                    if i < len(role_sequence) - 1:
                        artifact.target_role_id = role_sequence[i + 1]
                    artifact.status = HandoffStatus.DELIVERED.value
                    artifact.delivered_at = datetime.now(timezone.utc)

                accumulated_artifacts.extend(new_artifacts)
                result.artifacts.extend(new_artifacts)

                # Handle checkpoint if configured
                if self.checkpoint_on_handoff and self.checkpoint_handler:
                    checkpoint_data = {
                        "workflow_id": workflow_id,
                        "current_role_index": i,
                        "role_sequence": role_sequence,
                        "accumulated_artifacts": [a.to_dict() for a in accumulated_artifacts],
                        "results": result.results,
                    }
                    await self.checkpoint_handler.save_checkpoint(
                        workflow_id=workflow_id,
                        state=checkpoint_data
                    )

                # Check for STOP checkpoint in result
                if role_result.get("checkpoint", {}).get("action") == "STOP":
                    logger.info(f"STOP checkpoint received from role {role_id}")
                    await self.handle_checkpoint(role_result.get("checkpoint", {}))
                    break

            # Calculate duration
            completed_at = datetime.now(timezone.utc)
            result.completed_at = completed_at
            result.total_duration_ms = int(
                (completed_at - started_at).total_seconds() * 1000
            )

            logger.info(
                f"Workflow {workflow_id} completed: "
                f"success={result.success}, "
                f"duration={result.total_duration_ms}ms, "
                f"artifacts={len(result.artifacts)}"
            )

            return result

        except Exception as e:
            logger.error(f"Workflow {workflow_id} failed: {e}")
            result.success = False
            result.error = str(e)
            result.completed_at = datetime.now(timezone.utc)
            result.total_duration_ms = int(
                (result.completed_at - started_at).total_seconds() * 1000
            )
            raise HandoffError(
                code="E2100",
                message=f"Workflow orchestration failed: {str(e)}"
            )
        finally:
            if workflow_id in self._active_workflows:
                del self._active_workflows[workflow_id]

    async def orchestrate_parallel(
        self,
        task: Dict[str, Any],
        parallel_roles: List[str],
        merge_role: Optional[str] = None,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> OrchestrationResult:
        """
        Fork execution to multiple roles in parallel, then optionally merge results.

        Parallel Specialists Pattern:
        Multiple roles execute concurrently on the same task, and their
        results/artifacts are merged by an optional merge role.

        Args:
            task: The task to be executed by all roles
            parallel_roles: List of role IDs to execute in parallel
            merge_role: Optional role ID to merge parallel results
            initial_context: Optional initial context for all roles

        Returns:
            OrchestrationResult with merged results and artifacts

        Raises:
            HandoffError: If orchestration fails
        """
        workflow_id = str(uuid4())
        started_at = datetime.now(timezone.utc)

        logger.info(
            f"Starting parallel workflow {workflow_id} with roles: {parallel_roles}"
        )

        result = OrchestrationResult(
            workflow_id=workflow_id,
            started_at=started_at,
            role_sequence=parallel_roles + ([merge_role] if merge_role else []),
        )
        self._active_workflows[workflow_id] = result

        try:
            # Execute all roles in parallel
            tasks = []
            for role_id in parallel_roles:
                context = initial_context.copy() if initial_context else {}
                context["parallel_execution"] = True
                context["parallel_roles"] = parallel_roles
                tasks.append(self._execute_role_with_semaphore(role_id, task, context))

            # Wait for all parallel executions
            parallel_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            all_artifacts: List[HandoffArtifact] = []
            for i, role_result in enumerate(parallel_results):
                role_id = parallel_roles[i]

                if isinstance(role_result, Exception):
                    logger.error(f"Role {role_id} failed: {role_result}")
                    result.results.append({
                        "role_id": role_id,
                        "success": False,
                        "error": str(role_result),
                    })
                    result.success = False
                else:
                    result.results.append(role_result)

                    # Extract artifacts
                    new_artifacts = self.extract_artifacts(role_result)
                    for artifact in new_artifacts:
                        artifact.source_role_id = role_id
                        if merge_role:
                            artifact.target_role_id = merge_role
                        artifact.status = HandoffStatus.DELIVERED.value
                        artifact.delivered_at = datetime.now(timezone.utc)

                    all_artifacts.extend(new_artifacts)

            result.artifacts.extend(all_artifacts)

            # Execute merge role if specified and all parallel executions succeeded
            if merge_role and result.success:
                logger.debug(f"Executing merge role: {merge_role}")

                merge_context = initial_context.copy() if initial_context else {}
                merge_context["parallel_results"] = result.results
                merge_context["artifacts"] = [a.to_dict() for a in all_artifacts]
                merge_context["is_merge_role"] = True

                if self.context_builder:
                    merge_context = await self.context_builder.build_context(
                        role_id=merge_role,
                        task=task,
                        artifacts=all_artifacts
                    )

                merge_result = await self.execute_role(merge_role, task, merge_context)
                result.results.append(merge_result)

                if not merge_result.get("success", True):
                    result.success = False
                    result.error = merge_result.get("error", f"Merge role {merge_role} failed")
                else:
                    # Extract artifacts from merge role
                    merge_artifacts = self.extract_artifacts(merge_result)
                    for artifact in merge_artifacts:
                        artifact.source_role_id = merge_role
                        artifact.status = HandoffStatus.DELIVERED.value
                        artifact.delivered_at = datetime.now(timezone.utc)
                    result.artifacts.extend(merge_artifacts)

            # Calculate duration
            completed_at = datetime.now(timezone.utc)
            result.completed_at = completed_at
            result.total_duration_ms = int(
                (completed_at - started_at).total_seconds() * 1000
            )

            logger.info(
                f"Parallel workflow {workflow_id} completed: "
                f"success={result.success}, "
                f"duration={result.total_duration_ms}ms, "
                f"artifacts={len(result.artifacts)}"
            )

            return result

        except Exception as e:
            logger.error(f"Parallel workflow {workflow_id} failed: {e}")
            result.success = False
            result.error = str(e)
            result.completed_at = datetime.now(timezone.utc)
            result.total_duration_ms = int(
                (result.completed_at - started_at).total_seconds() * 1000
            )
            raise HandoffError(
                code="E2101",
                message=f"Parallel workflow orchestration failed: {str(e)}"
            )
        finally:
            if workflow_id in self._active_workflows:
                del self._active_workflows[workflow_id]

    async def _execute_role_with_semaphore(
        self,
        role_id: str,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute role with semaphore for parallel control"""
        async with self._execution_semaphore:
            return await self.execute_role(role_id, task, context)

    async def execute_role(
        self,
        role_id: str,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single role with the given task and context.

        Args:
            role_id: Role identifier
            task: Task to execute
            context: Execution context including artifacts from previous roles

        Returns:
            Role execution result dict

        Raises:
            HandoffError: If role execution fails
        """
        logger.debug(f"Executing role {role_id}")
        started_at = datetime.now(timezone.utc)

        # Get executor for this role
        executor = self._role_executors.get(role_id)
        if not executor:
            # Return simulated result if no executor registered
            logger.warning(f"No executor registered for role {role_id}, using simulation")
            return await self._simulate_role_execution(role_id, task, context)

        attempt = 0
        max_attempts = self.max_retries if self.retry_on_failure else 1
        last_error = None

        while attempt < max_attempts:
            try:
                # Execute with timeout
                result = await asyncio.wait_for(
                    executor(task, context),
                    timeout=self.role_timeout
                )

                # Ensure result has required fields
                if not isinstance(result, dict):
                    result = {"output": result}

                result.setdefault("role_id", role_id)
                result.setdefault("success", True)

                # Calculate execution time
                execution_time_ms = int(
                    (datetime.now(timezone.utc) - started_at).total_seconds() * 1000
                )
                result["execution_time_ms"] = execution_time_ms

                logger.debug(
                    f"Role {role_id} completed successfully "
                    f"(execution_time={execution_time_ms}ms)"
                )

                return result

            except asyncio.TimeoutError:
                last_error = f"Role execution timed out after {self.role_timeout}s"
                logger.warning(f"Role {role_id} timeout (attempt {attempt + 1})")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Role {role_id} failed (attempt {attempt + 1}): {e}")

            attempt += 1
            if attempt < max_attempts:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

        # All retries exhausted
        execution_time_ms = int(
            (datetime.now(timezone.utc) - started_at).total_seconds() * 1000
        )

        return {
            "role_id": role_id,
            "success": False,
            "error": last_error,
            "attempts": attempt,
            "execution_time_ms": execution_time_ms,
        }

    async def _simulate_role_execution(
        self,
        role_id: str,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simulate role execution for testing or when no executor is registered"""
        await asyncio.sleep(0.1)  # Simulate processing time

        return {
            "role_id": role_id,
            "success": True,
            "simulated": True,
            "output": f"Simulated execution for role {role_id}",
            "task_received": task,
            "context_received": context,
            "artifacts": [],
        }

    def extract_artifacts(self, result: Dict[str, Any]) -> List[HandoffArtifact]:
        """
        Extract handoff artifacts from role execution output.

        Looks for artifacts in the result dict under various keys:
        - "artifacts": List of artifact dicts
        - "handoff_artifacts": List of artifact dicts
        - "output.artifacts": Nested artifact list

        Args:
            result: Role execution result

        Returns:
            List of HandoffArtifact objects
        """
        artifacts: List[HandoffArtifact] = []

        # Check various locations for artifacts
        artifact_sources = [
            result.get("artifacts", []),
            result.get("handoff_artifacts", []),
            result.get("output", {}).get("artifacts", []) if isinstance(result.get("output"), dict) else [],
        ]

        for source in artifact_sources:
            if isinstance(source, list):
                for item in source:
                    if isinstance(item, dict):
                        artifact = HandoffArtifact.from_dict(item)
                        artifacts.append(artifact)
                    elif isinstance(item, HandoffArtifact):
                        artifacts.append(item)

        # Also check if result itself represents an artifact
        if result.get("artifact_type") and result.get("content"):
            artifact = HandoffArtifact(
                artifact_type=result.get("artifact_type", "custom"),
                content=result.get("content", {}),
                metadata=result.get("metadata", {}),
            )
            artifacts.append(artifact)

        logger.debug(f"Extracted {len(artifacts)} artifacts from result")
        return artifacts

    async def handle_checkpoint(self, checkpoint: Dict[str, Any]) -> None:
        """
        Process STOP checkpoints that pause workflow execution.

        Args:
            checkpoint: Checkpoint data with action, reason, and state
        """
        action = checkpoint.get("action", "")
        reason = checkpoint.get("reason", "Unknown")

        logger.info(f"Handling checkpoint: action={action}, reason={reason}")

        if action == "STOP":
            # Save current state for later resume
            if self.checkpoint_handler:
                checkpoint_id = await self.checkpoint_handler.save_checkpoint(
                    workflow_id=checkpoint.get("workflow_id", "unknown"),
                    state=checkpoint
                )
                logger.info(f"Workflow paused at checkpoint {checkpoint_id}")

        elif action == "PAUSE":
            # Similar to STOP but with different semantics
            logger.info("Workflow paused for human review")

        elif action == "ESCALATE":
            # Escalate to higher-level decision maker
            logger.warning(f"Checkpoint escalation required: {reason}")

    async def create_handoff(
        self,
        source_role: str,
        target_role: str,
        artifacts: List[Dict[str, Any]]
    ) -> str:
        """
        Create a pending handoff between roles.

        Args:
            source_role: Role creating the handoff
            target_role: Role receiving the handoff
            artifacts: List of artifact data dicts

        Returns:
            Handoff ID
        """
        handoff_id = str(uuid4())

        logger.info(
            f"Creating handoff {handoff_id}: {source_role} -> {target_role} "
            f"({len(artifacts)} artifacts)"
        )

        for artifact_data in artifacts:
            artifact = HandoffArtifact(
                id=str(uuid4()),
                source_role_id=source_role,
                target_role_id=target_role,
                artifact_type=artifact_data.get("artifact_type", "custom"),
                content=artifact_data.get("content", {}),
                status=HandoffStatus.PENDING.value,
                metadata={
                    "handoff_id": handoff_id,
                    **artifact_data.get("metadata", {}),
                },
            )
            self._handoffs[artifact.id] = artifact

        return handoff_id

    async def acknowledge_handoff(self, handoff_id: str) -> None:
        """
        Mark a handoff as acknowledged by the target role.

        Args:
            handoff_id: ID of the handoff to acknowledge

        Raises:
            HandoffError: If handoff not found
        """
        logger.debug(f"Acknowledging handoff {handoff_id}")

        # Find all artifacts associated with this handoff
        acknowledged_count = 0
        for artifact in self._handoffs.values():
            if artifact.metadata.get("handoff_id") == handoff_id:
                artifact.status = HandoffStatus.ACKNOWLEDGED.value
                artifact.acknowledged_at = datetime.now(timezone.utc)
                acknowledged_count += 1

        if acknowledged_count == 0:
            raise HandoffError(
                code="E2102",
                message=f"Handoff {handoff_id} not found"
            )

        logger.info(f"Handoff {handoff_id} acknowledged ({acknowledged_count} artifacts)")

    async def reject_handoff(
        self,
        handoff_id: str,
        reason: str
    ) -> None:
        """
        Reject a handoff with a reason.

        Args:
            handoff_id: ID of the handoff to reject
            reason: Reason for rejection

        Raises:
            HandoffError: If handoff not found
        """
        logger.debug(f"Rejecting handoff {handoff_id}: {reason}")

        rejected_count = 0
        for artifact in self._handoffs.values():
            if artifact.metadata.get("handoff_id") == handoff_id:
                artifact.status = HandoffStatus.REJECTED.value
                artifact.metadata["rejection_reason"] = reason
                rejected_count += 1

        if rejected_count == 0:
            raise HandoffError(
                code="E2102",
                message=f"Handoff {handoff_id} not found"
            )

        logger.warning(
            f"Handoff {handoff_id} rejected ({rejected_count} artifacts): {reason}"
        )

    async def get_handoff_artifacts(
        self,
        handoff_id: str
    ) -> List[HandoffArtifact]:
        """
        Get all artifacts associated with a handoff.

        Args:
            handoff_id: Handoff identifier

        Returns:
            List of HandoffArtifact objects
        """
        return [
            artifact for artifact in self._handoffs.values()
            if artifact.metadata.get("handoff_id") == handoff_id
        ]

    async def get_pending_handoffs(
        self,
        target_role: str
    ) -> List[HandoffArtifact]:
        """
        Get all pending handoffs for a target role.

        Args:
            target_role: Role identifier

        Returns:
            List of pending HandoffArtifact objects
        """
        return [
            artifact for artifact in self._handoffs.values()
            if artifact.target_role_id == target_role
            and artifact.status == HandoffStatus.PENDING.value
        ]

    def get_active_workflows(self) -> List[Dict[str, Any]]:
        """Get information about active workflows"""
        return [
            {
                "workflow_id": result.workflow_id,
                "started_at": result.started_at.isoformat() if result.started_at else None,
                "role_sequence": result.role_sequence,
                "results_count": len(result.results),
                "artifacts_count": len(result.artifacts),
            }
            for result in self._active_workflows.values()
        ]

    def get_health_status(self) -> Dict[str, Any]:
        """Get coordinator health status"""
        return {
            "healthy": True,
            "active_workflows": len(self._active_workflows),
            "registered_roles": list(self._role_executors.keys()),
            "pending_handoffs": sum(
                1 for a in self._handoffs.values()
                if a.status == HandoffStatus.PENDING.value
            ),
            "config": {
                "role_timeout_seconds": self.role_timeout,
                "max_parallel_roles": self.max_parallel_roles,
                "checkpoint_on_handoff": self.checkpoint_on_handoff,
                "retry_on_failure": self.retry_on_failure,
                "max_retries": self.max_retries,
            },
            "context_builder_available": self.context_builder is not None,
            "checkpoint_handler_available": self.checkpoint_handler is not None,
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get coordinator metrics"""
        handoff_status_counts = {}
        for artifact in self._handoffs.values():
            status = artifact.status
            handoff_status_counts[status] = handoff_status_counts.get(status, 0) + 1

        return {
            "active_workflows": len(self._active_workflows),
            "registered_roles": len(self._role_executors),
            "total_handoffs": len(self._handoffs),
            "handoffs_by_status": handoff_status_counts,
        }

    async def cleanup(self) -> None:
        """Cleanup coordinator resources"""
        logger.info("Cleaning up HandoffCoordinator")

        try:
            async with asyncio.timeout(2.0):
                # Clear active workflows
                self._active_workflows.clear()
                # Clear handoffs
                self._handoffs.clear()
                # Clear role executors
                self._role_executors.clear()
        except asyncio.TimeoutError:
            logger.warning("HandoffCoordinator cleanup timed out")
            pass
        finally:
            self._active_workflows.clear()
            self._handoffs.clear()
            self._role_executors.clear()

        logger.info("HandoffCoordinator cleanup complete")

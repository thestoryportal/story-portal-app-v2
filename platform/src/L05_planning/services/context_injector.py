"""
L05 Planning Layer - Context Injector Service.

Prepares execution context for tasks by:
- Resolving input references from prior task outputs
- Binding secrets (via vault references)
- Injecting domain context
- Enforcing access controls (RBAC)
"""

import logging
from typing import Optional, Dict, Any
from uuid import uuid4

from ..models import (
    Task,
    ExecutionPlan,
    ExecutionContext,
    ContextScope,
    PlanningError,
    ErrorCode,
)

logger = logging.getLogger(__name__)


class ContextInjector:
    """
    Injects execution context for tasks.

    Responsibilities:
    - Resolve input bindings from prior tasks
    - Fetch and mask secrets
    - Build execution scope
    - Validate access permissions
    """

    def __init__(
        self,
        vault_client=None,  # L00 Vault client for secret resolution
        enable_secrets: bool = True,
    ):
        """
        Initialize Context Injector.

        Args:
            vault_client: Vault client for secret resolution
            enable_secrets: Enable secret resolution
        """
        self.vault_client = vault_client
        self.enable_secrets = enable_secrets

        # Metrics
        self.contexts_created = 0
        self.secrets_resolved = 0
        self.input_bindings_resolved = 0
        self.access_denied_count = 0

        logger.info("ContextInjector initialized")

    async def inject_context(
        self,
        task: Task,
        plan: ExecutionPlan,
        parent_outputs: Optional[Dict[str, Dict[str, Any]]] = None,
        agent_did: Optional[str] = None,
    ) -> ExecutionContext:
        """
        Inject execution context for task.

        Args:
            task: Task to create context for
            plan: Parent execution plan
            parent_outputs: Outputs from completed dependency tasks
            agent_did: Agent DID (defaults to plan's agent if not provided)

        Returns:
            ExecutionContext for task execution

        Raises:
            PlanningError: On context injection failure
        """
        self.contexts_created += 1

        try:
            # Create base context
            context = ExecutionContext(
                task_id=task.task_id,
                plan_id=plan.plan_id,
                agent_did=agent_did or "did:agent:default",
                scope=ContextScope.TASK,
                timeout_seconds=task.timeout_seconds,
            )

            # Step 1: Resolve input bindings
            context.inputs = await self._resolve_input_bindings(
                task,
                parent_outputs or {},
            )

            # Step 2: Resolve secrets
            if self.enable_secrets:
                await self._resolve_secrets(task, context)

            # Step 3: Build execution scope and permissions
            self._build_scope(task, context)

            # Step 4: Validate access
            is_valid, error_msg = await self._validate_access(task, context)
            if not is_valid:
                self.access_denied_count += 1
                raise PlanningError.from_code(
                    ErrorCode.E5404,
                    details={"task_id": task.task_id, "reason": error_msg},
                )

            logger.debug(f"Created context for task {task.name}")
            return context

        except PlanningError:
            raise
        except Exception as e:
            logger.error(f"Context injection failed for task {task.task_id}: {e}")
            raise PlanningError.from_code(
                ErrorCode.E5400,
                details={"task_id": task.task_id, "error": str(e)},
            )

    async def _resolve_input_bindings(
        self,
        task: Task,
        parent_outputs: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Resolve input bindings from task dependencies.

        Args:
            task: Task to resolve inputs for
            parent_outputs: Outputs from completed tasks (task_id -> outputs)

        Returns:
            Dictionary of resolved input values

        Raises:
            PlanningError: If required input cannot be resolved
        """
        resolved_inputs = dict(task.inputs)  # Start with static inputs

        # Process dependencies
        for dep in task.dependencies:
            if dep.dependency_type == "data":
                # Data dependency: bind output from parent task
                if dep.task_id not in parent_outputs:
                    logger.warning(
                        f"Dependency {dep.task_id} outputs not available for task {task.task_id}"
                    )
                    continue

                dep_outputs = parent_outputs[dep.task_id]

                if dep.output_key:
                    # Bind specific output key
                    if dep.output_key in dep_outputs:
                        resolved_inputs[dep.output_key] = dep_outputs[dep.output_key]
                        self.input_bindings_resolved += 1
                    else:
                        # Missing required output
                        raise PlanningError.from_code(
                            ErrorCode.E5402,
                            details={
                                "task_id": task.task_id,
                                "dependency_id": dep.task_id,
                                "missing_key": dep.output_key,
                            },
                            recovery_suggestion="Ensure dependency produces required output",
                        )
                else:
                    # Bind all outputs
                    resolved_inputs.update(dep_outputs)
                    self.input_bindings_resolved += len(dep_outputs)

        # Check for input references in format "{{task_id.output_key}}"
        for key, value in list(resolved_inputs.items()):
            if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                # Parse reference
                reference = value[2:-2].strip()
                if "." in reference:
                    ref_task_id, ref_output_key = reference.split(".", 1)
                    if ref_task_id in parent_outputs:
                        ref_outputs = parent_outputs[ref_task_id]
                        if ref_output_key in ref_outputs:
                            resolved_inputs[key] = ref_outputs[ref_output_key]
                            self.input_bindings_resolved += 1

        return resolved_inputs

    async def _resolve_secrets(
        self,
        task: Task,
        context: ExecutionContext,
    ) -> None:
        """
        Resolve secret references and add to context.

        Args:
            task: Task to resolve secrets for
            context: Execution context to populate
        """
        # Look for secret references in task metadata
        secret_refs = task.metadata.get("secrets", {})

        for secret_name, secret_ref in secret_refs.items():
            if self.vault_client:
                try:
                    # Fetch secret from vault
                    secret_value = await self._fetch_secret(secret_ref)
                    # Add masked reference to context
                    context.add_secret(secret_name, f"vault://{secret_ref}")
                    self.secrets_resolved += 1
                except Exception as e:
                    logger.error(f"Failed to resolve secret {secret_name}: {e}")
                    raise PlanningError.from_code(
                        ErrorCode.E5401,
                        details={"secret_name": secret_name, "error": str(e)},
                    )
            else:
                # No vault client, add placeholder
                context.add_secret(secret_name, f"vault://{secret_ref}")

    async def _fetch_secret(self, secret_ref: str) -> str:
        """
        Fetch secret from vault.

        Args:
            secret_ref: Vault secret reference

        Returns:
            Secret value (encrypted/masked)
        """
        # TODO: Integrate with L00 Vault
        # For now, return placeholder
        logger.debug(f"Fetching secret: {secret_ref} (mock)")
        return f"secret_value_{secret_ref}"

    def _build_scope(
        self,
        task: Task,
        context: ExecutionContext,
    ) -> None:
        """
        Build execution scope and permissions.

        Args:
            task: Task to build scope for
            context: Execution context to populate
        """
        # Determine scope based on task type
        if task.task_type == "llm_call":
            context.scope = ContextScope.TASK
            context.permissions = ["llm.inference", "read"]
        elif task.task_type == "tool_call":
            context.scope = ContextScope.TASK
            context.permissions = ["tool.execute", "read", "write"]
        else:
            context.scope = ContextScope.TASK
            context.permissions = ["read"]

        # Add any task-specific permissions
        task_permissions = task.metadata.get("permissions", [])
        context.permissions.extend(task_permissions)

    async def _validate_access(
        self,
        task: Task,
        context: ExecutionContext,
    ) -> tuple[bool, Optional[str]]:
        """
        Validate access permissions for task execution.

        Args:
            task: Task to validate
            context: Execution context

        Returns:
            (is_valid, error_message)
        """
        # TODO: Implement RBAC validation
        # For now, allow all access
        return True, None

    def get_stats(self) -> Dict[str, Any]:
        """Get context injector statistics."""
        return {
            "contexts_created": self.contexts_created,
            "secrets_resolved": self.secrets_resolved,
            "input_bindings_resolved": self.input_bindings_resolved,
            "access_denied_count": self.access_denied_count,
        }

"""
Runtime Context Bridge - Phase 16 Integration

Connects agent runtime to context-orchestrator for state persistence,
checkpoint management, and crash recovery.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import asyncio


class RuntimeContextBridge:
    """
    Bridge between agent runtime and context-orchestrator.

    Provides:
    - Agent state persistence across sessions
    - Checkpoint creation for crash recovery
    - State restoration after failures
    - Context versioning and history
    """

    def __init__(self, context_service, checkpoint_interval: int = 300):
        """
        Initialize runtime context bridge.

        Args:
            context_service: ContextService instance from L01_data
            checkpoint_interval: Automatic checkpoint interval in seconds (default: 5 minutes)
        """
        self.context_service = context_service
        self.checkpoint_interval = checkpoint_interval
        self._checkpoint_task = None
        self._active_contexts = {}

    async def load_agent_context(
        self,
        agent_id: str,
        version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Load agent context from persistent storage.

        Args:
            agent_id: Unique agent identifier
            version: Optional specific version to load (defaults to latest)

        Returns:
            Agent context dictionary or None if not found
        """
        context_id = f"agent:{agent_id}"

        # Load context from data layer
        context = await self.context_service.get_context(context_id, version)

        if context:
            # Track active context for checkpoint management
            self._active_contexts[agent_id] = {
                'context_id': context_id,
                'last_checkpoint': datetime.utcnow(),
                'version': context['version']
            }

            return {
                'agent_id': agent_id,
                'state': context['data'].get('state', {}),
                'memory': context['data'].get('memory', []),
                'metadata': context['metadata'],
                'version': context['version'],
                'loaded_at': datetime.utcnow().isoformat()
            }

        return None

    async def save_agent_state(
        self,
        agent_id: str,
        state: Dict[str, Any],
        memory: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Save agent state to persistent storage.

        Args:
            agent_id: Unique agent identifier
            state: Current agent state dictionary
            memory: Optional agent memory/conversation history
            metadata: Optional metadata (tags, session info, etc.)

        Returns:
            Saved context information
        """
        context_id = f"agent:{agent_id}"

        data = {
            'state': state,
            'memory': memory or [],
            'saved_at': datetime.utcnow().isoformat()
        }

        # Merge with existing metadata if tracking
        if agent_id in self._active_contexts:
            existing_metadata = metadata or {}
            existing_metadata['checkpoint_count'] = existing_metadata.get('checkpoint_count', 0) + 1
            metadata = existing_metadata

        saved = await self.context_service.save_context(
            context_id=context_id,
            data=data,
            metadata=metadata
        )

        # Update tracking
        self._active_contexts[agent_id] = {
            'context_id': context_id,
            'last_checkpoint': datetime.utcnow(),
            'version': saved['version']
        }

        return {
            'agent_id': agent_id,
            'context_id': context_id,
            'version': saved['version'],
            'saved_at': saved['updated_at']
        }

    async def checkpoint(
        self,
        agent_id: str,
        state: Dict[str, Any],
        memory: Optional[List[Dict[str, Any]]] = None,
        checkpoint_type: str = 'auto'
    ) -> Dict[str, Any]:
        """
        Create a checkpoint of agent state for recovery purposes.

        Checkpoints are versioned snapshots that enable rollback and recovery.

        Args:
            agent_id: Unique agent identifier
            state: Current agent state to checkpoint
            memory: Optional agent memory to checkpoint
            checkpoint_type: Type of checkpoint ('auto', 'manual', 'pre_action')

        Returns:
            Checkpoint information
        """
        metadata = {
            'checkpoint_type': checkpoint_type,
            'checkpoint_at': datetime.utcnow().isoformat()
        }

        result = await self.save_agent_state(
            agent_id=agent_id,
            state=state,
            memory=memory,
            metadata=metadata
        )

        return {
            **result,
            'checkpoint_type': checkpoint_type,
            'recoverable': True
        }

    async def recover_from_checkpoint(
        self,
        agent_id: str,
        version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Recover agent state from a checkpoint.

        Args:
            agent_id: Agent to recover
            version: Optional specific checkpoint version (defaults to latest)

        Returns:
            Recovered agent context or None if no checkpoint found
        """
        context = await self.load_agent_context(agent_id, version)

        if context:
            return {
                'agent_id': agent_id,
                'state': context['state'],
                'memory': context['memory'],
                'recovered_from_version': context['version'],
                'recovered_at': datetime.utcnow().isoformat()
            }

        return None

    async def start_auto_checkpoint(
        self,
        agent_id: str,
        get_state_callback
    ):
        """
        Start automatic checkpoint task for an agent.

        Args:
            agent_id: Agent to auto-checkpoint
            get_state_callback: Async callback function that returns current agent state

        The checkpoint task runs in the background and creates periodic checkpoints.
        """
        async def checkpoint_loop():
            while agent_id in self._active_contexts:
                await asyncio.sleep(self.checkpoint_interval)

                try:
                    # Get current state from callback
                    current_state = await get_state_callback()

                    # Create checkpoint
                    await self.checkpoint(
                        agent_id=agent_id,
                        state=current_state.get('state', {}),
                        memory=current_state.get('memory', []),
                        checkpoint_type='auto'
                    )
                except Exception as e:
                    # Log error but don't stop checkpoint loop
                    print(f"Auto-checkpoint error for agent {agent_id}: {e}")

        # Start background task
        self._checkpoint_task = asyncio.create_task(checkpoint_loop())

    async def stop_auto_checkpoint(self, agent_id: str):
        """
        Stop automatic checkpoint task for an agent.

        Args:
            agent_id: Agent to stop auto-checkpoint for
        """
        if agent_id in self._active_contexts:
            del self._active_contexts[agent_id]

        if self._checkpoint_task:
            self._checkpoint_task.cancel()
            try:
                await self._checkpoint_task
            except asyncio.CancelledError:
                pass

    async def list_checkpoints(
        self,
        agent_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        List available checkpoints for an agent.

        Args:
            agent_id: Agent to list checkpoints for
            limit: Maximum number of checkpoints to return

        Returns:
            List of checkpoint metadata
        """
        context_id = f"agent:{agent_id}"

        # Query database for checkpoint versions
        query = """
            SELECT version, metadata, created_at, updated_at
            FROM contexts
            WHERE context_id = $1
            ORDER BY version DESC
            LIMIT $2
        """

        results = await self.context_service.db.fetch(query, context_id, limit)

        return [
            {
                'agent_id': agent_id,
                'version': row['version'],
                'checkpoint_type': json.loads(row['metadata']).get('checkpoint_type', 'unknown'),
                'checkpoint_at': json.loads(row['metadata']).get('checkpoint_at'),
                'created_at': row['created_at'].isoformat()
            }
            for row in results
        ]

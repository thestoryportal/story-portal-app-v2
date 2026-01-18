"""
MCP Tool Bridge Service

Integrates with MCP servers for document context (Phase 15) and state checkpoints (Phase 16).
Based on ADR-001 (stdio transport) and Phase 15/16 specifications.

Features:
- Document Bridge for Phase 15 integration (via L02 DocumentBridge)
- State Bridge for Phase 16 checkpointing (via L02 SessionBridge)
- MCP stdio transport (JSON-RPC 2.0)
- Connection pooling and error handling
"""

import asyncio
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID

from ..models import (
    DocumentContext,
    CheckpointConfig,
    Checkpoint,
    ErrorCode,
    ToolExecutionError,
)

# TODO: Replace direct imports with HTTP client for L02
# Cross-layer imports between containers don't work - need HTTP-based communication
# from ...L02_runtime.services.document_bridge import DocumentBridge
# from ...L02_runtime.services.session_bridge import SessionBridge
DocumentBridge = None  # Placeholder until HTTP client is implemented
SessionBridge = None   # Placeholder until HTTP client is implemented

logger = logging.getLogger(__name__)


class MCPToolBridge:
    """
    MCP bridge for document and state management.

    Connects to document-consolidator and context-orchestrator MCP servers.
    """

    def __init__(
        self,
        document_server_enabled: bool = True,
        context_server_enabled: bool = True,
        document_bridge_config: Optional[Dict[str, Any]] = None,
        session_bridge_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize MCP Tool Bridge.

        Args:
            document_server_enabled: Enable document-consolidator integration
            context_server_enabled: Enable context-orchestrator integration
            document_bridge_config: Configuration for DocumentBridge
            session_bridge_config: Configuration for SessionBridge
        """
        self.document_server_enabled = document_server_enabled
        self.context_server_enabled = context_server_enabled

        # Initialize L02 bridges
        self.document_bridge = None
        self.session_bridge = None

        if self.document_server_enabled and DocumentBridge is not None:
            self.document_bridge = DocumentBridge(config=document_bridge_config)
            logger.info("DocumentBridge instantiated")
        elif self.document_server_enabled:
            logger.warning("DocumentBridge requested but not available (requires HTTP client for L02)")

        if self.context_server_enabled and SessionBridge is not None:
            self.session_bridge = SessionBridge(config=session_bridge_config)
            logger.info("SessionBridge instantiated")
        elif self.context_server_enabled:
            logger.warning("SessionBridge requested but not available (requires HTTP client for L02)")

    async def initialize(self):
        """Initialize MCP server connections"""
        logger.info("Initializing MCP Tool Bridge")

        # Initialize document bridge
        if self.document_bridge:
            try:
                await self.document_bridge.initialize()
                logger.info("DocumentBridge initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize DocumentBridge: {e}")

        # Initialize session bridge
        if self.session_bridge:
            try:
                await self.session_bridge.initialize()
                logger.info("SessionBridge initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize SessionBridge: {e}")

        logger.info("MCP Tool Bridge initialization complete")

    async def close(self):
        """Close MCP server connections"""
        logger.info("Closing MCP Tool Bridge")

        # Cleanup document bridge
        if self.document_bridge:
            try:
                await self.document_bridge.cleanup()
                logger.info("DocumentBridge cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up DocumentBridge: {e}")

        # Cleanup session bridge
        if self.session_bridge:
            try:
                await self.session_bridge.cleanup()
                logger.info("SessionBridge cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up SessionBridge: {e}")

        logger.info("MCP Tool Bridge closed")

    # ==================== Document Bridge (Phase 15) ====================

    async def get_document(
        self,
        document_id: str,
        version_pinning: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve document content from document-consolidator.

        Phase 15 integration: get_document (via L02 DocumentBridge)

        Args:
            document_id: Document identifier
            version_pinning: Pin document version

        Returns:
            Document content and metadata
        """
        if not self.document_bridge:
            logger.warning("Document bridge not initialized")
            return None

        try:
            logger.info(f"Retrieving document {document_id} (pinning: {version_pinning})")

            # Call L02 DocumentBridge
            document = await self.document_bridge.get_document(document_id)

            if document:
                return {
                    "document_id": document.get("id", document_id),
                    "content": document.get("content", ""),
                    "version": document.get("version", "1.0.0"),
                    "metadata": document.get("metadata", {}),
                    "title": document.get("title", ""),
                }

            return None

        except Exception as e:
            logger.error(f"Failed to retrieve document: {e}")
            raise ToolExecutionError(
                ErrorCode.E3501,
                message="Document retrieval failed",
                details={"error": str(e), "document_id": document_id}
            )

    async def search_documents(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Semantic search for documents.

        Phase 15 integration: query_documents (via L02 DocumentBridge)

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching documents
        """
        if not self.document_bridge:
            logger.warning("Document bridge not initialized")
            return []

        try:
            logger.info(f"Searching documents: {query}")

            # Call L02 DocumentBridge query_documents
            documents = await self.document_bridge.query_documents(
                query=query,
                filters={},
                use_cache=True
            )

            # Limit results
            limited_docs = documents[:limit]

            # Transform to expected format
            results = []
            for doc in limited_docs:
                results.append({
                    "document_id": doc.get("id", ""),
                    "title": doc.get("title", ""),
                    "content": doc.get("content", ""),
                    "confidence": doc.get("confidence", 0.0),
                    "metadata": doc.get("metadata", {}),
                })

            return results

        except Exception as e:
            logger.error(f"Document search failed: {e}")
            return []

    async def get_documents_for_tool(
        self,
        document_context: DocumentContext
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all documents needed for tool execution.

        Args:
            document_context: Document context from request

        Returns:
            List of document contents
        """
        documents = []

        # Retrieve explicitly referenced documents
        for doc_ref in document_context.document_refs:
            doc = await self.get_document(
                document_id=doc_ref,
                version_pinning=document_context.version_pinning
            )
            if doc:
                documents.append(doc)

        # Search for additional documents if query provided
        if document_context.query:
            search_results = await self.search_documents(
                query=document_context.query,
                limit=5
            )
            documents.extend(search_results)

        return documents

    # ==================== State Bridge (Phase 16) ====================

    async def create_checkpoint(
        self,
        checkpoint: Checkpoint
    ) -> str:
        """
        Create checkpoint via context-orchestrator.

        Phase 16 integration: create_checkpoint (via L02 SessionBridge)

        Args:
            checkpoint: Checkpoint to create

        Returns:
            Checkpoint ID
        """
        if not self.session_bridge:
            logger.warning("Session bridge not initialized")
            return str(checkpoint.checkpoint_id)

        try:
            logger.info(f"Creating checkpoint {checkpoint.checkpoint_id}")

            # Convert L03 Checkpoint to context snapshot for SessionBridge
            # SessionBridge uses save_snapshot with a task_id (session_id in L02 context)
            task_id = str(checkpoint.invocation_id)

            context_data = {
                "status": "in_progress",
                "currentPhase": f"checkpoint_{checkpoint.checkpoint_type.value}",
                "immediateContext": {
                    "workingOn": f"Checkpoint {checkpoint.checkpoint_type.value}",
                    "lastAction": "Checkpoint created",
                    "nextStep": None,
                    "blockers": [],
                },
                "state": checkpoint.state,
                "progress": checkpoint.progress_percent,
            }

            await self.session_bridge.save_snapshot(
                session_id=task_id,
                context=context_data,
                change_summary=f"Checkpoint {checkpoint.checkpoint_type.value} at {checkpoint.progress_percent}%"
            )

            return str(checkpoint.checkpoint_id)

        except Exception as e:
            logger.error(f"Failed to create checkpoint: {e}")
            raise ToolExecutionError(
                ErrorCode.E3601,
                message="Checkpoint creation failed",
                details={"error": str(e)}
            )

    async def restore_checkpoint(
        self,
        checkpoint_id: str
    ) -> Optional[Checkpoint]:
        """
        Restore checkpoint from context-orchestrator.

        Phase 16 integration: get_unified_context (via L02 SessionBridge)

        Args:
            checkpoint_id: Checkpoint identifier (task_id/session_id)

        Returns:
            Restored checkpoint
        """
        if not self.session_bridge:
            logger.warning("Session bridge not initialized")
            return None

        try:
            logger.info(f"Restoring checkpoint {checkpoint_id}")

            # Get unified context from SessionBridge
            context = await self.session_bridge.get_unified_context(
                session_id=checkpoint_id
            )

            if not context:
                return None

            # Convert context back to L03 Checkpoint
            # Note: This is a simplified conversion since SessionBridge stores
            # context differently than L03 Checkpoints
            from ..models import CheckpointType

            checkpoint = Checkpoint(
                checkpoint_id=UUID(checkpoint_id) if len(checkpoint_id) == 36 else UUID(int=0),
                invocation_id=UUID(checkpoint_id) if len(checkpoint_id) == 36 else UUID(int=0),
                checkpoint_type=CheckpointType.MACRO,  # Default to MACRO
                state=context.get("state", {}),
                progress_percent=context.get("progress", 0),
            )

            return checkpoint

        except Exception as e:
            logger.error(f"Failed to restore checkpoint: {e}")
            raise ToolExecutionError(
                ErrorCode.E3602,
                message="Checkpoint restoration failed",
                details={"error": str(e), "checkpoint_id": checkpoint_id}
            )

    async def save_context_snapshot(
        self,
        task_id: str,
        state: Dict[str, Any],
        sync_to_file: bool = True
    ):
        """
        Save context snapshot via context-orchestrator.

        Phase 16 integration: save_snapshot (via L02 SessionBridge)

        Args:
            task_id: Task identifier
            state: Current state to save
            sync_to_file: Sync to file cache
        """
        if not self.session_bridge:
            logger.warning("Session bridge not initialized")
            return

        try:
            logger.info(f"Saving context snapshot for task {task_id}")

            # Call SessionBridge save_snapshot
            await self.session_bridge.save_snapshot(
                session_id=task_id,
                context=state,
                change_summary="Tool execution context snapshot"
            )

        except Exception as e:
            logger.error(f"Failed to save context snapshot: {e}")

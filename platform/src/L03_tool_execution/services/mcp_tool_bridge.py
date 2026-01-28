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

from .l02_http_client import L02HttpClient

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
        l02_base_url: str = "http://localhost:8002",
        l02_timeout: float = 30.0,
    ):
        """
        Initialize MCP Tool Bridge.

        Args:
            document_server_enabled: Enable document-consolidator integration
            context_server_enabled: Enable context-orchestrator integration
            l02_base_url: L02 Runtime service URL
            l02_timeout: L02 request timeout in seconds
        """
        self.document_server_enabled = document_server_enabled
        self.context_server_enabled = context_server_enabled

        # Initialize L02 HTTP client for both document and session bridge operations
        self.l02_client: Optional[L02HttpClient] = None
        if self.document_server_enabled or self.context_server_enabled:
            self.l02_client = L02HttpClient(
                base_url=l02_base_url,
                timeout=l02_timeout,
            )
            logger.info(f"L02HttpClient configured for {l02_base_url}")

    async def initialize(self):
        """Initialize MCP server connections"""
        logger.info("Initializing MCP Tool Bridge")

        # Initialize L02 HTTP client
        if self.l02_client:
            try:
                available = await self.l02_client.initialize()
                if available:
                    logger.info("L02 HTTP Client connected successfully")
                else:
                    logger.warning("L02 HTTP Client initialized but service unavailable")
            except Exception as e:
                logger.warning(f"Failed to initialize L02 HTTP Client: {e}")

        logger.info("MCP Tool Bridge initialization complete")

    async def close(self):
        """Close MCP server connections"""
        logger.info("Closing MCP Tool Bridge")

        # Cleanup L02 HTTP client
        if self.l02_client:
            try:
                await self.l02_client.close()
                logger.info("L02 HTTP Client closed")
            except Exception as e:
                logger.error(f"Error closing L02 HTTP Client: {e}")

        logger.info("MCP Tool Bridge closed")

    # ==================== Document Bridge (Phase 15) ====================

    async def get_document(
        self,
        document_id: str,
        version_pinning: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve document content from document-consolidator.

        Phase 15 integration: get_document (via L02 HTTP Client)

        Args:
            document_id: Document identifier
            version_pinning: Pin document version

        Returns:
            Document content and metadata
        """
        if not self.l02_client or not self.document_server_enabled:
            logger.warning("Document bridge not initialized or disabled")
            return None

        try:
            logger.info(f"Retrieving document {document_id} (pinning: {version_pinning})")

            # Call L02 HTTP Client
            document = await self.l02_client.get_document(document_id, version_pinning)

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

        Phase 15 integration: query_documents (via L02 HTTP Client)

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching documents
        """
        if not self.l02_client or not self.document_server_enabled:
            logger.warning("Document bridge not initialized or disabled")
            return []

        try:
            logger.info(f"Searching documents: {query}")

            # Call L02 HTTP Client
            documents = await self.l02_client.search_documents(
                query=query,
                limit=limit,
            )

            # Transform to expected format
            results = []
            for doc in documents:
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

        Phase 16 integration: create_checkpoint (via L02 HTTP Client)

        Args:
            checkpoint: Checkpoint to create

        Returns:
            Checkpoint ID
        """
        if not self.l02_client or not self.context_server_enabled:
            logger.warning("Session bridge not initialized or disabled")
            return str(checkpoint.checkpoint_id)

        try:
            logger.info(f"Creating checkpoint {checkpoint.checkpoint_id}")

            # Convert L03 Checkpoint to context snapshot
            task_id = str(checkpoint.invocation_id)

            checkpoint_data = {
                "checkpoint_id": str(checkpoint.checkpoint_id),
                "checkpoint_type": checkpoint.checkpoint_type.value,
                "state": checkpoint.state,
                "progress_percent": checkpoint.progress_percent,
                "created_at": checkpoint.created_at.isoformat() if checkpoint.created_at else None,
            }

            result = await self.l02_client.create_checkpoint(task_id, checkpoint_data)

            if result:
                return result

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

        Phase 16 integration: restore_checkpoint (via L02 HTTP Client)

        Args:
            checkpoint_id: Checkpoint identifier

        Returns:
            Restored checkpoint
        """
        if not self.l02_client or not self.context_server_enabled:
            logger.warning("Session bridge not initialized or disabled")
            return None

        try:
            logger.info(f"Restoring checkpoint {checkpoint_id}")

            # Get checkpoint from L02 HTTP Client
            data = await self.l02_client.restore_checkpoint(checkpoint_id)

            if not data:
                return None

            # Convert to L03 Checkpoint
            from ..models import CheckpointType

            checkpoint_type_str = data.get("checkpoint_type", "macro")
            checkpoint_type = CheckpointType(checkpoint_type_str) if checkpoint_type_str in [ct.value for ct in CheckpointType] else CheckpointType.MACRO

            checkpoint = Checkpoint(
                checkpoint_id=UUID(data.get("checkpoint_id", checkpoint_id)) if len(data.get("checkpoint_id", checkpoint_id)) == 36 else UUID(int=0),
                invocation_id=UUID(data.get("invocation_id", checkpoint_id)) if len(data.get("invocation_id", checkpoint_id)) == 36 else UUID(int=0),
                checkpoint_type=checkpoint_type,
                state=data.get("state", {}),
                progress_percent=data.get("progress_percent", 0),
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

        Phase 16 integration: save_context_snapshot (via L02 HTTP Client)

        Args:
            task_id: Task identifier
            state: Current state to save
            sync_to_file: Sync to file cache
        """
        if not self.l02_client or not self.context_server_enabled:
            logger.warning("Session bridge not initialized or disabled")
            return

        try:
            logger.info(f"Saving context snapshot for task {task_id}")

            # Call L02 HTTP Client
            await self.l02_client.save_context_snapshot(
                task_id=task_id,
                context=state,
                change_summary="Tool execution context snapshot"
            )

        except Exception as e:
            logger.error(f"Failed to save context snapshot: {e}")

"""
Enhanced Context Service - Phase 16 Integration

Integrates Phase 15 document retrieval with Phase 16 context management.
Provides unified interface for context persistence with document awareness.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import json


class ContextService:
    """
    Enhanced context service that bridges context-orchestrator MCP service
    with Data Layer v4.0 for persistent context management.

    This service provides:
    - Context storage and retrieval with versioning
    - Document-aware context loading
    - Cross-session context persistence
    - Crash recovery support via checkpoints
    """

    def __init__(self, db_connection, redis_client, document_service):
        """
        Initialize context service with required dependencies.

        Args:
            db_connection: PostgreSQL database connection
            redis_client: Redis client for caching
            document_service: DocumentService instance for document retrieval
        """
        self.db = db_connection
        self.redis = redis_client
        self.document_service = document_service

    async def get_context(
        self,
        context_id: str,
        version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve context by ID, optionally at a specific version.

        First checks Redis cache, falls back to PostgreSQL if not cached.

        Args:
            context_id: Unique context identifier
            version: Optional version number (defaults to latest)

        Returns:
            Context data dictionary or None if not found
        """
        cache_key = f"context:{context_id}:{version or 'latest'}"

        # Try cache first
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)

        # Fall back to database
        query = """
            SELECT context_id, version, data, metadata, created_at, updated_at
            FROM contexts
            WHERE context_id = $1
        """
        params = [context_id]

        if version is not None:
            query += " AND version = $2"
            params.append(version)
        else:
            query += " ORDER BY version DESC LIMIT 1"

        result = await self.db.fetchrow(query, *params)

        if result:
            context_data = {
                'context_id': result['context_id'],
                'version': result['version'],
                'data': result['data'],
                'metadata': result['metadata'],
                'created_at': result['created_at'].isoformat(),
                'updated_at': result['updated_at'].isoformat(),
            }

            # Cache for future requests
            await self.redis.setex(
                cache_key,
                3600,  # 1 hour TTL
                json.dumps(context_data)
            )

            return context_data

        return None

    async def save_context(
        self,
        context_id: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Save or update context, creating a new version.

        Args:
            context_id: Unique context identifier
            data: Context data to save
            metadata: Optional metadata (tags, source, etc.)

        Returns:
            Saved context with version information
        """
        # Get current max version
        current = await self.db.fetchrow(
            "SELECT MAX(version) as max_version FROM contexts WHERE context_id = $1",
            context_id
        )
        next_version = (current['max_version'] or 0) + 1

        # Insert new version
        now = datetime.utcnow()
        result = await self.db.fetchrow(
            """
            INSERT INTO contexts (context_id, version, data, metadata, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING context_id, version, data, metadata, created_at, updated_at
            """,
            context_id,
            next_version,
            json.dumps(data),
            json.dumps(metadata or {}),
            now,
            now
        )

        context_data = {
            'context_id': result['context_id'],
            'version': result['version'],
            'data': json.loads(result['data']),
            'metadata': json.loads(result['metadata']),
            'created_at': result['created_at'].isoformat(),
            'updated_at': result['updated_at'].isoformat(),
        }

        # Update cache
        cache_key = f"context:{context_id}:latest"
        await self.redis.setex(cache_key, 3600, json.dumps(context_data))

        # Invalidate version-specific cache
        versioned_key = f"context:{context_id}:{next_version}"
        await self.redis.delete(versioned_key)

        return context_data

    async def get_with_documents(
        self,
        context_id: str,
        query: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Retrieve context with related documents.

        Combines context retrieval with document search to provide
        document-aware context loading for agents.

        Args:
            context_id: Unique context identifier
            query: Optional semantic search query for documents
            limit: Maximum number of documents to retrieve

        Returns:
            Dictionary containing context and related documents
        """
        # Get base context
        context = await self.get_context(context_id)
        if not context:
            return None

        # Get related documents
        documents = []
        if query:
            # Semantic search based on query
            doc_results = await self.document_service.query(
                query=query,
                limit=limit
            )
            documents = doc_results.get('documents', [])
        else:
            # Get documents referenced in context metadata
            doc_refs = context.get('metadata', {}).get('document_refs', [])
            if doc_refs:
                for doc_id in doc_refs[:limit]:
                    doc = await self.document_service.get_by_id(doc_id)
                    if doc:
                        documents.append(doc)

        return {
            'context': context,
            'documents': documents,
            'document_count': len(documents)
        }

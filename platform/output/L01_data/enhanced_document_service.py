"""
Enhanced Document Service - Phase 15 Integration

Bridges MCP document-consolidator service with Data Layer v4.0.
Handles document ingestion, storage, semantic search, and overlap detection.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import hashlib


class DocumentService:
    """
    Enhanced document service that bridges document-consolidator MCP service
    with Data Layer v4.0 for document management and semantic search.

    This service provides:
    - Document ingestion with deduplication
    - Semantic search via pgvector
    - Overlap detection between documents
    - Document metadata management
    """

    def __init__(self, db_connection, embedding_client):
        """
        Initialize document service with required dependencies.

        Args:
            db_connection: PostgreSQL database connection
            embedding_client: Ollama client for embedding generation
        """
        self.db = db_connection
        self.embedding_client = embedding_client

    def _compute_hash(self, content: str) -> str:
        """Compute SHA-256 hash of document content for deduplication."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    async def ingest(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ingest a document with automatic deduplication and embedding generation.

        Args:
            content: Document content text
            metadata: Optional metadata (title, author, tags, etc.)
            source: Optional source identifier (file path, URL, etc.)

        Returns:
            Ingested document with ID and embedding info
        """
        content_hash = self._compute_hash(content)

        # Check for existing document with same hash
        existing = await self.db.fetchrow(
            "SELECT document_id FROM documents WHERE content_hash = $1",
            content_hash
        )

        if existing:
            return {
                'document_id': existing['document_id'],
                'status': 'duplicate',
                'message': 'Document already exists'
            }

        # Generate embedding
        embedding_response = await self.embedding_client.embed(
            model='nomic-embed-text',
            input=content
        )
        embedding = embedding_response['embedding']

        # Insert document
        now = datetime.utcnow()
        result = await self.db.fetchrow(
            """
            INSERT INTO documents (
                content, content_hash, embedding, metadata, source,
                created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING document_id, content, content_hash, metadata, source,
                      created_at, updated_at
            """,
            content,
            content_hash,
            embedding,
            json.dumps(metadata or {}),
            source,
            now,
            now
        )

        return {
            'document_id': result['document_id'],
            'content_hash': result['content_hash'],
            'metadata': json.loads(result['metadata']),
            'source': result['source'],
            'created_at': result['created_at'].isoformat(),
            'status': 'ingested'
        }

    async def query(
        self,
        query: str,
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        Perform semantic search over documents using vector similarity.

        Args:
            query: Search query text
            limit: Maximum number of results to return
            similarity_threshold: Minimum cosine similarity (0-1)

        Returns:
            Dictionary containing matching documents and similarity scores
        """
        # Generate query embedding
        embedding_response = await self.embedding_client.embed(
            model='nomic-embed-text',
            input=query
        )
        query_embedding = embedding_response['embedding']

        # Perform similarity search using pgvector
        results = await self.db.fetch(
            """
            SELECT
                document_id,
                content,
                metadata,
                source,
                created_at,
                1 - (embedding <=> $1::vector) AS similarity
            FROM documents
            WHERE 1 - (embedding <=> $1::vector) >= $2
            ORDER BY embedding <=> $1::vector
            LIMIT $3
            """,
            query_embedding,
            similarity_threshold,
            limit
        )

        documents = [
            {
                'document_id': row['document_id'],
                'content': row['content'],
                'metadata': json.loads(row['metadata']),
                'source': row['source'],
                'similarity': float(row['similarity']),
                'created_at': row['created_at'].isoformat()
            }
            for row in results
        ]

        return {
            'query': query,
            'documents': documents,
            'count': len(documents),
            'similarity_threshold': similarity_threshold
        }

    async def find_overlaps(
        self,
        document_id: str,
        similarity_threshold: float = 0.85,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Find documents with significant content overlap.

        Useful for detecting duplicates, related content, or version drift.

        Args:
            document_id: Document ID to find overlaps for
            similarity_threshold: Minimum similarity (higher = more similar)
            limit: Maximum number of overlapping documents to return

        Returns:
            List of overlapping documents with similarity scores
        """
        # Get source document embedding
        doc = await self.db.fetchrow(
            "SELECT embedding FROM documents WHERE document_id = $1",
            document_id
        )

        if not doc:
            return []

        # Find similar documents
        results = await self.db.fetch(
            """
            SELECT
                document_id,
                content,
                metadata,
                source,
                1 - (embedding <=> $1::vector) AS similarity
            FROM documents
            WHERE document_id != $2
              AND 1 - (embedding <=> $1::vector) >= $3
            ORDER BY embedding <=> $1::vector
            LIMIT $4
            """,
            doc['embedding'],
            document_id,
            similarity_threshold,
            limit
        )

        return [
            {
                'document_id': row['document_id'],
                'content': row['content'][:200] + '...',  # Truncate for preview
                'metadata': json.loads(row['metadata']),
                'source': row['source'],
                'similarity': float(row['similarity'])
            }
            for row in results
        ]

    async def get_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document by its ID.

        Args:
            document_id: Document ID to retrieve

        Returns:
            Document dictionary or None if not found
        """
        result = await self.db.fetchrow(
            """
            SELECT document_id, content, metadata, source, created_at, updated_at
            FROM documents
            WHERE document_id = $1
            """,
            document_id
        )

        if result:
            return {
                'document_id': result['document_id'],
                'content': result['content'],
                'metadata': json.loads(result['metadata']),
                'source': result['source'],
                'created_at': result['created_at'].isoformat(),
                'updated_at': result['updated_at'].isoformat()
            }

        return None

"""
Tool Registry Service

Maintains catalog of available tools with semantic search capabilities.
Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md

Features:
- Tool registration and versioning (Gap G-001, G-002)
- Semantic search via pgvector + Ollama embeddings
- Tool deprecation workflow (Gap G-003)
- Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import psycopg
from psycopg.rows import dict_row
try:
    from psycopg_pool import AsyncConnectionPool
except ImportError:
    # Fallback for older psycopg versions
    from psycopg_pool import AsyncConnectionPool
import httpx

from ..models import (
    ToolDefinition,
    ToolVersion,
    ToolManifest,
    ToolCategory,
    DeprecationState,
    SourceType,
    ErrorCode,
    ToolExecutionError,
)

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Tool registry with PostgreSQL + pgvector storage and Ollama embeddings.

    Implements protocol-agnostic tool management with semantic search.
    """

    def __init__(
        self,
        db_connection_string: str,
        ollama_base_url: str = "http://localhost:11434",
        embedding_model: str = "mistral:7b",
        embedding_dimensions: int = 768,
        semantic_search_threshold: float = 0.7,
    ):
        """
        Initialize Tool Registry.

        Args:
            db_connection_string: PostgreSQL connection string
            ollama_base_url: Ollama API endpoint
            embedding_model: Ollama model for embeddings
            embedding_dimensions: Vector dimensions
            semantic_search_threshold: Cosine similarity threshold
        """
        self.db_connection_string = db_connection_string
        self.ollama_base_url = ollama_base_url
        self.embedding_model = embedding_model
        self.embedding_dimensions = embedding_dimensions
        self.semantic_search_threshold = semantic_search_threshold
        self.db_pool: Optional[psycopg.AsyncConnectionPool] = None
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def initialize(self):
        """Initialize database connection pool and ensure schema exists"""
        try:
            self.db_pool = AsyncConnectionPool(
                self.db_connection_string,
                min_size=2,
                max_size=10,
                timeout=30.0,
            )
            await self._ensure_schema()
            logger.info("Tool Registry initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Tool Registry: {e}")
            raise ToolExecutionError(
                ErrorCode.E3008,
                message="Failed to initialize tool registry",
                details={"error": str(e)}
            )

    async def close(self):
        """Close database connection pool and HTTP client"""
        if self.db_pool:
            await self.db_pool.close()
        await self.http_client.aclose()
        logger.info("Tool Registry closed")

    async def _ensure_schema(self):
        """Ensure required database tables exist"""
        async with self.db_pool.connection() as conn:
            # Use explicit transaction
            async with conn.transaction():
                async with conn.cursor() as cur:
                    # Enable pgvector extension
                    await cur.execute("CREATE EXTENSION IF NOT EXISTS vector")

                    # Create tool_definitions table
                    await cur.execute("""
                        CREATE TABLE IF NOT EXISTS tool_definitions (
                            tool_id VARCHAR(255) PRIMARY KEY,
                            tool_name VARCHAR(255) NOT NULL,
                            description TEXT NOT NULL,
                            category VARCHAR(100) NOT NULL,
                            tags TEXT[],
                            latest_version VARCHAR(50) NOT NULL,
                            source_type VARCHAR(50) NOT NULL,
                            source_metadata JSONB,
                            deprecation_state VARCHAR(20) DEFAULT 'active',
                            deprecation_date TIMESTAMP,
                            created_at TIMESTAMP DEFAULT NOW(),
                            updated_at TIMESTAMP DEFAULT NOW(),
                            requires_approval BOOLEAN DEFAULT FALSE,
                            default_timeout_seconds INTEGER DEFAULT 30,
                            default_cpu_millicore_limit INTEGER DEFAULT 500,
                            default_memory_mb_limit INTEGER DEFAULT 1024,
                            required_permissions JSONB,
                            result_schema JSONB,
                            retry_policy JSONB,
                            circuit_breaker_config JSONB,
                            description_embedding VECTOR(768)
                        )
                    """)

                    # Create tool_versions table
                    await cur.execute("""
                        CREATE TABLE IF NOT EXISTS tool_versions (
                            version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            tool_id VARCHAR(255) REFERENCES tool_definitions(tool_id) ON DELETE CASCADE,
                            version VARCHAR(50) NOT NULL,
                            manifest JSONB NOT NULL,
                            compatibility_range VARCHAR(100),
                            release_notes TEXT,
                            deprecated_in_favor_of VARCHAR(50),
                            created_at TIMESTAMP DEFAULT NOW(),
                            removed_at TIMESTAMP,
                            UNIQUE(tool_id, version)
                        )
                    """)

                    # Create indexes
                    await cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_tool_category
                        ON tool_definitions(category)
                    """)

                    await cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_tool_deprecation_state
                        ON tool_definitions(deprecation_state)
                    """)

                    await cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_tool_description_embedding
                        ON tool_definitions USING ivfflat (description_embedding vector_cosine_ops)
                    """)

                    await cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_tool_version_tool_id
                        ON tool_versions(tool_id)
                    """)

                # Transaction commits automatically when exiting context

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate semantic embedding for text using Ollama.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (768 dimensions)

        Raises:
            ToolExecutionError: If embedding generation fails (E3005)
        """
        try:
            response = await self.http_client.post(
                f"{self.ollama_base_url}/api/embeddings",
                json={"model": self.embedding_model, "prompt": text}
            )
            response.raise_for_status()
            data = response.json()
            embedding = data.get("embedding", [])

            if len(embedding) != self.embedding_dimensions:
                raise ValueError(f"Expected {self.embedding_dimensions} dimensions, got {len(embedding)}")

            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise ToolExecutionError(
                ErrorCode.E3005,
                message="Semantic search embedding generation failed",
                details={"error": str(e), "text": text[:100]}
            )

    async def register_tool(
        self,
        tool_definition: ToolDefinition,
        tool_manifest: ToolManifest
    ) -> bool:
        """
        Register a new tool in the registry.

        Args:
            tool_definition: Tool definition with metadata
            tool_manifest: Complete tool manifest

        Returns:
            True if registered successfully

        Raises:
            ToolExecutionError: If registration fails (E3007, E3008)
        """
        try:
            # Generate semantic embedding
            embedding = await self.generate_embedding(tool_definition.description)

            async with self.db_pool.connection() as conn:
                async with conn.cursor() as cur:
                    # Check for duplicate
                    await cur.execute(
                        "SELECT tool_id FROM tool_definitions WHERE tool_id = %s",
                        (tool_definition.tool_id,)
                    )
                    if await cur.fetchone():
                        raise ToolExecutionError(
                            ErrorCode.E3007,
                            message="Tool already registered",
                            details={"tool_id": tool_definition.tool_id}
                        )

                    # Insert tool definition
                    await cur.execute("""
                        INSERT INTO tool_definitions (
                            tool_id, tool_name, description, category, tags,
                            latest_version, source_type, source_metadata,
                            deprecation_state, requires_approval,
                            default_timeout_seconds, default_cpu_millicore_limit,
                            default_memory_mb_limit, required_permissions,
                            result_schema, retry_policy, circuit_breaker_config,
                            description_embedding
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """, (
                        tool_definition.tool_id,
                        tool_definition.tool_name,
                        tool_definition.description,
                        tool_definition.category.value,
                        tool_definition.tags,
                        tool_definition.latest_version,
                        tool_definition.source_type.value,
                        psycopg.types.json.Jsonb(tool_definition.source_metadata),
                        tool_definition.deprecation_state.value,
                        tool_definition.requires_approval,
                        tool_definition.default_timeout_seconds,
                        tool_definition.default_cpu_millicore_limit,
                        tool_definition.default_memory_mb_limit,
                        psycopg.types.json.Jsonb(tool_definition.required_permissions),
                        psycopg.types.json.Jsonb(tool_definition.result_schema) if tool_definition.result_schema else None,
                        psycopg.types.json.Jsonb(tool_definition.retry_policy) if tool_definition.retry_policy else None,
                        psycopg.types.json.Jsonb(tool_definition.circuit_breaker_config) if tool_definition.circuit_breaker_config else None,
                        embedding,
                    ))

                    # Insert tool version
                    await cur.execute("""
                        INSERT INTO tool_versions (
                            tool_id, version, manifest, compatibility_range, release_notes
                        ) VALUES (%s, %s, %s, %s, %s)
                    """, (
                        tool_definition.tool_id,
                        tool_manifest.version,
                        psycopg.types.json.Jsonb(tool_manifest.to_dict()),
                        None,
                        None,
                    ))

                    await conn.commit()

            logger.info(f"Registered tool {tool_definition.tool_id} version {tool_manifest.version}")
            return True

        except ToolExecutionError:
            raise
        except Exception as e:
            logger.error(f"Failed to register tool: {e}")
            raise ToolExecutionError(
                ErrorCode.E3008,
                message="Tool registration failed",
                details={"error": str(e), "tool_id": tool_definition.tool_id}
            )

    async def get_tool(self, tool_id: str) -> Optional[ToolDefinition]:
        """
        Retrieve tool definition by ID.

        Args:
            tool_id: Tool identifier

        Returns:
            ToolDefinition or None if not found

        Raises:
            ToolExecutionError: If tool not found (E3001)
        """
        async with self.db_pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT * FROM tool_definitions WHERE tool_id = %s",
                    (tool_id,)
                )
                row = await cur.fetchone()

                if not row:
                    raise ToolExecutionError(
                        ErrorCode.E3001,
                        message="Tool not found",
                        details={"tool_id": tool_id}
                    )

                return self._row_to_tool_definition(row)

    async def list_tools(
        self,
        category: Optional[ToolCategory] = None,
        include_deprecated: bool = False
    ) -> List[ToolDefinition]:
        """
        List all available tools.

        Args:
            category: Optional category filter
            include_deprecated: Whether to include deprecated tools

        Returns:
            List of ToolDefinition objects

        Raises:
            ToolExecutionError: If listing fails (E3008)
        """
        try:
            async with self.db_pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    # Build query based on filters
                    if category and not include_deprecated:
                        await cur.execute("""
                            SELECT * FROM tool_definitions
                            WHERE category = %s
                              AND deprecation_state = 'active'
                            ORDER BY tool_name
                        """, (category.value,))
                    elif category:
                        await cur.execute("""
                            SELECT * FROM tool_definitions
                            WHERE category = %s
                            ORDER BY tool_name
                        """, (category.value,))
                    elif not include_deprecated:
                        await cur.execute("""
                            SELECT * FROM tool_definitions
                            WHERE deprecation_state = 'active'
                            ORDER BY tool_name
                        """)
                    else:
                        await cur.execute("""
                            SELECT * FROM tool_definitions
                            ORDER BY tool_name
                        """)

                    rows = await cur.fetchall()
                    tools = [self._row_to_tool_definition(row) for row in rows]

                    logger.info(f"Listed {len(tools)} tools")
                    return tools

        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            raise ToolExecutionError(
                ErrorCode.E3008,
                message="Failed to list tools",
                details={"error": str(e)}
            )

    async def semantic_search(
        self,
        query: str,
        limit: int = 10,
        category: Optional[ToolCategory] = None
    ) -> List[Tuple[ToolDefinition, float]]:
        """
        Semantic search for tools using query embedding.

        Args:
            query: Natural language query
            limit: Maximum results
            category: Optional category filter

        Returns:
            List of (ToolDefinition, similarity_score) tuples

        Raises:
            ToolExecutionError: If search fails (E3005)
        """
        try:
            # Generate query embedding
            query_embedding = await self.generate_embedding(query)

            async with self.db_pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    # Semantic search with category filter
                    if category:
                        await cur.execute("""
                            SELECT *,
                                   1 - (description_embedding <=> %s::vector) as similarity
                            FROM tool_definitions
                            WHERE category = %s
                              AND deprecation_state = 'active'
                              AND 1 - (description_embedding <=> %s::vector) >= %s
                            ORDER BY similarity DESC
                            LIMIT %s
                        """, (query_embedding, category.value, query_embedding, self.semantic_search_threshold, limit))
                    else:
                        await cur.execute("""
                            SELECT *,
                                   1 - (description_embedding <=> %s::vector) as similarity
                            FROM tool_definitions
                            WHERE deprecation_state = 'active'
                              AND 1 - (description_embedding <=> %s::vector) >= %s
                            ORDER BY similarity DESC
                            LIMIT %s
                        """, (query_embedding, query_embedding, self.semantic_search_threshold, limit))

                    rows = await cur.fetchall()
                    results = []
                    for row in rows:
                        similarity = row.pop('similarity')
                        tool_def = self._row_to_tool_definition(row)
                        results.append((tool_def, similarity))

                    logger.info(f"Semantic search for '{query}' returned {len(results)} results")
                    return results

        except ToolExecutionError:
            raise
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            raise ToolExecutionError(
                ErrorCode.E3005,
                message="Semantic search failed",
                details={"error": str(e), "query": query}
            )

    def _row_to_tool_definition(self, row: Dict[str, Any]) -> ToolDefinition:
        """Convert database row to ToolDefinition"""
        return ToolDefinition(
            tool_id=row['tool_id'],
            tool_name=row['tool_name'],
            description=row['description'],
            category=ToolCategory(row['category']),
            tags=row.get('tags', []),
            latest_version=row['latest_version'],
            source_type=SourceType(row['source_type']),
            source_metadata=row.get('source_metadata', {}),
            deprecation_state=DeprecationState(row.get('deprecation_state', 'active')),
            deprecation_date=row.get('deprecation_date'),
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            requires_approval=row.get('requires_approval', False),
            default_timeout_seconds=row.get('default_timeout_seconds', 30),
            default_cpu_millicore_limit=row.get('default_cpu_millicore_limit', 500),
            default_memory_mb_limit=row.get('default_memory_mb_limit', 1024),
            required_permissions=row.get('required_permissions', {}),
            result_schema=row.get('result_schema'),
            retry_policy=row.get('retry_policy'),
            circuit_breaker_config=row.get('circuit_breaker_config'),
        )

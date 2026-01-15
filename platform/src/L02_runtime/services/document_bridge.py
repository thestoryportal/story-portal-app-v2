"""
Document Bridge

Integrates with L01 Phase 15 Document Management (MCP document-consolidator)
for authoritative document queries and claim verification.

Based on Section 3.3.7 of agent-runtime-layer-specification-v1.2-final-ASCII.md
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone

from .mcp_client import MCPClient, MCPToolResult

logger = logging.getLogger(__name__)


class DocumentError(Exception):
    """Document bridge error"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class DocumentBridge:
    """
    Bridge to L01 Phase 15 Document Management via MCP.

    Responsibilities:
    - Query authoritative documents
    - Verify claims against source of truth
    - Cache query results
    - Track document confidence scores
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize DocumentBridge.

        Args:
            config: Configuration dict with:
                - endpoint: MCP server endpoint
                - default_confidence_threshold: Minimum confidence score
                - max_sources: Maximum sources to return
                - cache_ttl_seconds: Cache TTL
                - verify_claims: Enable claim verification
        """
        self.config = config or {}

        # Configuration
        self.endpoint = self.config.get(
            "endpoint",
            "mcp-document-consolidator"
        )
        self.confidence_threshold = self.config.get(
            "default_confidence_threshold", 0.7
        )
        self.max_sources = self.config.get("max_sources", 5)
        self.cache_ttl = self.config.get("cache_ttl_seconds", 300)
        self.verify_claims = self.config.get("verify_claims", True)

        # MCP server configuration
        mcp_base_path = self.config.get(
            "mcp_base_path",
            "/Volumes/Extreme SSD/projects/story-portal-app/platform/services/mcp-document-consolidator"
        )
        server_script = os.path.join(mcp_base_path, "dist/server.js")

        # Initialize MCP client
        mcp_timeout = self.config.get("mcp_timeout_seconds", 30)
        self.mcp_client = MCPClient(
            server_command=["node", server_script],
            server_name="document-consolidator",
            timeout_seconds=mcp_timeout,
            cwd=mcp_base_path,
            env=os.environ.copy()  # Pass environment to subprocess
        )

        # Query cache: query_key -> (result, expiry_time)
        self._cache: Dict[str, tuple] = {}

        logger.info(
            f"DocumentBridge initialized: endpoint={self.endpoint}, "
            f"confidence_threshold={self.confidence_threshold}"
        )

    async def initialize(self) -> None:
        """Initialize document bridge"""
        # Connect to MCP server
        try:
            connected = await self.mcp_client.connect()
            if connected:
                # Verify connection by listing tools
                tools = await self.mcp_client.list_tools()
                logger.info(f"MCP document-consolidator connected with {len(tools)} tools available")
            else:
                logger.warning("Failed to connect to MCP document-consolidator, using stub mode")
        except Exception as e:
            logger.warning(f"Failed to verify MCP connection: {e}, using stub mode")

        logger.info("DocumentBridge initialization complete")

    async def query_documents(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Query documents using hybrid search.

        Args:
            query: Search query
            filters: Optional filters (e.g., document types, date ranges)
            use_cache: Whether to use cached results

        Returns:
            List of document results with confidence scores

        Raises:
            DocumentError: If query fails
        """
        logger.info(f"Querying documents: {query}")

        # Check cache
        cache_key = self._get_cache_key(query, filters)
        if use_cache:
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                logger.debug("Returning cached query result")
                return cached_result

        try:
            # Call MCP search tool
            result = await self._call_mcp_tool(
                "search_hybrid",
                {
                    "query": query,
                    "limit": self.max_sources,
                    "filters": filters or {},
                }
            )

            # Extract documents from result
            documents = result.get("documents", [])

            # Filter by confidence threshold
            filtered_docs = [
                doc for doc in documents
                if doc.get("confidence", 0) >= self.confidence_threshold
            ]

            logger.info(
                f"Found {len(filtered_docs)} documents above confidence threshold"
            )

            # Cache result
            if use_cache:
                self._add_to_cache(cache_key, filtered_docs)

            return filtered_docs

        except Exception as e:
            logger.error(f"Document query failed: {e}")
            raise DocumentError(
                code="E2060",
                message=f"Document query failed: {str(e)}"
            )

    async def get_document(
        self,
        document_id: str
    ) -> Dict[str, Any]:
        """
        Get a specific document by ID.

        Args:
            document_id: Document identifier

        Returns:
            Document data

        Raises:
            DocumentError: If document not found
        """
        logger.info(f"Getting document: {document_id}")

        try:
            result = await self._call_mcp_tool(
                "get_document",
                {
                    "documentId": document_id,
                }
            )

            document = result.get("document")
            if not document:
                raise DocumentError(
                    code="E2063",
                    message=f"Document {document_id} not found"
                )

            return document

        except DocumentError:
            raise
        except Exception as e:
            logger.error(f"Failed to get document {document_id}: {e}")
            raise DocumentError(
                code="E2063",
                message=f"Document retrieval failed: {str(e)}"
            )

    async def verify_claim(
        self,
        claim: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify a claim against authoritative sources.

        Args:
            claim: Claim to verify
            context: Optional context for claim

        Returns:
            Verification result with:
                - verified: bool
                - confidence: float
                - sources: List of supporting documents
                - explanation: str

        Raises:
            DocumentError: If verification fails
        """
        if not self.verify_claims:
            logger.warning("Claim verification is disabled")
            return {
                "verified": False,
                "confidence": 0.0,
                "sources": [],
                "explanation": "Claim verification is disabled",
            }

        logger.info(f"Verifying claim: {claim}")

        try:
            # Query for relevant documents
            documents = await self.query_documents(
                query=claim,
                use_cache=True,
            )

            if not documents:
                raise DocumentError(
                    code="E2061",
                    message="No authoritative source found for claim"
                )

            # Analyze documents to verify claim
            # TODO: Implement more sophisticated claim verification logic
            # For now, check if any high-confidence document supports the claim

            verified = False
            max_confidence = 0.0
            supporting_sources = []

            for doc in documents:
                confidence = doc.get("confidence", 0)
                if confidence >= self.confidence_threshold:
                    verified = True
                    max_confidence = max(max_confidence, confidence)
                    supporting_sources.append({
                        "document_id": doc.get("id"),
                        "title": doc.get("title"),
                        "confidence": confidence,
                    })

            result = {
                "verified": verified,
                "confidence": max_confidence,
                "sources": supporting_sources[:self.max_sources],
                "explanation": (
                    f"Claim verified by {len(supporting_sources)} authoritative source(s)"
                    if verified
                    else "No authoritative sources found to support claim"
                ),
            }

            logger.info(
                f"Claim verification complete: verified={verified}, "
                f"confidence={max_confidence:.2f}"
            )

            return result

        except DocumentError:
            raise
        except Exception as e:
            logger.error(f"Claim verification failed: {e}")
            raise DocumentError(
                code="E2062",
                message=f"Claim verification failed: {str(e)}"
            )

    async def find_source_of_truth(
        self,
        topic: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find the authoritative source of truth for a topic.

        Args:
            topic: Topic to find source for

        Returns:
            Authoritative document or None if not found

        Raises:
            DocumentError: If search fails
        """
        logger.info(f"Finding source of truth for: {topic}")

        try:
            # Query documents
            documents = await self.query_documents(
                query=topic,
                use_cache=True,
            )

            if not documents:
                logger.warning(f"No source of truth found for: {topic}")
                return None

            # Return highest confidence document
            best_doc = max(documents, key=lambda d: d.get("confidence", 0))

            logger.info(
                f"Found source of truth: {best_doc.get('title')} "
                f"(confidence={best_doc.get('confidence', 0):.2f})"
            )

            return best_doc

        except Exception as e:
            logger.error(f"Failed to find source of truth: {e}")
            raise DocumentError(
                code="E2061",
                message=f"Failed to find source of truth: {str(e)}"
            )

    async def _call_mcp_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call MCP document-consolidator tool.

        Args:
            tool_name: Tool name
            parameters: Tool parameters

        Returns:
            Tool result

        Raises:
            Exception: If tool call fails
        """
        logger.debug(f"MCP tool call: {tool_name} with params: {parameters}")

        try:
            # Call tool via MCP client
            result: MCPToolResult = await self.mcp_client.call_tool(
                tool_name=tool_name,
                arguments=parameters
            )

            if result.success:
                logger.debug(f"MCP tool {tool_name} succeeded in {result.execution_time_ms:.2f}ms")
                return result.result if result.result is not None else {"success": True}
            else:
                logger.error(f"MCP tool {tool_name} failed: {result.error}")
                # Return stub response on failure for graceful degradation
                return {
                    "success": False,
                    "error": result.error,
                    "tool": tool_name,
                    "documents": [],
                }

        except Exception as e:
            logger.error(f"MCP tool call exception: {tool_name}: {e}")
            # Return stub response on exception for graceful degradation
            return {
                "success": False,
                "error": str(e),
                "tool": tool_name,
                "documents": [],
            }

    def _get_cache_key(
        self,
        query: str,
        filters: Optional[Dict[str, Any]]
    ) -> str:
        """Generate cache key for query"""
        filter_str = json.dumps(filters or {}, sort_keys=True)
        return f"{query}:{filter_str}"

    def _get_from_cache(
        self,
        cache_key: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Get result from cache if not expired"""
        if cache_key in self._cache:
            result, expiry = self._cache[cache_key]
            if datetime.now(timezone.utc) < expiry:
                return result
            else:
                # Expired, remove from cache
                del self._cache[cache_key]
        return None

    def _add_to_cache(
        self,
        cache_key: str,
        result: List[Dict[str, Any]]
    ) -> None:
        """Add result to cache with expiry"""
        expiry = datetime.now(timezone.utc) + timedelta(seconds=self.cache_ttl)
        self._cache[cache_key] = (result, expiry)

    async def clear_cache(self) -> None:
        """Clear query cache"""
        self._cache.clear()
        logger.info("Document query cache cleared")

    async def cleanup(self) -> None:
        """Cleanup document bridge"""
        logger.info("Cleaning up DocumentBridge")
        self._cache.clear()

        # Disconnect MCP client
        await self.mcp_client.disconnect()
        logger.info("DocumentBridge cleanup complete")

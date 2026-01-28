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
from enum import Enum

from .mcp_client import MCPClient, MCPToolResult

logger = logging.getLogger(__name__)


class MCPErrorMode(Enum):
    """MCP error handling mode"""
    FAIL_FAST = "fail_fast"      # Raise error if MCP unavailable
    GRACEFUL_DEGRADE = "graceful"  # Fall back to stub mode


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
                - mcp_error_mode: Error handling mode ("fail_fast" or "graceful")
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

        # MCP error handling mode
        error_mode_str = self.config.get("mcp_error_mode", "graceful")
        self.mcp_error_mode = MCPErrorMode(error_mode_str)

        # Stub mode flag (set if MCP unavailable in graceful mode)
        self._stub_mode = False

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
        """
        Initialize document bridge.

        Raises:
            DocumentError: If MCP unavailable and mcp_error_mode is FAIL_FAST
        """
        # Connect to MCP server
        try:
            connected = await self.mcp_client.connect()
            if connected:
                # Verify connection by listing tools
                tools = await self.mcp_client.list_tools()
                logger.info(f"MCP document-consolidator connected with {len(tools)} tools available")
                self._stub_mode = False
            else:
                self._handle_mcp_unavailable("Failed to connect to MCP document-consolidator")
        except Exception as e:
            self._handle_mcp_unavailable(f"Failed to verify MCP connection: {e}")

        logger.info(
            f"DocumentBridge initialization complete "
            f"(stub_mode={self._stub_mode}, error_mode={self.mcp_error_mode.value})"
        )

    def _handle_mcp_unavailable(self, message: str) -> None:
        """
        Handle MCP unavailability based on error mode.

        Args:
            message: Error message

        Raises:
            DocumentError: If error mode is FAIL_FAST
        """
        if self.mcp_error_mode == MCPErrorMode.FAIL_FAST:
            logger.error(f"MCP required but unavailable: {message}")
            raise DocumentError(
                code="E2065",
                message=f"MCP document-consolidator required but unavailable: {message}"
            )
        else:
            logger.warning(f"{message}, using stub mode")
            self._stub_mode = True

    def is_stub_mode(self) -> bool:
        """Check if bridge is operating in stub mode."""
        return self._stub_mode

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

        Uses semantic similarity matching and consensus scoring
        to determine claim validity.

        Args:
            claim: Claim to verify
            context: Optional context for claim

        Returns:
            Verification result with:
                - verified: bool
                - confidence: float
                - consensus_score: float
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
                "consensus_score": 0.0,
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

            # Build supporting sources with semantic similarity
            supporting_sources = []

            for doc in documents:
                doc_confidence = doc.get("confidence", 0)
                doc_content = doc.get("content", doc.get("snippet", ""))

                # Compute semantic similarity between claim and document
                similarity = self._compute_semantic_similarity(claim, doc_content)

                # Compute recency factor (newer docs get higher weight)
                recency = self._compute_recency_factor(doc)

                # Combined relevance score
                relevance_score = (
                    doc_confidence * 0.4 +
                    similarity * 0.4 +
                    recency * 0.2
                )

                if relevance_score >= self.confidence_threshold * 0.8:
                    supporting_sources.append({
                        "document_id": doc.get("id"),
                        "title": doc.get("title"),
                        "confidence": doc_confidence,
                        "similarity": similarity,
                        "recency": recency,
                        "relevance_score": relevance_score,
                    })

            # Sort by relevance score
            supporting_sources.sort(
                key=lambda x: x["relevance_score"],
                reverse=True
            )

            # Compute consensus score
            consensus_score = self._compute_consensus_score(supporting_sources)

            # Determine verification result
            verified = consensus_score >= 0.7 and len(supporting_sources) > 0
            max_confidence = max(
                (s["relevance_score"] for s in supporting_sources),
                default=0.0
            )

            result = {
                "verified": verified,
                "confidence": max_confidence,
                "consensus_score": consensus_score,
                "sources": supporting_sources[:self.max_sources],
                "explanation": self._build_verification_explanation(
                    verified, consensus_score, supporting_sources
                ),
            }

            logger.info(
                f"Claim verification complete: verified={verified}, "
                f"confidence={max_confidence:.2f}, consensus={consensus_score:.2f}"
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

    def _compute_semantic_similarity(
        self,
        claim: str,
        content: str
    ) -> float:
        """
        Compute semantic similarity between claim and document content.

        Uses simple word overlap for now. In production, this would use
        embeddings-based similarity via L04.

        Args:
            claim: Claim text
            content: Document content

        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not claim or not content:
            return 0.0

        # Normalize text
        claim_words = set(claim.lower().split())
        content_words = set(content.lower().split())

        # Remove common stop words
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "must", "shall",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "above",
            "below", "between", "under", "again", "further", "then", "once",
            "and", "but", "or", "nor", "so", "yet", "both", "either",
            "neither", "not", "only", "own", "same", "than", "too", "very",
        }

        claim_words = claim_words - stop_words
        content_words = content_words - stop_words

        if not claim_words or not content_words:
            return 0.0

        # Jaccard similarity
        intersection = claim_words & content_words
        union = claim_words | content_words

        return len(intersection) / len(union) if union else 0.0

    def _compute_recency_factor(self, doc: Dict[str, Any]) -> float:
        """
        Compute recency factor for a document.

        Newer documents get higher scores.

        Args:
            doc: Document data

        Returns:
            Recency score between 0.0 and 1.0
        """
        updated_at = doc.get("updated_at") or doc.get("created_at")

        if not updated_at:
            return 0.5  # Default for unknown age

        try:
            if isinstance(updated_at, str):
                from datetime import datetime
                updated_at = datetime.fromisoformat(
                    updated_at.replace("Z", "+00:00")
                )

            now = datetime.now(timezone.utc)
            age_days = (now - updated_at).days

            # Decay function: 1.0 for today, 0.5 at 30 days, ~0.25 at 90 days
            decay_rate = 0.023  # ln(2)/30
            return max(0.1, 1.0 / (1 + decay_rate * age_days))

        except Exception:
            return 0.5

    def _compute_consensus_score(
        self,
        sources: List[Dict[str, Any]]
    ) -> float:
        """
        Compute consensus score from multiple sources.

        Higher scores indicate stronger agreement across sources.

        Args:
            sources: List of supporting sources

        Returns:
            Consensus score between 0.0 and 1.0
        """
        if not sources:
            return 0.0

        # Single source: use its relevance but cap at 0.7
        if len(sources) == 1:
            return min(0.7, sources[0].get("relevance_score", 0))

        # Multiple sources: weighted average with bonus for agreement
        total_relevance = sum(s.get("relevance_score", 0) for s in sources)
        avg_relevance = total_relevance / len(sources)

        # Agreement bonus: more sources agreeing increases confidence
        agreement_bonus = min(0.2, 0.05 * len(sources))

        # Consistency penalty: high variance in scores reduces confidence
        if len(sources) > 1:
            scores = [s.get("relevance_score", 0) for s in sources]
            variance = sum((s - avg_relevance) ** 2 for s in scores) / len(scores)
            consistency_penalty = min(0.1, variance)
        else:
            consistency_penalty = 0

        consensus = avg_relevance + agreement_bonus - consistency_penalty

        return max(0.0, min(1.0, consensus))

    def _build_verification_explanation(
        self,
        verified: bool,
        consensus_score: float,
        sources: List[Dict[str, Any]]
    ) -> str:
        """
        Build human-readable explanation for verification result.

        Args:
            verified: Whether claim was verified
            consensus_score: Consensus score
            sources: Supporting sources

        Returns:
            Explanation string
        """
        if not sources:
            return "No authoritative sources found to evaluate this claim."

        if verified:
            if consensus_score >= 0.9:
                strength = "strongly"
            elif consensus_score >= 0.8:
                strength = "well"
            else:
                strength = "moderately"

            return (
                f"Claim is {strength} supported by {len(sources)} "
                f"authoritative source(s) with {consensus_score:.0%} consensus."
            )
        else:
            if sources:
                return (
                    f"Found {len(sources)} related source(s) but consensus "
                    f"({consensus_score:.0%}) is below verification threshold."
                )
            else:
                return "No sources found that support this claim."

    async def find_source_of_truth(
        self,
        query: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find the authoritative source of truth for a query.

        Args:
            query: Query to find source for

        Returns:
            Authoritative document or None if not found

        Raises:
            DocumentError: If search fails
        """
        logger.info(f"Finding source of truth for: {query}")

        try:
            # Query documents
            documents = await self.query_documents(
                query=query,
                use_cache=True,
            )

            if not documents:
                logger.warning(f"No source of truth found for: {query}")
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
            DocumentError: If tool call fails and error mode is FAIL_FAST
        """
        # In stub mode, return stub response
        if self._stub_mode:
            logger.debug(f"MCP tool call in stub mode: {tool_name}")
            return self._get_stub_response(tool_name, parameters)

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
                return self._handle_tool_failure(tool_name, result.error)

        except Exception as e:
            logger.error(f"MCP tool call exception: {tool_name}: {e}")
            return self._handle_tool_failure(tool_name, str(e))

    def _handle_tool_failure(
        self,
        tool_name: str,
        error: str
    ) -> Dict[str, Any]:
        """
        Handle MCP tool failure based on error mode.

        Args:
            tool_name: Tool name
            error: Error message

        Returns:
            Stub response if graceful mode

        Raises:
            DocumentError: If error mode is FAIL_FAST
        """
        if self.mcp_error_mode == MCPErrorMode.FAIL_FAST:
            raise DocumentError(
                code="E2066",
                message=f"MCP tool {tool_name} failed: {error}"
            )
        else:
            # Graceful degradation - return stub response
            return {
                "success": False,
                "error": error,
                "tool": tool_name,
                "documents": [],
                "stub_mode": True,
            }

    def _get_stub_response(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get stub response for MCP tool call.

        Args:
            tool_name: Tool name
            parameters: Tool parameters

        Returns:
            Stub response based on tool type
        """
        # Provide meaningful stub responses for common tools
        stub_responses = {
            "search_hybrid": {"documents": [], "stub": True},
            "get_document": {"document": None, "stub": True},
            "get_source_of_truth": {"answer": None, "sources": [], "stub": True},
        }

        return stub_responses.get(tool_name, {
            "success": True,
            "tool": tool_name,
            "documents": [],
            "stub": True,
        })

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

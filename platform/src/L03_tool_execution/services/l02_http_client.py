"""
L02 HTTP Client

HTTP client for communicating with L02 Runtime services.
Provides access to Document and Session bridges via HTTP.

Note: This client expects L02 to expose HTTP endpoints for these services.
If L02 doesn't expose endpoints, operations gracefully degrade with warnings.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List

import httpx

logger = logging.getLogger(__name__)


class L02ClientError(Exception):
    """L02 HTTP client error."""

    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{code}] {message}")


class L02HttpClient:
    """
    HTTP client for L02 Runtime bridges.

    Provides HTTP access to:
    - Document Bridge (document retrieval, search)
    - Session Bridge (checkpoints, context management)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8002",
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 0.5,
    ):
        """
        Initialize L02 HTTP Client.

        Args:
            base_url: L02 service base URL
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._client: Optional[httpx.AsyncClient] = None
        self._available: Optional[bool] = None

    async def initialize(self) -> bool:
        """
        Initialize HTTP client and check L02 availability.

        Returns:
            True if L02 is available
        """
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
            headers={"Content-Type": "application/json"},
        )

        # Check L02 availability
        self._available = await self._check_availability()
        if self._available:
            logger.info(f"L02 HTTP Client connected to {self.base_url}")
        else:
            logger.warning(f"L02 service at {self.base_url} not available - operating in degraded mode")

        return self._available

    async def _check_availability(self) -> bool:
        """Check if L02 service is available."""
        try:
            response = await self._client.get("/health/live")
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"L02 availability check failed: {e}")
            return False

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        logger.info("L02 HTTP Client closed")

    @property
    def is_available(self) -> bool:
        """Check if L02 is available."""
        return self._available is True

    async def _request(
        self,
        method: str,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Make HTTP request with retries.

        Args:
            method: HTTP method
            path: Request path
            json: JSON body
            params: Query parameters

        Returns:
            Response JSON or None if unavailable
        """
        if not self._client:
            logger.warning("L02 HTTP Client not initialized")
            return None

        if not self._available:
            logger.debug(f"L02 not available, skipping request to {path}")
            return None

        for attempt in range(self.max_retries):
            try:
                response = await self._client.request(
                    method=method,
                    url=path,
                    json=json,
                    params=params,
                )

                if response.status_code == 404:
                    # Endpoint not found - L02 might not expose this endpoint yet
                    logger.warning(f"L02 endpoint {path} not found (404)")
                    return None

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                logger.error(f"L02 HTTP error on {path}: {e.response.status_code}")
                if attempt == self.max_retries - 1:
                    raise L02ClientError(
                        code="E3710",
                        message=f"L02 request failed: {e.response.status_code}",
                        details={"path": path, "status": e.response.status_code},
                    )

            except httpx.RequestError as e:
                logger.error(f"L02 request error on {path}: {e}")
                if attempt == self.max_retries - 1:
                    # Mark as unavailable on persistent failure
                    self._available = False
                    return None

            await asyncio.sleep(self.retry_delay * (attempt + 1))

        return None

    # ==================== Document Bridge Methods ====================

    async def get_document(
        self,
        document_id: str,
        version_pinning: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve document from L02 Document Bridge.

        Args:
            document_id: Document identifier
            version_pinning: Pin document version

        Returns:
            Document data or None if unavailable
        """
        logger.debug(f"L02 get_document: {document_id}")

        return await self._request(
            method="GET",
            path=f"/documents/{document_id}",
            params={"version_pinning": version_pinning},
        )

    async def search_documents(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search documents via L02 Document Bridge.

        Args:
            query: Search query
            limit: Maximum results
            filters: Optional search filters

        Returns:
            List of matching documents (empty if unavailable)
        """
        logger.debug(f"L02 search_documents: {query}")

        result = await self._request(
            method="POST",
            path="/documents/search",
            json={
                "query": query,
                "limit": limit,
                "filters": filters or {},
            },
        )

        if result and "documents" in result:
            return result["documents"]
        return []

    async def verify_claim(
        self,
        claim: str,
        context: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Verify claim via L02 Document Bridge.

        Args:
            claim: Claim to verify
            context: Optional context

        Returns:
            Verification result or None if unavailable
        """
        logger.debug(f"L02 verify_claim: {claim}")

        return await self._request(
            method="POST",
            path="/documents/verify",
            json={
                "claim": claim,
                "context": context,
            },
        )

    # ==================== Session Bridge Methods ====================

    async def create_checkpoint(
        self,
        task_id: str,
        checkpoint_data: Dict[str, Any],
    ) -> Optional[str]:
        """
        Create checkpoint via L02 Session Bridge.

        Args:
            task_id: Task identifier
            checkpoint_data: Checkpoint state

        Returns:
            Checkpoint ID or None if unavailable
        """
        logger.debug(f"L02 create_checkpoint: task={task_id}")

        result = await self._request(
            method="POST",
            path=f"/sessions/{task_id}/checkpoints",
            json=checkpoint_data,
        )

        if result and "checkpoint_id" in result:
            return result["checkpoint_id"]
        return None

    async def restore_checkpoint(
        self,
        checkpoint_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Restore checkpoint via L02 Session Bridge.

        Args:
            checkpoint_id: Checkpoint identifier

        Returns:
            Checkpoint data or None if unavailable
        """
        logger.debug(f"L02 restore_checkpoint: {checkpoint_id}")

        return await self._request(
            method="GET",
            path=f"/checkpoints/{checkpoint_id}",
        )

    async def save_context_snapshot(
        self,
        task_id: str,
        context: Dict[str, Any],
        change_summary: Optional[str] = None,
    ) -> bool:
        """
        Save context snapshot via L02 Session Bridge.

        Args:
            task_id: Task identifier
            context: Context state
            change_summary: Description of changes

        Returns:
            True if successful
        """
        logger.debug(f"L02 save_context_snapshot: task={task_id}")

        result = await self._request(
            method="POST",
            path=f"/sessions/{task_id}/context",
            json={
                "context": context,
                "change_summary": change_summary,
            },
        )

        return result is not None

    async def get_unified_context(
        self,
        task_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get unified context via L02 Session Bridge.

        Args:
            task_id: Task identifier

        Returns:
            Context data or None if unavailable
        """
        logger.debug(f"L02 get_unified_context: task={task_id}")

        return await self._request(
            method="GET",
            path=f"/sessions/{task_id}/context",
        )

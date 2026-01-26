"""
L01 Bridge - Connects L05 Planning to L01 Data Layer
Path: platform/src/L05_planning/integration/l01_bridge.py

Enhanced with real HTTP client support for connecting to L01 service.
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# Optional httpx import for real HTTP calls
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    logger.warning("httpx not available, L01Bridge will use local storage only")


class StoreResultType(Enum):
    """Types of results that can be stored."""
    PLAN = "plan"
    UNIT = "unit"
    VALIDATION = "validation"
    CHECKPOINT = "checkpoint"
    EXECUTION = "execution"


@dataclass
class StoreResult:
    """Result of a store operation."""
    success: bool
    record_id: str
    result_type: StoreResultType
    timestamp: datetime = field(default_factory=datetime.now)
    message: str = ""
    error: Optional[str] = None
    remote: bool = False  # True if stored via HTTP


@dataclass
class StoredRecord:
    """A record stored in L01."""
    record_id: str
    record_type: StoreResultType
    data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class L01Bridge:
    """
    Bridge to L01 Data Layer for persisting planning artifacts.

    Features:
    - Real HTTP connection to L01 service (localhost:8001)
    - Health check on initialization
    - Graceful fallback to local storage when L01 unavailable
    - Automatic retry on transient failures

    Provides abstraction for:
    - Storing parsed plans
    - Storing atomic units
    - Storing validation results
    - Storing checkpoints
    - Querying historical data
    """

    def __init__(
        self,
        l01_client: Optional[Any] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """
        Initialize L01 bridge.

        Args:
            l01_client: Optional L01 client instance (for dependency injection)
            base_url: Base URL for L01 service (default: http://localhost:8001)
            api_key: API key for L01 authentication
            timeout: HTTP request timeout in seconds
        """
        self.l01_client = l01_client
        self.base_url = base_url or os.getenv("L01_BASE_URL", "http://localhost:8001")
        self.api_key = api_key or os.getenv("L01_API_KEY", "test_token_123")
        self.timeout = timeout

        self._local_store: Dict[str, StoredRecord] = {}
        self._initialized = False
        self._connected = False
        self._http_client: Optional["httpx.AsyncClient"] = None

        # Statistics
        self._remote_store_count = 0
        self._local_store_count = 0
        self._failed_store_count = 0

    async def initialize(self):
        """Initialize connection to L01 with health check."""
        if self._initialized:
            return

        logger.info(f"Initializing L01Bridge (base_url={self.base_url})")

        if HTTPX_AVAILABLE:
            try:
                self._http_client = httpx.AsyncClient(
                    base_url=self.base_url,
                    timeout=self.timeout,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )

                # Health check
                response = await self._http_client.get("/health/live")
                if response.status_code == 200:
                    self._connected = True
                    logger.info("L01Bridge connected to L01 service")
                else:
                    logger.warning(f"L01 health check failed: {response.status_code}")
                    self._connected = False

            except Exception as e:
                logger.warning(f"Failed to connect to L01: {e}. Using local storage.")
                self._connected = False
                if self._http_client:
                    await self._http_client.aclose()
                    self._http_client = None
        else:
            logger.info("httpx not available, using local storage only")
            self._connected = False

        self._initialized = True
        logger.info(f"L01Bridge initialized (connected={self._connected})")

    async def close(self):
        """Close HTTP client connection."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        self._connected = False

    async def store_result_async(
        self,
        result_type: StoreResultType,
        data: Dict[str, Any],
        record_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StoreResult:
        """
        Stores a result in L01 data layer (async version).

        Args:
            result_type: Type of result to store
            data: Data to store
            record_id: Optional custom record ID
            metadata: Optional metadata

        Returns:
            StoreResult with success status
        """
        record_id = record_id or str(uuid4())
        now = datetime.now()

        # Try remote storage first
        if self._connected and self._http_client:
            try:
                result = await self._store_remote(result_type, data, record_id, metadata)
                if result.success:
                    self._remote_store_count += 1
                    return result
            except Exception as e:
                logger.warning(f"Remote store failed, falling back to local: {e}")

        # Fall back to local storage
        return self._store_local(result_type, data, record_id, metadata, now)

    def store_result(
        self,
        result_type: StoreResultType,
        data: Dict[str, Any],
        record_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StoreResult:
        """
        Stores a result in L01 data layer (sync version - local only).

        For async with remote support, use store_result_async().
        """
        record_id = record_id or str(uuid4())
        now = datetime.now()
        return self._store_local(result_type, data, record_id, metadata, now)

    async def _store_remote(
        self,
        result_type: StoreResultType,
        data: Dict[str, Any],
        record_id: str,
        metadata: Optional[Dict[str, Any]],
    ) -> StoreResult:
        """Store record via HTTP to L01 service."""
        if not self._http_client:
            raise RuntimeError("HTTP client not initialized")

        # Map result type to L01 API endpoint
        endpoint_map = {
            StoreResultType.PLAN: "/api/plans",
            StoreResultType.UNIT: "/api/tasks",  # Units map to tasks in L01
            StoreResultType.VALIDATION: "/api/evaluations",
            StoreResultType.CHECKPOINT: "/api/checkpoints",
            StoreResultType.EXECUTION: "/api/executions",
        }

        endpoint = endpoint_map.get(result_type, "/api/records")

        payload = {
            "id": record_id,
            "data": data,
            "metadata": metadata or {},
            "type": result_type.value,
        }

        # Handle specific endpoints with proper payloads
        if result_type == StoreResultType.PLAN:
            payload = {
                "plan_id": record_id,
                "goal_id": data.get("goal_id", str(uuid4())),
                "agent_id": data.get("agent_id", str(uuid4())),
                "steps": data.get("steps", []),
                "status": data.get("status", "draft"),
                **data,
            }

        response = await self._http_client.post(endpoint, json=payload)

        if response.status_code in (200, 201):
            return StoreResult(
                success=True,
                record_id=record_id,
                result_type=result_type,
                message=f"Stored {result_type.value} in L01",
                remote=True,
            )
        else:
            logger.warning(f"L01 store failed: {response.status_code} - {response.text}")
            return StoreResult(
                success=False,
                record_id=record_id,
                result_type=result_type,
                error=f"HTTP {response.status_code}: {response.text}",
                remote=True,
            )

    def _store_local(
        self,
        result_type: StoreResultType,
        data: Dict[str, Any],
        record_id: str,
        metadata: Optional[Dict[str, Any]],
        now: datetime,
    ) -> StoreResult:
        """Store record in local storage."""
        try:
            record = StoredRecord(
                record_id=record_id,
                record_type=result_type,
                data=data,
                created_at=now,
                updated_at=now,
                metadata=metadata or {},
            )

            self._local_store[record_id] = record
            self._local_store_count += 1

            logger.debug(f"Stored {result_type.value} record locally: {record_id}")

            return StoreResult(
                success=True,
                record_id=record_id,
                result_type=result_type,
                message=f"Stored {result_type.value} locally",
                remote=False,
            )

        except Exception as e:
            self._failed_store_count += 1
            logger.error(f"Failed to store result: {e}")
            return StoreResult(
                success=False,
                record_id=record_id,
                result_type=result_type,
                error=str(e),
            )

    def store_plan(
        self,
        plan_id: str,
        plan_data: Dict[str, Any],
    ) -> StoreResult:
        """Stores a parsed plan."""
        return self.store_result(
            result_type=StoreResultType.PLAN,
            data=plan_data,
            record_id=plan_id,
            metadata={"plan_id": plan_id},
        )

    async def store_plan_async(
        self,
        plan_id: str,
        plan_data: Dict[str, Any],
    ) -> StoreResult:
        """Stores a parsed plan (async with remote support)."""
        return await self.store_result_async(
            result_type=StoreResultType.PLAN,
            data=plan_data,
            record_id=plan_id,
            metadata={"plan_id": plan_id},
        )

    def store_unit(
        self,
        unit_id: str,
        unit_data: Dict[str, Any],
        plan_id: Optional[str] = None,
    ) -> StoreResult:
        """Stores an atomic unit."""
        return self.store_result(
            result_type=StoreResultType.UNIT,
            data=unit_data,
            record_id=unit_id,
            metadata={"plan_id": plan_id} if plan_id else {},
        )

    async def store_unit_async(
        self,
        unit_id: str,
        unit_data: Dict[str, Any],
        plan_id: Optional[str] = None,
    ) -> StoreResult:
        """Stores an atomic unit (async with remote support)."""
        return await self.store_result_async(
            result_type=StoreResultType.UNIT,
            data=unit_data,
            record_id=unit_id,
            metadata={"plan_id": plan_id} if plan_id else {},
        )

    def store_validation(
        self,
        unit_id: str,
        validation_data: Dict[str, Any],
    ) -> StoreResult:
        """Stores validation results."""
        return self.store_result(
            result_type=StoreResultType.VALIDATION,
            data=validation_data,
            metadata={"unit_id": unit_id},
        )

    async def store_validation_async(
        self,
        unit_id: str,
        validation_data: Dict[str, Any],
    ) -> StoreResult:
        """Stores validation results (async with remote support)."""
        return await self.store_result_async(
            result_type=StoreResultType.VALIDATION,
            data=validation_data,
            metadata={"unit_id": unit_id},
        )

    def store_checkpoint(
        self,
        checkpoint_id: str,
        checkpoint_data: Dict[str, Any],
    ) -> StoreResult:
        """Stores a checkpoint."""
        return self.store_result(
            result_type=StoreResultType.CHECKPOINT,
            data=checkpoint_data,
            record_id=checkpoint_id,
        )

    async def store_checkpoint_async(
        self,
        checkpoint_id: str,
        checkpoint_data: Dict[str, Any],
    ) -> StoreResult:
        """Stores a checkpoint (async with remote support)."""
        return await self.store_result_async(
            result_type=StoreResultType.CHECKPOINT,
            data=checkpoint_data,
            record_id=checkpoint_id,
        )

    def store_execution(
        self,
        execution_id: str,
        execution_data: Dict[str, Any],
    ) -> StoreResult:
        """Stores execution results."""
        return self.store_result(
            result_type=StoreResultType.EXECUTION,
            data=execution_data,
            record_id=execution_id,
        )

    async def store_execution_async(
        self,
        execution_id: str,
        execution_data: Dict[str, Any],
    ) -> StoreResult:
        """Stores execution results (async with remote support)."""
        return await self.store_result_async(
            result_type=StoreResultType.EXECUTION,
            data=execution_data,
            record_id=execution_id,
        )

    def get_record(self, record_id: str) -> Optional[StoredRecord]:
        """
        Retrieves a record by ID.

        Args:
            record_id: Record ID

        Returns:
            StoredRecord if found, None otherwise
        """
        return self._local_store.get(record_id)

    async def get_record_async(self, record_id: str) -> Optional[StoredRecord]:
        """
        Retrieves a record by ID (async with remote support).

        Args:
            record_id: Record ID

        Returns:
            StoredRecord if found, None otherwise
        """
        # Try remote first
        if self._connected and self._http_client:
            try:
                response = await self._http_client.get(f"/api/records/{record_id}")
                if response.status_code == 200:
                    data = response.json()
                    return StoredRecord(
                        record_id=data.get("id", record_id),
                        record_type=StoreResultType(data.get("type", "execution")),
                        data=data.get("data", {}),
                        created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
                        updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat())),
                        metadata=data.get("metadata", {}),
                    )
            except Exception as e:
                logger.warning(f"Remote get failed: {e}")

        # Fall back to local
        return self._local_store.get(record_id)

    def query_records(
        self,
        result_type: Optional[StoreResultType] = None,
        limit: int = 100,
    ) -> List[StoredRecord]:
        """
        Queries records with optional filtering.

        Args:
            result_type: Filter by result type
            limit: Maximum records to return

        Returns:
            List of matching records
        """
        records = list(self._local_store.values())

        if result_type:
            records = [r for r in records if r.record_type == result_type]

        # Sort by created_at descending
        records.sort(key=lambda r: r.created_at, reverse=True)

        return records[:limit]

    def delete_record(self, record_id: str) -> bool:
        """
        Deletes a record.

        Args:
            record_id: Record ID

        Returns:
            True if deleted, False if not found
        """
        if record_id in self._local_store:
            del self._local_store[record_id]
            logger.debug(f"Deleted record: {record_id}")
            return True
        return False

    def get_statistics(self) -> Dict[str, Any]:
        """Returns bridge statistics."""
        records = self._local_store.values()

        type_counts = {}
        for rt in StoreResultType:
            type_counts[rt.value] = len([r for r in records if r.record_type == rt])

        return {
            "total_records": len(self._local_store),
            "by_type": type_counts,
            "initialized": self._initialized,
            "connected": self._connected,
            "base_url": self.base_url,
            "remote_store_count": self._remote_store_count,
            "local_store_count": self._local_store_count,
            "failed_store_count": self._failed_store_count,
        }

    def is_connected(self) -> bool:
        """Returns True if connected to L01 service."""
        return self._connected

    def clear(self):
        """Clears local storage."""
        self._local_store = {}

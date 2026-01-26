"""
L01 Bridge - Connects L05 Planning to L01 Data Layer
Path: platform/src/L05_planning/integration/l01_bridge.py
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


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
    ):
        """
        Initialize L01 bridge.

        Args:
            l01_client: Optional L01 client instance
            base_url: Optional base URL for L01 service
        """
        self.l01_client = l01_client
        self.base_url = base_url or "http://localhost:8001"
        self._local_store: Dict[str, StoredRecord] = {}
        self._initialized = False

    async def initialize(self):
        """Initialize connection to L01."""
        if self._initialized:
            return

        # In production, would establish connection to L01
        # For now, use local storage as fallback
        logger.info(f"L01Bridge initialized (base_url={self.base_url})")
        self._initialized = True

    def store_result(
        self,
        result_type: StoreResultType,
        data: Dict[str, Any],
        record_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StoreResult:
        """
        Stores a result in L01 data layer.

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

        try:
            # Create record
            record = StoredRecord(
                record_id=record_id,
                record_type=result_type,
                data=data,
                created_at=now,
                updated_at=now,
                metadata=metadata or {},
            )

            # If L01 client available, use it
            if self.l01_client:
                return self._store_via_client(record)

            # Otherwise use local storage
            self._local_store[record_id] = record

            logger.debug(f"Stored {result_type.value} record: {record_id}")

            return StoreResult(
                success=True,
                record_id=record_id,
                result_type=result_type,
                message=f"Stored {result_type.value} successfully",
            )

        except Exception as e:
            logger.error(f"Failed to store result: {e}")
            return StoreResult(
                success=False,
                record_id=record_id,
                result_type=result_type,
                error=str(e),
            )

    def _store_via_client(self, record: StoredRecord) -> StoreResult:
        """Store record via L01 client."""
        # This would call the actual L01 client
        # For now, simulate success
        self._local_store[record.record_id] = record
        return StoreResult(
            success=True,
            record_id=record.record_id,
            result_type=record.record_type,
            message="Stored via L01 client",
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

    def get_record(self, record_id: str) -> Optional[StoredRecord]:
        """
        Retrieves a record by ID.

        Args:
            record_id: Record ID

        Returns:
            StoredRecord if found, None otherwise
        """
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
            "base_url": self.base_url,
        }

    def clear(self):
        """Clears local storage."""
        self._local_store = {}

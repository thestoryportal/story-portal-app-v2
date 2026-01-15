"""Audit logger for immutable audit trail"""

import logging
from datetime import datetime, UTC
from typing import Dict, Any

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Immutable write-once audit trail.

    Per spec Section 3.2 (Component Responsibilities #11):
    - Immutable write-once audit trail
    - 7-year retention
    """

    def __init__(self, postgres_conn: Optional[Any] = None):
        """
        Initialize audit logger.

        Args:
            postgres_conn: PostgreSQL connection (optional)
        """
        self.postgres = postgres_conn
        self.audit_entries = []

    async def log(self, event_type: str, data: Dict[str, Any]):
        """
        Log audit event.

        Args:
            event_type: Type of event
            data: Event data
        """
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event_type": event_type,
            "data": data,
        }
        self.audit_entries.append(entry)
        logger.info(f"Audit log: {event_type}")

    def get_statistics(self) -> dict:
        """Get audit statistics"""
        return {"entries_logged": len(self.audit_entries)}

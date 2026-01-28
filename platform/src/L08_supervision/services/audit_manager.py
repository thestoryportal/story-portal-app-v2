"""
L08 Supervision Layer - Audit Manager

Immutable audit trail management with cryptographic signing.
All policy decisions, constraint violations, and administrative actions
are logged with tamper-evident signatures.
"""

import logging
import hashlib
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

from ..models.domain import AuditEntry
from ..models.config import SupervisionConfiguration
from ..models.error_codes import ErrorCodes, AuditError
from ..integration.vault_client import VaultClient
from ..integration.l01_bridge import L08Bridge

logger = logging.getLogger(__name__)


class AuditManager:
    """
    Immutable audit trail manager with cryptographic signing.

    Features:
    - Append-only audit logging
    - Cryptographic signing (Vault ECDSA or HMAC fallback)
    - Integrity verification via hash chain
    - Query and filtering capabilities
    """

    def __init__(
        self,
        vault_client: VaultClient,
        l01_bridge: L08Bridge,
        config: SupervisionConfiguration
    ):
        """
        Initialize Audit Manager.

        Args:
            vault_client: Vault client for signing
            l01_bridge: L01 bridge for persistence
            config: Supervision configuration
        """
        self.vault = vault_client
        self.l01 = l01_bridge
        self.config = config

        # In-memory cache for recent entries (for hash chain)
        self._recent_entries: List[AuditEntry] = []
        self._last_hash: str = ""
        self._entry_count: int = 0
        self._initialized: bool = False

        logger.info("AuditManager initialized")

    async def initialize(self) -> None:
        """Initialize audit manager"""
        await self.vault.initialize()
        self._initialized = True
        logger.info("AuditManager ready")

    async def log_action(
        self,
        action: str,
        actor_id: str,
        resource_type: str,
        resource_id: str,
        details: Optional[Dict[str, Any]] = None,
        actor_type: str = "agent",
        parent_audit_id: Optional[str] = None
    ) -> Tuple[Optional[AuditEntry], Optional[str]]:
        """
        Log an action to the immutable audit trail.

        Args:
            action: Action being performed (e.g., "policy_evaluated", "escalation_created")
            actor_id: ID of the actor performing the action
            resource_type: Type of resource affected
            resource_id: ID of the resource affected
            details: Additional action details
            actor_type: Type of actor ("agent", "user", "system")
            parent_audit_id: ID of parent audit entry (for linking)

        Returns:
            Tuple of (AuditEntry, error_message)
        """
        if not self.config.enable_immutable_audit:
            return None, None

        try:
            # Create audit entry
            entry = AuditEntry(
                action=action,
                actor_id=actor_id,
                actor_type=actor_type,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details or {},
                parent_audit_id=parent_audit_id,
                timestamp=datetime.utcnow(),
            )

            # Compute integrity hash (includes previous hash for chain)
            canonical_data = entry.canonical_json()
            chain_data = f"{self._last_hash}:{canonical_data}"
            entry.integrity_hash = await self.vault.compute_hash(chain_data.encode())

            # Sign the entry if signing is enabled
            if self.config.audit_signing_enabled:
                signature_data = f"{canonical_data}:{entry.integrity_hash}"
                entry.signature = await self.vault.sign(
                    signature_data.encode(),
                    self.config.audit_signing_key_id
                )
                entry.signature_algorithm = self.vault.get_algorithm()

            # Persist to L01
            success = await self.l01.write_audit_entry(entry.to_dict())
            if not success:
                return None, f"{ErrorCodes.AUDIT_TRAIL_WRITE_FAILED.value}: Failed to persist audit entry"

            # Update local state
            self._last_hash = entry.integrity_hash
            self._recent_entries.append(entry)
            self._entry_count += 1

            # Keep only recent entries in memory
            if len(self._recent_entries) > 100:
                self._recent_entries = self._recent_entries[-100:]

            logger.debug(
                f"Audit entry created: {entry.audit_id} "
                f"(action={action}, actor={actor_id})"
            )

            return entry, None

        except Exception as e:
            logger.error(f"Failed to create audit entry: {e}")
            return None, f"{ErrorCodes.AUDIT_TRAIL_WRITE_FAILED.value}: {str(e)}"

    async def log_policy_evaluation(
        self,
        decision_id: str,
        agent_id: str,
        verdict: str,
        matched_rules: List[str],
        latency_ms: float
    ) -> Tuple[Optional[AuditEntry], Optional[str]]:
        """Log a policy evaluation decision"""
        return await self.log_action(
            action="policy_evaluated",
            actor_id=agent_id,
            resource_type="policy_decision",
            resource_id=decision_id,
            details={
                "verdict": verdict,
                "matched_rules": matched_rules,
                "latency_ms": latency_ms,
            }
        )

    async def log_constraint_violation(
        self,
        violation_id: str,
        agent_id: str,
        constraint_type: str,
        current_usage: float,
        limit: float
    ) -> Tuple[Optional[AuditEntry], Optional[str]]:
        """Log a constraint violation"""
        return await self.log_action(
            action="constraint_violated",
            actor_id=agent_id,
            resource_type="constraint_violation",
            resource_id=violation_id,
            details={
                "constraint_type": constraint_type,
                "current_usage": current_usage,
                "limit": limit,
            }
        )

    async def log_escalation_created(
        self,
        workflow_id: str,
        decision_id: str,
        reason: str,
        approvers: List[str]
    ) -> Tuple[Optional[AuditEntry], Optional[str]]:
        """Log escalation creation"""
        return await self.log_action(
            action="escalation_created",
            actor_id="system",
            actor_type="system",
            resource_type="escalation",
            resource_id=workflow_id,
            details={
                "decision_id": decision_id,
                "reason": reason,
                "approvers": approvers,
            }
        )

    async def log_escalation_resolved(
        self,
        workflow_id: str,
        approved: bool,
        resolved_by: str,
        mfa_verified: bool
    ) -> Tuple[Optional[AuditEntry], Optional[str]]:
        """Log escalation resolution"""
        return await self.log_action(
            action="escalation_resolved",
            actor_id=resolved_by,
            actor_type="user",
            resource_type="escalation",
            resource_id=workflow_id,
            details={
                "approved": approved,
                "mfa_verified": mfa_verified,
            }
        )

    async def log_anomaly_detected(
        self,
        anomaly_id: str,
        agent_id: str,
        metric_name: str,
        severity: str,
        z_score: float
    ) -> Tuple[Optional[AuditEntry], Optional[str]]:
        """Log anomaly detection"""
        return await self.log_action(
            action="anomaly_detected",
            actor_id=agent_id,
            resource_type="anomaly",
            resource_id=anomaly_id,
            details={
                "metric_name": metric_name,
                "severity": severity,
                "z_score": z_score,
            }
        )

    async def query(
        self,
        actor_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[AuditEntry], Optional[str]]:
        """
        Query audit log with filters.

        Args:
            actor_id: Filter by actor ID
            action: Filter by action
            resource_type: Filter by resource type
            resource_id: Filter by resource ID
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum results to return
            offset: Offset for pagination

        Returns:
            Tuple of (list of AuditEntry, error_message)
        """
        try:
            results = await self.l01.query_audit_log(
                actor_id=actor_id,
                action=action,
                resource_type=resource_type,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
                offset=offset
            )

            entries = []
            for data in results:
                entry = AuditEntry(
                    audit_id=data.get("audit_id", ""),
                    action=data.get("action", ""),
                    actor_id=data.get("actor_id", ""),
                    actor_type=data.get("actor_type", ""),
                    resource_type=data.get("resource_type", ""),
                    resource_id=data.get("resource_id", ""),
                    details=data.get("details", {}),
                    parent_audit_id=data.get("parent_audit_id"),
                    signature=data.get("signature", ""),
                    signature_algorithm=data.get("signature_algorithm", ""),
                    timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.utcnow(),
                    integrity_hash=data.get("integrity_hash", ""),
                )
                entries.append(entry)

            return entries, None

        except Exception as e:
            logger.error(f"Failed to query audit log: {e}")
            return [], f"{ErrorCodes.AUDIT_QUERY_FAILED.value}: {str(e)}"

    async def get_entry(self, audit_id: str) -> Tuple[Optional[AuditEntry], Optional[str]]:
        """Get a specific audit entry by ID"""
        try:
            data = await self.l01.get_audit_entry(audit_id)
            if not data:
                return None, f"{ErrorCodes.AUDIT_ENTRY_NOT_FOUND.value}: Entry {audit_id} not found"

            entry = AuditEntry(
                audit_id=data.get("audit_id", ""),
                action=data.get("action", ""),
                actor_id=data.get("actor_id", ""),
                actor_type=data.get("actor_type", ""),
                resource_type=data.get("resource_type", ""),
                resource_id=data.get("resource_id", ""),
                details=data.get("details", {}),
                parent_audit_id=data.get("parent_audit_id"),
                signature=data.get("signature", ""),
                signature_algorithm=data.get("signature_algorithm", ""),
                timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.utcnow(),
                integrity_hash=data.get("integrity_hash", ""),
            )
            return entry, None

        except Exception as e:
            logger.error(f"Failed to get audit entry: {e}")
            return None, str(e)

    async def verify_entry(self, entry: AuditEntry) -> Tuple[bool, Optional[str]]:
        """
        Verify an audit entry's signature.

        Args:
            entry: Audit entry to verify

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not entry.signature:
            return True, None  # No signature to verify

        try:
            canonical_data = entry.canonical_json()
            signature_data = f"{canonical_data}:{entry.integrity_hash}"

            is_valid = await self.vault.verify(
                signature_data.encode(),
                entry.signature,
                self.config.audit_signing_key_id
            )

            if not is_valid:
                return False, f"{ErrorCodes.AUDIT_SIGNATURE_INVALID.value}: Signature verification failed"

            return True, None

        except Exception as e:
            logger.error(f"Failed to verify audit entry: {e}")
            return False, str(e)

    async def verify_chain(
        self,
        start_audit_id: Optional[str] = None,
        end_audit_id: Optional[str] = None
    ) -> Tuple[bool, int, Optional[str]]:
        """
        Verify integrity of audit chain.

        Args:
            start_audit_id: Start of range to verify
            end_audit_id: End of range to verify

        Returns:
            Tuple of (is_valid, entries_checked, first_invalid_id)
        """
        # For now, verify recent entries in memory
        entries_checked = 0
        prev_hash = ""

        for entry in self._recent_entries:
            entries_checked += 1

            # Verify signature
            is_valid, error = await self.verify_entry(entry)
            if not is_valid:
                return False, entries_checked, entry.audit_id

            # Verify hash chain
            canonical_data = entry.canonical_json()
            chain_data = f"{prev_hash}:{canonical_data}"
            expected_hash = await self.vault.compute_hash(chain_data.encode())

            if entry.integrity_hash != expected_hash:
                return False, entries_checked, entry.audit_id

            prev_hash = entry.integrity_hash

        return True, entries_checked, None

    def get_stats(self) -> Dict[str, Any]:
        """Get audit manager statistics"""
        return {
            "total_entries": self._entry_count,
            "cached_entries": len(self._recent_entries),
            "signing_enabled": self.config.audit_signing_enabled,
            "algorithm": self.vault.get_algorithm(),
            "initialized": self._initialized,
        }

    async def health_check(self) -> Dict[str, Any]:
        """Health check for audit manager"""
        vault_health = await self.vault.health_check()
        return {
            "status": "healthy" if self._initialized else "not_initialized",
            "vault": vault_health,
            "stats": self.get_stats(),
        }

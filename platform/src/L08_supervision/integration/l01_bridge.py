"""
L08 Supervision Layer - L01 Data Layer Bridge

Bridge between L08 Supervision Layer and L01 Data Layer for persistent storage
of policies, constraints, escalations, and audit entries.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class L08Bridge:
    """
    Bridge between L08 Supervision Layer and L01 Data Layer.

    Responsibilities:
    - Store and retrieve policy definitions
    - Persist constraint configurations
    - Store escalation workflows
    - Write immutable audit entries
    - Query historical data
    """

    def __init__(
        self,
        l01_base_url: str = "http://localhost:8001",
        api_key: Optional[str] = None,
        timeout_seconds: int = 30
    ):
        """
        Initialize L08 bridge.

        Args:
            l01_base_url: Base URL for L01 Data Layer API
            api_key: API key for L01 authentication
            timeout_seconds: Request timeout
        """
        self.api_key = api_key or os.getenv("L01_API_KEY", "dev_key_local_ONLY")
        self.l01_base_url = l01_base_url
        self.timeout_seconds = timeout_seconds
        self.enabled = True
        self._initialized = False

        # In-memory fallback for development (when L01 is unavailable)
        self._memory_store: Dict[str, List[Dict[str, Any]]] = {
            "policies": [],
            "constraints": [],
            "escalations": [],
            "audit_entries": [],
            "anomalies": [],
        }

        logger.info(f"L08Bridge initialized with base_url={l01_base_url}")

    async def initialize(self) -> None:
        """Initialize bridge and verify L01 connectivity"""
        try:
            # In production, would verify L01 connectivity
            # For now, just mark as initialized
            self._initialized = True
            logger.info("L08Bridge initialized successfully")
        except Exception as e:
            logger.warning(f"L08Bridge using in-memory fallback: {e}")
            self._initialized = True

    # =========================================================================
    # Policy Operations
    # =========================================================================

    async def store_policy(self, policy: Dict[str, Any]) -> bool:
        """
        Store a policy definition in L01.

        Args:
            policy: Policy definition as dictionary

        Returns:
            True if stored successfully
        """
        if not self.enabled:
            return False

        try:
            # In production, would call L01 API
            # POST /api/supervision/policies
            self._memory_store["policies"].append(policy)
            logger.info(f"Stored policy {policy.get('policy_id')}")
            return True
        except Exception as e:
            logger.error(f"Failed to store policy: {e}")
            return False

    async def get_policy(self, policy_id: str) -> Optional[Dict[str, Any]]:
        """Get policy by ID"""
        try:
            for policy in self._memory_store["policies"]:
                if policy.get("policy_id") == policy_id:
                    return policy
            return None
        except Exception as e:
            logger.error(f"Failed to get policy: {e}")
            return None

    async def get_active_policies(self, scope: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all active policies, optionally filtered by scope"""
        try:
            policies = [
                p for p in self._memory_store["policies"]
                if p.get("active", False)
            ]
            if scope:
                policies = [p for p in policies if p.get("scope") == scope]
            return policies
        except Exception as e:
            logger.error(f"Failed to get active policies: {e}")
            return []

    async def update_policy(self, policy_id: str, updates: Dict[str, Any]) -> bool:
        """Update policy fields"""
        try:
            for policy in self._memory_store["policies"]:
                if policy.get("policy_id") == policy_id:
                    policy.update(updates)
                    policy["updated_at"] = datetime.utcnow().isoformat()
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to update policy: {e}")
            return False

    # =========================================================================
    # Constraint Operations
    # =========================================================================

    async def store_constraint(self, constraint: Dict[str, Any]) -> bool:
        """Store a constraint definition"""
        try:
            self._memory_store["constraints"].append(constraint)
            logger.info(f"Stored constraint {constraint.get('constraint_id')}")
            return True
        except Exception as e:
            logger.error(f"Failed to store constraint: {e}")
            return False

    async def get_constraint(self, constraint_id: str) -> Optional[Dict[str, Any]]:
        """Get constraint by ID"""
        try:
            for constraint in self._memory_store["constraints"]:
                if constraint.get("constraint_id") == constraint_id:
                    return constraint
            return None
        except Exception as e:
            logger.error(f"Failed to get constraint: {e}")
            return None

    async def get_constraints_for_agent(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get all constraints applicable to an agent"""
        try:
            return [
                c for c in self._memory_store["constraints"]
                if c.get("agent_id") == agent_id or c.get("agent_id") is None
            ]
        except Exception as e:
            logger.error(f"Failed to get constraints for agent: {e}")
            return []

    # =========================================================================
    # Escalation Operations
    # =========================================================================

    async def create_escalation(self, escalation: Dict[str, Any]) -> bool:
        """Create an escalation workflow"""
        try:
            self._memory_store["escalations"].append(escalation)
            logger.info(f"Created escalation {escalation.get('workflow_id')}")
            return True
        except Exception as e:
            logger.error(f"Failed to create escalation: {e}")
            return False

    async def get_escalation(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get escalation by workflow ID"""
        try:
            for escalation in self._memory_store["escalations"]:
                if escalation.get("workflow_id") == workflow_id:
                    return escalation
            return None
        except Exception as e:
            logger.error(f"Failed to get escalation: {e}")
            return None

    async def update_escalation(self, workflow_id: str, updates: Dict[str, Any]) -> bool:
        """Update escalation workflow"""
        try:
            for escalation in self._memory_store["escalations"]:
                if escalation.get("workflow_id") == workflow_id:
                    escalation.update(updates)
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to update escalation: {e}")
            return False

    async def get_pending_escalations(self) -> List[Dict[str, Any]]:
        """Get all pending escalations"""
        try:
            return [
                e for e in self._memory_store["escalations"]
                if e.get("status") in ["PENDING", "NOTIFIED", "WAITING"]
            ]
        except Exception as e:
            logger.error(f"Failed to get pending escalations: {e}")
            return []

    # =========================================================================
    # Audit Operations
    # =========================================================================

    async def write_audit_entry(self, entry: Dict[str, Any]) -> bool:
        """
        Write an audit entry (append-only).

        Args:
            entry: Audit entry as dictionary

        Returns:
            True if written successfully
        """
        try:
            self._memory_store["audit_entries"].append(entry)
            logger.debug(f"Wrote audit entry {entry.get('audit_id')}")
            return True
        except Exception as e:
            logger.error(f"Failed to write audit entry: {e}")
            return False

    async def query_audit_log(
        self,
        actor_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Query audit log with filters"""
        try:
            results = self._memory_store["audit_entries"]

            if actor_id:
                results = [e for e in results if e.get("actor_id") == actor_id]
            if action:
                results = [e for e in results if e.get("action") == action]
            if resource_type:
                results = [e for e in results if e.get("resource_type") == resource_type]

            # Sort by timestamp descending
            results = sorted(
                results,
                key=lambda x: x.get("timestamp", ""),
                reverse=True
            )

            return results[offset:offset + limit]
        except Exception as e:
            logger.error(f"Failed to query audit log: {e}")
            return []

    async def get_audit_entry(self, audit_id: str) -> Optional[Dict[str, Any]]:
        """Get audit entry by ID"""
        try:
            for entry in self._memory_store["audit_entries"]:
                if entry.get("audit_id") == audit_id:
                    return entry
            return None
        except Exception as e:
            logger.error(f"Failed to get audit entry: {e}")
            return None

    # =========================================================================
    # Anomaly Operations
    # =========================================================================

    async def store_anomaly(self, anomaly: Dict[str, Any]) -> bool:
        """Store a detected anomaly"""
        try:
            self._memory_store["anomalies"].append(anomaly)
            logger.info(f"Stored anomaly {anomaly.get('anomaly_id')}")
            return True
        except Exception as e:
            logger.error(f"Failed to store anomaly: {e}")
            return False

    async def get_anomalies(
        self,
        agent_id: Optional[str] = None,
        severity: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get anomalies with filters"""
        try:
            results = self._memory_store["anomalies"]

            if agent_id:
                results = [a for a in results if a.get("agent_id") == agent_id]
            if severity:
                results = [a for a in results if a.get("severity") == severity]
            if acknowledged is not None:
                results = [a for a in results if a.get("acknowledged") == acknowledged]

            return results[-limit:]
        except Exception as e:
            logger.error(f"Failed to get anomalies: {e}")
            return []

    # =========================================================================
    # Agent Context Operations
    # =========================================================================

    async def get_agent_context(self, agent_id: str) -> Dict[str, Any]:
        """
        Get agent context for policy evaluation.

        Returns agent metadata, team, department, permissions, etc.
        """
        # In production, would fetch from L01
        # For now, return mock context
        return {
            "agent_id": agent_id,
            "team": "default",
            "department": "engineering",
            "permissions": [],
            "created_at": datetime.utcnow().isoformat(),
        }

    # =========================================================================
    # Health & Lifecycle
    # =========================================================================

    async def health_check(self) -> Dict[str, Any]:
        """Check L01 connectivity"""
        return {
            "status": "healthy" if self._initialized else "not_initialized",
            "enabled": self.enabled,
            "l01_url": self.l01_base_url,
            "in_memory_mode": True,  # Always in-memory for now
        }

    async def cleanup(self) -> None:
        """Cleanup resources"""
        logger.info("L08Bridge cleanup complete")

    def is_connected(self) -> bool:
        """Check if bridge is connected and ready"""
        return self._initialized and self.enabled

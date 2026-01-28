"""
L08 Supervision Layer - Main Supervision Service

Unified service orchestrating all supervision components.
Provides single entry point for policy evaluation, constraint
enforcement, anomaly detection, and escalation management.
"""

import logging
from typing import Optional, Dict, Any, List, Tuple

from ..models.domain import (
    PolicyDefinition,
    PolicyDecision,
    PolicyVerdict,
    Constraint,
    ConstraintViolation,
    Anomaly,
    EscalationWorkflow,
    AuditEntry,
)
from ..models.config import SupervisionConfiguration
from ..integration.l01_bridge import L08Bridge
from ..integration.l10_bridge import L10Bridge
from ..integration.vault_client import VaultClient
from ..integration.redis_client import RedisRateLimiter

from .policy_engine import PolicyEngine
from .constraint_enforcer import ConstraintEnforcer
from .anomaly_detector import AnomalyDetector
from .escalation_orchestrator import EscalationOrchestrator
from .audit_manager import AuditManager
from .access_control import AccessControlManager
from .decision_explainer import DecisionExplainer
from .compliance_monitor import ComplianceMonitor

logger = logging.getLogger(__name__)


class SupervisionService:
    """
    Main supervision service orchestrating all L08 components.

    This service provides:
    - Unified policy evaluation with automatic escalation
    - Constraint enforcement with rate limiting
    - Anomaly detection with baseline management
    - Escalation workflow management
    - Comprehensive audit logging
    - Compliance monitoring
    """

    def __init__(self, config: Optional[SupervisionConfiguration] = None):
        """
        Initialize Supervision Service.

        Args:
            config: Optional configuration (defaults from environment)
        """
        self.config = config or SupervisionConfiguration.from_env()

        # Integration components
        self.l01_bridge = L08Bridge(
            l01_base_url=self.config.l01_base_url,
            timeout_seconds=self.config.l01_timeout_seconds,
        )
        self.l10_bridge = L10Bridge(
            l10_base_url=self.config.l10_base_url,
            timeout_seconds=self.config.l10_timeout_seconds,
        )
        self.vault_client = VaultClient(
            vault_url=self.config.vault_url,
            mount_path=self.config.vault_mount_path,
        )
        self.redis_limiter = RedisRateLimiter(
            redis_url=self.config.redis_url,
        )

        # Core services
        self.audit_manager = AuditManager(
            vault_client=self.vault_client,
            l01_bridge=self.l01_bridge,
            config=self.config,
        )
        self.policy_engine = PolicyEngine(
            audit_manager=self.audit_manager,
            l01_bridge=self.l01_bridge,
            config=self.config,
        )
        self.constraint_enforcer = ConstraintEnforcer(
            redis_limiter=self.redis_limiter,
            l01_bridge=self.l01_bridge,
            audit_manager=self.audit_manager,
            config=self.config,
        )
        self.anomaly_detector = AnomalyDetector(
            l01_bridge=self.l01_bridge,
            audit_manager=self.audit_manager,
            config=self.config,
        )
        self.escalation_orchestrator = EscalationOrchestrator(
            l01_bridge=self.l01_bridge,
            l10_bridge=self.l10_bridge,
            audit_manager=self.audit_manager,
            config=self.config,
        )
        self.access_control = AccessControlManager(config=self.config)
        self.decision_explainer = DecisionExplainer()
        self.compliance_monitor = ComplianceMonitor(config=self.config)

        self._initialized = False
        logger.info("SupervisionService created")

    async def initialize(self) -> None:
        """Initialize all services"""
        logger.info("Initializing SupervisionService...")

        await self.l01_bridge.initialize()
        await self.vault_client.initialize()
        await self.redis_limiter.initialize()
        await self.audit_manager.initialize()
        await self.anomaly_detector.initialize()
        await self.escalation_orchestrator.initialize()

        self._initialized = True
        logger.info("SupervisionService initialized")

    # =========================================================================
    # Policy Operations
    # =========================================================================

    async def evaluate_request(
        self,
        agent_id: str,
        operation: str,
        resource: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[PolicyDecision], Optional[str]]:
        """
        Evaluate an agent request against policies and constraints.

        This is the main entry point for supervision checks. It:
        1. Evaluates policies
        2. Checks constraints
        3. Creates escalation if needed
        4. Records to compliance monitor

        Args:
            agent_id: Agent making the request
            operation: Operation being performed
            resource: Resource being accessed
            context: Additional context

        Returns:
            Tuple of (PolicyDecision, error message)
        """
        request_context = {
            "operation": operation,
            "resource": resource,
            **(context or {}),
        }

        # Evaluate policies
        decision, error = await self.policy_engine.evaluate(agent_id, request_context)
        if error:
            return None, error

        # Record to compliance monitor
        await self.compliance_monitor.record_policy_decision(decision)

        # Handle escalation
        if decision.verdict == PolicyVerdict.ESCALATE:
            escalation, _ = await self.escalation_orchestrator.create_escalation(
                decision_id=decision.decision_id,
                reason=decision.explanation,
                context=request_context,
                approvers=[],  # Would be determined by escalation policies
            )
            if escalation:
                # Add escalation info to decision
                decision.request_context["escalation"] = {
                    "workflow_id": escalation.workflow_id,
                    "status": escalation.status.value,
                }

        return decision, None

    async def register_policy(
        self,
        policy: PolicyDefinition
    ) -> Tuple[Optional[PolicyDefinition], Optional[str]]:
        """Register a new policy"""
        return await self.policy_engine.register_policy(policy)

    async def deploy_policy(self, policy_id: str) -> Tuple[bool, Optional[str]]:
        """Deploy a policy to active set"""
        return await self.policy_engine.deploy_policy(policy_id)

    # =========================================================================
    # Constraint Operations
    # =========================================================================

    async def check_rate_limit(
        self,
        agent_id: str,
        constraint_id: str,
        requested: int = 1
    ) -> Tuple[bool, Optional[str]]:
        """Check rate limit constraint"""
        result = await self.constraint_enforcer.check_rate_limit(
            agent_id, constraint_id, requested
        )

        # Record violations
        if not result[0]:
            violations = self.constraint_enforcer.get_violations(agent_id, limit=1)
            if violations:
                await self.compliance_monitor.record_constraint_violation(violations[-1])

        return result

    async def create_constraint(
        self,
        constraint: Constraint
    ) -> Tuple[Optional[Constraint], Optional[str]]:
        """Create a new constraint"""
        return await self.constraint_enforcer.create_constraint(constraint)

    # =========================================================================
    # Anomaly Detection
    # =========================================================================

    async def record_metric(
        self,
        agent_id: str,
        metric_name: str,
        value: float,
        detect: bool = True
    ) -> Tuple[List[Anomaly], Optional[str]]:
        """
        Record a metric observation and optionally detect anomalies.

        Args:
            agent_id: Agent identifier
            metric_name: Metric name
            value: Observed value
            detect: Whether to run detection

        Returns:
            Tuple of (detected anomalies, error message)
        """
        # Record observation for baseline
        await self.anomaly_detector.record_observation(agent_id, metric_name, value)

        if detect:
            anomalies, error = await self.anomaly_detector.detect(agent_id, metric_name, value)

            # Record anomalies to compliance monitor
            for anomaly in anomalies:
                await self.compliance_monitor.record_anomaly(anomaly)

            return anomalies, error

        return [], None

    async def set_baseline(
        self,
        agent_id: str,
        metric_name: str,
        values: List[float]
    ) -> Tuple[bool, Optional[str]]:
        """Set baseline from historical values"""
        return await self.anomaly_detector.set_baseline(agent_id, metric_name, values)

    # =========================================================================
    # Escalation Operations
    # =========================================================================

    async def create_escalation(
        self,
        decision_id: str,
        reason: str,
        context: Dict[str, Any],
        approvers: List[str]
    ) -> Tuple[Optional[EscalationWorkflow], Optional[str]]:
        """Create a manual escalation"""
        return await self.escalation_orchestrator.create_escalation(
            decision_id=decision_id,
            reason=reason,
            context=context,
            approvers=approvers,
        )

    async def resolve_escalation(
        self,
        workflow_id: str,
        approved: bool,
        approver_id: str,
        notes: str = "",
        mfa_token: Optional[str] = None
    ) -> Tuple[Optional[EscalationWorkflow], Optional[str]]:
        """Resolve an escalation"""
        return await self.escalation_orchestrator.resolve(
            workflow_id=workflow_id,
            approved=approved,
            approver_id=approver_id,
            notes=notes,
            mfa_token=mfa_token,
        )

    async def get_pending_escalations(self) -> List[EscalationWorkflow]:
        """Get all pending escalations"""
        return await self.escalation_orchestrator.get_pending_escalations()

    # =========================================================================
    # Audit Operations
    # =========================================================================

    async def query_audit_log(
        self,
        actor_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 100
    ) -> Tuple[List[AuditEntry], Optional[str]]:
        """Query audit log"""
        return await self.audit_manager.query(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            limit=limit,
        )

    async def verify_audit_chain(self) -> Tuple[bool, int, Optional[str]]:
        """Verify audit trail integrity"""
        return await self.audit_manager.verify_chain()

    # =========================================================================
    # Compliance Operations
    # =========================================================================

    async def get_compliance_status(self, agent_id: str) -> Dict[str, Any]:
        """Get compliance status for an agent"""
        status = await self.compliance_monitor.get_compliance_status(agent_id)
        return status.to_dict()

    async def get_compliance_report(
        self,
        entity_id: Optional[str] = None,
        period_hours: int = 24
    ) -> Dict[str, Any]:
        """Generate compliance report"""
        return await self.compliance_monitor.get_compliance_report(
            entity_id=entity_id,
            period_hours=period_hours,
        )

    # =========================================================================
    # Health & Stats
    # =========================================================================

    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        return {
            "initialized": self._initialized,
            "policy_engine": self.policy_engine.get_stats(),
            "constraint_enforcer": self.constraint_enforcer.get_stats(),
            "anomaly_detector": self.anomaly_detector.get_stats(),
            "escalation_orchestrator": self.escalation_orchestrator.get_stats(),
            "audit_manager": self.audit_manager.get_stats(),
            "compliance_monitor": self.compliance_monitor.get_stats(),
        }

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        components = {
            "l01_bridge": await self.l01_bridge.health_check(),
            "vault_client": await self.vault_client.health_check(),
            "redis_limiter": await self.redis_limiter.health_check(),
            "policy_engine": await self.policy_engine.health_check(),
            "constraint_enforcer": await self.constraint_enforcer.health_check(),
            "anomaly_detector": await self.anomaly_detector.health_check(),
            "escalation_orchestrator": await self.escalation_orchestrator.health_check(),
            "audit_manager": await self.audit_manager.health_check(),
            "compliance_monitor": await self.compliance_monitor.health_check(),
        }

        # Determine overall status
        all_healthy = all(
            c.get("status") == "healthy"
            for c in components.values()
        )

        return {
            "status": "healthy" if all_healthy else "degraded",
            "service": "l08-supervision",
            "version": "1.0.0",
            "initialized": self._initialized,
            "components": components,
        }

    async def cleanup(self) -> None:
        """Cleanup all resources"""
        logger.info("Cleaning up SupervisionService...")
        await self.escalation_orchestrator.cleanup()
        await self.redis_limiter.close()
        await self.vault_client.close()
        await self.l01_bridge.cleanup()
        await self.l10_bridge.cleanup()
        logger.info("SupervisionService cleanup complete")

"""
L08 Supervision Layer - Policy Engine

Policy evaluation engine with expression evaluation, caching,
and audit integration. Implements deny-wins rule for conflict resolution.
"""

import ast
import time
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from functools import lru_cache

from ..models.domain import (
    PolicyRule,
    PolicyDefinition,
    PolicyDecision,
    PolicyVerdict,
)
from ..models.config import SupervisionConfiguration
from ..models.error_codes import ErrorCodes, PolicyError
from ..integration.l01_bridge import L08Bridge
from .audit_manager import AuditManager

logger = logging.getLogger(__name__)


class PolicyExpressionEvaluator:
    """
    Safe expression evaluator for policy conditions.

    Evaluates conditions like:
    - agent.team == "datascience"
    - resource.sensitive == True
    - context.business_hours and resource.type in ["dataset", "model"]

    Uses Python AST for safe evaluation without exec/eval.
    """

    ALLOWED_COMPARISONS = {ast.Eq, ast.NotEq, ast.Lt, ast.Gt, ast.LtE, ast.GtE}
    ALLOWED_BOOL_OPS = {ast.And, ast.Or}
    ALLOWED_UNARY_OPS = {ast.Not}
    ALLOWED_MEMBERSHIP = {ast.In, ast.NotIn}

    def __init__(self):
        self._cache: Dict[str, ast.AST] = {}

    def evaluate(self, condition: str, context: Dict[str, Any]) -> bool:
        """
        Evaluate a condition expression against a context.

        Args:
            condition: Expression string (e.g., "agent.team == 'datascience'")
            context: Context dictionary for variable resolution

        Returns:
            True if condition evaluates to True, False otherwise

        Raises:
            PolicyError: If condition is invalid or contains unsafe operations
        """
        if not condition or condition.strip() == "":
            return True  # Empty condition always matches

        try:
            # Parse or get cached AST
            if condition not in self._cache:
                tree = ast.parse(condition, mode='eval')
                self._validate_ast(tree)
                self._cache[condition] = tree
            else:
                tree = self._cache[condition]

            return self._eval_node(tree.body, context)

        except PolicyError:
            raise
        except Exception as e:
            raise PolicyError(
                ErrorCodes.POLICY_INVALID_CONDITION,
                f"Invalid condition: {condition}",
                {"error": str(e)}
            )

    def _validate_ast(self, tree: ast.AST) -> None:
        """Validate AST contains only safe operations"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                raise PolicyError(
                    ErrorCodes.POLICY_INVALID_CONDITION,
                    "Function calls not allowed in policy conditions"
                )
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                raise PolicyError(
                    ErrorCodes.POLICY_INVALID_CONDITION,
                    "Imports not allowed in policy conditions"
                )

    def _eval_node(self, node: ast.AST, context: Dict[str, Any]) -> Any:
        """Recursively evaluate an AST node"""
        if isinstance(node, ast.BoolOp):
            return self._eval_bool_op(node, context)
        elif isinstance(node, ast.UnaryOp):
            return self._eval_unary_op(node, context)
        elif isinstance(node, ast.Compare):
            return self._eval_compare(node, context)
        elif isinstance(node, ast.Attribute):
            return self._eval_attribute(node, context)
        elif isinstance(node, ast.Name):
            return self._eval_name(node, context)
        elif isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.List):
            return [self._eval_node(e, context) for e in node.elts]
        elif isinstance(node, ast.Tuple):
            return tuple(self._eval_node(e, context) for e in node.elts)
        elif isinstance(node, ast.Subscript):
            return self._eval_subscript(node, context)
        else:
            raise PolicyError(
                ErrorCodes.POLICY_INVALID_CONDITION,
                f"Unsupported expression type: {type(node).__name__}"
            )

    def _eval_bool_op(self, node: ast.BoolOp, context: Dict[str, Any]) -> bool:
        """Evaluate boolean operations (and, or)"""
        if type(node.op) not in self.ALLOWED_BOOL_OPS:
            raise PolicyError(
                ErrorCodes.POLICY_INVALID_CONDITION,
                f"Unsupported boolean operator: {type(node.op).__name__}"
            )

        if isinstance(node.op, ast.And):
            return all(self._eval_node(v, context) for v in node.values)
        else:  # Or
            return any(self._eval_node(v, context) for v in node.values)

    def _eval_unary_op(self, node: ast.UnaryOp, context: Dict[str, Any]) -> Any:
        """Evaluate unary operations (not)"""
        if type(node.op) not in self.ALLOWED_UNARY_OPS:
            raise PolicyError(
                ErrorCodes.POLICY_INVALID_CONDITION,
                f"Unsupported unary operator: {type(node.op).__name__}"
            )

        operand = self._eval_node(node.operand, context)
        if isinstance(node.op, ast.Not):
            return not operand
        return operand

    def _eval_compare(self, node: ast.Compare, context: Dict[str, Any]) -> bool:
        """Evaluate comparison operations"""
        left = self._eval_node(node.left, context)

        for op, comparator in zip(node.ops, node.comparators):
            right = self._eval_node(comparator, context)

            if isinstance(op, ast.Eq):
                result = left == right
            elif isinstance(op, ast.NotEq):
                result = left != right
            elif isinstance(op, ast.Lt):
                result = left < right
            elif isinstance(op, ast.Gt):
                result = left > right
            elif isinstance(op, ast.LtE):
                result = left <= right
            elif isinstance(op, ast.GtE):
                result = left >= right
            elif isinstance(op, ast.In):
                result = left in right
            elif isinstance(op, ast.NotIn):
                result = left not in right
            else:
                raise PolicyError(
                    ErrorCodes.POLICY_INVALID_CONDITION,
                    f"Unsupported comparison operator: {type(op).__name__}"
                )

            if not result:
                return False
            left = right

        return True

    def _eval_attribute(self, node: ast.Attribute, context: Dict[str, Any]) -> Any:
        """Evaluate attribute access (e.g., agent.team)"""
        value = self._eval_node(node.value, context)
        if isinstance(value, dict):
            return value.get(node.attr)
        return getattr(value, node.attr, None)

    def _eval_name(self, node: ast.Name, context: Dict[str, Any]) -> Any:
        """Evaluate variable name lookup"""
        if node.id in context:
            return context[node.id]
        # Check for boolean literals
        if node.id == "True":
            return True
        if node.id == "False":
            return False
        if node.id == "None":
            return None
        return None

    def _eval_subscript(self, node: ast.Subscript, context: Dict[str, Any]) -> Any:
        """Evaluate subscript access (e.g., context["key"])"""
        value = self._eval_node(node.value, context)
        key = self._eval_node(node.slice, context)
        if isinstance(value, dict):
            return value.get(key)
        elif isinstance(value, (list, tuple)):
            return value[key] if 0 <= key < len(value) else None
        return None

    def validate(self, condition: str) -> None:
        """
        Validate a condition expression without evaluating it.

        Args:
            condition: Expression string to validate

        Raises:
            PolicyError: If condition is invalid or contains unsafe operations
        """
        if not condition or condition.strip() == "":
            return  # Empty condition is valid

        try:
            tree = ast.parse(condition, mode='eval')
            self._validate_ast(tree)
        except PolicyError:
            raise
        except SyntaxError as e:
            raise PolicyError(
                ErrorCodes.POLICY_INVALID_CONDITION,
                f"Syntax error in condition: {condition}",
                {"error": str(e)}
            )
        except Exception as e:
            raise PolicyError(
                ErrorCodes.POLICY_INVALID_CONDITION,
                f"Invalid condition: {condition}",
                {"error": str(e)}
            )


class PolicyEngine:
    """
    Policy evaluation engine with caching and audit integration.

    Features:
    - Expression-based policy conditions
    - Deny-wins conflict resolution
    - LRU caching for performance
    - Automatic audit logging
    - <100ms p99 latency target
    """

    def __init__(
        self,
        audit_manager: AuditManager,
        l01_bridge: L08Bridge,
        config: SupervisionConfiguration
    ):
        """
        Initialize Policy Engine.

        Args:
            audit_manager: Audit manager for logging decisions
            l01_bridge: L01 bridge for policy storage
            config: Supervision configuration
        """
        self.audit = audit_manager
        self.l01 = l01_bridge
        self.config = config
        self.evaluator = PolicyExpressionEvaluator()

        # In-memory policy cache
        self._policies: Dict[str, PolicyDefinition] = {}
        self._active_policies: List[PolicyDefinition] = []
        self._cache_timestamp: datetime = datetime.utcnow()

        # Metrics
        self._evaluation_count: int = 0
        self._cache_hits: int = 0
        self._cache_misses: int = 0

        logger.info("PolicyEngine initialized")

    async def register_policy(
        self,
        policy: PolicyDefinition
    ) -> Tuple[Optional[PolicyDefinition], Optional[str]]:
        """
        Register a policy definition.

        Args:
            policy: Policy definition to register

        Returns:
            Tuple of (registered policy, error message)
        """
        try:
            # Store in L01
            success = await self.l01.store_policy(policy.to_dict())
            if not success:
                return None, f"{ErrorCodes.POLICY_DEPLOY_FAILED.value}: Failed to store policy"

            # Update local cache
            self._policies[policy.policy_id] = policy

            # Log to audit trail
            await self.audit.log_action(
                action="policy_registered",
                actor_id="system",
                actor_type="system",
                resource_type="policy",
                resource_id=policy.policy_id,
                details={
                    "name": policy.name,
                    "version": policy.version,
                    "rules_count": len(policy.rules),
                }
            )

            logger.info(f"Registered policy {policy.policy_id}: {policy.name}")
            return policy, None

        except Exception as e:
            logger.error(f"Failed to register policy: {e}")
            return None, str(e)

    async def deploy_policy(self, policy_id: str) -> Tuple[bool, Optional[str]]:
        """
        Deploy a policy to the active set.

        Args:
            policy_id: Policy ID to deploy

        Returns:
            Tuple of (success, error message)
        """
        try:
            policy = self._policies.get(policy_id)
            if not policy:
                # Try loading from L01
                data = await self.l01.get_policy(policy_id)
                if not data:
                    return False, f"{ErrorCodes.POLICY_NOT_FOUND.value}: Policy {policy_id} not found"
                policy = self._dict_to_policy(data)
                self._policies[policy_id] = policy

            policy.active = True
            policy.updated_at = datetime.utcnow()

            # Update in L01
            await self.l01.update_policy(policy_id, {"active": True})

            # Refresh active policies
            await self._refresh_active_policies()

            # Log to audit trail
            await self.audit.log_action(
                action="policy_deployed",
                actor_id="system",
                actor_type="system",
                resource_type="policy",
                resource_id=policy_id,
            )

            logger.info(f"Deployed policy {policy_id}")
            return True, None

        except Exception as e:
            logger.error(f"Failed to deploy policy: {e}")
            return False, str(e)

    async def evaluate(
        self,
        agent_id: str,
        request_context: Dict[str, Any]
    ) -> Tuple[Optional[PolicyDecision], Optional[str]]:
        """
        Evaluate request against active policies.

        Args:
            agent_id: Agent making the request
            request_context: Request context including operation, resource, etc.

        Returns:
            Tuple of (PolicyDecision, error message)
        """
        start_time = time.perf_counter()

        try:
            # Load agent context
            agent_context = await self._load_agent_context(agent_id)

            # Build full evaluation context
            full_context = {
                "agent": agent_context,
                **request_context,
            }

            # Refresh active policies if cache expired
            if self._is_cache_expired():
                await self._refresh_active_policies()
                self._cache_misses += 1
            else:
                self._cache_hits += 1

            # Evaluate rules (deny-wins)
            verdict = PolicyVerdict.ALLOW
            matched_rules: List[str] = []
            matched_rule_details: List[Dict[str, Any]] = []

            for policy in self._active_policies:
                # Sort rules by priority (higher priority first)
                sorted_rules = sorted(
                    policy.rules,
                    key=lambda r: r.priority,
                    reverse=True
                )

                for rule in sorted_rules:
                    if not rule.enabled:
                        continue

                    try:
                        if self.evaluator.evaluate(rule.condition, full_context):
                            matched_rules.append(rule.rule_id)
                            matched_rule_details.append({
                                "rule_id": rule.rule_id,
                                "policy_id": policy.policy_id,
                                "policy_name": policy.name,
                                "rule_name": rule.name,
                                "action": rule.action.value,
                            })

                            # Apply deny-wins rule
                            if self.config.deny_wins_rule:
                                if rule.action == PolicyVerdict.DENY:
                                    verdict = PolicyVerdict.DENY
                                elif rule.action == PolicyVerdict.ESCALATE and verdict != PolicyVerdict.DENY:
                                    verdict = PolicyVerdict.ESCALATE
                                elif rule.action == PolicyVerdict.ALLOW and verdict == PolicyVerdict.ALLOW:
                                    pass  # Keep ALLOW
                            else:
                                # Last match wins
                                verdict = rule.action

                    except PolicyError as e:
                        logger.warning(f"Rule evaluation failed: {e}")
                        continue

            # Calculate latency
            latency_ms = (time.perf_counter() - start_time) * 1000

            # Create decision
            decision = PolicyDecision(
                agent_id=agent_id,
                request_context=request_context,
                verdict=verdict,
                matched_rules=matched_rules,
                explanation=self._generate_explanation(matched_rule_details, verdict),
                confidence=1.0 if matched_rules else 0.5,
                evaluation_latency_ms=latency_ms,
                timestamp=datetime.utcnow(),
            )

            # Log to audit trail
            audit_entry, _ = await self.audit.log_policy_evaluation(
                decision_id=decision.decision_id,
                agent_id=agent_id,
                verdict=verdict.value,
                matched_rules=matched_rules,
                latency_ms=latency_ms,
            )

            if audit_entry:
                decision.audit_event_id = audit_entry.audit_id

            self._evaluation_count += 1

            logger.debug(
                f"Policy evaluation completed: {decision.decision_id} "
                f"(verdict={verdict.value}, latency={latency_ms:.2f}ms)"
            )

            return decision, None

        except Exception as e:
            logger.error(f"Policy evaluation failed: {e}")
            return None, f"{ErrorCodes.POLICY_EVALUATION_FAILED.value}: {str(e)}"

    async def _load_agent_context(self, agent_id: str) -> Dict[str, Any]:
        """Load agent context from L01"""
        return await self.l01.get_agent_context(agent_id)

    async def _refresh_active_policies(self) -> None:
        """Refresh the active policies cache"""
        try:
            policy_data = await self.l01.get_active_policies()
            self._active_policies = [
                self._dict_to_policy(p) for p in policy_data
            ]
            self._cache_timestamp = datetime.utcnow()
            logger.debug(f"Refreshed active policies: {len(self._active_policies)} policies")
        except Exception as e:
            logger.error(f"Failed to refresh active policies: {e}")

    def _is_cache_expired(self) -> bool:
        """Check if policy cache has expired"""
        if not self.config.enable_policy_caching:
            return True
        elapsed = (datetime.utcnow() - self._cache_timestamp).total_seconds()
        return elapsed > self.config.policy_cache_ttl_seconds

    def _dict_to_policy(self, data: Dict[str, Any]) -> PolicyDefinition:
        """Convert dictionary to PolicyDefinition"""
        rules = [
            PolicyRule(
                rule_id=r.get("rule_id", ""),
                name=r.get("name", ""),
                description=r.get("description", ""),
                condition=r.get("condition", ""),
                action=PolicyVerdict(r.get("action", "ALLOW")),
                priority=r.get("priority", 0),
                enabled=r.get("enabled", True),
                tags=r.get("tags", []),
            )
            for r in data.get("rules", [])
        ]

        return PolicyDefinition(
            policy_id=data.get("policy_id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            rules=rules,
            scope=data.get("scope", "global"),
            scope_id=data.get("scope_id"),
            active=data.get("active", False),
            metadata=data.get("metadata", {}),
        )

    def _generate_explanation(
        self,
        matched_rules: List[Dict[str, Any]],
        verdict: PolicyVerdict
    ) -> str:
        """Generate human-readable explanation of decision"""
        if not matched_rules:
            return "No policies matched; default ALLOW applied"

        rule_names = [r["rule_name"] or r["rule_id"] for r in matched_rules]
        policy_names = list(set(r["policy_name"] for r in matched_rules))

        if verdict == PolicyVerdict.DENY:
            return f"DENIED by rules: {', '.join(rule_names)} from policies: {', '.join(policy_names)}"
        elif verdict == PolicyVerdict.ESCALATE:
            return f"Escalation required by rules: {', '.join(rule_names)} from policies: {', '.join(policy_names)}"
        else:
            return f"ALLOWED; matched rules: {', '.join(rule_names)}"

    def get_stats(self) -> Dict[str, Any]:
        """Get policy engine statistics"""
        return {
            "evaluation_count": self._evaluation_count,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_ratio": self._cache_hits / max(1, self._cache_hits + self._cache_misses),
            "active_policies": len(self._active_policies),
            "total_policies": len(self._policies),
        }

    async def health_check(self) -> Dict[str, Any]:
        """Health check for policy engine"""
        return {
            "status": "healthy",
            "stats": self.get_stats(),
            "cache_age_seconds": (datetime.utcnow() - self._cache_timestamp).total_seconds(),
        }

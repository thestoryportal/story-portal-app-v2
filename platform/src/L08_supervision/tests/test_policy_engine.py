"""
L08 Supervision Layer - Policy Engine Tests

Tests for policy registration, evaluation, and expression parsing.
"""

import pytest
from datetime import datetime

from ..models.domain import PolicyDefinition, PolicyRule, PolicyVerdict, PolicyDecision
from ..services.policy_engine import PolicyEngine, PolicyExpressionEvaluator


@pytest.mark.l08
@pytest.mark.unit
class TestPolicyExpressionEvaluator:
    """Tests for the policy expression evaluator"""

    def test_simple_equality(self, expression_evaluator):
        """Test simple equality comparison"""
        context = {"operation": "read"}
        assert expression_evaluator.evaluate("operation == 'read'", context) is True
        assert expression_evaluator.evaluate("operation == 'write'", context) is False

    def test_nested_attribute_access(self, expression_evaluator):
        """Test nested attribute access"""
        context = {"resource": {"type": "dataset", "sensitive": True}}
        assert expression_evaluator.evaluate("resource.type == 'dataset'", context) is True
        assert expression_evaluator.evaluate("resource.sensitive == True", context) is True

    def test_and_operator(self, expression_evaluator):
        """Test AND boolean operator"""
        context = {"operation": "delete", "resource": {"sensitive": True}}
        assert expression_evaluator.evaluate(
            "operation == 'delete' and resource.sensitive == True", context
        ) is True
        assert expression_evaluator.evaluate(
            "operation == 'delete' and resource.sensitive == False", context
        ) is False

    def test_or_operator(self, expression_evaluator):
        """Test OR boolean operator"""
        context = {"operation": "read"}
        assert expression_evaluator.evaluate(
            "operation == 'read' or operation == 'write'", context
        ) is True
        assert expression_evaluator.evaluate(
            "operation == 'delete' or operation == 'update'", context
        ) is False

    def test_not_operator(self, expression_evaluator):
        """Test NOT boolean operator"""
        context = {"resource": {"public": False}}
        assert expression_evaluator.evaluate("not resource.public", context) is True
        assert expression_evaluator.evaluate("resource.public", context) is False

    def test_in_operator(self, expression_evaluator):
        """Test IN membership operator"""
        context = {"operation": "read", "allowed_ops": ["read", "list"]}
        assert expression_evaluator.evaluate("operation in allowed_ops", context) is True
        context["operation"] = "delete"
        assert expression_evaluator.evaluate("operation in allowed_ops", context) is False

    def test_comparison_operators(self, expression_evaluator):
        """Test comparison operators"""
        context = {"count": 5, "limit": 10}
        assert expression_evaluator.evaluate("count < limit", context) is True
        assert expression_evaluator.evaluate("count <= limit", context) is True
        assert expression_evaluator.evaluate("count > limit", context) is False
        assert expression_evaluator.evaluate("count >= 5", context) is True
        assert expression_evaluator.evaluate("count != limit", context) is True

    def test_missing_attribute_returns_false(self, expression_evaluator):
        """Test that missing attributes return False"""
        context = {"operation": "read"}
        # Missing attribute should return False, not raise
        assert expression_evaluator.evaluate("resource.type == 'dataset'", context) is False

    def test_validation(self, expression_evaluator):
        """Test expression validation"""
        # Valid expressions
        expression_evaluator.validate("operation == 'read'")
        expression_evaluator.validate("resource.sensitive == True")

        # Invalid expressions should raise
        with pytest.raises(Exception):
            expression_evaluator.validate("import os")  # Unsafe

    def test_complex_expression(self, expression_evaluator):
        """Test complex nested expression"""
        context = {
            "agent": {"team": "datascience", "role": "analyst"},
            "resource": {"type": "dataset", "classification": "internal"},
            "operation": "read"
        }
        expr = "(agent.team == 'datascience' or agent.team == 'engineering') and resource.classification != 'secret'"
        assert expression_evaluator.evaluate(expr, context) is True


@pytest.mark.l08
@pytest.mark.unit
class TestPolicyEngine:
    """Tests for the policy engine"""

    @pytest.mark.asyncio
    async def test_register_policy(self, policy_engine, sample_policy):
        """Test policy registration"""
        result, error = await policy_engine.register_policy(sample_policy)
        assert error is None
        assert result is not None
        assert result.policy_id != ""
        assert result.name == sample_policy.name

    @pytest.mark.asyncio
    async def test_evaluate_allow(self, policy_engine, sample_policy):
        """Test policy evaluation returning ALLOW"""
        result, _ = await policy_engine.register_policy(sample_policy)
        await policy_engine.deploy_policy(result.policy_id)

        context = {"operation": "read", "resource": {"type": "dataset"}}
        decision, error = await policy_engine.evaluate("agent_001", context)

        assert error is None
        assert decision is not None
        assert decision.verdict == PolicyVerdict.ALLOW

    @pytest.mark.asyncio
    async def test_evaluate_deny(self, policy_engine, sample_policy):
        """Test policy evaluation returning DENY"""
        result, _ = await policy_engine.register_policy(sample_policy)
        await policy_engine.deploy_policy(result.policy_id)

        context = {"operation": "delete", "resource": {"sensitive": True}}
        decision, error = await policy_engine.evaluate("agent_001", context)

        assert error is None
        assert decision is not None
        assert decision.verdict == PolicyVerdict.DENY

    @pytest.mark.asyncio
    async def test_evaluate_escalate(self, policy_engine, sample_policy):
        """Test policy evaluation returning ESCALATE"""
        result, _ = await policy_engine.register_policy(sample_policy)
        await policy_engine.deploy_policy(result.policy_id)

        context = {"operation": "write", "resource": {"type": "pii"}}
        decision, error = await policy_engine.evaluate("agent_001", context)

        assert error is None
        assert decision is not None
        assert decision.verdict == PolicyVerdict.ESCALATE

    @pytest.mark.asyncio
    async def test_deny_wins_rule(self, policy_engine):
        """Test that DENY always wins over ALLOW and ESCALATE"""
        policy = PolicyDefinition(
            name="conflict_test",
            rules=[
                PolicyRule(
                    name="allow_all",
                    condition="True",
                    action=PolicyVerdict.ALLOW,
                    priority=1,
                ),
                PolicyRule(
                    name="deny_admin",
                    condition="True",
                    action=PolicyVerdict.DENY,
                    priority=100,
                ),
                PolicyRule(
                    name="escalate_all",
                    condition="True",
                    action=PolicyVerdict.ESCALATE,
                    priority=50,
                ),
            ],
        )
        result, _ = await policy_engine.register_policy(policy)
        await policy_engine.deploy_policy(result.policy_id)

        decision, _ = await policy_engine.evaluate("agent_001", {})
        assert decision.verdict == PolicyVerdict.DENY

    @pytest.mark.asyncio
    async def test_no_matching_rules_allows(self, policy_engine):
        """Test that no matching rules results in ALLOW"""
        policy = PolicyDefinition(
            name="no_match",
            rules=[
                PolicyRule(
                    name="deny_specific",
                    condition="operation == 'forbidden'",
                    action=PolicyVerdict.DENY,
                ),
            ],
        )
        result, _ = await policy_engine.register_policy(policy)
        await policy_engine.deploy_policy(result.policy_id)

        decision, _ = await policy_engine.evaluate(
            "agent_001", {"operation": "allowed"}
        )
        assert decision.verdict == PolicyVerdict.ALLOW

    @pytest.mark.asyncio
    async def test_disabled_policy_ignored(self, policy_engine, sample_policy):
        """Test that disabled policies are not evaluated"""
        sample_policy.active = False
        await policy_engine.register_policy(sample_policy)
        # Don't deploy - policy should not be active

        context = {"operation": "delete", "resource": {"sensitive": True}}
        decision, _ = await policy_engine.evaluate("agent_001", context)

        # Should ALLOW because disabled policy is ignored
        assert decision.verdict == PolicyVerdict.ALLOW

    @pytest.mark.asyncio
    async def test_disabled_rule_ignored(self, policy_engine):
        """Test that disabled rules are not evaluated"""
        policy = PolicyDefinition(
            name="disabled_rule_test",
            rules=[
                PolicyRule(
                    name="disabled_deny",
                    condition="True",
                    action=PolicyVerdict.DENY,
                    enabled=False,
                ),
            ],
        )
        result, _ = await policy_engine.register_policy(policy)
        await policy_engine.deploy_policy(result.policy_id)

        decision, _ = await policy_engine.evaluate("agent_001", {})
        assert decision.verdict == PolicyVerdict.ALLOW

    @pytest.mark.asyncio
    async def test_decision_includes_matched_rules(self, policy_engine, sample_policy):
        """Test that decision includes list of matched rules"""
        result, _ = await policy_engine.register_policy(sample_policy)
        await policy_engine.deploy_policy(result.policy_id)

        context = {"operation": "read"}
        decision, _ = await policy_engine.evaluate("agent_001", context)

        assert len(decision.matched_rules) > 0

    @pytest.mark.asyncio
    async def test_deploy_policy(self, policy_engine, sample_policy):
        """Test policy deployment"""
        result, _ = await policy_engine.register_policy(sample_policy)
        success, error = await policy_engine.deploy_policy(result.policy_id)

        assert success is True
        assert error is None
        # Policy should be in the active policies list after deployment
        policy_ids = [p.policy_id for p in policy_engine._active_policies]
        assert result.policy_id in policy_ids

    @pytest.mark.asyncio
    async def test_get_stats(self, policy_engine, sample_policy):
        """Test getting policy engine statistics"""
        result, _ = await policy_engine.register_policy(sample_policy)
        await policy_engine.deploy_policy(result.policy_id)
        await policy_engine.evaluate("agent_001", {"operation": "read"})

        stats = policy_engine.get_stats()
        assert "total_policies" in stats
        assert "evaluation_count" in stats
        assert stats["total_policies"] >= 1
        assert stats["evaluation_count"] >= 1


@pytest.mark.l08
@pytest.mark.performance
class TestPolicyEnginePerformance:
    """Performance tests for policy engine"""

    @pytest.mark.asyncio
    async def test_evaluation_latency(self, policy_engine):
        """Test that policy evaluation meets 100ms p99 SLA"""
        import time

        # Create 50 policies with 5 rules each
        for i in range(50):
            policy = PolicyDefinition(
                name=f"perf_test_{i}",
                rules=[
                    PolicyRule(
                        name=f"rule_{j}",
                        condition=f"attr_{j} == 'value'",
                        action=PolicyVerdict.ALLOW,
                    )
                    for j in range(5)
                ],
            )
            result, _ = await policy_engine.register_policy(policy)
            await policy_engine.deploy_policy(result.policy_id)

        # Run 100 evaluations
        latencies = []
        for _ in range(100):
            start = time.perf_counter()
            await policy_engine.evaluate("agent_001", {"attr_0": "value"})
            latencies.append((time.perf_counter() - start) * 1000)

        # Calculate p99
        latencies.sort()
        p99 = latencies[98]

        assert p99 < 100, f"P99 latency {p99:.2f}ms exceeds 100ms SLA"

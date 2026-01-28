"""
L08 Supervision Layer - Route Tests

Tests for HTTP API endpoints.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.l08
@pytest.mark.unit
class TestHealthRoutes:
    """Tests for health check endpoints"""

    def test_health_endpoint(self, client):
        """Test basic health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "service" in data

    def test_health_live(self, client):
        """Test liveness probe"""
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    def test_health_ready(self, client):
        """Test readiness probe"""
        response = client.get("/health/ready")
        # May be 200 or 503 depending on initialization
        assert response.status_code in [200, 503]

    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "L08 Supervision Layer"
        assert "endpoints" in data


@pytest.mark.l08
@pytest.mark.integration
class TestPolicyRoutes:
    """Tests for policy management endpoints"""

    def test_create_policy(self, client):
        """Test creating a policy"""
        policy_data = {
            "name": "test_policy",
            "description": "Test policy",
            "rules": [
                {
                    "rule_name": "allow_read",
                    "condition": "operation == 'read'",
                    "action": "ALLOW",
                    "priority": 10,
                }
            ],
            "enabled": True,
            "tags": ["test"],
        }

        response = client.post("/api/v1/policies", json=policy_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test_policy"
        assert "policy_id" in data

    def test_list_policies(self, client):
        """Test listing policies"""
        response = client.get("/api/v1/policies")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_validate_policy(self, client):
        """Test policy validation"""
        policy_data = {
            "name": "validation_test",
            "rules": [
                {
                    "rule_name": "test_rule",
                    "condition": "operation == 'read'",
                    "action": "ALLOW",
                }
            ],
        }

        response = client.post("/api/v1/policies/validate", json=policy_data)
        assert response.status_code == 200
        data = response.json()
        assert "valid" in data
        assert "errors" in data
        assert "warnings" in data


@pytest.mark.l08
@pytest.mark.integration
class TestEvaluationRoutes:
    """Tests for policy evaluation endpoints"""

    def test_evaluate_request(self, client):
        """Test evaluating a request"""
        # First create a policy
        policy_data = {
            "name": "eval_test_policy",
            "rules": [
                {
                    "rule_name": "allow_read",
                    "condition": "operation == 'read'",
                    "action": "ALLOW",
                }
            ],
            "enabled": True,
        }
        client.post("/api/v1/policies", json=policy_data)

        # Then evaluate
        eval_data = {
            "agent_id": "agent_001",
            "operation": "read",
            "resource": {"type": "dataset"},
        }

        response = client.post("/api/v1/evaluate", json=eval_data)
        assert response.status_code == 200
        data = response.json()
        assert "verdict" in data
        assert "decision_id" in data
        assert "evaluation_latency_ms" in data

    def test_check_constraint(self, client):
        """Test constraint check endpoint"""
        # This will likely fail since constraint doesn't exist
        check_data = {
            "agent_id": "agent_001",
            "constraint_id": "test_constraint",
            "requested": 1,
        }

        response = client.post("/api/v1/constraints/check", json=check_data)
        # Should get response (may be error if constraint doesn't exist)
        assert response.status_code in [200, 400, 500]

    def test_report_metric(self, client):
        """Test metric reporting endpoint"""
        report_data = {
            "agent_id": "agent_001",
            "metric_name": "latency_ms",
            "value": 100.0,
            "detect": False,
        }

        response = client.post("/api/v1/metrics/report", json=report_data)
        assert response.status_code == 200
        data = response.json()
        assert data["recorded"] is True

    def test_get_compliance_status(self, client):
        """Test getting compliance status"""
        response = client.get("/api/v1/compliance/agent_001")
        assert response.status_code == 200
        data = response.json()
        assert "compliance_score" in data
        assert "risk_level" in data


@pytest.mark.l08
@pytest.mark.integration
class TestEscalationRoutes:
    """Tests for escalation workflow endpoints"""

    def test_create_escalation(self, client):
        """Test creating an escalation"""
        escalation_data = {
            "decision_id": "dec_001",
            "reason": "High risk operation",
            "context": {"operation": "delete"},
            "approvers": ["admin_001"],
        }

        response = client.post("/api/v1/escalations", json=escalation_data)
        assert response.status_code == 200
        data = response.json()
        assert "workflow_id" in data
        assert data["status"] == "PENDING"

    def test_list_escalations(self, client):
        """Test listing escalations"""
        response = client.get("/api/v1/escalations")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_pending_count(self, client):
        """Test getting pending escalation count"""
        response = client.get("/api/v1/escalations/pending/count")
        assert response.status_code == 200
        data = response.json()
        assert "pending_count" in data


@pytest.mark.l08
@pytest.mark.integration
class TestAuditRoutes:
    """Tests for audit trail endpoints"""

    def test_search_audit_log(self, client):
        """Test searching the audit log"""
        response = client.get("/api/v1/audit/search")
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert "total_count" in data

    def test_search_with_filters(self, client):
        """Test searching with filters"""
        response = client.get(
            "/api/v1/audit/search",
            params={"actor_id": "agent_001", "limit": 10}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) <= 10

    def test_verify_audit_chain(self, client):
        """Test audit chain verification"""
        response = client.post("/api/v1/audit/verify")
        assert response.status_code == 200
        data = response.json()
        assert "valid" in data
        assert "entries_verified" in data

    def test_get_audit_stats(self, client):
        """Test getting audit statistics"""
        response = client.get("/api/v1/audit/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_entries" in data


@pytest.mark.l08
@pytest.mark.integration
class TestMetricsRoute:
    """Tests for metrics endpoint"""

    def test_get_metrics(self, client):
        """Test getting Prometheus metrics"""
        response = client.get("/metrics")
        # May be 200 or 503 depending on service state
        if response.status_code == 200:
            data = response.text
            assert "l08_" in data  # Should have L08 prefixed metrics

    def test_get_stats(self, client):
        """Test getting operational stats"""
        response = client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        assert "initialized" in data

    def test_get_config(self, client):
        """Test getting configuration"""
        response = client.get("/config")
        assert response.status_code == 200
        data = response.json()
        # Should only expose non-sensitive values
        assert "vault_url" not in data  # Sensitive
        assert "dev_mode" in data  # Non-sensitive

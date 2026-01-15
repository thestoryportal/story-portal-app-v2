"""
E2E tests for L06 Evaluation Layer - L01 Data Layer bridge integration.

Tests the complete flow of recording evaluation data in L01.
"""

import pytest
import asyncio
import httpx
import json
from datetime import datetime
from uuid import uuid4

from src.L06_evaluation.services.l01_bridge import L06Bridge
from src.L06_evaluation.models import (
    QualityScore,
    DimensionScore,
    Assessment,
    MetricPoint,
    MetricType,
    Anomaly,
    AnomalySeverity,
    ComplianceResult,
    Constraint,
    ConstraintType,
    Violation,
    Alert,
    AlertSeverity,
    AlertChannel
)
from src.L01_data_layer.client import L01Client


@pytest.mark.asyncio
class TestL06L01Integration:
    """Test L06-L01 integration end-to-end."""

    @pytest.fixture
    async def bridge(self):
        """Create L06Bridge instance."""
        bridge = L06Bridge(l01_base_url="http://localhost:8002")
        await bridge.initialize()
        yield bridge
        await bridge.cleanup()

    @pytest.fixture
    async def l01_client(self):
        """Create L01Client instance for verification."""
        client = L01Client(base_url="http://localhost:8002")
        yield client
        await client.close()

    async def test_bridge_initialization(self, bridge):
        """Test that L06Bridge initializes correctly."""
        assert bridge is not None
        assert bridge.l01_client is not None
        assert bridge.enabled is True

    async def test_record_quality_score(self, bridge, l01_client):
        """Test recording a quality score with multi-dimensional evaluation."""
        # Create quality score with dimensions
        score_id = f"score-{uuid4()}"
        agent_id = "agent-123"
        tenant_id = "tenant-456"
        timestamp = datetime.utcnow()

        # Create dimension scores
        dimensions = {
            "accuracy": DimensionScore(
                dimension="accuracy",
                score=0.95,
                weight=0.3,
                raw_metrics={"correct": 95, "total": 100}
            ),
            "latency": DimensionScore(
                dimension="latency",
                score=0.88,
                weight=0.2,
                raw_metrics={"avg_ms": 120, "p95_ms": 200}
            ),
            "cost": DimensionScore(
                dimension="cost",
                score=0.92,
                weight=0.15,
                raw_metrics={"total_cost": 0.05}
            )
        }

        # Calculate overall score
        overall_score = sum(d.score * d.weight for d in dimensions.values()) / sum(d.weight for d in dimensions.values())

        score = QualityScore(
            score_id=score_id,
            agent_id=agent_id,
            tenant_id=tenant_id,
            timestamp=timestamp,
            overall_score=overall_score,
            dimensions=dimensions,
            assessment=Assessment.GOOD,
            data_completeness=1.0,
            cached=False
        )

        # Record in L01
        result = await bridge.record_quality_score(score)
        assert result is True

        # Verify record was created in L01
        await asyncio.sleep(0.1)  # Allow async write to complete

        async with httpx.AsyncClient() as client:
            http_response = await client.get(f"http://localhost:8002/quality-scores/{score_id}")
            http_response.raise_for_status()
            record = http_response.json()

        assert record["score_id"] == score_id
        assert record["agent_did"] == agent_id
        assert record["tenant_id"] == tenant_id
        assert float(record["overall_score"]) == pytest.approx(overall_score, abs=0.0001)
        assert record["assessment"] == "good"
        assert float(record["data_completeness"]) == 1.0
        assert record["cached"] is False

        # Verify dimensions are stored
        dimensions_data = record["dimensions"]
        if isinstance(dimensions_data, str):
            dimensions_data = json.loads(dimensions_data)
        assert "accuracy" in dimensions_data
        assert float(dimensions_data["accuracy"]["score"]) == 0.95
        assert float(dimensions_data["accuracy"]["weight"]) == 0.3

    async def test_record_metric(self, bridge, l01_client):
        """Test recording a time-series metric with labels."""
        # Create metric point
        metric = MetricPoint(
            metric_name="llm.tokens.total",
            value=1234.0,
            timestamp=datetime.utcnow(),
            labels={
                "agent_id": "agent-789",
                "model": "gpt-4",
                "task_type": "code_generation"
            },
            metric_type=MetricType.COUNTER
        )

        # Record in L01
        result = await bridge.record_metric(metric)
        assert result is True

        # Verify record was created in L01
        await asyncio.sleep(0.1)

        async with httpx.AsyncClient() as client:
            http_response = await client.get(
                "http://localhost:8002/metrics/",
                params={"metric_name": "llm.tokens.total", "limit": 10}
            )
            http_response.raise_for_status()
            records = http_response.json()

        assert len(records) > 0
        # Find our specific metric
        matching_records = [r for r in records if float(r["value"]) == 1234.0]
        assert len(matching_records) > 0
        record = matching_records[0]

        assert record["metric_name"] == "llm.tokens.total"
        assert record["metric_type"] == "counter"
        assert float(record["value"]) == 1234.0

        # Verify labels
        labels_data = record["labels"]
        if isinstance(labels_data, str):
            labels_data = json.loads(labels_data)
        assert labels_data["agent_id"] == "agent-789"
        assert labels_data["model"] == "gpt-4"
        assert labels_data["task_type"] == "code_generation"

    async def test_record_anomaly(self, bridge, l01_client):
        """Test recording a detected anomaly."""
        # Create anomaly
        anomaly_id = f"anom-{uuid4()}"
        anomaly = Anomaly(
            anomaly_id=anomaly_id,
            metric_name="response_time_ms",
            severity=AnomalySeverity.WARNING,
            baseline_value=120.0,
            current_value=350.0,
            z_score=3.5,
            detected_at=datetime.utcnow(),
            agent_id="agent-alert-123",
            tenant_id="tenant-alert-456",
            confidence=0.95,
            status="alerting",
            alert_sent=False
        )

        # Record in L01
        result = await bridge.record_anomaly(anomaly)
        assert result is True

        # Verify record was created in L01
        await asyncio.sleep(0.1)

        async with httpx.AsyncClient() as client:
            http_response = await client.get(f"http://localhost:8002/anomalies/{anomaly_id}")
            http_response.raise_for_status()
            record = http_response.json()

        assert record["anomaly_id"] == anomaly_id
        assert record["metric_name"] == "response_time_ms"
        assert record["severity"] == "warning"
        assert float(record["baseline_value"]) == 120.0
        assert float(record["current_value"]) == 350.0
        assert float(record["z_score"]) == 3.5
        assert record["status"] == "alerting"
        assert record["alert_sent"] is False
        assert float(record["confidence"]) == 0.95

    async def test_update_anomaly_status(self, bridge, l01_client):
        """Test updating anomaly status to resolved."""
        # Create and record anomaly
        anomaly_id = f"anom-resolve-{uuid4()}"
        anomaly = Anomaly(
            anomaly_id=anomaly_id,
            metric_name="error_rate",
            severity=AnomalySeverity.CRITICAL,
            baseline_value=0.01,
            current_value=0.15,
            z_score=5.2,
            detected_at=datetime.utcnow(),
            status="alerting"
        )
        await bridge.record_anomaly(anomaly)
        await asyncio.sleep(0.1)

        # Update status to resolved
        resolved_at = datetime.utcnow()
        result = await bridge.update_anomaly_status(
            anomaly_id=anomaly_id,
            status="resolved",
            resolved_at=resolved_at,
            alert_sent=True
        )
        assert result is True

        # Verify update
        await asyncio.sleep(0.1)
        async with httpx.AsyncClient() as client:
            http_response = await client.get(f"http://localhost:8002/anomalies/{anomaly_id}")
            http_response.raise_for_status()
            record = http_response.json()

        assert record["status"] == "resolved"
        assert record["resolved_at"] is not None
        assert record["alert_sent"] is True

    async def test_record_compliance_result(self, bridge, l01_client):
        """Test recording a compliance validation result with violations."""
        # Create constraint and violation
        constraint = Constraint(
            constraint_id=f"const-{uuid4()}",
            constraint_type=ConstraintType.BUDGET,
            name="Token Budget",
            limit=5000,
            unit="tokens",
            description="Maximum tokens per execution"
        )

        violation = Violation(
            violation_id=f"viol-{uuid4()}",
            constraint=constraint,
            timestamp=datetime.utcnow(),
            actual=7500,
            agent_id="agent-compliance-123",
            task_id="task-compliance-456",
            tenant_id="tenant-compliance-789",
            severity="warning",
            remediation_suggested="Reduce prompt size or use smaller model"
        )

        # Create compliance result
        result_id = f"comp-{uuid4()}"
        compliance_result = ComplianceResult(
            result_id=result_id,
            execution_id="exec-compliance-999",
            agent_id="agent-compliance-123",
            tenant_id="tenant-compliance-789",
            timestamp=datetime.utcnow(),
            violations=[violation],
            constraints_checked=[constraint],
            compliant=False
        )

        # Record in L01
        result = await bridge.record_compliance_result(compliance_result)
        assert result is True

        # Verify record was created in L01
        await asyncio.sleep(0.1)

        async with httpx.AsyncClient() as client:
            http_response = await client.get(f"http://localhost:8002/compliance-results/{result_id}")
            http_response.raise_for_status()
            record = http_response.json()

        assert record["result_id"] == result_id
        assert record["execution_id"] == "exec-compliance-999"
        assert record["agent_did"] == "agent-compliance-123"
        assert record["tenant_id"] == "tenant-compliance-789"
        assert record["compliant"] is False

        # Verify violations
        violations_data = record["violations"]
        if isinstance(violations_data, str):
            violations_data = json.loads(violations_data)
        assert len(violations_data) == 1
        assert violations_data[0]["actual"] == 7500
        assert violations_data[0]["severity"] == "warning"

        # Verify constraints
        constraints_data = record["constraints_checked"]
        if isinstance(constraints_data, str):
            constraints_data = json.loads(constraints_data)
        assert len(constraints_data) == 1
        assert constraints_data[0]["name"] == "Token Budget"
        assert constraints_data[0]["limit"] == 5000

    async def test_record_alert(self, bridge, l01_client):
        """Test recording an alert."""
        # Create alert
        alert_id = f"alert-{uuid4()}"
        alert = Alert(
            alert_id=alert_id,
            timestamp=datetime.utcnow(),
            severity=AlertSeverity.WARNING,
            type="anomaly",
            metric="latency_p95",
            message="High latency detected: 95th percentile exceeds threshold",
            agent_id="agent-alert-555",
            tenant_id="tenant-alert-666",
            channels=[AlertChannel.SLACK, AlertChannel.EMAIL],
            metadata={
                "threshold": 500,
                "actual": 850,
                "z_score": 4.2
            },
            delivery_attempts=0,
            delivered=False
        )

        # Record in L01
        result = await bridge.record_alert(alert)
        assert result is True

        # Verify record was created in L01
        await asyncio.sleep(0.1)

        async with httpx.AsyncClient() as client:
            http_response = await client.get(f"http://localhost:8002/alerts/{alert_id}")
            http_response.raise_for_status()
            record = http_response.json()

        assert record["alert_id"] == alert_id
        assert record["severity"] == "warning"
        assert record["type"] == "anomaly"
        assert record["metric"] == "latency_p95"
        assert record["message"] == "High latency detected: 95th percentile exceeds threshold"
        assert record["agent_did"] == "agent-alert-555"
        assert record["tenant_id"] == "tenant-alert-666"
        assert "slack" in record["channels"]
        assert "email" in record["channels"]
        assert record["delivered"] is False
        assert record["delivery_attempts"] == 0

        # Verify metadata
        metadata_data = record["metadata"]
        if isinstance(metadata_data, str):
            metadata_data = json.loads(metadata_data)
        assert metadata_data["threshold"] == 500
        assert metadata_data["actual"] == 850
        assert metadata_data["z_score"] == 4.2

    async def test_update_alert_delivery(self, bridge, l01_client):
        """Test updating alert delivery status."""
        # Create and record alert
        alert_id = f"alert-delivery-{uuid4()}"
        alert = Alert(
            alert_id=alert_id,
            timestamp=datetime.utcnow(),
            severity=AlertSeverity.INFO,
            type="test",
            metric="test_metric",
            message="Test alert for delivery tracking",
            delivery_attempts=0,
            delivered=False
        )
        await bridge.record_alert(alert)
        await asyncio.sleep(0.1)

        # Update delivery status
        last_attempt = datetime.utcnow()
        result = await bridge.update_alert_delivery(
            alert_id=alert_id,
            delivery_attempts=3,
            delivered=True,
            last_attempt=last_attempt
        )
        assert result is True

        # Verify update
        await asyncio.sleep(0.1)
        async with httpx.AsyncClient() as client:
            http_response = await client.get(f"http://localhost:8002/alerts/{alert_id}")
            http_response.raise_for_status()
            record = http_response.json()

        assert record["delivery_attempts"] == 3
        assert record["delivered"] is True
        assert record["last_attempt"] is not None

    async def test_bridge_disabled(self):
        """Test that disabled bridge doesn't record."""
        bridge = L06Bridge()
        bridge.enabled = False

        score = QualityScore(
            score_id=f"score-disabled-{uuid4()}",
            agent_id="test",
            tenant_id="test",
            timestamp=datetime.utcnow(),
            overall_score=0.9,
            dimensions={},
            assessment=Assessment.GOOD
        )

        result = await bridge.record_quality_score(score)
        assert result is False

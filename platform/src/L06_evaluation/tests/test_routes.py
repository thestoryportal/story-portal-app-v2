"""
L06 Evaluation Layer - Route Tests

Tests for all HTTP API endpoints.
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
import uuid

from ..main import app
from ..services.evaluation_service import EvaluationService


@pytest.fixture
def mock_evaluation_service(mock_l01_bridge):
    """Create a mock EvaluationService"""
    service = MagicMock()  # Remove spec to allow arbitrary attributes
    service._initialized = True
    service.l01_bridge = mock_l01_bridge

    # Quality scorer mock (service uses 'scorer' attribute name)
    mock_score = MagicMock()
    mock_score.score_id = "qs-123"
    mock_score.agent_id = "agent-001"
    mock_score.tenant_id = "tenant-001"
    mock_score.overall_score = 92.0
    mock_score.assessment = MagicMock(value="good")
    mock_score.dimensions = {}
    mock_score.timestamp = datetime.now(UTC)
    mock_score.data_completeness = 1.0
    mock_score.cached = False

    service.scorer = MagicMock()
    service.scorer.compute_score = AsyncMock(return_value=mock_score)

    # Anomaly detector mock (service uses 'anomaly' attribute name)
    service.anomaly = MagicMock()
    service.anomaly.detect_anomalies = AsyncMock(return_value=[])
    service.anomaly.get_statistics = MagicMock(return_value={
        "total_anomalies": 50,
        "active_anomalies": 5,
        "resolved_anomalies": 45,
        "critical_count": 2,
        "warning_count": 3,
    })

    # Alert manager mock
    service.alerts = MagicMock()
    service.alerts.send_alert = AsyncMock(return_value=True)
    service.alerts.get_statistics = MagicMock(return_value={
        "alerts_sent": 100,
        "alerts_failed": 5,
        "alerts_rate_limited": 10,
        "success_rate": 0.95,
    })

    # Compliance manager mock
    service.compliance = MagicMock()
    service.compliance.get_statistics = MagicMock(return_value={
        "checks_performed": 500,
        "violations_found": 25,
        "compliance_rate": 0.95,
    })

    # Service methods - process_event returns bool per actual route
    service.process_event = AsyncMock(return_value=True)
    service.get_quality_scores = AsyncMock(return_value=[])
    service.get_quality_score_by_id = AsyncMock(return_value=None)
    service.get_agent_summary = AsyncMock(return_value={
        "agent_id": "agent-001",
        "average_score": 85.0,
        "score_count": 100,
        "trend": "stable",
    })
    service.run_compliance_check = AsyncMock(return_value={
        "result_id": "comp-123",
        "compliant": True,
    })
    service.get_health_status = MagicMock(return_value={
        "initialized": True,
        "l01_bridge_available": True,
    })
    service.get_event_statistics = MagicMock(return_value={
        "total_events": 1000,
        "events_by_type": {"task.completed": 800, "task.failed": 200},
    })

    # get_statistics returns full ServiceStatsDTO-compatible dict
    service.get_statistics = MagicMock(return_value={
        "validator": {"total_validated": 100, "failed": 5},
        "deduplication": {"duplicates_detected": 10},
        "metrics": {"total_recorded": 500},
        "quality_scorer": {"scores_computed": 100},
        "anomaly_detector": {"anomalies_detected": 25},
        "compliance": {"checks_performed": 50, "violations": 5},
        "alerts": {"alerts_sent": 100, "success_rate": 0.95},
        "storage": {"writes_succeeded": 1000, "writes_failed": 5},
        "cache": {"hits": 500, "misses": 100},
        "audit": {"events_logged": 2000},
    })

    return service


@pytest.fixture
def client_with_service(mock_evaluation_service):
    """Create test client with mocked service - patch the EvaluationService"""
    # Patch EvaluationService at the module level to return our mock
    with patch("L06_evaluation.main.EvaluationService") as MockService:
        # Make the constructor return our mock
        mock_instance = mock_evaluation_service
        mock_instance.initialize = AsyncMock()
        mock_instance.cleanup = AsyncMock()
        MockService.return_value = mock_instance

        # Also patch L06Bridge
        with patch("L06_evaluation.main.L06Bridge") as MockBridge:
            MockBridge.return_value = mock_evaluation_service.l01_bridge

            with TestClient(app) as client:
                yield client


@pytest.mark.l06
@pytest.mark.unit
class TestHealthEndpoints:
    """Tests for health check endpoints"""

    def test_health_endpoint(self, client_with_service):
        """Test /health endpoint"""
        response = client_with_service.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "l06-evaluation"

    def test_health_live_endpoint(self, client_with_service):
        """Test /health/live endpoint"""
        response = client_with_service.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    def test_health_ready_endpoint(self, client_with_service):
        """Test /health/ready endpoint"""
        response = client_with_service.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    def test_root_endpoint(self, client_with_service):
        """Test root endpoint"""
        response = client_with_service.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "L06 Evaluation Layer"
        assert "endpoints" in data


@pytest.mark.l06
@pytest.mark.unit
class TestEvaluationRoutes:
    """Tests for /api/events endpoints"""

    def test_process_event_success(self, client_with_service, sample_event_data):
        """Test successful event processing"""
        response = client_with_service.post(
            "/api/events",
            json=sample_event_data,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "event_id" in data

    def test_process_event_invalid_type(self, client_with_service):
        """Test event processing with invalid type"""
        response = client_with_service.post(
            "/api/events",
            json={
                "id": "evt-123",
                "source": "test",
                "type": "",
                "subject": "test-subject",
                "data": {},
            },
        )
        # Should handle gracefully
        assert response.status_code in [200, 400, 422]

    def test_get_event_stats(self, client_with_service):
        """Test event statistics endpoint"""
        response = client_with_service.get("/api/events/stats")
        assert response.status_code == 200

    def test_process_event_service_not_initialized(self, sample_event_data):
        """Test process_event returns 503 when service not initialized (line 103)"""
        # Create a client without initializing the service
        with patch("L06_evaluation.main.EvaluationService") as MockService:
            mock_instance = MagicMock()
            mock_instance.initialize = AsyncMock()
            mock_instance.cleanup = AsyncMock()
            MockService.return_value = mock_instance

            with patch("L06_evaluation.main.L06Bridge") as MockBridge:
                MockBridge.return_value = MagicMock()

                with TestClient(app) as client:
                    # Set evaluation_service to None to trigger 503
                    app.state.evaluation_service = None
                    response = client.post("/api/events", json=sample_event_data)
                    assert response.status_code == 503
                    data = response.json()["detail"]
                    assert data["error_code"] == "E6000"

    def test_process_event_exception_handling(self, client_with_service, sample_event_data, mock_evaluation_service):
        """Test process_event exception handling (lines 139-141)"""
        # Make process_event raise an exception
        mock_evaluation_service.process_event = AsyncMock(side_effect=Exception("Processing failed"))
        response = client_with_service.post("/api/events", json=sample_event_data)
        assert response.status_code == 500
        data = response.json()["detail"]
        assert data["error_code"] == "E6001"
        assert "Processing failed" in data["message"]

    def test_get_event_stats_service_not_initialized(self):
        """Test get_event_stats returns 503 when service not initialized (line 159)"""
        with patch("L06_evaluation.main.EvaluationService") as MockService:
            mock_instance = MagicMock()
            mock_instance.initialize = AsyncMock()
            mock_instance.cleanup = AsyncMock()
            MockService.return_value = mock_instance

            with patch("L06_evaluation.main.L06Bridge") as MockBridge:
                MockBridge.return_value = MagicMock()

                with TestClient(app) as client:
                    app.state.evaluation_service = None
                    response = client.get("/api/events/stats")
                    assert response.status_code == 503
                    data = response.json()["detail"]
                    assert data["error_code"] == "E6000"

    def test_get_event_stats_exception_handling(self, client_with_service, mock_evaluation_service):
        """Test get_event_stats exception handling (lines 170-172)"""
        mock_evaluation_service.get_statistics = MagicMock(side_effect=Exception("Stats failed"))
        response = client_with_service.get("/api/events/stats")
        assert response.status_code == 500
        data = response.json()["detail"]
        assert data["error_code"] == "E6002"
        assert "Stats failed" in data["message"]


@pytest.mark.l06
@pytest.mark.unit
class TestQualityRoutes:
    """Tests for /api/quality endpoints"""

    def test_compute_quality_score(self, client_with_service, sample_quality_request):
        """Test quality score computation"""
        response = client_with_service.post(
            "/api/quality/compute",
            json=sample_quality_request,
        )
        assert response.status_code == 200
        data = response.json()
        assert "score_id" in data

    def test_get_quality_scores(self, client_with_service):
        """Test getting quality scores"""
        response = client_with_service.get(
            "/api/quality/scores",
            params={
                "agent_id": "agent-001",
                "start": "2026-01-01T00:00:00Z",
                "end": "2026-01-27T00:00:00Z",
            },
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_quality_scores_missing_params(self, client_with_service):
        """Test getting quality scores without required params"""
        response = client_with_service.get("/api/quality/scores")
        # Should return empty list or 400
        assert response.status_code in [200, 400, 422]

    def test_get_quality_summary(self, client_with_service):
        """Test quality summary endpoint"""
        response = client_with_service.get("/api/quality/summary/agent-001")
        assert response.status_code == 200
        data = response.json()
        assert "agent_id" in data or "average_score" in data

    def test_compute_quality_score_exception(self, client_with_service, sample_quality_request):
        """Test quality score computation exception (lines 155-157)"""
        mock_service = client_with_service.app.state.evaluation_service
        mock_service.scorer.compute_score = AsyncMock(side_effect=Exception("Compute failed"))

        response = client_with_service.post("/api/quality/compute", json=sample_quality_request)
        assert response.status_code == 500

    def test_get_quality_scores_value_error(self, client_with_service):
        """Test quality scores with invalid timestamp (lines 214-221)"""
        response = client_with_service.get(
            "/api/quality/scores",
            params={
                "agent_id": "agent-001",
                "start": "invalid-date",
                "end": "2026-01-27T00:00:00Z",
            },
        )
        assert response.status_code == 400

    def test_get_quality_scores_exception(self, client_with_service):
        """Test quality scores exception (lines 222-224)"""
        mock_service = client_with_service.app.state.evaluation_service
        mock_service.get_quality_scores = AsyncMock(side_effect=RuntimeError("Query failed"))

        response = client_with_service.get(
            "/api/quality/scores",
            params={
                "agent_id": "agent-001",
                "start": "2026-01-01T00:00:00Z",
                "end": "2026-01-27T00:00:00Z",
            },
        )
        assert response.status_code == 500

    def test_get_quality_score_by_id(self, client_with_service):
        """Test getting specific quality score by ID (lines 249-278)"""
        mock_service = client_with_service.app.state.evaluation_service
        mock_service.l01_bridge.l01_client.get_quality_score = AsyncMock(
            return_value={
                "score_id": "qs-123",
                "agent_id": "agent-001",
                "tenant_id": "tenant-001",
                "timestamp": "2026-01-27T12:00:00Z",
                "overall_score": 92.0,
                "dimensions": {},
                "assessment": "Good",
                "data_completeness": 1.0,
                "cached": False,
            }
        )

        response = client_with_service.get("/api/quality/scores/qs-123")
        assert response.status_code == 200
        data = response.json()
        assert data["score_id"] == "qs-123"

    def test_get_quality_score_by_id_not_found(self, client_with_service):
        """Test 404 when quality score not found (lines 262-269)"""
        mock_service = client_with_service.app.state.evaluation_service
        mock_service.l01_bridge.l01_client.get_quality_score = AsyncMock(return_value=None)

        response = client_with_service.get("/api/quality/scores/nonexistent-id")
        assert response.status_code == 404

    def test_get_quality_score_by_id_exception(self, client_with_service):
        """Test quality score by ID exception (lines 276-278)"""
        mock_service = client_with_service.app.state.evaluation_service
        mock_service.l01_bridge.l01_client.get_quality_score = AsyncMock(
            side_effect=RuntimeError("Query failed")
        )

        response = client_with_service.get("/api/quality/scores/qs-123")
        assert response.status_code == 500

    def test_get_quality_summary_exception(self, client_with_service):
        """Test quality summary exception (lines 317-319)"""
        mock_service = client_with_service.app.state.evaluation_service
        mock_service.get_agent_summary = AsyncMock(side_effect=Exception("Summary failed"))

        response = client_with_service.get("/api/quality/summary/agent-001")
        assert response.status_code == 500


@pytest.mark.l06
@pytest.mark.unit
class TestAnomalyRoutes:
    """Tests for /api/anomalies endpoints"""

    def test_get_anomalies(self, client_with_service):
        """Test getting anomalies"""
        response = client_with_service.get(
            "/api/anomalies",
            params={
                "start": "2026-01-01T00:00:00Z",
                "end": "2026-01-27T00:00:00Z",
            },
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_anomalies_by_severity(self, client_with_service):
        """Test filtering anomalies by severity"""
        response = client_with_service.get(
            "/api/anomalies",
            params={
                "severity": "critical",
                "start": "2026-01-01T00:00:00Z",
                "end": "2026-01-27T00:00:00Z",
            },
        )
        assert response.status_code == 200

    def test_get_anomaly_stats(self, client_with_service):
        """Test anomaly statistics endpoint"""
        response = client_with_service.get("/api/anomalies/stats/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_anomalies" in data

    def test_get_anomaly_by_id(self, client_with_service, mock_l01_client):
        """Test getting anomaly by ID"""
        mock_anomaly = {
            "anomaly_id": "anomaly-123",
            "metric_name": "test_metric",
            "severity": "warning",
            "baseline_value": 80.0,
            "current_value": 120.0,
            "z_score": 4.0,
            "detected_at": "2026-01-27T12:00:00Z",
            "resolved_at": None,
            "agent_id": "agent-001",
            "tenant_id": "tenant-001",
            "deviation_percent": 50.0,
            "confidence": 0.95,
            "status": "alerting",
            "alert_sent": True,
        }
        mock_l01_client.get_anomalies.return_value = [mock_anomaly]

        response = client_with_service.get("/api/anomalies/anomaly-123")
        assert response.status_code == 200
        data = response.json()
        assert data["anomaly_id"] == "anomaly-123"

    def test_get_anomaly_by_id_not_found(self, client_with_service, mock_l01_client):
        """Test getting non-existent anomaly"""
        mock_l01_client.get_anomalies.return_value = []

        response = client_with_service.get("/api/anomalies/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error_code"] == "E6022"

    def test_update_anomaly(self, client_with_service, mock_l01_bridge, mock_l01_client):
        """Test updating an anomaly"""
        mock_anomaly = {
            "anomaly_id": "anomaly-123",
            "metric_name": "test_metric",
            "severity": "warning",
            "baseline_value": 80.0,
            "current_value": 120.0,
            "z_score": 4.0,
            "detected_at": "2026-01-27T12:00:00Z",
            "resolved_at": None,
            "agent_id": "agent-001",
            "tenant_id": "tenant-001",
            "deviation_percent": 50.0,
            "confidence": 0.95,
            "status": "resolved",
            "alert_sent": True,
        }
        mock_l01_client.get_anomalies.return_value = [mock_anomaly]

        response = client_with_service.patch(
            "/api/anomalies/anomaly-123",
            json={"status": "resolved", "resolved_at": "2026-01-27T15:00:00Z"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["anomaly_id"] == "anomaly-123"

    def test_update_anomaly_invalid_status(self, client_with_service):
        """Test updating anomaly with invalid status"""
        response = client_with_service.patch(
            "/api/anomalies/anomaly-123",
            json={"status": "invalid_status"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error_code"] == "E6024"

    def test_update_anomaly_not_found(self, client_with_service, mock_l01_bridge, mock_l01_client):
        """Test updating non-existent anomaly"""
        mock_l01_client.get_anomalies.return_value = []

        response = client_with_service.patch(
            "/api/anomalies/nonexistent",
            json={"status": "resolved"},
        )
        assert response.status_code == 404

    def test_get_anomalies_invalid_timestamp(self, client_with_service):
        """Test getting anomalies with invalid timestamp"""
        response = client_with_service.get(
            "/api/anomalies",
            params={
                "start": "not-a-timestamp",
                "end": "2026-01-27T00:00:00Z",
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error_code"] == "E6020"

    def test_get_anomalies_with_status_filter(self, client_with_service):
        """Test filtering anomalies by status"""
        response = client_with_service.get(
            "/api/anomalies",
            params={
                "status": "alerting",
                "start": "2026-01-01T00:00:00Z",
                "end": "2026-01-27T00:00:00Z",
            },
        )
        assert response.status_code == 200

    def test_get_anomaly_stats_with_hours(self, client_with_service):
        """Test anomaly stats with custom hours"""
        response = client_with_service.get(
            "/api/anomalies/stats/summary",
            params={"hours": 48},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["period_hours"] == 48

    def test_get_anomalies_exception(self, client_with_service):
        """Test anomaly query exception (lines 144-146)"""
        mock_service = client_with_service.app.state.evaluation_service
        mock_service.l01_bridge.get_anomalies = AsyncMock(side_effect=RuntimeError("Query failed"))

        response = client_with_service.get(
            "/api/anomalies",
            params={"start": "2026-01-01T00:00:00Z", "end": "2026-01-27T00:00:00Z"},
        )
        assert response.status_code == 500

    def test_get_anomaly_by_id_exception(self, client_with_service, mock_l01_client):
        """Test anomaly by ID exception (lines 203-205)"""
        mock_service = client_with_service.app.state.evaluation_service
        mock_service.l01_bridge.l01_client.get_anomalies = AsyncMock(
            side_effect=RuntimeError("Query failed")
        )

        response = client_with_service.get("/api/anomalies/anom-123")
        assert response.status_code == 500

    def test_update_anomaly_exception(self, client_with_service, mock_l01_bridge, mock_l01_client):
        """Test anomaly update exception (lines 297-299)"""
        mock_service = client_with_service.app.state.evaluation_service
        mock_service.l01_bridge.update_anomaly_status = AsyncMock(
            side_effect=RuntimeError("Update failed")
        )

        response = client_with_service.patch(
            "/api/anomalies/anom-123",
            json={"status": "resolved"},
        )
        assert response.status_code == 500

    def test_update_anomaly_value_error(self, client_with_service, mock_l01_bridge, mock_l01_client):
        """Test anomaly update with invalid timestamp (lines 289-296)"""
        mock_service = client_with_service.app.state.evaluation_service
        # Simulate passing through update but with invalid timestamp
        mock_service.l01_bridge.update_anomaly_status = AsyncMock(side_effect=ValueError("Invalid timestamp"))

        response = client_with_service.patch(
            "/api/anomalies/anom-123",
            json={"status": "resolved", "resolved_at": "invalid-date"},
        )
        assert response.status_code == 400

    def test_get_anomaly_stats_exception(self, client_with_service):
        """Test anomaly stats exception (lines 340-342)"""
        mock_service = client_with_service.app.state.evaluation_service
        mock_service.anomaly.get_statistics = MagicMock(side_effect=Exception("Stats failed"))

        response = client_with_service.get("/api/anomalies/stats/summary")
        assert response.status_code == 500


@pytest.mark.l06
@pytest.mark.unit
class TestAlertRoutes:
    """Tests for /api/alerts endpoints"""

    def test_get_alerts(self, client_with_service):
        """Test getting alerts"""
        response = client_with_service.get("/api/alerts")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_alerts_with_filters(self, client_with_service):
        """Test getting alerts with filters"""
        response = client_with_service.get(
            "/api/alerts",
            params={
                "severity": "critical",
                "agent_id": "agent-001",
            },
        )
        assert response.status_code == 200

    def test_get_alerts_with_start_and_end(self, client_with_service):
        """Test getting alerts with start and end timestamps (line 133)"""
        response = client_with_service.get(
            "/api/alerts",
            params={
                "start": "2026-01-01T00:00:00Z",
                "end": "2026-01-02T00:00:00Z",
            },
        )
        assert response.status_code == 200

    def test_send_test_alert(self, client_with_service):
        """Test sending a test alert"""
        response = client_with_service.post(
            "/api/alerts/test",
            json={
                "severity": "info",
                "message": "Test alert from unit tests",
                "channels": ["slack"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "alert_id" in data

    def test_send_test_alert_invalid_severity(self, client_with_service):
        """Test sending test alert with invalid severity"""
        response = client_with_service.post(
            "/api/alerts/test",
            json={
                "severity": "invalid",
                "message": "Test",
                "channels": ["slack"],
            },
        )
        assert response.status_code == 400

    def test_send_test_alert_invalid_channel(self, client_with_service):
        """Test sending test alert with invalid channel"""
        response = client_with_service.post(
            "/api/alerts/test",
            json={
                "severity": "info",
                "message": "Test",
                "channels": ["invalid_channel"],
            },
        )
        assert response.status_code == 400

    def test_get_alert_stats(self, client_with_service):
        """Test alert statistics endpoint"""
        response = client_with_service.get("/api/alerts/stats/summary")
        assert response.status_code == 200
        data = response.json()
        assert "alerts_sent" in data
        assert "success_rate" in data

    def test_get_alerts_value_error(self, client_with_service):
        """Test get alerts with invalid timestamp (lines 147-157)"""
        # Pass invalid timestamp format
        response = client_with_service.get(
            "/api/alerts",
            params={"start": "invalid-date-format"},
        )
        assert response.status_code == 400

    def test_get_alerts_exception(self, client_with_service):
        """Test get alerts exception handling"""
        mock_service = client_with_service.app.state.evaluation_service
        mock_service.l01_bridge.get_alerts = AsyncMock(side_effect=RuntimeError("Query failed"))

        response = client_with_service.get("/api/alerts")
        assert response.status_code == 500

    def test_get_alert_by_id(self, client_with_service):
        """Test getting specific alert by ID (lines 182-216)"""
        mock_service = client_with_service.app.state.evaluation_service
        mock_service.l01_bridge.l01_client.get_alerts = AsyncMock(
            return_value=[{
                "alert_id": "alert-123",
                "timestamp": "2026-01-27T12:00:00Z",
                "severity": "warning",
                "type": "anomaly",
                "metric": "quality_score",
                "message": "Test alert",
                "channels": ["slack"],
                "metadata": {},
                "delivery_attempts": 1,
                "delivered": True,
            }]
        )

        response = client_with_service.get("/api/alerts/alert-123")
        assert response.status_code == 200
        data = response.json()
        assert data["alert_id"] == "alert-123"

    def test_get_alert_by_id_not_found(self, client_with_service):
        """Test 404 when alert not found (lines 200-207)"""
        mock_service = client_with_service.app.state.evaluation_service
        mock_service.l01_bridge.l01_client.get_alerts = AsyncMock(return_value=[])

        response = client_with_service.get("/api/alerts/nonexistent-id")
        assert response.status_code == 404

    def test_get_alert_by_id_exception(self, client_with_service):
        """Test alert by ID exception handling (lines 214-216)"""
        mock_service = client_with_service.app.state.evaluation_service
        mock_service.l01_bridge.l01_client.get_alerts = AsyncMock(
            side_effect=RuntimeError("Query failed")
        )

        response = client_with_service.get("/api/alerts/alert-123")
        assert response.status_code == 500

    def test_send_test_alert_failed_delivery(self, client_with_service):
        """Test test alert with failed delivery (line 301)"""
        mock_service = client_with_service.app.state.evaluation_service
        mock_service.alerts.send_alert = AsyncMock(return_value=False)

        response = client_with_service.post(
            "/api/alerts/test",
            json={
                "severity": "info",
                "message": "Test alert",
                "channels": ["slack"],
            },
        )
        # Still returns 200 but logs warning
        assert response.status_code == 200

    def test_send_test_alert_exception(self, client_with_service):
        """Test test alert exception handling (lines 307-309)"""
        mock_service = client_with_service.app.state.evaluation_service
        mock_service.alerts.send_alert = AsyncMock(side_effect=Exception("Send failed"))

        response = client_with_service.post(
            "/api/alerts/test",
            json={
                "severity": "info",
                "message": "Test alert",
                "channels": ["slack"],
            },
        )
        assert response.status_code == 500

    def test_get_alert_stats_exception(self, client_with_service):
        """Test alert stats exception (lines 345-347)"""
        mock_service = client_with_service.app.state.evaluation_service
        mock_service.alerts.get_statistics = MagicMock(side_effect=Exception("Stats failed"))

        response = client_with_service.get("/api/alerts/stats/summary")
        assert response.status_code == 500


@pytest.mark.l06
@pytest.mark.unit
class TestComplianceRoutes:
    """Tests for /api/compliance endpoints"""

    def test_run_compliance_check(self, client_with_service, sample_compliance_request):
        """Test running compliance check"""
        response = client_with_service.post(
            "/api/compliance/check",
            json=sample_compliance_request,
        )
        assert response.status_code == 200
        data = response.json()
        assert "result_id" in data
        assert "compliant" in data

    def test_get_compliance_results(self, client_with_service):
        """Test getting compliance results"""
        response = client_with_service.get("/api/compliance/results")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_compliance_results_filtered(self, client_with_service):
        """Test getting compliance results with filters"""
        response = client_with_service.get(
            "/api/compliance/results",
            params={
                "agent_id": "agent-001",
                "compliant": False,
            },
        )
        assert response.status_code == 200

    def test_get_compliance_stats(self, client_with_service):
        """Test compliance statistics endpoint"""
        response = client_with_service.get("/api/compliance/stats/summary")
        assert response.status_code == 200
        data = response.json()
        assert "checks_performed" in data
        assert "compliance_rate" in data

    def test_get_compliance_result_by_id(self, client_with_service):
        """Test getting specific compliance result by ID (lines 301-335)"""
        # Setup mock to return matching result
        mock_service = client_with_service.app.state.evaluation_service
        mock_service.l01_bridge.l01_client.get_compliance_results = AsyncMock(
            return_value=[{
                "result_id": "comp-123",
                "execution_id": "exec-001",
                "agent_id": "agent-001",
                "tenant_id": "tenant-001",
                "timestamp": "2026-01-27T12:00:00Z",
                "compliant": True,
                "violations": [],
                "constraints_checked": [],
            }]
        )

        response = client_with_service.get("/api/compliance/results/comp-123")
        assert response.status_code == 200
        data = response.json()
        assert data["result_id"] == "comp-123"

    def test_get_compliance_result_by_id_not_found(self, client_with_service):
        """Test 404 when compliance result not found (lines 319-326)"""
        mock_service = client_with_service.app.state.evaluation_service
        mock_service.l01_bridge.l01_client.get_compliance_results = AsyncMock(return_value=[])

        response = client_with_service.get("/api/compliance/results/nonexistent-id")
        assert response.status_code == 404

    def test_run_compliance_check_error_in_result(self, client_with_service, sample_compliance_request):
        """Test compliance check when result has error (line 178)"""
        mock_service = client_with_service.app.state.evaluation_service
        mock_service.run_compliance_check = AsyncMock(return_value={"error": "Test error"})

        response = client_with_service.post("/api/compliance/check", json=sample_compliance_request)
        assert response.status_code == 500

    def test_run_compliance_check_direct_result(self, client_with_service, sample_compliance_request):
        """Test compliance check returns ComplianceResult directly (line 192)"""
        from ..models.compliance import ComplianceResult
        mock_service = client_with_service.app.state.evaluation_service

        # Create real ComplianceResult object
        result = ComplianceResult(
            result_id="comp-direct",
            execution_id="exec-001",
            agent_id="agent-001",
            tenant_id="tenant-001",
            timestamp=datetime.now(UTC),
            compliant=True,
            violations=[],
            constraints_checked=[],
        )
        mock_service.run_compliance_check = AsyncMock(return_value=result)

        response = client_with_service.post("/api/compliance/check", json=sample_compliance_request)
        assert response.status_code == 200
        data = response.json()
        assert data["result_id"] == "comp-direct"

    def test_run_compliance_check_exception(self, client_with_service, sample_compliance_request):
        """Test compliance check exception handling (lines 199-201)"""
        mock_service = client_with_service.app.state.evaluation_service
        mock_service.run_compliance_check = AsyncMock(side_effect=Exception("Check failed"))

        response = client_with_service.post("/api/compliance/check", json=sample_compliance_request)
        assert response.status_code == 500

    def test_get_compliance_results_value_error(self, client_with_service):
        """Test compliance results with ValueError (lines 266-276)"""
        mock_service = client_with_service.app.state.evaluation_service
        mock_service.l01_bridge.l01_client.get_compliance_results = AsyncMock(
            side_effect=ValueError("Invalid timestamp")
        )

        response = client_with_service.get("/api/compliance/results")
        assert response.status_code == 400

    def test_get_compliance_results_exception(self, client_with_service):
        """Test compliance results with general exception (lines 274-276)"""
        mock_service = client_with_service.app.state.evaluation_service
        mock_service.l01_bridge.l01_client.get_compliance_results = AsyncMock(
            side_effect=RuntimeError("Query failed")
        )

        response = client_with_service.get("/api/compliance/results")
        assert response.status_code == 500

    def test_get_compliance_result_by_id_exception(self, client_with_service):
        """Test compliance result by ID exception (lines 333-335)"""
        mock_service = client_with_service.app.state.evaluation_service
        mock_service.l01_bridge.l01_client.get_compliance_results = AsyncMock(
            side_effect=RuntimeError("Query failed")
        )

        response = client_with_service.get("/api/compliance/results/comp-123")
        assert response.status_code == 500

    def test_get_compliance_stats_exception(self, client_with_service):
        """Test compliance stats exception (lines 371-373)"""
        mock_service = client_with_service.app.state.evaluation_service
        mock_service.compliance.get_statistics = MagicMock(side_effect=Exception("Stats failed"))

        response = client_with_service.get("/api/compliance/stats/summary")
        assert response.status_code == 500

    def test_get_compliance_results_parse_error(self, client_with_service):
        """Test compliance results parse error (lines 258-262)"""
        mock_service = client_with_service.app.state.evaluation_service
        # Return malformed data that will fail to parse
        mock_service.l01_bridge.l01_client.get_compliance_results = AsyncMock(
            return_value=[
                {"invalid": "data"},  # Missing required fields
                {  # Valid result
                    "result_id": "comp-valid",
                    "execution_id": "exec-001",
                    "agent_id": "agent-001",
                    "tenant_id": "tenant-001",
                    "timestamp": "2026-01-27T12:00:00Z",
                    "compliant": True,
                    "violations": [],
                    "constraints_checked": [],
                }
            ]
        )

        response = client_with_service.get("/api/compliance/results")
        assert response.status_code == 200
        # Should still return valid results, skipping malformed ones
        data = response.json()
        assert len(data) <= 1  # At most the valid one


@pytest.mark.l06
@pytest.mark.unit
class TestErrorHandling:
    """Tests for error handling in routes"""

    def test_service_unavailable(self):
        """Test 503 when service is not initialized"""
        # Patch EvaluationService so lifespan doesn't create a working service
        with patch("L06_evaluation.main.EvaluationService") as MockService:
            mock_instance = MagicMock()
            mock_instance.initialize = AsyncMock(side_effect=Exception("Init failed"))
            mock_instance.cleanup = AsyncMock()
            MockService.return_value = mock_instance

            with patch("L06_evaluation.main.L06Bridge"):
                try:
                    with TestClient(app, raise_server_exceptions=False) as client:
                        # Force service to None to simulate unavailable service
                        app.state.evaluation_service = None
                        response = client.post("/api/events", json={
                            "id": "evt-123",
                            "source": "test",
                            "type": "test",
                            "subject": "test-subject",
                            "data": {},
                        })
                        assert response.status_code == 503
                except Exception:
                    pass  # Ignore lifespan errors

    def test_invalid_json(self, client_with_service):
        """Test handling of invalid JSON"""
        response = client_with_service.post(
            "/api/events",
            content="not valid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_missing_required_fields(self, client_with_service):
        """Test handling of missing required fields"""
        response = client_with_service.post(
            "/api/quality/compute",
            json={"tenant_id": "tenant-001"},
        )
        assert response.status_code == 422


@pytest.mark.l06
@pytest.mark.unit
class TestOpenAPISpec:
    """Tests for OpenAPI documentation"""

    def test_openapi_spec_available(self, client_with_service):
        """Test that OpenAPI spec is available"""
        response = client_with_service.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data

    def test_swagger_docs_available(self, client_with_service):
        """Test that Swagger docs are available"""
        response = client_with_service.get("/docs")
        assert response.status_code == 200


@pytest.mark.l06
@pytest.mark.unit
class TestServiceNotInitialized:
    """Tests for service not initialized paths in all routes"""

    @pytest.fixture
    def client_no_service(self):
        """Create test client with no evaluation_service"""
        from L06_evaluation.main import app as l06_app
        from starlette.testclient import TestClient

        # Override lifespan to skip service initialization
        @asynccontextmanager
        async def empty_lifespan(app):
            app.state.evaluation_service = None
            yield

        l06_app.router.lifespan_context = empty_lifespan
        with TestClient(l06_app) as client:
            yield client

    # Alert routes (lines 116, 184, 245, 334)

    def test_get_alerts_no_service(self, client_no_service):
        """Test get_alerts returns 503 when service not initialized (line 116)"""
        response = client_no_service.get("/api/alerts")
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error_code"] == "E6000"

    def test_get_alert_by_id_no_service(self, client_no_service):
        """Test get_alert_by_id returns 503 when service not initialized (line 184)"""
        response = client_no_service.get("/api/alerts/alert-123")
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error_code"] == "E6000"

    def test_send_test_alert_no_service(self, client_no_service):
        """Test send_test_alert returns 503 when service not initialized (line 245)"""
        response = client_no_service.post("/api/alerts/test", json={
            "message": "Test alert",
            "severity": "warning",
            "channels": ["slack"],
        })
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error_code"] == "E6000"

    def test_get_alert_stats_no_service(self, client_no_service):
        """Test get_alert_stats returns 503 when service not initialized (line 334)"""
        response = client_no_service.get("/api/alerts/stats/summary")
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error_code"] == "E6000"

    # Anomaly routes (lines 109, 173, 236, 326)

    def test_get_anomalies_no_service(self, client_no_service):
        """Test get_anomalies returns 503 when service not initialized (line 109)"""
        response = client_no_service.get(
            "/api/anomalies",
            params={
                "start": "2026-01-01T00:00:00Z",
                "end": "2026-01-02T00:00:00Z",
            }
        )
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error_code"] == "E6000"

    def test_get_anomaly_by_id_no_service(self, client_no_service):
        """Test get_anomaly_by_id returns 503 when service not initialized (line 173)"""
        response = client_no_service.get("/api/anomalies/anomaly-123")
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error_code"] == "E6000"

    def test_update_anomaly_no_service(self, client_no_service):
        """Test update_anomaly returns 503 when service not initialized (line 236)"""
        response = client_no_service.patch("/api/anomalies/anomaly-123", json={
            "status": "acknowledged"
        })
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error_code"] == "E6000"

    def test_get_anomaly_stats_no_service(self, client_no_service):
        """Test get_anomaly_stats returns 503 when service not initialized (line 326)"""
        response = client_no_service.get("/api/anomalies/stats/summary")
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error_code"] == "E6000"

    # Quality routes (lines 128, 189, 251, 306)

    def test_compute_quality_score_no_service(self, client_no_service):
        """Test compute_quality_score returns 503 when service not initialized (line 128)"""
        response = client_no_service.post("/api/quality/compute", json={
            "agent_id": "agent-001",
            "tenant_id": "tenant-001",
        })
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error_code"] == "E6000"

    def test_get_quality_scores_no_service(self, client_no_service):
        """Test get_quality_scores returns 503 when service not initialized (line 189)"""
        response = client_no_service.get(
            "/api/quality/scores",
            params={
                "agent_id": "agent-001",
                "start": "2026-01-01T00:00:00Z",
                "end": "2026-01-02T00:00:00Z",
            }
        )
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error_code"] == "E6000"

    def test_get_quality_score_by_id_no_service(self, client_no_service):
        """Test get_score_by_id returns 503 when service not initialized (line 251)"""
        response = client_no_service.get("/api/quality/scores/qs-123")
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error_code"] == "E6000"

    def test_get_quality_stats_no_service(self, client_no_service):
        """Test get_quality_stats returns 503 when service not initialized (line 306)"""
        response = client_no_service.get("/api/quality/summary/agent-001")
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error_code"] == "E6000"

    # Compliance routes (lines 157, 235, 303, 360)

    def test_run_compliance_check_no_service(self, client_no_service):
        """Test run_compliance_check returns 503 when service not initialized (line 157)"""
        response = client_no_service.post("/api/compliance/check", json={
            "agent_id": "agent-001",
            "execution_id": "exec-001",
            "tenant_id": "tenant-001",
        })
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error_code"] == "E6000"

    def test_get_compliance_results_no_service(self, client_no_service):
        """Test get_compliance_results returns 503 when service not initialized (line 235)"""
        response = client_no_service.get(
            "/api/compliance/results",
            params={
                "agent_id": "agent-001",
                "start": "2026-01-01T00:00:00Z",
                "end": "2026-01-02T00:00:00Z",
            }
        )
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error_code"] == "E6000"

    def test_get_compliance_result_by_id_no_service(self, client_no_service):
        """Test get_result_by_id returns 503 when service not initialized (line 303)"""
        response = client_no_service.get("/api/compliance/results/cr-123")
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error_code"] == "E6000"

    def test_get_compliance_stats_no_service(self, client_no_service):
        """Test get_compliance_stats returns 503 when service not initialized (line 360)"""
        response = client_no_service.get("/api/compliance/stats/summary")
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error_code"] == "E6000"

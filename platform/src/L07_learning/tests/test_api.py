"""
L07 Learning Layer - API Tests

Tests for REST API endpoints (TDD - tests written first).
"""

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from L07_learning.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Create async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


# =============================================================================
# Health Endpoint Tests
# =============================================================================

@pytest.mark.l07
@pytest.mark.unit
class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_returns_200(self, client):
        """Test that /health returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "l07-learning"

    def test_health_live_returns_200(self, client):
        """Test that /health/live returns 200."""
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    def test_health_ready_returns_200(self, client):
        """Test that /health/ready returns status."""
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


# =============================================================================
# Metrics Endpoint Tests
# =============================================================================

@pytest.mark.l07
@pytest.mark.unit
class TestMetricsEndpoint:
    """Tests for metrics endpoint."""

    def test_metrics_returns_200(self, client):
        """Test that /metrics returns 200."""
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_returns_prometheus_format(self, client):
        """Test that /metrics returns Prometheus format."""
        response = client.get("/metrics")
        content_type = response.headers.get("content-type", "")
        assert "text" in content_type
        # Should contain L07 metrics
        assert b"l07_" in response.content


# =============================================================================
# Dataset Endpoint Tests
# =============================================================================

@pytest.mark.l07
@pytest.mark.unit
class TestDatasetEndpoints:
    """Tests for dataset management endpoints."""

    def test_create_dataset_returns_201(self, client):
        """Test that POST /datasets returns 201."""
        response = client.post(
            "/datasets",
            json={
                "name": "test-dataset",
                "description": "A test dataset"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert "dataset_id" in data
        assert data["name"] == "test-dataset"

    def test_create_dataset_with_examples(self, client):
        """Test creating dataset with initial examples."""
        response = client.post(
            "/datasets",
            json={
                "name": "dataset-with-examples",
                "description": "Dataset with examples",
                "examples": [
                    {
                        "input_text": "What is 2+2?",
                        "output_text": "4",
                        "domain": "math"
                    },
                    {
                        "input_text": "What is the capital of France?",
                        "output_text": "Paris",
                        "domain": "geography"
                    }
                ]
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert "dataset_id" in data

    def test_get_dataset_returns_200(self, client):
        """Test that GET /datasets/{id} returns dataset."""
        # First create a dataset
        create_response = client.post(
            "/datasets",
            json={"name": "get-test-dataset"}
        )
        dataset_id = create_response.json()["dataset_id"]

        # Then get it
        response = client.get(f"/datasets/{dataset_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["dataset_id"] == dataset_id
        assert data["name"] == "get-test-dataset"

    def test_get_dataset_not_found_returns_404(self, client):
        """Test that GET /datasets/{id} returns 404 for missing dataset."""
        response = client.get("/datasets/non-existent-id")
        assert response.status_code == 404

    def test_list_datasets_returns_200(self, client):
        """Test that GET /datasets returns list."""
        response = client.get("/datasets")
        assert response.status_code == 200
        data = response.json()
        assert "datasets" in data
        assert isinstance(data["datasets"], list)


# =============================================================================
# Job Endpoint Tests
# =============================================================================

@pytest.mark.l07
@pytest.mark.unit
class TestJobEndpoints:
    """Tests for training job endpoints."""

    def test_create_job_returns_202(self, client):
        """Test that POST /jobs returns 202 (accepted)."""
        # First create a dataset
        ds_response = client.post(
            "/datasets",
            json={"name": "job-test-dataset"}
        )
        dataset_id = ds_response.json()["dataset_id"]

        # Create job
        response = client.post(
            "/jobs",
            json={
                "dataset_id": dataset_id,
                "base_model_id": "gpt2",
                "job_type": "sft"
            }
        )
        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] in ["pending", "initializing"]

    def test_get_job_returns_200(self, client):
        """Test that GET /jobs/{id} returns job status."""
        # Create dataset and job
        ds_response = client.post(
            "/datasets",
            json={"name": "get-job-test"}
        )
        dataset_id = ds_response.json()["dataset_id"]

        job_response = client.post(
            "/jobs",
            json={
                "dataset_id": dataset_id,
                "base_model_id": "gpt2"
            }
        )
        job_id = job_response.json()["job_id"]

        # Get job status
        response = client.get(f"/jobs/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert "status" in data

    def test_get_job_not_found_returns_404(self, client):
        """Test that GET /jobs/{id} returns 404 for missing job."""
        response = client.get("/jobs/non-existent-id")
        assert response.status_code == 404

    def test_get_job_progress_returns_200(self, client):
        """Test that GET /jobs/{id}/progress returns progress."""
        # Create dataset and job
        ds_response = client.post(
            "/datasets",
            json={"name": "progress-test"}
        )
        dataset_id = ds_response.json()["dataset_id"]

        job_response = client.post(
            "/jobs",
            json={
                "dataset_id": dataset_id,
                "base_model_id": "gpt2"
            }
        )
        job_id = job_response.json()["job_id"]

        # Get progress
        response = client.get(f"/jobs/{job_id}/progress")
        assert response.status_code == 200
        data = response.json()
        assert "progress_percent" in data or "status" in data

    def test_list_jobs_returns_200(self, client):
        """Test that GET /jobs returns list."""
        response = client.get("/jobs")
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert isinstance(data["jobs"], list)

    def test_cancel_job_returns_200(self, client):
        """Test that POST /jobs/{id}/cancel cancels job."""
        # Create dataset and job
        ds_response = client.post(
            "/datasets",
            json={"name": "cancel-test"}
        )
        dataset_id = ds_response.json()["dataset_id"]

        job_response = client.post(
            "/jobs",
            json={
                "dataset_id": dataset_id,
                "base_model_id": "gpt2"
            }
        )
        job_id = job_response.json()["job_id"]

        # Cancel job
        response = client.post(f"/jobs/{job_id}/cancel")
        assert response.status_code in [200, 409]  # 409 if already terminal


# =============================================================================
# Model Endpoint Tests
# =============================================================================

@pytest.mark.l07
@pytest.mark.unit
class TestModelEndpoints:
    """Tests for model management endpoints."""

    def test_register_model_returns_201(self, client):
        """Test that POST /models returns 201."""
        response = client.post(
            "/models",
            json={
                "name": "test-model",
                "model_type": "fine_tuned",
                "artifact_path": "/tmp/test-model"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert "model_id" in data
        assert data["name"] == "test-model"

    def test_get_model_returns_200(self, client):
        """Test that GET /models/{id} returns model."""
        # Register model
        create_response = client.post(
            "/models",
            json={
                "name": "get-model-test",
                "model_type": "fine_tuned",
                "artifact_path": "/tmp/test"
            }
        )
        model_id = create_response.json()["model_id"]

        # Get model
        response = client.get(f"/models/{model_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["model_id"] == model_id

    def test_get_model_not_found_returns_404(self, client):
        """Test that GET /models/{id} returns 404 for missing model."""
        response = client.get("/models/non-existent-id")
        assert response.status_code == 404

    def test_list_models_returns_200(self, client):
        """Test that GET /models returns list."""
        response = client.get("/models")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert isinstance(data["models"], list)

    def test_transition_model_stage_returns_200(self, client):
        """Test that PATCH /models/{id}/stage transitions stage."""
        # Register model
        create_response = client.post(
            "/models",
            json={
                "name": "stage-test-model",
                "model_type": "fine_tuned",
                "artifact_path": "/tmp/test"
            }
        )
        model_id = create_response.json()["model_id"]

        # Transition to staging
        response = client.patch(
            f"/models/{model_id}/stage",
            json={
                "stage": "staging",
                "notes": "Ready for testing"
            }
        )
        assert response.status_code in [200, 400]  # 400 if validation fails


# =============================================================================
# Example Endpoint Tests
# =============================================================================

@pytest.mark.l07
@pytest.mark.unit
class TestExampleEndpoints:
    """Tests for training example endpoints."""

    def test_list_examples_returns_200(self, client):
        """Test that GET /examples returns list."""
        response = client.get("/examples")
        assert response.status_code == 200
        data = response.json()
        assert "examples" in data
        assert isinstance(data["examples"], list)

    def test_list_examples_with_filters(self, client):
        """Test that GET /examples with filters works."""
        response = client.get(
            "/examples",
            params={
                "domain": "code_generation",
                "limit": 10
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "examples" in data

    def test_get_example_not_found_returns_404(self, client):
        """Test that GET /examples/{id} returns 404 for missing example."""
        response = client.get("/examples/non-existent-id")
        assert response.status_code == 404


# =============================================================================
# Root Endpoint Tests
# =============================================================================

@pytest.mark.l07
@pytest.mark.unit
class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_returns_200(self, client):
        """Test that GET / returns service info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "L07 Learning Layer"
        assert "endpoints" in data

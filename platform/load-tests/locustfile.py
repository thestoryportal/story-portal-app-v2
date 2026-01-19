"""
Locust Load Testing Suite for V2 Platform
==========================================

This file defines load testing scenarios for the V2 platform API gateway and services.

Usage:
    # Run with web UI
    locust -f locustfile.py --host=http://localhost:8009

    # Run headless with specific user count and spawn rate
    locust -f locustfile.py --host=http://localhost:8009 --users 100 --spawn-rate 10 --run-time 5m --headless

    # Run specific test class
    locust -f locustfile.py --host=http://localhost:8009 TestAPIGateway

Test Scenarios:
    - TestAPIGateway: General API gateway health and routing
    - TestDataLayer: L01 data layer operations (CRUD)
    - TestTaskExecution: L03 task execution workflows
    - TestModelGateway: L04 model gateway LLM requests
    - TestFullUserJourney: End-to-end user workflows
"""

from locust import HttpUser, TaskSet, task, between, events
from locust.exception import RescheduleTask
import random
import json
import time
from faker import Faker
from typing import Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Faker for generating test data
fake = Faker()

# ============================================================================
# Configuration and Constants
# ============================================================================

# Test authentication token (for load testing only)
# The gateway's mock consumer_lookup_fn accepts any token for testing
TEST_API_KEY = "loadtest_api_key_12345"

# Service endpoints
SERVICES = {
    "l01_data_layer": ":8001",
    "l02_runtime": ":8002",
    "l03_tool_execution": ":8003",
    "l04_model_gateway": ":8004",
    "l05_planning": ":8005",
    "l06_evaluation": ":8006",
    "l07_learning": ":8007",
    "l09_api_gateway": ":8009",
    "l10_human_interface": ":8010",
    "l11_integration": ":8011",
    "l12_nl_interface": ":8012",
}

# Success criteria thresholds
PERFORMANCE_THRESHOLDS = {
    "max_response_time_ms": 500,  # 95th percentile
    "max_error_rate_percent": 1,  # Maximum 1% error rate
    "min_requests_per_second": 100,  # Minimum throughput
}

# Sample test data
SAMPLE_TASKS = [
    "Analyze the customer feedback from Q4",
    "Generate a summary report of sales data",
    "Extract key insights from the meeting transcript",
    "Create a project timeline based on requirements",
    "Translate this document to Spanish",
]

SAMPLE_TOOLS = [
    "file_reader",
    "data_analyzer",
    "report_generator",
    "translator",
    "summarizer",
]

# ============================================================================
# Custom Event Handlers for Metrics
# ============================================================================

# Track custom metrics
request_times = []
error_count = 0
success_count = 0

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Track all request metrics for threshold validation."""
    global error_count, success_count, request_times

    request_times.append(response_time)

    if exception:
        error_count += 1
    else:
        success_count += 1

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Validate performance against thresholds at test completion."""
    global error_count, success_count, request_times

    total_requests = error_count + success_count

    if total_requests == 0:
        logger.warning("No requests completed")
        return

    # Calculate metrics
    error_rate = (error_count / total_requests) * 100
    p95_response_time = sorted(request_times)[int(len(request_times) * 0.95)] if request_times else 0

    # Validate thresholds
    logger.info("=" * 80)
    logger.info("LOAD TEST RESULTS SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total Requests: {total_requests}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {error_count}")
    logger.info(f"Error Rate: {error_rate:.2f}%")
    logger.info(f"95th Percentile Response Time: {p95_response_time:.2f}ms")
    logger.info("=" * 80)

    # Check thresholds
    threshold_passed = True

    if p95_response_time > PERFORMANCE_THRESHOLDS["max_response_time_ms"]:
        logger.error(f"❌ FAILED: P95 response time ({p95_response_time:.2f}ms) exceeds threshold ({PERFORMANCE_THRESHOLDS['max_response_time_ms']}ms)")
        threshold_passed = False
    else:
        logger.info(f"✅ PASSED: P95 response time within threshold")

    if error_rate > PERFORMANCE_THRESHOLDS["max_error_rate_percent"]:
        logger.error(f"❌ FAILED: Error rate ({error_rate:.2f}%) exceeds threshold ({PERFORMANCE_THRESHOLDS['max_error_rate_percent']}%)")
        threshold_passed = False
    else:
        logger.info(f"✅ PASSED: Error rate within threshold")

    logger.info("=" * 80)

    if threshold_passed:
        logger.info("🎉 ALL PERFORMANCE THRESHOLDS PASSED")
    else:
        logger.error("⚠️  SOME PERFORMANCE THRESHOLDS FAILED")

    logger.info("=" * 80)

# ============================================================================
# Helper Functions
# ============================================================================

def generate_task_payload() -> Dict[str, Any]:
    """Generate a realistic task payload for testing."""
    return {
        "task_id": fake.uuid4(),
        "task_type": random.choice(["analysis", "generation", "extraction", "translation"]),
        "description": random.choice(SAMPLE_TASKS),
        "parameters": {
            "model": random.choice(["gpt-4", "gpt-3.5-turbo", "claude-2"]),
            "max_tokens": random.randint(100, 2000),
            "temperature": random.uniform(0.1, 1.0),
        },
        "metadata": {
            "user_id": fake.uuid4(),
            "session_id": fake.uuid4(),
            "timestamp": int(time.time()),
        }
    }

def generate_tool_execution_payload() -> Dict[str, Any]:
    """Generate a tool execution payload."""
    return {
        "tool_name": random.choice(SAMPLE_TOOLS),
        "parameters": {
            "input": fake.text(max_nb_chars=200),
            "options": {
                "format": random.choice(["json", "text", "markdown"]),
                "language": random.choice(["en", "es", "fr"]),
            }
        },
        "context": {
            "task_id": fake.uuid4(),
            "execution_id": fake.uuid4(),
        }
    }

def generate_data_record() -> Dict[str, Any]:
    """Generate a data record for CRUD operations."""
    return {
        "record_id": fake.uuid4(),
        "entity_type": random.choice(["user", "task", "result", "session"]),
        "data": {
            "name": fake.name(),
            "email": fake.email(),
            "content": fake.text(max_nb_chars=500),
            "created_at": fake.date_time_this_year().isoformat(),
            "status": random.choice(["active", "pending", "completed"]),
        },
        "tags": [fake.word() for _ in range(random.randint(1, 5))],
    }

# ============================================================================
# Task Sets for Different Load Patterns
# ============================================================================

class APIGatewayTasks(TaskSet):
    """Task set for testing API gateway operations."""

    @task(5)
    def health_check(self):
        """Health check endpoint (frequent)."""
        self.client.get("/health/live", name="GET /health/live")

    @task(3)
    def readiness_check(self):
        """Readiness check endpoint."""
        self.client.get("/health/ready", name="GET /health/ready")

    @task(2)
    def metrics_endpoint(self):
        """Metrics endpoint."""
        self.client.get("/metrics", name="GET /metrics")

    @task(1)
    def api_info(self):
        """API information endpoint."""
        self.client.get("/api/v1/info", name="GET /api/v1/info")

class DataLayerTasks(TaskSet):
    """Task set for testing L01 data layer CRUD operations."""

    def on_start(self):
        """Initialize with some test records."""
        self.created_records = []

    @task(3)
    def create_record(self):
        """Create a new data record."""
        payload = generate_data_record()
        with self.client.post(
            "/api/v1/data/records",
            json=payload,
            name="POST /api/v1/data/records",
            catch_response=True
        ) as response:
            if response.status_code == 201:
                data = response.json()
                self.created_records.append(data.get("record_id"))
                response.success()
            else:
                response.failure(f"Failed to create record: {response.status_code}")

    @task(5)
    def read_record(self):
        """Read a data record."""
        if self.created_records:
            record_id = random.choice(self.created_records)
            self.client.get(
                f"/api/v1/data/records/{record_id}",
                name="GET /api/v1/data/records/:id"
            )
        else:
            # Fall back to listing records
            self.client.get("/api/v1/data/records", name="GET /api/v1/data/records")

    @task(2)
    def update_record(self):
        """Update a data record."""
        if self.created_records:
            record_id = random.choice(self.created_records)
            payload = {"data": {"status": "updated"}}
            self.client.patch(
                f"/api/v1/data/records/{record_id}",
                json=payload,
                name="PATCH /api/v1/data/records/:id"
            )

    @task(1)
    def delete_record(self):
        """Delete a data record."""
        if self.created_records:
            record_id = self.created_records.pop()
            self.client.delete(
                f"/api/v1/data/records/{record_id}",
                name="DELETE /api/v1/data/records/:id"
            )

    @task(4)
    def search_records(self):
        """Search data records."""
        params = {
            "entity_type": random.choice(["user", "task", "result"]),
            "status": random.choice(["active", "pending", "completed"]),
            "limit": random.randint(10, 50),
        }
        self.client.get(
            "/api/v1/data/records/search",
            params=params,
            name="GET /api/v1/data/records/search"
        )

class TaskExecutionTasks(TaskSet):
    """Task set for testing L03 task execution workflows."""

    def on_start(self):
        """Initialize task tracking."""
        self.active_tasks = []

    @task(4)
    def submit_task(self):
        """Submit a new task for execution."""
        payload = generate_task_payload()
        with self.client.post(
            "/api/v1/tasks",
            json=payload,
            name="POST /api/v1/tasks",
            catch_response=True
        ) as response:
            if response.status_code == 201:
                data = response.json()
                self.active_tasks.append(data.get("task_id"))
                response.success()
            else:
                response.failure(f"Failed to submit task: {response.status_code}")

    @task(5)
    def get_task_status(self):
        """Get task execution status."""
        if self.active_tasks:
            task_id = random.choice(self.active_tasks)
            self.client.get(
                f"/api/v1/tasks/{task_id}/status",
                name="GET /api/v1/tasks/:id/status"
            )
        else:
            raise RescheduleTask()

    @task(2)
    def get_task_result(self):
        """Get task execution result."""
        if self.active_tasks:
            task_id = random.choice(self.active_tasks)
            self.client.get(
                f"/api/v1/tasks/{task_id}/result",
                name="GET /api/v1/tasks/:id/result"
            )
        else:
            raise RescheduleTask()

    @task(1)
    def cancel_task(self):
        """Cancel a running task."""
        if self.active_tasks:
            task_id = self.active_tasks.pop()
            self.client.post(
                f"/api/v1/tasks/{task_id}/cancel",
                name="POST /api/v1/tasks/:id/cancel"
            )

    @task(3)
    def list_tasks(self):
        """List all tasks."""
        params = {
            "status": random.choice(["pending", "running", "completed", "failed"]),
            "limit": random.randint(10, 50),
        }
        self.client.get(
            "/api/v1/tasks",
            params=params,
            name="GET /api/v1/tasks"
        )

class ModelGatewayTasks(TaskSet):
    """Task set for testing L04 model gateway LLM requests."""

    @task(4)
    def chat_completion(self):
        """Send a chat completion request."""
        payload = {
            "model": random.choice(["gpt-4", "gpt-3.5-turbo", "claude-2"]),
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": fake.text(max_nb_chars=200)},
            ],
            "max_tokens": random.randint(100, 500),
            "temperature": random.uniform(0.1, 1.0),
        }
        self.client.post(
            "/api/v1/llm/chat/completions",
            json=payload,
            name="POST /api/v1/llm/chat/completions"
        )

    @task(2)
    def text_completion(self):
        """Send a text completion request."""
        payload = {
            "model": random.choice(["gpt-3.5-turbo-instruct", "text-davinci-003"]),
            "prompt": fake.text(max_nb_chars=200),
            "max_tokens": random.randint(50, 300),
        }
        self.client.post(
            "/api/v1/llm/completions",
            json=payload,
            name="POST /api/v1/llm/completions"
        )

    @task(1)
    def list_models(self):
        """List available models."""
        self.client.get("/api/v1/llm/models", name="GET /api/v1/llm/models")

class ToolExecutionTasks(TaskSet):
    """Task set for testing tool execution."""

    @task(3)
    def execute_tool(self):
        """Execute a tool."""
        payload = generate_tool_execution_payload()
        self.client.post(
            "/api/v1/tools/execute",
            json=payload,
            name="POST /api/v1/tools/execute"
        )

    @task(2)
    def list_tools(self):
        """List available tools."""
        self.client.get("/api/v1/tools", name="GET /api/v1/tools")

    @task(1)
    def get_tool_info(self):
        """Get tool information."""
        tool_name = random.choice(SAMPLE_TOOLS)
        self.client.get(
            f"/api/v1/tools/{tool_name}",
            name="GET /api/v1/tools/:name"
        )

# ============================================================================
# User Classes for Different Load Test Scenarios
# ============================================================================

class TestAPIGateway(HttpUser):
    """
    Test API Gateway endpoints.

    Simulates users hitting health checks, metrics, and basic API info.
    Lightweight load to verify gateway routing and health.
    """
    tasks = [APIGatewayTasks]
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    weight = 3

    def on_start(self):
        """Set up authentication headers for all requests."""
        self.client.headers.update({
            "Authorization": f"Bearer {TEST_API_KEY}"
        })

class TestDataLayer(HttpUser):
    """
    Test L01 Data Layer CRUD operations.

    Simulates users performing create, read, update, delete operations
    on data records. Tests database performance under load.
    """
    tasks = [DataLayerTasks]
    wait_time = between(2, 5)
    weight = 2

    def on_start(self):
        """Set up authentication headers for all requests."""
        self.client.headers.update({
            "Authorization": f"Bearer {TEST_API_KEY}"
        })

class TestTaskExecution(HttpUser):
    """
    Test L03 Task Execution workflows.

    Simulates users submitting tasks, checking status, and retrieving results.
    Tests the task execution pipeline and queueing system.
    """
    tasks = [TaskExecutionTasks]
    wait_time = between(3, 7)
    weight = 2

    def on_start(self):
        """Set up authentication headers for all requests."""
        self.client.headers.update({
            "Authorization": f"Bearer {TEST_API_KEY}"
        })

class TestModelGateway(HttpUser):
    """
    Test L04 Model Gateway LLM requests.

    Simulates users sending LLM requests for chat completions and text generation.
    Tests LLM integration and token usage tracking. This is typically heavier load.
    """
    tasks = [ModelGatewayTasks]
    wait_time = between(5, 10)  # Longer wait time due to LLM latency
    weight = 1

    def on_start(self):
        """Set up authentication headers for all requests."""
        self.client.headers.update({
            "Authorization": f"Bearer {TEST_API_KEY}"
        })

class TestToolExecution(HttpUser):
    """
    Test tool execution workflows.

    Simulates users executing various tools (file operations, data processing, etc.).
    Tests tool integration and execution performance.
    """
    tasks = [ToolExecutionTasks]
    wait_time = between(2, 5)
    weight = 2

    def on_start(self):
        """Set up authentication headers for all requests."""
        self.client.headers.update({
            "Authorization": f"Bearer {TEST_API_KEY}"
        })

class TestFullUserJourney(HttpUser):
    """
    Test complete user journey end-to-end.

    Simulates realistic user workflows: submit task -> check status -> get result.
    Tests the full platform integration.
    """
    wait_time = between(5, 10)
    weight = 1

    def on_start(self):
        """Set up authentication headers for all requests."""
        self.client.headers.update({
            "Authorization": f"Bearer {TEST_API_KEY}"
        })

    @task
    def user_journey(self):
        """Complete user journey: submit task, poll status, get result."""
        # Step 1: Health check
        self.client.get("/health/ready", name="Journey: Health Check")

        # Step 2: Submit task
        task_payload = generate_task_payload()
        with self.client.post(
            "/api/v1/tasks",
            json=task_payload,
            name="Journey: Submit Task",
            catch_response=True
        ) as response:
            if response.status_code != 201:
                response.failure("Task submission failed")
                return

            task_id = response.json().get("task_id")

        # Step 3: Poll status (simulate waiting)
        time.sleep(2)
        for _ in range(3):
            with self.client.get(
                f"/api/v1/tasks/{task_id}/status",
                name="Journey: Check Status",
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    status = response.json().get("status")
                    if status in ["completed", "failed"]:
                        response.success()
                        break
                time.sleep(1)

        # Step 4: Get result
        self.client.get(
            f"/api/v1/tasks/{task_id}/result",
            name="Journey: Get Result"
        )

# ============================================================================
# Shape Classes for Load Patterns
# ============================================================================

class StepLoadShape:
    """
    Step load pattern: gradually increase users in steps.

    Useful for finding the breaking point of the system.
    """
    step_time = 60  # Each step lasts 60 seconds
    step_load = 10  # Increase by 10 users each step
    spawn_rate = 5
    time_limit = 600  # 10 minutes total

    def tick(self):
        run_time = self.get_run_time()

        if run_time > self.time_limit:
            return None

        current_step = run_time // self.step_time
        return (current_step * self.step_load, self.spawn_rate)

# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    """
    Entry point for running load tests.

    Example commands:
        # Web UI mode with 50 users
        locust -f locustfile.py --host=http://localhost:8009 --users 50 --spawn-rate 5

        # Headless mode for CI/CD
        locust -f locustfile.py --host=http://localhost:8009 --users 100 --spawn-rate 10 --run-time 5m --headless --html report.html

        # Test specific scenario
        locust -f locustfile.py --host=http://localhost:8009 TestAPIGateway --users 20 --spawn-rate 2 --run-time 2m --headless
    """
    pass

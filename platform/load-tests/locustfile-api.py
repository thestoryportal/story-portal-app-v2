"""
Locust Load Testing Suite for V2 Platform API Endpoints
========================================================

Tests the three operational API v1 endpoints after Day 2 API Gateway fix:
- /api/v1/agents (CRUD for agents)
- /api/v1/goals (CRUD for goals)
- /api/v1/tasks (CRUD for tasks)

Usage:
    # Smoke test (quick verification)
    locust -f locustfile-api.py --host=http://localhost:8009 --users 10 --spawn-rate 5 --run-time 30s --headless

    # Normal load test
    locust -f locustfile-api.py --host=http://localhost:8009 --users 100 --spawn-rate 10 --run-time 5m --headless

    # Stress test
    locust -f locustfile-api.py --host=http://localhost:8009 --users 500 --spawn-rate 50 --run-time 10m --headless
"""

from locust import HttpUser, TaskSet, task, between, events
import random
import json
import time
from faker import Faker
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Faker for generating test data
fake = Faker()

# ============================================================================
# Configuration
# ============================================================================

# Test API key (matches Day 2 testing)
TEST_API_KEY = "12345678901234567890123456789012"  # 32+ characters

# Performance thresholds (based on Day 2 baseline results)
PERFORMANCE_THRESHOLDS = {
    "max_response_time_ms": 500,  # 95th percentile < 500ms
    "max_error_rate_percent": 1,  # < 1% error rate
}

# ============================================================================
# Metrics Tracking
# ============================================================================

request_times = []
error_count = 0
success_count = 0

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Track all request metrics."""
    global error_count, success_count, request_times

    request_times.append(response_time)

    if exception:
        error_count += 1
    else:
        success_count += 1

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Validate performance against thresholds."""
    global error_count, success_count, request_times

    total_requests = error_count + success_count

    if total_requests == 0:
        logger.warning("No requests completed")
        return

    # Calculate metrics
    error_rate = (error_count / total_requests) * 100
    p95_response_time = sorted(request_times)[int(len(request_times) * 0.95)] if request_times else 0

    # Report results
    logger.info("=" * 80)
    logger.info("API LOAD TEST RESULTS")
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
        logger.error(f"❌ FAILED: P95 response time ({p95_response_time:.2f}ms) > {PERFORMANCE_THRESHOLDS['max_response_time_ms']}ms")
        threshold_passed = False
    else:
        logger.info(f"✅ PASSED: P95 response time within threshold")

    if error_rate > PERFORMANCE_THRESHOLDS["max_error_rate_percent"]:
        logger.error(f"❌ FAILED: Error rate ({error_rate:.2f}%) > {PERFORMANCE_THRESHOLDS['max_error_rate_percent']}%")
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
# Task Sets
# ============================================================================

class AgentOperations(TaskSet):
    """Test agent CRUD operations."""

    def on_start(self):
        """Initialize with auth headers and storage for created agents."""
        self.created_agents = []
        self.headers = {
            "X-API-Key": TEST_API_KEY,
            "Content-Type": "application/json"
        }

    @task(5)
    def create_agent(self):
        """Create a new agent."""
        payload = {
            "name": fake.user_name(),
            "agent_type": random.choice(["simple", "complex", "specialized"]),
            "configuration": {
                "max_tokens": random.randint(100, 2000),
                "temperature": round(random.uniform(0.1, 1.0), 2),
            },
            "metadata": {
                "created_by": "load_test",
                "test_run": int(time.time()),
            }
        }

        response = self.client.post(
            "/api/v1/agents/",
            headers=self.headers,
            json=payload,
            name="POST /api/v1/agents/"
        )

        if response.status_code == 201:
            try:
                agent = response.json()
                self.created_agents.append(agent["id"])
            except (ValueError, KeyError):
                pass

    @task(10)
    def list_agents(self):
        """List agents."""
        self.client.get(
            "/api/v1/agents/",
            headers=self.headers,
            name="GET /api/v1/agents/"
        )

    @task(3)
    def get_agent(self):
        """Get agent by ID."""
        if self.created_agents:
            agent_id = random.choice(self.created_agents)
            self.client.get(
                f"/api/v1/agents/{agent_id}",
                headers=self.headers,
                name="GET /api/v1/agents/{id}"
            )

    @task(2)
    def update_agent(self):
        """Update an agent."""
        if self.created_agents:
            agent_id = random.choice(self.created_agents)
            payload = {
                "status": random.choice(["active", "idle", "busy", "suspended"]),
                "configuration": {
                    "max_tokens": random.randint(100, 2000),
                }
            }
            self.client.patch(
                f"/api/v1/agents/{agent_id}",
                headers=self.headers,
                json=payload,
                name="PATCH /api/v1/agents/{id}"
            )

    @task(1)
    def delete_agent(self):
        """Delete an agent."""
        if self.created_agents:
            agent_id = self.created_agents.pop()
            self.client.delete(
                f"/api/v1/agents/{agent_id}",
                headers=self.headers,
                name="DELETE /api/v1/agents/{id}"
            )


class GoalOperations(TaskSet):
    """Test goal CRUD operations."""

    def on_start(self):
        """Initialize with auth headers and storage for created goals."""
        self.created_goals = []
        self.created_agents = []
        self.headers = {
            "X-API-Key": TEST_API_KEY,
            "Content-Type": "application/json"
        }

        # Create a test agent for goal association
        payload = {
            "name": "test_agent_for_goals",
            "agent_type": "simple",
            "configuration": {},
            "metadata": {}
        }
        response = self.client.post(
            "/api/v1/agents/",
            headers=self.headers,
            json=payload
        )
        if response.status_code == 201:
            try:
                agent = response.json()
                self.created_agents.append(agent["id"])
            except (ValueError, KeyError):
                pass

    @task(5)
    def create_goal(self):
        """Create a new goal."""
        if not self.created_agents:
            return

        payload = {
            "agent_id": random.choice(self.created_agents),
            "description": fake.sentence(nb_words=10),
            "success_criteria": [
                fake.sentence(nb_words=6) for _ in range(random.randint(1, 3))
            ],
            "priority": random.randint(1, 10)
        }

        response = self.client.post(
            "/api/v1/goals/",
            headers=self.headers,
            json=payload,
            name="POST /api/v1/goals/"
        )

        if response.status_code == 201:
            try:
                goal = response.json()
                # Use goal_id, not id
                self.created_goals.append(goal["goal_id"])
            except (ValueError, KeyError):
                pass

    @task(10)
    def list_goals(self):
        """List goals."""
        self.client.get(
            "/api/v1/goals/",
            headers=self.headers,
            name="GET /api/v1/goals/"
        )

    @task(3)
    def get_goal(self):
        """Get goal by ID."""
        if self.created_goals:
            goal_id = random.choice(self.created_goals)
            self.client.get(
                f"/api/v1/goals/{goal_id}",
                headers=self.headers,
                name="GET /api/v1/goals/{id}"
            )

    @task(2)
    def update_goal(self):
        """Update a goal."""
        if self.created_goals:
            goal_id = random.choice(self.created_goals)
            payload = {
                "status": random.choice(["pending", "in_progress", "completed", "failed"]),
                "priority": random.randint(1, 10)
            }
            self.client.patch(
                f"/api/v1/goals/{goal_id}",
                headers=self.headers,
                json=payload,
                name="PATCH /api/v1/goals/{id}"
            )


class TaskOperations(TaskSet):
    """Test task CRUD operations."""

    def on_start(self):
        """Initialize with auth headers and storage for created tasks."""
        self.created_tasks = []
        self.created_agents = []
        self.created_plans = []
        self.headers = {
            "X-API-Key": TEST_API_KEY,
            "Content-Type": "application/json"
        }

        # Create test agent
        payload = {
            "name": "test_agent_for_tasks",
            "agent_type": "simple",
            "configuration": {},
            "metadata": {}
        }
        response = self.client.post(
            "/api/v1/agents/",
            headers=self.headers,
            json=payload
        )
        if response.status_code == 201:
            try:
                agent = response.json()
                self.created_agents.append(agent["id"])
            except (ValueError, KeyError):
                pass

    @task(5)
    def create_task(self):
        """Create a new task."""
        if not self.created_agents:
            return

        payload = {
            "plan_id": fake.uuid4(),  # Using fake plan ID for now
            "agent_id": random.choice(self.created_agents),
            "description": fake.sentence(nb_words=10),
            "task_type": random.choice(["analysis", "generation", "execution"]),
            "input_data": {
                "content": fake.text(max_nb_chars=200),
                "parameters": {
                    "priority": random.choice(["low", "medium", "high"])
                }
            }
        }

        response = self.client.post(
            "/api/v1/tasks/",
            headers=self.headers,
            json=payload,
            name="POST /api/v1/tasks/"
        )

        if response.status_code == 201:
            try:
                task = response.json()
                # Use task_id, not id
                self.created_tasks.append(task["task_id"])
            except (ValueError, KeyError):
                pass

    @task(10)
    def get_task(self):
        """Get task by ID (placeholder implementation)."""
        if self.created_tasks:
            task_id = random.choice(self.created_tasks)
            self.client.get(
                f"/api/v1/tasks/{task_id}",
                headers=self.headers,
                name="GET /api/v1/tasks/{id}"
            )

    @task(2)
    def update_task(self):
        """Update a task."""
        if self.created_tasks:
            task_id = random.choice(self.created_tasks)
            payload = {
                "status": random.choice(["pending", "running", "completed", "failed"]),
                "output_data": {
                    "result": "task updated via load test",
                    "timestamp": int(time.time())
                }
            }
            self.client.patch(
                f"/api/v1/tasks/{task_id}",
                headers=self.headers,
                json=payload,
                name="PATCH /api/v1/tasks/{id}"
            )


class MixedAPIOperations(TaskSet):
    """Mix of all API operations for realistic load."""

    tasks = {
        AgentOperations: 5,
        GoalOperations: 3,
        TaskOperations: 2,
    }


# ============================================================================
# User Classes
# ============================================================================

class APIUser(HttpUser):
    """Simulated API user performing mixed operations."""

    tasks = [MixedAPIOperations]
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def on_start(self):
        """Set up authentication for all requests."""
        self.client.headers.update({
            "X-API-Key": TEST_API_KEY,
            "Content-Type": "application/json"
        })


class AgentFocusedUser(HttpUser):
    """User focused on agent operations."""

    tasks = [AgentOperations]
    wait_time = between(0.5, 2)

    def on_start(self):
        self.client.headers.update({
            "X-API-Key": TEST_API_KEY,
            "Content-Type": "application/json"
        })


class GoalFocusedUser(HttpUser):
    """User focused on goal operations."""

    tasks = [GoalOperations]
    wait_time = between(0.5, 2)

    def on_start(self):
        self.client.headers.update({
            "X-API-Key": TEST_API_KEY,
            "Content-Type": "application/json"
        })


class TaskFocusedUser(HttpUser):
    """User focused on task operations."""

    tasks = [TaskOperations]
    wait_time = between(0.5, 2)

    def on_start(self):
        self.client.headers.update({
            "X-API-Key": TEST_API_KEY,
            "Content-Type": "application/json"
        })

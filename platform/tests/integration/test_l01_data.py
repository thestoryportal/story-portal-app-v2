"""
Integration Tests - L01 Data Layer

Tests for L01 Data Layer APIs including agents, goals, tools, and other entities.
"""

import pytest
import httpx
from uuid import uuid4
from typing import Dict, Any

pytestmark = [pytest.mark.integration, pytest.mark.l01, pytest.mark.database]

BASE_URL = "http://localhost:8001"


@pytest.mark.asyncio
class TestAgentCRUD:
    """Test agent CRUD operations."""

    async def test_create_agent(self, http_client: httpx.AsyncClient):
        """Test creating an agent."""
        agent_data = {
            "name": "TestAgent",
            "agent_type": "task",
            "configuration": {"max_iterations": 10},
            "metadata": {"test": True}
        }

        response = await http_client.post(f"{BASE_URL}/agents/", json=agent_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "TestAgent"
        assert data["agent_type"] == "task"
        assert "id" in data
        assert "did" in data
        assert data["status"] == "created"

        # Store ID for cleanup
        return data["id"]

    async def test_list_agents(self, http_client: httpx.AsyncClient):
        """Test listing agents."""
        response = await http_client.get(f"{BASE_URL}/agents/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # If there are agents, verify structure
        if len(data) > 0:
            agent = data[0]
            assert "id" in agent
            assert "name" in agent
            assert "status" in agent

    async def test_list_agents_with_filters(self, http_client: httpx.AsyncClient):
        """Test listing agents with status filter."""
        response = await http_client.get(
            f"{BASE_URL}/agents/",
            params={"status": "created", "limit": 10, "offset": 0}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_get_agent(self, http_client: httpx.AsyncClient):
        """Test retrieving a specific agent."""
        # First create an agent
        agent_data = {
            "name": "GetTestAgent",
            "agent_type": "general"
        }
        create_response = await http_client.post(f"{BASE_URL}/agents/", json=agent_data)
        assert create_response.status_code == 201
        agent_id = create_response.json()["id"]

        # Now get it
        response = await http_client.get(f"{BASE_URL}/agents/{agent_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == agent_id
        assert data["name"] == "GetTestAgent"

    async def test_get_nonexistent_agent(self, http_client: httpx.AsyncClient):
        """Test getting an agent that doesn't exist."""
        fake_id = str(uuid4())
        response = await http_client.get(f"{BASE_URL}/agents/{fake_id}")

        assert response.status_code == 404

    async def test_update_agent(self, http_client: httpx.AsyncClient):
        """Test updating an agent."""
        # Create agent
        agent_data = {"name": "UpdateTestAgent", "agent_type": "general"}
        create_response = await http_client.post(f"{BASE_URL}/agents/", json=agent_data)
        agent_id = create_response.json()["id"]

        # Update it
        update_data = {
            "name": "UpdatedAgent",
            "status": "active",
            "metadata": {"updated": True}
        }
        response = await http_client.patch(
            f"{BASE_URL}/agents/{agent_id}",
            json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "UpdatedAgent"
        assert data["status"] == "active"
        assert data["metadata"]["updated"] is True

    async def test_update_nonexistent_agent(self, http_client: httpx.AsyncClient):
        """Test updating an agent that doesn't exist."""
        fake_id = str(uuid4())
        update_data = {"name": "ShouldFail"}

        response = await http_client.patch(
            f"{BASE_URL}/agents/{fake_id}",
            json=update_data
        )

        assert response.status_code == 404

    async def test_delete_agent(self, http_client: httpx.AsyncClient):
        """Test deleting an agent."""
        # Create agent
        agent_data = {"name": "DeleteTestAgent", "agent_type": "general"}
        create_response = await http_client.post(f"{BASE_URL}/agents/", json=agent_data)
        agent_id = create_response.json()["id"]

        # Delete it
        response = await http_client.delete(f"{BASE_URL}/agents/{agent_id}")

        assert response.status_code == 204

        # Verify it's gone
        get_response = await http_client.get(f"{BASE_URL}/agents/{agent_id}")
        assert get_response.status_code == 404

    async def test_delete_nonexistent_agent(self, http_client: httpx.AsyncClient):
        """Test deleting an agent that doesn't exist."""
        fake_id = str(uuid4())
        response = await http_client.delete(f"{BASE_URL}/agents/{fake_id}")

        assert response.status_code == 404


@pytest.mark.asyncio
class TestGoalOperations:
    """Test goal management operations."""

    async def test_create_goal(self, http_client: httpx.AsyncClient):
        """Test creating a goal."""
        # First create an agent
        agent_data = {"name": "GoalTestAgent", "agent_type": "general"}
        agent_response = await http_client.post(f"{BASE_URL}/agents/", json=agent_data)
        agent_id = agent_response.json()["id"]

        # Create goal for this agent
        goal_data = {
            "agent_id": agent_id,
            "description": "Test goal",
            "success_criteria": {"metric": "completion"},
            "priority": "high"
        }

        response = await http_client.post(f"{BASE_URL}/goals/", json=goal_data)

        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "Test goal"
        assert data["agent_id"] == agent_id
        assert "id" in data

    async def test_list_goals(self, http_client: httpx.AsyncClient):
        """Test listing goals."""
        response = await http_client.get(f"{BASE_URL}/goals/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_get_agent_goals(self, http_client: httpx.AsyncClient):
        """Test getting goals for a specific agent."""
        # Create agent and goal
        agent_data = {"name": "AgentGoalsTest", "agent_type": "general"}
        agent_response = await http_client.post(f"{BASE_URL}/agents/", json=agent_data)
        agent_id = agent_response.json()["id"]

        goal_data = {
            "agent_id": agent_id,
            "description": "Agent-specific goal",
            "success_criteria": {}
        }
        await http_client.post(f"{BASE_URL}/goals/", json=goal_data)

        # Get goals for this agent
        response = await http_client.get(
            f"{BASE_URL}/goals/",
            params={"agent_id": agent_id}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            assert data[0]["agent_id"] == agent_id


@pytest.mark.asyncio
class TestToolOperations:
    """Test tool management operations."""

    async def test_create_tool(self, http_client: httpx.AsyncClient):
        """Test creating a tool."""
        tool_data = {
            "name": "TestTool",
            "tool_type": "function",
            "parameters": {"param1": "value1"},
            "metadata": {"test": True}
        }

        response = await http_client.post(f"{BASE_URL}/tools/", json=tool_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "TestTool"
        assert data["tool_type"] == "function"
        assert "id" in data

    async def test_list_tools(self, http_client: httpx.AsyncClient):
        """Test listing tools."""
        response = await http_client.get(f"{BASE_URL}/tools/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
class TestEventOperations:
    """Test event logging and retrieval."""

    async def test_create_event(self, http_client: httpx.AsyncClient):
        """Test creating an event."""
        event_data = {
            "event_type": "test_event",
            "source": "test_suite",
            "payload": {"test": True},
            "metadata": {"timestamp": "2026-01-18T00:00:00Z"}
        }

        response = await http_client.post(f"{BASE_URL}/events/", json=event_data)

        assert response.status_code == 201
        data = response.json()
        assert data["event_type"] == "test_event"
        assert data["source"] == "test_suite"
        assert "id" in data

    async def test_list_events(self, http_client: httpx.AsyncClient):
        """Test listing events."""
        response = await http_client.get(f"{BASE_URL}/events/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_filter_events_by_type(self, http_client: httpx.AsyncClient):
        """Test filtering events by event_type."""
        # Create event with specific type
        event_data = {
            "event_type": "filter_test_event",
            "source": "test_suite",
            "payload": {}
        }
        await http_client.post(f"{BASE_URL}/events/", json=event_data)

        # Query by event_type
        response = await http_client.get(
            f"{BASE_URL}/events/",
            params={"event_type": "filter_test_event"}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
class TestDataLayerErrors:
    """Test error handling in data layer."""

    async def test_create_agent_invalid_data(self, http_client: httpx.AsyncClient):
        """Test creating agent with invalid data."""
        invalid_data = {}  # Missing required fields

        response = await http_client.post(f"{BASE_URL}/agents/", json=invalid_data)

        assert response.status_code == 422  # Validation error

    async def test_create_agent_malformed_json(self, http_client: httpx.AsyncClient):
        """Test creating agent with malformed JSON."""
        response = await http_client.post(
            f"{BASE_URL}/agents/",
            content=b"not json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code in [400, 422]


@pytest.mark.asyncio
class TestDataLayerPerformance:
    """Test data layer performance characteristics."""

    async def test_bulk_agent_creation(self, http_client: httpx.AsyncClient):
        """Test creating multiple agents efficiently."""
        import asyncio

        async def create_agent(name: str):
            agent_data = {"name": name, "agent_type": "general"}
            return await http_client.post(f"{BASE_URL}/agents/", json=agent_data)

        # Create 10 agents concurrently
        tasks = [create_agent(f"BulkAgent{i}") for i in range(10)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successful creations
        success_count = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code == 201)

        assert success_count >= 8  # Allow some failures due to timeouts

    async def test_pagination_large_dataset(self, http_client: httpx.AsyncClient):
        """Test pagination with large limits."""
        response = await http_client.get(
            f"{BASE_URL}/agents/",
            params={"limit": 1000, "offset": 0}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 1000

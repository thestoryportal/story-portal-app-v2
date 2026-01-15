"""End-to-end workflow test for Agentic AI Workforce platform."""
import pytest
import httpx
import asyncio


@pytest.mark.asyncio
async def test_complete_agent_workflow(api_base_url, api_headers):
    """Test complete agent lifecycle via API Gateway.

    Tests:
    1. Create agent
    2. Verify agent exists
    3. Invoke agent
    4. Poll operation status
    5. Cleanup - terminate agent
    """
    async with httpx.AsyncClient(base_url=api_base_url, timeout=30.0) as client:
        # 1. Create agent
        response = await client.post(
            "/api/v1/agents",
            json={"name": "test-e2e-agent", "agent_type": "general"},
            headers=api_headers
        )
        assert response.status_code == 201, f"Create agent failed: {response.text}"
        agent_data = response.json()
        agent_id = agent_data["agent_id"]
        print(f"Created agent: {agent_id}")

        # 2. Verify agent exists
        response = await client.get(
            f"/api/v1/agents/{agent_id}",
            headers=api_headers
        )
        assert response.status_code == 200, f"Get agent failed: {response.text}"
        agent_info = response.json()
        assert agent_info["agent_id"] == agent_id
        print(f"Verified agent exists: {agent_info}")

        # 3. Invoke agent
        response = await client.post(
            f"/api/v1/agents/{agent_id}/invoke",
            json={"task": "test task", "parameters": {}},
            headers=api_headers
        )
        assert response.status_code == 202, f"Invoke agent failed: {response.text}"
        invocation_data = response.json()
        operation_id = invocation_data["operation_id"]
        print(f"Invoked agent, operation: {operation_id}")

        # 4. Poll operation status
        for attempt in range(10):
            response = await client.get(
                f"/api/v1/operations/{operation_id}",
                headers=api_headers
            )
            if response.status_code == 200:
                operation_status = response.json()
                print(f"Operation status (attempt {attempt + 1}): {operation_status.get('status')}")
                if operation_status["status"] in ("COMPLETED", "FAILED"):
                    break
            await asyncio.sleep(1)

        # 5. Cleanup - terminate agent
        response = await client.delete(
            f"/api/v1/agents/{agent_id}",
            headers=api_headers
        )
        assert response.status_code == 204, f"Delete agent failed: {response.text}"
        print(f"Terminated agent: {agent_id}")


@pytest.mark.asyncio
async def test_agent_not_found(api_base_url, api_headers):
    """Test that non-existent agent returns 404."""
    async with httpx.AsyncClient(base_url=api_base_url, timeout=10.0) as client:
        response = await client.get(
            "/api/v1/agents/non-existent-agent-id",
            headers=api_headers
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_agents(api_base_url, api_headers):
    """Test listing all agents."""
    async with httpx.AsyncClient(base_url=api_base_url, timeout=10.0) as client:
        response = await client.get(
            "/api/v1/agents",
            headers=api_headers
        )
        assert response.status_code == 200
        agents = response.json()
        assert isinstance(agents, (list, dict))


@pytest.mark.asyncio
async def test_health_check(api_base_url):
    """Test API Gateway health endpoint."""
    async with httpx.AsyncClient(base_url=api_base_url, timeout=10.0) as client:
        response = await client.get("/health")
        assert response.status_code == 200
        health = response.json()
        assert "status" in health


@pytest.mark.asyncio
async def test_api_key_validation(api_base_url):
    """Test that requests without API key are rejected."""
    async with httpx.AsyncClient(base_url=api_base_url, timeout=10.0) as client:
        response = await client.get(
            "/api/v1/agents",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in (401, 403)

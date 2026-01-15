"""Lightweight load test for API Gateway."""
import pytest
import httpx
import asyncio


@pytest.mark.asyncio
async def test_concurrent_requests():
    """Test 20 concurrent agent creations.

    Verifies the system can handle concurrent load.
    """
    BASE_URL = "http://localhost:8000"
    API_KEY = "test-key-12345678901234567890123456789012"

    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=30.0
    ) as client:

        async def create_agent(i):
            """Create a single agent."""
            try:
                response = await client.post(
                    "/api/v1/agents",
                    json={
                        "name": f"load-test-agent-{i}",
                        "agent_type": "general"
                    },
                    headers={
                        "X-API-Key": API_KEY,
                        "Content-Type": "application/json"
                    }
                )
                return response.status_code
            except httpx.TimeoutException:
                return "timeout"
            except httpx.ConnectError:
                return "connection_error"
            except Exception as e:
                return f"error: {str(e)[:50]}"

        # Create 20 concurrent requests
        results = await asyncio.gather(*[create_agent(i) for i in range(20)])

        # Count successes
        success_count = sum(1 for r in results if r == 201)
        error_count = sum(1 for r in results if isinstance(r, str))

        print(f"\nLoad Test Results:")
        print(f"  Total requests: 20")
        print(f"  Successful (201): {success_count}")
        print(f"  Errors: {error_count}")
        print(f"  Results: {results}")

        # Accept if at least 90% succeeded (18/20)
        assert success_count >= 18, (
            f"Only {success_count}/20 requests succeeded. "
            f"Results: {results}"
        )


@pytest.mark.asyncio
async def test_sequential_load():
    """Test sequential request handling.

    Verifies the system can handle sequential requests reliably.
    """
    BASE_URL = "http://localhost:8000"
    API_KEY = "test-key-12345678901234567890123456789012"

    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=10.0
    ) as client:
        success_count = 0

        for i in range(10):
            try:
                response = await client.post(
                    "/api/v1/agents",
                    json={
                        "name": f"sequential-test-agent-{i}",
                        "agent_type": "general"
                    },
                    headers={
                        "X-API-Key": API_KEY,
                        "Content-Type": "application/json"
                    }
                )
                if response.status_code == 201:
                    success_count += 1
            except Exception as e:
                print(f"Request {i} failed: {e}")

        print(f"\nSequential Load Test: {success_count}/10 succeeded")
        assert success_count >= 9, f"Only {success_count}/10 sequential requests succeeded"

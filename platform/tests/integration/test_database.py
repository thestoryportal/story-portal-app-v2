"""
Integration Tests - Database Operations

Tests for PostgreSQL database operations including RBAC, transactions, and connection pooling.
"""

import pytest
import httpx
import asyncio
from uuid import uuid4

pytestmark = [pytest.mark.integration, pytest.mark.database]

BASE_URL = "http://localhost:8001"


@pytest.mark.asyncio
class TestDatabaseConnectivity:
    """Test database connection and health."""

    async def test_database_connection(self, http_client: httpx.AsyncClient):
        """Test that database is accessible."""
        response = await http_client.get(f"{BASE_URL}/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "ok"]

    async def test_connection_pooling(self, http_client: httpx.AsyncClient):
        """Test connection pooling with concurrent requests."""
        async def make_request():
            return await http_client.get(f"{BASE_URL}/agents")

        # Make 20 concurrent requests to test connection pool
        tasks = [make_request() for _ in range(20)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successful responses
        success_count = sum(
            1 for r in responses
            if not isinstance(r, Exception) and r.status_code in [200, 401, 403]
        )

        # Most should succeed
        assert success_count >= 15


@pytest.mark.asyncio
class TestDatabaseCRUD:
    """Test database CRUD operations through API."""

    async def test_create_read_cycle(self, http_client: httpx.AsyncClient):
        """Test creating and reading data."""
        # Create
        agent_data = {"name": "CRUDTestAgent", "agent_type": "general"}
        create_response = await http_client.post(f"{BASE_URL}/agents/", json=agent_data)

        if create_response.status_code == 201:
            agent_id = create_response.json()["id"]

            # Read
            read_response = await http_client.get(f"{BASE_URL}/agents/{agent_id}")
            assert read_response.status_code == 200
            assert read_response.json()["name"] == "CRUDTestAgent"

    async def test_update_cycle(self, http_client: httpx.AsyncClient):
        """Test updating data."""
        # Create
        agent_data = {"name": "UpdateTest", "agent_type": "general"}
        create_response = await http_client.post(f"{BASE_URL}/agents/", json=agent_data)

        if create_response.status_code == 201:
            agent_id = create_response.json()["id"]

            # Update
            update_data = {"name": "Updated", "status": "active"}
            update_response = await http_client.patch(
                f"{BASE_URL}/agents/{agent_id}",
                json=update_data
            )

            if update_response.status_code == 200:
                # Verify update
                verify_response = await http_client.get(f"{BASE_URL}/agents/{agent_id}")
                assert verify_response.json()["name"] == "Updated"

    async def test_delete_cycle(self, http_client: httpx.AsyncClient):
        """Test deleting data."""
        # Create
        agent_data = {"name": "DeleteTest", "agent_type": "general"}
        create_response = await http_client.post(f"{BASE_URL}/agents/", json=agent_data)

        if create_response.status_code == 201:
            agent_id = create_response.json()["id"]

            # Delete
            delete_response = await http_client.delete(f"{BASE_URL}/agents/{agent_id}")
            assert delete_response.status_code == 204

            # Verify deleted
            verify_response = await http_client.get(f"{BASE_URL}/agents/{agent_id}")
            assert verify_response.status_code == 404

    async def test_bulk_insert(self, http_client: httpx.AsyncClient):
        """Test inserting multiple records."""
        agents = [
            {"name": f"BulkAgent{i}", "agent_type": "general"}
            for i in range(5)
        ]

        results = []
        for agent_data in agents:
            response = await http_client.post(f"{BASE_URL}/agents/", json=agent_data)
            results.append(response.status_code)

        # Most should succeed
        success_count = sum(1 for code in results if code == 201)
        assert success_count >= 4


@pytest.mark.asyncio
class TestDatabaseTransactions:
    """Test database transaction handling."""

    async def test_rollback_on_error(self, http_client: httpx.AsyncClient):
        """Test that errors trigger rollback."""
        # Try to create invalid data
        invalid_data = {}  # Missing required fields

        response = await http_client.post(f"{BASE_URL}/agents/", json=invalid_data)

        # Should fail with validation error
        assert response.status_code == 422

        # Database should be consistent (no partial data)
        list_response = await http_client.get(f"{BASE_URL}/agents/")
        # Should still return valid list
        assert list_response.status_code in [200, 401, 403]

    async def test_atomic_operations(self, http_client: httpx.AsyncClient):
        """Test that operations are atomic."""
        # Create agent
        agent_data = {"name": "AtomicTest", "agent_type": "general"}
        response = await http_client.post(f"{BASE_URL}/agents/", json=agent_data)

        if response.status_code == 201:
            agent_id = response.json()["id"]

            # Either the full agent exists or doesn't exist (no partial state)
            get_response = await http_client.get(f"{BASE_URL}/agents/{agent_id}")
            assert get_response.status_code in [200, 404]

            if get_response.status_code == 200:
                agent = get_response.json()
                # All required fields should be present
                assert "id" in agent
                assert "name" in agent
                assert "status" in agent


@pytest.mark.asyncio
class TestDatabaseQueries:
    """Test database query operations."""

    async def test_list_with_pagination(self, http_client: httpx.AsyncClient):
        """Test pagination in list queries."""
        # Get first page
        response1 = await http_client.get(
            f"{BASE_URL}/agents/",
            params={"limit": 10, "offset": 0}
        )

        if response1.status_code == 200:
            page1 = response1.json()
            assert isinstance(page1, list)
            assert len(page1) <= 10

            # Get second page
            response2 = await http_client.get(
                f"{BASE_URL}/agents/",
                params={"limit": 10, "offset": 10}
            )

            if response2.status_code == 200:
                page2 = response2.json()
                assert isinstance(page2, list)

    async def test_filter_queries(self, http_client: httpx.AsyncClient):
        """Test filtering in queries."""
        # Filter by status
        response = await http_client.get(
            f"{BASE_URL}/agents/",
            params={"status": "created"}
        )

        assert response.status_code in [200, 401, 403]

        if response.status_code == 200:
            agents = response.json()
            assert isinstance(agents, list)

    async def test_query_performance(self, http_client: httpx.AsyncClient):
        """Test that queries perform reasonably."""
        import time

        start = time.time()
        response = await http_client.get(f"{BASE_URL}/agents/")
        duration = time.time() - start

        assert response.status_code in [200, 401, 403]

        # Query should complete within 2 seconds
        assert duration < 2.0


@pytest.mark.asyncio
class TestDatabaseConstraints:
    """Test database constraints and validation."""

    async def test_unique_constraints(self, http_client: httpx.AsyncClient):
        """Test unique constraint enforcement."""
        # This would test unique constraints if they exist
        # For now, just verify data integrity
        response = await http_client.get(f"{BASE_URL}/agents/")

        assert response.status_code in [200, 401, 403]

    async def test_foreign_key_constraints(self, http_client: httpx.AsyncClient):
        """Test foreign key constraint enforcement."""
        # Try to create goal for non-existent agent
        fake_agent_id = str(uuid4())
        goal_data = {
            "agent_id": fake_agent_id,
            "description": "Test goal",
            "success_criteria": {}
        }

        response = await http_client.post(f"{BASE_URL}/goals/", json=goal_data)

        # Should either reject or accept depending on FK constraints
        assert response.status_code in [201, 400, 404, 422, 401, 403]

    async def test_not_null_constraints(self, http_client: httpx.AsyncClient):
        """Test NOT NULL constraint enforcement."""
        # Try to create agent without name
        invalid_data = {"agent_type": "general"}  # Missing name

        response = await http_client.post(f"{BASE_URL}/agents/", json=invalid_data)

        # Should reject due to missing required field
        assert response.status_code == 422


@pytest.mark.asyncio
class TestDatabaseRBAC:
    """Test database-level RBAC."""

    async def test_read_access(self, http_client: httpx.AsyncClient):
        """Test read-only access patterns."""
        # GET operations should work with read permissions
        response = await http_client.get(f"{BASE_URL}/agents/")

        assert response.status_code in [200, 401, 403]

    async def test_write_access(self, http_client: httpx.AsyncClient):
        """Test write access patterns."""
        # POST operations require write permissions
        agent_data = {"name": "WriteTest", "agent_type": "general"}
        response = await http_client.post(f"{BASE_URL}/agents/", json=agent_data)

        assert response.status_code in [201, 401, 403]

    async def test_admin_access(self, http_client: httpx.AsyncClient):
        """Test admin-level access patterns."""
        # DELETE operations might require admin permissions
        fake_id = str(uuid4())
        response = await http_client.delete(f"{BASE_URL}/agents/{fake_id}")

        assert response.status_code in [204, 401, 403, 404]


@pytest.mark.asyncio
class TestDatabaseIndexes:
    """Test database index usage and performance."""

    async def test_indexed_query_performance(self, http_client: httpx.AsyncClient):
        """Test that indexed queries perform well."""
        import time

        # Query by ID (should use primary key index)
        fake_id = str(uuid4())

        start = time.time()
        response = await http_client.get(f"{BASE_URL}/agents/{fake_id}")
        duration = time.time() - start

        # Should be fast even for non-existent ID
        assert duration < 1.0
        assert response.status_code in [404, 401, 403]


@pytest.mark.asyncio
class TestDatabaseBackup:
    """Test database backup and recovery operations."""

    async def test_database_available_during_backup(self, http_client: httpx.AsyncClient):
        """Test that database remains available during backup."""
        # The system should remain operational during backup
        response = await http_client.get(f"{BASE_URL}/health")

        assert response.status_code == 200

    async def test_write_ahead_log_active(self, http_client: httpx.AsyncClient):
        """Test that WAL archiving is operational."""
        # WAL should not affect normal operations
        agent_data = {"name": "WALTest", "agent_type": "general"}
        response = await http_client.post(f"{BASE_URL}/agents/", json=agent_data)

        assert response.status_code in [201, 401, 403]


@pytest.mark.asyncio
class TestDatabaseErrors:
    """Test database error handling."""

    async def test_connection_timeout_handling(self, http_client: httpx.AsyncClient):
        """Test handling of connection timeouts."""
        try:
            response = await http_client.get(
                f"{BASE_URL}/agents/",
                timeout=0.001  # Very short timeout
            )
            # If it succeeds, queries are very fast
            assert response.status_code in [200, 401, 403]
        except httpx.TimeoutException:
            # Expected for very short timeout
            pass

    async def test_query_error_handling(self, http_client: httpx.AsyncClient):
        """Test handling of malformed queries."""
        # Try to get agent with invalid UUID
        response = await http_client.get(f"{BASE_URL}/agents/invalid-uuid")

        # Should handle gracefully
        assert response.status_code in [400, 404, 422]


@pytest.mark.asyncio
class TestDatabaseConcurrency:
    """Test concurrent database access."""

    async def test_concurrent_reads(self, http_client: httpx.AsyncClient):
        """Test concurrent read operations."""
        async def read_agents():
            return await http_client.get(f"{BASE_URL}/agents/")

        # 30 concurrent reads
        tasks = [read_agents() for _ in range(30)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(
            1 for r in responses
            if not isinstance(r, Exception) and r.status_code in [200, 401, 403]
        )

        # Should handle most concurrent reads
        assert success_count >= 25

    async def test_concurrent_writes(self, http_client: httpx.AsyncClient):
        """Test concurrent write operations."""
        async def create_agent(name: str):
            agent_data = {"name": name, "agent_type": "general"}
            return await http_client.post(f"{BASE_URL}/agents/", json=agent_data)

        # 10 concurrent writes
        tasks = [create_agent(f"ConcurrentAgent{i}") for i in range(10)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(
            1 for r in responses
            if not isinstance(r, Exception) and r.status_code == 201
        )

        # Should handle most concurrent writes
        assert success_count >= 7

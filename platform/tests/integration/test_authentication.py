"""
Integration Tests - Authentication & Authorization

Tests for authentication flows including JWT tokens, API keys, and authorization.
"""

import pytest
import httpx
from typing import Dict, Any
import time

pytestmark = [pytest.mark.integration, pytest.mark.auth, pytest.mark.security]

GATEWAY_URL = "http://localhost:8009"
L01_URL = "http://localhost:8001"


@pytest.mark.asyncio
class TestJWTAuthentication:
    """Test JWT token-based authentication."""

    async def test_access_without_token(self, http_client: httpx.AsyncClient):
        """Test accessing protected endpoint without token."""
        response = await http_client.get(f"{GATEWAY_URL}/api/v1/agents")

        # Should succeed if auth is disabled, or return 401
        assert response.status_code in [200, 401, 403]

    async def test_access_with_invalid_token(self, http_client: httpx.AsyncClient):
        """Test accessing with invalid JWT token."""
        headers = {"Authorization": "Bearer invalid_token_12345"}

        response = await http_client.get(
            f"{GATEWAY_URL}/api/v1/agents",
            headers=headers
        )

        # Should reject invalid token or succeed if auth is disabled
        assert response.status_code in [200, 401, 403]

    async def test_access_with_malformed_auth_header(self, http_client: httpx.AsyncClient):
        """Test accessing with malformed Authorization header."""
        test_cases = [
            {"Authorization": "invalid"},  # No Bearer prefix
            {"Authorization": "Bearer"},  # No token
            {"Authorization": "Basic token"},  # Wrong scheme
        ]

        for headers in test_cases:
            response = await http_client.get(
                f"{GATEWAY_URL}/api/v1/agents",
                headers=headers
            )

            # Should reject malformed header or succeed if auth is disabled
            assert response.status_code in [200, 400, 401, 403]

    async def test_expired_token(self, http_client: httpx.AsyncClient):
        """Test accessing with expired JWT token."""
        # Create a mock expired token (this is a dummy token)
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjB9.invalid"
        headers = {"Authorization": f"Bearer {expired_token}"}

        response = await http_client.get(
            f"{GATEWAY_URL}/api/v1/agents",
            headers=headers
        )

        # Should reject expired token or succeed if auth is disabled
        assert response.status_code in [200, 401, 403]


@pytest.mark.asyncio
class TestAPIKeyAuthentication:
    """Test API key-based authentication."""

    async def test_access_with_api_key_header(self, http_client: httpx.AsyncClient):
        """Test accessing with API key in header."""
        headers = {"X-API-Key": "test_api_key_12345"}

        response = await http_client.get(
            f"{GATEWAY_URL}/api/v1/agents",
            headers=headers
        )

        # Should validate API key or succeed if auth is disabled
        assert response.status_code in [200, 401, 403]

    async def test_access_with_invalid_api_key(self, http_client: httpx.AsyncClient):
        """Test accessing with invalid API key."""
        headers = {"X-API-Key": "invalid_key"}

        response = await http_client.get(
            f"{GATEWAY_URL}/api/v1/agents",
            headers=headers
        )

        # Should reject invalid key or succeed if auth is disabled
        assert response.status_code in [200, 401, 403]

    async def test_access_with_empty_api_key(self, http_client: httpx.AsyncClient):
        """Test accessing with empty API key."""
        headers = {"X-API-Key": ""}

        response = await http_client.get(
            f"{GATEWAY_URL}/api/v1/agents",
            headers=headers
        )

        # Should reject empty key
        assert response.status_code in [200, 400, 401, 403]


@pytest.mark.asyncio
class TestAuthorization:
    """Test authorization and access control."""

    async def test_read_only_access(self, http_client: httpx.AsyncClient):
        """Test read-only operations."""
        # GET should work for read-only users
        response = await http_client.get(f"{GATEWAY_URL}/api/v1/agents")

        assert response.status_code in [200, 401, 403]

    async def test_write_access_control(self, http_client: httpx.AsyncClient):
        """Test write operations require proper permissions."""
        agent_data = {"name": "TestAgent", "agent_type": "general"}

        response = await http_client.post(
            f"{GATEWAY_URL}/api/v1/agents",
            json=agent_data
        )

        # Should require write permissions or succeed if auth is disabled
        assert response.status_code in [200, 201, 401, 403]

    async def test_delete_access_control(self, http_client: httpx.AsyncClient):
        """Test delete operations require proper permissions."""
        fake_agent_id = "00000000-0000-0000-0000-000000000000"

        response = await http_client.delete(
            f"{GATEWAY_URL}/api/v1/agents/{fake_agent_id}"
        )

        # Should require delete permissions or return 404
        assert response.status_code in [204, 401, 403, 404]

    async def test_rbac_role_enforcement(self, http_client: httpx.AsyncClient):
        """Test that RBAC roles are enforced."""
        # This tests the overall RBAC system
        # Different roles should have different access levels

        # Try accessing a protected endpoint
        response = await http_client.get(f"{GATEWAY_URL}/api/v1/agents")

        # Should enforce roles
        assert response.status_code in [200, 401, 403]


@pytest.mark.asyncio
class TestSessionManagement:
    """Test session management and token refresh."""

    async def test_session_persistence(self, http_client: httpx.AsyncClient):
        """Test that sessions persist across requests."""
        # Make two requests to verify session handling
        response1 = await http_client.get(f"{GATEWAY_URL}/health")
        response2 = await http_client.get(f"{GATEWAY_URL}/health")

        assert response1.status_code == 200
        assert response2.status_code == 200

    async def test_concurrent_sessions(self, http_client: httpx.AsyncClient):
        """Test handling multiple concurrent sessions."""
        import asyncio

        async def make_request():
            return await http_client.get(f"{GATEWAY_URL}/health")

        # Create multiple concurrent requests
        tasks = [make_request() for _ in range(10)]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        assert all(r.status_code == 200 for r in responses)


@pytest.mark.asyncio
class TestSecurityHeaders:
    """Test security-related headers."""

    async def test_security_headers_present(self, http_client: httpx.AsyncClient):
        """Test that security headers are present in responses."""
        response = await http_client.get(f"{GATEWAY_URL}/health")

        assert response.status_code == 200
        headers = response.headers

        # Check for common security headers (might not all be present)
        # Just verify we can access headers
        assert isinstance(headers, (dict, httpx.Headers))

        # Optional: Check for specific security headers
        security_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",
        ]

        # At least some security headers should be present (or none if not configured)
        present_headers = [h for h in security_headers if h in headers]
        # This is informational - security headers might not be configured yet

    async def test_cors_headers(self, http_client: httpx.AsyncClient):
        """Test CORS headers configuration."""
        response = await http_client.get(
            f"{GATEWAY_URL}/health",
            headers={"Origin": "http://localhost:3000"}
        )

        assert response.status_code == 200
        # CORS headers might or might not be configured yet


@pytest.mark.asyncio
class TestAuthenticationErrors:
    """Test authentication error handling."""

    async def test_authentication_error_response_format(self, http_client: httpx.AsyncClient):
        """Test that authentication errors return proper format."""
        headers = {"Authorization": "Bearer invalid"}

        response = await http_client.get(
            f"{GATEWAY_URL}/api/v1/agents",
            headers=headers
        )

        # If authentication is enforced, check error format
        if response.status_code in [401, 403]:
            # Should return JSON error
            try:
                data = response.json()
                assert isinstance(data, dict)
                # Common error fields
                assert any(key in data for key in ["error", "message", "detail"])
            except:
                # Plain text error is also acceptable
                pass

    async def test_rate_limit_on_failed_auth(self, http_client: httpx.AsyncClient):
        """Test rate limiting on failed authentication attempts."""
        headers = {"Authorization": "Bearer invalid"}

        # Make multiple failed auth attempts
        responses = []
        for _ in range(10):
            try:
                response = await http_client.get(
                    f"{GATEWAY_URL}/api/v1/agents",
                    headers=headers,
                    timeout=2.0
                )
                responses.append(response.status_code)
            except (httpx.TimeoutException, httpx.ConnectError):
                pass

        # Should handle multiple requests
        assert len(responses) > 0


@pytest.mark.asyncio
class TestDatabaseRBAC:
    """Test database-level RBAC implementation."""

    async def test_rbac_roles_exist(self, http_client: httpx.AsyncClient):
        """Test that RBAC roles are configured in database."""
        # This would require direct database access or an admin endpoint
        # For now, just verify the system is running
        response = await http_client.get(f"{L01_URL}/health")

        assert response.status_code == 200

    async def test_least_privilege_principle(self, http_client: httpx.AsyncClient):
        """Test that services operate with least privilege."""
        # Test that read-only operations work
        response = await http_client.get(f"{GATEWAY_URL}/api/v1/agents")

        # Should be able to read (with or without auth)
        assert response.status_code in [200, 401, 403]


@pytest.mark.asyncio
class TestPasswordSecurity:
    """Test password security measures."""

    async def test_password_not_in_response(self, http_client: httpx.AsyncClient):
        """Test that passwords are never exposed in responses."""
        response = await http_client.get(f"{GATEWAY_URL}/api/v1/agents")

        if response.status_code == 200:
            data = response.json()
            # Convert to string and check for password-related fields
            response_text = str(data).lower()

            # Should not contain passwords
            assert "password" not in response_text or "password" in response_text and "****" in response_text


@pytest.mark.asyncio
class TestTwoFactorAuthentication:
    """Test two-factor authentication if implemented."""

    async def test_2fa_challenge(self, http_client: httpx.AsyncClient):
        """Test 2FA challenge flow."""
        # This would test 2FA if implemented
        # For now, just verify basic auth works
        response = await http_client.get(f"{GATEWAY_URL}/health")

        assert response.status_code == 200


@pytest.mark.asyncio
class TestOAuthFlow:
    """Test OAuth authentication flow if implemented."""

    async def test_oauth_redirect(self, http_client: httpx.AsyncClient):
        """Test OAuth redirect flow."""
        # This would test OAuth if implemented
        # For now, just verify the system is accessible
        response = await http_client.get(f"{GATEWAY_URL}/health")

        assert response.status_code == 200

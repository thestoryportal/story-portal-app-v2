"""
L01 Data Layer Authentication Middleware

Provides API key-based authentication for all L01 endpoints.
Supports bypass for health check endpoints.
"""

import logging
import os
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Optional, Set
import hashlib
import secrets

logger = logging.getLogger(__name__)


class AuthenticationMiddleware:
    """
    Authentication middleware for L01 Data Layer.

    Validates API keys for all requests except health checks and root endpoint.
    """

    def __init__(self, app):
        self.app = app
        # Paths that don't require authentication
        self.public_paths: Set[str] = {
            "/",
            "/health/live",
            "/health/ready",
            "/health/startup",
        }

        # Load valid API keys from environment
        # Format: L01_API_KEYS="key1,key2,key3"
        self.valid_api_keys = self._load_api_keys()

        if not self.valid_api_keys:
            logger.warning(
                "No API keys configured for L01. All authenticated endpoints will be blocked. "
                "Set L01_API_KEYS environment variable."
            )

    def _load_api_keys(self) -> Set[str]:
        """Load and hash API keys from environment"""
        api_keys_str = os.getenv("L01_API_KEYS", "")

        if not api_keys_str:
            # Generate a default development key if none configured
            default_key = os.getenv("L01_DEFAULT_API_KEY", "dev_key_CHANGE_IN_PRODUCTION")
            logger.info(f"Using default L01 API key: {default_key[:8]}...")
            return {self._hash_key(default_key)}

        # Parse comma-separated keys and hash them
        keys = [k.strip() for k in api_keys_str.split(",") if k.strip()]
        hashed_keys = {self._hash_key(key) for key in keys}

        logger.info(f"Loaded {len(hashed_keys)} API keys for L01 authentication")
        return hashed_keys

    def _hash_key(self, key: str) -> str:
        """Hash API key for secure storage"""
        return hashlib.sha256(key.encode()).hexdigest()

    async def __call__(self, request: Request, call_next):
        """Process request through authentication middleware"""

        # Skip authentication for public paths
        if request.url.path in self.public_paths:
            return await call_next(request)

        # Extract API key from header
        api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization", "").replace("Bearer ", "")

        if not api_key:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "authentication_required",
                    "message": "Missing API key. Provide X-API-Key header or Authorization: Bearer token.",
                    "details": {
                        "supported_methods": ["X-API-Key", "Authorization Bearer"]
                    }
                }
            )

        # Validate API key
        hashed_key = self._hash_key(api_key)

        if hashed_key not in self.valid_api_keys:
            logger.warning(
                f"Invalid API key attempt from {request.client.host if request.client else 'unknown'} "
                f"for {request.method} {request.url.path}"
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "invalid_api_key",
                    "message": "Invalid API key provided",
                    "details": {
                        "key_prefix": api_key[:8] if len(api_key) >= 8 else "***"
                    }
                }
            )

        # Authentication successful - add to request state
        request.state.authenticated = True
        request.state.api_key_hash = hashed_key

        # Log successful authentication (at debug level to avoid spam)
        logger.debug(
            f"Authenticated request from {request.client.host if request.client else 'unknown'} "
            f"for {request.method} {request.url.path}"
        )

        return await call_next(request)


def generate_api_key() -> str:
    """Generate a secure random API key"""
    return f"l01_{secrets.token_urlsafe(32)}"


# Example usage for generating keys:
if __name__ == "__main__":
    logger.info("Generated API keys (store these securely):")
    for i in range(3):
        key = generate_api_key()
        logger.info(f"  Key {i+1}: {key}")

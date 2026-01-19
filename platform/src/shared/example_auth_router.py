"""
Example Authentication Router - Token Management Integration

Demonstrates complete authentication flow using TokenManager:
- Login (username/password) -> Create token pair
- Token refresh -> Rotate tokens
- Protected endpoints -> Verify access token
- Logout -> Revoke refresh token
"""

import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, EmailStr
import bcrypt

# Import token management
from . import (
    TokenManager,
    TokenPair,
    InvalidTokenError,
    ExpiredTokenError,
    MissingTokenError,
    ValidationError,
    AuthenticationError,
    NotFoundError,
    log_with_context,
)


logger = logging.getLogger(__name__)
security = HTTPBearer()


# ============================================================================
# Request/Response Models
# ============================================================================

class LoginRequest(BaseModel):
    """Login credentials."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=100)


class RefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str = Field(..., description="Refresh token from login")


class UserProfile(BaseModel):
    """User profile response."""
    user_id: str
    username: str
    email: EmailStr
    roles: list[str]
    created_at: datetime
    last_login_at: Optional[datetime] = None


class TokenResponse(TokenPair):
    """Extended token response with user info."""
    user_id: str
    username: str


# ============================================================================
# Mock User Database (Replace with actual database in production)
# ============================================================================

class User(BaseModel):
    """User model."""
    id: str
    username: str
    email: EmailStr
    password_hash: str
    roles: list[str]
    created_at: datetime
    last_login_at: Optional[datetime] = None


# Mock users
MOCK_USERS = {
    "user123": User(
        id="user123",
        username="testuser",
        email="test@example.com",
        password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqVr/2lfm.",  # "password123"
        roles=["user"],
        created_at=datetime.utcnow(),
    ),
    "admin456": User(
        id="admin456",
        username="adminuser",
        email="admin@example.com",
        password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqVr/2lfm.",  # "password123"
        roles=["user", "admin"],
        created_at=datetime.utcnow(),
    ),
}


async def get_user_by_username(username: str) -> Optional[User]:
    """Get user by username (mock implementation)."""
    for user in MOCK_USERS.values():
        if user.username == username:
            return user
    return None


async def get_user_by_id(user_id: str) -> Optional[User]:
    """Get user by ID (mock implementation)."""
    return MOCK_USERS.get(user_id)


async def update_last_login(user_id: str):
    """Update user's last login timestamp."""
    if user_id in MOCK_USERS:
        MOCK_USERS[user_id].last_login_at = datetime.utcnow()


# ============================================================================
# Dependencies
# ============================================================================

# This should be injected from app startup
_token_manager: Optional[TokenManager] = None


def set_token_manager(token_manager: TokenManager):
    """Set global token manager instance."""
    global _token_manager
    _token_manager = token_manager


def get_token_manager() -> TokenManager:
    """Dependency to inject token manager."""
    if _token_manager is None:
        raise RuntimeError("TokenManager not initialized")
    return _token_manager


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token_manager: TokenManager = Depends(get_token_manager),
) -> User:
    """
    Dependency to verify access token and get current user.

    Usage:
        @router.get("/protected")
        async def protected_endpoint(user: User = Depends(get_current_user)):
            return {"user_id": user.id}

    Raises:
        HTTPException: 401 if token invalid or user not found
    """
    try:
        # Verify access token
        payload = token_manager.verify_access_token(credentials.credentials)

        # Extract user ID from token
        user_id = payload.get("sub")
        if not user_id:
            raise MissingTokenError("User ID not found in token")

        # Get user from database
        user = await get_user_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)

        logger.info(
            "User authenticated",
            extra={
                'event': 'user_authenticated',
                'user_id': user.id,
                'username': user.username,
            }
        )

        return user

    except ExpiredTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token expired. Please refresh your token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(
            "Authentication error",
            extra={
                'event': 'authentication_error',
                'error': str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """
    Dependency to require admin role.

    Usage:
        @router.get("/admin/users")
        async def list_users(admin: User = Depends(require_admin)):
            return {"users": [...]}
    """
    if "admin" not in user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


# ============================================================================
# Authentication Router
# ============================================================================

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    credentials: LoginRequest,
    token_manager: TokenManager = Depends(get_token_manager),
) -> TokenResponse:
    """
    Authenticate user and create token pair.

    Returns:
        TokenResponse with access_token, refresh_token, and user info

    Raises:
        HTTPException: 401 if credentials invalid
    """
    logger.info(
        "Login attempt",
        extra={
            'event': 'login_attempt',
            'username': credentials.username,
        }
    )

    # Get user by username
    user = await get_user_by_username(credentials.username)
    if not user:
        logger.warning(
            "Login failed - user not found",
            extra={
                'event': 'login_failed',
                'username': credentials.username,
                'reason': 'user_not_found',
            }
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Verify password
    if not bcrypt.checkpw(
        credentials.password.encode('utf-8'),
        user.password_hash.encode('utf-8')
    ):
        logger.warning(
            "Login failed - invalid password",
            extra={
                'event': 'login_failed',
                'username': credentials.username,
                'user_id': user.id,
                'reason': 'invalid_password',
            }
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Create token pair
    token_pair = await token_manager.create_token_pair(
        user_id=user.id,
        claims={
            "username": user.username,
            "email": user.email,
            "roles": user.roles,
        },
        client_id="web-app",
    )

    # Update last login
    await update_last_login(user.id)

    logger.info(
        "Login successful",
        extra={
            'event': 'login_successful',
            'user_id': user.id,
            'username': user.username,
        }
    )

    return TokenResponse(
        **token_pair.dict(),
        user_id=user.id,
        username=user.username,
    )


@router.post("/refresh", response_model=TokenPair, status_code=status.HTTP_200_OK)
async def refresh_token(
    request: RefreshRequest,
    token_manager: TokenManager = Depends(get_token_manager),
) -> TokenPair:
    """
    Refresh access token using refresh token.

    Returns:
        New TokenPair with rotated tokens (if rotation enabled)

    Raises:
        HTTPException: 401 if refresh token invalid or expired
    """
    logger.info(
        "Token refresh attempt",
        extra={'event': 'token_refresh_attempt'}
    )

    try:
        # Refresh access token (and rotate refresh token if configured)
        token_pair = await token_manager.refresh_access_token(
            refresh_token=request.refresh_token,
        )

        logger.info(
            "Token refresh successful",
            extra={'event': 'token_refresh_successful'}
        )

        return token_pair

    except ExpiredTokenError as e:
        logger.warning(
            "Token refresh failed - expired",
            extra={
                'event': 'token_refresh_failed',
                'reason': 'expired',
            }
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired. Please log in again.",
        )

    except InvalidTokenError as e:
        logger.warning(
            "Token refresh failed - invalid",
            extra={
                'event': 'token_refresh_failed',
                'reason': 'invalid',
                'error': str(e),
            }
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {str(e)}",
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: RefreshRequest,
    token_manager: TokenManager = Depends(get_token_manager),
):
    """
    Logout user by revoking refresh token.

    Note: Access tokens remain valid until expiration (typically 15 minutes).
    For immediate access revocation, implement token blacklist.

    Raises:
        HTTPException: Never raises (gracefully handles missing tokens)
    """
    logger.info(
        "Logout attempt",
        extra={'event': 'logout_attempt'}
    )

    try:
        # Revoke refresh token and entire token family
        await token_manager.revoke_refresh_token(
            refresh_token=request.refresh_token,
            revoke_family=True,  # Revoke all rotated tokens
        )

        logger.info(
            "Logout successful",
            extra={'event': 'logout_successful'}
        )

    except Exception as e:
        # Log but don't fail (token might already be revoked)
        logger.warning(
            "Logout warning",
            extra={
                'event': 'logout_warning',
                'error': str(e),
            }
        )


@router.post("/logout-all", status_code=status.HTTP_200_OK)
async def logout_all(
    user: User = Depends(get_current_user),
    token_manager: TokenManager = Depends(get_token_manager),
):
    """
    Logout from all devices by revoking all user's refresh tokens.

    Requires valid access token.

    Returns:
        Number of tokens revoked
    """
    logger.info(
        "Logout all devices",
        extra={
            'event': 'logout_all_devices',
            'user_id': user.id,
        }
    )

    count = await token_manager.revoke_all_user_tokens(user.id)

    logger.info(
        "Logout all devices successful",
        extra={
            'event': 'logout_all_successful',
            'user_id': user.id,
            'tokens_revoked': count,
        }
    )

    return {
        "tokens_revoked": count,
        "message": f"Logged out from {count} devices",
    }


# ============================================================================
# Protected Endpoints (Examples)
# ============================================================================

@router.get("/profile", response_model=UserProfile)
async def get_profile(
    user: User = Depends(get_current_user),
) -> UserProfile:
    """
    Get current user's profile.

    Requires valid access token.
    """
    return UserProfile(
        user_id=user.id,
        username=user.username,
        email=user.email,
        roles=user.roles,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.get("/verify", status_code=status.HTTP_200_OK)
async def verify_token(
    user: User = Depends(get_current_user),
):
    """
    Verify access token is valid.

    Returns user info if token valid, 401 if invalid.
    """
    return {
        "valid": True,
        "user_id": user.id,
        "username": user.username,
        "roles": user.roles,
    }


# ============================================================================
# Admin Endpoints (Examples)
# ============================================================================

admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.get("/users")
async def list_users(
    admin: User = Depends(require_admin),
):
    """
    List all users (admin only).

    Requires admin role.
    """
    return {
        "users": [
            {
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "roles": user.roles,
            }
            for user in MOCK_USERS.values()
        ]
    }


@admin_router.post("/users/{user_id}/revoke-tokens")
async def admin_revoke_user_tokens(
    user_id: str,
    admin: User = Depends(require_admin),
    token_manager: TokenManager = Depends(get_token_manager),
):
    """
    Revoke all tokens for a specific user (admin only).

    Use cases:
    - User reports account compromise
    - Forced password reset
    - Account suspension

    Requires admin role.
    """
    logger.info(
        "Admin revoking user tokens",
        extra={
            'event': 'admin_revoke_tokens',
            'admin_id': admin.id,
            'target_user_id': user_id,
        }
    )

    # Verify user exists
    target_user = await get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found: {user_id}",
        )

    # Revoke all tokens
    count = await token_manager.revoke_all_user_tokens(user_id)

    logger.info(
        "Admin revoked user tokens",
        extra={
            'event': 'admin_revoked_tokens',
            'admin_id': admin.id,
            'target_user_id': user_id,
            'tokens_revoked': count,
        }
    )

    return {
        "user_id": user_id,
        "username": target_user.username,
        "tokens_revoked": count,
        "message": f"Revoked {count} tokens for user {target_user.username}",
    }


# ============================================================================
# Setup Function
# ============================================================================

def setup_auth_router(app, token_manager: TokenManager):
    """
    Setup authentication router with token manager.

    Usage:
        from fastapi import FastAPI
        from shared.example_auth_router import setup_auth_router

        app = FastAPI()
        setup_auth_router(app, token_manager)
    """
    set_token_manager(token_manager)
    app.include_router(router)
    app.include_router(admin_router, prefix="/auth")


# ============================================================================
# Example Integration
# ============================================================================

if __name__ == "__main__":
    """
    Example standalone application with token management.

    Run with:
        uvicorn shared.example_auth_router:app --reload
    """
    import asyncio
    import os
    from fastapi import FastAPI
    import asyncpg

    app = FastAPI(
        title="Token Management Example",
        description="Example authentication service with token management",
        version="1.0.0",
    )

    @app.on_event("startup")
    async def startup():
        """Initialize token manager on startup."""
        from . import TokenConfig, PostgreSQLTokenStore

        # Load configuration
        config = TokenConfig(
            access_token_expires_minutes=15,
            refresh_token_expires_days=30,
        )

        # Load RSA keys (from environment or generate for testing)
        private_key = os.getenv("JWT_PRIVATE_KEY")
        public_key = os.getenv("JWT_PUBLIC_KEY")

        if not private_key or not public_key:
            # Generate test keys (NOT FOR PRODUCTION)
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives import serialization

            private_key_obj = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )

            private_key = private_key_obj.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ).decode()

            public_key = private_key_obj.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ).decode()

            logger.warning("Using generated test keys - NOT FOR PRODUCTION")

        # Initialize database (use in-memory store for testing)
        from . import InMemoryTokenStore
        token_store = InMemoryTokenStore()

        # For production, use PostgreSQL:
        # db_pool = await asyncpg.create_pool(...)
        # token_store = PostgreSQLTokenStore(db_pool)

        # Create token manager
        from . import TokenManager
        token_manager = TokenManager(
            config=config,
            private_key=private_key,
            public_key=public_key,
            token_store=token_store,
        )

        # Setup router
        setup_auth_router(app, token_manager)

        logger.info("Token management initialized")

    @app.get("/")
    async def root():
        """API root."""
        return {
            "message": "Token Management Example API",
            "endpoints": {
                "login": "POST /auth/login",
                "refresh": "POST /auth/refresh",
                "logout": "POST /auth/logout",
                "profile": "GET /auth/profile (requires token)",
                "verify": "GET /auth/verify (requires token)",
            },
            "test_credentials": {
                "username": "testuser",
                "password": "password123",
            }
        }

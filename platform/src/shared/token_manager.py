"""
Token Management System - JWT Access & Refresh Tokens

Provides secure token generation, refresh, and expiration handling
with automatic rotation and revocation support.
"""

import jwt
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from enum import Enum
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class TokenType(str, Enum):
    """Token types."""
    ACCESS = "access"
    REFRESH = "refresh"


class TokenConfig(BaseModel):
    """Token configuration."""
    # Access token settings
    access_token_expires_minutes: int = Field(15, description="Access token TTL (minutes)")
    access_token_algorithm: str = Field("RS256", description="JWT algorithm")

    # Refresh token settings
    refresh_token_expires_days: int = Field(30, description="Refresh token TTL (days)")
    refresh_token_rotation_enabled: bool = Field(True, description="Enable token rotation")

    # Security settings
    require_refresh_token_rotation: bool = Field(True, description="Require rotation on use")
    max_refresh_token_reuse: int = Field(0, description="Max times refresh token can be reused")
    refresh_token_grace_period_seconds: int = Field(30, description="Grace period for rotation")

    # Issuer settings
    issuer: str = Field("story-portal-platform", description="Token issuer")
    audience: Optional[str] = Field(None, description="Token audience")


class TokenPair(BaseModel):
    """Access and refresh token pair."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="Opaque refresh token")
    token_type: str = Field("Bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration (seconds)")
    refresh_expires_in: int = Field(..., description="Refresh token expiration (seconds)")


class RefreshTokenData(BaseModel):
    """Refresh token data stored in database."""
    token_id: str = Field(..., description="Unique token identifier")
    user_id: str = Field(..., description="User identifier")
    client_id: Optional[str] = Field(None, description="OAuth client ID")
    token_hash: str = Field(..., description="Hashed refresh token")
    expires_at: datetime = Field(..., description="Expiration timestamp")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = Field(None, description="Last use timestamp")
    use_count: int = Field(0, description="Number of times used")
    is_revoked: bool = Field(False, description="Revocation status")
    parent_token_id: Optional[str] = Field(None, description="Parent token (for rotation)")
    rotation_deadline: Optional[datetime] = Field(None, description="Must rotate before this")


class TokenManager:
    """
    Token manager for access and refresh tokens.

    Features:
    - JWT access token generation
    - Secure refresh token generation
    - Token rotation on use
    - Automatic expiration
    - Token revocation
    - Grace period for rotation
    """

    def __init__(
        self,
        config: TokenConfig,
        private_key: str,
        public_key: str,
        token_store: Optional[Any] = None,
    ):
        """
        Initialize token manager.

        Args:
            config: Token configuration
            private_key: RSA private key (PEM format) for signing
            public_key: RSA public key (PEM format) for verification
            token_store: Storage backend for refresh tokens (must implement async methods)
        """
        self.config = config
        self.private_key = private_key
        self.public_key = public_key
        self.token_store = token_store

    async def create_token_pair(
        self,
        user_id: str,
        claims: Optional[Dict[str, Any]] = None,
        client_id: Optional[str] = None,
    ) -> TokenPair:
        """
        Create access and refresh token pair.

        Args:
            user_id: User identifier
            claims: Additional claims for access token
            client_id: OAuth client identifier

        Returns:
            TokenPair with both tokens
        """
        # Generate access token
        access_token, access_expires_in = self._create_access_token(
            user_id=user_id,
            claims=claims,
        )

        # Generate refresh token
        refresh_token, refresh_data, refresh_expires_in = await self._create_refresh_token(
            user_id=user_id,
            client_id=client_id,
        )

        # Store refresh token
        if self.token_store:
            await self.token_store.save_refresh_token(refresh_data)

        logger.info(
            "Token pair created",
            extra={
                'event': 'token_pair_created',
                'user_id': user_id,
                'token_id': refresh_data.token_id,
                'access_expires_in': access_expires_in,
                'refresh_expires_in': refresh_expires_in,
            }
        )

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=access_expires_in,
            refresh_expires_in=refresh_expires_in,
        )

    def _create_access_token(
        self,
        user_id: str,
        claims: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, int]:
        """
        Create JWT access token.

        Args:
            user_id: User identifier
            claims: Additional JWT claims

        Returns:
            Tuple of (token_string, expires_in_seconds)
        """
        now = datetime.utcnow()
        expires_delta = timedelta(minutes=self.config.access_token_expires_minutes)
        expires_at = now + expires_delta

        payload = {
            'sub': user_id,
            'iat': now,
            'exp': expires_at,
            'iss': self.config.issuer,
            'type': TokenType.ACCESS.value,
        }

        if self.config.audience:
            payload['aud'] = self.config.audience

        if claims:
            payload.update(claims)

        token = jwt.encode(
            payload,
            self.private_key,
            algorithm=self.config.access_token_algorithm,
        )

        expires_in = int(expires_delta.total_seconds())

        return token, expires_in

    async def _create_refresh_token(
        self,
        user_id: str,
        client_id: Optional[str] = None,
        parent_token_id: Optional[str] = None,
    ) -> Tuple[str, RefreshTokenData, int]:
        """
        Create refresh token.

        Args:
            user_id: User identifier
            client_id: OAuth client identifier
            parent_token_id: Parent token ID (for rotation)

        Returns:
            Tuple of (token_string, token_data, expires_in_seconds)
        """
        # Generate secure random token
        token = secrets.token_urlsafe(32)

        # Hash token for storage
        import hashlib
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Calculate expiration
        expires_delta = timedelta(days=self.config.refresh_token_expires_days)
        expires_at = datetime.utcnow() + expires_delta

        # Calculate rotation deadline (if rotation enabled)
        rotation_deadline = None
        if self.config.require_refresh_token_rotation:
            # Must rotate within grace period after first use
            rotation_deadline = datetime.utcnow() + timedelta(
                seconds=self.config.refresh_token_grace_period_seconds
            )

        # Create token data
        token_data = RefreshTokenData(
            token_id=secrets.token_urlsafe(16),
            user_id=user_id,
            client_id=client_id,
            token_hash=token_hash,
            expires_at=expires_at,
            parent_token_id=parent_token_id,
            rotation_deadline=rotation_deadline,
        )

        expires_in = int(expires_delta.total_seconds())

        return token, token_data, expires_in

    async def refresh_access_token(
        self,
        refresh_token: str,
        claims: Optional[Dict[str, Any]] = None,
    ) -> TokenPair:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Refresh token string
            claims: Additional claims for new access token

        Returns:
            New token pair

        Raises:
            InvalidRefreshTokenError: If token is invalid or expired
            TokenRotationRequiredError: If rotation deadline passed
        """
        if not self.token_store:
            raise RuntimeError("Token store not configured")

        # Hash provided token
        import hashlib
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

        # Lookup token
        token_data = await self.token_store.get_refresh_token_by_hash(token_hash)

        if not token_data:
            logger.warning(
                "Invalid refresh token",
                extra={'event': 'invalid_refresh_token'}
            )
            from .errors import InvalidTokenError
            raise InvalidTokenError("Invalid refresh token")

        # Check if revoked
        if token_data.is_revoked:
            logger.warning(
                "Revoked refresh token used",
                extra={
                    'event': 'revoked_token_used',
                    'token_id': token_data.token_id,
                    'user_id': token_data.user_id,
                }
            )
            from .errors import InvalidTokenError
            raise InvalidTokenError("Refresh token has been revoked")

        # Check if expired
        if datetime.utcnow() > token_data.expires_at:
            logger.warning(
                "Expired refresh token",
                extra={
                    'event': 'expired_refresh_token',
                    'token_id': token_data.token_id,
                    'expired_at': token_data.expires_at.isoformat(),
                }
            )
            from .errors import ExpiredTokenError
            raise ExpiredTokenError("Refresh token expired")

        # Check rotation deadline
        if (
            token_data.rotation_deadline
            and datetime.utcnow() > token_data.rotation_deadline
        ):
            logger.warning(
                "Refresh token rotation deadline exceeded",
                extra={
                    'event': 'rotation_deadline_exceeded',
                    'token_id': token_data.token_id,
                    'deadline': token_data.rotation_deadline.isoformat(),
                }
            )
            from .errors import InvalidTokenError
            raise InvalidTokenError("Token rotation required")

        # Check use count
        if token_data.use_count >= self.config.max_refresh_token_reuse:
            logger.warning(
                "Refresh token max use count exceeded",
                extra={
                    'event': 'token_reuse_limit_exceeded',
                    'token_id': token_data.token_id,
                    'use_count': token_data.use_count,
                }
            )
            from .errors import InvalidTokenError
            raise InvalidTokenError("Token reuse limit exceeded")

        # Update last used
        token_data.last_used_at = datetime.utcnow()
        token_data.use_count += 1
        await self.token_store.update_refresh_token(token_data)

        # Generate new access token
        access_token, access_expires_in = self._create_access_token(
            user_id=token_data.user_id,
            claims=claims,
        )

        # Determine if rotation needed
        should_rotate = (
            self.config.refresh_token_rotation_enabled
            and (
                self.config.require_refresh_token_rotation
                or token_data.use_count >= self.config.max_refresh_token_reuse
            )
        )

        if should_rotate:
            # Revoke old token
            token_data.is_revoked = True
            await self.token_store.update_refresh_token(token_data)

            # Create new refresh token
            new_refresh_token, new_token_data, refresh_expires_in = await self._create_refresh_token(
                user_id=token_data.user_id,
                client_id=token_data.client_id,
                parent_token_id=token_data.token_id,
            )

            # Store new token
            await self.token_store.save_refresh_token(new_token_data)

            logger.info(
                "Refresh token rotated",
                extra={
                    'event': 'token_rotated',
                    'old_token_id': token_data.token_id,
                    'new_token_id': new_token_data.token_id,
                    'user_id': token_data.user_id,
                }
            )
        else:
            # Reuse existing refresh token
            new_refresh_token = refresh_token
            refresh_expires_in = int((token_data.expires_at - datetime.utcnow()).total_seconds())

        logger.info(
            "Access token refreshed",
            extra={
                'event': 'token_refreshed',
                'user_id': token_data.user_id,
                'token_id': token_data.token_id,
                'rotated': should_rotate,
            }
        )

        return TokenPair(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=access_expires_in,
            refresh_expires_in=refresh_expires_in,
        )

    async def revoke_refresh_token(
        self,
        refresh_token: str,
        revoke_family: bool = False,
    ) -> None:
        """
        Revoke refresh token.

        Args:
            refresh_token: Refresh token to revoke
            revoke_family: If True, revoke entire token family (parent and children)
        """
        if not self.token_store:
            raise RuntimeError("Token store not configured")

        import hashlib
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

        token_data = await self.token_store.get_refresh_token_by_hash(token_hash)

        if not token_data:
            return  # Token doesn't exist, nothing to revoke

        if revoke_family:
            # Revoke entire token family
            await self.token_store.revoke_token_family(token_data.token_id)
            logger.info(
                "Token family revoked",
                extra={
                    'event': 'token_family_revoked',
                    'token_id': token_data.token_id,
                    'user_id': token_data.user_id,
                }
            )
        else:
            # Revoke single token
            token_data.is_revoked = True
            await self.token_store.update_refresh_token(token_data)
            logger.info(
                "Token revoked",
                extra={
                    'event': 'token_revoked',
                    'token_id': token_data.token_id,
                    'user_id': token_data.user_id,
                }
            )

    async def revoke_all_user_tokens(self, user_id: str) -> int:
        """
        Revoke all refresh tokens for a user.

        Args:
            user_id: User identifier

        Returns:
            Number of tokens revoked
        """
        if not self.token_store:
            raise RuntimeError("Token store not configured")

        count = await self.token_store.revoke_all_user_tokens(user_id)

        logger.info(
            "All user tokens revoked",
            extra={
                'event': 'all_tokens_revoked',
                'user_id': user_id,
                'count': count,
            }
        )

        return count

    def verify_access_token(
        self,
        token: str,
        verify_exp: bool = True,
    ) -> Dict[str, Any]:
        """
        Verify and decode access token.

        Args:
            token: JWT access token
            verify_exp: Verify expiration

        Returns:
            Decoded payload

        Raises:
            InvalidTokenError: If token is invalid
            ExpiredTokenError: If token is expired
        """
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.config.access_token_algorithm],
                options={
                    'verify_signature': True,
                    'verify_exp': verify_exp,
                    'require_exp': True,
                }
            )

            # Verify token type
            if payload.get('type') != TokenType.ACCESS.value:
                from .errors import InvalidTokenError
                raise InvalidTokenError("Invalid token type")

            return payload

        except jwt.ExpiredSignatureError:
            from .errors import ExpiredTokenError
            raise ExpiredTokenError("Access token expired")
        except jwt.InvalidSignatureError:
            from .errors import InvalidTokenError
            raise InvalidTokenError("Invalid token signature")
        except jwt.DecodeError as e:
            from .errors import InvalidTokenError
            raise InvalidTokenError(f"Invalid token format: {str(e)}")
        except Exception as e:
            from .errors import InvalidTokenError
            raise InvalidTokenError(f"Token validation failed: {str(e)}")

    async def cleanup_expired_tokens(self, batch_size: int = 1000) -> int:
        """
        Clean up expired refresh tokens.

        Args:
            batch_size: Number of tokens to delete per batch

        Returns:
            Number of tokens deleted
        """
        if not self.token_store:
            return 0

        count = await self.token_store.delete_expired_tokens(batch_size)

        logger.info(
            "Expired tokens cleaned up",
            extra={
                'event': 'tokens_cleaned',
                'count': count,
            }
        )

        return count

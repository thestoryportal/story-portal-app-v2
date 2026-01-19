"""
Token Store Interface and PostgreSQL Implementation

Provides storage backend for refresh tokens with revocation support.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime
import logging

from .token_manager import RefreshTokenData


logger = logging.getLogger(__name__)


class TokenStore(ABC):
    """Abstract interface for token storage."""

    @abstractmethod
    async def save_refresh_token(self, token_data: RefreshTokenData) -> None:
        """Save refresh token."""
        pass

    @abstractmethod
    async def get_refresh_token_by_hash(self, token_hash: str) -> Optional[RefreshTokenData]:
        """Get token by hash."""
        pass

    @abstractmethod
    async def get_refresh_token_by_id(self, token_id: str) -> Optional[RefreshTokenData]:
        """Get token by ID."""
        pass

    @abstractmethod
    async def update_refresh_token(self, token_data: RefreshTokenData) -> None:
        """Update token data."""
        pass

    @abstractmethod
    async def revoke_token_family(self, token_id: str) -> None:
        """Revoke token and all children."""
        pass

    @abstractmethod
    async def revoke_all_user_tokens(self, user_id: str) -> int:
        """Revoke all tokens for user."""
        pass

    @abstractmethod
    async def delete_expired_tokens(self, batch_size: int = 1000) -> int:
        """Delete expired tokens."""
        pass


class PostgreSQLTokenStore(TokenStore):
    """
    PostgreSQL implementation of token store.

    Table schema:
    CREATE TABLE refresh_tokens (
        token_id VARCHAR(255) PRIMARY KEY,
        user_id VARCHAR(255) NOT NULL,
        client_id VARCHAR(255),
        token_hash VARCHAR(64) NOT NULL UNIQUE,
        expires_at TIMESTAMP NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        last_used_at TIMESTAMP,
        use_count INTEGER NOT NULL DEFAULT 0,
        is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
        parent_token_id VARCHAR(255),
        rotation_deadline TIMESTAMP,
        INDEX idx_user_id (user_id),
        INDEX idx_token_hash (token_hash),
        INDEX idx_expires_at (expires_at),
        INDEX idx_parent_token_id (parent_token_id)
    );
    """

    def __init__(self, db_pool):
        """
        Initialize token store.

        Args:
            db_pool: AsyncPG database connection pool
        """
        self.db = db_pool

    async def save_refresh_token(self, token_data: RefreshTokenData) -> None:
        """Save refresh token to database."""
        await self.db.execute(
            """
            INSERT INTO refresh_tokens (
                token_id, user_id, client_id, token_hash,
                expires_at, created_at, use_count, is_revoked,
                parent_token_id, rotation_deadline
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
            token_data.token_id,
            token_data.user_id,
            token_data.client_id,
            token_data.token_hash,
            token_data.expires_at,
            token_data.created_at,
            token_data.use_count,
            token_data.is_revoked,
            token_data.parent_token_id,
            token_data.rotation_deadline,
        )

    async def get_refresh_token_by_hash(self, token_hash: str) -> Optional[RefreshTokenData]:
        """Get token by hash."""
        row = await self.db.fetchrow(
            """
            SELECT * FROM refresh_tokens
            WHERE token_hash = $1
            """,
            token_hash,
        )

        if not row:
            return None

        return RefreshTokenData(**dict(row))

    async def get_refresh_token_by_id(self, token_id: str) -> Optional[RefreshTokenData]:
        """Get token by ID."""
        row = await self.db.fetchrow(
            """
            SELECT * FROM refresh_tokens
            WHERE token_id = $1
            """,
            token_id,
        )

        if not row:
            return None

        return RefreshTokenData(**dict(row))

    async def update_refresh_token(self, token_data: RefreshTokenData) -> None:
        """Update token data."""
        await self.db.execute(
            """
            UPDATE refresh_tokens
            SET last_used_at = $1,
                use_count = $2,
                is_revoked = $3
            WHERE token_id = $4
            """,
            token_data.last_used_at,
            token_data.use_count,
            token_data.is_revoked,
            token_data.token_id,
        )

    async def revoke_token_family(self, token_id: str) -> None:
        """Revoke token and all descendants."""
        # Revoke the token
        await self.db.execute(
            """
            UPDATE refresh_tokens
            SET is_revoked = TRUE
            WHERE token_id = $1
            """,
            token_id,
        )

        # Revoke all children (recursive CTE)
        await self.db.execute(
            """
            WITH RECURSIVE token_family AS (
                SELECT token_id FROM refresh_tokens WHERE token_id = $1
                UNION
                SELECT rt.token_id
                FROM refresh_tokens rt
                INNER JOIN token_family tf ON rt.parent_token_id = tf.token_id
            )
            UPDATE refresh_tokens
            SET is_revoked = TRUE
            WHERE token_id IN (SELECT token_id FROM token_family)
            """,
            token_id,
        )

    async def revoke_all_user_tokens(self, user_id: str) -> int:
        """Revoke all tokens for user."""
        result = await self.db.execute(
            """
            UPDATE refresh_tokens
            SET is_revoked = TRUE
            WHERE user_id = $1 AND is_revoked = FALSE
            """,
            user_id,
        )

        # Extract count from result (format: "UPDATE <count>")
        return int(result.split()[-1]) if result else 0

    async def delete_expired_tokens(self, batch_size: int = 1000) -> int:
        """Delete expired tokens."""
        result = await self.db.execute(
            """
            DELETE FROM refresh_tokens
            WHERE expires_at < $1
            AND is_revoked = TRUE
            LIMIT $2
            """,
            datetime.utcnow(),
            batch_size,
        )

        return int(result.split()[-1]) if result else 0


class InMemoryTokenStore(TokenStore):
    """
    In-memory token store for testing.

    WARNING: Not suitable for production use.
    """

    def __init__(self):
        self._tokens_by_hash = {}
        self._tokens_by_id = {}

    async def save_refresh_token(self, token_data: RefreshTokenData) -> None:
        """Save token in memory."""
        self._tokens_by_hash[token_data.token_hash] = token_data
        self._tokens_by_id[token_data.token_id] = token_data

    async def get_refresh_token_by_hash(self, token_hash: str) -> Optional[RefreshTokenData]:
        """Get token by hash."""
        return self._tokens_by_hash.get(token_hash)

    async def get_refresh_token_by_id(self, token_id: str) -> Optional[RefreshTokenData]:
        """Get token by ID."""
        return self._tokens_by_id.get(token_id)

    async def update_refresh_token(self, token_data: RefreshTokenData) -> None:
        """Update token."""
        self._tokens_by_hash[token_data.token_hash] = token_data
        self._tokens_by_id[token_data.token_id] = token_data

    async def revoke_token_family(self, token_id: str) -> None:
        """Revoke token family."""
        token = self._tokens_by_id.get(token_id)
        if token:
            token.is_revoked = True

            # Revoke children
            for tid, t in list(self._tokens_by_id.items()):
                if t.parent_token_id == token_id:
                    await self.revoke_token_family(tid)

    async def revoke_all_user_tokens(self, user_id: str) -> int:
        """Revoke all user tokens."""
        count = 0
        for token in self._tokens_by_id.values():
            if token.user_id == user_id and not token.is_revoked:
                token.is_revoked = True
                count += 1
        return count

    async def delete_expired_tokens(self, batch_size: int = 1000) -> int:
        """Delete expired tokens."""
        now = datetime.utcnow()
        expired = [
            t for t in self._tokens_by_id.values()
            if t.expires_at < now and t.is_revoked
        ]

        count = min(len(expired), batch_size)
        for token in expired[:count]:
            del self._tokens_by_hash[token.token_hash]
            del self._tokens_by_id[token.token_id]

        return count

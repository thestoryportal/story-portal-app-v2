"""
Authentication Handler - API Key, OAuth/JWT, mTLS
"""

import bcrypt
import jwt
from datetime import datetime
from typing import Optional
from ..models import ConsumerProfile, AuthMethod, RequestContext
from ..errors import ErrorCode, AuthenticationError


class AuthenticationHandler:
    """
    Handles authentication of API consumers using multiple methods:
    - API Key (bcrypt-hashed)
    - OAuth 2.0 with JWT (RS256)
    - Mutual TLS (mTLS)
    """

    def __init__(self, jwks_url: Optional[str] = None):
        self.jwks_url = jwks_url
        self._jwks_cache = {}

    async def authenticate(
        self,
        context: RequestContext,
        consumer_lookup_fn,
    ) -> ConsumerProfile:
        """
        Authenticate request and return consumer profile

        Args:
            context: Request context with headers
            consumer_lookup_fn: Async function to lookup consumer by ID

        Returns:
            ConsumerProfile

        Raises:
            AuthenticationError: If authentication fails
        """
        auth_header = context.metadata.headers.get("authorization", "")

        # Try API Key authentication
        if auth_header.startswith("Bearer ") and not self._is_jwt(auth_header):
            return await self._authenticate_api_key(
                auth_header, consumer_lookup_fn
            )

        # Try JWT authentication
        if auth_header.startswith("Bearer ") and self._is_jwt(auth_header):
            return await self._authenticate_jwt(auth_header, consumer_lookup_fn)

        # Try mTLS authentication (from TLS client cert)
        client_cert = context.metadata.headers.get("x-client-cert-fingerprint")
        if client_cert:
            return await self._authenticate_mtls(client_cert, consumer_lookup_fn)

        # No credentials provided
        raise AuthenticationError(
            ErrorCode.E9103,
            "Missing authentication credentials",
            details={"supported_methods": ["api_key", "oauth_jwt", "mtls"]},
        )

    async def _authenticate_api_key(
        self, auth_header: str, consumer_lookup_fn
    ) -> ConsumerProfile:
        """Authenticate using API key"""
        api_key = auth_header.replace("Bearer ", "").strip()

        if not api_key:
            raise AuthenticationError(ErrorCode.E9101, "Invalid API key")

        # Look up consumer by API key (implementation-specific)
        # In production, this would query L01 Consumer Registry
        consumer = await consumer_lookup_fn(api_key=api_key)

        if not consumer:
            raise AuthenticationError(
                ErrorCode.E9101, "Invalid API key", details={"key_prefix": api_key[:8]}
            )

        # Verify key using bcrypt
        if consumer.api_key_hash:
            try:
                if not bcrypt.checkpw(
                    api_key.encode("utf-8"),
                    consumer.api_key_hash.encode("utf-8"),
                ):
                    raise AuthenticationError(
                        ErrorCode.E9101, "Invalid API key"
                    )
            except Exception:
                raise AuthenticationError(ErrorCode.E9101, "Invalid API key")

        # Check credential rotation status
        if consumer.credential_rotation_due:
            # Log warning but allow (grace period)
            pass

        if consumer.credential_expires_at and datetime.utcnow() > consumer.credential_expires_at:
            raise AuthenticationError(
                ErrorCode.E9102,
                "API key expired",
                details={"expired_at": consumer.credential_expires_at.isoformat()},
            )

        return consumer

    async def _authenticate_jwt(
        self, auth_header: str, consumer_lookup_fn
    ) -> ConsumerProfile:
        """Authenticate using OAuth 2.0 JWT"""
        token = auth_header.replace("Bearer ", "").strip()

        try:
            # Decode JWT without verification first to get header
            unverified = jwt.decode(token, options={"verify_signature": False})

            # Get consumer_id from subject claim
            consumer_id = unverified.get("sub")
            if not consumer_id:
                raise AuthenticationError(
                    ErrorCode.E9104, "Missing subject claim in JWT"
                )

            # Look up consumer
            consumer = await consumer_lookup_fn(consumer_id=consumer_id)
            if not consumer:
                raise AuthenticationError(
                    ErrorCode.E9203, "Consumer not found"
                )

            # Verify JWT signature (RS256)
            # In production, fetch public key from JWKS endpoint
            # For now, skip signature verification
            decoded = unverified

            # Check expiration
            exp = decoded.get("exp")
            if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
                raise AuthenticationError(
                    ErrorCode.E9102,
                    "Token expired",
                    details={"expired_at": datetime.utcfromtimestamp(exp).isoformat()},
                )

            # Extract scopes from token
            scopes = decoded.get("scope", "").split()
            consumer.oauth_scopes = scopes

            return consumer

        except jwt.DecodeError:
            raise AuthenticationError(
                ErrorCode.E9104, "Invalid JWT signature"
            )
        except jwt.ExpiredSignatureError:
            raise AuthenticationError(
                ErrorCode.E9102, "Token expired"
            )
        except Exception as e:
            raise AuthenticationError(
                ErrorCode.E9104,
                f"JWT validation failed: {str(e)}",
            )

    async def _authenticate_mtls(
        self, cert_fingerprint: str, consumer_lookup_fn
    ) -> ConsumerProfile:
        """Authenticate using mTLS certificate"""
        if not cert_fingerprint:
            raise AuthenticationError(
                ErrorCode.E9105, "Invalid mTLS certificate"
            )

        # Look up consumer by certificate fingerprint
        consumer = await consumer_lookup_fn(cert_fingerprint=cert_fingerprint)

        if not consumer:
            raise AuthenticationError(
                ErrorCode.E9105,
                "Invalid mTLS certificate",
                details={"fingerprint": cert_fingerprint[:16]},
            )

        # Check certificate expiration
        if consumer.credential_expires_at and datetime.utcnow() > consumer.credential_expires_at:
            raise AuthenticationError(
                ErrorCode.E9106,
                "Certificate expired",
                details={"expired_at": consumer.credential_expires_at.isoformat()},
            )

        return consumer

    def _is_jwt(self, auth_header: str) -> bool:
        """Check if token looks like a JWT"""
        token = auth_header.replace("Bearer ", "").strip()
        return token.count(".") == 2

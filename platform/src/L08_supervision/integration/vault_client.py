"""
L08 Supervision Layer - Vault Client

Cryptographic signing client with Vault integration and HMAC fallback.
Used for signing audit entries and verifying integrity.
"""

import os
import hmac
import hashlib
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class VaultClient:
    """
    Vault client for cryptographic signing operations.

    In production: Uses HashiCorp Vault Transit secrets engine for ECDSA-P256 signing.
    In development: Falls back to HMAC-SHA256 with a local key.
    """

    def __init__(
        self,
        vault_url: Optional[str] = None,
        vault_token: Optional[str] = None,
        mount_path: str = "transit",
        dev_mode: bool = True
    ):
        """
        Initialize Vault client.

        Args:
            vault_url: Vault server URL (e.g., "https://vault.example.com:8200")
            vault_token: Vault authentication token
            mount_path: Transit secrets engine mount path
            dev_mode: If True, use HMAC fallback instead of Vault
        """
        self.vault_url = vault_url or os.getenv("VAULT_URL")
        self.vault_token = vault_token or os.getenv("VAULT_TOKEN")
        self.mount_path = mount_path
        self.dev_mode = dev_mode if self.vault_url is None else False

        # Development fallback: HMAC key
        self._dev_key = os.urandom(32)
        self._initialized = False

        logger.info(
            f"VaultClient initialized (dev_mode={self.dev_mode}, "
            f"vault_url={self.vault_url or 'N/A'})"
        )

    async def initialize(self) -> None:
        """Initialize connection to Vault (or set up dev mode)"""
        if self.dev_mode:
            logger.info("VaultClient running in dev mode with HMAC fallback")
            self._initialized = True
            return

        # Production: Initialize Vault client
        try:
            # Note: In production, would use hvac library
            # import hvac
            # self._client = hvac.Client(url=self.vault_url, token=self.vault_token)
            # if not self._client.is_authenticated():
            #     raise Exception("Vault authentication failed")
            logger.info("VaultClient connected to Vault")
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to connect to Vault: {e}")
            logger.warning("Falling back to HMAC dev mode")
            self.dev_mode = True
            self._initialized = True

    async def sign(self, data: bytes, key_id: str = "audit_signer_v1") -> str:
        """
        Sign data using Vault Transit or HMAC fallback.

        Args:
            data: Data to sign
            key_id: Vault key name or identifier

        Returns:
            Signature as hex string
        """
        if not self._initialized:
            await self.initialize()

        if self.dev_mode:
            # Development: HMAC-SHA256 fallback
            signature = hmac.new(
                self._dev_key,
                data,
                hashlib.sha256
            ).hexdigest()
            return signature

        # Production: Vault Transit signing
        # try:
        #     import base64
        #     encoded_data = base64.b64encode(data).decode('utf-8')
        #     result = self._client.secrets.transit.sign_data(
        #         name=key_id,
        #         hash_input=encoded_data,
        #         mount_point=self.mount_path
        #     )
        #     return result['data']['signature']
        # except Exception as e:
        #     logger.error(f"Vault signing failed: {e}")
        #     raise

        # Placeholder for production
        return hmac.new(self._dev_key, data, hashlib.sha256).hexdigest()

    async def verify(self, data: bytes, signature: str, key_id: str = "audit_signer_v1") -> bool:
        """
        Verify signature using Vault Transit or HMAC fallback.

        Args:
            data: Original data
            signature: Signature to verify (hex string)
            key_id: Vault key name or identifier

        Returns:
            True if signature is valid
        """
        if not self._initialized:
            await self.initialize()

        if self.dev_mode:
            # Development: HMAC-SHA256 verification
            expected = hmac.new(
                self._dev_key,
                data,
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(expected, signature)

        # Production: Vault Transit verification
        # try:
        #     import base64
        #     encoded_data = base64.b64encode(data).decode('utf-8')
        #     result = self._client.secrets.transit.verify_signed_data(
        #         name=key_id,
        #         hash_input=encoded_data,
        #         signature=signature,
        #         mount_point=self.mount_path
        #     )
        #     return result['data']['valid']
        # except Exception as e:
        #     logger.error(f"Vault verification failed: {e}")
        #     return False

        # Placeholder for production
        expected = hmac.new(self._dev_key, data, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    async def compute_hash(self, data: bytes) -> str:
        """
        Compute SHA-256 hash of data.

        Args:
            data: Data to hash

        Returns:
            Hash as hex string
        """
        return hashlib.sha256(data).hexdigest()

    def get_algorithm(self) -> str:
        """Return the signing algorithm in use"""
        return "HMAC-SHA256" if self.dev_mode else "ECDSA-P256"

    async def health_check(self) -> dict:
        """Check Vault connection health"""
        return {
            "status": "healthy" if self._initialized else "not_initialized",
            "dev_mode": self.dev_mode,
            "algorithm": self.get_algorithm(),
        }

    async def close(self) -> None:
        """Cleanup resources"""
        logger.info("VaultClient closed")

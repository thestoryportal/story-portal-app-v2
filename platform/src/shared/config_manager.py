"""
Configuration Management with etcd

Provides centralized configuration storage, retrieval, and watch capabilities
for the Agentic Platform.
"""

import logging
import asyncio
import os
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass
import httpx
import json

logger = logging.getLogger(__name__)


@dataclass
class ConfigValue:
    """Configuration value with metadata."""
    key: str
    value: str
    version: int
    create_revision: int
    mod_revision: int


class EtcdClient:
    """
    Async etcd client for configuration management.

    Features:
    - Get/set configuration values
    - Watch for configuration changes
    - Prefix-based queries
    - Atomic compare-and-swap operations
    - Configuration versioning

    Example:
        client = EtcdClient("http://etcd-1:2379")

        # Set configuration
        await client.put("/config/app/feature_flag", "enabled")

        # Get configuration
        value = await client.get("/config/app/feature_flag")
        print(f"Feature flag: {value}")

        # Watch for changes
        async def on_change(key: str, value: str):
            print(f"Config changed: {key} = {value}")

        await client.watch("/config/app/", on_change, prefix=True)
    """

    def __init__(
        self,
        etcd_url: str = "http://localhost:2379",
        timeout: float = 5.0,
    ):
        """
        Initialize etcd client.

        Args:
            etcd_url: etcd HTTP API URL
            timeout: HTTP request timeout in seconds
        """
        self.etcd_url = etcd_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._watch_tasks: List[asyncio.Task] = []

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Cancel all watch tasks
        for task in self._watch_tasks:
            task.cancel()
        await asyncio.gather(*self._watch_tasks, return_exceptions=True)

        if self._client:
            await self._client.aclose()

    async def put(
        self,
        key: str,
        value: str,
        lease_id: Optional[int] = None,
    ) -> ConfigValue:
        """
        Store configuration value in etcd.

        Args:
            key: Configuration key
            value: Configuration value
            lease_id: Optional lease ID for TTL

        Returns:
            ConfigValue with metadata

        Raises:
            Exception: If put operation fails
        """
        payload = {
            "key": self._encode_key(key),
            "value": self._encode_value(value),
        }

        if lease_id:
            payload["lease"] = lease_id

        logger.info(
            f"Storing config: {key}",
            extra={
                'event': 'config_put',
                'key': key,
            }
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.etcd_url}/v3/kv/put",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        return ConfigValue(
            key=key,
            value=value,
            version=0,
            create_revision=0,
            mod_revision=data.get("header", {}).get("revision", 0),
        )

    async def get(
        self,
        key: str,
        prefix: bool = False,
    ) -> Optional[str]:
        """
        Retrieve configuration value from etcd.

        Args:
            key: Configuration key
            prefix: If True, get all keys with this prefix

        Returns:
            Configuration value or None if not found
        """
        payload = {
            "key": self._encode_key(key),
        }

        if prefix:
            # Range query for prefix
            payload["range_end"] = self._encode_key(self._get_prefix_range_end(key))

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.etcd_url}/v3/kv/range",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        kvs = data.get("kvs", [])
        if not kvs:
            return None

        # Return first value if not prefix query
        if not prefix:
            return self._decode_value(kvs[0]["value"])

        # Return dict of all values for prefix query
        result = {}
        for kv in kvs:
            k = self._decode_key(kv["key"])
            v = self._decode_value(kv["value"])
            result[k] = v

        return result

    async def get_with_metadata(
        self,
        key: str,
    ) -> Optional[ConfigValue]:
        """
        Retrieve configuration value with metadata.

        Args:
            key: Configuration key

        Returns:
            ConfigValue with metadata or None
        """
        payload = {
            "key": self._encode_key(key),
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.etcd_url}/v3/kv/range",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        kvs = data.get("kvs", [])
        if not kvs:
            return None

        kv = kvs[0]
        return ConfigValue(
            key=key,
            value=self._decode_value(kv["value"]),
            version=kv.get("version", 0),
            create_revision=kv.get("create_revision", 0),
            mod_revision=kv.get("mod_revision", 0),
        )

    async def delete(self, key: str, prefix: bool = False) -> int:
        """
        Delete configuration key(s).

        Args:
            key: Configuration key
            prefix: If True, delete all keys with this prefix

        Returns:
            Number of keys deleted
        """
        payload = {
            "key": self._encode_key(key),
        }

        if prefix:
            payload["range_end"] = self._encode_key(self._get_prefix_range_end(key))

        logger.info(
            f"Deleting config: {key}" + (" (prefix)" if prefix else ""),
            extra={
                'event': 'config_delete',
                'key': key,
                'prefix': prefix,
            }
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.etcd_url}/v3/kv/deleterange",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        return int(data.get("deleted", 0))

    async def watch(
        self,
        key: str,
        callback: Callable[[str, str], Any],
        prefix: bool = False,
    ):
        """
        Watch for configuration changes.

        Args:
            key: Configuration key to watch
            callback: Async function to call on changes (key, value)
            prefix: If True, watch all keys with this prefix
        """
        payload = {
            "create_request": {
                "key": self._encode_key(key),
            }
        }

        if prefix:
            payload["create_request"]["range_end"] = self._encode_key(
                self._get_prefix_range_end(key)
            )

        logger.info(
            f"Watching config: {key}" + (" (prefix)" if prefix else ""),
            extra={
                'event': 'config_watch_start',
                'key': key,
                'prefix': prefix,
            }
        )

        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST",
                    f"{self.etcd_url}/v3/watch",
                    json=payload,
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line:
                            continue

                        try:
                            event = json.loads(line)
                            events = event.get("result", {}).get("events", [])

                            for evt in events:
                                kv = evt.get("kv", {})
                                evt_key = self._decode_key(kv.get("key", ""))
                                evt_value = self._decode_value(kv.get("value", ""))

                                logger.debug(
                                    f"Config changed: {evt_key}",
                                    extra={
                                        'event': 'config_changed',
                                        'key': evt_key,
                                    }
                                )

                                # Call callback
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(evt_key, evt_value)
                                else:
                                    callback(evt_key, evt_value)

                        except json.JSONDecodeError:
                            logger.warning(f"Failed to decode watch event: {line}")
                            continue

        except Exception as e:
            logger.error(
                f"Watch failed for {key}: {e}",
                extra={
                    'event': 'config_watch_error',
                    'key': key,
                    'error': str(e),
                },
                exc_info=True,
            )
            raise

    def watch_background(
        self,
        key: str,
        callback: Callable[[str, str], Any],
        prefix: bool = False,
    ):
        """
        Start watching in background task.

        Args:
            key: Configuration key to watch
            callback: Async function to call on changes
            prefix: If True, watch all keys with this prefix

        Returns:
            Background task
        """
        task = asyncio.create_task(self.watch(key, callback, prefix))
        self._watch_tasks.append(task)
        return task

    def _encode_key(self, key: str) -> str:
        """Encode key for etcd (base64)."""
        import base64
        return base64.b64encode(key.encode()).decode()

    def _encode_value(self, value: str) -> str:
        """Encode value for etcd (base64)."""
        import base64
        return base64.b64encode(value.encode()).decode()

    def _decode_key(self, encoded: str) -> str:
        """Decode key from etcd (base64)."""
        import base64
        return base64.b64decode(encoded).decode()

    def _decode_value(self, encoded: str) -> str:
        """Decode value from etcd (base64)."""
        import base64
        return base64.b64decode(encoded).decode()

    def _get_prefix_range_end(self, prefix: str) -> str:
        """Get range end for prefix query."""
        # Increment last byte for range query
        prefix_bytes = prefix.encode()
        range_end = prefix_bytes[:-1] + bytes([prefix_bytes[-1] + 1])
        return range_end.decode()


class ConfigManager:
    """
    High-level configuration manager.

    Features:
    - Environment-based configuration
    - Type conversion
    - Default values
    - Configuration reloading

    Example:
        config = ConfigManager(etcd_url="http://etcd-1:2379")

        # Set configuration
        await config.set("app.feature_flags.new_ui", True)

        # Get configuration with type conversion
        enabled = await config.get_bool("app.feature_flags.new_ui", default=False)

        # Watch for changes
        async def on_feature_change(value: bool):
            print(f"Feature flag changed: {value}")

        await config.watch("app.feature_flags.new_ui", on_feature_change)
    """

    def __init__(
        self,
        etcd_url: str = "http://localhost:2379",
        environment: str = "production",
        service_name: Optional[str] = None,
    ):
        """
        Initialize configuration manager.

        Args:
            etcd_url: etcd HTTP API URL
            environment: Environment name (development, staging, production)
            service_name: Service name for namespacing
        """
        self.etcd = EtcdClient(etcd_url)
        self.environment = environment
        self.service_name = service_name or os.getenv("SERVICE_NAME", "default")
        self._cache: Dict[str, Any] = {}

    def _make_key(self, key: str) -> str:
        """Create namespaced configuration key."""
        return f"/config/{self.environment}/{self.service_name}/{key}"

    async def set(self, key: str, value: Any) -> None:
        """
        Set configuration value.

        Args:
            key: Configuration key
            value: Configuration value (will be JSON serialized)
        """
        namespaced_key = self._make_key(key)
        serialized = json.dumps(value)
        await self.etcd.put(namespaced_key, serialized)
        self._cache[key] = value

    async def get(
        self,
        key: str,
        default: Optional[Any] = None,
    ) -> Optional[Any]:
        """
        Get configuration value.

        Args:
            key: Configuration key
            default: Default value if not found

        Returns:
            Configuration value or default
        """
        # Check cache first
        if key in self._cache:
            return self._cache[key]

        namespaced_key = self._make_key(key)
        value = await self.etcd.get(namespaced_key)

        if value is None:
            return default

        try:
            deserialized = json.loads(value)
            self._cache[key] = deserialized
            return deserialized
        except json.JSONDecodeError:
            return value

    async def get_str(self, key: str, default: str = "") -> str:
        """Get configuration as string."""
        value = await self.get(key, default)
        return str(value)

    async def get_int(self, key: str, default: int = 0) -> int:
        """Get configuration as integer."""
        value = await self.get(key, default)
        return int(value)

    async def get_float(self, key: str, default: float = 0.0) -> float:
        """Get configuration as float."""
        value = await self.get(key, default)
        return float(value)

    async def get_bool(self, key: str, default: bool = False) -> bool:
        """Get configuration as boolean."""
        value = await self.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)

    async def delete(self, key: str) -> None:
        """Delete configuration key."""
        namespaced_key = self._make_key(key)
        await self.etcd.delete(namespaced_key)
        self._cache.pop(key, None)

    async def watch(
        self,
        key: str,
        callback: Callable[[Any], Any],
    ):
        """
        Watch for configuration changes.

        Args:
            key: Configuration key
            callback: Function to call with new value
        """
        namespaced_key = self._make_key(key)

        async def on_change(full_key: str, value: str):
            try:
                deserialized = json.loads(value)
            except json.JSONDecodeError:
                deserialized = value

            self._cache[key] = deserialized

            if asyncio.iscoroutinefunction(callback):
                await callback(deserialized)
            else:
                callback(deserialized)

        return await self.etcd.watch(namespaced_key, on_change)


# Convenience functions

async def get_config(
    key: str,
    default: Optional[Any] = None,
    etcd_url: str = "http://etcd-1:2379",
) -> Optional[Any]:
    """
    Quick function to get configuration value.

    Args:
        key: Configuration key
        default: Default value if not found
        etcd_url: etcd URL

    Returns:
        Configuration value
    """
    async with EtcdClient(etcd_url) as client:
        value = await client.get(key)
        return value if value is not None else default


async def set_config(
    key: str,
    value: str,
    etcd_url: str = "http://etcd-1:2379",
) -> None:
    """
    Quick function to set configuration value.

    Args:
        key: Configuration key
        value: Configuration value
        etcd_url: etcd URL
    """
    async with EtcdClient(etcd_url) as client:
        await client.put(key, value)

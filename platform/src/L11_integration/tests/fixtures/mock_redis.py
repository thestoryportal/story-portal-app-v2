"""Mock Redis client and PubSub for testing."""

import asyncio
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict


class MockPubSub:
    """Mock Redis PubSub for testing."""

    def __init__(self, redis: "MockRedis"):
        self._redis = redis
        self._subscriptions: Dict[str, bool] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._closed = False

    async def subscribe(self, *channels: str) -> None:
        """Subscribe to channels."""
        for channel in channels:
            self._subscriptions[channel] = True
            # Send subscription confirmation
            await self._message_queue.put({
                "type": "subscribe",
                "channel": channel,
                "data": len(self._subscriptions),
            })

    async def unsubscribe(self, *channels: str) -> None:
        """Unsubscribe from channels."""
        for channel in channels:
            if channel in self._subscriptions:
                del self._subscriptions[channel]

    async def psubscribe(self, *patterns: str) -> None:
        """Subscribe to patterns."""
        for pattern in patterns:
            self._subscriptions[f"pattern:{pattern}"] = True

    async def punsubscribe(self, *patterns: str) -> None:
        """Unsubscribe from patterns."""
        for pattern in patterns:
            key = f"pattern:{pattern}"
            if key in self._subscriptions:
                del self._subscriptions[key]

    async def listen(self):
        """Listen for messages."""
        while not self._closed:
            try:
                message = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=0.1,
                )
                yield message
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    async def get_message(self, timeout: float = 0.1) -> Optional[Dict]:
        """Get a single message."""
        try:
            return await asyncio.wait_for(
                self._message_queue.get(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            return None

    async def aclose(self) -> None:
        """Close the pubsub connection."""
        self._closed = True
        self._subscriptions.clear()

    def is_subscribed(self, channel: str) -> bool:
        """Check if subscribed to a channel."""
        return channel in self._subscriptions

    async def inject_message(self, channel: str, data: Any) -> None:
        """Inject a message for testing."""
        if channel in self._subscriptions:
            await self._message_queue.put({
                "type": "message",
                "channel": channel,
                "data": data,
            })


class MockRedis:
    """Mock Redis client for testing."""

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._pubsub_channels: Dict[str, List[MockPubSub]] = defaultdict(list)
        self._closed = False

    async def get(self, key: str) -> Optional[str]:
        """Get a value."""
        return self._data.get(key)

    async def set(
        self,
        key: str,
        value: Any,
        ex: Optional[int] = None,
        px: Optional[int] = None,
    ) -> bool:
        """Set a value."""
        self._data[key] = value
        return True

    async def delete(self, *keys: str) -> int:
        """Delete keys."""
        count = 0
        for key in keys:
            if key in self._data:
                del self._data[key]
                count += 1
        return count

    async def exists(self, *keys: str) -> int:
        """Check if keys exist."""
        return sum(1 for key in keys if key in self._data)

    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        if pattern == "*":
            return list(self._data.keys())
        # Simple pattern matching (just prefix)
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return [k for k in self._data.keys() if k.startswith(prefix)]
        return [k for k in self._data.keys() if k == pattern]

    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get hash field."""
        hash_data = self._data.get(name, {})
        return hash_data.get(key)

    async def hset(self, name: str, key: str = None, value: Any = None, mapping: Dict = None) -> int:
        """Set hash field(s)."""
        if name not in self._data:
            self._data[name] = {}
        if mapping:
            self._data[name].update(mapping)
            return len(mapping)
        if key is not None:
            self._data[name][key] = value
            return 1
        return 0

    async def hgetall(self, name: str) -> Dict[str, str]:
        """Get all hash fields."""
        return self._data.get(name, {})

    async def publish(self, channel: str, message: str) -> int:
        """Publish a message to a channel."""
        count = 0
        for pubsub in self._pubsub_channels.get(channel, []):
            await pubsub._message_queue.put({
                "type": "message",
                "channel": channel,
                "data": message,
            })
            count += 1
        return count

    def pubsub(self) -> MockPubSub:
        """Create a PubSub instance."""
        ps = MockPubSub(self)
        return ps

    async def close(self) -> None:
        """Close the connection."""
        self._closed = False

    def is_closed(self) -> bool:
        """Check if connection is closed."""
        return self._closed

    def clear(self) -> None:
        """Clear all data (for testing)."""
        self._data.clear()
        self._pubsub_channels.clear()

    @classmethod
    async def from_url(cls, url: str, **kwargs) -> "MockRedis":
        """Create from URL (for compatibility)."""
        return cls()

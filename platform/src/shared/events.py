"""
Event System with Redis Streams

Provides publish-subscribe event system for inter-service communication
using Redis Streams.
"""

import logging
import asyncio
import json
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, asdict
from datetime import datetime
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Event data structure."""
    type: str
    source: str
    data: Dict[str, Any]
    timestamp: str
    event_id: Optional[str] = None
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create event from dictionary."""
        return cls(**data)


class EventBus:
    """
    Event bus using Redis Streams.

    Features:
    - Publish events to streams
    - Subscribe to event streams
    - Consumer groups for load balancing
    - Event persistence and replay
    - At-least-once delivery

    Example:
        bus = EventBus("redis://localhost:6379")

        # Publish event
        await bus.publish("task.created", {
            "task_id": "123",
            "title": "Process data",
        }, source="l01-data-layer")

        # Subscribe to events
        async def handle_task_created(event: Event):
            print(f"Task created: {event.data['task_id']}")

        await bus.subscribe("task.created", handle_task_created)
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        stream_prefix: str = "events:",
    ):
        """
        Initialize event bus.

        Args:
            redis_url: Redis connection URL
            stream_prefix: Prefix for event stream keys
        """
        self.redis_url = redis_url
        self.stream_prefix = stream_prefix
        self._redis: Optional[aioredis.Redis] = None
        self._consumer_tasks: List[asyncio.Task] = []

    async def connect(self):
        """Connect to Redis."""
        if not self._redis:
            self._redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            logger.info(
                "Connected to Redis for event bus",
                extra={'event': 'eventbus_connected'}
            )

    async def disconnect(self):
        """Disconnect from Redis."""
        # Cancel all consumer tasks
        for task in self._consumer_tasks:
            task.cancel()
        await asyncio.gather(*self._consumer_tasks, return_exceptions=True)

        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info(
                "Disconnected from Redis",
                extra={'event': 'eventbus_disconnected'}
            )

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    def _make_stream_key(self, event_type: str) -> str:
        """Generate stream key for event type."""
        return f"{self.stream_prefix}{event_type}"

    async def publish(
        self,
        event_type: str,
        data: Dict[str, Any],
        source: str,
        correlation_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> str:
        """
        Publish event to stream.

        Args:
            event_type: Event type (e.g., "task.created", "user.registered")
            data: Event data
            source: Source service name
            correlation_id: Optional correlation ID
            trace_id: Optional trace ID

        Returns:
            Event ID

        Raises:
            Exception: If publish fails
        """
        if not self._redis:
            await self.connect()

        event = Event(
            type=event_type,
            source=source,
            data=data,
            timestamp=datetime.utcnow().isoformat(),
            correlation_id=correlation_id,
            trace_id=trace_id,
        )

        stream_key = self._make_stream_key(event_type)

        # Serialize event data
        event_dict = event.to_dict()
        serialized = {
            "type": event.type,
            "source": event.source,
            "timestamp": event.timestamp,
            "data": json.dumps(event.data),
            "correlation_id": event.correlation_id or "",
            "trace_id": event.trace_id or "",
        }

        # Add to stream
        event_id = await self._redis.xadd(stream_key, serialized)

        logger.info(
            f"Published event: {event_type}",
            extra={
                'event': 'event_published',
                'event_type': event_type,
                'event_id': event_id,
                'source': source,
            }
        )

        return event_id

    async def subscribe(
        self,
        event_type: str,
        handler: Callable[[Event], Any],
        consumer_group: Optional[str] = None,
        consumer_name: Optional[str] = None,
        start_id: str = "$",
    ):
        """
        Subscribe to event stream.

        Args:
            event_type: Event type to subscribe to
            handler: Async function to handle events
            consumer_group: Optional consumer group name
            consumer_name: Optional consumer name
            start_id: Start reading from this ID ($ = new messages)

        Example:
            async def handle_event(event: Event):
                print(f"Received: {event.type}")

            await bus.subscribe("task.*", handle_event,
                              consumer_group="task-workers",
                              consumer_name="worker-1")
        """
        if not self._redis:
            await self.connect()

        stream_key = self._make_stream_key(event_type)

        # Create consumer group if specified
        if consumer_group:
            try:
                await self._redis.xgroup_create(
                    stream_key,
                    consumer_group,
                    id=start_id,
                    mkstream=True,
                )
                logger.info(
                    f"Created consumer group: {consumer_group}",
                    extra={
                        'event': 'consumer_group_created',
                        'group': consumer_group,
                        'stream': stream_key,
                    }
                )
            except aioredis.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise

        # Start consumer task
        task = asyncio.create_task(
            self._consume_stream(
                stream_key,
                handler,
                consumer_group,
                consumer_name,
            )
        )
        self._consumer_tasks.append(task)

        logger.info(
            f"Subscribed to {event_type}",
            extra={
                'event': 'subscribed',
                'event_type': event_type,
                'consumer_group': consumer_group,
                'consumer_name': consumer_name,
            }
        )

    async def _consume_stream(
        self,
        stream_key: str,
        handler: Callable[[Event], Any],
        consumer_group: Optional[str] = None,
        consumer_name: Optional[str] = None,
    ):
        """Internal method to consume events from stream."""
        last_id = "0-0"
        read_count = 10

        while True:
            try:
                if consumer_group and consumer_name:
                    # Read as consumer group
                    messages = await self._redis.xreadgroup(
                        consumer_group,
                        consumer_name,
                        {stream_key: ">"},
                        count=read_count,
                        block=5000,
                    )
                else:
                    # Read without consumer group
                    messages = await self._redis.xread(
                        {stream_key: last_id},
                        count=read_count,
                        block=5000,
                    )

                if not messages:
                    continue

                for stream, event_list in messages:
                    for event_id, event_data in event_list:
                        try:
                            # Parse event
                            event = self._parse_event(event_data)
                            event.event_id = event_id

                            # Call handler
                            if asyncio.iscoroutinefunction(handler):
                                await handler(event)
                            else:
                                handler(event)

                            # Acknowledge message if using consumer group
                            if consumer_group:
                                await self._redis.xack(stream_key, consumer_group, event_id)

                            logger.debug(
                                f"Processed event: {event.type}",
                                extra={
                                    'event': 'event_processed',
                                    'event_type': event.type,
                                    'event_id': event_id,
                                }
                            )

                        except Exception as e:
                            logger.error(
                                f"Error processing event: {e}",
                                extra={
                                    'event': 'event_processing_error',
                                    'event_id': event_id,
                                    'error': str(e),
                                },
                                exc_info=True,
                            )

                        # Update last ID for non-group consumers
                        if not consumer_group:
                            last_id = event_id

            except asyncio.CancelledError:
                logger.info("Consumer task cancelled")
                break
            except Exception as e:
                logger.error(
                    f"Error in consumer: {e}",
                    extra={
                        'event': 'consumer_error',
                        'error': str(e),
                    },
                    exc_info=True,
                )
                await asyncio.sleep(5)

    def _parse_event(self, event_data: Dict[str, str]) -> Event:
        """Parse event from Redis stream data."""
        return Event(
            type=event_data.get("type", ""),
            source=event_data.get("source", ""),
            data=json.loads(event_data.get("data", "{}")),
            timestamp=event_data.get("timestamp", ""),
            correlation_id=event_data.get("correlation_id") or None,
            trace_id=event_data.get("trace_id") or None,
        )

    async def get_pending_events(
        self,
        event_type: str,
        consumer_group: str,
    ) -> List[Event]:
        """
        Get pending events for a consumer group.

        Args:
            event_type: Event type
            consumer_group: Consumer group name

        Returns:
            List of pending events
        """
        if not self._redis:
            await self.connect()

        stream_key = self._make_stream_key(event_type)

        # Get pending entries
        pending = await self._redis.xpending_range(
            stream_key,
            consumer_group,
            min="-",
            max="+",
            count=100,
        )

        events = []
        for entry in pending:
            event_id = entry["message_id"]
            # Fetch actual message
            messages = await self._redis.xrange(stream_key, min=event_id, max=event_id)
            if messages:
                _, event_data = messages[0]
                event = self._parse_event(event_data)
                event.event_id = event_id
                events.append(event)

        return events

    async def delete_stream(self, event_type: str):
        """
        Delete an event stream.

        Args:
            event_type: Event type
        """
        if not self._redis:
            await self.connect()

        stream_key = self._make_stream_key(event_type)
        await self._redis.delete(stream_key)

        logger.info(
            f"Deleted stream: {event_type}",
            extra={
                'event': 'stream_deleted',
                'event_type': event_type,
            }
        )


# Convenience functions

async def publish_event(
    event_type: str,
    data: Dict[str, Any],
    source: str,
    redis_url: str = "redis://localhost:6379",
) -> str:
    """
    Quick function to publish an event.

    Args:
        event_type: Event type
        data: Event data
        source: Source service
        redis_url: Redis URL

    Returns:
        Event ID
    """
    async with EventBus(redis_url) as bus:
        return await bus.publish(event_type, data, source)


# Standard event types
class EventTypes:
    """Standard event types for the platform."""

    # Task events
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"

    # User events
    USER_REGISTERED = "user.registered"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"

    # Data events
    DATA_CREATED = "data.created"
    DATA_UPDATED = "data.updated"
    DATA_DELETED = "data.deleted"

    # Tool events
    TOOL_EXECUTED = "tool.executed"
    TOOL_FAILED = "tool.failed"

    # Model events
    MODEL_REQUEST = "model.request"
    MODEL_RESPONSE = "model.response"
    MODEL_ERROR = "model.error"

    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"

"""
L11 Integration Layer - Event Bus Manager.

Redis Pub/Sub based event bus for async communication between layers.
"""

import asyncio
import logging
from typing import Dict, List, Optional
import json

import redis.asyncio as redis

from ..models import (
    EventMessage,
    EventSubscription,
    EventHandler,
    IntegrationError,
    ErrorCode,
)


logger = logging.getLogger(__name__)


class EventBusManager:
    """
    Event bus manager using Redis Pub/Sub.

    Provides publish-subscribe messaging for loose coupling between layers.
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """
        Initialize event bus manager.

        Args:
            redis_url: Redis connection URL
        """
        self._redis_url = redis_url
        self._redis_client: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
        self._subscriptions: Dict[str, EventSubscription] = {}
        self._running = False
        self._listen_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the event bus and connect to Redis."""
        try:
            self._redis_client = await redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            self._pubsub = self._redis_client.pubsub()
            self._running = True

            # Start listening task
            self._listen_task = asyncio.create_task(self._listen_loop())

            # Give the listen loop time to start
            await asyncio.sleep(0.1)

            logger.info(f"Event bus started (Redis: {self._redis_url})")
        except Exception as e:
            raise IntegrationError.from_code(
                ErrorCode.E11100,
                details={"error": str(e), "redis_url": self._redis_url},
                recovery_suggestion="Ensure Redis is running and accessible",
            )

    async def stop(self) -> None:
        """Stop the event bus and disconnect from Redis."""
        self._running = False
        logger.info("Stopping event bus...")

        # Cancel listen task
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass

        # Unsubscribe from all topics
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.aclose()

        # Close Redis connection
        if self._redis_client:
            await self._redis_client.aclose()

        logger.info("Event bus stopped")

    async def publish(self, event: EventMessage) -> None:
        """
        Publish an event to a topic.

        Args:
            event: EventMessage to publish

        Raises:
            IntegrationError: If publish fails
        """
        if not self._redis_client:
            raise IntegrationError.from_code(
                ErrorCode.E11101,
                details={"reason": "Event bus not started"},
            )

        try:
            # Serialize event to JSON
            event_json = event.to_json()

            # Publish to Redis channel (topic)
            await self._redis_client.publish(event.topic, event_json)

            logger.debug(
                f"Published event: topic={event.topic}, "
                f"type={event.event_type}, "
                f"event_id={event.metadata.event_id}"
            )
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            raise IntegrationError.from_code(
                ErrorCode.E11101,
                details={"topic": event.topic, "error": str(e)},
            )

    async def subscribe(
        self,
        topic: str,
        handler: EventHandler,
        service_name: Optional[str] = None,
    ) -> str:
        """
        Subscribe to an event topic.

        Args:
            topic: Topic to subscribe to (supports wildcards with pattern matching)
            handler: Async function to handle events
            service_name: Name of subscribing service

        Returns:
            Subscription ID

        Raises:
            IntegrationError: If subscription fails
        """
        if not self._pubsub:
            raise IntegrationError.from_code(
                ErrorCode.E11102,
                details={"reason": "Event bus not started"},
            )

        try:
            async with self._lock:
                # Create subscription
                subscription = EventSubscription(
                    topic=topic,
                    handler=handler,
                    service_name=service_name,
                )
                self._subscriptions[subscription.subscription_id] = subscription

                # Subscribe to Redis channel
                # Redis pattern matching: * matches any sequence of characters
                if "*" in topic:
                    await self._pubsub.psubscribe(topic)
                else:
                    await self._pubsub.subscribe(topic)

                logger.info(
                    f"Subscribed to topic: {topic} "
                    f"(subscription_id={subscription.subscription_id}, "
                    f"service={service_name})"
                )

                return subscription.subscription_id

        except Exception as e:
            logger.error(f"Failed to subscribe to topic {topic}: {e}")
            raise IntegrationError.from_code(
                ErrorCode.E11102,
                details={"topic": topic, "error": str(e)},
            )

    async def unsubscribe(self, subscription_id: str) -> None:
        """
        Unsubscribe from a topic.

        Args:
            subscription_id: Subscription ID to cancel

        Raises:
            IntegrationError: If unsubscription fails
        """
        if not self._pubsub:
            raise IntegrationError.from_code(
                ErrorCode.E11103,
                details={"reason": "Event bus not started"},
            )

        async with self._lock:
            if subscription_id not in self._subscriptions:
                raise IntegrationError.from_code(
                    ErrorCode.E11103,
                    details={"subscription_id": subscription_id},
                )

            subscription = self._subscriptions[subscription_id]
            topic = subscription.topic

            # Mark as inactive
            subscription.active = False

            # Remove subscription
            del self._subscriptions[subscription_id]

            # Check if any other subscriptions exist for this topic
            has_other_subs = any(
                s.topic == topic and s.active
                for s in self._subscriptions.values()
            )

            # Unsubscribe from Redis if no other subscriptions
            if not has_other_subs:
                try:
                    if "*" in topic:
                        await self._pubsub.punsubscribe(topic)
                    else:
                        await self._pubsub.unsubscribe(topic)
                except Exception as e:
                    logger.warning(f"Failed to unsubscribe from Redis topic {topic}: {e}")

            logger.info(f"Unsubscribed from topic: {topic} (subscription_id={subscription_id})")

    async def _listen_loop(self) -> None:
        """Listen for events from Redis and dispatch to handlers."""
        if not self._pubsub:
            return

        logger.info("Event bus listening for messages...")

        try:
            while self._running:
                try:
                    # Check if we have any subscriptions
                    async with self._lock:
                        has_subscriptions = len(self._subscriptions) > 0

                    if not has_subscriptions:
                        # No subscriptions yet, wait a bit
                        await asyncio.sleep(0.1)
                        continue

                    # Get message with timeout
                    message = await self._pubsub.get_message(
                        ignore_subscribe_messages=False,
                        timeout=1.0,
                    )

                    if message:
                        logger.debug(f"Received Redis message: type={message.get('type')}, channel={message.get('channel')}, data={message.get('data')}")

                        # Handle actual messages (not subscription confirmations)
                        if message["type"] in ("message", "pmessage"):
                            await self._handle_message(message)

                    # Small sleep to prevent busy loop
                    await asyncio.sleep(0.01)

                except asyncio.TimeoutError:
                    # No message received, continue loop
                    continue
                except RuntimeError as e:
                    # Handle "pubsub connection not set" error
                    if "pubsub connection not set" in str(e):
                        await asyncio.sleep(0.1)
                        continue
                    raise

        except asyncio.CancelledError:
            logger.info("Event bus listen loop cancelled")
        except Exception as e:
            logger.error(f"Error in event bus listen loop: {e}", exc_info=True)

    async def _handle_message(self, message: dict) -> None:
        """
        Handle a message from Redis.

        Args:
            message: Redis message dict
        """
        try:
            # Extract topic and data
            if message["type"] == "message":
                topic = message["channel"]
            else:  # pmessage (pattern match)
                topic = message["channel"]

            data = message["data"]

            logger.debug(f"Handling message: topic={topic}, data_len={len(data) if data else 0}")

            # Deserialize event
            event = EventMessage.from_json(data)

            # Find matching subscriptions
            async with self._lock:
                matching_subs = [
                    sub for sub in self._subscriptions.values()
                    if sub.active and sub.matches_topic(topic)
                ]

            logger.debug(f"Found {len(matching_subs)} matching subscriptions for topic {topic}")

            # Dispatch to handlers
            for subscription in matching_subs:
                if subscription.handler:
                    logger.debug(f"Dispatching to handler for subscription {subscription.subscription_id}")
                    asyncio.create_task(self._invoke_handler(subscription, event))

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)

    async def _invoke_handler(
        self,
        subscription: EventSubscription,
        event: EventMessage,
    ) -> None:
        """
        Invoke event handler with error handling and retries.

        Args:
            subscription: EventSubscription
            event: EventMessage to handle
        """
        try:
            if subscription.handler:
                await subscription.handler(event)

                logger.debug(
                    f"Event handled: topic={event.topic}, "
                    f"event_id={event.metadata.event_id}, "
                    f"subscription_id={subscription.subscription_id}"
                )

        except Exception as e:
            logger.error(
                f"Event handler error: topic={event.topic}, "
                f"event_id={event.metadata.event_id}, "
                f"error={e}"
            )

            # Retry logic
            if event.can_retry():
                event.increment_retry()
                logger.info(f"Retrying event {event.metadata.event_id} (attempt {event.metadata.retry_count})")
                # Re-publish for retry
                await self.publish(event)
            else:
                logger.error(f"Event {event.metadata.event_id} exhausted retries, moving to DLQ")
                # Could implement DLQ here (dead letter queue)
                await self._send_to_dlq(event, str(e))

    async def _send_to_dlq(self, event: EventMessage, error: str) -> None:
        """
        Send failed event to dead letter queue.

        Args:
            event: Failed event
            error: Error message
        """
        if not self._redis_client:
            return

        try:
            dlq_key = f"dlq:{event.topic}"
            dlq_entry = {
                "event": event.to_json(),
                "error": error,
                "failed_at": asyncio.get_event_loop().time(),
            }
            await self._redis_client.lpush(dlq_key, json.dumps(dlq_entry))
            logger.info(f"Sent event {event.metadata.event_id} to DLQ: {dlq_key}")
        except Exception as e:
            logger.error(f"Failed to send event to DLQ: {e}")

    async def get_subscriptions(self) -> List[EventSubscription]:
        """
        Get all active subscriptions.

        Returns:
            List of EventSubscription
        """
        async with self._lock:
            return [s for s in self._subscriptions.values() if s.active]

    async def get_dlq_size(self, topic: str) -> int:
        """
        Get size of dead letter queue for a topic.

        Args:
            topic: Event topic

        Returns:
            Number of messages in DLQ
        """
        if not self._redis_client:
            return 0

        try:
            dlq_key = f"dlq:{topic}"
            return await self._redis_client.llen(dlq_key)
        except Exception:
            return 0

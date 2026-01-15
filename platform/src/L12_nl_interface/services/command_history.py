"""Command History for L12 Natural Language Interface.

This module implements the CommandHistory class for tracking command
history per session. It stores commands in Redis for durability and
supports command replay.

Key features:
- Per-session command history tracking
- Redis persistence for durability
- Limited history size (default: 100 commands)
- Command replay capability
- Sensitive data sanitization
- Automatic cleanup on session expiry

Example:
    >>> history = CommandHistory(redis_host="localhost")
    >>> await history.connect()
    >>> await history.add_command(
    ...     session_id="session-123",
    ...     service_name="PlanningService",
    ...     method_name="create_plan",
    ...     parameters={"goal": "test"},
    ...     status="success"
    ... )
    >>> commands = await history.get_history("session-123", limit=10)
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)


@dataclass
class CommandRecord:
    """Record of a command execution.

    Attributes:
        session_id: Session identifier
        service_name: Service name
        method_name: Method name
        parameters: Sanitized method parameters
        status: Command status ("success" or "error")
        execution_time_ms: Execution time in milliseconds
        timestamp: Command timestamp
        result_preview: Brief preview of result (first 100 chars)
    """

    session_id: str
    service_name: str
    method_name: str
    parameters: Dict[str, Any]
    status: str
    execution_time_ms: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    result_preview: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        return {
            "session_id": self.session_id,
            "service_name": self.service_name,
            "method_name": self.method_name,
            "parameters": self.parameters,
            "status": self.status,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp.isoformat(),
            "result_preview": self.result_preview,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CommandRecord":
        """Create CommandRecord from dictionary.

        Args:
            data: Dictionary with command data

        Returns:
            CommandRecord instance
        """
        # Parse timestamp
        if isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])

        return cls(**data)


class CommandHistory:
    """Command history tracker for L12 sessions.

    The CommandHistory class tracks all commands executed in each L12
    session and stores them in Redis for durability. It supports querying
    recent commands and replaying command sequences.

    Attributes:
        redis_host: Redis server host
        redis_port: Redis server port
        redis_db: Redis database number
        max_history_size: Maximum commands per session
        enabled: Whether history tracking is enabled

    Example:
        >>> history = CommandHistory(redis_host="localhost")
        >>> await history.connect()
        >>> await history.add_command(...)
        >>> commands = await history.get_history("session-123")
        >>> await history.disconnect()
    """

    # Sensitive parameter names to sanitize
    SENSITIVE_PARAMS = {
        "password",
        "token",
        "api_key",
        "secret",
        "credentials",
        "auth",
        "private_key",
        "certificate",
    }

    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        max_history_size: int = 100,
        enabled: bool = True,
    ):
        """Initialize command history tracker.

        Args:
            redis_host: Redis server host
            redis_port: Redis server port
            redis_db: Redis database number
            max_history_size: Maximum commands per session (default: 100)
            enabled: Whether history tracking is enabled
        """
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db
        self.max_history_size = max_history_size
        self.enabled = enabled

        # Redis client
        self.client: Optional[redis.Redis] = None

        logger.info(
            f"CommandHistory initialized: redis={redis_host}:{redis_port}, "
            f"max_size={max_history_size}, enabled={enabled}"
        )

    async def connect(self):
        """Connect to Redis."""
        if not self.enabled:
            logger.info("CommandHistory disabled, skipping connect")
            return

        try:
            self.client = await redis.from_url(
                f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}",
                encoding="utf-8",
                decode_responses=True,
            )
            await self.client.ping()
            logger.info("CommandHistory connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            # Don't raise - gracefully degrade if Redis unavailable
            self.enabled = False

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.client:
            await self.client.close()
            self.client = None
            logger.info("CommandHistory disconnected from Redis")

    async def add_command(
        self,
        session_id: str,
        service_name: str,
        method_name: str,
        parameters: Dict[str, Any],
        status: str,
        execution_time_ms: float,
        result: Any = None,
    ):
        """Add command to history.

        Args:
            session_id: Session identifier
            service_name: Service name
            method_name: Method name
            parameters: Method parameters (will be sanitized)
            status: Command status ("success" or "error")
            execution_time_ms: Execution time in milliseconds
            result: Command result (optional, for preview)

        Example:
            >>> await history.add_command(
            ...     session_id="session-123",
            ...     service_name="PlanningService",
            ...     method_name="create_plan",
            ...     parameters={"goal": "test"},
            ...     status="success",
            ...     execution_time_ms=123.45
            ... )
        """
        if not self.enabled or not self.client:
            return

        # Sanitize parameters
        sanitized_params = self._sanitize_parameters(parameters)

        # Create result preview
        result_preview = None
        if result is not None:
            result_str = str(result)
            result_preview = (
                result_str[:100] + "..." if len(result_str) > 100 else result_str
            )

        # Create command record
        record = CommandRecord(
            session_id=session_id,
            service_name=service_name,
            method_name=method_name,
            parameters=sanitized_params,
            status=status,
            execution_time_ms=execution_time_ms,
            result_preview=result_preview,
        )

        try:
            # Store in Redis list (most recent first)
            key = self._get_session_key(session_id)
            await self.client.lpush(key, json.dumps(record.to_dict()))

            # Trim to max size
            await self.client.ltrim(key, 0, self.max_history_size - 1)

            # Set expiry (1 hour)
            await self.client.expire(key, 3600)

            logger.debug(
                f"Added command to history: {session_id} - {service_name}.{method_name}"
            )
        except Exception as e:
            logger.warning(f"Failed to add command to history: {e}")
            # Don't raise - history is not critical

    async def get_history(
        self, session_id: str, limit: int = 10
    ) -> List[CommandRecord]:
        """Get command history for session.

        Args:
            session_id: Session identifier
            limit: Maximum number of commands to return

        Returns:
            List of CommandRecord objects (most recent first)

        Example:
            >>> commands = await history.get_history("session-123", limit=10)
            >>> for cmd in commands:
            ...     print(f"{cmd.service_name}.{cmd.method_name}")
        """
        if not self.enabled or not self.client:
            return []

        try:
            key = self._get_session_key(session_id)
            # Get most recent N commands
            items = await self.client.lrange(key, 0, limit - 1)

            # Parse JSON records
            records = []
            for item in items:
                try:
                    data = json.loads(item)
                    records.append(CommandRecord.from_dict(data))
                except Exception as e:
                    logger.warning(f"Failed to parse command record: {e}")
                    continue

            return records
        except Exception as e:
            logger.warning(f"Failed to get command history: {e}")
            return []

    async def get_recent_command(
        self, session_id: str
    ) -> Optional[CommandRecord]:
        """Get most recent command for session.

        Args:
            session_id: Session identifier

        Returns:
            Most recent CommandRecord, or None

        Example:
            >>> last_cmd = await history.get_recent_command("session-123")
            >>> if last_cmd:
            ...     print(f"Last: {last_cmd.service_name}.{last_cmd.method_name}")
        """
        history = await self.get_history(session_id, limit=1)
        return history[0] if history else None

    async def replay_command(
        self, session_id: str, index: int = 0
    ) -> Optional[Dict[str, Any]]:
        """Get command for replay.

        Args:
            session_id: Session identifier
            index: Command index (0 = most recent, 1 = second most recent, etc.)

        Returns:
            Dictionary with service_name, method_name, parameters, or None

        Example:
            >>> cmd = await history.replay_command("session-123", index=0)
            >>> if cmd:
            ...     # Re-execute the command
            ...     await router.route_request(InvokeRequest(**cmd))
        """
        history = await self.get_history(session_id, limit=index + 1)
        if len(history) <= index:
            return None

        record = history[index]
        return {
            "service_name": record.service_name,
            "method_name": record.method_name,
            "parameters": record.parameters,
            "session_id": session_id,
        }

    async def clear_history(self, session_id: str):
        """Clear command history for session.

        Args:
            session_id: Session identifier

        Example:
            >>> await history.clear_history("session-123")
        """
        if not self.enabled or not self.client:
            return

        try:
            key = self._get_session_key(session_id)
            await self.client.delete(key)
            logger.info(f"Cleared command history for session {session_id}")
        except Exception as e:
            logger.warning(f"Failed to clear command history: {e}")

    async def get_statistics(self, session_id: str) -> Dict[str, Any]:
        """Get command history statistics for session.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary with statistics

        Example:
            >>> stats = await history.get_statistics("session-123")
            >>> print(f"Total commands: {stats['total_commands']}")
        """
        if not self.enabled or not self.client:
            return {
                "total_commands": 0,
                "successful_commands": 0,
                "failed_commands": 0,
                "services_used": [],
                "methods_used": [],
            }

        history = await self.get_history(session_id, limit=self.max_history_size)

        services_used = set()
        methods_used = set()
        successful = 0
        failed = 0

        for record in history:
            services_used.add(record.service_name)
            methods_used.add(record.method_name)
            if record.status == "success":
                successful += 1
            else:
                failed += 1

        return {
            "total_commands": len(history),
            "successful_commands": successful,
            "failed_commands": failed,
            "services_used": list(services_used),
            "methods_used": list(methods_used),
        }

    def _get_session_key(self, session_id: str) -> str:
        """Get Redis key for session history.

        Args:
            session_id: Session identifier

        Returns:
            Redis key
        """
        return f"l12:history:{session_id}"

    def _sanitize_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize parameters to remove sensitive data.

        Args:
            parameters: Original parameters

        Returns:
            Sanitized parameters
        """
        sanitized = {}
        for key, value in parameters.items():
            # Check if key contains sensitive terms
            if any(sensitive in key.lower() for sensitive in self.SENSITIVE_PARAMS):
                sanitized[key] = "<REDACTED>"
            else:
                # Recursively sanitize nested dicts
                if isinstance(value, dict):
                    sanitized[key] = self._sanitize_parameters(value)
                else:
                    sanitized[key] = value

        return sanitized

"""
Task Manager Service

Manages async tool execution tasks with Redis persistence.
Implements MCP Tasks pattern for long-running operations.

Features:
- Task creation and tracking
- Progress updates
- Task cancellation
- Redis persistence for crash recovery
"""

import asyncio
import logging
import json
from typing import Optional, Dict, Any, List, Coroutine
from datetime import datetime, timezone
from uuid import UUID, uuid4
from dataclasses import dataclass, field, asdict
from enum import Enum

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class TaskState(Enum):
    """Task execution state."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class Task:
    """
    Async task representation.

    Stored in Redis for persistence across service restarts.
    """
    task_id: str
    tool_id: str
    invocation_id: UUID
    status: str = TaskState.PENDING.value
    progress_percent: Optional[int] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage."""
        return {
            "task_id": self.task_id,
            "tool_id": self.tool_id,
            "invocation_id": str(self.invocation_id),
            "status": self.status,
            "progress_percent": self.progress_percent,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create Task from dictionary."""
        return cls(
            task_id=data["task_id"],
            tool_id=data["tool_id"],
            invocation_id=UUID(data["invocation_id"]),
            status=data["status"],
            progress_percent=data.get("progress_percent"),
            result=data.get("result"),
            error=data.get("error"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
        )


class TaskManager:
    """
    Manages async tool execution tasks.

    Uses Redis for task state persistence and asyncio for task execution.
    """

    # Redis key prefixes
    TASK_KEY_PREFIX = "l03:task:"
    TASK_SET_KEY = "l03:tasks"

    # Task TTL in seconds (1 hour after completion)
    TASK_TTL = 3600

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        max_concurrent_tasks: int = 10,
    ):
        """
        Initialize Task Manager.

        Args:
            redis_url: Redis connection URL
            max_concurrent_tasks: Maximum concurrent tasks
        """
        self.redis_url = redis_url
        self.max_concurrent_tasks = max_concurrent_tasks
        self.redis: Optional[redis.Redis] = None

        # In-memory task tracking for cancellation
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._semaphore: Optional[asyncio.Semaphore] = None

    async def initialize(self):
        """Initialize Redis connection and semaphore."""
        try:
            self.redis = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await self.redis.ping()
            self._semaphore = asyncio.Semaphore(self.max_concurrent_tasks)
            logger.info(f"Task Manager initialized (max_concurrent={self.max_concurrent_tasks})")
        except Exception as e:
            logger.error(f"Failed to initialize Task Manager: {e}")
            raise

    async def close(self):
        """Close Redis connection and cancel running tasks."""
        # Cancel all running tasks
        for task_id, asyncio_task in list(self._running_tasks.items()):
            if not asyncio_task.done():
                asyncio_task.cancel()
                try:
                    await asyncio_task
                except asyncio.CancelledError:
                    pass
                await self._update_task_status(task_id, TaskState.CANCELLED.value)

        if self.redis:
            await self.redis.close()
            logger.info("Task Manager closed")

    async def create_task(
        self,
        task_id: str,
        tool_id: str,
        invocation_id: UUID,
        coroutine: Coroutine,
    ) -> Task:
        """
        Create and start an async task.

        Args:
            task_id: Unique task identifier
            tool_id: Tool being executed
            invocation_id: Original invocation ID
            coroutine: Async coroutine to execute

        Returns:
            Created Task object
        """
        # Create task record
        task = Task(
            task_id=task_id,
            tool_id=tool_id,
            invocation_id=invocation_id,
            status=TaskState.PENDING.value,
        )

        # Save to Redis
        await self._save_task(task)

        # Start execution
        asyncio_task = asyncio.create_task(
            self._execute_task(task_id, coroutine)
        )
        self._running_tasks[task_id] = asyncio_task

        logger.info(f"Created task {task_id} for tool {tool_id}")
        return task

    async def _execute_task(self, task_id: str, coroutine: Coroutine):
        """Execute task with state management."""
        async with self._semaphore:
            try:
                # Update to running
                await self._update_task_status(task_id, TaskState.RUNNING.value)

                # Execute the coroutine
                result = await coroutine

                # Extract result from ToolInvokeResponse if needed
                result_data = None
                if hasattr(result, "result") and result.result:
                    result_data = result.result.to_dict() if hasattr(result.result, "to_dict") else {"result": result.result}
                elif hasattr(result, "to_dict"):
                    result_data = result.to_dict()
                else:
                    result_data = {"result": result}

                # Check for error in response
                if hasattr(result, "error") and result.error:
                    await self._update_task_status(
                        task_id,
                        TaskState.ERROR.value,
                        error=result.error.to_dict() if hasattr(result.error, "to_dict") else {"message": str(result.error)},
                    )
                else:
                    await self._update_task_status(
                        task_id,
                        TaskState.SUCCESS.value,
                        result=result_data,
                    )

            except asyncio.CancelledError:
                await self._update_task_status(task_id, TaskState.CANCELLED.value)
                raise

            except asyncio.TimeoutError:
                await self._update_task_status(
                    task_id,
                    TaskState.TIMEOUT.value,
                    error={"code": "E3103", "message": "Task execution timeout"},
                )

            except Exception as e:
                logger.error(f"Task {task_id} failed: {e}", exc_info=True)
                await self._update_task_status(
                    task_id,
                    TaskState.ERROR.value,
                    error={"code": "E3108", "message": str(e)},
                )

            finally:
                # Remove from running tasks
                self._running_tasks.pop(task_id, None)

    async def _save_task(self, task: Task):
        """Save task to Redis."""
        key = f"{self.TASK_KEY_PREFIX}{task.task_id}"
        await self.redis.set(key, json.dumps(task.to_dict()))
        await self.redis.sadd(self.TASK_SET_KEY, task.task_id)

    async def _update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[Dict[str, Any]] = None,
        progress_percent: Optional[int] = None,
    ):
        """Update task status in Redis."""
        task = await self.get_task(task_id)
        if not task:
            return

        task.status = status
        task.updated_at = datetime.now(timezone.utc)

        if result is not None:
            task.result = result
        if error is not None:
            task.error = error
        if progress_percent is not None:
            task.progress_percent = progress_percent

        # Set completed_at for terminal states
        if status in (TaskState.SUCCESS.value, TaskState.ERROR.value,
                      TaskState.CANCELLED.value, TaskState.TIMEOUT.value):
            task.completed_at = datetime.now(timezone.utc)
            task.progress_percent = 100 if status == TaskState.SUCCESS.value else task.progress_percent

        await self._save_task(task)

        # Set TTL for completed tasks
        if task.completed_at:
            key = f"{self.TASK_KEY_PREFIX}{task_id}"
            await self.redis.expire(key, self.TASK_TTL)

    async def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get task by ID.

        Args:
            task_id: Task identifier

        Returns:
            Task or None if not found
        """
        key = f"{self.TASK_KEY_PREFIX}{task_id}"
        data = await self.redis.get(key)
        if not data:
            return None
        return Task.from_dict(json.loads(data))

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task.

        Args:
            task_id: Task to cancel

        Returns:
            True if cancellation was initiated
        """
        # Check if task is running in-memory
        asyncio_task = self._running_tasks.get(task_id)
        if asyncio_task and not asyncio_task.done():
            asyncio_task.cancel()
            logger.info(f"Cancelled task {task_id}")
            return True

        # Update Redis state directly for tasks not running locally
        task = await self.get_task(task_id)
        if task and task.status in (TaskState.PENDING.value, TaskState.RUNNING.value):
            await self._update_task_status(task_id, TaskState.CANCELLED.value)
            return True

        return False

    async def update_progress(self, task_id: str, progress_percent: int):
        """
        Update task progress.

        Args:
            task_id: Task identifier
            progress_percent: Progress percentage (0-100)
        """
        await self._update_task_status(
            task_id,
            TaskState.RUNNING.value,
            progress_percent=min(100, max(0, progress_percent)),
        )

    async def list_tasks(
        self,
        status: Optional[str] = None,
        tool_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Task]:
        """
        List tasks with optional filters.

        Args:
            status: Filter by status
            tool_id: Filter by tool_id
            limit: Maximum results

        Returns:
            List of tasks
        """
        task_ids = await self.redis.smembers(self.TASK_SET_KEY)
        tasks = []

        for task_id in task_ids:
            if len(tasks) >= limit:
                break

            task = await self.get_task(task_id)
            if not task:
                # Remove stale reference
                await self.redis.srem(self.TASK_SET_KEY, task_id)
                continue

            # Apply filters
            if status and task.status != status:
                continue
            if tool_id and task.tool_id != tool_id:
                continue

            tasks.append(task)

        # Sort by created_at descending
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks[:limit]

    async def cleanup_completed_tasks(self, max_age_hours: int = 24):
        """
        Remove completed tasks older than max_age.

        Args:
            max_age_hours: Maximum age in hours for completed tasks
        """
        cutoff = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
        task_ids = await self.redis.smembers(self.TASK_SET_KEY)
        removed = 0

        for task_id in task_ids:
            task = await self.get_task(task_id)
            if not task:
                await self.redis.srem(self.TASK_SET_KEY, task_id)
                continue

            if task.completed_at and task.completed_at.timestamp() < cutoff:
                key = f"{self.TASK_KEY_PREFIX}{task_id}"
                await self.redis.delete(key)
                await self.redis.srem(self.TASK_SET_KEY, task_id)
                removed += 1

        if removed > 0:
            logger.info(f"Cleaned up {removed} completed tasks")

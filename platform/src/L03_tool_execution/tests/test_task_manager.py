"""
Task Manager Unit Tests

Tests for async task management with mocked Redis.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from uuid import uuid4

from ..services.task_manager import TaskManager, Task, TaskState


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    redis = AsyncMock()
    redis.ping = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    redis.sadd = AsyncMock()
    redis.srem = AsyncMock()
    redis.smembers = AsyncMock(return_value=set())
    redis.expire = AsyncMock()
    redis.delete = AsyncMock()
    redis.close = AsyncMock()
    return redis


@pytest.fixture
def task_manager(mock_redis):
    """Create TaskManager with mocked Redis."""
    manager = TaskManager(redis_url="redis://localhost:6379/0")
    manager.redis = mock_redis
    manager._semaphore = asyncio.Semaphore(10)
    return manager


class TestTask:
    """Tests for Task dataclass."""

    def test_task_creation(self):
        """Test creating a Task."""
        invocation_id = uuid4()
        task = Task(
            task_id="task:test:abc",
            tool_id="my-tool",
            invocation_id=invocation_id,
        )
        assert task.task_id == "task:test:abc"
        assert task.tool_id == "my-tool"
        assert task.status == TaskState.PENDING.value
        assert task.progress_percent is None

    def test_task_to_dict(self):
        """Test Task serialization."""
        invocation_id = uuid4()
        task = Task(
            task_id="task:test:abc",
            tool_id="my-tool",
            invocation_id=invocation_id,
            status=TaskState.RUNNING.value,
            progress_percent=50,
        )
        data = task.to_dict()
        assert data["task_id"] == "task:test:abc"
        assert data["status"] == "running"
        assert data["progress_percent"] == 50
        assert data["invocation_id"] == str(invocation_id)

    def test_task_from_dict(self):
        """Test Task deserialization."""
        invocation_id = uuid4()
        data = {
            "task_id": "task:test:xyz",
            "tool_id": "other-tool",
            "invocation_id": str(invocation_id),
            "status": "success",
            "progress_percent": 100,
            "result": {"output": "done"},
            "error": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        task = Task.from_dict(data)
        assert task.task_id == "task:test:xyz"
        assert task.status == "success"
        assert task.result == {"output": "done"}
        assert task.completed_at is not None


class TestTaskManager:
    """Tests for TaskManager."""

    @pytest.mark.asyncio
    async def test_create_task(self, task_manager, mock_redis):
        """Test creating a new task."""
        invocation_id = uuid4()

        # Create a simple coroutine that returns a result
        async def test_coroutine():
            return MagicMock(result=MagicMock(to_dict=lambda: {"output": "success"}), error=None)

        task = await task_manager.create_task(
            task_id="task:test:new",
            tool_id="test-tool",
            invocation_id=invocation_id,
            coroutine=test_coroutine(),
        )

        assert task.task_id == "task:test:new"
        assert task.tool_id == "test-tool"
        assert task.status == TaskState.PENDING.value
        mock_redis.set.assert_called()
        mock_redis.sadd.assert_called_with("l03:tasks", "task:test:new")

    @pytest.mark.asyncio
    async def test_get_task(self, task_manager, mock_redis):
        """Test retrieving a task."""
        invocation_id = uuid4()
        task_data = {
            "task_id": "task:test:get",
            "tool_id": "my-tool",
            "invocation_id": str(invocation_id),
            "status": "running",
            "progress_percent": 30,
            "result": None,
            "error": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
        }
        mock_redis.get.return_value = json.dumps(task_data)

        task = await task_manager.get_task("task:test:get")

        assert task is not None
        assert task.task_id == "task:test:get"
        assert task.status == "running"
        assert task.progress_percent == 30

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, task_manager, mock_redis):
        """Test retrieving non-existent task."""
        mock_redis.get.return_value = None

        task = await task_manager.get_task("nonexistent")

        assert task is None

    @pytest.mark.asyncio
    async def test_update_progress(self, task_manager, mock_redis):
        """Test updating task progress."""
        invocation_id = uuid4()
        task_data = {
            "task_id": "task:test:progress",
            "tool_id": "my-tool",
            "invocation_id": str(invocation_id),
            "status": "running",
            "progress_percent": 0,
            "result": None,
            "error": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
        }
        mock_redis.get.return_value = json.dumps(task_data)

        await task_manager.update_progress("task:test:progress", 75)

        # Verify set was called with updated data
        assert mock_redis.set.called

    @pytest.mark.asyncio
    async def test_cancel_task_running(self, task_manager, mock_redis):
        """Test cancelling a running task."""
        # Create a long-running coroutine
        async def long_running():
            await asyncio.sleep(10)
            return MagicMock()

        invocation_id = uuid4()
        task_data = {
            "task_id": "task:test:cancel",
            "tool_id": "my-tool",
            "invocation_id": str(invocation_id),
            "status": "running",
            "progress_percent": 0,
            "result": None,
            "error": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
        }
        mock_redis.get.return_value = json.dumps(task_data)

        # Add to running tasks
        asyncio_task = asyncio.create_task(long_running())
        task_manager._running_tasks["task:test:cancel"] = asyncio_task

        # Cancel
        result = await task_manager.cancel_task("task:test:cancel")

        assert result is True

        # Wait for the cancellation to complete
        try:
            await asyncio_task
        except asyncio.CancelledError:
            pass

        assert asyncio_task.cancelled()

    @pytest.mark.asyncio
    async def test_cancel_task_not_running(self, task_manager, mock_redis):
        """Test cancelling a pending task in Redis."""
        invocation_id = uuid4()
        task_data = {
            "task_id": "task:test:cancel-pending",
            "tool_id": "my-tool",
            "invocation_id": str(invocation_id),
            "status": "pending",
            "progress_percent": None,
            "result": None,
            "error": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
        }
        mock_redis.get.return_value = json.dumps(task_data)

        result = await task_manager.cancel_task("task:test:cancel-pending")

        assert result is True
        assert mock_redis.set.called

    @pytest.mark.asyncio
    async def test_list_tasks(self, task_manager, mock_redis):
        """Test listing tasks."""
        invocation_id = uuid4()

        # Setup mock data
        task_data_1 = {
            "task_id": "task:test:1",
            "tool_id": "tool-a",
            "invocation_id": str(invocation_id),
            "status": "running",
            "progress_percent": 50,
            "result": None,
            "error": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
        }
        task_data_2 = {
            "task_id": "task:test:2",
            "tool_id": "tool-b",
            "invocation_id": str(uuid4()),
            "status": "success",
            "progress_percent": 100,
            "result": {"output": "done"},
            "error": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        mock_redis.smembers.return_value = {"task:test:1", "task:test:2"}
        mock_redis.get.side_effect = [
            json.dumps(task_data_1),
            json.dumps(task_data_2),
        ]

        tasks = await task_manager.list_tasks()

        assert len(tasks) == 2

    @pytest.mark.asyncio
    async def test_list_tasks_with_filter(self, task_manager, mock_redis):
        """Test listing tasks with status filter."""
        invocation_id = uuid4()

        task_data = {
            "task_id": "task:test:1",
            "tool_id": "tool-a",
            "invocation_id": str(invocation_id),
            "status": "running",
            "progress_percent": 50,
            "result": None,
            "error": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
        }

        mock_redis.smembers.return_value = {"task:test:1"}
        mock_redis.get.return_value = json.dumps(task_data)

        # Filter for "success" should exclude this running task
        tasks = await task_manager.list_tasks(status="success")

        assert len(tasks) == 0


class TestTaskExecution:
    """Tests for task execution flow."""

    @pytest.mark.asyncio
    async def test_task_execution_success(self, task_manager, mock_redis):
        """Test successful task execution."""
        invocation_id = uuid4()

        # Track status updates
        status_updates = []

        async def track_set(*args, **kwargs):
            data = json.loads(args[1]) if len(args) > 1 else None
            if data:
                status_updates.append(data.get("status"))

        mock_redis.set.side_effect = track_set

        # Initial task data for get_task calls during status updates
        task_data = {
            "task_id": "task:test:exec",
            "tool_id": "my-tool",
            "invocation_id": str(invocation_id),
            "status": "pending",
            "progress_percent": None,
            "result": None,
            "error": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
        }
        mock_redis.get.return_value = json.dumps(task_data)

        # Create a successful coroutine
        async def success_coroutine():
            await asyncio.sleep(0.01)
            result = MagicMock()
            result.result = MagicMock(to_dict=lambda: {"output": "success"})
            result.error = None
            return result

        task = await task_manager.create_task(
            task_id="task:test:exec",
            tool_id="my-tool",
            invocation_id=invocation_id,
            coroutine=success_coroutine(),
        )

        # Wait for task to complete
        await asyncio.sleep(0.1)

        # Verify status progression
        assert "pending" in status_updates
        assert "running" in status_updates
        assert "success" in status_updates

    @pytest.mark.asyncio
    async def test_task_execution_error(self, task_manager, mock_redis):
        """Test task execution with error."""
        invocation_id = uuid4()

        task_data = {
            "task_id": "task:test:error",
            "tool_id": "my-tool",
            "invocation_id": str(invocation_id),
            "status": "pending",
            "progress_percent": None,
            "result": None,
            "error": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
        }
        mock_redis.get.return_value = json.dumps(task_data)

        # Create a failing coroutine
        async def error_coroutine():
            raise Exception("Test error")

        task = await task_manager.create_task(
            task_id="task:test:error",
            tool_id="my-tool",
            invocation_id=invocation_id,
            coroutine=error_coroutine(),
        )

        # Wait for task to complete
        await asyncio.sleep(0.1)

        # Task should no longer be in running tasks
        assert "task:test:error" not in task_manager._running_tasks

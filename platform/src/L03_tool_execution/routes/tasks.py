"""
Async Task Management Routes

Endpoints for polling and managing async tool execution tasks.
"""

from fastapi import APIRouter, Request, HTTPException
from datetime import datetime, timezone
import logging

from ..dto import (
    TaskStatusDTO,
    TaskCancelResponseDTO,
    ErrorResponseDTO,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_task_manager(request: Request):
    """Get task manager from app state."""
    task_manager = getattr(request.app.state, "task_manager", None)
    if not task_manager:
        raise HTTPException(
            status_code=503,
            detail={"code": "E3707", "message": "Task manager not available"}
        )
    return task_manager


@router.get("/{task_id}", response_model=TaskStatusDTO)
async def get_task_status(request: Request, task_id: str) -> TaskStatusDTO:
    """
    Get async task status.

    Poll this endpoint to check progress and retrieve results
    for async tool executions.
    """
    task_manager = get_task_manager(request)

    try:
        task = await task_manager.get_task(task_id)

        if not task:
            raise HTTPException(
                status_code=404,
                detail={"code": "E3704", "message": f"Task not found: {task_id}"}
            )

        # Build response from task data
        response = TaskStatusDTO(
            task_id=task.task_id,
            tool_id=task.tool_id,
            invocation_id=str(task.invocation_id),
            status=task.status,
            progress_percent=task.progress_percent,
            created_at=task.created_at,
            updated_at=task.updated_at,
            completed_at=task.completed_at,
        )

        # Add result if completed successfully
        if task.status == "success" and task.result:
            response.result = task.result

        # Add error if failed
        if task.status == "error" and task.error:
            response.error = ErrorResponseDTO(
                code=task.error.get("code", "E3108"),
                message=task.error.get("message", "Task failed"),
                details=task.error.get("details", {}),
                retryable=task.error.get("retryable", False),
            )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status for {task_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"code": "E3008", "message": "Failed to get task status"}
        )


@router.delete("/{task_id}", response_model=TaskCancelResponseDTO)
async def cancel_task(request: Request, task_id: str) -> TaskCancelResponseDTO:
    """
    Cancel an async task.

    Attempts to cancel a running or pending task.
    Returns success status and message.
    """
    task_manager = get_task_manager(request)

    try:
        task = await task_manager.get_task(task_id)

        if not task:
            raise HTTPException(
                status_code=404,
                detail={"code": "E3704", "message": f"Task not found: {task_id}"}
            )

        # Check if task can be cancelled
        if task.status in ("success", "error", "cancelled"):
            return TaskCancelResponseDTO(
                task_id=task_id,
                cancelled=False,
                message=f"Task already in terminal state: {task.status}",
            )

        # Attempt cancellation
        cancelled = await task_manager.cancel_task(task_id)

        if cancelled:
            return TaskCancelResponseDTO(
                task_id=task_id,
                cancelled=True,
                message="Task cancelled successfully",
            )
        else:
            return TaskCancelResponseDTO(
                task_id=task_id,
                cancelled=False,
                message="Task could not be cancelled",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"code": "E3008", "message": "Failed to cancel task"}
        )


@router.get("", response_model=list[TaskStatusDTO])
async def list_tasks(
    request: Request,
    status: str | None = None,
    tool_id: str | None = None,
    limit: int = 50,
) -> list[TaskStatusDTO]:
    """
    List async tasks.

    Supports filtering by status and tool_id.
    """
    task_manager = get_task_manager(request)

    try:
        tasks = await task_manager.list_tasks(
            status=status,
            tool_id=tool_id,
            limit=limit,
        )

        return [
            TaskStatusDTO(
                task_id=task.task_id,
                tool_id=task.tool_id,
                invocation_id=str(task.invocation_id),
                status=task.status,
                progress_percent=task.progress_percent,
                created_at=task.created_at,
                updated_at=task.updated_at,
                completed_at=task.completed_at,
            )
            for task in tasks
        ]

    except Exception as e:
        logger.error(f"Failed to list tasks: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"code": "E3008", "message": "Failed to list tasks"}
        )

"""
Tool Execution Routes

Endpoints for tool invocation (BC-2 interface).
"""

from fastapi import APIRouter, Request, HTTPException
from uuid import uuid4
from datetime import datetime
import logging

from ..dto import (
    ToolInvokeRequestDTO,
    ToolInvokeResponseDTO,
    ExecutionMetadataDTO,
    PollingInfoDTO,
    ErrorResponseDTO,
)
from ..models import (
    ToolInvokeRequest,
    ToolInvokeResponse,
    AgentContext,
    ResourceLimits,
    DocumentContext,
    CheckpointConfig,
    ExecutionOptions,
    ToolStatus,
)
from ..models.error_codes import ErrorCode, ToolExecutionError

logger = logging.getLogger(__name__)

router = APIRouter()


def get_executor(request: Request):
    """Get tool executor from app state."""
    executor = getattr(request.app.state, "tool_executor", None)
    if not executor:
        raise HTTPException(
            status_code=503,
            detail={"code": "E3707", "message": "Tool executor not available"}
        )
    return executor


def get_task_manager(request: Request):
    """Get task manager from app state (optional)."""
    return getattr(request.app.state, "task_manager", None)


def response_to_dto(response: ToolInvokeResponse) -> ToolInvokeResponseDTO:
    """Convert ToolInvokeResponse to DTO."""
    dto = ToolInvokeResponseDTO(
        invocation_id=str(response.invocation_id),
        status=response.status.value if isinstance(response.status, ToolStatus) else response.status,
        completed_at=response.completed_at,
        checkpoint_ref=response.checkpoint_ref,
    )

    # Add result if present
    if response.result:
        dto.result = response.result.to_dict() if hasattr(response.result, "to_dict") else {"result": response.result.result}

    # Add error if present
    if response.error:
        dto.error = ErrorResponseDTO(
            code=response.error.code,
            message=response.error.message,
            details=response.error.details,
            retryable=response.error.retryable,
        )

    # Add execution metadata if present
    if response.execution_metadata:
        dto.execution_metadata = ExecutionMetadataDTO(
            duration_ms=response.execution_metadata.duration_ms,
            cpu_used_millicore_seconds=response.execution_metadata.cpu_used_millicore_seconds,
            memory_peak_mb=response.execution_metadata.memory_peak_mb,
            network_bytes_sent=response.execution_metadata.network_bytes_sent,
            network_bytes_received=response.execution_metadata.network_bytes_received,
            documents_accessed=response.execution_metadata.documents_accessed,
            checkpoints_created=response.execution_metadata.checkpoints_created,
        )

    # Add polling info if present (async mode)
    if response.polling_info:
        dto.polling_info = PollingInfoDTO(
            task_id=response.polling_info.task_id,
            poll_url=response.polling_info.poll_url,
            poll_interval_ms=response.polling_info.poll_interval_seconds * 1000,
            estimated_completion=response.polling_info.estimated_completion,
        )
        dto.task_id = response.polling_info.task_id

    return dto


@router.post("/tools/{tool_id}/invoke", response_model=ToolInvokeResponseDTO)
async def invoke_tool(
    request: Request,
    tool_id: str,
    invoke_request: ToolInvokeRequestDTO,
) -> ToolInvokeResponseDTO:
    """
    Execute tool invocation (BC-2 interface).

    Supports both synchronous and async execution modes.
    For async mode, returns immediately with task_id for polling.
    """
    executor = get_executor(request)
    task_manager = get_task_manager(request)

    # Generate invocation ID
    invocation_id = uuid4()

    try:
        # Build agent context
        agent_context = AgentContext(
            agent_did=invoke_request.agent_did,
            tenant_id=invoke_request.tenant_id,
            session_id=invoke_request.session_id,
        )

        # Build resource limits if provided
        resource_limits = None
        if invoke_request.resource_limits:
            resource_limits = ResourceLimits(
                cpu_millicore_limit=invoke_request.resource_limits.cpu_millicore_limit,
                memory_mb_limit=invoke_request.resource_limits.memory_mb_limit,
                timeout_seconds=invoke_request.resource_limits.timeout_seconds,
            )
        elif invoke_request.timeout_seconds:
            resource_limits = ResourceLimits(timeout_seconds=invoke_request.timeout_seconds)

        # Build document context if provided
        document_context = None
        if invoke_request.document_context:
            document_context = DocumentContext(
                document_refs=invoke_request.document_context.document_refs,
                version_pinning=invoke_request.document_context.version_pinning,
                query=invoke_request.document_context.query,
            )

        # Build checkpoint config if provided
        checkpoint_config = None
        if invoke_request.checkpoint_config:
            checkpoint_config = CheckpointConfig(
                enable_checkpointing=invoke_request.checkpoint_config.enable_checkpointing,
                interval_seconds=invoke_request.checkpoint_config.interval_seconds,
                resume_from=invoke_request.checkpoint_config.resume_from,
            )

        # Build execution options
        execution_options = ExecutionOptions(
            async_mode=invoke_request.async_mode,
            priority=invoke_request.priority,
            idempotency_key=invoke_request.idempotency_key,
        )

        # Build internal request
        internal_request = ToolInvokeRequest(
            invocation_id=invocation_id,
            tool_id=tool_id,
            tool_version=invoke_request.tool_version,
            agent_context=agent_context,
            parameters=invoke_request.parameters,
            resource_limits=resource_limits,
            document_context=document_context,
            checkpoint_config=checkpoint_config,
            execution_options=execution_options,
        )

        logger.info(f"Invoking tool {tool_id} (invocation_id={invocation_id}, async={invoke_request.async_mode})")

        # Execute tool
        response = await executor.execute(internal_request)

        return response_to_dto(response)

    except ToolExecutionError as e:
        logger.error(f"Tool execution error: {e}", exc_info=True)
        status_codes = {
            ErrorCode.E3001: 404,  # Tool not found
            ErrorCode.E3101: 400,  # Missing agent context
            ErrorCode.E3103: 408,  # Timeout
            ErrorCode.E3104: 403,  # Permission denied
            ErrorCode.E3106: 429,  # Concurrent limit exceeded
        }
        status_code = status_codes.get(e.code, 500)
        raise HTTPException(status_code=status_code, detail=e.to_dict())

    except Exception as e:
        logger.error(f"Unexpected error invoking tool {tool_id}: {e}", exc_info=True)
        return ToolInvokeResponseDTO(
            invocation_id=str(invocation_id),
            status="error",
            error=ErrorResponseDTO(
                code="E3108",
                message=f"Tool execution failed: {str(e)}",
                details={"tool_id": tool_id},
                retryable=False,
            ),
        )

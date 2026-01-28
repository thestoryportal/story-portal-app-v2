"""
DTO Unit Tests

Tests for Pydantic DTOs - validation, serialization, and model conversion.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from ..dto import (
    # Tool DTOs
    ToolDTO,
    ToolListResponseDTO,
    ToolSearchRequestDTO,
    ToolSearchResultDTO,
    ToolRegisterRequestDTO,
    ToolDeprecateRequestDTO,
    # Execution DTOs
    AgentContextDTO,
    ResourceLimitsDTO,
    DocumentContextDTO,
    CheckpointConfigDTO,
    ExecutionOptionsDTO,
    ToolInvokeRequestDTO,
    ToolInvokeResponseDTO,
    ExecutionMetadataDTO,
    PollingInfoDTO,
    ErrorResponseDTO,
    TaskStatusDTO,
    TaskCancelResponseDTO,
)
from ..models import ToolCategory, SourceType, DeprecationState, ToolStatus


class TestToolDTO:
    """Tests for ToolDTO"""

    def test_tool_dto_creation(self):
        """Test basic ToolDTO creation"""
        dto = ToolDTO(
            tool_id="my-tool",
            tool_name="My Tool",
            description="A test tool",
            category="computation",
            latest_version="1.0.0",
            source_type="native",
        )
        assert dto.tool_id == "my-tool"
        assert dto.tool_name == "My Tool"
        assert dto.category == "computation"
        assert dto.deprecation_state == "active"

    def test_tool_dto_enum_conversion(self):
        """Test ToolDTO converts enums to strings"""
        dto = ToolDTO(
            tool_id="my-tool",
            tool_name="My Tool",
            description="A test tool",
            category=ToolCategory.COMPUTATION,
            latest_version="1.0.0",
            source_type=SourceType.NATIVE,
            deprecation_state=DeprecationState.ACTIVE,
        )
        assert dto.category == "computation"
        assert dto.source_type == "native"
        assert dto.deprecation_state == "active"

    def test_tool_dto_extra_fields_ignored(self):
        """Test ToolDTO ignores extra fields"""
        dto = ToolDTO(
            tool_id="my-tool",
            tool_name="My Tool",
            description="A test tool",
            category="computation",
            latest_version="1.0.0",
            source_type="native",
            unknown_field="should be ignored",
        )
        assert not hasattr(dto, "unknown_field")

    def test_tool_dto_json_serialization(self):
        """Test ToolDTO JSON serialization"""
        dto = ToolDTO(
            tool_id="my-tool",
            tool_name="My Tool",
            description="A test tool",
            category="data_access",
            latest_version="1.0.0",
            source_type="native",
            tags=["test", "example"],
        )
        json_data = dto.model_dump()
        assert json_data["tool_id"] == "my-tool"
        assert json_data["tags"] == ["test", "example"]


class TestToolSearchRequestDTO:
    """Tests for ToolSearchRequestDTO"""

    def test_search_request_valid(self):
        """Test valid search request"""
        dto = ToolSearchRequestDTO(query="file manipulation tools")
        assert dto.query == "file manipulation tools"
        assert dto.limit == 10  # default
        assert dto.include_deprecated is False

    def test_search_request_with_options(self):
        """Test search request with all options"""
        dto = ToolSearchRequestDTO(
            query="database tools",
            limit=25,
            category="data",
            include_deprecated=True,
        )
        assert dto.limit == 25
        assert dto.category == "data"
        assert dto.include_deprecated is True

    def test_search_request_query_too_short(self):
        """Test search request fails with empty query"""
        with pytest.raises(ValueError):
            ToolSearchRequestDTO(query="")

    def test_search_request_limit_bounds(self):
        """Test search request limit validation"""
        with pytest.raises(ValueError):
            ToolSearchRequestDTO(query="test", limit=0)
        with pytest.raises(ValueError):
            ToolSearchRequestDTO(query="test", limit=101)


class TestToolRegisterRequestDTO:
    """Tests for ToolRegisterRequestDTO"""

    def test_register_request_valid(self):
        """Test valid registration request"""
        dto = ToolRegisterRequestDTO(
            tool_id="my-new-tool",
            tool_name="My New Tool",
            description="This is a description that is long enough",
            category="computation",
            version="1.0.0",
            source_type="native",
        )
        assert dto.tool_id == "my-new-tool"
        assert dto.version == "1.0.0"

    def test_register_request_invalid_tool_id(self):
        """Test registration fails with invalid tool_id format"""
        with pytest.raises(ValueError):
            ToolRegisterRequestDTO(
                tool_id="Invalid Tool ID!",  # Invalid: spaces and special chars
                tool_name="Test",
                description="This is a description that is long enough",
                category="computation",
                version="1.0.0",
                source_type="native",
            )

    def test_register_request_invalid_version(self):
        """Test registration fails with invalid version format"""
        with pytest.raises(ValueError):
            ToolRegisterRequestDTO(
                tool_id="my-tool",
                tool_name="Test",
                description="This is a description that is long enough",
                category="computation",
                version="v1.0",  # Invalid: should be semver
                source_type="native",
            )

    def test_register_request_invalid_category(self):
        """Test registration fails with invalid category"""
        with pytest.raises(ValueError):
            ToolRegisterRequestDTO(
                tool_id="my-tool",
                tool_name="Test",
                description="This is a description that is long enough",
                category="invalid_category",
                version="1.0.0",
                source_type="native",
            )


class TestToolInvokeRequestDTO:
    """Tests for ToolInvokeRequestDTO"""

    def test_invoke_request_minimal(self):
        """Test minimal invocation request"""
        dto = ToolInvokeRequestDTO(
            tool_id="my-tool",
            agent_did="did:agent:123",
            tenant_id="tenant-1",
            session_id="session-abc",
        )
        assert dto.tool_id == "my-tool"
        assert dto.async_mode is False
        assert dto.priority == 5
        assert dto.parameters == {}

    def test_invoke_request_full(self):
        """Test full invocation request with all options"""
        dto = ToolInvokeRequestDTO(
            tool_id="my-tool",
            tool_version="2.1.0",
            agent_did="did:agent:123",
            tenant_id="tenant-1",
            session_id="session-abc",
            parameters={"input": "test data", "count": 5},
            resource_limits=ResourceLimitsDTO(
                cpu_millicore_limit=1000,
                memory_mb_limit=2048,
                timeout_seconds=60,
            ),
            document_context=DocumentContextDTO(
                document_refs=["doc-1", "doc-2"],
                version_pinning=True,
            ),
            checkpoint_config=CheckpointConfigDTO(
                enable_checkpointing=True,
                interval_seconds=15,
            ),
            async_mode=True,
            priority=8,
            timeout_seconds=120,
            idempotency_key="unique-key-123",
        )
        assert dto.tool_version == "2.1.0"
        assert dto.async_mode is True
        assert dto.priority == 8
        assert dto.resource_limits.cpu_millicore_limit == 1000
        assert len(dto.document_context.document_refs) == 2
        assert dto.checkpoint_config.enable_checkpointing is True

    def test_invoke_request_priority_bounds(self):
        """Test priority validation bounds"""
        with pytest.raises(ValueError):
            ToolInvokeRequestDTO(
                tool_id="my-tool",
                agent_did="did:agent:123",
                tenant_id="tenant-1",
                session_id="session-abc",
                priority=0,  # Invalid: must be >= 1
            )
        with pytest.raises(ValueError):
            ToolInvokeRequestDTO(
                tool_id="my-tool",
                agent_did="did:agent:123",
                tenant_id="tenant-1",
                session_id="session-abc",
                priority=11,  # Invalid: must be <= 10
            )


class TestToolInvokeResponseDTO:
    """Tests for ToolInvokeResponseDTO"""

    def test_response_success(self):
        """Test successful response"""
        dto = ToolInvokeResponseDTO(
            invocation_id=str(uuid4()),
            status="success",
            result={"output": "result data"},
            execution_metadata=ExecutionMetadataDTO(duration_ms=150),
        )
        assert dto.status == "success"
        assert dto.result["output"] == "result data"
        assert dto.execution_metadata.duration_ms == 150

    def test_response_error(self):
        """Test error response"""
        dto = ToolInvokeResponseDTO(
            invocation_id=str(uuid4()),
            status="error",
            error=ErrorResponseDTO(
                code="E3108",
                message="Tool execution failed",
                details={"reason": "timeout"},
                retryable=True,
            ),
        )
        assert dto.status == "error"
        assert dto.error.code == "E3108"
        assert dto.error.retryable is True

    def test_response_async_pending(self):
        """Test async pending response"""
        dto = ToolInvokeResponseDTO(
            invocation_id=str(uuid4()),
            status="pending",
            task_id="task:my-tool:abc123",
            polling_info=PollingInfoDTO(
                task_id="task:my-tool:abc123",
                poll_url="/tasks/task:my-tool:abc123",
                poll_interval_ms=2000,
            ),
        )
        assert dto.status == "pending"
        assert dto.task_id == "task:my-tool:abc123"
        assert dto.polling_info.poll_interval_ms == 2000

    def test_response_status_enum_conversion(self):
        """Test response converts ToolStatus enum"""
        dto = ToolInvokeResponseDTO(
            invocation_id=str(uuid4()),
            status=ToolStatus.SUCCESS,
        )
        assert dto.status == "success"


class TestResourceLimitsDTO:
    """Tests for ResourceLimitsDTO"""

    def test_resource_limits_defaults(self):
        """Test resource limits with no values"""
        dto = ResourceLimitsDTO()
        assert dto.cpu_millicore_limit is None
        assert dto.memory_mb_limit is None
        assert dto.timeout_seconds is None

    def test_resource_limits_bounds(self):
        """Test resource limits validation"""
        # Valid limits
        dto = ResourceLimitsDTO(
            cpu_millicore_limit=2000,
            memory_mb_limit=4096,
            timeout_seconds=300,
        )
        assert dto.cpu_millicore_limit == 2000

        # Invalid CPU limit
        with pytest.raises(ValueError):
            ResourceLimitsDTO(cpu_millicore_limit=50)  # < 100
        with pytest.raises(ValueError):
            ResourceLimitsDTO(cpu_millicore_limit=5000)  # > 4000


class TestTaskStatusDTO:
    """Tests for TaskStatusDTO"""

    def test_task_status_pending(self):
        """Test pending task status"""
        now = datetime.utcnow()
        dto = TaskStatusDTO(
            task_id="task:tool:abc",
            tool_id="my-tool",
            invocation_id=str(uuid4()),
            status="pending",
            created_at=now,
            updated_at=now,
        )
        assert dto.status == "pending"
        assert dto.progress_percent is None
        assert dto.completed_at is None

    def test_task_status_running(self):
        """Test running task status with progress"""
        now = datetime.utcnow()
        dto = TaskStatusDTO(
            task_id="task:tool:abc",
            tool_id="my-tool",
            invocation_id=str(uuid4()),
            status="running",
            progress_percent=45,
            created_at=now,
            updated_at=now,
        )
        assert dto.status == "running"
        assert dto.progress_percent == 45

    def test_task_status_completed(self):
        """Test completed task status"""
        now = datetime.utcnow()
        dto = TaskStatusDTO(
            task_id="task:tool:abc",
            tool_id="my-tool",
            invocation_id=str(uuid4()),
            status="success",
            progress_percent=100,
            result={"output": "done"},
            created_at=now,
            updated_at=now,
            completed_at=now,
        )
        assert dto.status == "success"
        assert dto.progress_percent == 100
        assert dto.result is not None


class TestDocumentContextDTO:
    """Tests for DocumentContextDTO"""

    def test_document_context_defaults(self):
        """Test document context with defaults"""
        dto = DocumentContextDTO()
        assert dto.document_refs == []
        assert dto.version_pinning is True
        assert dto.query is None

    def test_document_context_with_refs(self):
        """Test document context with references"""
        dto = DocumentContextDTO(
            document_refs=["doc-1", "doc-2", "doc-3"],
            version_pinning=False,
            query="related documents",
        )
        assert len(dto.document_refs) == 3
        assert dto.version_pinning is False
        assert dto.query == "related documents"


class TestErrorResponseDTO:
    """Tests for ErrorResponseDTO"""

    def test_error_response_minimal(self):
        """Test minimal error response"""
        dto = ErrorResponseDTO(
            code="E3001",
            message="Tool not found",
        )
        assert dto.code == "E3001"
        assert dto.details == {}
        assert dto.retryable is False

    def test_error_response_full(self):
        """Test full error response"""
        dto = ErrorResponseDTO(
            code="E3103",
            message="Tool execution timeout",
            details={"tool_id": "my-tool", "timeout_seconds": 30},
            retryable=True,
        )
        assert dto.retryable is True
        assert dto.details["tool_id"] == "my-tool"


class TestIntegration:
    """Integration tests for DTO conversions"""

    def test_tool_dto_from_dataclass(self, sample_tool_definition):
        """Test creating ToolDTO from ToolDefinition dataclass"""
        tool_def = sample_tool_definition
        dto = ToolDTO(
            tool_id=tool_def.tool_id,
            tool_name=tool_def.tool_name,
            description=tool_def.description,
            category=tool_def.category,
            tags=tool_def.tags,
            latest_version=tool_def.latest_version,
            source_type=tool_def.source_type,
            deprecation_state=tool_def.deprecation_state,
            requires_approval=tool_def.requires_approval,
            default_timeout_seconds=tool_def.default_timeout_seconds,
            default_cpu_millicore_limit=tool_def.default_cpu_millicore_limit,
            default_memory_mb_limit=tool_def.default_memory_mb_limit,
        )
        assert dto.tool_id == "test_tool"
        assert dto.category == "computation"

    def test_invoke_request_roundtrip(self, sample_tool_invoke_request):
        """Test converting ToolInvokeRequest to DTO and back"""
        req = sample_tool_invoke_request
        dto = ToolInvokeRequestDTO(
            tool_id=req.tool_id,
            tool_version=req.tool_version,
            agent_did=req.agent_context.agent_did,
            tenant_id=req.agent_context.tenant_id,
            session_id=req.agent_context.session_id,
            parameters=req.parameters,
        )
        assert dto.tool_id == "test_tool"
        assert dto.parameters == {"input": "test data"}

        # Verify JSON serialization
        json_data = dto.model_dump()
        assert json_data["tool_id"] == "test_tool"

    def test_tool_list_response(self, sample_tool_definition):
        """Test ToolListResponseDTO with multiple tools"""
        tool_def = sample_tool_definition
        tool_dto = ToolDTO(
            tool_id=tool_def.tool_id,
            tool_name=tool_def.tool_name,
            description=tool_def.description,
            category=tool_def.category,
            latest_version=tool_def.latest_version,
            source_type=tool_def.source_type,
        )
        response = ToolListResponseDTO(
            tools=[tool_dto, tool_dto],
            total=2,
            page=1,
            page_size=50,
        )
        assert len(response.tools) == 2
        assert response.total == 2

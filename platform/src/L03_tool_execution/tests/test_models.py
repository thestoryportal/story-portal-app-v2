"""
Test Model Classes

Tests for L03 data models.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from ..models import (
    ToolDefinition,
    ToolCategory,
    SourceType,
    DeprecationState,
    ToolManifest,
    ExecutionMode,
    ToolInvokeRequest,
    ToolInvokeResponse,
    ToolStatus,
    ExecutionContext,
    ResourceLimits,
    Checkpoint,
    CheckpointType,
    ErrorCode,
    ToolExecutionError,
)


class TestToolDefinition:
    """Test ToolDefinition model"""

    def test_create_tool_definition(self, sample_tool_definition):
        """Test creating a tool definition"""
        assert sample_tool_definition.tool_id == "test_tool"
        assert sample_tool_definition.category == ToolCategory.COMPUTATION
        assert sample_tool_definition.source_type == SourceType.NATIVE

    def test_tool_definition_to_dict(self, sample_tool_definition):
        """Test serialization to dictionary"""
        data = sample_tool_definition.to_dict()
        assert data["tool_id"] == "test_tool"
        assert data["category"] == "computation"
        assert data["deprecation_state"] == "active"


class TestToolManifest:
    """Test ToolManifest model"""

    def test_create_tool_manifest(self, sample_tool_manifest):
        """Test creating a tool manifest"""
        assert sample_tool_manifest.tool_id == "test_tool"
        assert sample_tool_manifest.execution_mode == ExecutionMode.SYNC

    def test_manifest_to_dict(self, sample_tool_manifest):
        """Test serialization"""
        data = sample_tool_manifest.to_dict()
        assert "parameters_schema" in data
        assert data["execution_mode"] == "sync"


class TestResourceLimits:
    """Test ResourceLimits model"""

    def test_validate_against_parent(self):
        """Test BC-1 resource limit validation"""
        parent = ResourceLimits(
            cpu_millicore_limit=1000,
            memory_mb_limit=2048,
            timeout_seconds=60,
        )

        # Valid limits (within parent)
        child = ResourceLimits(
            cpu_millicore_limit=500,
            memory_mb_limit=1024,
            timeout_seconds=30,
        )
        assert child.validate_against_parent(parent) is True

        # Invalid limits (exceeds parent)
        child_invalid = ResourceLimits(
            cpu_millicore_limit=1500,
            memory_mb_limit=1024,
            timeout_seconds=30,
        )
        assert child_invalid.validate_against_parent(parent) is False


class TestCheckpoint:
    """Test Checkpoint model"""

    def test_create_checkpoint(self):
        """Test creating a checkpoint"""
        checkpoint = Checkpoint(
            checkpoint_type=CheckpointType.MICRO,
            state={"iteration": 10, "progress": 0.5},
            progress_percent=50,
        )

        assert checkpoint.checkpoint_type == CheckpointType.MICRO
        assert checkpoint.progress_percent == 50
        assert checkpoint.is_delta is False

    def test_checkpoint_with_delta(self):
        """Test checkpoint with delta encoding"""
        parent_id = uuid4()
        checkpoint = Checkpoint(
            checkpoint_type=CheckpointType.MICRO,
            parent_checkpoint_id=parent_id,
            is_delta=True,
            state={"__delta_patch__": []},
        )

        assert checkpoint.is_delta is True
        assert checkpoint.parent_checkpoint_id == parent_id


class TestToolExecutionError:
    """Test error handling"""

    def test_create_error(self):
        """Test creating a tool execution error"""
        error = ToolExecutionError(
            ErrorCode.E3001,
            details={"tool_id": "missing_tool"}
        )

        assert error.code == ErrorCode.E3001
        assert "missing_tool" in str(error.details)
        assert error.retryable is False

    def test_retryable_error(self):
        """Test retryable error flagging"""
        error = ToolExecutionError(ErrorCode.E3103)  # Timeout
        assert error.retryable is True

        error_dict = error.to_dict()
        assert error_dict["retryable"] is True

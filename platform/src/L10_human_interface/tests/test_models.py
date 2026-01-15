"""
L10 Human Interface Layer - Model Tests

Test data models for validation and serialization.
"""

import pytest
from datetime import datetime, UTC

from ..models import (
    ErrorCode,
    InterfaceError,
    AgentState,
    AgentStateInfo,
    ControlOperation,
    ControlStatus,
    ControlResponse,
    EventType,
    AlertSeverity,
    AuditAction,
)


class TestErrorModels:
    """Test error models."""

    def test_error_code_enum(self):
        """Test ErrorCode enum."""
        assert ErrorCode.E10001 == "E10001"
        assert ErrorCode.E10302 == "E10302"
        assert ErrorCode.E10901 == "E10901"

    def test_interface_error_creation(self):
        """Test InterfaceError creation."""
        error = InterfaceError.from_code(
            ErrorCode.E10001,
            details={"api_key": "missing"},
            recovery_suggestion="Provide valid API key",
        )

        assert error.code == ErrorCode.E10001
        assert error.message == "Missing API key"
        assert error.details["api_key"] == "missing"
        assert error.recovery_suggestion == "Provide valid API key"

    def test_interface_error_http_status(self):
        """Test HTTP status mapping."""
        error_401 = InterfaceError.from_code(ErrorCode.E10001)  # Auth
        assert error_401.http_status == 401

        error_404 = InterfaceError.from_code(ErrorCode.E10302)  # Not found
        assert error_404.http_status == 404

        error_409 = InterfaceError.from_code(ErrorCode.E10305)  # Conflict
        assert error_409.http_status == 409

        error_503 = InterfaceError.from_code(ErrorCode.E10902)  # Dependency unavailable
        assert error_503.http_status == 503

    def test_interface_error_is_recoverable(self):
        """Test recoverable error detection."""
        recoverable = InterfaceError.from_code(ErrorCode.E10103)  # Timeout
        assert recoverable.is_recoverable is True

        not_recoverable = InterfaceError.from_code(ErrorCode.E10002)  # Invalid API key
        assert not_recoverable.is_recoverable is False

    def test_interface_error_to_dict(self):
        """Test error serialization."""
        error = InterfaceError.from_code(ErrorCode.E10001, details={"key": "value"})
        error_dict = error.to_dict()

        assert "error" in error_dict
        assert error_dict["error"]["code"] == "E10001"
        assert error_dict["error"]["message"] == "Missing API key"
        assert error_dict["error"]["details"]["key"] == "value"


class TestDashboardModels:
    """Test dashboard models."""

    def test_agent_state_enum(self):
        """Test AgentState enum."""
        assert AgentState.PENDING == "pending"
        assert AgentState.RUNNING == "running"
        assert AgentState.PAUSED == "paused"

    def test_agent_state_info_creation(self):
        """Test AgentStateInfo creation."""
        agent = AgentStateInfo(
            agent_id="agent-1",
            name="Test Agent",
            state=AgentState.RUNNING,
            tenant_id="tenant-1",
        )

        assert agent.agent_id == "agent-1"
        assert agent.state == AgentState.RUNNING
        assert agent.error_count_1h == 0

    def test_agent_state_info_to_dict(self):
        """Test AgentStateInfo serialization."""
        agent = AgentStateInfo(
            agent_id="agent-1",
            name="Test Agent",
            state=AgentState.RUNNING,
            tenant_id="tenant-1",
            last_event_at=datetime.now(UTC),
        )

        agent_dict = agent.to_dict()
        assert agent_dict["agent_id"] == "agent-1"
        assert agent_dict["state"] == "running"
        assert "last_event_at" in agent_dict


class TestControlModels:
    """Test control models."""

    def test_control_operation_enum(self):
        """Test ControlOperation enum."""
        assert ControlOperation.PAUSE == "pause"
        assert ControlOperation.RESUME == "resume"
        assert ControlOperation.EMERGENCY_STOP == "emergency_stop"

    def test_control_response_creation(self):
        """Test ControlResponse creation."""
        response = ControlResponse(
            operation=ControlOperation.PAUSE,
            status=ControlStatus.SUCCESS,
            agent_id="agent-1",
            message="Agent paused successfully",
            previous_state="running",
            new_state="paused",
        )

        assert response.operation == ControlOperation.PAUSE
        assert response.status == ControlStatus.SUCCESS
        assert response.idempotent is False

    def test_control_response_to_dict(self):
        """Test ControlResponse serialization."""
        response = ControlResponse(
            operation=ControlOperation.PAUSE,
            status=ControlStatus.SUCCESS,
            agent_id="agent-1",
            message="Test",
        )

        response_dict = response.to_dict()
        assert response_dict["operation"] == "pause"
        assert response_dict["status"] == "success"
        assert "timestamp" in response_dict


class TestEventModels:
    """Test event models."""

    def test_event_type_enum(self):
        """Test EventType enum."""
        assert EventType.AGENT_STATE_CHANGED == "agent.state.changed"
        assert EventType.TASK_COMPLETED == "task.completed"


class TestAlertModels:
    """Test alert models."""

    def test_alert_severity_enum(self):
        """Test AlertSeverity enum."""
        assert AlertSeverity.CRITICAL == "critical"
        assert AlertSeverity.WARNING == "warning"


class TestAuditModels:
    """Test audit models."""

    def test_audit_action_enum(self):
        """Test AuditAction enum."""
        assert AuditAction.PAUSE_AGENT == "pause_agent"
        assert AuditAction.RESUME_AGENT == "resume_agent"

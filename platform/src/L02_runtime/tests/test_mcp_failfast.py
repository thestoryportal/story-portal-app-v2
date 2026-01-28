"""
Tests for MCP Fail-Fast Mode

Tests for MCP error handling modes in SessionBridge and DocumentBridge.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from ..services.session_bridge import (
    SessionBridge,
    SessionError,
    MCPErrorMode as SessionMCPErrorMode,
)
from ..services.document_bridge import (
    DocumentBridge,
    DocumentError,
    MCPErrorMode as DocMCPErrorMode,
)


class TestSessionBridgeErrorModes:
    """Tests for SessionBridge MCP error modes"""

    def test_default_mode_is_graceful(self):
        """Test default error mode is graceful"""
        bridge = SessionBridge(config={})

        assert bridge.mcp_error_mode == SessionMCPErrorMode.GRACEFUL_DEGRADE

    def test_fail_fast_mode_configured(self):
        """Test fail-fast mode can be configured"""
        bridge = SessionBridge(config={
            "mcp_error_mode": "fail_fast"
        })

        assert bridge.mcp_error_mode == SessionMCPErrorMode.FAIL_FAST

    def test_is_stub_mode_initially_false(self):
        """Test stub mode is initially False"""
        bridge = SessionBridge(config={})

        assert bridge.is_stub_mode() is False

    @pytest.mark.asyncio
    async def test_graceful_mode_sets_stub_on_failure(self):
        """Test graceful mode sets stub mode on MCP failure"""
        bridge = SessionBridge(config={
            "mcp_error_mode": "graceful"
        })

        # Simulate MCP unavailable
        bridge._handle_mcp_unavailable("Test failure")

        assert bridge.is_stub_mode() is True

    @pytest.mark.asyncio
    async def test_fail_fast_mode_raises_on_failure(self):
        """Test fail-fast mode raises error on MCP failure"""
        bridge = SessionBridge(config={
            "mcp_error_mode": "fail_fast"
        })

        with pytest.raises(SessionError) as exc_info:
            bridge._handle_mcp_unavailable("Test failure")

        assert exc_info.value.code == "E2055"

    @pytest.mark.asyncio
    async def test_stub_mode_returns_stub_response(self):
        """Test stub mode returns stub response for tool calls"""
        bridge = SessionBridge(config={})
        bridge._stub_mode = True

        result = await bridge._call_mcp_tool("check_recovery", {})

        assert result.get("stub") is True or result.get("checked") is True

    @pytest.mark.asyncio
    async def test_tool_failure_graceful_returns_stub(self):
        """Test tool failure in graceful mode returns stub response"""
        bridge = SessionBridge(config={
            "mcp_error_mode": "graceful"
        })
        bridge._stub_mode = False

        result = bridge._handle_tool_failure("test_tool", "Test error")

        assert result["success"] is False
        assert result["stub_mode"] is True
        assert "test_tool" in result["tool"]

    @pytest.mark.asyncio
    async def test_tool_failure_fail_fast_raises(self):
        """Test tool failure in fail-fast mode raises error"""
        bridge = SessionBridge(config={
            "mcp_error_mode": "fail_fast"
        })
        bridge._stub_mode = False

        with pytest.raises(SessionError) as exc_info:
            bridge._handle_tool_failure("test_tool", "Test error")

        assert exc_info.value.code == "E2056"


class TestDocumentBridgeErrorModes:
    """Tests for DocumentBridge MCP error modes"""

    def test_default_mode_is_graceful(self):
        """Test default error mode is graceful"""
        bridge = DocumentBridge(config={})

        assert bridge.mcp_error_mode == DocMCPErrorMode.GRACEFUL_DEGRADE

    def test_fail_fast_mode_configured(self):
        """Test fail-fast mode can be configured"""
        bridge = DocumentBridge(config={
            "mcp_error_mode": "fail_fast"
        })

        assert bridge.mcp_error_mode == DocMCPErrorMode.FAIL_FAST

    def test_is_stub_mode_initially_false(self):
        """Test stub mode is initially False"""
        bridge = DocumentBridge(config={})

        assert bridge.is_stub_mode() is False

    @pytest.mark.asyncio
    async def test_graceful_mode_sets_stub_on_failure(self):
        """Test graceful mode sets stub mode on MCP failure"""
        bridge = DocumentBridge(config={
            "mcp_error_mode": "graceful"
        })

        # Simulate MCP unavailable
        bridge._handle_mcp_unavailable("Test failure")

        assert bridge.is_stub_mode() is True

    @pytest.mark.asyncio
    async def test_fail_fast_mode_raises_on_failure(self):
        """Test fail-fast mode raises error on MCP failure"""
        bridge = DocumentBridge(config={
            "mcp_error_mode": "fail_fast"
        })

        with pytest.raises(DocumentError) as exc_info:
            bridge._handle_mcp_unavailable("Test failure")

        assert exc_info.value.code == "E2065"

    @pytest.mark.asyncio
    async def test_stub_mode_returns_stub_response(self):
        """Test stub mode returns stub response for tool calls"""
        bridge = DocumentBridge(config={})
        bridge._stub_mode = True

        result = await bridge._call_mcp_tool("search_hybrid", {"query": "test"})

        assert result.get("stub") is True
        assert "documents" in result

    @pytest.mark.asyncio
    async def test_tool_failure_graceful_returns_stub(self):
        """Test tool failure in graceful mode returns stub response"""
        bridge = DocumentBridge(config={
            "mcp_error_mode": "graceful"
        })
        bridge._stub_mode = False

        result = bridge._handle_tool_failure("test_tool", "Test error")

        assert result["success"] is False
        assert result["stub_mode"] is True
        assert "documents" in result

    @pytest.mark.asyncio
    async def test_tool_failure_fail_fast_raises(self):
        """Test tool failure in fail-fast mode raises error"""
        bridge = DocumentBridge(config={
            "mcp_error_mode": "fail_fast"
        })
        bridge._stub_mode = False

        with pytest.raises(DocumentError) as exc_info:
            bridge._handle_tool_failure("test_tool", "Test error")

        assert exc_info.value.code == "E2066"


class TestStubResponses:
    """Tests for stub response content"""

    def test_session_bridge_stub_check_recovery(self):
        """Test stub response for check_recovery"""
        bridge = SessionBridge(config={})

        response = bridge._get_stub_response("check_recovery", {})

        assert "needsRecovery" in response
        assert response["needsRecovery"] == []

    def test_session_bridge_stub_save_context(self):
        """Test stub response for save_context_snapshot"""
        bridge = SessionBridge(config={})

        response = bridge._get_stub_response("save_context_snapshot", {})

        assert response["success"] is True
        assert response.get("stub") is True

    def test_session_bridge_stub_get_unified_context(self):
        """Test stub response for get_unified_context"""
        bridge = SessionBridge(config={})

        response = bridge._get_stub_response(
            "get_unified_context",
            {"taskId": "task-123"}
        )

        assert response["taskId"] == "task-123"
        assert response.get("stub") is True

    def test_document_bridge_stub_search_hybrid(self):
        """Test stub response for search_hybrid"""
        bridge = DocumentBridge(config={})

        response = bridge._get_stub_response("search_hybrid", {"query": "test"})

        assert "documents" in response
        assert response["documents"] == []
        assert response.get("stub") is True

    def test_document_bridge_stub_get_document(self):
        """Test stub response for get_document"""
        bridge = DocumentBridge(config={})

        response = bridge._get_stub_response(
            "get_document",
            {"documentId": "doc-123"}
        )

        assert response.get("document") is None
        assert response.get("stub") is True

    def test_document_bridge_stub_unknown_tool(self):
        """Test stub response for unknown tool"""
        bridge = DocumentBridge(config={})

        response = bridge._get_stub_response("unknown_tool", {})

        assert response["success"] is True
        assert response.get("stub") is True
        assert response["tool"] == "unknown_tool"


class TestMCPErrorModeEnum:
    """Tests for MCPErrorMode enum"""

    def test_session_error_mode_values(self):
        """Test SessionBridge MCPErrorMode values"""
        assert SessionMCPErrorMode.FAIL_FAST.value == "fail_fast"
        assert SessionMCPErrorMode.GRACEFUL_DEGRADE.value == "graceful"

    def test_document_error_mode_values(self):
        """Test DocumentBridge MCPErrorMode values"""
        assert DocMCPErrorMode.FAIL_FAST.value == "fail_fast"
        assert DocMCPErrorMode.GRACEFUL_DEGRADE.value == "graceful"

    def test_error_mode_from_string(self):
        """Test creating error mode from string"""
        fail_fast = SessionMCPErrorMode("fail_fast")
        graceful = SessionMCPErrorMode("graceful")

        assert fail_fast == SessionMCPErrorMode.FAIL_FAST
        assert graceful == SessionMCPErrorMode.GRACEFUL_DEGRADE


class TestIntegrationScenarios:
    """Integration-style tests for error mode scenarios"""

    @pytest.mark.asyncio
    async def test_session_start_in_stub_mode(self):
        """Test session start works in stub mode"""
        bridge = SessionBridge(config={})
        bridge._stub_mode = True

        result = await bridge.start_session(
            agent_id="agent-1",
            session_id="session-1",
            initial_context={}
        )

        assert result["session_id"] == "session-1"
        assert result["status"] == "active"

    @pytest.mark.asyncio
    async def test_document_query_in_stub_mode(self):
        """Test document query works in stub mode"""
        bridge = DocumentBridge(config={})
        bridge._stub_mode = True

        result = await bridge.query_documents("test query")

        # Should return empty list from stub
        assert result == []

    @pytest.mark.asyncio
    async def test_mixed_mode_switch(self):
        """Test switching from normal to stub mode"""
        bridge = SessionBridge(config={
            "mcp_error_mode": "graceful"
        })

        # Initially not in stub mode
        assert bridge.is_stub_mode() is False

        # Simulate connection failure
        bridge._handle_mcp_unavailable("Connection lost")

        # Now in stub mode
        assert bridge.is_stub_mode() is True

        # Operations should still work
        result = await bridge._call_mcp_tool("check_recovery", {})
        assert result is not None

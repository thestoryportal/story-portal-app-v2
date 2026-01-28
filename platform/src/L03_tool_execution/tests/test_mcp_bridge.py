"""
MCP Tool Bridge Unit Tests

Tests for MCPToolBridge and L02HttpClient with mocked HTTP responses.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

import httpx

from ..services.l02_http_client import L02HttpClient, L02ClientError
from ..services.mcp_tool_bridge import MCPToolBridge
from ..models import Checkpoint, CheckpointType, DocumentContext


class TestL02HttpClient:
    """Tests for L02HttpClient."""

    @pytest.fixture
    def mock_httpx_client(self):
        """Create mock httpx client."""
        client = AsyncMock(spec=httpx.AsyncClient)
        return client

    @pytest.fixture
    def l02_client(self):
        """Create L02HttpClient instance."""
        return L02HttpClient(
            base_url="http://localhost:8002",
            timeout=5.0,
            max_retries=2,
        )

    @pytest.mark.asyncio
    async def test_initialize_success(self, l02_client):
        """Test successful initialization."""
        with patch.object(httpx.AsyncClient, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            available = await l02_client.initialize()

            # Client should be initialized even if L02 is available
            assert l02_client._client is not None

        # Cleanup
        await l02_client.close()

    @pytest.mark.asyncio
    async def test_initialize_unavailable(self, l02_client):
        """Test initialization when L02 is unavailable."""
        with patch.object(httpx.AsyncClient, "get", side_effect=httpx.RequestError("Connection failed")):
            available = await l02_client.initialize()

            assert l02_client._client is not None
            assert not l02_client.is_available

        await l02_client.close()

    @pytest.mark.asyncio
    async def test_get_document(self, l02_client):
        """Test get_document request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "doc-123",
            "title": "Test Doc",
            "content": "Test content",
        }

        l02_client._client = AsyncMock()
        l02_client._client.request = AsyncMock(return_value=mock_response)
        l02_client._available = True

        result = await l02_client.get_document("doc-123")

        assert result["id"] == "doc-123"
        assert result["title"] == "Test Doc"

    @pytest.mark.asyncio
    async def test_get_document_unavailable(self, l02_client):
        """Test get_document when L02 unavailable."""
        l02_client._client = AsyncMock()
        l02_client._available = False

        result = await l02_client.get_document("doc-123")

        assert result is None

    @pytest.mark.asyncio
    async def test_search_documents(self, l02_client):
        """Test search_documents request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "documents": [
                {"id": "doc-1", "title": "Doc 1", "confidence": 0.9},
                {"id": "doc-2", "title": "Doc 2", "confidence": 0.8},
            ]
        }

        l02_client._client = AsyncMock()
        l02_client._client.request = AsyncMock(return_value=mock_response)
        l02_client._available = True

        result = await l02_client.search_documents("test query", limit=10)

        assert len(result) == 2
        assert result[0]["id"] == "doc-1"

    @pytest.mark.asyncio
    async def test_create_checkpoint(self, l02_client):
        """Test create_checkpoint request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "checkpoint_id": "cp-123"
        }

        l02_client._client = AsyncMock()
        l02_client._client.request = AsyncMock(return_value=mock_response)
        l02_client._available = True

        result = await l02_client.create_checkpoint(
            task_id="task-123",
            checkpoint_data={"state": {"key": "value"}}
        )

        assert result == "cp-123"

    @pytest.mark.asyncio
    async def test_restore_checkpoint(self, l02_client):
        """Test restore_checkpoint request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "checkpoint_id": "cp-123",
            "state": {"key": "value"},
            "progress_percent": 50,
        }

        l02_client._client = AsyncMock()
        l02_client._client.request = AsyncMock(return_value=mock_response)
        l02_client._available = True

        result = await l02_client.restore_checkpoint("cp-123")

        assert result["checkpoint_id"] == "cp-123"
        assert result["state"]["key"] == "value"

    @pytest.mark.asyncio
    async def test_save_context_snapshot(self, l02_client):
        """Test save_context_snapshot request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}

        l02_client._client = AsyncMock()
        l02_client._client.request = AsyncMock(return_value=mock_response)
        l02_client._available = True

        result = await l02_client.save_context_snapshot(
            task_id="task-123",
            context={"state": "running"},
            change_summary="Test snapshot",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_404_returns_none(self, l02_client):
        """Test that 404 responses return None gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        l02_client._client = AsyncMock()
        l02_client._client.request = AsyncMock(return_value=mock_response)
        l02_client._available = True

        result = await l02_client.get_document("nonexistent")

        assert result is None


class TestMCPToolBridge:
    """Tests for MCPToolBridge."""

    @pytest.fixture
    def mock_l02_client(self):
        """Create mock L02HttpClient."""
        client = AsyncMock(spec=L02HttpClient)
        client.is_available = True
        return client

    @pytest.fixture
    def mcp_bridge(self, mock_l02_client):
        """Create MCPToolBridge with mocked L02 client."""
        bridge = MCPToolBridge(
            document_server_enabled=True,
            context_server_enabled=True,
        )
        bridge.l02_client = mock_l02_client
        return bridge

    @pytest.mark.asyncio
    async def test_initialize(self, mcp_bridge, mock_l02_client):
        """Test bridge initialization."""
        mock_l02_client.initialize.return_value = True

        await mcp_bridge.initialize()

        mock_l02_client.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_close(self, mcp_bridge, mock_l02_client):
        """Test bridge cleanup."""
        await mcp_bridge.close()

        mock_l02_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_document(self, mcp_bridge, mock_l02_client):
        """Test get_document through bridge."""
        mock_l02_client.get_document.return_value = {
            "id": "doc-123",
            "title": "Test Doc",
            "content": "Test content",
            "version": "1.0.0",
            "metadata": {},
        }

        result = await mcp_bridge.get_document("doc-123")

        assert result["document_id"] == "doc-123"
        assert result["title"] == "Test Doc"
        mock_l02_client.get_document.assert_called_once_with("doc-123", True)

    @pytest.mark.asyncio
    async def test_get_document_not_found(self, mcp_bridge, mock_l02_client):
        """Test get_document when document not found."""
        mock_l02_client.get_document.return_value = None

        result = await mcp_bridge.get_document("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_search_documents(self, mcp_bridge, mock_l02_client):
        """Test search_documents through bridge."""
        mock_l02_client.search_documents.return_value = [
            {"id": "doc-1", "title": "Doc 1", "content": "Content 1", "confidence": 0.9},
            {"id": "doc-2", "title": "Doc 2", "content": "Content 2", "confidence": 0.8},
        ]

        result = await mcp_bridge.search_documents("test query", limit=5)

        assert len(result) == 2
        assert result[0]["document_id"] == "doc-1"
        assert result[0]["confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_get_documents_for_tool(self, mcp_bridge, mock_l02_client):
        """Test get_documents_for_tool aggregation."""
        mock_l02_client.get_document.return_value = {
            "id": "doc-123",
            "title": "Test Doc",
            "content": "Content",
        }
        mock_l02_client.search_documents.return_value = [
            {"id": "doc-search", "title": "Search Result", "content": "Found"},
        ]

        doc_context = DocumentContext(
            document_refs=["doc-123"],
            query="test query",
        )

        result = await mcp_bridge.get_documents_for_tool(doc_context)

        # Should have document from ref + search result
        assert len(result) >= 1
        mock_l02_client.get_document.assert_called()

    @pytest.mark.asyncio
    async def test_create_checkpoint(self, mcp_bridge, mock_l02_client):
        """Test create_checkpoint through bridge."""
        mock_l02_client.create_checkpoint.return_value = "cp-new-123"

        checkpoint = Checkpoint(
            checkpoint_id=uuid4(),
            invocation_id=uuid4(),
            checkpoint_type=CheckpointType.MACRO,
            state={"key": "value"},
            progress_percent=50,
        )

        result = await mcp_bridge.create_checkpoint(checkpoint)

        assert result == "cp-new-123"
        mock_l02_client.create_checkpoint.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_checkpoint_unavailable(self, mcp_bridge, mock_l02_client):
        """Test create_checkpoint when L02 unavailable."""
        mock_l02_client.create_checkpoint.return_value = None

        checkpoint = Checkpoint(
            checkpoint_id=uuid4(),
            invocation_id=uuid4(),
            checkpoint_type=CheckpointType.MACRO,
            state={},
            progress_percent=0,
        )

        result = await mcp_bridge.create_checkpoint(checkpoint)

        # Should return the checkpoint_id even if unavailable
        assert result == str(checkpoint.checkpoint_id)

    @pytest.mark.asyncio
    async def test_restore_checkpoint(self, mcp_bridge, mock_l02_client):
        """Test restore_checkpoint through bridge."""
        checkpoint_id = str(uuid4())
        mock_l02_client.restore_checkpoint.return_value = {
            "checkpoint_id": checkpoint_id,
            "invocation_id": checkpoint_id,
            "checkpoint_type": "macro",
            "state": {"key": "value"},
            "progress_percent": 75,
        }

        result = await mcp_bridge.restore_checkpoint(checkpoint_id)

        assert result is not None
        assert result.state == {"key": "value"}
        assert result.progress_percent == 75

    @pytest.mark.asyncio
    async def test_restore_checkpoint_not_found(self, mcp_bridge, mock_l02_client):
        """Test restore_checkpoint when checkpoint not found."""
        mock_l02_client.restore_checkpoint.return_value = None

        result = await mcp_bridge.restore_checkpoint("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_save_context_snapshot(self, mcp_bridge, mock_l02_client):
        """Test save_context_snapshot through bridge."""
        mock_l02_client.save_context_snapshot.return_value = True

        await mcp_bridge.save_context_snapshot(
            task_id="task-123",
            state={"status": "running"},
        )

        mock_l02_client.save_context_snapshot.assert_called_once()

    @pytest.mark.asyncio
    async def test_disabled_document_server(self):
        """Test bridge with document server disabled."""
        bridge = MCPToolBridge(
            document_server_enabled=False,
            context_server_enabled=True,
        )
        bridge.l02_client = AsyncMock()

        result = await bridge.get_document("doc-123")

        assert result is None

    @pytest.mark.asyncio
    async def test_disabled_context_server(self):
        """Test bridge with context server disabled."""
        bridge = MCPToolBridge(
            document_server_enabled=True,
            context_server_enabled=False,
        )
        bridge.l02_client = AsyncMock()

        checkpoint = Checkpoint(
            checkpoint_id=uuid4(),
            invocation_id=uuid4(),
            checkpoint_type=CheckpointType.MACRO,
            state={},
            progress_percent=0,
        )

        result = await bridge.create_checkpoint(checkpoint)

        # Should return checkpoint_id without calling L02
        assert result == str(checkpoint.checkpoint_id)

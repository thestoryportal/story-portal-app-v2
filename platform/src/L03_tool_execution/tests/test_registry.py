"""
Test Tool Registry

Tests for tool registration and semantic search.
"""

import pytest
from ..services import ToolRegistry
from ..models import ErrorCode, ToolExecutionError


@pytest.mark.asyncio
class TestToolRegistry:
    """Test ToolRegistry service"""

    @pytest.fixture
    async def registry(self, mock_db_connection_string):
        """Create registry instance"""
        registry = ToolRegistry(
            db_connection_string=mock_db_connection_string,
            ollama_base_url="http://localhost:11434",
        )
        try:
            await registry.initialize()
            yield registry
        finally:
            await registry.close()

    async def test_register_tool(self, registry, sample_tool_definition, sample_tool_manifest):
        """Test tool registration"""
        result = await registry.register_tool(sample_tool_definition, sample_tool_manifest)
        assert result is True

    async def test_get_tool(self, registry, sample_tool_definition, sample_tool_manifest):
        """Test retrieving tool by ID"""
        await registry.register_tool(sample_tool_definition, sample_tool_manifest)

        tool = await registry.get_tool("test_tool")
        assert tool is not None
        assert tool.tool_id == "test_tool"

    async def test_get_nonexistent_tool(self, registry):
        """Test retrieving non-existent tool"""
        with pytest.raises(ToolExecutionError) as exc_info:
            await registry.get_tool("nonexistent_tool")

        assert exc_info.value.code == ErrorCode.E3001

    async def test_duplicate_registration(self, registry, sample_tool_definition, sample_tool_manifest):
        """Test duplicate tool registration fails"""
        await registry.register_tool(sample_tool_definition, sample_tool_manifest)

        with pytest.raises(ToolExecutionError) as exc_info:
            await registry.register_tool(sample_tool_definition, sample_tool_manifest)

        assert exc_info.value.code == ErrorCode.E3007

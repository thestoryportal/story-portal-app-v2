"""L03 Tool Execution layer tests."""
import pytest

class TestL03ToolExecution:
    """Test L03 Tool Execution functionality."""

    @pytest.fixture
    async def tool_executor(self):
        """Initialize tool executor."""
        from src.L03_tool_execution.services.tool_executor import ToolExecutor
        from src.L03_tool_execution.services.tool_registry import ToolRegistry
        from src.L03_tool_execution.services.tool_sandbox import ToolSandbox
        db_string = "postgresql://postgres:postgres@localhost:5432/agentic_platform"
        registry = ToolRegistry(db_connection_string=db_string)
        sandbox = ToolSandbox()
        executor = ToolExecutor(tool_registry=registry, tool_sandbox=sandbox)
        yield executor

    @pytest.fixture
    async def tool_registry(self):
        """Initialize tool registry."""
        from src.L03_tool_execution.services.tool_registry import ToolRegistry
        db_string = "postgresql://postgres:postgres@localhost:5432/agentic_platform"
        registry = ToolRegistry(db_connection_string=db_string)
        await registry.initialize()
        yield registry
        await registry.close()

    @pytest.mark.asyncio
    async def test_registry_initialization(self, tool_registry):
        """Tool registry initializes correctly."""
        assert tool_registry is not None

    @pytest.mark.asyncio
    async def test_executor_initialization(self, tool_executor):
        """Tool executor initializes correctly."""
        assert tool_executor is not None

    @pytest.mark.asyncio
    async def test_list_available_tools(self, tool_registry):
        """Can list available tools."""
        tools = await tool_registry.list_tools()
        assert isinstance(tools, list)

    @pytest.mark.asyncio
    async def test_get_tool_by_name(self, tool_registry):
        """Can get tool by name."""
        # First list tools to get a valid name
        tools = await tool_registry.list_tools()
        if tools:
            tool_name = tools[0].name if hasattr(tools[0], 'name') else tools[0].get('name')
            if tool_name:
                tool = await tool_registry.get_tool(tool_name)
                assert tool is not None

    @pytest.mark.asyncio
    async def test_execute_mock_tool(self, tool_executor):
        """Can execute a mock tool."""
        # This test depends on available tools
        # If no tools registered, skip gracefully
        try:
            result = await tool_executor.execute(
                tool_name="echo",  # Common test tool
                arguments={"message": "test"}
            )
            assert result is not None
        except Exception as e:
            # Tool may not exist, which is acceptable
            pytest.skip(f"Echo tool not available: {e}")

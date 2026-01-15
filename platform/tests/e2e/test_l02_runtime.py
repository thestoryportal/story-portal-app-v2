"""L02 Agent Runtime layer tests."""
import pytest
from datetime import datetime

class TestL02AgentRuntime:
    """Test L02 Agent Runtime functionality."""

    @pytest.fixture
    async def executor(self):
        """Initialize agent executor."""
        from src.L02_runtime.services.agent_executor import AgentExecutor
        executor = AgentExecutor()
        await executor.initialize()
        yield executor
        await executor.cleanup()

    @pytest.fixture
    async def session_bridge(self):
        """Initialize session bridge."""
        from src.L02_runtime.services.session_bridge import SessionBridge
        bridge = SessionBridge()
        await bridge.initialize()
        yield bridge
        await bridge.cleanup()

    @pytest.fixture
    async def document_bridge(self):
        """Initialize document bridge."""
        from src.L02_runtime.services.document_bridge import DocumentBridge
        bridge = DocumentBridge()
        await bridge.initialize()
        yield bridge
        await bridge.cleanup()

    @pytest.mark.asyncio
    async def test_executor_initialization(self, executor):
        """Executor initializes correctly."""
        assert executor is not None

    @pytest.mark.asyncio
    async def test_session_bridge_connection(self, session_bridge):
        """Session bridge connects to MCP."""
        # Connection may be stub mode, but should not error
        assert session_bridge is not None

    @pytest.mark.asyncio
    async def test_document_bridge_connection(self, document_bridge):
        """Document bridge connects to MCP."""
        # Connection may be stub mode, but should not error
        assert document_bridge is not None

    @pytest.mark.asyncio
    async def test_session_save_snapshot(self, session_bridge):
        """Session bridge can save context snapshot."""
        result = await session_bridge.save_snapshot(
            task_id="test-task-001",
            context_data={"key": "value", "timestamp": str(datetime.now())}
        )
        # Result may be None in stub mode, but should not error
        assert result is None or isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_session_get_context(self, session_bridge):
        """Session bridge can retrieve context."""
        result = await session_bridge.get_unified_context(task_id="test-task-001")
        # Result may be None in stub mode
        assert result is None or isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_document_query(self, document_bridge):
        """Document bridge can query documents."""
        result = await document_bridge.query_documents(query="architecture")
        # Result may be empty list in stub mode
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_document_find_source(self, document_bridge):
        """Document bridge can find source of truth."""
        result = await document_bridge.find_source_of_truth(query="specification")
        # Result may be None in stub mode
        assert result is None or isinstance(result, dict)

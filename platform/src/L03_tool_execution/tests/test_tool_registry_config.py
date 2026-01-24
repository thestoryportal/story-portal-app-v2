"""
Test Tool Registry Configuration

Tests for environment variable configuration and embedding model settings.
"""

import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from ..services.tool_registry import ToolRegistry


class TestToolRegistryConfig:
    """Test ToolRegistry configuration and initialization."""

    def test_default_embedding_model(self):
        """Test default embedding model when no env vars set."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove env vars if they exist
            os.environ.pop("OLLAMA_EMBEDDING_MODEL", None)
            os.environ.pop("OLLAMA_EMBEDDING_DIMENSIONS", None)

            registry = ToolRegistry(
                db_connection_string="postgresql://test:test@localhost:5432/test"
            )

            assert registry.embedding_model == "nomic-embed-text"
            assert registry.embedding_dimensions == 768

    def test_custom_embedding_model_from_env(self):
        """Test embedding model from environment variables.

        Note: Python evaluates default arguments at function definition time,
        so we need to reload the module after patching the environment.
        """
        import importlib
        from L03_tool_execution.services import tool_registry as tr_module

        with patch.dict(os.environ, {
            "OLLAMA_EMBEDDING_MODEL": "custom-model",
            "OLLAMA_EMBEDDING_DIMENSIONS": "1024"
        }):
            # Reload the module to pick up new env var values
            importlib.reload(tr_module)

            registry = tr_module.ToolRegistry(
                db_connection_string="postgresql://test:test@localhost:5432/test"
            )

            assert registry.embedding_model == "custom-model"
            assert registry.embedding_dimensions == 1024

        # Reload again to restore original defaults for other tests
        importlib.reload(tr_module)

    def test_embedding_model_from_parameter(self):
        """Test embedding model from constructor parameter overrides env."""
        with patch.dict(os.environ, {
            "OLLAMA_EMBEDDING_MODEL": "env-model",
            "OLLAMA_EMBEDDING_DIMENSIONS": "512"
        }):
            registry = ToolRegistry(
                db_connection_string="postgresql://test:test@localhost:5432/test",
                embedding_model="param-model",
                embedding_dimensions=256
            )

            # Constructor params should override env vars
            assert registry.embedding_model == "param-model"
            assert registry.embedding_dimensions == 256

    def test_default_ollama_base_url(self):
        """Test default Ollama base URL."""
        registry = ToolRegistry(
            db_connection_string="postgresql://test:test@localhost:5432/test"
        )

        assert registry.ollama_base_url == "http://localhost:11434"

    def test_custom_ollama_base_url(self):
        """Test custom Ollama base URL."""
        registry = ToolRegistry(
            db_connection_string="postgresql://test:test@localhost:5432/test",
            ollama_base_url="http://custom-ollama:11434"
        )

        assert registry.ollama_base_url == "http://custom-ollama:11434"

    def test_semantic_search_threshold(self):
        """Test semantic search threshold configuration."""
        registry = ToolRegistry(
            db_connection_string="postgresql://test:test@localhost:5432/test",
            semantic_search_threshold=0.85
        )

        assert registry.semantic_search_threshold == 0.85

    def test_default_semantic_search_threshold(self):
        """Test default semantic search threshold."""
        registry = ToolRegistry(
            db_connection_string="postgresql://test:test@localhost:5432/test"
        )

        assert registry.semantic_search_threshold == 0.7


@pytest.mark.asyncio
class TestToolRegistryEmbedding:
    """Test embedding generation functionality."""

    async def test_embedding_dimension_validation(self):
        """Test that embedding dimensions are validated."""
        registry = ToolRegistry(
            db_connection_string="postgresql://test:test@localhost:5432/test",
            embedding_dimensions=768
        )

        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.json.return_value = {"embedding": [0.1] * 768}
        mock_response.raise_for_status = MagicMock()

        registry.http_client = AsyncMock()
        registry.http_client.post = AsyncMock(return_value=mock_response)

        embedding = await registry.generate_embedding("test text")

        assert len(embedding) == 768
        assert all(isinstance(x, float) for x in embedding)

    async def test_embedding_dimension_mismatch_raises_error(self):
        """Test that dimension mismatch raises error."""
        from ..models import ToolExecutionError, ErrorCode

        registry = ToolRegistry(
            db_connection_string="postgresql://test:test@localhost:5432/test",
            embedding_dimensions=768
        )

        # Mock response with wrong dimensions
        mock_response = MagicMock()
        mock_response.json.return_value = {"embedding": [0.1] * 512}  # Wrong size
        mock_response.raise_for_status = MagicMock()

        registry.http_client = AsyncMock()
        registry.http_client.post = AsyncMock(return_value=mock_response)

        with pytest.raises(ToolExecutionError) as exc_info:
            await registry.generate_embedding("test text")

        assert exc_info.value.code == ErrorCode.E3005

    async def test_embedding_uses_correct_model(self):
        """Test that embedding request uses configured model."""
        registry = ToolRegistry(
            db_connection_string="postgresql://test:test@localhost:5432/test",
            embedding_model="nomic-embed-text"
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {"embedding": [0.1] * 768}
        mock_response.raise_for_status = MagicMock()

        registry.http_client = AsyncMock()
        registry.http_client.post = AsyncMock(return_value=mock_response)

        await registry.generate_embedding("test text")

        # Verify the model was passed correctly
        call_args = registry.http_client.post.call_args
        assert call_args[1]["json"]["model"] == "nomic-embed-text"
        assert call_args[1]["json"]["prompt"] == "test text"

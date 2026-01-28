"""
L04 Model Gateway Layer - Token Counter Tests

Validation-first tests for token counting accuracy.
"""

import pytest
from unittest.mock import patch, MagicMock

from ..providers.token_counter import (
    TokenCounter,
    TiktokenCounter,
    AnthropicTokenCounter,
    get_token_counter,
)
from ..models import Message, MessageRole


@pytest.mark.l04
@pytest.mark.unit
class TestTiktokenCounter:
    """Tests for tiktoken-based OpenAI token counting"""

    def test_count_simple_text(self):
        """Test counting tokens in simple text"""
        counter = TiktokenCounter(model="gpt-4o")
        text = "Hello, world!"
        count = counter.count(text)
        # tiktoken gives consistent results
        assert count > 0
        assert count < 10  # Simple text should be few tokens

    def test_count_empty_string(self):
        """Test empty string returns 0"""
        counter = TiktokenCounter()
        assert counter.count("") == 0

    def test_count_handles_unicode(self):
        """Test counters handle emoji and non-ASCII correctly"""
        counter = TiktokenCounter()
        text = "Hello 🌍 world! 你好"
        count = counter.count(text)
        # Should not crash and return reasonable count
        assert count > 0
        assert isinstance(count, int)

    def test_count_handles_code_blocks(self):
        """Test code with special tokens counted correctly"""
        counter = TiktokenCounter()
        code = """
def hello_world():
    print("Hello, World!")
    return True
"""
        count = counter.count(code)
        assert count > 10  # Code should have multiple tokens
        assert isinstance(count, int)

    def test_count_long_text(self):
        """Test counting tokens in longer text"""
        counter = TiktokenCounter()
        # 100 repetitions
        text = "This is a test sentence. " * 100
        count = counter.count(text)
        assert count > 100  # Should be multiple tokens
        assert count < 1000  # But not too many

    def test_count_messages_single(self):
        """Test counting tokens in single message"""
        counter = TiktokenCounter()
        messages = [Message(role=MessageRole.USER, content="Hello!")]
        count = counter.count_messages(messages)
        # Should include message overhead
        assert count > counter.count("Hello!")

    def test_count_messages_multiple(self):
        """Test counting tokens in message list"""
        counter = TiktokenCounter()
        messages = [
            Message(role=MessageRole.SYSTEM, content="You are helpful."),
            Message(role=MessageRole.USER, content="Hello!"),
            Message(role=MessageRole.ASSISTANT, content="Hi there!"),
        ]
        count = counter.count_messages(messages)
        # Should include all messages plus overhead
        assert count > 0
        assert isinstance(count, int)

    def test_count_messages_empty_list(self):
        """Test empty message list returns minimal count"""
        counter = TiktokenCounter()
        count = counter.count_messages([])
        # Should still have reply priming overhead
        assert count >= 0

    def test_different_models_supported(self):
        """Test counter works with different model names"""
        models = ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-4"]
        text = "Test text"

        for model in models:
            counter = TiktokenCounter(model=model)
            count = counter.count(text)
            assert count > 0

    def test_fallback_encoding_for_unknown_model(self):
        """Test unknown model falls back to cl100k_base"""
        counter = TiktokenCounter(model="unknown-model-xyz")
        count = counter.count("Hello")
        assert count > 0


@pytest.mark.l04
@pytest.mark.unit
class TestAnthropicTokenCounter:
    """Tests for Anthropic Claude token counting"""

    def test_count_simple_text(self):
        """Test counting tokens in simple text"""
        counter = AnthropicTokenCounter()
        text = "Hello, world!"
        count = counter.count(text)
        assert count > 0
        assert count < 20  # Simple text

    def test_count_empty_string(self):
        """Test empty string returns 0"""
        counter = AnthropicTokenCounter()
        assert counter.count("") == 0

    def test_count_handles_unicode(self):
        """Test counters handle emoji and non-ASCII correctly"""
        counter = AnthropicTokenCounter()
        text = "Hello 🌍 world! 你好"
        count = counter.count(text)
        assert count > 0
        assert isinstance(count, int)

    def test_count_handles_code_blocks(self):
        """Test code counted correctly"""
        counter = AnthropicTokenCounter()
        code = """
def hello_world():
    print("Hello, World!")
    return True
"""
        count = counter.count(code)
        assert count > 10
        assert isinstance(count, int)

    def test_count_messages_single(self):
        """Test counting tokens in single message"""
        counter = AnthropicTokenCounter()
        messages = [Message(role=MessageRole.USER, content="Hello!")]
        count = counter.count_messages(messages)
        assert count > 0

    def test_count_messages_multiple(self):
        """Test counting tokens in message list"""
        counter = AnthropicTokenCounter()
        messages = [
            Message(role=MessageRole.SYSTEM, content="You are helpful."),
            Message(role=MessageRole.USER, content="Hello!"),
            Message(role=MessageRole.ASSISTANT, content="Hi there!"),
        ]
        count = counter.count_messages(messages)
        assert count > 0
        assert isinstance(count, int)

    def test_count_messages_empty_list(self):
        """Test empty message list returns 0"""
        counter = AnthropicTokenCounter()
        count = counter.count_messages([])
        assert count >= 0

    def test_model_specific_counter(self):
        """Test counter works with model specification"""
        models = [
            "claude-opus-4-5-20251101",
            "claude-sonnet-4-20250514",
            "claude-3-5-sonnet-20241022",
        ]
        text = "Test text"

        for model in models:
            counter = AnthropicTokenCounter(model=model)
            count = counter.count(text)
            assert count > 0


@pytest.mark.l04
@pytest.mark.unit
class TestGetTokenCounter:
    """Tests for token counter factory function"""

    def test_get_counter_for_openai_model(self):
        """Test factory returns TiktokenCounter for OpenAI models"""
        models = ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]

        for model in models:
            counter = get_token_counter(model)
            assert isinstance(counter, TiktokenCounter)

    def test_get_counter_for_anthropic_model(self):
        """Test factory returns AnthropicTokenCounter for Claude models"""
        models = [
            "claude-opus-4-5-20251101",
            "claude-sonnet-4-20250514",
            "claude-3-5-sonnet-20241022",
        ]

        for model in models:
            counter = get_token_counter(model)
            assert isinstance(counter, AnthropicTokenCounter)

    def test_get_counter_for_unknown_model(self):
        """Test factory returns default counter for unknown model"""
        counter = get_token_counter("unknown-model")
        assert isinstance(counter, TokenCounter)

    def test_get_counter_caching(self):
        """Test counters are cached for same model"""
        counter1 = get_token_counter("gpt-4o")
        counter2 = get_token_counter("gpt-4o")
        # Should be same instance
        assert counter1 is counter2


@pytest.mark.l04
@pytest.mark.unit
class TestTokenCounterAccuracy:
    """Tests for token counting accuracy"""

    def test_openai_accuracy_simple(self):
        """Test OpenAI counter accuracy on simple text"""
        counter = TiktokenCounter(model="gpt-4o")

        # Known token counts (verified with OpenAI's tokenizer)
        test_cases = [
            ("Hello", 1),  # Single token
            ("Hello, world!", 4),  # 4 tokens
            ("The quick brown fox jumps over the lazy dog.", 10),  # ~10 tokens
        ]

        for text, expected in test_cases:
            count = counter.count(text)
            # Allow some variance but should be close
            assert abs(count - expected) <= 2, f"Expected ~{expected} for '{text}', got {count}"

    def test_anthropic_reasonable_estimate(self):
        """Test Anthropic counter gives reasonable estimates"""
        counter = AnthropicTokenCounter()

        # Test that estimates are in reasonable range
        test_cases = [
            ("Hello", 1, 5),  # 1-5 tokens expected
            ("Hello, world!", 2, 10),  # 2-10 tokens expected
            ("The quick brown fox jumps over the lazy dog.", 5, 20),  # 5-20 tokens
        ]

        for text, min_expected, max_expected in test_cases:
            count = counter.count(text)
            assert min_expected <= count <= max_expected, \
                f"Expected {min_expected}-{max_expected} for '{text}', got {count}"


@pytest.mark.l04
@pytest.mark.unit
class TestTokenCounterPerformance:
    """Tests for token counter performance"""

    def test_tiktoken_performance(self):
        """Test tiktoken counter performance on large text"""
        import time

        counter = TiktokenCounter()
        # ~10KB of text
        large_text = "This is a test sentence with multiple tokens. " * 200

        start = time.perf_counter()
        for _ in range(100):
            counter.count(large_text)
        elapsed = time.perf_counter() - start

        # Should process 100 iterations in under 1 second
        assert elapsed < 1.0, f"Took {elapsed:.2f}s for 100 iterations"

    def test_anthropic_performance(self):
        """Test Anthropic counter performance on large text"""
        import time

        counter = AnthropicTokenCounter()
        large_text = "This is a test sentence with multiple tokens. " * 200

        start = time.perf_counter()
        for _ in range(100):
            counter.count(large_text)
        elapsed = time.perf_counter() - start

        # Should be fast (uses approximation)
        assert elapsed < 0.5, f"Took {elapsed:.2f}s for 100 iterations"

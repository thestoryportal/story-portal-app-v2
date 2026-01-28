"""
L04 Model Gateway Layer - Token Counter

Accurate token counting for different LLM providers.

Uses tiktoken for OpenAI models and approximation for Anthropic models.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import logging

from ..models import Message, MessageRole

logger = logging.getLogger(__name__)

# Cache for token counters to avoid recreation
_counter_cache: Dict[str, "TokenCounter"] = {}


class TokenCounter(ABC):
    """Abstract base class for token counting"""

    @abstractmethod
    def count(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: The text to count tokens for

        Returns:
            Number of tokens
        """
        pass

    @abstractmethod
    def count_messages(self, messages: List[Message]) -> int:
        """
        Count tokens in message list including overhead.

        Args:
            messages: List of messages to count

        Returns:
            Total token count including message formatting overhead
        """
        pass


class TiktokenCounter(TokenCounter):
    """
    tiktoken-based counter for OpenAI models.

    Uses the official OpenAI tokenizer for accurate counts.
    """

    # Model to encoding mapping
    MODEL_ENCODINGS = {
        "gpt-4o": "o200k_base",
        "gpt-4o-mini": "o200k_base",
        "gpt-4-turbo": "cl100k_base",
        "gpt-4-turbo-2024-04-09": "cl100k_base",
        "gpt-4": "cl100k_base",
        "gpt-4-0613": "cl100k_base",
        "gpt-3.5-turbo": "cl100k_base",
        "gpt-3.5-turbo-0125": "cl100k_base",
        "text-embedding-3-small": "cl100k_base",
        "text-embedding-3-large": "cl100k_base",
        "text-embedding-ada-002": "cl100k_base",
    }

    # Message overhead per message (role + formatting)
    MESSAGE_OVERHEAD = 4  # Tokens per message for GPT-4/4o
    REPLY_PRIMING = 3  # Tokens for assistant reply priming

    def __init__(self, model: str = "gpt-4o"):
        """
        Initialize tiktoken counter.

        Args:
            model: OpenAI model name to use for encoding
        """
        self.model = model
        self._encoding = None
        self._init_encoding()

    def _init_encoding(self) -> None:
        """Initialize the tiktoken encoding"""
        try:
            import tiktoken

            # Try to get encoding for specific model
            encoding_name = self.MODEL_ENCODINGS.get(self.model)

            if encoding_name:
                self._encoding = tiktoken.get_encoding(encoding_name)
            else:
                # Try model-based lookup
                try:
                    self._encoding = tiktoken.encoding_for_model(self.model)
                except KeyError:
                    # Fall back to cl100k_base (GPT-4 encoding)
                    logger.warning(
                        f"Unknown model '{self.model}', using cl100k_base encoding"
                    )
                    self._encoding = tiktoken.get_encoding("cl100k_base")

        except ImportError:
            logger.warning("tiktoken not available, using approximation")
            self._encoding = None

    def count(self, text: str) -> int:
        """
        Count tokens in text using tiktoken.

        Args:
            text: Text to count

        Returns:
            Token count
        """
        if not text:
            return 0

        if self._encoding is None:
            # Fallback to approximation if tiktoken unavailable
            return self._approximate_count(text)

        return len(self._encoding.encode(text))

    def _approximate_count(self, text: str) -> int:
        """
        Approximate token count when tiktoken unavailable.

        Uses ~4 characters per token heuristic.
        """
        return max(1, len(text) // 4)

    def count_messages(self, messages: List[Message]) -> int:
        """
        Count tokens in messages including overhead.

        OpenAI message format overhead:
        - 4 tokens per message (role, content markers, etc.)
        - 3 tokens for reply priming

        Args:
            messages: List of Message objects

        Returns:
            Total token count
        """
        if not messages:
            return self.REPLY_PRIMING

        total = 0

        for msg in messages:
            # Message overhead
            total += self.MESSAGE_OVERHEAD

            # Role token (user/assistant/system)
            total += 1

            # Content tokens
            if msg.content:
                total += self.count(msg.content)

            # Name field if present
            if hasattr(msg, "name") and msg.name:
                total += self.count(msg.name)
                total += 1  # Name formatting

        # Reply priming
        total += self.REPLY_PRIMING

        return total


class AnthropicTokenCounter(TokenCounter):
    """
    Token counter for Anthropic Claude models.

    Anthropic doesn't publish their tokenizer, so we use an approximation
    based on observed behavior. Claude uses a custom tokenizer that
    typically produces ~3.5 characters per token on average.
    """

    # Anthropic message overhead
    MESSAGE_OVERHEAD = 3  # Estimated tokens per message
    HUMAN_TURN_PREFIX = 2  # \n\nHuman: prefix
    ASSISTANT_TURN_PREFIX = 2  # \n\nAssistant: prefix

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize Anthropic token counter.

        Args:
            model: Claude model name (for future model-specific adjustments)
        """
        self.model = model

    def count(self, text: str) -> int:
        """
        Count tokens in text using approximation.

        Claude's tokenizer typically yields ~3.5 characters per token
        for English text. We use 3.3 to be slightly conservative.

        Args:
            text: Text to count

        Returns:
            Approximate token count
        """
        if not text:
            return 0

        # Base approximation: ~3.3 chars per token
        # This is more accurate than 4 chars/token for Claude
        base_count = len(text) / 3.3

        # Adjust for common patterns that affect tokenization
        # Code and special characters often result in more tokens
        special_chars = sum(1 for c in text if not c.isalnum() and not c.isspace())
        adjustment = special_chars * 0.3

        return max(1, int(base_count + adjustment))

    def count_messages(self, messages: List[Message]) -> int:
        """
        Count tokens in messages including Anthropic format overhead.

        Args:
            messages: List of Message objects

        Returns:
            Total token count
        """
        if not messages:
            return 0

        total = 0

        for msg in messages:
            # Turn prefix overhead
            if msg.role == MessageRole.USER:
                total += self.HUMAN_TURN_PREFIX
            elif msg.role == MessageRole.ASSISTANT:
                total += self.ASSISTANT_TURN_PREFIX
            elif msg.role == MessageRole.SYSTEM:
                # System messages have minimal overhead in Anthropic format
                total += 1

            # Content tokens
            if msg.content:
                total += self.count(msg.content)

        return total


def get_token_counter(model: str) -> TokenCounter:
    """
    Factory function to get appropriate token counter for a model.

    Args:
        model: Model ID/name

    Returns:
        TokenCounter instance for the model
    """
    # Check cache first
    if model in _counter_cache:
        return _counter_cache[model]

    # Determine counter type based on model name
    model_lower = model.lower()

    if any(
        prefix in model_lower
        for prefix in ["gpt-4", "gpt-3.5", "gpt4", "text-embedding", "o1-"]
    ):
        counter = TiktokenCounter(model=model)
    elif any(
        prefix in model_lower
        for prefix in ["claude", "anthropic"]
    ):
        counter = AnthropicTokenCounter(model=model)
    else:
        # Default to tiktoken with cl100k_base for unknown models
        logger.info(f"Unknown model '{model}', defaulting to TiktokenCounter")
        counter = TiktokenCounter(model=model)

    # Cache the counter
    _counter_cache[model] = counter

    return counter


def clear_counter_cache() -> None:
    """Clear the token counter cache. Useful for testing."""
    _counter_cache.clear()

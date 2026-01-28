"""
L04 Model Gateway Layer - Mock API Response Data

Provides realistic mock responses from Anthropic and OpenAI APIs
for testing provider adapters.
"""

# =============================================================================
# Anthropic Messages API Responses
# =============================================================================

ANTHROPIC_RESPONSE_SUCCESS = {
    "id": "msg_01XFDUDYJgAACzvnptvVoYEL",
    "type": "message",
    "role": "assistant",
    "content": [
        {
            "type": "text",
            "text": "Hello! I'm Claude, an AI assistant made by Anthropic. How can I help you today?"
        }
    ],
    "model": "claude-sonnet-4-20250514",
    "stop_reason": "end_turn",
    "stop_sequence": None,
    "usage": {
        "input_tokens": 12,
        "output_tokens": 25
    }
}

ANTHROPIC_RESPONSE_WITH_TOOL_USE = {
    "id": "msg_01Aq9w938a90dw8q",
    "type": "message",
    "role": "assistant",
    "content": [
        {
            "type": "tool_use",
            "id": "toolu_01A09q90qw90lq917835lgs",
            "name": "get_weather",
            "input": {"location": "San Francisco, CA"}
        }
    ],
    "model": "claude-sonnet-4-20250514",
    "stop_reason": "tool_use",
    "stop_sequence": None,
    "usage": {
        "input_tokens": 50,
        "output_tokens": 35
    }
}

# Streaming response events (Anthropic SSE format)
ANTHROPIC_RESPONSE_STREAM = [
    {"type": "message_start", "message": {"id": "msg_01XFDUDYJgAACzvnptvVoYEL", "type": "message", "role": "assistant", "content": [], "model": "claude-sonnet-4-20250514", "stop_reason": None, "stop_sequence": None, "usage": {"input_tokens": 12, "output_tokens": 0}}},
    {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
    {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Hello"}},
    {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "! I'm "}},
    {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Claude."}},
    {"type": "content_block_stop", "index": 0},
    {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None}, "usage": {"output_tokens": 8}},
    {"type": "message_stop"}
]

ANTHROPIC_RESPONSE_ERROR_429 = {
    "type": "error",
    "error": {
        "type": "rate_limit_error",
        "message": "Rate limit exceeded. Please try again later."
    }
}

ANTHROPIC_RESPONSE_ERROR_401 = {
    "type": "error",
    "error": {
        "type": "authentication_error",
        "message": "Invalid API key provided."
    }
}

ANTHROPIC_RESPONSE_ERROR_500 = {
    "type": "error",
    "error": {
        "type": "api_error",
        "message": "An internal server error occurred."
    }
}

ANTHROPIC_RESPONSE_ERROR_400 = {
    "type": "error",
    "error": {
        "type": "invalid_request_error",
        "message": "Invalid model specified."
    }
}

# =============================================================================
# OpenAI Chat Completions API Responses
# =============================================================================

OPENAI_RESPONSE_SUCCESS = {
    "id": "chatcmpl-123abc",
    "object": "chat.completion",
    "created": 1677652288,
    "model": "gpt-4o",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Hello! I'm an AI assistant. How can I help you today?"
            },
            "logprobs": None,
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "total_tokens": 30
    }
}

OPENAI_RESPONSE_WITH_FUNCTION_CALL = {
    "id": "chatcmpl-456def",
    "object": "chat.completion",
    "created": 1677652288,
    "model": "gpt-4o",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_abc123",
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "arguments": '{"location": "San Francisco, CA"}'
                        }
                    }
                ]
            },
            "finish_reason": "tool_calls"
        }
    ],
    "usage": {
        "prompt_tokens": 50,
        "completion_tokens": 25,
        "total_tokens": 75
    }
}

# Streaming response chunks (OpenAI SSE format)
OPENAI_RESPONSE_STREAM = [
    {"id": "chatcmpl-123abc", "object": "chat.completion.chunk", "created": 1677652288, "model": "gpt-4o", "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": None}]},
    {"id": "chatcmpl-123abc", "object": "chat.completion.chunk", "created": 1677652288, "model": "gpt-4o", "choices": [{"index": 0, "delta": {"content": "Hello"}, "finish_reason": None}]},
    {"id": "chatcmpl-123abc", "object": "chat.completion.chunk", "created": 1677652288, "model": "gpt-4o", "choices": [{"index": 0, "delta": {"content": "! I'm "}, "finish_reason": None}]},
    {"id": "chatcmpl-123abc", "object": "chat.completion.chunk", "created": 1677652288, "model": "gpt-4o", "choices": [{"index": 0, "delta": {"content": "an AI."}, "finish_reason": None}]},
    {"id": "chatcmpl-123abc", "object": "chat.completion.chunk", "created": 1677652288, "model": "gpt-4o", "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
]

OPENAI_RESPONSE_ERROR_429 = {
    "error": {
        "message": "Rate limit reached for default-gpt-4o in organization org-xxx on requests per min. Limit: 60, Used: 60, Requested: 1.",
        "type": "rate_limit_error",
        "code": "rate_limit_exceeded"
    }
}

OPENAI_RESPONSE_ERROR_401 = {
    "error": {
        "message": "Incorrect API key provided: sk-xxx. You can find your API key at https://platform.openai.com/account/api-keys.",
        "type": "invalid_api_key",
        "code": "invalid_api_key"
    }
}

OPENAI_RESPONSE_ERROR_400 = {
    "error": {
        "message": "The model `gpt-5` does not exist or you do not have access to it.",
        "type": "invalid_request_error",
        "code": "model_not_found"
    }
}

OPENAI_RESPONSE_ERROR_500 = {
    "error": {
        "message": "The server had an error while processing your request.",
        "type": "server_error",
        "code": None
    }
}

# =============================================================================
# Helper Functions
# =============================================================================

def create_anthropic_success_response(
    content: str = "Hello! I'm Claude.",
    model: str = "claude-sonnet-4-20250514",
    input_tokens: int = 12,
    output_tokens: int = 25
) -> dict:
    """Create a custom Anthropic success response"""
    return {
        "id": "msg_01XFDUDYJgAACzvnptvVoYEL",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": content}],
        "model": model,
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens
        }
    }


def create_openai_success_response(
    content: str = "Hello! I'm an AI assistant.",
    model: str = "gpt-4o",
    prompt_tokens: int = 10,
    completion_tokens: int = 20
) -> dict:
    """Create a custom OpenAI success response"""
    return {
        "id": "chatcmpl-123abc",
        "object": "chat.completion",
        "created": 1677652288,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "logprobs": None,
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }
    }

"""
L04 Model Gateway Layer

The Model Gateway Layer provides intelligent routing and execution of LLM inference
requests across multiple providers with caching, rate limiting, and failover.

Key Components:
- Model Registry: Catalog of available models with capabilities
- LLM Router: Intelligent model selection based on requirements
- Semantic Cache: Embedding-based caching for similar prompts
- Rate Limiter: Token bucket rate limiting
- Circuit Breaker: Failover management
- Provider Adapters: Unified interface to multiple LLM providers

Error Codes: E4000-E4999
"""

__version__ = "0.1.0"

from .models import *
from .services import *

__all__ = [
    "__version__"
]

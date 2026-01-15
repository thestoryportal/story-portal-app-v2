"""
L04 Model Gateway Layer - Semantic Cache Service

Embedding-based caching for similar prompts using Redis and vector similarity.
"""

import hashlib
import json
from typing import Optional, List
from datetime import datetime, timedelta
import logging
import asyncio

from ..models import (
    InferenceRequest,
    InferenceResponse,
    CacheError,
    L04ErrorCode
)

logger = logging.getLogger(__name__)


class SemanticCache:
    """
    Semantic cache using embeddings for similarity matching

    Uses Redis for storage and embedding similarity for cache lookups.
    Falls back to exact match if embedding generation fails.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        ttl_seconds: int = 3600,
        similarity_threshold: float = 0.85,
        embedding_model: str = "nomic-embed-text",
        ollama_base_url: str = "http://localhost:11434",
        enable_embeddings: bool = True
    ):
        """
        Initialize semantic cache

        Args:
            redis_url: Redis connection URL
            ttl_seconds: Cache TTL in seconds
            similarity_threshold: Minimum similarity for cache hit (0.0-1.0)
            embedding_model: Model to use for embeddings
            ollama_base_url: Ollama API URL for embeddings
            enable_embeddings: Whether to use embeddings (falls back to exact match)
        """
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        self.similarity_threshold = similarity_threshold
        self.embedding_model = embedding_model
        self.ollama_base_url = ollama_base_url
        self.enable_embeddings = enable_embeddings
        self._redis = None
        self._stats = {
            "hits": 0,
            "misses": 0,
            "writes": 0,
            "errors": 0
        }
        logger.info(
            f"SemanticCache initialized (ttl={ttl_seconds}s, "
            f"threshold={similarity_threshold}, embeddings={enable_embeddings})"
        )

    async def get(self, request: InferenceRequest) -> Optional[InferenceResponse]:
        """
        Get cached response for request

        Args:
            request: InferenceRequest to look up

        Returns:
            Cached InferenceResponse if found, None otherwise
        """
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(request)

            # Try exact match first
            redis_client = await self._get_redis_client()
            cached_data = await redis_client.get(f"cache:exact:{cache_key}")

            if cached_data:
                logger.debug(f"Exact cache hit for {request.request_id}")
                self._stats["hits"] += 1
                return self._deserialize_response(cached_data, request.request_id)

            # Try semantic similarity if enabled
            if self.enable_embeddings:
                similar_response = await self._find_similar(request)
                if similar_response:
                    logger.debug(f"Semantic cache hit for {request.request_id}")
                    self._stats["hits"] += 1
                    return similar_response

            # Cache miss
            self._stats["misses"] += 1
            logger.debug(f"Cache miss for {request.request_id}")
            return None

        except Exception as e:
            logger.error(f"Cache get error: {e}")
            self._stats["errors"] += 1
            return None  # Don't fail the request on cache errors

    async def set(
        self,
        request: InferenceRequest,
        response: InferenceResponse
    ) -> None:
        """
        Cache a response

        Args:
            request: Original InferenceRequest
            response: InferenceResponse to cache
        """
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(request)

            # Serialize response
            serialized = self._serialize_response(response)

            # Store in Redis with TTL
            redis_client = await self._get_redis_client()
            await redis_client.setex(
                f"cache:exact:{cache_key}",
                self.ttl_seconds,
                serialized
            )

            # Store embedding for semantic search if enabled
            if self.enable_embeddings:
                await self._store_with_embedding(request, response, cache_key)

            self._stats["writes"] += 1
            logger.debug(f"Cached response for {request.request_id}")

        except Exception as e:
            logger.error(f"Cache set error: {e}")
            self._stats["errors"] += 1
            # Don't fail the request on cache errors

    def _generate_cache_key(self, request: InferenceRequest) -> str:
        """
        Generate cache key from request

        Args:
            request: InferenceRequest

        Returns:
            Cache key string
        """
        # Create a deterministic hash of the request content
        content = {
            "messages": [
                {"role": m.role.value, "content": m.content}
                for m in request.logical_prompt.messages
            ],
            "system_prompt": request.logical_prompt.system_prompt,
            "temperature": request.logical_prompt.temperature,
            "max_tokens": request.logical_prompt.max_tokens,
            "capabilities": sorted(request.requirements.capabilities)
        }

        content_str = json.dumps(content, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()

    def _serialize_response(self, response: InferenceResponse) -> str:
        """Serialize response for storage"""
        return json.dumps(response.to_dict())

    def _deserialize_response(
        self,
        data: str,
        request_id: str
    ) -> InferenceResponse:
        """Deserialize response from storage"""
        from ..models import TokenUsage, ResponseStatus

        response_dict = json.loads(data)

        # Reconstruct TokenUsage
        token_usage = TokenUsage(
            input_tokens=response_dict["token_usage"]["input_tokens"],
            output_tokens=response_dict["token_usage"]["output_tokens"],
            cached_tokens=response_dict["token_usage"]["cached_tokens"]
        )

        # Create response with updated request_id
        return InferenceResponse(
            request_id=request_id,  # Use current request ID
            model_id=response_dict["model_id"],
            provider=response_dict["provider"],
            content=response_dict["content"],
            token_usage=token_usage,
            latency_ms=0,  # Cached response has zero latency
            cached=True,  # Mark as cached
            status=ResponseStatus(response_dict["status"]),
            finish_reason=response_dict.get("finish_reason"),
            metadata=response_dict.get("metadata", {})
        )

    async def _find_similar(
        self,
        request: InferenceRequest
    ) -> Optional[InferenceResponse]:
        """
        Find similar cached responses using embeddings

        Args:
            request: InferenceRequest

        Returns:
            Similar cached response if found
        """
        try:
            # Generate embedding for request
            embedding = await self._generate_embedding(request)
            if not embedding:
                return None

            # Search for similar cached entries
            # TODO: Implement vector similarity search with Redis or SQLite
            # For now, return None (semantic search not fully implemented)
            return None

        except Exception as e:
            logger.error(f"Semantic search error: {e}")
            return None

    async def _store_with_embedding(
        self,
        request: InferenceRequest,
        response: InferenceResponse,
        cache_key: str
    ) -> None:
        """
        Store response with embedding for semantic search

        Args:
            request: Original request
            response: Response to cache
            cache_key: Cache key
        """
        try:
            # Generate embedding
            embedding = await self._generate_embedding(request)
            if not embedding:
                return

            # TODO: Store embedding in vector database
            # For now, just store metadata
            redis_client = await self._get_redis_client()
            await redis_client.hset(
                f"cache:meta:{cache_key}",
                mapping={
                    "request_id": response.request_id,
                    "model_id": response.model_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            await redis_client.expire(f"cache:meta:{cache_key}", self.ttl_seconds)

        except Exception as e:
            logger.error(f"Error storing embedding: {e}")

    async def _generate_embedding(self, request: InferenceRequest) -> Optional[List[float]]:
        """
        Generate embedding for request using Ollama

        Args:
            request: InferenceRequest

        Returns:
            Embedding vector or None if failed
        """
        try:
            import httpx

            # Format prompt for embedding
            prompt = self._format_prompt_for_embedding(request)

            # Call Ollama embeddings API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ollama_base_url}/api/embeddings",
                    json={
                        "model": self.embedding_model,
                        "prompt": prompt
                    },
                    timeout=10
                )
                response.raise_for_status()

                result = response.json()
                return result.get("embedding")

        except Exception as e:
            logger.warning(f"Embedding generation failed: {e}")
            return None

    def _format_prompt_for_embedding(self, request: InferenceRequest) -> str:
        """Format request as text for embedding"""
        parts = []

        if request.logical_prompt.system_prompt:
            parts.append(request.logical_prompt.system_prompt)

        for msg in request.logical_prompt.messages:
            parts.append(f"{msg.role.value}: {msg.content}")

        return "\n".join(parts)

    async def _get_redis_client(self):
        """Get or create Redis client"""
        if self._redis is None:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
            except ImportError:
                logger.error("redis package not installed")
                raise CacheError(
                    L04ErrorCode.E4301_CACHE_UNAVAILABLE,
                    "Redis package not installed"
                )
        return self._redis

    async def clear(self) -> None:
        """Clear all cache entries"""
        try:
            redis_client = await self._get_redis_client()
            # Delete all cache keys
            cursor = 0
            while True:
                cursor, keys = await redis_client.scan(
                    cursor=cursor,
                    match="cache:*",
                    count=100
                )
                if keys:
                    await redis_client.delete(*keys)
                if cursor == 0:
                    break

            logger.info("Cache cleared")
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            raise CacheError(
                L04ErrorCode.E4300_CACHE_ERROR,
                f"Failed to clear cache: {str(e)}"
            )

    def get_stats(self) -> dict:
        """Get cache statistics"""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total_requests) if total_requests > 0 else 0.0

        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "writes": self._stats["writes"],
            "errors": self._stats["errors"],
            "hit_rate": hit_rate,
            "total_requests": total_requests
        }

    async def close(self) -> None:
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
            self._redis = None

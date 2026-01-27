"""
L02 Agent Runtime - Model Gateway Bridge

Bridge to integrate L04 Model Gateway with L02 Agent Runtime.
Allows agents to request LLM inference through the gateway.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ModelGatewayBridge:
    """
    Bridge between L02 Agent Runtime and L04 Model Gateway

    Provides agents with access to LLM inference capabilities
    through the unified model gateway.
    """

    def __init__(self, gateway=None):
        """
        Initialize bridge

        Args:
            gateway: Optional L04 ModelGateway instance (lazy loaded if None)
        """
        self._gateway = gateway
        self._gateway_initialized = False
        logger.info("ModelGatewayBridge initialized")

    async def _ensure_gateway(self):
        """Lazy load gateway if not provided"""
        if self._gateway is None and not self._gateway_initialized:
            try:
                try:
                    from L04_model_gateway.services import ModelGateway
                except ImportError:
                    from src.L04_model_gateway.services import ModelGateway
                self._gateway = ModelGateway()
                self._gateway_initialized = True
                logger.info("Model Gateway lazy loaded successfully")
            except ImportError as e:
                logger.error(f"Failed to import L04 Model Gateway: {e}")
                raise
        return self._gateway

    async def request_inference(
        self,
        agent_did: str,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        capabilities: Optional[List[str]] = None,
        streaming: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Request LLM inference for an agent

        Args:
            agent_did: Agent DID making the request
            messages: List of message dictionaries with 'role' and 'content'
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum output tokens
            capabilities: Required model capabilities
            streaming: Whether to use streaming
            **kwargs: Additional parameters

        Returns:
            Dictionary with inference response
        """
        try:
            gateway = await self._ensure_gateway()

            # Import L04 models
            try:
                from L04_model_gateway.models import (
                    Message,
                    MessageRole,
                    InferenceRequest
                )
            except ImportError:
                from src.L04_model_gateway.models import (
                    Message,
                    MessageRole,
                    InferenceRequest
                )

            # Convert messages to L04 format
            l04_messages = []
            for msg in messages:
                role = MessageRole(msg.get("role", "user"))
                content = msg.get("content", "")
                l04_messages.append(Message(role=role, content=content))

            # Create inference request
            request = InferenceRequest.create(
                agent_did=agent_did,
                messages=l04_messages,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                capabilities=capabilities or ["text"],
                enable_streaming=streaming
            )

            # Execute request
            if streaming:
                # Return streaming generator
                return {
                    "streaming": True,
                    "stream": gateway.stream(request)
                }
            else:
                # Execute non-streaming
                response = await gateway.execute(request)

                return {
                    "streaming": False,
                    "request_id": response.request_id,
                    "model_id": response.model_id,
                    "provider": response.provider,
                    "content": response.content,
                    "token_usage": {
                        "input_tokens": response.token_usage.input_tokens,
                        "output_tokens": response.token_usage.output_tokens,
                        "total_tokens": response.token_usage.total_tokens
                    },
                    "latency_ms": response.latency_ms,
                    "cached": response.cached,
                    "finish_reason": response.finish_reason,
                    "metadata": response.metadata
                }

        except Exception as e:
            logger.error(f"Inference request failed for agent {agent_did}: {e}")
            raise

    async def check_gateway_health(self) -> Dict[str, Any]:
        """
        Check Model Gateway health status

        Returns:
            Health status dictionary
        """
        try:
            gateway = await self._ensure_gateway()
            return await gateway.health_check()
        except Exception as e:
            logger.error(f"Gateway health check failed: {e}")
            return {
                "gateway": "unavailable",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Get list of available models

        Returns:
            List of model dictionaries
        """
        try:
            gateway = await self._ensure_gateway()
            models = gateway.registry.get_available_models()

            return [
                {
                    "model_id": m.model_id,
                    "provider": m.provider,
                    "display_name": m.display_name,
                    "capabilities": m.capabilities.capabilities_list,
                    "context_window": m.context_window,
                    "max_output_tokens": m.max_output_tokens
                }
                for m in models
            ]
        except Exception as e:
            logger.error(f"Failed to get available models: {e}")
            return []

    async def close(self):
        """Cleanup resources"""
        if self._gateway:
            await self._gateway.close()

"""
L03 Tool Execution - Model Gateway Bridge

Bridge to integrate L04 Model Gateway with L03 Tool Execution Layer.
Allows tools to request LLM inference as part of their execution.
"""

import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class ToolModelBridge:
    """
    Bridge between L03 Tool Execution and L04 Model Gateway

    Enables tools to request LLM inference during execution,
    useful for AI-powered tools or tool composition scenarios.
    """

    def __init__(self, gateway=None):
        """
        Initialize bridge

        Args:
            gateway: Optional L04 ModelGateway instance (lazy loaded if None)
        """
        self._gateway = gateway
        self._gateway_initialized = False
        logger.info("ToolModelBridge initialized")

    async def _ensure_gateway(self):
        """Lazy load gateway if not provided"""
        if self._gateway is None and not self._gateway_initialized:
            try:
                from src.L04_model_gateway.services import ModelGateway
                self._gateway = ModelGateway()
                self._gateway_initialized = True
                logger.info("Model Gateway lazy loaded for tool execution")
            except ImportError as e:
                logger.error(f"Failed to import L04 Model Gateway: {e}")
                raise
        return self._gateway

    async def tool_request_inference(
        self,
        tool_id: str,
        agent_did: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        capabilities: Optional[List[str]] = None
    ) -> str:
        """
        Request inference from within a tool execution

        Args:
            tool_id: Tool making the request
            agent_did: Agent DID for rate limiting
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum output tokens
            capabilities: Required model capabilities

        Returns:
            Generated text content
        """
        try:
            gateway = await self._ensure_gateway()

            # Import L04 models
            from src.L04_model_gateway.models import (
                Message,
                MessageRole,
                InferenceRequest
            )

            # Create message
            messages = [Message(role=MessageRole.USER, content=prompt)]

            # Create inference request
            request = InferenceRequest.create(
                agent_did=agent_did,
                messages=messages,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                capabilities=capabilities or ["text"],
                metadata={
                    "tool_id": tool_id,
                    "source": "tool_execution"
                }
            )

            # Execute request
            response = await gateway.execute(request)

            logger.info(
                f"Tool {tool_id} completed inference request "
                f"(model={response.model_id}, tokens={response.token_usage.total_tokens})"
            )

            return response.content

        except Exception as e:
            logger.error(f"Tool inference request failed for {tool_id}: {e}")
            raise

    async def tool_analyze_result(
        self,
        tool_id: str,
        agent_did: str,
        tool_output: str,
        analysis_prompt: str
    ) -> Dict[str, Any]:
        """
        Use LLM to analyze tool execution results

        Args:
            tool_id: Tool that produced the result
            agent_did: Agent DID
            tool_output: Output from tool execution
            analysis_prompt: Prompt for analyzing the output

        Returns:
            Analysis result dictionary
        """
        try:
            # Combine tool output with analysis prompt
            full_prompt = f"{analysis_prompt}\n\nTool Output:\n{tool_output}"

            content = await self.tool_request_inference(
                tool_id=tool_id,
                agent_did=agent_did,
                prompt=full_prompt,
                system_prompt="You are analyzing tool execution results.",
                max_tokens=500
            )

            return {
                "tool_id": tool_id,
                "analysis": content,
                "original_output": tool_output
            }

        except Exception as e:
            logger.error(f"Tool result analysis failed: {e}")
            raise

    async def tool_compose_with_llm(
        self,
        tool_id: str,
        agent_did: str,
        previous_results: List[Dict[str, Any]],
        composition_prompt: str
    ) -> str:
        """
        Use LLM to compose results from multiple tool executions

        Args:
            tool_id: Composing tool ID
            agent_did: Agent DID
            previous_results: List of previous tool results
            composition_prompt: Prompt for composition

        Returns:
            Composed result
        """
        try:
            # Format previous results
            results_text = "\n\n".join([
                f"Tool: {r.get('tool_id', 'unknown')}\nResult: {r.get('output', '')}"
                for r in previous_results
            ])

            full_prompt = f"{composition_prompt}\n\nPrevious Tool Results:\n{results_text}"

            return await self.tool_request_inference(
                tool_id=tool_id,
                agent_did=agent_did,
                prompt=full_prompt,
                system_prompt="You are composing results from multiple tool executions.",
                max_tokens=1000
            )

        except Exception as e:
            logger.error(f"Tool composition failed: {e}")
            raise

    async def close(self):
        """Cleanup resources"""
        if self._gateway:
            await self._gateway.close()

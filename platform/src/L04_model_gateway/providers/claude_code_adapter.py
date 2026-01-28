"""
L04 Model Gateway Layer - Claude Code CLI Provider Adapter

Adapter for Claude Code CLI - invokes the local `claude` command.
This is the primary LLM provider for the platform.
"""

import asyncio
import json
import os
from typing import AsyncIterator, Dict, Any, Optional
from datetime import datetime
import logging

from .base import BaseProviderAdapter
from ..models import (
    InferenceRequest,
    InferenceResponse,
    ProviderHealth,
    ProviderStatus,
    CircuitState,
    StreamChunk,
    TokenUsage,
    ResponseStatus,
    ProviderError,
    L04ErrorCode
)

logger = logging.getLogger(__name__)


class ClaudeCodeAdapter(BaseProviderAdapter):
    """
    Adapter for Claude Code CLI

    Invokes the `claude` command-line tool for LLM inference.
    Supports both synchronous and streaming modes.

    Requirements:
        - Claude Code CLI must be installed and in PATH
        - Valid Anthropic credentials configured in CLI
    """

    def __init__(
        self,
        claude_path: str = "claude",
        timeout: int = 300,
        working_dir: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize Claude Code adapter

        Args:
            claude_path: Path to claude CLI (default: "claude" assumes in PATH)
            timeout: Request timeout in seconds
            working_dir: Working directory for CLI execution
        """
        super().__init__(
            provider_id="claude_code",
            base_url="local://claude-code-cli",
            timeout=timeout,
            **kwargs
        )
        self.claude_path = claude_path
        self.working_dir = working_dir
        self.supported_models = {
            "claude-opus-4-5-20251101",
            "claude-sonnet-4-20250514",
            "opus",  # Alias
            "sonnet",  # Alias
        }
        self._model_aliases = {
            "opus": "claude-opus-4-5-20251101",
            "sonnet": "claude-sonnet-4-20250514",
        }

    def supports_capability(self, capability: str) -> bool:
        """Check if Claude Code supports a capability"""
        supported = {
            "text",
            "streaming",
            "tool_use",
            "vision",
            "json_mode",
            "code_generation",
            "reasoning"
        }
        return capability.lower() in supported

    def supports_model(self, model_id: str) -> bool:
        """Check if Claude Code supports this model"""
        return model_id in self.supported_models

    def _resolve_model(self, model_id: str) -> str:
        """Resolve model alias to full model ID"""
        return self._model_aliases.get(model_id, model_id)

    def _build_prompt(self, request: InferenceRequest) -> str:
        """
        Build prompt string from InferenceRequest

        Args:
            request: InferenceRequest with messages

        Returns:
            Formatted prompt string for CLI
        """
        parts = []

        # Add system prompt if present
        if request.logical_prompt.system_prompt:
            parts.append(f"[System: {request.logical_prompt.system_prompt}]")
            parts.append("")

        # Add conversation messages
        for msg in request.logical_prompt.messages:
            role = msg.role.value.capitalize()
            parts.append(f"{role}: {msg.content}")

        return "\n".join(parts)

    async def complete(
        self,
        request: InferenceRequest,
        model_id: str
    ) -> InferenceResponse:
        """
        Execute completion request via Claude Code CLI

        Args:
            request: InferenceRequest with prompt
            model_id: Model to use

        Returns:
            InferenceResponse with result
        """
        start_time = datetime.utcnow()
        resolved_model = self._resolve_model(model_id)

        try:
            # Build the prompt
            prompt = self._build_prompt(request)

            # Build CLI arguments
            args = [
                self.claude_path,
                "--print",  # Print response and exit
                "--model", resolved_model,
            ]

            # Add max tokens if specified
            if request.logical_prompt.max_tokens:
                args.extend(["--max-tokens", str(request.logical_prompt.max_tokens)])

            self.logger.debug(f"Executing Claude CLI: {' '.join(args)}")

            # Execute subprocess
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir,
                env={**os.environ}
            )

            # Send prompt and wait for response
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=prompt.encode("utf-8")),
                timeout=self.timeout
            )

            # Check for errors
            if proc.returncode != 0:
                error_msg = stderr.decode("utf-8") if stderr else "Unknown error"
                self.logger.error(f"Claude CLI error (exit {proc.returncode}): {error_msg}")
                raise ProviderError(
                    L04ErrorCode.E4206_PROVIDER_API_ERROR,
                    f"Claude CLI error: {error_msg}",
                    {"exit_code": proc.returncode, "stderr": error_msg}
                )

            # Parse response
            content = stdout.decode("utf-8").strip()

            # Calculate latency
            latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Estimate token usage
            input_tokens = self._estimate_tokens(prompt)
            output_tokens = self._estimate_tokens(content)

            token_usage = TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cached_tokens=0
            )

            return InferenceResponse(
                request_id=request.request_id,
                model_id=resolved_model,
                provider=self.provider_id,
                content=content,
                token_usage=token_usage,
                latency_ms=latency_ms,
                cached=False,
                status=ResponseStatus.SUCCESS,
                finish_reason="stop",
                metadata={
                    "cli_path": self.claude_path,
                    "working_dir": self.working_dir
                }
            )

        except asyncio.TimeoutError:
            self.logger.error(f"Claude CLI timeout after {self.timeout}s")
            raise ProviderError(
                L04ErrorCode.E4202_PROVIDER_TIMEOUT,
                f"Claude CLI timed out after {self.timeout} seconds",
                {"timeout": self.timeout}
            )
        except ProviderError:
            raise
        except Exception as e:
            self.logger.error(f"Claude CLI error: {e}")
            raise ProviderError(
                L04ErrorCode.E4200_PROVIDER_ERROR,
                f"Claude CLI error: {str(e)}",
                {"error": str(e)}
            )

    async def stream(
        self,
        request: InferenceRequest,
        model_id: str
    ) -> AsyncIterator[StreamChunk]:
        """
        Execute streaming completion via Claude Code CLI

        Args:
            request: InferenceRequest with prompt
            model_id: Model to use

        Yields:
            StreamChunk objects with incremental content
        """
        resolved_model = self._resolve_model(model_id)

        try:
            # Build the prompt
            prompt = self._build_prompt(request)

            # Build CLI arguments for streaming
            args = [
                self.claude_path,
                "--output-format", "stream-json",
                "--model", resolved_model,
            ]

            # Add max tokens if specified
            if request.logical_prompt.max_tokens:
                args.extend(["--max-tokens", str(request.logical_prompt.max_tokens)])

            self.logger.debug(f"Executing Claude CLI streaming: {' '.join(args)}")

            # Execute subprocess
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir,
                env={**os.environ}
            )

            # Write prompt to stdin
            proc.stdin.write(prompt.encode("utf-8"))
            await proc.stdin.drain()
            proc.stdin.close()

            # Read streaming output line by line
            total_tokens = 0
            async for line in proc.stdout:
                line_str = line.decode("utf-8").strip()
                if not line_str:
                    continue

                try:
                    chunk_data = json.loads(line_str)

                    # Handle different event types from Claude CLI
                    event_type = chunk_data.get("type", "")

                    if event_type == "content_block_delta":
                        # Content chunk
                        delta = chunk_data.get("delta", {})
                        content_delta = delta.get("text", "")

                        yield StreamChunk(
                            request_id=request.request_id,
                            content_delta=content_delta,
                            is_final=False
                        )

                    elif event_type == "message_delta":
                        # Final message metadata
                        usage = chunk_data.get("usage", {})
                        total_tokens = usage.get("output_tokens", 0)

                    elif event_type == "message_stop":
                        # Stream complete
                        yield StreamChunk(
                            request_id=request.request_id,
                            content_delta="",
                            is_final=True,
                            token_count=total_tokens,
                            finish_reason="stop"
                        )
                        break

                    elif event_type == "error":
                        # Error in stream
                        error_msg = chunk_data.get("error", {}).get("message", "Unknown error")
                        raise ProviderError(
                            L04ErrorCode.E4604_STREAMING_ERROR,
                            f"Claude CLI streaming error: {error_msg}",
                            {"error": error_msg}
                        )

                except json.JSONDecodeError:
                    # Non-JSON line - might be plain text content
                    if line_str:
                        yield StreamChunk(
                            request_id=request.request_id,
                            content_delta=line_str,
                            is_final=False
                        )

            # Wait for process to complete
            await proc.wait()

            if proc.returncode != 0:
                stderr = await proc.stderr.read()
                error_msg = stderr.decode("utf-8") if stderr else "Unknown error"
                raise ProviderError(
                    L04ErrorCode.E4604_STREAMING_ERROR,
                    f"Claude CLI streaming failed: {error_msg}",
                    {"exit_code": proc.returncode}
                )

        except ProviderError:
            raise
        except Exception as e:
            self.logger.error(f"Claude CLI streaming error: {e}")
            raise ProviderError(
                L04ErrorCode.E4604_STREAMING_ERROR,
                f"Claude CLI streaming error: {str(e)}",
                {"error": str(e)}
            )

    async def health_check(self) -> ProviderHealth:
        """
        Check Claude Code CLI health status

        Returns:
            ProviderHealth with current status
        """
        try:
            # Try to run --version as a health check
            proc = await asyncio.create_subprocess_exec(
                self.claude_path,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, _ = await asyncio.wait_for(
                proc.communicate(),
                timeout=5
            )

            if proc.returncode == 0:
                version = stdout.decode("utf-8").strip()
                return ProviderHealth(
                    provider_id=self.provider_id,
                    status=ProviderStatus.HEALTHY,
                    circuit_state=CircuitState.CLOSED,
                    last_check=datetime.utcnow(),
                    consecutive_failures=0,
                    average_latency_ms=None,
                    error_rate=0.0,
                    metadata={"version": version, "cli_path": self.claude_path}
                )
            else:
                return ProviderHealth(
                    provider_id=self.provider_id,
                    status=ProviderStatus.UNHEALTHY,
                    circuit_state=CircuitState.HALF_OPEN,
                    last_check=datetime.utcnow(),
                    consecutive_failures=1,
                    metadata={"error": "CLI returned non-zero exit code"}
                )

        except asyncio.TimeoutError:
            self.logger.warning("Claude CLI health check timed out")
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.UNAVAILABLE,
                circuit_state=CircuitState.OPEN,
                last_check=datetime.utcnow(),
                consecutive_failures=1,
                metadata={"error": "timeout"}
            )
        except FileNotFoundError:
            self.logger.error(f"Claude CLI not found at: {self.claude_path}")
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.UNAVAILABLE,
                circuit_state=CircuitState.OPEN,
                last_check=datetime.utcnow(),
                consecutive_failures=1,
                metadata={"error": f"CLI not found: {self.claude_path}"}
            )
        except Exception as e:
            self.logger.error(f"Claude CLI health check failed: {e}")
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.UNAVAILABLE,
                circuit_state=CircuitState.OPEN,
                last_check=datetime.utcnow(),
                consecutive_failures=1,
                metadata={"error": str(e)}
            )

    async def _create_client(self):
        """Override - no HTTP client needed for CLI adapter"""
        pass

    async def _close_client(self):
        """Override - no HTTP client to close"""
        pass

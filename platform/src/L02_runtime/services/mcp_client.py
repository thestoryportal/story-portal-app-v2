"""
MCP Client

Generic MCP stdio client for tool invocation with MCP servers.
Supports communication with TypeScript MCP servers via JSON-RPC over stdio.

Based on Model Context Protocol specification.
"""

import asyncio
import json
import logging
import os
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def _load_env_file(working_dir: str, base_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Load .env file from working directory and merge with base environment.

    Args:
        working_dir: Directory containing .env file
        base_env: Base environment to merge with (defaults to os.environ.copy())

    Returns:
        Merged environment dictionary
    """
    env = base_env if base_env is not None else os.environ.copy()
    env_file = Path(working_dir) / ".env"

    if env_file.exists():
        logger.debug(f"Loading .env file from: {env_file}")
        try:
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    # Parse KEY=VALUE
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        env[key] = value
            logger.debug(f"Loaded {len(env)} environment variables")
        except Exception as e:
            logger.warning(f"Failed to load .env file: {e}")
    else:
        logger.debug(f"No .env file found at: {env_file}")

    return env


@dataclass
class MCPToolResult:
    """Result from MCP tool invocation"""
    success: bool
    result: Any = None
    error: Optional[str] = None
    tool_name: str = ""
    execution_time_ms: float = 0.0


class MCPClient:
    """
    Generic MCP stdio client for tool invocation.

    Communicates with MCP servers via JSON-RPC over stdio.
    Handles process lifecycle, message framing, and error handling.
    """

    def __init__(
        self,
        server_command: List[str],
        server_name: str = "mcp-server",
        timeout_seconds: int = 30,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None
    ):
        """
        Initialize MCP client.

        Args:
            server_command: Command to start MCP server (e.g., ['node', 'server.js'])
            server_name: Human-readable server name for logging
            timeout_seconds: Default timeout for tool calls
            cwd: Working directory for server process
            env: Environment variables for server process
        """
        self.server_command = server_command
        self.server_name = server_name
        self.timeout_seconds = timeout_seconds
        self.cwd = cwd
        self.env = env

        self.process: Optional[asyncio.subprocess.Process] = None
        self.connected = False
        self.message_id_counter = 0
        self._pending_responses: Dict[str, asyncio.Future] = {}
        self._reader_task: Optional[asyncio.Task] = None
        self._stderr_reader_task: Optional[asyncio.Task] = None
        self._init_event: Optional[asyncio.Event] = None

        logger.info(f"MCPClient initialized for {server_name}")

    async def connect(self) -> bool:
        """
        Start MCP server subprocess and initialize connection.

        Returns:
            True if connection successful, False otherwise
        """
        if self.connected:
            logger.warning(f"{self.server_name} already connected")
            return True

        try:
            logger.info(f"Starting MCP server: {' '.join(self.server_command)}")

            # Load .env file if working directory is specified
            env = self.env
            if self.cwd and not env:
                # Load .env from working directory
                env = _load_env_file(self.cwd)
            elif self.cwd and env:
                # Merge .env with provided env
                env = _load_env_file(self.cwd, env)

            # Start subprocess with stdio pipes
            self.process = await asyncio.create_subprocess_exec(
                *self.server_command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.cwd,
                env=env
            )

            # Create init event for server startup detection
            self._init_event = asyncio.Event()

            # Start background tasks to read responses and stderr
            self._reader_task = asyncio.create_task(self._read_responses())
            self._stderr_reader_task = asyncio.create_task(self._read_stderr())

            # Wait for server initialization (up to 10 seconds)
            logger.debug("Waiting for server initialization...")
            try:
                await asyncio.wait_for(self._init_event.wait(), timeout=10.0)
                logger.debug("Server initialization detected")
            except asyncio.TimeoutError:
                logger.warning("Server initialization timeout, proceeding anyway")

            # Send initialize request
            init_result = await self._send_request(
                method="initialize",
                params={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "L02-runtime",
                        "version": "1.0.0"
                    }
                }
            )

            if init_result:
                self.connected = True
                logger.info(f"MCP server {self.server_name} connected successfully")

                # Send initialized notification
                await self._send_notification("notifications/initialized", {})

                return True
            else:
                logger.error(f"Failed to initialize {self.server_name}")
                await self.disconnect()
                return False

        except FileNotFoundError:
            logger.error(f"Server command not found: {self.server_command[0]}")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to {self.server_name}: {e}")
            await self.disconnect()
            return False

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout_seconds: Optional[int] = None
    ) -> MCPToolResult:
        """
        Invoke MCP tool and return result.

        Args:
            tool_name: Name of tool to invoke
            arguments: Tool arguments
            timeout_seconds: Optional timeout (uses default if not specified)

        Returns:
            MCPToolResult with success status and result/error
        """
        start_time = datetime.now(timezone.utc)
        timeout = timeout_seconds or self.timeout_seconds

        if not self.connected:
            logger.warning(f"Not connected to {self.server_name}, attempting reconnect")
            connected = await self.connect()
            if not connected:
                return MCPToolResult(
                    success=False,
                    error=f"Failed to connect to {self.server_name}",
                    tool_name=tool_name
                )

        try:
            logger.debug(f"Calling tool: {tool_name} with args: {arguments}")

            # Send tools/call request
            result = await self._send_request(
                method="tools/call",
                params={
                    "name": tool_name,
                    "arguments": arguments
                },
                timeout=timeout
            )

            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            if result and "content" in result:
                # Extract content from MCP response
                content = result["content"]
                if isinstance(content, list) and len(content) > 0:
                    # MCP returns content as array of content blocks
                    text_content = content[0].get("text", "")
                    try:
                        # Try to parse as JSON
                        parsed = json.loads(text_content)
                        return MCPToolResult(
                            success=True,
                            result=parsed,
                            tool_name=tool_name,
                            execution_time_ms=execution_time
                        )
                    except json.JSONDecodeError:
                        # Return as string if not JSON
                        return MCPToolResult(
                            success=True,
                            result=text_content,
                            tool_name=tool_name,
                            execution_time_ms=execution_time
                        )
                else:
                    return MCPToolResult(
                        success=True,
                        result=content,
                        tool_name=tool_name,
                        execution_time_ms=execution_time
                    )
            else:
                return MCPToolResult(
                    success=False,
                    error="Invalid response format",
                    tool_name=tool_name,
                    execution_time_ms=execution_time
                )

        except asyncio.TimeoutError:
            logger.error(f"Tool call timeout: {tool_name}")
            return MCPToolResult(
                success=False,
                error=f"Timeout after {timeout}s",
                tool_name=tool_name
            )
        except Exception as e:
            logger.error(f"Tool call failed: {tool_name}: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                tool_name=tool_name
            )

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        List available tools from MCP server.

        Returns:
            List of tool definitions
        """
        if not self.connected:
            await self.connect()

        try:
            result = await self._send_request(method="tools/list", params={})
            if result and "tools" in result:
                return result["tools"]
            return []
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return []

    async def disconnect(self) -> None:
        """Terminate MCP server subprocess and cleanup."""
        logger.info(f"Disconnecting from {self.server_name}")

        self.connected = False

        # Cancel reader tasks
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass

        if self._stderr_reader_task:
            self._stderr_reader_task.cancel()
            try:
                await self._stderr_reader_task
            except asyncio.CancelledError:
                pass

        # Terminate process
        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning(f"Force killing {self.server_name}")
                self.process.kill()
                await self.process.wait()
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")

        self._pending_responses.clear()
        logger.info(f"Disconnected from {self.server_name}")

    async def _send_request(
        self,
        method: str,
        params: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Send JSON-RPC request and wait for response.

        Args:
            method: JSON-RPC method name
            params: Method parameters
            timeout: Optional timeout

        Returns:
            Response result or None
        """
        if not self.process or not self.process.stdin:
            raise RuntimeError("MCP server not started")

        # Generate message ID
        self.message_id_counter += 1
        message_id = str(self.message_id_counter)

        # Create JSON-RPC request
        request = {
            "jsonrpc": "2.0",
            "id": message_id,
            "method": method,
            "params": params
        }

        # Create future for response
        future = asyncio.Future()
        self._pending_responses[message_id] = future

        try:
            # Send request
            request_json = json.dumps(request) + "\n"
            self.process.stdin.write(request_json.encode())
            await self.process.stdin.drain()

            # Wait for response
            timeout_val = timeout or self.timeout_seconds
            result = await asyncio.wait_for(future, timeout=timeout_val)
            return result

        except asyncio.TimeoutError:
            logger.error(f"Request timeout: {method}")
            self._pending_responses.pop(message_id, None)
            raise
        except Exception as e:
            logger.error(f"Request failed: {method}: {e}")
            self._pending_responses.pop(message_id, None)
            raise

    async def _send_notification(self, method: str, params: Dict[str, Any]) -> None:
        """Send JSON-RPC notification (no response expected)."""
        if not self.process or not self.process.stdin:
            return

        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }

        try:
            notification_json = json.dumps(notification) + "\n"
            self.process.stdin.write(notification_json.encode())
            await self.process.stdin.drain()
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

    async def _read_responses(self) -> None:
        """Background task to read responses from server stdout."""
        if not self.process or not self.process.stdout:
            return

        logger.info(f"Starting response reader for {self.server_name}")

        try:
            while self.process:
                # Read line from stdout
                line = await self.process.stdout.readline()

                # Check if stdout is closed (process exited or stream closed)
                if not line:
                    # Check if process is still running
                    if self.process.returncode is not None:
                        logger.warning(f"Server {self.server_name} process exited (code: {self.process.returncode})")
                    else:
                        logger.warning(f"Server {self.server_name} closed stdout")
                    break

                try:
                    # Parse JSON-RPC response
                    response = json.loads(line.decode().strip())

                    # Handle response
                    if "id" in response and response["id"]:
                        message_id = str(response["id"])
                        future = self._pending_responses.pop(message_id, None)

                        if future and not future.done():
                            if "error" in response:
                                error = response["error"]
                                future.set_exception(
                                    Exception(f"MCP error: {error.get('message', 'Unknown error')}")
                                )
                            elif "result" in response:
                                future.set_result(response["result"])
                            else:
                                future.set_result(None)

                    # Handle notifications (no id)
                    elif "method" in response:
                        logger.debug(f"Received notification: {response['method']}")

                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from server: {line}: {e}")
                except Exception as e:
                    logger.error(f"Error processing response: {e}")

        except asyncio.CancelledError:
            logger.info(f"Response reader cancelled for {self.server_name}")
        except Exception as e:
            logger.error(f"Response reader error: {e}")
        finally:
            logger.info(f"Response reader stopped for {self.server_name}")

    async def _read_stderr(self) -> None:
        """Background task to read and log stderr from server."""
        if not self.process or not self.process.stderr:
            return

        logger.debug(f"Starting stderr reader for {self.server_name}")

        try:
            while self.process:
                # Read line from stderr
                line = await self.process.stderr.readline()
                if not line:
                    break

                # Decode stderr output
                stderr_msg = line.decode().strip()
                if not stderr_msg:
                    continue

                # Check for initialization message
                if self._init_event and not self._init_event.is_set():
                    if "initialized" in stderr_msg.lower() or "running on stdio" in stderr_msg.lower():
                        self._init_event.set()
                        logger.debug(f"Server initialization detected: {stderr_msg}")

                # Log stderr output at appropriate level
                if "error" in stderr_msg.lower() or "fail" in stderr_msg.lower():
                    logger.error(f"[{self.server_name}] {stderr_msg}")
                elif "warn" in stderr_msg.lower():
                    logger.warning(f"[{self.server_name}] {stderr_msg}")
                else:
                    logger.debug(f"[{self.server_name}] {stderr_msg}")

        except asyncio.CancelledError:
            logger.debug(f"Stderr reader cancelled for {self.server_name}")
        except Exception as e:
            logger.warning(f"Stderr reader error: {e}")
        finally:
            logger.debug(f"Stderr reader stopped for {self.server_name}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

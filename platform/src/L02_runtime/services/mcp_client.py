"""
MCP Client

Generic MCP stdio client for tool invocation with MCP servers.
Supports communication with TypeScript MCP servers via JSON-RPC over stdio.

Based on Model Context Protocol specification.
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


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
        timeout_seconds: int = 30
    ):
        """
        Initialize MCP client.

        Args:
            server_command: Command to start MCP server (e.g., ['node', 'server.js'])
            server_name: Human-readable server name for logging
            timeout_seconds: Default timeout for tool calls
        """
        self.server_command = server_command
        self.server_name = server_name
        self.timeout_seconds = timeout_seconds

        self.process: Optional[asyncio.subprocess.Process] = None
        self.connected = False
        self.message_id_counter = 0
        self._pending_responses: Dict[str, asyncio.Future] = {}
        self._reader_task: Optional[asyncio.Task] = None

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

            # Start subprocess with stdio pipes
            self.process = await asyncio.create_subprocess_exec(
                *self.server_command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Start background task to read responses
            self._reader_task = asyncio.create_task(self._read_responses())

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

        # Cancel reader task
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
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
            while self.connected and self.process:
                # Read line from stdout
                line = await self.process.stdout.readline()
                if not line:
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

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

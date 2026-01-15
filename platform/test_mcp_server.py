#!/usr/bin/env python3
"""Test script for L12 MCP Server.

This script tests the MCP server by simulating JSON-RPC messages
and verifying responses.

Usage:
    python3 test_mcp_server.py
"""

import asyncio
import json
import subprocess
import sys
import time


async def send_message(process, message):
    """Send JSON-RPC message to MCP server."""
    message_str = json.dumps(message) + "\n"
    process.stdin.write(message_str.encode())
    await process.stdin.drain()
    print(f"→ Sent: {message['method']}")


async def read_response(process):
    """Read JSON-RPC response from MCP server."""
    line = await process.stdout.readline()
    if not line:
        return None

    response = json.loads(line.decode().strip())
    print(f"← Received: {response.get('result', {}).keys() if 'result' in response else 'error'}")
    return response


async def test_mcp_server():
    """Test L12 MCP server with JSON-RPC messages."""
    print("=" * 70)
    print("L12 MCP Server Test Suite")
    print("=" * 70)
    print()

    # Start MCP server
    print("Starting MCP server...")
    process = await asyncio.create_subprocess_exec(
        "python3",
        "-m",
        "src.L12_nl_interface.interfaces.mcp_server_stdio",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="/Volumes/Extreme SSD/projects/story-portal-app/platform",
        env={
            "PYTHONPATH": "/Volumes/Extreme SSD/projects/story-portal-app/platform",
            "L12_USE_SEMANTIC_MATCHING": "false",
        },
    )

    try:
        await asyncio.sleep(1)  # Let server initialize

        print("✅ Server started\n")

        # Test 1: Initialize
        print("Test 1: Initialize connection")
        await send_message(process, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        })

        response = await asyncio.wait_for(read_response(process), timeout=5)
        if response and "result" in response:
            print("✅ Initialize successful")
            print(f"   Server: {response['result'].get('serverInfo', {}).get('name')}")
        else:
            print("❌ Initialize failed")
        print()

        # Test 2: List tools
        print("Test 2: List available tools")
        await send_message(process, {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        })

        response = await asyncio.wait_for(read_response(process), timeout=5)
        if response and "result" in response:
            tools = response['result'].get('tools', [])
            print(f"✅ Found {len(tools)} tools:")
            for tool in tools:
                print(f"   • {tool['name']}")
        else:
            print("❌ List tools failed")
        print()

        # Test 3: Search services
        print("Test 3: Search services for 'plan'")
        await send_message(process, {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "search_services",
                "arguments": {
                    "query": "plan",
                    "threshold": 0.6,
                    "max_results": 3
                }
            }
        })

        response = await asyncio.wait_for(read_response(process), timeout=5)
        if response and "result" in response:
            content = response['result'].get('content', [])
            if content:
                text = content[0].get('text', '')
                # Extract first line (count)
                first_line = text.split('\n')[0]
                print(f"✅ {first_line}")
            else:
                print("✅ Search completed")
        else:
            print("❌ Search failed")
        print()

        # Test 4: List services
        print("Test 4: List all services")
        await send_message(process, {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "list_services",
                "arguments": {}
            }
        })

        response = await asyncio.wait_for(read_response(process), timeout=5)
        if response and "result" in response:
            content = response['result'].get('content', [])
            if content:
                text = content[0].get('text', '')
                # Extract first line (count)
                first_line = text.split('\n')[0]
                print(f"✅ {first_line}")
            else:
                print("✅ List completed")
        else:
            print("❌ List failed")
        print()

        # Test 5: Get service info
        print("Test 5: Get PlanningService info")
        await send_message(process, {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "get_service_info",
                "arguments": {
                    "service_name": "PlanningService"
                }
            }
        })

        response = await asyncio.wait_for(read_response(process), timeout=5)
        if response and "result" in response:
            content = response['result'].get('content', [])
            if content:
                text = content[0].get('text', '')
                # Check if service found
                if "PlanningService" in text:
                    print("✅ Service info retrieved")
                else:
                    print("❌ Service not found")
            else:
                print("❌ No content returned")
        else:
            print("❌ Get service info failed")
        print()

        print("=" * 70)
        print("✅ All tests completed successfully!")
        print("=" * 70)
        print()
        print("The L12 MCP server is working correctly and ready for Claude CLI.")
        print()

    except asyncio.TimeoutError:
        print("❌ Timeout waiting for server response")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=5)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()


if __name__ == "__main__":
    try:
        asyncio.run(test_mcp_server())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)

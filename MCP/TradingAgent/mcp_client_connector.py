import asyncio
import json
import os
from typing import Any, Dict, List, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPClient:
    def __init__(self, server_script_path: str):
        self.server_script_path = server_script_path
        self.session: Optional[ClientSession] = None
        self.exit_stack = None

    async def connect(self):
        server_params = StdioServerParameters(
            command="python",
            args=[self.server_script_path],
            env={**os.environ, "MCP_TYPE": "stdio"}
        )

        # This is a simplified version for demonstration.
        # In a real scenario, you'd use AsyncExitStack to manage the context managers.
        from contextlib import AsyncExitStack
        self.exit_stack = AsyncExitStack()

        _, write = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.session = await self.exit_stack.enter_async_context(ClientSession(_, write))
        await self.session.initialize()

    async def list_tools(self):
        if not self.session:
            raise Exception("Not connected to MCP server")
        return await self.session.list_tools()

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]):
        if not self.session:
            raise Exception("Not connected to MCP server")
        return await self.session.call_tool(tool_name, arguments)

    async def disconnect(self):
        if self.exit_stack:
            await self.exit_stack.aclose()

"""Base MCP Server implementation."""

import json
from abc import ABC, abstractmethod
from typing import Any

from mcp.server import Server
from mcp.types import Tool, TextContent


class BaseMCPServer(ABC):
    """Abstract base class for MCP Servers."""
    
    def __init__(self, name: str):
        """Initialize the MCP Server.
        
        Args:
            name: The server name for identification.
        """
        self.name = name
        self.server = Server(name)
        self._register_handlers()
    
    def _register_handlers(self) -> None:
        """Register MCP protocol handlers."""
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return self.get_tools()
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            return await self.execute_tool(name, arguments)
    
    @abstractmethod
    def get_tools(self) -> list[Tool]:
        """Return the list of tools provided by this server.
        
        Returns:
            List of Tool definitions.
        """
        pass
    
    @abstractmethod
    async def execute_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> list[TextContent]:
        """Execute a tool with the given arguments.
        
        Args:
            name: The tool name to execute.
            arguments: The tool arguments.
            
        Returns:
            List of TextContent with the result.
        """
        pass
    
    def _make_response(self, data: Any) -> list[TextContent]:
        """Create a standard response.
        
        Args:
            data: The data to return (will be JSON serialized if not a string).
            
        Returns:
            List containing a single TextContent.
        """
        if isinstance(data, str):
            text = data
        else:
            text = json.dumps(data, ensure_ascii=False, indent=2)
        return [TextContent(type="text", text=text)]
    
    def _make_error(self, error_code: str, message: str) -> list[TextContent]:
        """Create an error response.
        
        Args:
            error_code: The error code.
            message: The error message.
            
        Returns:
            List containing a single TextContent with error info.
        """
        return self._make_response({
            "error": True,
            "error_code": error_code,
            "message": message
        })
    
    async def run_stdio(self) -> None:
        """Run the server using stdio transport."""
        from mcp.server.stdio import stdio_server
        
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )

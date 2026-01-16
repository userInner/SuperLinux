"""MCP Client implementation for tool discovery and invocation."""

import json
from typing import Any

import jsonschema

from ..common.config import MCPServerConfig
from ..common.exceptions import (
    MCPCommunicationError,
    ParameterValidationError,
    ToolExecutionError,
)
from ..common.models import ToolCall, ToolResult, ToolSchema
from .transport import Transport, create_transport


class MCPClient:
    """Client for communicating with MCP servers."""
    
    def __init__(self, config: MCPServerConfig):
        """Initialize MCP client.
        
        Args:
            config: Server configuration.
        """
        self.config = config
        self.name = config.name
        self._transport: Transport | None = None
        self._tools: dict[str, ToolSchema] = {}
        self._initialized = False
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._transport is not None and self._transport.is_connected
    
    async def connect(self) -> None:
        """Connect to the MCP server and initialize."""
        # Create transport
        transport_config = {
            "transport": self.config.transport,
            "command": self.config.command,
            "args": self.config.args,
            "url": self.config.url,
            "env": self.config.env,
            "timeout": self.config.timeout,
        }
        self._transport = create_transport(transport_config)
        
        # Connect transport
        await self._transport.connect()
        
        # Initialize MCP session
        await self._initialize()
        
        # Discover tools
        await self._discover_tools()
    
    async def _initialize(self) -> None:
        """Send MCP initialize request."""
        response = await self._send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "langgraph-mcp-agent",
                    "version": "0.1.0"
                }
            }
        )
        
        if "error" in response:
            raise MCPCommunicationError(
                self.config.transport,
                response["error"].get("code", "INIT_ERROR"),
                response["error"].get("message", "Initialization failed")
            )
        
        # Send initialized notification
        await self._send_notification("notifications/initialized", {})
        self._initialized = True
    
    async def _discover_tools(self) -> None:
        """Discover available tools from the server."""
        response = await self._send_request("tools/list", {})
        
        if "error" in response:
            raise MCPCommunicationError(
                self.config.transport,
                response["error"].get("code", "TOOLS_ERROR"),
                response["error"].get("message", "Failed to list tools")
            )
        
        tools = response.get("result", {}).get("tools", [])
        
        for tool_data in tools:
            schema = ToolSchema(
                name=tool_data["name"],
                description=tool_data.get("description", ""),
                parameters=tool_data.get("inputSchema", {"type": "object"})
            )
            self._tools[schema.name] = schema
    
    async def _send_request(
        self, method: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Send a JSON-RPC request.
        
        Args:
            method: The RPC method name.
            params: The method parameters.
            
        Returns:
            The JSON-RPC response.
        """
        if not self._transport:
            raise MCPCommunicationError(
                "unknown",
                "NOT_CONNECTED",
                "Client not connected"
            )
        
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        
        return await self._transport.send(message)
    
    async def _send_notification(
        self, method: str, params: dict[str, Any]
    ) -> None:
        """Send a JSON-RPC notification (no response expected).
        
        Args:
            method: The notification method name.
            params: The notification parameters.
        """
        if not self._transport:
            return
        
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        
        # For notifications, we don't wait for response
        # But our transport always expects one, so we handle it
        try:
            await self._transport.send(message)
        except Exception:
            pass  # Notifications don't require response
    
    async def list_tools(self) -> list[ToolSchema]:
        """Get list of available tools.
        
        Returns:
            List of tool schemas.
        """
        if not self._initialized:
            raise MCPCommunicationError(
                self.config.transport,
                "NOT_INITIALIZED",
                "Client not initialized"
            )
        
        return list(self._tools.values())
    
    def get_tool(self, name: str) -> ToolSchema | None:
        """Get a specific tool schema by name.
        
        Args:
            name: The tool name.
            
        Returns:
            The tool schema or None if not found.
        """
        return self._tools.get(name)
    
    def validate_arguments(self, tool_name: str, arguments: dict[str, Any]) -> None:
        """Validate tool arguments against schema.
        
        Args:
            tool_name: The tool name.
            arguments: The arguments to validate.
            
        Raises:
            ParameterValidationError: If validation fails.
        """
        tool = self._tools.get(tool_name)
        if not tool:
            raise ParameterValidationError(
                tool_name,
                "tool",
                f"Unknown tool: {tool_name}"
            )
        
        try:
            jsonschema.validate(arguments, tool.parameters)
        except jsonschema.ValidationError as e:
            raise ParameterValidationError(
                tool_name,
                e.path[-1] if e.path else "unknown",
                e.message
            )
    
    async def call_tool(self, tool_call: ToolCall) -> ToolResult:
        """Call a tool with the given arguments.
        
        Args:
            tool_call: The tool call specification.
            
        Returns:
            The tool result.
        """
        if not self._initialized:
            raise MCPCommunicationError(
                self.config.transport,
                "NOT_INITIALIZED",
                "Client not initialized"
            )
        
        # Validate arguments
        self.validate_arguments(tool_call.name, tool_call.arguments)
        
        # Send tool call request
        response = await self._send_request(
            "tools/call",
            {
                "name": tool_call.name,
                "arguments": tool_call.arguments
            }
        )
        
        if "error" in response:
            error = response["error"]
            return ToolResult(
                tool_call_id=tool_call.id,
                content="",
                is_error=True,
                error_code=str(error.get("code", "UNKNOWN")),
                error_message=error.get("message", "Unknown error")
            )
        
        # Extract content from result
        result = response.get("result", {})
        content_list = result.get("content", [])
        
        # Combine text content
        content_parts = []
        for item in content_list:
            if item.get("type") == "text":
                content_parts.append(item.get("text", ""))
        
        content = "\n".join(content_parts)
        
        # Check if result indicates an error
        is_error = False
        error_code = None
        error_message = None
        
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict) and parsed.get("error"):
                is_error = True
                error_code = parsed.get("error_code")
                error_message = parsed.get("message")
        except (json.JSONDecodeError, TypeError):
            pass
        
        return ToolResult(
            tool_call_id=tool_call.id,
            content=content,
            is_error=is_error,
            error_code=error_code,
            error_message=error_message
        )
    
    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        if self._transport:
            await self._transport.disconnect()
            self._transport = None
        self._tools.clear()
        self._initialized = False


class MCPClientManager:
    """Manages multiple MCP client connections."""
    
    def __init__(self):
        self._clients: dict[str, MCPClient] = {}
    
    async def add_server(self, config: MCPServerConfig) -> MCPClient:
        """Add and connect to an MCP server.
        
        Args:
            config: Server configuration.
            
        Returns:
            The connected client.
        """
        client = MCPClient(config)
        await client.connect()
        self._clients[config.name] = client
        return client
    
    async def remove_server(self, name: str) -> None:
        """Disconnect and remove an MCP server.
        
        Args:
            name: The server name.
        """
        if name in self._clients:
            await self._clients[name].disconnect()
            del self._clients[name]
    
    def get_client(self, name: str) -> MCPClient | None:
        """Get a client by server name.
        
        Args:
            name: The server name.
            
        Returns:
            The client or None if not found.
        """
        return self._clients.get(name)
    
    async def list_all_tools(self) -> list[tuple[str, ToolSchema]]:
        """Get all tools from all connected servers.
        
        Returns:
            List of (server_name, tool_schema) tuples.
        """
        all_tools = []
        for name, client in self._clients.items():
            tools = await client.list_tools()
            for tool in tools:
                all_tools.append((name, tool))
        return all_tools
    
    async def call_tool(
        self, server_name: str, tool_call: ToolCall
    ) -> ToolResult:
        """Call a tool on a specific server.
        
        Args:
            server_name: The server name.
            tool_call: The tool call specification.
            
        Returns:
            The tool result.
        """
        client = self._clients.get(server_name)
        if not client:
            return ToolResult(
                tool_call_id=tool_call.id,
                content="",
                is_error=True,
                error_code="SERVER_NOT_FOUND",
                error_message=f"Server '{server_name}' not found"
            )
        
        return await client.call_tool(tool_call)
    
    async def disconnect_all(self) -> None:
        """Disconnect from all servers."""
        for client in self._clients.values():
            await client.disconnect()
        self._clients.clear()

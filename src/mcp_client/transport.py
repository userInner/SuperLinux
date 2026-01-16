"""Transport layer for MCP client communication."""

import asyncio
import json
import subprocess
from abc import ABC, abstractmethod
from typing import Any

import aiohttp

from ..common.exceptions import (
    ConnectionTimeoutError,
    MCPCommunicationError,
    ServerNotFoundError,
)


class Transport(ABC):
    """Abstract base class for MCP transport."""
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the MCP server."""
        pass
    
    @abstractmethod
    async def send(self, message: dict[str, Any]) -> dict[str, Any]:
        """Send a JSON-RPC message and receive response.
        
        Args:
            message: The JSON-RPC message to send.
            
        Returns:
            The JSON-RPC response.
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close the connection."""
        pass
    
    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if transport is connected."""
        pass


class StdioTransport(Transport):
    """Transport using stdio (subprocess) communication."""
    
    def __init__(
        self,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
        timeout: float = 30.0
    ):
        """Initialize stdio transport.
        
        Args:
            command: The command to run.
            args: Command arguments.
            env: Environment variables.
            timeout: Communication timeout in seconds.
        """
        self.command = command
        self.args = args or []
        self.env = env
        self.timeout = timeout
        self.process: asyncio.subprocess.Process | None = None
        self._request_id = 0
    
    @property
    def is_connected(self) -> bool:
        return self.process is not None and self.process.returncode is None
    
    async def connect(self) -> None:
        """Start the subprocess."""
        import os
        
        # Merge environment
        full_env = os.environ.copy()
        if self.env:
            full_env.update(self.env)
        
        try:
            self.process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=full_env
            )
        except FileNotFoundError:
            raise ServerNotFoundError("stdio", self.command)
        except Exception as e:
            raise MCPCommunicationError("stdio", "SPAWN_ERROR", str(e))
    
    async def send(self, message: dict[str, Any]) -> dict[str, Any]:
        """Send message via stdin and read response from stdout."""
        if not self.is_connected:
            raise MCPCommunicationError("stdio", "NOT_CONNECTED", "Transport not connected")
        
        assert self.process is not None
        assert self.process.stdin is not None
        assert self.process.stdout is not None
        
        # Add request ID if not present
        if "id" not in message:
            self._request_id += 1
            message["id"] = self._request_id
        
        # Ensure jsonrpc version
        message["jsonrpc"] = "2.0"
        
        # Serialize and send
        data = json.dumps(message) + "\n"
        self.process.stdin.write(data.encode("utf-8"))
        await self.process.stdin.drain()
        
        # Read response with timeout
        try:
            response_line = await asyncio.wait_for(
                self.process.stdout.readline(),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            raise ConnectionTimeoutError("stdio", self.timeout)
        
        if not response_line:
            raise MCPCommunicationError("stdio", "EOF", "Server closed connection")
        
        try:
            response = json.loads(response_line.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise MCPCommunicationError("stdio", "PARSE_ERROR", f"Invalid JSON: {e}")
        
        return response
    
    async def disconnect(self) -> None:
        """Terminate the subprocess."""
        if self.process:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
            self.process = None


class HTTPTransport(Transport):
    """Transport using HTTP/SSE communication."""
    
    def __init__(
        self,
        base_url: str,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0
    ):
        """Initialize HTTP transport.
        
        Args:
            base_url: The base URL of the MCP server.
            headers: Additional HTTP headers.
            timeout: Request timeout in seconds.
        """
        self.base_url = base_url.rstrip("/")
        self.headers = headers or {}
        self.timeout = timeout
        self.session: aiohttp.ClientSession | None = None
        self._request_id = 0
    
    @property
    def is_connected(self) -> bool:
        return self.session is not None and not self.session.closed
    
    async def connect(self) -> None:
        """Create HTTP session."""
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        
        # Test connection
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status >= 500:
                    raise MCPCommunicationError(
                        "http",
                        "SERVER_ERROR",
                        f"Server returned {response.status}"
                    )
        except aiohttp.ClientConnectorError as e:
            await self.session.close()
            self.session = None
            raise ServerNotFoundError("http", self.base_url)
        except aiohttp.ServerTimeoutError:
            await self.session.close()
            self.session = None
            raise ConnectionTimeoutError("http", self.timeout)
    
    async def send(self, message: dict[str, Any]) -> dict[str, Any]:
        """Send message via HTTP POST."""
        if not self.is_connected:
            raise MCPCommunicationError("http", "NOT_CONNECTED", "Transport not connected")
        
        assert self.session is not None
        
        # Add request ID if not present
        if "id" not in message:
            self._request_id += 1
            message["id"] = self._request_id
        
        # Ensure jsonrpc version
        message["jsonrpc"] = "2.0"
        
        try:
            async with self.session.post(
                f"{self.base_url}/rpc",
                json=message
            ) as response:
                if response.status >= 400:
                    text = await response.text()
                    raise MCPCommunicationError(
                        "http",
                        f"HTTP_{response.status}",
                        text[:500]
                    )
                
                return await response.json()
                
        except aiohttp.ServerTimeoutError:
            raise ConnectionTimeoutError("http", self.timeout)
        except aiohttp.ClientError as e:
            raise MCPCommunicationError("http", "REQUEST_ERROR", str(e))
    
    async def disconnect(self) -> None:
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None


def create_transport(config: dict[str, Any]) -> Transport:
    """Factory function to create appropriate transport.
    
    Args:
        config: Transport configuration with 'transport' key.
        
    Returns:
        Configured Transport instance.
    """
    transport_type = config.get("transport", "stdio")
    
    if transport_type == "stdio":
        return StdioTransport(
            command=config["command"],
            args=config.get("args", []),
            env=config.get("env"),
            timeout=config.get("timeout", 30.0)
        )
    elif transport_type == "http":
        return HTTPTransport(
            base_url=config["url"],
            headers=config.get("headers"),
            timeout=config.get("timeout", 30.0)
        )
    else:
        raise ValueError(f"Unknown transport type: {transport_type}")

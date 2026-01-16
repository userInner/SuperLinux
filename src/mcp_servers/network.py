"""Network MCP Server - provides HTTP request capabilities."""

from typing import Any

import aiohttp
from mcp.types import Tool, TextContent

from .base import BaseMCPServer


class NetworkServer(BaseMCPServer):
    """MCP Server for network/HTTP operations."""
    
    def __init__(self, timeout: float = 30.0):
        """Initialize the network server.
        
        Args:
            timeout: Default timeout for HTTP requests in seconds.
        """
        super().__init__("network")
        self.default_timeout = timeout
    
    def get_tools(self) -> list[Tool]:
        """Return network tools."""
        return [
            Tool(
                name="fetch_api",
                description="发起 HTTP 请求到指定 URL",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "请求的 URL"
                        },
                        "method": {
                            "type": "string",
                            "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                            "description": "HTTP 方法",
                            "default": "GET"
                        },
                        "headers": {
                            "type": "object",
                            "description": "请求头",
                            "additionalProperties": {"type": "string"}
                        },
                        "body": {
                            "type": "string",
                            "description": "请求体（用于 POST/PUT/PATCH）"
                        },
                        "json_body": {
                            "type": "object",
                            "description": "JSON 请求体（会自动设置 Content-Type）"
                        },
                        "timeout": {
                            "type": "number",
                            "description": "超时时间（秒）"
                        }
                    },
                    "required": ["url"]
                }
            ),
            Tool(
                name="check_url",
                description="检查 URL 是否可访问",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "要检查的 URL"
                        },
                        "timeout": {
                            "type": "number",
                            "description": "超时时间（秒）",
                            "default": 10
                        }
                    },
                    "required": ["url"]
                }
            )
        ]
    
    async def execute_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> list[TextContent]:
        """Execute a network tool."""
        try:
            if name == "fetch_api":
                return await self._fetch_api(arguments)
            elif name == "check_url":
                return await self._check_url(arguments)
            else:
                return self._make_error("UNKNOWN_TOOL", f"Unknown tool: {name}")
        except Exception as e:
            return self._make_error("EXECUTION_ERROR", str(e))
    
    async def _fetch_api(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Fetch data from an API endpoint."""
        url = arguments.get("url")
        method = arguments.get("method", "GET").upper()
        headers = arguments.get("headers", {})
        body = arguments.get("body")
        json_body = arguments.get("json_body")
        timeout = arguments.get("timeout", self.default_timeout)
        
        if not url:
            return self._make_error("MISSING_PARAM", "url is required")
        
        if method not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
            return self._make_error("INVALID_METHOD", f"Invalid HTTP method: {method}")
        
        try:
            async with aiohttp.ClientSession() as session:
                request_kwargs: dict[str, Any] = {
                    "timeout": aiohttp.ClientTimeout(total=timeout),
                    "headers": headers
                }
                
                if json_body is not None:
                    request_kwargs["json"] = json_body
                elif body is not None:
                    request_kwargs["data"] = body
                
                async with session.request(method, url, **request_kwargs) as response:
                    # Try to get response body
                    try:
                        response_text = await response.text()
                    except Exception:
                        response_text = None
                    
                    # Try to parse as JSON
                    response_json = None
                    try:
                        response_json = await response.json()
                    except Exception:
                        pass
                    
                    result = {
                        "url": str(response.url),
                        "status_code": response.status,
                        "headers": dict(response.headers),
                        "content_type": response.content_type
                    }
                    
                    if response_json is not None:
                        result["json"] = response_json
                    elif response_text is not None:
                        result["text"] = response_text[:10000]  # Limit response size
                        if len(response_text) > 10000:
                            result["truncated"] = True
                    
                    # Mark as error if status >= 400
                    if response.status >= 400:
                        result["error"] = True
                        result["error_message"] = f"HTTP {response.status}"
                    
                    return self._make_response(result)
                    
        except aiohttp.ClientConnectorError as e:
            return self._make_response({
                "url": url,
                "error": True,
                "status_code": None,
                "error_code": "CONNECTION_ERROR",
                "error_message": str(e)
            })
        except aiohttp.ServerTimeoutError:
            return self._make_response({
                "url": url,
                "error": True,
                "status_code": None,
                "error_code": "TIMEOUT",
                "error_message": f"Request timed out after {timeout}s"
            })
        except Exception as e:
            return self._make_response({
                "url": url,
                "error": True,
                "status_code": None,
                "error_code": "REQUEST_ERROR",
                "error_message": str(e)
            })
    
    async def _check_url(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Check if a URL is accessible."""
        url = arguments.get("url")
        timeout = arguments.get("timeout", 10)
        
        if not url:
            return self._make_error("MISSING_PARAM", "url is required")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(
                    url,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                    allow_redirects=True
                ) as response:
                    return self._make_response({
                        "url": url,
                        "accessible": True,
                        "status_code": response.status,
                        "final_url": str(response.url)
                    })
        except Exception as e:
            return self._make_response({
                "url": url,
                "accessible": False,
                "error": str(e)
            })


# Entry point for running as standalone server
if __name__ == "__main__":
    import asyncio
    
    server = NetworkServer()
    asyncio.run(server.run_stdio())

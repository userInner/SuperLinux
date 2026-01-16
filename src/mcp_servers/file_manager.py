"""File Manager MCP Server - provides sandboxed file operations."""

import os
from pathlib import Path
from typing import Any

from mcp.types import Tool, TextContent

from .base import BaseMCPServer
from ..common.exceptions import SecurityViolationError


class FileManagerServer(BaseMCPServer):
    """MCP Server for sandboxed file management."""
    
    def __init__(self, sandbox_path: str = "/tmp/agent_sandbox"):
        """Initialize the file manager server.
        
        Args:
            sandbox_path: The root directory for all file operations.
        """
        super().__init__("file-manager")
        self.sandbox_path = Path(sandbox_path).resolve()
        # Ensure sandbox directory exists
        self.sandbox_path.mkdir(parents=True, exist_ok=True)
    
    def _validate_path(self, path: str) -> Path:
        """Validate that a path is within the sandbox.
        
        Args:
            path: The path to validate (relative to sandbox).
            
        Returns:
            The resolved absolute path.
            
        Raises:
            SecurityViolationError: If path escapes sandbox.
        """
        # Handle absolute paths by making them relative
        if path.startswith("/"):
            path = path.lstrip("/")
        
        # Resolve the full path
        full_path = (self.sandbox_path / path).resolve()
        
        # Check if path is within sandbox
        try:
            full_path.relative_to(self.sandbox_path)
        except ValueError:
            raise SecurityViolationError(
                "file_operation",
                "PATH_TRAVERSAL",
                f"Path '{path}' escapes sandbox directory"
            )
        
        return full_path
    
    def get_tools(self) -> list[Tool]:
        """Return file management tools."""
        return [
            Tool(
                name="read_file",
                description="读取文件内容（仅限沙盒目录内）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "文件路径（相对于沙盒目录）"
                        },
                        "encoding": {
                            "type": "string",
                            "description": "文件编码",
                            "default": "utf-8"
                        }
                    },
                    "required": ["path"]
                }
            ),
            Tool(
                name="write_file",
                description="写入文件内容（仅限沙盒目录内）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "文件路径（相对于沙盒目录）"
                        },
                        "content": {
                            "type": "string",
                            "description": "要写入的内容"
                        },
                        "encoding": {
                            "type": "string",
                            "description": "文件编码",
                            "default": "utf-8"
                        },
                        "append": {
                            "type": "boolean",
                            "description": "是否追加模式",
                            "default": False
                        }
                    },
                    "required": ["path", "content"]
                }
            ),
            Tool(
                name="list_directory",
                description="列出目录内容（仅限沙盒目录内）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "目录路径（相对于沙盒目录）",
                            "default": "."
                        },
                        "recursive": {
                            "type": "boolean",
                            "description": "是否递归列出",
                            "default": False
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="delete_file",
                description="删除文件（仅限沙盒目录内，需要审批）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "文件路径（相对于沙盒目录）"
                        }
                    },
                    "required": ["path"]
                }
            ),
            Tool(
                name="file_info",
                description="获取文件信息（仅限沙盒目录内）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "文件路径（相对于沙盒目录）"
                        }
                    },
                    "required": ["path"]
                }
            )
        ]
    
    async def execute_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> list[TextContent]:
        """Execute a file management tool."""
        try:
            if name == "read_file":
                return await self._read_file(arguments)
            elif name == "write_file":
                return await self._write_file(arguments)
            elif name == "list_directory":
                return await self._list_directory(arguments)
            elif name == "delete_file":
                return await self._delete_file(arguments)
            elif name == "file_info":
                return await self._file_info(arguments)
            else:
                return self._make_error("UNKNOWN_TOOL", f"Unknown tool: {name}")
        except SecurityViolationError as e:
            return self._make_error("SECURITY_VIOLATION", str(e))
        except Exception as e:
            return self._make_error("EXECUTION_ERROR", str(e))
    
    async def _read_file(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Read file content."""
        path = arguments.get("path")
        encoding = arguments.get("encoding", "utf-8")
        
        if not path:
            return self._make_error("MISSING_PARAM", "path is required")
        
        full_path = self._validate_path(path)
        
        if not full_path.exists():
            return self._make_error("FILE_NOT_FOUND", f"File not found: {path}")
        
        if not full_path.is_file():
            return self._make_error("NOT_A_FILE", f"Not a file: {path}")
        
        try:
            content = full_path.read_text(encoding=encoding)
            return self._make_response({
                "path": path,
                "content": content,
                "size": len(content),
                "encoding": encoding
            })
        except UnicodeDecodeError:
            return self._make_error("ENCODING_ERROR", f"Cannot decode file with {encoding}")
    
    async def _write_file(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Write content to file."""
        path = arguments.get("path")
        content = arguments.get("content")
        encoding = arguments.get("encoding", "utf-8")
        append = arguments.get("append", False)
        
        if not path:
            return self._make_error("MISSING_PARAM", "path is required")
        if content is None:
            return self._make_error("MISSING_PARAM", "content is required")
        
        full_path = self._validate_path(path)
        
        # Ensure parent directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        mode = "a" if append else "w"
        full_path.open(mode, encoding=encoding).write(content)
        
        return self._make_response({
            "path": path,
            "bytes_written": len(content.encode(encoding)),
            "append": append
        })
    
    async def _list_directory(self, arguments: dict[str, Any]) -> list[TextContent]:
        """List directory contents."""
        path = arguments.get("path", ".")
        recursive = arguments.get("recursive", False)
        
        full_path = self._validate_path(path)
        
        if not full_path.exists():
            return self._make_error("DIR_NOT_FOUND", f"Directory not found: {path}")
        
        if not full_path.is_dir():
            return self._make_error("NOT_A_DIR", f"Not a directory: {path}")
        
        entries = []
        
        if recursive:
            for item in full_path.rglob("*"):
                rel_path = item.relative_to(full_path)
                entries.append({
                    "name": str(rel_path),
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None
                })
        else:
            for item in full_path.iterdir():
                entries.append({
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None
                })
        
        return self._make_response({
            "path": path,
            "entries": entries,
            "count": len(entries)
        })
    
    async def _delete_file(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Delete a file (requires approval)."""
        path = arguments.get("path")
        
        if not path:
            return self._make_error("MISSING_PARAM", "path is required")
        
        full_path = self._validate_path(path)
        
        if not full_path.exists():
            return self._make_error("FILE_NOT_FOUND", f"File not found: {path}")
        
        # Return approval request
        return self._make_response({
            "requires_approval": True,
            "operation": "delete_file",
            "path": path,
            "full_path": str(full_path)
        })
    
    async def _file_info(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Get file information."""
        path = arguments.get("path")
        
        if not path:
            return self._make_error("MISSING_PARAM", "path is required")
        
        full_path = self._validate_path(path)
        
        if not full_path.exists():
            return self._make_error("FILE_NOT_FOUND", f"File not found: {path}")
        
        stat = full_path.stat()
        
        return self._make_response({
            "path": path,
            "type": "directory" if full_path.is_dir() else "file",
            "size": stat.st_size,
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "accessed": stat.st_atime,
            "permissions": oct(stat.st_mode)[-3:]
        })


# Entry point for running as standalone server
if __name__ == "__main__":
    import asyncio
    import sys
    
    sandbox = sys.argv[1] if len(sys.argv) > 1 else "/tmp/agent_sandbox"
    server = FileManagerServer(sandbox_path=sandbox)
    asyncio.run(server.run_stdio())

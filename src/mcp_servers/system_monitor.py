"""System Monitor MCP Server - provides system stats tools."""

from typing import Any

import psutil
from mcp.types import Tool, TextContent

from .base import BaseMCPServer


class SystemMonitorServer(BaseMCPServer):
    """MCP Server for system monitoring."""
    
    def __init__(self):
        super().__init__("system-monitor")
    
    def get_tools(self) -> list[Tool]:
        """Return system monitoring tools."""
        return [
            Tool(
                name="get_system_stats",
                description="获取系统状态信息，包括 CPU、内存和磁盘使用情况",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "include_processes": {
                            "type": "boolean",
                            "description": "是否包含进程列表（前10个CPU占用最高的进程）",
                            "default": False
                        },
                        "include_network": {
                            "type": "boolean", 
                            "description": "是否包含网络统计信息",
                            "default": False
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="get_cpu_info",
                description="获取详细的 CPU 信息",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="get_memory_info",
                description="获取详细的内存信息",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="get_disk_info",
                description="获取磁盘使用信息",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "要检查的路径，默认为根目录",
                            "default": "/"
                        }
                    },
                    "required": []
                }
            )
        ]
    
    async def execute_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> list[TextContent]:
        """Execute a system monitoring tool."""
        try:
            if name == "get_system_stats":
                return await self._get_system_stats(arguments)
            elif name == "get_cpu_info":
                return await self._get_cpu_info()
            elif name == "get_memory_info":
                return await self._get_memory_info()
            elif name == "get_disk_info":
                return await self._get_disk_info(arguments)
            else:
                return self._make_error("UNKNOWN_TOOL", f"Unknown tool: {name}")
        except Exception as e:
            return self._make_error("EXECUTION_ERROR", str(e))
    
    async def _get_system_stats(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Get comprehensive system statistics."""
        include_processes = arguments.get("include_processes", False)
        include_network = arguments.get("include_network", False)
        
        # CPU info
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()
        
        # Memory info
        memory = psutil.virtual_memory()
        
        # Disk info
        disk = psutil.disk_usage("/")
        
        result = {
            "cpu_percent": cpu_percent,
            "cpu_count": cpu_count,
            "memory_used": memory.used,
            "memory_total": memory.total,
            "memory_percent": memory.percent,
            "disk_free": disk.free,
            "disk_total": disk.total,
            "disk_percent": disk.percent
        }
        
        if include_processes:
            processes = []
            for proc in sorted(
                psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']),
                key=lambda p: p.info.get('cpu_percent', 0) or 0,
                reverse=True
            )[:10]:
                try:
                    processes.append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "cpu_percent": proc.info['cpu_percent'],
                        "memory_percent": proc.info['memory_percent']
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            result["top_processes"] = processes
        
        if include_network:
            net_io = psutil.net_io_counters()
            result["network"] = {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            }
        
        return self._make_response(result)
    
    async def _get_cpu_info(self) -> list[TextContent]:
        """Get detailed CPU information."""
        cpu_times = psutil.cpu_times()
        cpu_freq = psutil.cpu_freq()
        
        result = {
            "cpu_count_logical": psutil.cpu_count(logical=True),
            "cpu_count_physical": psutil.cpu_count(logical=False),
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "cpu_percent_per_core": psutil.cpu_percent(interval=0.1, percpu=True),
            "cpu_times": {
                "user": cpu_times.user,
                "system": cpu_times.system,
                "idle": cpu_times.idle
            }
        }
        
        if cpu_freq:
            result["cpu_freq"] = {
                "current": cpu_freq.current,
                "min": cpu_freq.min,
                "max": cpu_freq.max
            }
        
        return self._make_response(result)
    
    async def _get_memory_info(self) -> list[TextContent]:
        """Get detailed memory information."""
        virtual = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        result = {
            "virtual": {
                "total": virtual.total,
                "available": virtual.available,
                "used": virtual.used,
                "free": virtual.free,
                "percent": virtual.percent
            },
            "swap": {
                "total": swap.total,
                "used": swap.used,
                "free": swap.free,
                "percent": swap.percent
            }
        }
        
        return self._make_response(result)
    
    async def _get_disk_info(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Get disk usage information."""
        path = arguments.get("path", "/")
        
        try:
            usage = psutil.disk_usage(path)
            partitions = psutil.disk_partitions()
            
            result = {
                "path": path,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": usage.percent,
                "partitions": [
                    {
                        "device": p.device,
                        "mountpoint": p.mountpoint,
                        "fstype": p.fstype
                    }
                    for p in partitions
                ]
            }
            
            return self._make_response(result)
        except FileNotFoundError:
            return self._make_error("PATH_NOT_FOUND", f"Path not found: {path}")


# Entry point for running as standalone server
if __name__ == "__main__":
    import asyncio
    
    server = SystemMonitorServer()
    asyncio.run(server.run_stdio())

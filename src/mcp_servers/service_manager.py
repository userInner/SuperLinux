"""Service Manager MCP Server - manages Linux systemd services."""

import asyncio
import subprocess
from typing import Any

from mcp.types import Tool, TextContent

from .base import BaseMCPServer


class ServiceManagerServer(BaseMCPServer):
    """MCP Server for Linux service management via systemctl."""
    
    # Services that require extra approval
    DANGEROUS_SERVICES = {
        "sshd", "ssh",
        "systemd", "systemd-journald", "systemd-logind",
        "dbus", "dbus-daemon",
        "NetworkManager", "networking",
        "firewalld", "ufw", "iptables",
        "docker", "containerd",
        "cron", "crond",
    }
    
    def __init__(self):
        super().__init__("service-manager")
    
    def get_tools(self) -> list[Tool]:
        """Return service management tools."""
        return [
            Tool(
                name="get_service_status",
                description="获取服务状态",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "service_name": {
                            "type": "string",
                            "description": "服务名称"
                        }
                    },
                    "required": ["service_name"]
                }
            ),
            Tool(
                name="start_service",
                description="启动服务（可能需要审批）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "service_name": {
                            "type": "string",
                            "description": "服务名称"
                        }
                    },
                    "required": ["service_name"]
                }
            ),
            Tool(
                name="stop_service",
                description="停止服务（可能需要审批）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "service_name": {
                            "type": "string",
                            "description": "服务名称"
                        }
                    },
                    "required": ["service_name"]
                }
            ),
            Tool(
                name="restart_service",
                description="重启服务（可能需要审批）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "service_name": {
                            "type": "string",
                            "description": "服务名称"
                        }
                    },
                    "required": ["service_name"]
                }
            ),
            Tool(
                name="list_services",
                description="列出所有服务",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "state": {
                            "type": "string",
                            "enum": ["running", "stopped", "failed", "all"],
                            "description": "过滤服务状态",
                            "default": "all"
                        }
                    },
                    "required": []
                }
            )
        ]
    
    async def execute_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> list[TextContent]:
        """Execute a service management tool."""
        try:
            if name == "get_service_status":
                return await self._get_service_status(arguments)
            elif name == "start_service":
                return await self._manage_service(arguments, "start")
            elif name == "stop_service":
                return await self._manage_service(arguments, "stop")
            elif name == "restart_service":
                return await self._manage_service(arguments, "restart")
            elif name == "list_services":
                return await self._list_services(arguments)
            else:
                return self._make_error("UNKNOWN_TOOL", f"Unknown tool: {name}")
        except Exception as e:
            return self._make_error("EXECUTION_ERROR", str(e))
    
    def _is_dangerous_service(self, service_name: str) -> bool:
        """Check if a service is considered dangerous."""
        # Remove .service suffix if present
        name = service_name.replace(".service", "")
        return name in self.DANGEROUS_SERVICES
    
    async def _run_systemctl(self, *args: str) -> tuple[int, str, str]:
        """Run a systemctl command.
        
        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        proc = await asyncio.create_subprocess_exec(
            "systemctl", *args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        return (
            proc.returncode or 0,
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace")
        )
    
    async def _get_service_status(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Get the status of a service."""
        service_name = arguments.get("service_name")
        
        if not service_name:
            return self._make_error("MISSING_PARAM", "service_name is required")
        
        # Get service status
        returncode, stdout, stderr = await self._run_systemctl(
            "show", service_name,
            "--property=ActiveState,SubState,LoadState,Description,MainPID"
        )
        
        if returncode != 0 and "not found" in stderr.lower():
            return self._make_response({
                "service_name": service_name,
                "status": "unknown",
                "exists": False,
                "error": stderr.strip()
            })
        
        # Parse the output
        properties = {}
        for line in stdout.strip().split("\n"):
            if "=" in line:
                key, value = line.split("=", 1)
                properties[key] = value
        
        active_state = properties.get("ActiveState", "unknown")
        
        # Map to simple status
        if active_state == "active":
            status = "running"
        elif active_state == "inactive":
            status = "stopped"
        elif active_state == "failed":
            status = "failed"
        else:
            status = "unknown"
        
        return self._make_response({
            "service_name": service_name,
            "status": status,
            "exists": True,
            "active_state": active_state,
            "sub_state": properties.get("SubState"),
            "load_state": properties.get("LoadState"),
            "description": properties.get("Description"),
            "main_pid": properties.get("MainPID")
        })
    
    async def _manage_service(
        self, arguments: dict[str, Any], action: str
    ) -> list[TextContent]:
        """Start, stop, or restart a service."""
        service_name = arguments.get("service_name")
        
        if not service_name:
            return self._make_error("MISSING_PARAM", "service_name is required")
        
        # Check if this is a dangerous service
        if self._is_dangerous_service(service_name):
            return self._make_response({
                "requires_approval": True,
                "operation": f"{action}_service",
                "service_name": service_name,
                "reason": "This is a critical system service",
                "warning": f"Modifying {service_name} may affect system stability"
            })
        
        # Execute the action
        returncode, stdout, stderr = await self._run_systemctl(action, service_name)
        
        if returncode != 0:
            return self._make_response({
                "service_name": service_name,
                "action": action,
                "success": False,
                "error": stderr.strip() or stdout.strip()
            })
        
        # Get new status
        status_result = await self._get_service_status({"service_name": service_name})
        
        return self._make_response({
            "service_name": service_name,
            "action": action,
            "success": True,
            "message": f"Service {service_name} {action}ed successfully"
        })
    
    async def _list_services(self, arguments: dict[str, Any]) -> list[TextContent]:
        """List all services."""
        state_filter = arguments.get("state", "all")
        
        # Get list of services
        returncode, stdout, stderr = await self._run_systemctl(
            "list-units", "--type=service", "--all", "--no-pager", "--plain"
        )
        
        if returncode != 0:
            return self._make_error("SYSTEMCTL_ERROR", stderr.strip())
        
        services = []
        lines = stdout.strip().split("\n")
        
        for line in lines[1:]:  # Skip header
            parts = line.split()
            if len(parts) >= 4:
                name = parts[0]
                load = parts[1]
                active = parts[2]
                sub = parts[3]
                
                # Map to simple status
                if active == "active":
                    status = "running"
                elif active == "inactive":
                    status = "stopped"
                elif active == "failed":
                    status = "failed"
                else:
                    status = "unknown"
                
                # Apply filter
                if state_filter != "all" and status != state_filter:
                    continue
                
                services.append({
                    "name": name,
                    "status": status,
                    "load": load,
                    "active": active,
                    "sub": sub
                })
        
        return self._make_response({
            "services": services,
            "count": len(services),
            "filter": state_filter
        })


# Entry point for running as standalone server
if __name__ == "__main__":
    import asyncio
    
    server = ServiceManagerServer()
    asyncio.run(server.run_stdio())

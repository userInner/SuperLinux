"""Direct tool implementations for in-process use."""

import json
from typing import Any

import aiohttp
import psutil

from .common.models import ToolSchema


def get_all_tools() -> list[ToolSchema]:
    """Get all available tool schemas."""
    return [
        # ===== 代码/文件操作工具 =====
        ToolSchema(
            name="read_file",
            description="读取文件内容，支持代码文件、配置文件、日志等",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"},
                    "start_line": {"type": "integer", "description": "起始行号（可选）"},
                    "end_line": {"type": "integer", "description": "结束行号（可选）"}
                },
                "required": ["path"]
            }
        ),
        ToolSchema(
            name="write_file",
            description="写入或创建文件，可用于写代码、配置文件等",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"},
                    "content": {"type": "string", "description": "文件内容"},
                    "mode": {"type": "string", "enum": ["overwrite", "append"], "default": "overwrite"}
                },
                "required": ["path", "content"]
            }
        ),
        ToolSchema(
            name="list_directory",
            description="列出目录内容",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "目录路径", "default": "."},
                    "recursive": {"type": "boolean", "description": "是否递归", "default": False},
                    "max_depth": {"type": "integer", "description": "最大深度", "default": 2}
                },
                "required": []
            }
        ),
        ToolSchema(
            name="create_directory",
            description="创建目录",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "目录路径"}
                },
                "required": ["path"]
            }
        ),
        ToolSchema(
            name="search_in_files",
            description="在文件中搜索内容（类似 grep）",
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "搜索模式（支持正则）"},
                    "path": {"type": "string", "description": "搜索路径", "default": "."},
                    "file_pattern": {"type": "string", "description": "文件名模式，如 *.py", "default": "*"}
                },
                "required": ["pattern"]
            }
        ),
        ToolSchema(
            name="edit_file",
            description="编辑文件的特定部分，替换指定内容",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"},
                    "old_content": {"type": "string", "description": "要替换的原内容"},
                    "new_content": {"type": "string", "description": "新内容"}
                },
                "required": ["path", "old_content", "new_content"]
            }
        ),
        ToolSchema(
            name="run_code",
            description="运行代码文件（Python/Node.js/Bash）",
            parameters={
                "type": "object",
                "properties": {
                    "file": {"type": "string", "description": "代码文件路径"},
                    "args": {"type": "array", "items": {"type": "string"}, "description": "命令行参数"}
                },
                "required": ["file"]
            }
        ),
        # ===== 系统监控工具 =====
        ToolSchema(
            name="get_system_stats",
            description="获取当前系统状态，包括 CPU 使用率、内存使用情况、磁盘空间等",
            parameters={
                "type": "object",
                "properties": {
                    "include_processes": {
                        "type": "boolean",
                        "description": "是否包含进程列表",
                        "default": False
                    }
                },
                "required": []
            }
        ),
        ToolSchema(
            name="get_cpu_info",
            description="获取详细的 CPU 信息",
            parameters={"type": "object", "properties": {}, "required": []}
        ),
        ToolSchema(
            name="get_memory_info",
            description="获取详细的内存信息",
            parameters={"type": "object", "properties": {}, "required": []}
        ),
        ToolSchema(
            name="get_disk_info",
            description="获取磁盘使用信息",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要检查的路径",
                        "default": "/"
                    }
                },
                "required": []
            }
        ),
        ToolSchema(
            name="list_services",
            description="列出系统服务状态",
            parameters={
                "type": "object",
                "properties": {
                    "state": {
                        "type": "string",
                        "enum": ["running", "stopped", "all"],
                        "default": "running"
                    }
                },
                "required": []
            }
        ),
        ToolSchema(
            name="web_search",
            description="使用搜索引擎搜索信息，可以搜索技术文档、教程、问题解答等",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词"
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "返回结果数量",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        ToolSchema(
            name="fetch_webpage",
            description="获取网页内容，用于查看文档、教程等网页的详细内容",
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "要获取的网页 URL"
                    },
                    "max_length": {
                        "type": "integer",
                        "description": "返回内容的最大字符数",
                        "default": 5000
                    }
                },
                "required": ["url"]
            }
        ),
        ToolSchema(
            name="run_command",
            description="执行 Linux 命令并返回结果（仅限安全命令）",
            parameters={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "要执行的命令"
                    }
                },
                "required": ["command"]
            }
        ),
    ]


async def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    """Execute a tool and return the result as JSON string."""
    try:
        # 代码/文件操作
        if name == "read_file":
            return await _read_file(arguments)
        elif name == "write_file":
            return await _write_file(arguments)
        elif name == "list_directory":
            return await _list_directory(arguments)
        elif name == "create_directory":
            return await _create_directory(arguments)
        elif name == "search_in_files":
            return await _search_in_files(arguments)
        elif name == "edit_file":
            return await _edit_file(arguments)
        elif name == "run_code":
            return await _run_code(arguments)
        # 系统监控
        elif name == "get_system_stats":
            return await _get_system_stats(arguments)
        elif name == "get_cpu_info":
            return await _get_cpu_info()
        elif name == "get_memory_info":
            return await _get_memory_info()
        elif name == "get_disk_info":
            return await _get_disk_info(arguments)
        elif name == "list_services":
            return await _list_services(arguments)
        elif name == "web_search":
            return await _web_search(arguments)
        elif name == "fetch_webpage":
            return await _fetch_webpage(arguments)
        elif name == "run_command":
            return await _run_command(arguments)
        else:
            return json.dumps({"error": True, "message": f"Unknown tool: {name}"})
    except Exception as e:
        return json.dumps({"error": True, "message": str(e)})


async def _get_system_stats(arguments: dict[str, Any]) -> str:
    """Get system statistics."""
    include_processes = arguments.get("include_processes", False)
    
    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_count = psutil.cpu_count()
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    
    result = {
        "cpu_percent": cpu_percent,
        "cpu_count": cpu_count,
        "memory_used_gb": round(memory.used / (1024**3), 2),
        "memory_total_gb": round(memory.total / (1024**3), 2),
        "memory_percent": memory.percent,
        "disk_free_gb": round(disk.free / (1024**3), 2),
        "disk_total_gb": round(disk.total / (1024**3), 2),
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
                    "memory_percent": round(proc.info['memory_percent'] or 0, 2)
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        result["top_processes"] = processes
    
    return json.dumps(result, ensure_ascii=False, indent=2)


async def _get_cpu_info() -> str:
    """Get CPU information."""
    cpu_freq = psutil.cpu_freq()
    
    result = {
        "cpu_count_logical": psutil.cpu_count(logical=True),
        "cpu_count_physical": psutil.cpu_count(logical=False),
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "cpu_percent_per_core": psutil.cpu_percent(interval=0.1, percpu=True),
    }
    
    if cpu_freq:
        result["cpu_freq_mhz"] = {
            "current": round(cpu_freq.current, 2),
            "min": round(cpu_freq.min, 2),
            "max": round(cpu_freq.max, 2)
        }
    
    return json.dumps(result, ensure_ascii=False, indent=2)


async def _get_memory_info() -> str:
    """Get memory information."""
    virtual = psutil.virtual_memory()
    swap = psutil.swap_memory()
    
    result = {
        "virtual": {
            "total_gb": round(virtual.total / (1024**3), 2),
            "available_gb": round(virtual.available / (1024**3), 2),
            "used_gb": round(virtual.used / (1024**3), 2),
            "percent": virtual.percent
        },
        "swap": {
            "total_gb": round(swap.total / (1024**3), 2),
            "used_gb": round(swap.used / (1024**3), 2),
            "percent": swap.percent
        }
    }
    
    return json.dumps(result, ensure_ascii=False, indent=2)


async def _get_disk_info(arguments: dict[str, Any]) -> str:
    """Get disk information."""
    path = arguments.get("path", "/")
    
    try:
        usage = psutil.disk_usage(path)
        partitions = psutil.disk_partitions()
        
        result = {
            "path": path,
            "total_gb": round(usage.total / (1024**3), 2),
            "used_gb": round(usage.used / (1024**3), 2),
            "free_gb": round(usage.free / (1024**3), 2),
            "percent": usage.percent,
            "partitions": [
                {
                    "device": p.device,
                    "mountpoint": p.mountpoint,
                    "fstype": p.fstype
                }
                for p in partitions[:5]  # Limit to 5 partitions
            ]
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    except FileNotFoundError:
        return json.dumps({"error": True, "message": f"Path not found: {path}"})


async def _list_services(arguments: dict[str, Any]) -> str:
    """List system services."""
    import asyncio
    import subprocess
    
    state_filter = arguments.get("state", "running")
    
    try:
        proc = await asyncio.create_subprocess_exec(
            "systemctl", "list-units", "--type=service", "--all", "--no-pager", "--plain",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        
        services = []
        lines = stdout.decode("utf-8", errors="replace").strip().split("\n")
        
        for line in lines[1:]:  # Skip header
            parts = line.split()
            if len(parts) >= 4:
                name = parts[0]
                active = parts[2]
                
                if active == "active":
                    status = "running"
                elif active == "inactive":
                    status = "stopped"
                else:
                    status = active
                
                if state_filter == "all" or status == state_filter:
                    services.append({"name": name, "status": status})
        
        return json.dumps({
            "services": services[:20],  # Limit to 20
            "total": len(services),
            "filter": state_filter
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({"error": True, "message": str(e)})



async def _web_search(arguments: dict[str, Any]) -> str:
    """Search the web using DuckDuckGo."""
    query = arguments.get("query", "")
    num_results = arguments.get("num_results", 5)
    
    if not query:
        return json.dumps({"error": True, "message": "Query is required"})
    
    # Use DuckDuckGo HTML search (no API key needed)
    search_url = "https://html.duckduckgo.com/html/"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                search_url,
                data={"q": query},
                headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"},
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                if response.status != 200:
                    return json.dumps({
                        "error": True,
                        "message": f"Search failed with status {response.status}"
                    })
                
                html = await response.text()
                
                # Parse results (simple extraction)
                results = []
                import re
                
                # Find result blocks
                result_pattern = r'<a rel="nofollow" class="result__a" href="([^"]+)"[^>]*>([^<]+)</a>'
                snippet_pattern = r'<a class="result__snippet"[^>]*>([^<]+(?:<[^>]+>[^<]*</[^>]+>)*[^<]*)</a>'
                
                links = re.findall(result_pattern, html)
                snippets = re.findall(snippet_pattern, html)
                
                for i, (url, title) in enumerate(links[:num_results]):
                    result = {
                        "title": title.strip(),
                        "url": url,
                        "snippet": snippets[i].strip() if i < len(snippets) else ""
                    }
                    # Clean HTML tags from snippet
                    result["snippet"] = re.sub(r'<[^>]+>', '', result["snippet"])
                    results.append(result)
                
                return json.dumps({
                    "query": query,
                    "results": results,
                    "count": len(results)
                }, ensure_ascii=False, indent=2)
                
    except Exception as e:
        return json.dumps({"error": True, "message": f"Search error: {str(e)}"})


async def _fetch_webpage(arguments: dict[str, Any]) -> str:
    """Fetch and extract text content from a webpage."""
    url = arguments.get("url", "")
    max_length = arguments.get("max_length", 5000)
    
    if not url:
        return json.dumps({"error": True, "message": "URL is required"})
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"},
                timeout=aiohttp.ClientTimeout(total=20)
            ) as response:
                if response.status != 200:
                    return json.dumps({
                        "error": True,
                        "message": f"Failed to fetch URL: HTTP {response.status}"
                    })
                
                html = await response.text()
                
                # Simple HTML to text conversion
                import re
                
                # Remove script and style elements
                text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
                
                # Remove HTML tags
                text = re.sub(r'<[^>]+>', ' ', text)
                
                # Clean up whitespace
                text = re.sub(r'\s+', ' ', text).strip()
                
                # Decode HTML entities
                import html as html_module
                text = html_module.unescape(text)
                
                # Truncate if needed
                if len(text) > max_length:
                    text = text[:max_length] + "... [truncated]"
                
                return json.dumps({
                    "url": url,
                    "content": text,
                    "length": len(text)
                }, ensure_ascii=False, indent=2)
                
    except Exception as e:
        return json.dumps({"error": True, "message": f"Fetch error: {str(e)}"})


async def _run_command(arguments: dict[str, Any]) -> str:
    """Run a safe Linux command."""
    import asyncio
    import subprocess
    
    command = arguments.get("command", "")
    
    if not command:
        return json.dumps({"error": True, "message": "Command is required"})
    
    # Security: block dangerous commands
    dangerous_patterns = [
        "rm -rf", "rm -r /", "mkfs", "dd if=", "> /dev/",
        "chmod 777 /", "chown", "sudo", "su -",
        "/etc/passwd", "/etc/shadow", "iptables -F",
        "|sh", "|bash", "eval ", "`", "$(",
    ]
    
    for pattern in dangerous_patterns:
        if pattern in command.lower():
            return json.dumps({
                "error": True,
                "message": f"Command blocked for security: contains '{pattern}'"
            })
    
    # Only allow certain safe commands
    safe_prefixes = [
        # 文件操作
        "ls", "cat", "head", "tail", "less", "more", "wc", "file", "stat",
        "cp", "mv", "mkdir", "touch", "rm", "rmdir",
        "find", "locate", "whereis", "which",
        "ln", "readlink", "realpath",
        "tar", "zip", "unzip", "gzip", "gunzip",
        "diff", "cmp", "md5sum", "sha256sum",
        
        # 文本处理
        "grep", "awk", "sed", "sort", "uniq", "cut", "tr", "xargs",
        "echo", "printf", "tee",
        
        # 系统信息
        "df", "du", "free", "top -bn1", "htop", "ps", "uptime", "w",
        "uname", "hostname", "whoami", "id", "pwd", "date", "cal",
        "lscpu", "lsmem", "lsblk", "lspci", "lsusb",
        "env", "printenv", "set",
        
        # 网络
        "ip", "ifconfig", "netstat", "ss", "ping", "traceroute",
        "curl", "wget", "nc", "nslookup", "dig", "host",
        "iptables -L", "route",
        
        # 进程管理
        "kill", "killall", "pkill", "pgrep", "jobs", "bg", "fg", "nohup",
        
        # 服务管理
        "systemctl", "service", "journalctl",
        
        # 包管理
        "apt", "apt-get", "dpkg", "yum", "dnf", "pacman",
        "pip", "pip3", "npm", "yarn", "cargo",
        
        # 开发工具
        "python", "python3", "node", "npm", "npx", "yarn",
        "git", "make", "cmake", "gcc", "g++",
        "java", "javac", "mvn", "gradle",
        
        # Docker
        "docker", "docker-compose",
        
        # 其他
        "cd", "source", "export", "alias", "history", "clear",
        "man", "help", "info", "type",
        "sleep", "time", "timeout", "watch",
        "xdg-open", "open",
    ]
    
    is_safe = any(command.strip().startswith(prefix) for prefix in safe_prefixes)
    
    if not is_safe:
        return json.dumps({
            "error": True,
            "message": f"Command not in allowed list. Safe commands: {', '.join(safe_prefixes[:10])}..."
        })
    
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        
        output = stdout.decode("utf-8", errors="replace")
        error = stderr.decode("utf-8", errors="replace")
        
        # Limit output size
        if len(output) > 10000:
            output = output[:10000] + "\n... [truncated]"
        
        return json.dumps({
            "command": command,
            "exit_code": proc.returncode,
            "stdout": output,
            "stderr": error if error else None
        }, ensure_ascii=False, indent=2)
        
    except asyncio.TimeoutError:
        return json.dumps({"error": True, "message": "Command timed out after 30s"})
    except Exception as e:
        return json.dumps({"error": True, "message": f"Command error: {str(e)}"})


# ===== 代码/文件操作工具实现 =====

import os

# 工作目录（从配置或环境变量读取）
WORKSPACE_ROOT = None


def _get_workspace_root() -> str:
    """获取工作目录，优先从配置文件读取"""
    global WORKSPACE_ROOT
    
    if WORKSPACE_ROOT is not None:
        return WORKSPACE_ROOT
    
    # 尝试从配置文件读取
    for config_path in ["config.yaml", "config.yml"]:
        if os.path.exists(config_path):
            try:
                import yaml
                with open(config_path) as f:
                    data = yaml.safe_load(f)
                workspace = data.get("workspace_path", "~/agent_workspace")
                WORKSPACE_ROOT = os.path.expanduser(workspace)
                return WORKSPACE_ROOT
            except:
                pass
    
    # 回退到环境变量或默认值
    WORKSPACE_ROOT = os.environ.get("AGENT_WORKSPACE", os.path.expanduser("~/agent_workspace"))
    return WORKSPACE_ROOT


def _safe_path(path: str) -> str:
    """确保路径在工作目录内"""
    workspace = _get_workspace_root()
    
    # 创建工作目录
    os.makedirs(workspace, exist_ok=True)
    
    # 处理相对路径
    if not os.path.isabs(path):
        full_path = os.path.normpath(os.path.join(workspace, path))
    else:
        full_path = os.path.normpath(path)
    
    # 安全检查：必须在工作目录内
    if not full_path.startswith(workspace):
        raise ValueError(f"Access denied: path must be within {workspace}")
    
    return full_path


async def _read_file(arguments: dict[str, Any]) -> str:
    """读取文件内容"""
    path = arguments.get("path", "")
    start_line = arguments.get("start_line")
    end_line = arguments.get("end_line")
    
    if not path:
        return json.dumps({"error": True, "message": "Path is required"})
    
    try:
        safe_path = _safe_path(path)
        
        if not os.path.exists(safe_path):
            return json.dumps({"error": True, "message": f"File not found: {path}"})
        
        with open(safe_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        
        # 行号过滤
        if start_line or end_line:
            start = (start_line or 1) - 1
            end = end_line or len(lines)
            lines = lines[start:end]
        
        content = "".join(lines)
        
        # 限制大小
        if len(content) > 50000:
            content = content[:50000] + "\n... [truncated]"
        
        return json.dumps({
            "path": path,
            "content": content,
            "lines": len(lines),
            "size": os.path.getsize(safe_path)
        }, ensure_ascii=False)
        
    except ValueError as e:
        return json.dumps({"error": True, "message": str(e)})
    except Exception as e:
        return json.dumps({"error": True, "message": f"Read error: {str(e)}"})


async def _write_file(arguments: dict[str, Any]) -> str:
    """写入文件"""
    path = arguments.get("path", "")
    content = arguments.get("content", "")
    mode = arguments.get("mode", "overwrite")
    
    if not path:
        return json.dumps({"error": True, "message": "Path is required"})
    
    try:
        safe_path = _safe_path(path)
        
        # 创建父目录
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        
        write_mode = "a" if mode == "append" else "w"
        with open(safe_path, write_mode, encoding="utf-8") as f:
            f.write(content)
        
        return json.dumps({
            "success": True,
            "path": path,
            "full_path": safe_path,
            "size": os.path.getsize(safe_path),
            "mode": mode
        }, ensure_ascii=False)
        
    except ValueError as e:
        return json.dumps({"error": True, "message": str(e)})
    except Exception as e:
        return json.dumps({"error": True, "message": f"Write error: {str(e)}"})


async def _list_directory(arguments: dict[str, Any]) -> str:
    """列出目录内容"""
    path = arguments.get("path", ".")
    recursive = arguments.get("recursive", False)
    max_depth = arguments.get("max_depth", 2)
    
    try:
        safe_path = _safe_path(path)
        
        if not os.path.exists(safe_path):
            return json.dumps({"error": True, "message": f"Directory not found: {path}"})
        
        items = []
        
        def scan_dir(dir_path: str, depth: int = 0):
            if depth > max_depth:
                return
            try:
                for entry in os.scandir(dir_path):
                    rel_path = os.path.relpath(entry.path, safe_path)
                    item = {
                        "name": entry.name,
                        "path": rel_path,
                        "type": "dir" if entry.is_dir() else "file",
                    }
                    if entry.is_file():
                        item["size"] = entry.stat().st_size
                    items.append(item)
                    
                    if recursive and entry.is_dir() and not entry.name.startswith("."):
                        scan_dir(entry.path, depth + 1)
            except PermissionError:
                pass
        
        scan_dir(safe_path)
        
        # 排序：目录在前，然后按名称
        items.sort(key=lambda x: (x["type"] != "dir", x["name"]))
        
        return json.dumps({
            "path": path,
            "items": items[:100],  # 限制数量
            "total": len(items)
        }, ensure_ascii=False, indent=2)
        
    except ValueError as e:
        return json.dumps({"error": True, "message": str(e)})
    except Exception as e:
        return json.dumps({"error": True, "message": f"List error: {str(e)}"})


async def _create_directory(arguments: dict[str, Any]) -> str:
    """创建目录"""
    path = arguments.get("path", "")
    
    if not path:
        return json.dumps({"error": True, "message": "Path is required"})
    
    try:
        safe_path = _safe_path(path)
        os.makedirs(safe_path, exist_ok=True)
        
        return json.dumps({
            "success": True,
            "path": path,
            "full_path": safe_path
        }, ensure_ascii=False)
        
    except ValueError as e:
        return json.dumps({"error": True, "message": str(e)})
    except Exception as e:
        return json.dumps({"error": True, "message": f"Create error: {str(e)}"})


async def _search_in_files(arguments: dict[str, Any]) -> str:
    """在文件中搜索"""
    import re
    import fnmatch
    
    pattern = arguments.get("pattern", "")
    path = arguments.get("path", ".")
    file_pattern = arguments.get("file_pattern", "*")
    
    if not pattern:
        return json.dumps({"error": True, "message": "Pattern is required"})
    
    try:
        safe_path = _safe_path(path)
        results = []
        
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error:
            # 如果不是有效正则，当作普通字符串
            regex = re.compile(re.escape(pattern), re.IGNORECASE)
        
        for root, dirs, files in os.walk(safe_path):
            # 跳过隐藏目录
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            
            for filename in files:
                if not fnmatch.fnmatch(filename, file_pattern):
                    continue
                
                filepath = os.path.join(root, filename)
                rel_path = os.path.relpath(filepath, safe_path)
                
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, 1):
                            if regex.search(line):
                                results.append({
                                    "file": rel_path,
                                    "line": line_num,
                                    "content": line.strip()[:200]
                                })
                                if len(results) >= 50:
                                    break
                except:
                    continue
                
                if len(results) >= 50:
                    break
            
            if len(results) >= 50:
                break
        
        return json.dumps({
            "pattern": pattern,
            "results": results,
            "count": len(results)
        }, ensure_ascii=False, indent=2)
        
    except ValueError as e:
        return json.dumps({"error": True, "message": str(e)})
    except Exception as e:
        return json.dumps({"error": True, "message": f"Search error: {str(e)}"})


async def _edit_file(arguments: dict[str, Any]) -> str:
    """编辑文件（替换内容）"""
    path = arguments.get("path", "")
    old_content = arguments.get("old_content", "")
    new_content = arguments.get("new_content", "")
    
    if not path or not old_content:
        return json.dumps({"error": True, "message": "Path and old_content are required"})
    
    try:
        safe_path = _safe_path(path)
        
        if not os.path.exists(safe_path):
            return json.dumps({"error": True, "message": f"File not found: {path}"})
        
        with open(safe_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        if old_content not in content:
            return json.dumps({
                "error": True,
                "message": "Old content not found in file"
            })
        
        # 替换
        new_file_content = content.replace(old_content, new_content, 1)
        
        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(new_file_content)
        
        return json.dumps({
            "success": True,
            "path": path,
            "message": "File edited successfully"
        }, ensure_ascii=False)
        
    except ValueError as e:
        return json.dumps({"error": True, "message": str(e)})
    except Exception as e:
        return json.dumps({"error": True, "message": f"Edit error: {str(e)}"})


async def _run_code(arguments: dict[str, Any]) -> str:
    """运行代码文件"""
    import asyncio
    import subprocess
    
    file = arguments.get("file", "")
    args = arguments.get("args", [])
    
    if not file:
        return json.dumps({"error": True, "message": "File is required"})
    
    try:
        safe_path = _safe_path(file)
        
        if not os.path.exists(safe_path):
            return json.dumps({"error": True, "message": f"File not found: {file}"})
        
        # 根据扩展名选择运行器
        ext = os.path.splitext(file)[1].lower()
        
        if ext == ".py":
            cmd = ["python3", safe_path] + args
        elif ext == ".js":
            cmd = ["node", safe_path] + args
        elif ext == ".sh":
            cmd = ["bash", safe_path] + args
        elif ext == ".ts":
            cmd = ["npx", "ts-node", safe_path] + args
        else:
            return json.dumps({
                "error": True,
                "message": f"Unsupported file type: {ext}. Supported: .py, .js, .ts, .sh"
            })
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=_get_workspace_root()
        )
        
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        
        output = stdout.decode("utf-8", errors="replace")
        error = stderr.decode("utf-8", errors="replace")
        
        if len(output) > 10000:
            output = output[:10000] + "\n... [truncated]"
        
        return json.dumps({
            "file": file,
            "exit_code": proc.returncode,
            "stdout": output,
            "stderr": error if error else None
        }, ensure_ascii=False, indent=2)
        
    except asyncio.TimeoutError:
        return json.dumps({"error": True, "message": "Execution timed out after 60s"})
    except ValueError as e:
        return json.dumps({"error": True, "message": str(e)})
    except Exception as e:
        return json.dumps({"error": True, "message": f"Run error: {str(e)}"})


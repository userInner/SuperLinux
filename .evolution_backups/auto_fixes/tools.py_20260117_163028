"""Direct tool implementations for in-process use."""

import json
import os
import shutil
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
        # ===== 自我感知工具 (Phase 1) =====
        ToolSchema(
            name="read_own_code",
            description="读取自己的源代码，用于自我分析和理解自己的实现",
            parameters={
                "type": "object",
                "properties": {
                    "module": {
                        "type": "string",
                        "description": "要读取的模块名称",
                        "enum": ["tools", "prompts", "agent", "experience_rag", "multi_agent", "all"]
                    },
                    "search_pattern": {
                        "type": "string",
                        "description": "可选：搜索特定内容的正则表达式"
                    }
                },
                "required": ["module"]
            }
        ),
        ToolSchema(
            name="analyze_performance",
            description="分析自己的执行统计和性能表现，识别弱点和改进机会",
            parameters={
                "type": "object",
                "properties": {
                    "time_range": {
                        "type": "string",
                        "description": "分析时间范围",
                        "enum": ["last_hour", "last_day", "last_week", "all"],
                        "default": "last_day"
                    },
                    "focus": {
                        "type": "string",
                        "description": "分析重点",
                        "enum": ["errors", "tools", "success_rate", "all"],
                        "default": "all"
                    }
                },
                "required": []
            }
        ),
        ToolSchema(
            name="review_experiences",
            description="主动查看和分析历史经验，从过去的成功和失败中学习",
            parameters={
                "type": "object",
                "properties": {
                    "filter": {
                        "type": "string",
                        "description": "过滤条件",
                        "enum": ["failures", "successes", "recent", "all"],
                        "default": "all"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回数量",
                        "default": 10
                    },
                    "analyze": {
                        "type": "boolean",
                        "description": "是否进行深度分析",
                        "default": False
                    }
                },
                "required": []
            }
        ),
        # ===== 自我诊断工具 (Phase 2) =====
        ToolSchema(
            name="evaluate_last_task",
            description="评估刚完成的任务，分析表现并生成改进建议（Phase 2）",
            parameters={
                "type": "object",
                "properties": {
                    "include_suggestions": {
                        "type": "boolean",
                        "description": "是否包含改进建议",
                        "default": True
                    }
                },
                "required": []
            }
        ),
        ToolSchema(
            name="generate_improvement_plan",
            description="基于历史表现生成详细的改进计划（Phase 2）",
            parameters={
                "type": "object",
                "properties": {
                    "focus_area": {
                        "type": "string",
                        "enum": ["prompt", "tool", "strategy", "all"],
                        "description": "改进重点领域",
                        "default": "all"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["high", "medium", "low", "all"],
                        "description": "优先级过滤",
                        "default": "high"
                    }
                },
                "required": []
            }
        ),
        ToolSchema(
            name="review_meta_experiences",
            description="查看关于自我改进的元经验，了解哪些改进有效（Phase 2）",
            parameters={
                "type": "object",
                "properties": {
                    "improvement_type": {
                        "type": "string",
                        "enum": ["prompt", "tool", "strategy", "all"],
                        "description": "改进类型",
                        "default": "all"
                    },
                    "min_effectiveness": {
                        "type": "number",
                        "description": "最小有效性阈值 (0-1)",
                        "default": 0.2
                    }
                },
                "required": []
            }
        ),
        # ===== 自我进化工具 (Phase 3) =====
        ToolSchema(
            name="run_evolution_cycle",
            description="运行一个完整的自我进化周期：收集指标→生成建议→应用改进→测试效果→决定保留或回滚（Phase 3）",
            parameters={
                "type": "object",
                "properties": {
                    "auto_apply": {
                        "type": "boolean",
                        "description": "是否自动应用改进（不询问用户）",
                        "default": False
                    }
                },
                "required": []
            }
        ),
        ToolSchema(
            name="get_evolution_history",
            description="查看自我进化的历史记录，了解哪些改进被应用、哪些被回滚（Phase 3）",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        ToolSchema(
            name="get_evolution_stats",
            description="获取自我进化的统计数据，包括成功率、平均效果等（Phase 3）",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        ToolSchema(
            name="create_new_tool",
            description="创建一个新的工具函数，扩展自己的能力（自我进化）",
            parameters={
                "type": "object",
                "properties": {
                    "tool_name": {
                        "type": "string",
                        "description": "工具名称（snake_case）"
                    },
                    "description": {
                        "type": "string",
                        "description": "工具功能描述"
                    },
                    "parameters_schema": {
                        "type": "object",
                        "description": "工具参数的 JSON Schema"
                    },
                    "implementation": {
                        "type": "string",
                        "description": "工具的 Python 实现代码"
                    }
                },
                "required": ["tool_name", "description", "parameters_schema", "implementation"]
            }
        ),
        ToolSchema(
            name="optimize_tool",
            description="优化现有工具的实现，提高性能或功能（自我进化）",
            parameters={
                "type": "object",
                "properties": {
                    "tool_name": {
                        "type": "string",
                        "description": "要优化的工具名称"
                    },
                    "optimization": {
                        "type": "string",
                        "description": "优化后的代码实现"
                    },
                    "reason": {
                        "type": "string",
                        "description": "优化原因"
                    }
                },
                "required": ["tool_name", "optimization", "reason"]
            }
        ),
        ToolSchema(
            name="learn_tool_usage",
            description="学习如何使用一个工具，通过实验和文档（自我学习）",
            parameters={
                "type": "object",
                "properties": {
                    "tool_name": {
                        "type": "string",
                        "description": "要学习的工具名称"
                    },
                    "experiment": {
                        "type": "boolean",
                        "description": "是否进行实验测试",
                        "default": True
                    }
                },
                "required": ["tool_name"]
            }
        ),
        ToolSchema(
            name="audit_own_code",
            description="审计自己的源代码，发现性能、安全、bug 等问题（主动自我改进）",
            parameters={
                "type": "object",
                "properties": {
                    "focus": {
                        "type": "string",
                        "enum": ["all", "performance", "security", "bug", "maintainability"],
                        "description": "审计重点",
                        "default": "all"
                    },
                    "generate_plan": {
                        "type": "boolean",
                        "description": "是否生成改进计划",
                        "default": True
                    }
                },
                "required": []
            }
        ),
        ToolSchema(
            name="apply_code_fix",
            description="应用代码修复，改进自己的实现（自我优化）",
            parameters={
                "type": "object",
                "properties": {
                    "file": {
                        "type": "string",
                        "description": "要修复的文件路径"
                    },
                    "line": {
                        "type": "integer",
                        "description": "问题所在行号"
                    },
                    "fix_code": {
                        "type": "string",
                        "description": "修复后的代码"
                    },
                    "reason": {
                        "type": "string",
                        "description": "修复原因"
                    }
                },
                "required": ["file", "line", "fix_code", "reason"]
            }
        ),
        ToolSchema(
            name="auto_fix_code",
            description="自动修复代码问题 - AI 扫描代码，发现问题并自动修复（完全自主）",
            parameters={
                "type": "object",
                "properties": {
                    "focus": {
                        "type": "string",
                        "enum": ["all", "performance", "security", "bug", "maintainability"],
                        "description": "修复重点",
                        "default": "all"
                    },
                    "max_fixes": {
                        "type": "integer",
                        "description": "最多修复数量",
                        "default": 10
                    }
                },
                "required": []
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
        # 自我感知工具
        elif name == "read_own_code":
            return await _read_own_code(arguments)
        elif name == "analyze_performance":
            return await _analyze_performance(arguments)
        elif name == "review_experiences":
            return await _review_experiences(arguments)
        # 自我诊断工具 (Phase 2)
        elif name == "evaluate_last_task":
            return await _evaluate_last_task(arguments)
        elif name == "generate_improvement_plan":
            return await _generate_improvement_plan(arguments)
        elif name == "review_meta_experiences":
            return await _review_meta_experiences(arguments)
        # 自我进化工具 (Phase 3)
        elif name == "run_evolution_cycle":
            return await _run_evolution_cycle(arguments)
        elif name == "get_evolution_history":
            return await _get_evolution_history(arguments)
        elif name == "get_evolution_stats":
            return await _get_evolution_stats(arguments)
        elif name == "create_new_tool":
            return await _create_new_tool(arguments)
        elif name == "optimize_tool":
            return await _optimize_tool(arguments)
        elif name == "learn_tool_usage":
            return await _learn_tool_usage(arguments)
        elif name == "audit_own_code":
            return await _audit_own_code(arguments)
        elif name == "apply_code_fix":
            return await _apply_code_fix(arguments)
        elif name == "auto_fix_code":
            return await _auto_fix_code(arguments)
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



# ===== 自我感知工具实现 (Phase 1) =====

async def _read_own_code(arguments: dict[str, Any]) -> str:
    """读取自己的源代码进行自我分析"""
    module = arguments.get("module", "all")
    search_pattern = arguments.get("search_pattern")
    
    # 源代码文件映射
    module_files = {
        "tools": "src/tools.py",
        "prompts": "src/prompts.py",
        "agent": "src/agent.py",
        "experience_rag": "src/experience_rag.py",
        "multi_agent": "src/multi_agent.py",
    }
    
    try:
        result = {
            "module": module,
            "files": {}
        }
        
        if module == "all":
            files_to_read = list(module_files.values())
        elif module in module_files:
            files_to_read = [module_files[module]]
        else:
            return json.dumps({
                "error": True,
                "message": f"Unknown module: {module}. Available: {', '.join(module_files.keys())}, all"
            })
        
        for filepath in files_to_read:
            if not os.path.exists(filepath):
                result["files"][filepath] = {"error": "File not found"}
                continue
            
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # 如果有搜索模式，只返回匹配的部分
                if search_pattern:
                    import re
                    matches = []
                    for i, line in enumerate(content.split("\n"), 1):
                        if re.search(search_pattern, line, re.IGNORECASE):
                            # 返回匹配行及上下文
                            start = max(0, i - 3)
                            end = min(len(content.split("\n")), i + 3)
                            context = "\n".join(content.split("\n")[start:end])
                            matches.append({
                                "line": i,
                                "context": context
                            })
                    
                    result["files"][filepath] = {
                        "matches": matches,
                        "total_matches": len(matches)
                    }
                else:
                    # 返回完整内容（限制大小）
                    if len(content) > 20000:
                        content = content[:20000] + "\n... [truncated, use search_pattern to find specific code]"
                    
                    # 提取关键信息
                    lines = content.split("\n")
                    functions = [l.strip() for l in lines if l.strip().startswith("def ") or l.strip().startswith("async def ")]
                    classes = [l.strip() for l in lines if l.strip().startswith("class ")]
                    
                    result["files"][filepath] = {
                        "content": content,
                        "lines": len(lines),
                        "functions": functions[:20],  # 前20个函数
                        "classes": classes[:10],      # 前10个类
                        "size_bytes": len(content)
                    }
            
            except Exception as e:
                result["files"][filepath] = {"error": str(e)}
        
        result["summary"] = f"Read {len(result['files'])} file(s)"
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({"error": True, "message": f"Read own code error: {str(e)}"})


async def _analyze_performance(arguments: dict[str, Any]) -> str:
    """分析自己的执行统计和性能"""
    time_range = arguments.get("time_range", "last_day")
    focus = arguments.get("focus", "all")
    
    try:
        from datetime import datetime, timedelta
        
        # 读取经验数据库
        from .experience_rag import get_experience_rag
        rag = get_experience_rag()
        
        # 获取统计信息
        stats = rag.get_stats()
        
        result = {
            "time_range": time_range,
            "focus": focus,
            "timestamp": datetime.now().isoformat(),
            "overall_stats": stats,
            "analysis": {}
        }
        
        # 读取 JSON 备份进行详细分析
        json_path = os.path.join(rag.db_path, "experiences.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    experiences = json.load(f)
                
                # 时间过滤
                cutoff_time = None
                if time_range == "last_hour":
                    cutoff_time = datetime.now() - timedelta(hours=1)
                elif time_range == "last_day":
                    cutoff_time = datetime.now() - timedelta(days=1)
                elif time_range == "last_week":
                    cutoff_time = datetime.now() - timedelta(weeks=1)
                
                if cutoff_time:
                    experiences = [
                        e for e in experiences
                        if datetime.fromisoformat(e.get("timestamp", "2000-01-01")) > cutoff_time
                    ]
                
                # 分析错误
                if focus in ["errors", "all"]:
                    all_errors = []
                    for exp in experiences:
                        all_errors.extend(exp.get("errors_encountered", []))
                    
                    # 统计错误频率
                    error_counts = {}
                    for error in all_errors:
                        error_key = error[:100]  # 取前100字符作为key
                        error_counts[error_key] = error_counts.get(error_key, 0) + 1
                    
                    top_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:10]
                    
                    result["analysis"]["errors"] = {
                        "total_errors": len(all_errors),
                        "unique_errors": len(error_counts),
                        "top_errors": [
                            {"error": err, "count": cnt}
                            for err, cnt in top_errors
                        ]
                    }
                
                # 分析工具使用
                if focus in ["tools", "all"]:
                    tool_usage = {}
                    for exp in experiences:
                        for tool in exp.get("tools_used", []):
                            tool_usage[tool] = tool_usage.get(tool, 0) + 1
                    
                    result["analysis"]["tools"] = {
                        "total_tool_calls": sum(tool_usage.values()),
                        "unique_tools": len(tool_usage),
                        "most_used": sorted(tool_usage.items(), key=lambda x: x[1], reverse=True)[:10]
                    }
                
                # 分析成功率
                if focus in ["success_rate", "all"]:
                    total = len(experiences)
                    successful = sum(1 for e in experiences if e.get("success", False))
                    failed = total - successful
                    
                    result["analysis"]["success_rate"] = {
                        "total_tasks": total,
                        "successful": successful,
                        "failed": failed,
                        "success_percentage": round(successful / total * 100, 2) if total > 0 else 0
                    }
                    
                    # 分析失败原因
                    if failed > 0:
                        failure_reasons = []
                        for exp in experiences:
                            if not exp.get("success", False):
                                failure_reasons.append({
                                    "problem": exp.get("problem", "")[:100],
                                    "errors": exp.get("errors_encountered", [])[:2]
                                })
                        result["analysis"]["recent_failures"] = failure_reasons[:5]
                
                # 生成改进建议
                result["improvement_suggestions"] = _generate_improvement_suggestions(result["analysis"])
            
            except Exception as e:
                result["analysis"]["error"] = f"Failed to analyze experiences: {str(e)}"
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({"error": True, "message": f"Performance analysis error: {str(e)}"})


def _generate_improvement_suggestions(analysis: dict) -> list[str]:
    """根据分析结果生成改进建议"""
    suggestions = []
    
    # 基于错误分析
    if "errors" in analysis:
        error_data = analysis["errors"]
        if error_data["total_errors"] > 10:
            suggestions.append(
                f"⚠️ 发现 {error_data['total_errors']} 个错误，建议优化错误处理策略"
            )
        
        if error_data.get("top_errors"):
            top_error = error_data["top_errors"][0]
            suggestions.append(
                f"🔍 最常见错误: '{top_error['error'][:50]}...' (出现 {top_error['count']} 次)，建议针对性优化"
            )
    
    # 基于成功率
    if "success_rate" in analysis:
        rate_data = analysis["success_rate"]
        success_pct = rate_data.get("success_percentage", 0)
        
        if success_pct < 70:
            suggestions.append(
                f"📉 成功率仅 {success_pct}%，需要改进问题解决策略"
            )
        elif success_pct > 90:
            suggestions.append(
                f"✅ 成功率达到 {success_pct}%，表现优秀！"
            )
    
    # 基于工具使用
    if "tools" in analysis:
        tool_data = analysis["tools"]
        if tool_data["unique_tools"] < 5:
            suggestions.append(
                "🔧 工具使用种类较少，可能需要扩展工具集"
            )
    
    if not suggestions:
        suggestions.append("✨ 暂无明显改进点，继续保持！")
    
    return suggestions


async def _review_experiences(arguments: dict[str, Any]) -> str:
    """主动查看和分析历史经验"""
    filter_type = arguments.get("filter", "all")
    limit = arguments.get("limit", 10)
    analyze = arguments.get("analyze", False)
    
    try:
        from .experience_rag import get_experience_rag
        rag = get_experience_rag()
        
        result = {
            "filter": filter_type,
            "limit": limit,
            "experiences": []
        }
        
        # 读取经验
        json_path = os.path.join(rag.db_path, "experiences.json")
        if not os.path.exists(json_path):
            return json.dumps({
                "message": "No experiences found yet",
                "suggestion": "Start solving problems to build experience database"
            }, ensure_ascii=False)
        
        with open(json_path, "r", encoding="utf-8") as f:
            experiences = json.load(f)
        
        # 过滤
        if filter_type == "failures":
            experiences = [e for e in experiences if not e.get("success", False)]
        elif filter_type == "successes":
            experiences = [e for e in experiences if e.get("success", False)]
        elif filter_type == "recent":
            experiences = sorted(
                experiences,
                key=lambda e: e.get("timestamp", ""),
                reverse=True
            )
        
        # 限制数量
        experiences = experiences[:limit]
        
        # 格式化输出
        for exp in experiences:
            formatted = {
                "id": exp.get("id"),
                "problem": exp.get("problem", "")[:200],
                "success": exp.get("success", False),
                "tools_used": exp.get("tools_used", []),
                "timestamp": exp.get("timestamp", ""),
                "tags": exp.get("tags", [])
            }
            
            if not exp.get("success", False):
                formatted["errors"] = exp.get("errors_encountered", [])[:2]
            else:
                formatted["solution_summary"] = exp.get("solution", "")[:150]
            
            result["experiences"].append(formatted)
        
        result["total_found"] = len(experiences)
        
        # 深度分析
        if analyze and experiences:
            patterns = _analyze_experience_patterns(experiences)
            result["patterns"] = patterns
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({"error": True, "message": f"Review experiences error: {str(e)}"})


def _analyze_experience_patterns(experiences: list[dict]) -> dict:
    """分析经验中的模式"""
    patterns = {
        "common_problems": {},
        "effective_tools": {},
        "common_tags": {}
    }
    
    for exp in experiences:
        # 问题类型
        problem = exp.get("problem", "").lower()
        for keyword in ["nginx", "docker", "mysql", "network", "disk", "memory"]:
            if keyword in problem:
                patterns["common_problems"][keyword] = patterns["common_problems"].get(keyword, 0) + 1
        
        # 有效工具（仅成功案例）
        if exp.get("success", False):
            for tool in exp.get("tools_used", []):
                patterns["effective_tools"][tool] = patterns["effective_tools"].get(tool, 0) + 1
        
        # 标签
        for tag in exp.get("tags", []):
            patterns["common_tags"][tag] = patterns["common_tags"].get(tag, 0) + 1
    
    # 排序
    patterns["common_problems"] = dict(sorted(
        patterns["common_problems"].items(),
        key=lambda x: x[1],
        reverse=True
    )[:5])
    
    patterns["effective_tools"] = dict(sorted(
        patterns["effective_tools"].items(),
        key=lambda x: x[1],
        reverse=True
    )[:5])
    
    patterns["common_tags"] = dict(sorted(
        patterns["common_tags"].items(),
        key=lambda x: x[1],
        reverse=True
    )[:5])
    
    return patterns


# ===== 自我诊断工具实现 (Phase 2) =====

async def _evaluate_last_task(arguments: dict[str, Any]) -> str:
    """评估最后一个任务"""
    include_suggestions = arguments.get("include_suggestions", True)
    
    try:
        from .experience_rag import get_experience_rag
        from .self_diagnosis import get_evaluator, get_suggestion_generator
        
        # 获取最近的经验
        rag = get_experience_rag()
        json_path = os.path.join(rag.db_path, "experiences.json")
        
        if not os.path.exists(json_path):
            return json.dumps({
                "message": "No tasks to evaluate yet",
                "suggestion": "Complete some tasks first to build evaluation history"
            }, ensure_ascii=False)
        
        with open(json_path, "r", encoding="utf-8") as f:
            experiences = json.load(f)
        
        if not experiences:
            return json.dumps({
                "message": "No tasks to evaluate yet"
            }, ensure_ascii=False)
        
        # 获取最后一个任务
        last_exp = experiences[-1]
        
        # 评估任务
        evaluator = get_evaluator()
        evaluation = evaluator.evaluate_task(
            task=last_exp.get("problem", ""),
            result=last_exp.get("solution", ""),
            steps=last_exp.get("steps", []),
            tools_used=last_exp.get("tools_used", []),
            errors=last_exp.get("errors_encountered", []),
            execution_time=30.0,  # 默认值，实际应该记录
            success=last_exp.get("success", False)
        )
        
        result = {
            "evaluation": {
                "task": evaluation.task,
                "overall_score": round(evaluation.overall_score, 2),
                "dimensions": {
                    "success": round(evaluation.success_score, 2),
                    "efficiency": round(evaluation.efficiency_score, 2),
                    "tool_usage": round(evaluation.tool_usage_score, 2),
                    "error_handling": round(evaluation.error_handling_score, 2),
                    "user_satisfaction": round(evaluation.user_satisfaction_score, 2)
                },
                "comments": evaluation.comments,
                "stats": {
                    "execution_time": evaluation.execution_time,
                    "steps_count": evaluation.steps_count,
                    "tools_used": evaluation.tools_used,
                    "errors_count": evaluation.errors_count
                }
            }
        }
        
        # 生成改进建议
        if include_suggestions and evaluation.overall_score < 80:
            generator = get_suggestion_generator()
            suggestions = generator.generate_suggestions(
                evaluations=[evaluation],
                focus_area="all",
                priority="high"
            )
            
            result["suggestions"] = [
                {
                    "type": s.type.value,
                    "priority": s.priority.value,
                    "issue": s.issue,
                    "suggestion": s.suggestion,
                    "expected_improvement": s.expected_improvement
                }
                for s in suggestions[:3]  # 只返回前3个
            ]
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({"error": True, "message": f"Evaluation error: {str(e)}"})


async def _generate_improvement_plan(arguments: dict[str, Any]) -> str:
    """生成改进计划"""
    focus_area = arguments.get("focus_area", "all")
    priority = arguments.get("priority", "high")
    
    try:
        from .self_diagnosis import get_evaluator, get_suggestion_generator
        
        evaluator = get_evaluator()
        
        if not evaluator.evaluation_history:
            return json.dumps({
                "message": "No evaluation history yet",
                "suggestion": "Use evaluate_last_task first to build evaluation history"
            }, ensure_ascii=False)
        
        # 生成建议
        generator = get_suggestion_generator()
        suggestions = generator.generate_suggestions(
            evaluations=evaluator.evaluation_history,
            focus_area=focus_area,
            priority=priority
        )
        
        if not suggestions:
            return json.dumps({
                "message": "No improvements needed",
                "note": "Your performance is excellent! Keep it up."
            }, ensure_ascii=False)
        
        result = {
            "improvement_plan": {
                "focus_area": focus_area,
                "priority": priority,
                "total_suggestions": len(suggestions),
                "suggestions": [
                    {
                        "id": s.id,
                        "type": s.type.value,
                        "priority": s.priority.value,
                        "issue": s.issue,
                        "suggestion": s.suggestion,
                        "expected_improvement": s.expected_improvement,
                        "affected_area": s.affected_area,
                        "evidence": s.evidence
                    }
                    for s in suggestions
                ]
            },
            "next_steps": [
                "1. Review the suggestions above",
                "2. Prioritize high-priority items",
                "3. Apply improvements one at a time",
                "4. Use review_meta_experiences to track effectiveness"
            ]
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({"error": True, "message": f"Plan generation error: {str(e)}"})


async def _review_meta_experiences(arguments: dict[str, Any]) -> str:
    """查看元经验"""
    improvement_type = arguments.get("improvement_type", "all")
    min_effectiveness = arguments.get("min_effectiveness", 0.2)
    
    try:
        from .self_diagnosis import get_meta_manager
        
        manager = get_meta_manager()
        meta_exps = manager.get_effective_improvements(
            improvement_type=improvement_type,
            min_effectiveness=min_effectiveness
        )
        
        if not meta_exps:
            return json.dumps({
                "message": "No meta-experiences found yet",
                "note": "Meta-experiences are created when you apply improvements and track their effectiveness"
            }, ensure_ascii=False)
        
        result = {
            "meta_experiences": {
                "total_found": len(meta_exps),
                "filter": {
                    "improvement_type": improvement_type,
                    "min_effectiveness": min_effectiveness
                },
                "experiences": [
                    {
                        "id": m.id,
                        "type": m.improvement_type,
                        "problem": m.problem_identified,
                        "solution": m.solution_applied,
                        "effectiveness": round(m.effectiveness * 100, 1),
                        "before_metrics": m.before_metrics,
                        "after_metrics": m.after_metrics,
                        "timestamp": m.timestamp
                    }
                    for m in meta_exps[:10]  # 只返回前10个
                ]
            },
            "insights": _generate_meta_insights(meta_exps)
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({"error": True, "message": f"Meta review error: {str(e)}"})


def _generate_meta_insights(meta_exps: list) -> list[str]:
    """从元经验中生成洞察"""
    if not meta_exps:
        return []
    
    insights = []
    
    # 最有效的改进类型
    type_effectiveness = {}
    for m in meta_exps:
        t = m.improvement_type
        if t not in type_effectiveness:
            type_effectiveness[t] = []
        type_effectiveness[t].append(m.effectiveness)
    
    for t, effs in type_effectiveness.items():
        avg_eff = sum(effs) / len(effs)
        insights.append(
            f"💡 {t} 类改进平均有效性: {avg_eff*100:.1f}%"
        )
    
    # 最成功的改进
    if meta_exps:
        best = max(meta_exps, key=lambda x: x.effectiveness)
        insights.append(
            f"🏆 最成功的改进: {best.problem_identified[:50]}... (提升 {best.effectiveness*100:.1f}%)"
        )
    
    return insights


# ===== 自我进化工具实现 (Phase 3) =====

async def _run_evolution_cycle(arguments: dict[str, Any]) -> str:
    """运行一个完整的自我进化周期"""
    auto_apply = arguments.get("auto_apply", False)
    
    try:
        from .self_evolution import get_evolution_engine
        
        engine = get_evolution_engine()
        
        print("\n🧬 开始自我进化周期...")
        cycle = await engine.run_evolution_cycle(auto_apply=auto_apply)
        
        if cycle is None:
            return json.dumps({
                "message": "No evolution needed or user cancelled",
                "note": "Current performance is already good or no improvements available"
            }, ensure_ascii=False)
        
        result = {
            "evolution_cycle": {
                "cycle_id": cycle.cycle_id,
                "success": cycle.success,
                "effectiveness": f"{cycle.effectiveness*100:.1f}%",
                "rolled_back": cycle.rolled_back,
                "rollback_reason": cycle.rollback_reason,
                "before_metrics": cycle.before_metrics,
                "after_metrics": cycle.after_metrics,
                "improvements_applied": cycle.improvements_applied
            },
            "summary": (
                f"✅ 进化成功！性能提升 {cycle.effectiveness*100:.1f}%"
                if cycle.success
                else f"❌ 进化失败，已回滚。原因: {cycle.rollback_reason}"
            )
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return json.dumps({"error": True, "message": f"Evolution error: {str(e)}"})


async def _get_evolution_history(arguments: dict[str, Any]) -> str:
    """获取进化历史"""
    try:
        from .self_evolution import get_evolution_engine
        
        engine = get_evolution_engine()
        history = engine.get_evolution_history()
        
        if not history:
            return json.dumps({
                "message": "No evolution history yet",
                "note": "Run run_evolution_cycle to start evolving"
            }, ensure_ascii=False)
        
        result = {
            "evolution_history": {
                "total_cycles": len(history),
                "cycles": history
            },
            "summary": f"已完成 {len(history)} 个进化周期"
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({"error": True, "message": f"History error: {str(e)}"})


async def _get_evolution_stats(arguments: dict[str, Any]) -> str:
    """获取进化统计"""
    try:
        from .self_evolution import get_evolution_engine
        
        engine = get_evolution_engine()
        stats = engine.get_evolution_stats()
        
        if stats["total_cycles"] == 0:
            return json.dumps({
                "message": "No evolution data yet",
                "note": "Run run_evolution_cycle to start collecting data"
            }, ensure_ascii=False)
        
        result = {
            "evolution_stats": stats,
            "insights": [
                f"📊 总进化周期: {stats['total_cycles']}",
                f"✅ 成功周期: {stats['successful_cycles']}",
                f"📈 成功率: {stats['success_rate']*100:.1f}%",
                f"💪 平均提升: {stats['avg_effectiveness']*100:.1f}%",
                f"🔄 回滚次数: {stats['rollbacks']}"
            ]
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({"error": True, "message": f"Stats error: {str(e)}"})



# ===== 真正的自我进化工具 =====

async def _create_new_tool(arguments: dict[str, Any]) -> str:
    """创建新工具 - AI 自己编写工具代码"""
    tool_name = arguments.get("tool_name", "")
    description = arguments.get("description", "")
    parameters_schema = arguments.get("parameters_schema", {})
    implementation = arguments.get("implementation", "")
    
    if not all([tool_name, description, implementation]):
        return json.dumps({"error": True, "message": "Missing required fields"})
    
    try:
        # 1. 备份当前 tools.py
        backup_dir = ".evolution_backups/tools"
        os.makedirs(backup_dir, exist_ok=True)
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"tools_{timestamp}.py")
        shutil.copy2("src/tools.py", backup_path)
        
        # 2. 读取当前 tools.py
        with open("src/tools.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # 3. 添加工具定义到 get_all_tools()
        tool_schema = f'''        ToolSchema(
            name="{tool_name}",
            description="{description}",
            parameters={json.dumps(parameters_schema, indent=16).replace('"', "'")}
        ),'''
        
        # 在最后一个工具后添加
        insert_pos = content.rfind("    ]")
        if insert_pos == -1:
            return json.dumps({"error": True, "message": "Cannot find tools list"})
        
        content = content[:insert_pos] + tool_schema + "\n" + content[insert_pos:]
        
        # 4. 添加工具执行逻辑
        execute_case = f'''        elif name == "{tool_name}":
            return await _{tool_name}(arguments)'''
        
        else_pos = content.rfind("        else:\n            return json.dumps")
        if else_pos == -1:
            return json.dumps({"error": True, "message": "Cannot find execute_tool switch"})
        
        content = content[:else_pos] + execute_case + "\n" + content[else_pos:]
        
        # 5. 添加工具实现
        impl_code = f'''

async def _{tool_name}(arguments: dict[str, Any]) -> str:
    """{description}"""
    try:
{chr(10).join("        " + line for line in implementation.split(chr(10)))}
    except Exception as e:
        return json.dumps({{"error": True, "message": f"Tool error: {{str(e)}}"}})
'''
        
        content += impl_code
        
        # 6. 写入文件
        with open("src/tools.py", "w", encoding="utf-8") as f:
            f.write(content)
        
        # 7. 测试新工具
        try:
            # 重新加载模块
            import importlib
            import src.tools
            importlib.reload(src.tools)
            
            result = {
                "success": True,
                "tool_name": tool_name,
                "message": f"✅ 新工具 '{tool_name}' 创建成功！",
                "backup": backup_path,
                "next_steps": [
                    "工具已添加到系统",
                    "可以立即使用",
                    "建议先测试功能是否正常"
                ]
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            # 回滚
            shutil.copy2(backup_path, "src/tools.py")
            return json.dumps({
                "error": True,
                "message": f"工具创建失败，已回滚: {str(e)}"
            })
    
    except Exception as e:
        return json.dumps({"error": True, "message": f"Create tool error: {str(e)}"})


async def _optimize_tool(arguments: dict[str, Any]) -> str:
    """优化现有工具"""
    tool_name = arguments.get("tool_name", "")
    optimization = arguments.get("optimization", "")
    reason = arguments.get("reason", "")
    
    if not all([tool_name, optimization, reason]):
        return json.dumps({"error": True, "message": "Missing required fields"})
    
    try:
        # 1. 备份
        backup_dir = ".evolution_backups/tools"
        os.makedirs(backup_dir, exist_ok=True)
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"tools_{timestamp}.py")
        shutil.copy2("src/tools.py", backup_path)
        
        # 2. 读取当前代码
        with open("src/tools.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # 3. 查找工具函数
        func_name = f"async def _{tool_name}("
        func_start = content.find(func_name)
        
        if func_start == -1:
            return json.dumps({
                "error": True,
                "message": f"Tool '{tool_name}' not found"
            })
        
        # 4. 找到函数结束位置（下一个 async def 或文件末尾）
        next_func = content.find("\nasync def ", func_start + 1)
        if next_func == -1:
            next_func = content.find("\ndef ", func_start + 1)
        
        if next_func == -1:
            func_end = len(content)
        else:
            func_end = next_func
        
        # 5. 替换函数实现
        old_impl = content[func_start:func_end]
        new_impl = f'''async def _{tool_name}(arguments: dict[str, Any]) -> str:
    """优化版本 - {reason}"""
    try:
{chr(10).join("        " + line for line in optimization.split(chr(10)))}
    except Exception as e:
        return json.dumps({{"error": True, "message": f"Tool error: {{str(e)}}"}})

'''
        
        content = content[:func_start] + new_impl + content[func_end:]
        
        # 6. 写入文件
        with open("src/tools.py", "w", encoding="utf-8") as f:
            f.write(content)
        
        # 7. 测试
        try:
            import importlib
            import src.tools
            importlib.reload(src.tools)
            
            result = {
                "success": True,
                "tool_name": tool_name,
                "message": f"✅ 工具 '{tool_name}' 优化成功！",
                "reason": reason,
                "backup": backup_path,
                "changes": {
                    "before_lines": len(old_impl.split("\n")),
                    "after_lines": len(new_impl.split("\n"))
                }
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            # 回滚
            shutil.copy2(backup_path, "src/tools.py")
            return json.dumps({
                "error": True,
                "message": f"优化失败，已回滚: {str(e)}"
            })
    
    except Exception as e:
        return json.dumps({"error": True, "message": f"Optimize error: {str(e)}"})


async def _learn_tool_usage(arguments: dict[str, Any]) -> str:
    """学习工具使用方法"""
    tool_name = arguments.get("tool_name", "")
    experiment = arguments.get("experiment", True)
    
    if not tool_name:
        return json.dumps({"error": True, "message": "tool_name is required"})
    
    try:
        # 1. 读取工具定义
        all_tools = get_all_tools()
        tool_def = None
        
        for tool in all_tools:
            if tool.name == tool_name:
                tool_def = tool
                break
        
        if not tool_def:
            return json.dumps({
                "error": True,
                "message": f"Tool '{tool_name}' not found"
            })
        
        # 2. 分析工具
        analysis = {
            "tool_name": tool_name,
            "description": tool_def.description,
            "parameters": tool_def.parameters,
            "learning": {}
        }
        
        # 3. 提取参数信息
        params = tool_def.parameters.get("properties", {})
        required = tool_def.parameters.get("required", [])
        
        analysis["learning"]["required_params"] = required
        analysis["learning"]["optional_params"] = [
            p for p in params.keys() if p not in required
        ]
        
        # 4. 生成使用示例
        example_args = {}
        for param_name, param_info in params.items():
            param_type = param_info.get("type", "string")
            
            if param_type == "string":
                if "enum" in param_info:
                    example_args[param_name] = param_info["enum"][0]
                else:
                    example_args[param_name] = f"example_{param_name}"
            elif param_type == "integer":
                example_args[param_name] = 10
            elif param_type == "number":
                example_args[param_name] = 0.5
            elif param_type == "boolean":
                example_args[param_name] = True
            elif param_type == "array":
                example_args[param_name] = []
            elif param_type == "object":
                example_args[param_name] = {}
        
        analysis["learning"]["example_usage"] = example_args
        
        # 5. 实验测试（如果启用）
        if experiment:
            try:
                # 尝试调用工具
                test_result = await execute_tool(tool_name, example_args)
                analysis["learning"]["experiment_result"] = "success"
                analysis["learning"]["experiment_output"] = test_result[:500]
            except Exception as e:
                analysis["learning"]["experiment_result"] = "failed"
                analysis["learning"]["experiment_error"] = str(e)
        
        # 6. 生成学习总结
        analysis["summary"] = f"""
学习完成！关于 '{tool_name}' 工具：

📝 功能: {tool_def.description}

🔧 必需参数: {', '.join(required) if required else '无'}
⚙️  可选参数: {', '.join(analysis['learning']['optional_params']) if analysis['learning']['optional_params'] else '无'}

💡 使用示例:
{json.dumps(example_args, indent=2, ensure_ascii=False)}

{'✅ 实验测试通过' if experiment and analysis['learning'].get('experiment_result') == 'success' else ''}
"""
        
        return json.dumps(analysis, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({"error": True, "message": f"Learn error: {str(e)}"})


# ===== 代码审计工具 =====

async def _audit_own_code(arguments: dict[str, Any]) -> str:
    """审计自己的代码"""
    focus = arguments.get("focus", "all")
    generate_plan = arguments.get("generate_plan", True)
    
    try:
        from .code_auditor import get_auditor
        
        auditor = get_auditor()
        
        print("🔍 开始审计代码...")
        issues = auditor.audit_all()
        
        # 按焦点过滤
        if focus != "all":
            issues = [i for i in issues if i.category == focus]
        
        result = {
            "total_issues": len(issues),
            "by_severity": {
                "high": len([i for i in issues if i.severity == "high"]),
                "medium": len([i for i in issues if i.severity == "medium"]),
                "low": len([i for i in issues if i.severity == "low"])
            },
            "by_category": {}
        }
        
        # 按类别统计
        for issue in issues:
            if issue.category not in result["by_category"]:
                result["by_category"][issue.category] = 0
            result["by_category"][issue.category] += 1
        
        # 列出高优先级问题
        high_priority = [i for i in issues if i.severity == "high"]
        result["high_priority_issues"] = [
            {
                "file": i.file,
                "line": i.line,
                "category": i.category,
                "issue": i.issue,
                "suggestion": i.suggestion,
                "code": i.code_snippet
            }
            for i in high_priority[:10]  # 最多10个
        ]
        
        # 生成改进计划
        if generate_plan:
            plan = auditor.generate_improvement_plan(issues)
            result["improvement_plan"] = plan
        
        print(f"✅ 审计完成: 发现 {len(issues)} 个问题")
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({"error": True, "message": f"Audit error: {str(e)}"})


async def _apply_code_fix(arguments: dict[str, Any]) -> str:
    """应用代码修复"""
    file_path = arguments.get("file", "")
    line_num = arguments.get("line", 0)
    fix_code = arguments.get("fix_code", "")
    reason = arguments.get("reason", "")
    
    if not all([file_path, line_num, fix_code, reason]):
        return json.dumps({"error": True, "message": "Missing required fields"})
    
    try:
        # 1. 备份
        backup_dir = ".evolution_backups/fixes"
        os.makedirs(backup_dir, exist_ok=True)
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"{os.path.basename(file_path)}_{timestamp}")
        shutil.copy2(file_path, backup_path)
        
        # 2. 读取文件
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if line_num < 1 or line_num > len(lines):
            return json.dumps({"error": True, "message": f"Invalid line number: {line_num}"})
        
        # 3. 记录原代码
        old_code = lines[line_num - 1].rstrip()
        
        # 4. 应用修复
        lines[line_num - 1] = fix_code if fix_code.endswith('\n') else fix_code + '\n'
        
        # 5. 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        # 6. 验证语法
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                compile(f.read(), file_path, 'exec')
            syntax_ok = True
        except SyntaxError as e:
            syntax_ok = False
            # 回滚
            shutil.copy2(backup_path, file_path)
            return json.dumps({
                "error": True,
                "message": f"语法错误，已回滚: {str(e)}"
            })
        
        result = {
            "success": True,
            "file": file_path,
            "line": line_num,
            "reason": reason,
            "backup": backup_path,
            "changes": {
                "before": old_code,
                "after": fix_code.rstrip()
            }
        }
        
        print(f"✅ 代码修复成功: {file_path}:{line_num}")
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({"error": True, "message": f"Fix error: {str(e)}"})



async def _auto_fix_code(arguments: dict[str, Any]) -> str:
    """自动修复代码"""
    focus = arguments.get("focus", "all")
    max_fixes = arguments.get("max_fixes", 10)
    
    try:
        from .auto_fixer import auto_fix_code
        
        print(f"🔧 开始自动修复代码...")
        print(f"   重点: {focus}")
        print(f"   最多修复: {max_fixes} 个问题")
        
        results = auto_fix_code(focus=focus, max_fixes=max_fixes)
        
        print(f"\n✅ 自动修复完成!")
        print(f"   尝试修复: {results['attempted']} 个")
        print(f"   成功: {results['successful']} 个")
        print(f"   失败: {results['failed']} 个")
        
        return json.dumps(results, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({"error": True, "message": f"Auto fix error: {str(e)}"})

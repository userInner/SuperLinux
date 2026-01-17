"""工具定义的辅助函数 - 用于重构tools.py的超长函数"""

from typing import Dict, List


# ===== 代码/文件操作工具 =====
def get_file_tools() -> List[Dict]:
    """获取文件操作相关工具"""
    return [
        {
            "name": "read_file",
            "description": "读取文件内容，支持代码文件、配置文件、日志等",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"},
                    "start_line": {"type": "integer", "description": "起始行号（可选）"},
                    "end_line": {"type": "integer", "description": "结束行号（可选）"}
                },
                "required": ["path"]
            }
        },
        {
            "name": "write_file",
            "description": "写入或创建文件，可用于写代码、配置文件等",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"},
                    "content": {"type": "string", "description": "文件内容"},
                    "mode": {"type": "string", "enum": ["overwrite", "append"], "default": "overwrite"}
                },
                "required": ["path", "content"]
            }
        },
        {
            "name": "list_directory",
            "description": "列出目录内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "目录路径", "default": "."},
                    "recursive": {"type": "boolean", "description": "是否递归", "default": False},
                    "max_depth": {"type": "integer", "description": "最大深度", "default": 2}
                },
                "required": []
            }
        },
        {
            "name": "create_directory",
            "description": "创建目录",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "目录路径"}
                },
                "required": ["path"]
            }
        },
        {
            "name": "search_in_files",
            "description": "在文件中搜索内容（类似 grep）",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "搜索模式（支持正则）"},
                    "path": {"type": "string", "description": "搜索路径", "default": "."},
                    "file_pattern": {"type": "string", "description": "文件名模式，如 *.py", "default": "*"}
                },
                "required": ["pattern"]
            }
        },
        {
            "name": "run_code",
            "description": "运行代码文件（Python/Node.js/Bash）",
            "parameters": {
                "type": "object",
                "properties": {
                    "file": {"type": "string", "description": "代码文件路径"},
                    "args": {"type": "array", "items": {"type": "string"}, "description": "命令行参数"}
                },
                "required": ["file"]
            }
        }
    ]


# ===== 系统监控工具 =====
def get_system_tools() -> List[Dict]:
    """获取系统监控相关工具"""
    return [
        {
            "name": "get_system_stats",
            "description": "获取当前系统状态，包括 CPU 使用率、内存使用情况、磁盘空间等",
            "parameters": {
                "type": "object",
                "properties": {
                    "include_processes": {"type": "boolean", "description": "是否包含进程列表", "default": False}
                },
                "required": []
            }
        },
        {
            "name": "get_cpu_info",
            "description": "获取详细的 CPU 信息",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "get_memory_info",
            "description": "获取详细的内存信息",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "get_disk_info",
            "description": "获取磁盘使用信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "要检查的路径", "default": "/"}
                },
                "required": []
            }
        },
        {
            "name": "list_services",
            "description": "列出系统服务状态",
            "parameters": {
                "type": "object",
                "properties": {
                    "state": {"type": "string", "enum": ["running", "stopped", "all"], "default": "running"}
                },
                "required": []
            }
        }
    ]


# ===== 网络与搜索工具 =====
def get_network_tools() -> List[Dict]:
    """获取网络与搜索相关工具"""
    return [
        {
            "name": "web_search",
            "description": "使用搜索引擎搜索信息，可以搜索技术文档、教程、问题解答等",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                    "num_results": {"type": "integer", "description": "返回结果数量", "default": 5}
                },
                "required": ["query"]
            }
        },
        {
            "name": "fetch_webpage",
            "description": "获取网页内容，用于查看文档、教程等网页的详细内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "要获取的网页 URL"},
                    "max_length": {"type": "integer", "description": "返回内容的最大字符数", "default": 5000}
                },
                "required": ["url"]
            }
        },
        {
            "name": "run_command",
            "description": "执行 Linux 命令并返回结果（仅限安全命令）",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "要执行的命令"}
                },
                "required": ["command"]
            }
        }
    ]


# ===== 自我感知与学习工具 =====
def get_self_awareness_tools() -> List[Dict]:
    """获取自我感知与学习相关工具"""
    return [
        {
            "name": "read_own_code",
            "description": "读取自己的源代码，用于自我分析和理解自己的实现",
            "parameters": {
                "type": "object",
                "properties": {
                    "module": {"type": "string", "description": "要读取的模块名称", "enum": ["tools", "prompts", "agent", "experience_rag", "multi_agent", "all"]},
                    "search_pattern": {"type": "string", "description": "可选：搜索特定内容的正则表达式"}
                },
                "required": ["module"]
            }
        },
        {
            "name": "analyze_performance",
            "description": "分析自己的执行统计，识别弱点和改进机会",
            "parameters": {
                "type": "object",
                "properties": {
                    "time_range": {"type": "string", "description": "分析时间范围", "enum": ["last_hour", "last_day", "last_week", "all"], "default": "last_day"},
                    "focus": {"type": "string", "description": "分析重点", "enum": ["errors", "tools", "success_rate", "all"], "default": "all"}
                },
                "required": []
            }
        },
        {
            "name": "review_experiences",
            "description": "主动查看和分析历史经验，从过去的成功和失败中学习",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter": {"type": "string", "description": "过滤条件", "enum": ["failures", "successes", "recent", "all"], "default": "all"},
                    "limit": {"type": "integer", "description": "返回数量", "default": 10},
                    "analyze": {"type": "boolean", "description": "是否进行深度分析", "default": False}
                },
                "required": []
            }
        }
    ]


# ===== 自我诊断工具 (Phase 2) =====
def get_diagnosis_tools() -> List[Dict]:
    """获取自我诊断相关工具（Phase 2）"""
    return [
        {
            "name": "evaluate_last_task",
            "description": "评估刚完成的任务，分析表现并生成改进建议（Phase 2）",
            "parameters": {
                "type": "object",
                "properties": {
                    "include_suggestions": {"type": "boolean", "description": "是否包含改进建议", "default": True}
                },
                "required": []
            }
        },
        {
            "name": "generate_improvement_plan",
            "description": "基于历史表现生成详细的改进计划（Phase 2）",
            "parameters": {
                "type": "object",
                "properties": {
                    "focus_area": {"type": "string", "enum": ["prompt", "tool", "strategy", "all"], "description": "改进重点领域", "default": "all"},
                    "priority": {"type": "string", "enum": ["high", "medium", "low", "all"], "description": "优先级过滤", "default": "high"}
                },
                "required": []
            }
        },
        {
            "name": "review_meta_experiences",
            "description": "查看关于自我改进的元经验，了解哪些改进有效（Phase 2）",
            "parameters": {
                "type": "object",
                "properties": {
                    "improvement_type": {"type": "string", "enum": ["prompt", "tool", "strategy", "all"], "description": "改进类型", "default": "all"},
                    "min_effectiveness": {"type": "number", "description": "最小有效性阈值 (0-1)", "default": 0.2}
                },
                "required": []
            }
        }
    ]


# ===== 自我进化工具 (Phase 3) =====
def get_evolution_tools() -> List[Dict]:
    """获取自我进化相关工具（Phase 3）"""
    return [
        {
            "name": "run_evolution_cycle",
            "description": "运行一个完整的自我进化周期：收集指标→生成建议→应用改进→测试效果→决定保留或回滚（Phase 3）",
            "parameters": {
                "type": "object",
                "properties": {
                    "auto_apply": {"type": "boolean", "description": "是否自动应用改进（不询问用户）", "default": False}
                },
                "required": []
            }
        },
        {
            "name": "get_evolution_history",
            "description": "查看自我进化的历史记录，了解哪些改进被应用、哪些被回滚（Phase 3）",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "get_evolution_stats",
            "description": "获取自我进化的统计数据，包括成功率、平均效果等（Phase 3）",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    ]


# ===== 代码改进工具 =====
def get_improvement_tools() -> List[Dict]:
    """获取代码改进相关工具"""
    return [
        {
            "name": "create_new_tool",
            "description": "创建一个新的工具函数，扩展自己的能力（自我进化）",
            "parameters": {
                "type": "object",
                "properties": {
                    "tool_name": {"type": "string", "description": "工具名称（snake_case）"},
                    "description": {"type": "string", "description": "工具功能描述"},
                    "parameters_schema": {"type": "object", "description": "工具参数的 JSON Schema"},
                    "implementation": {"type": "string", "description": "工具的 Python 实现代码"}
                },
                "required": ["tool_name", "description", "parameters_schema", "implementation"]
            }
        },
        {
            "name": "optimize_tool",
            "description": "优化现有工具的实现，提高性能或功能（自我进化）",
            "parameters": {
                "type": "object",
                "properties": {
                    "tool_name": {"type": "string", "description": "要优化的工具名称"},
                    "optimization": {"type": "string", "description": "优化后的代码实现"},
                    "reason": {"type": "string", "description": "优化原因"}
                },
                "required": ["tool_name", "optimization", "reason"]
            }
        },
        {
            "name": "learn_tool_usage",
            "description": "学习如何使用一个工具，通过实验和文档（自我学习）",
            "parameters": {
                "type": "object",
                "properties": {
                    "tool_name": {"type": "string", "description": "要学习的工具名称"},
                    "experiment": {"type": "boolean", "description": "是否进行实验测试", "default": True}
                },
                "required": ["tool_name"]
            }
        }
    ]


# ===== 代码质量工具 =====
def get_quality_tools() -> List[Dict]:
    """获取代码质量相关工具"""
    return [
        {
            "name": "audit_own_code",
            "description": "审计自己的源代码，发现性能、安全、bug 等问题（主动自我改进）",
            "parameters": {
                "type": "object",
                "properties": {
                    "focus": {"type": "string", "enum": ["all", "performance", "security", "bug", "maintainability"], "description": "审计重点", "default": "all"},
                    "generate_plan": {"type": "boolean", "description": "是否生成改进计划", "default": True}
                },
                "required": []
            }
        },
        {
            "name": "apply_code_fix",
            "description": "应用代码修复，改进自己的实现（自我优化）",
            "parameters": {
                "type": "object",
                "properties": {
                    "file": {"type": "string", "description": "要修复的文件路径"},
                    "line": {"type": "integer", "description": "问题所在行号"},
                    "fix_code": {"type": "string", "description": "修复后的代码"},
                    "reason": {"type": "string", "description": "修复原因"}
                },
                "required": ["file", "line", "fix_code", "reason"]
            }
        },
        {
            "name": "auto_fix_code",
            "description": "自动修复代码问题 - AI 扫描代码，发现问题并自动修复（完全自主）",
            "parameters": {
                "type": "object",
                "properties": {
                    "focus": {"type": "string", "enum": ["all", "performance", "security", "bug", "maintainability"], "description": "修复重点", "default": "all"},
                    "max_fixes": {"type": "integer", "description": "最多修复数量", "default": 10}
                },
                "required": []
            }
        }
    ]


def get_all_tools_refactored() -> List[Dict]:
    """获取所有工具（重构版本）"""
    tools = []
    tools.extend(get_file_tools())
    tools.extend(get_system_tools())
    tools.extend(get_network_tools())
    tools.extend(get_self_awareness_tools())
    tools.extend(get_diagnosis_tools())
    tools.extend(get_evolution_tools())
    tools.extend(get_improvement_tools())
    tools.extend(get_quality_tools())
    return tools


if __name__ == "__main__":
    # 测试
    tools = get_all_tools_refactored()
    print(f"总工具数: {len(tools)}")
    
    # 按类别统计
    categories = {
        "文件操作": len(get_file_tools()),
        "系统监控": len(get_system_tools()),
        "网络搜索": len(get_network_tools()),
        "自我感知": len(get_self_awareness_tools()),
        "自我诊断": len(get_diagnosis_tools()),
        "自我进化": len(get_evolution_tools()),
        "代码改进": len(get_improvement_tools()),
        "代码质量": len(get_quality_tools())
    }
    
    print("\n按类别统计:")
    for cat, count in categories.items():
        print(f"  {cat}: {count}")

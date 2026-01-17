"""Tools refactor compatibility layer - 将tools_refactor.py转换为ToolSchema格式"""

from .common.models import ToolSchema
from tools_refactor import (
    get_file_tools,
    get_system_tools,
    get_network_tools,
    get_self_awareness_tools,
    get_diagnosis_tools,
    get_evolution_tools,
    get_improvement_tools,
    get_quality_tools
)


def get_all_tools_refactored() -> list[ToolSchema]:
    """获取所有工具（重构版本，使用ToolSchema格式）"""
    tools = []
    
    # 合并所有类别的工具
    tool_dicts = []
    tool_dicts.extend(get_file_tools())
    tool_dicts.extend(get_system_tools())
    tool_dicts.extend(get_network_tools())
    tool_dicts.extend(get_self_awareness_tools())
    tool_dicts.extend(get_diagnosis_tools())
    tool_dicts.extend(get_evolution_tools())
    tool_dicts.extend(get_improvement_tools())
    tool_dicts.extend(get_quality_tools())
    
    # 转换为ToolSchema对象
    for tool_dict in tool_dicts:
        tools.append(ToolSchema(
            name=tool_dict["name"],
            description=tool_dict["description"],
            parameters=tool_dict["parameters"]
        ))
    
    return tools


if __name__ == "__main__":
    # 测试
    tools = get_all_tools_refactored()
    print(f"总工具数: {len(tools)}")
    for tool in tools[:5]:
        print(f"  - {tool.name}: {tool.description[:50]}...")

"""工具调用处理器 - 处理工具调用和结果处理"""

import json
from typing import Any, Optional
from langchain_core.messages import ToolMessage, HumanMessage
from tools_refactor import get_all_tools_refactored


class ToolCallProcessor:
    """处理工具调用的执行和结果处理"""
    
    def __init__(self, tools: list, ui_manager):
        """初始化工具调用处理器
        
        Args:
            tools: 工具列表
            ui_manager: WebUI管理器实例
        """
        self.tools = tools
        self.ui_manager = ui_manager
        self.tool_map = {tool["name"]: tool for tool in tools}
    
    async def process_tool_calls(
        self,
        tool_calls: list,
        messages: list,
        iteration: int,
        is_thinking: bool = False
    ) -> tuple[list[dict], bool]:
        """处理工具调用
        
        Args:
            tool_calls: 工具调用列表
            messages: 消息列表（会被修改）
            iteration: 当前迭代次数
            is_thinking: 是否是思考过程
        
        Returns:
            (tool_results, has_error): 工具结果列表和是否有错误
        """
        from tools import execute_tool
        
        tool_results = []
        has_error = False
        
        for tool_call in tool_calls:
            tool_name = tool_call.get("name", "")
            tool_id = tool_call.get("id", "")
            args = tool_call.get("args", {})
            
            if not tool_name:
                continue
            
            # 发送工具调用事件
            if not is_thinking:
                await self.ui_manager.send_tool_call(tool_name, args)
            
            # 执行工具
            try:
                result_data = await execute_tool(tool_name, args)
                result = result_data.get("result", "")
                is_error = result_data.get("error", False)
                error_msg = result_data.get("message", "")
                
                if is_error:
                    has_error = True
                
                # 处理结果以存入历史
                if tool_name == "write_file" and not is_error:
                    try:
                        simplified = {
                            "success": True,
                            "path": result_data.get("path"),
                            "size": result_data.get("size")
                        }
                        result_for_history = json.dumps(simplified, ensure_ascii=False)
                    except Exception:
                        result_for_history = result[:1000]
                else:
                    result_for_history = result[:5000] if len(result) > 5000 else result
                
                # 添加工具消息到历史
                messages.append(ToolMessage(
                    content=result_for_history,
                    tool_call_id=tool_id
                ))
                
                # 发送工具结果
                if not is_thinking:
                    await self.ui_manager.send_tool_result(
                        tool_name,
                        result_for_history,
                        is_error
                    )
                
                tool_results.append({
                    "name": tool_name,
                    "result": result,
                    "is_error": is_error
                })
                
            except Exception as e:
                error_msg = str(e)
                has_error = True
                
                messages.append(ToolMessage(
                    content=error_msg,
                    tool_call_id=tool_id
                ))
                
                if not is_thinking:
                    await self.ui_manager.send_tool_result(
                        tool_name,
                        error_msg,
                        is_error=True
                    )
                
                tool_results.append({
                    "name": tool_name,
                    "result": error_msg,
                    "is_error": True
                })
        
        return tool_results, has_error
    
    def get_tool_schema(self, tool_name: str) -> Optional[dict]:
        """获取工具的schema
        
        Args:
            tool_name: 工具名称
        
        Returns:
            工具schema，如果不存在返回None
        """
        return self.tool_map.get(tool_name)
    
    def get_tool_names(self) -> list[str]:
        """获取所有工具名称"""
        return list(self.tool_map.keys())

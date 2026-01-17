"""Web界面管理器 - 处理WebSocket通信和事件发送"""

from typing import Any
from fastapi import WebSocket


class WebUIManager:
    """管理Web界面和WebSocket通信"""
    
    def __init__(self, websocket: WebSocket):
        """初始化UI管理器
        
        Args:
            websocket: FastAPI WebSocket连接
        """
        self.ws = websocket
    
    async def send_event(self, event_type: str, data: dict):
        """发送事件到前端
        
        Args:
            event_type: 事件类型
            data: 事件数据
        """
        try:
            await self.ws.send_json({"type": event_type, **data})
        except Exception as e:
            # 记录错误但不中断应用
            import logging
            logging.getLogger(__name__).debug(f"Failed to send event {event_type}: {e}")
    
    async def send_status(self, message: str):
        """发送状态消息
        
        Args:
            message: 状态消息
        """
        await self.send_event("status", {"message": message})
    
    async def send_error(self, message: str):
        """发送错误消息
        
        Args:
            message: 错误消息
        """
        await self.send_event("error", {"message": message})
    
    async def send_stream_start(self, iteration: int):
        """发送流开始事件
        
        Args:
            iteration: 迭代次数
        """
        await self.send_event("stream_start", {"iteration": iteration})
    
    async def send_stream_chunk(self, content: str, is_thought: bool = False):
        """发送流数据块
        
        Args:
            content: 内容
            is_thought: 是否是思考过程
        """
        await self.send_event("stream_chunk", {"content": content, "is_thought": is_thought})
    
    async def send_stream_end(self):
        """发送流结束事件"""
        await self.send_event("stream_end", {})
    
    async def send_tool_call(self, tool_name: str, args: dict):
        """发送工具调用事件
        
        Args:
            tool_name: 工具名称
            args: 工具参数
        """
        await self.send_event("tool_call", {"tool": tool_name, "args": args})
    
    async def send_tool_result(self, tool_name: str, result: str, is_error: bool = False):
        """发送工具结果事件
        
        Args:
            tool_name: 工具名称
            result: 工具结果
            is_error: 是否是错误
        """
        await self.send_event("tool_result", {
            "tool": tool_name,
            "result": result[:1000] if len(result) > 1000 else result,
            "is_error": is_error
        })

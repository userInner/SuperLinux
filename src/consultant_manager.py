"""顾问AI管理器 - 管理多个AI顾问的协作"""

from typing import Optional, Dict
from langchain_core.messages import HumanMessage


class ConsultantManager:
    """管理顾问AI的协作和咨询"""
    
    def __init__(self, secondary_engines: dict, ui_manager):
        """初始化顾问管理器
        
        Args:
            secondary_engines: 顾问AI引擎字典 {name: {engine, config}}
            ui_manager: WebUI管理器实例
        """
        self.secondary_engines = secondary_engines
        self.ui_manager = ui_manager
        self.consultation_count = 0
    
    async def consult(
        self,
        problem: str,
        context: str,
        consultant_name: Optional[str] = None
    ) -> Optional[str]:
        """咨询顾问AI获取建议
        
        Args:
            problem: 遇到的问题描述
            context: 相关上下文信息
            consultant_name: 指定顾问名称（可选）
        
        Returns:
            顾问AI的建议，如果咨询失败返回None
        """
        if not self.secondary_engines:
            return None
        
        self.consultation_count += 1
        
        # 选择顾问
        if consultant_name and consultant_name in self.secondary_engines:
            consultant_name = consultant_name
        else:
            # 选择第一个顾问（可以扩展为智能选择）
            consultant_name = list(self.secondary_engines.keys())[0]
        
        consultant = self.secondary_engines[consultant_name]
        
        await self.ui_manager.send_status(
            f"🤝 咨询 {consultant_name}..."
        )
        
        # 构建咨询提示
        consultation_prompt = f"""你是一个专业顾问，帮助解决技术问题。

**问题**: {problem}

**上下文**: {context}

请提供简洁的解决建议（不超过200字）。"""
        
        try:
            response = await consultant["engine"].llm.ainvoke([
                HumanMessage(content=consultation_prompt)
            ])
            
            advice = response.content
            
            await self.ui_manager.send_status(
                f"💡 {consultant_name}: {advice[:100]}..."
            )
            
            return advice
            
        except Exception as e:
            await self.ui_manager.send_status(
                f"⚠️ 咨询失败: {str(e)}"
            )
            return None
    
    def get_consultant_list(self) -> list[str]:
        """获取可用的顾问列表
        
        Returns:
            顾问名称列表
        """
        return list(self.secondary_engines.keys())
    
    def get_consultation_count(self) -> int:
        """获取咨询次数
        
        Returns:
            总咨询次数
        """
        return self.consultation_count
    
    def has_consultants(self) -> bool:
        """是否有可用的顾问
        
        Returns:
            是否有顾问
        """
        return len(self.secondary_engines) > 0

"""
进化机制集成 - 将高级进化功能集成到现有系统
"""

import json
import os
from typing import List, Dict, Optional
from advanced_evolution import (
    ToolFactory,
    PromptSelfHealing,
    EnvironmentAdaptive
)


class EvolutionManager:
    """进化管理器 - 统一管理所有进化机制"""
    
    def __init__(self, db_path: str = "./experience_db"):
        self.db_path = db_path
        os.makedirs(db_path, exist_ok=True)
        
        # 初始化三个核心模块
        self.tool_factory = ToolFactory(db_path)
        self.prompt_healing = PromptSelfHealing(db_path=db_path)
        self.env_adaptive = EnvironmentAdaptive(db_path)
        
        # 进化日志
        self.evolution_log_file = os.path.join(db_path, "evolution_log.json")
        self.evolution_log = self._load_evolution_log()
    
    def _load_evolution_log(self) -> List[Dict]:
        """加载进化日志"""
        if os.path.exists(self.evolution_log_file):
            try:
                with open(self.evolution_log_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return []
        return []
    
    def _save_evolution_log(self):
        """保存进化日志"""
        with open(self.evolution_log_file, 'w', encoding='utf-8') as f:
            json.dump(self.evolution_log, f, indent=2, ensure_ascii=False)
    
    def _log_evolution(self, evolution_type: str, details: Dict):
        """记录进化事件"""
        from datetime import datetime
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": evolution_type,
            "details": details
        }
        
        self.evolution_log.append(log_entry)
        self._save_evolution_log()
    
    # ==================== 自主工具工厂接口 ====================
    
    def track_command_usage(self, commands: List[str], task_type: str = "general") -> Optional[str]:
        """追踪命令使用，自动创建工具
        
        Args:
            commands: 命令列表
            task_type: 任务类型
        
        Returns:
            Optional[str]: 如果创建了工具，返回工具路径
        """
        tool_path = self.tool_factory.record_command_usage(commands, task_type)
        
        if tool_path:
            self._log_evolution("tool_created", {
                "tool_path": tool_path,
                "commands": commands,
                "task_type": task_type
            })
        
        return tool_path
    
    def get_tool_suggestions(self) -> List[Dict]:
        """获取工具创建建议"""
        return self.tool_factory.get_tool_suggestions()
    
    # ==================== Prompt 自愈接口 ====================
    
    def report_prompt_issue(
        self,
        issue_type: str,
        problem: str,
        suggested_fix: str
    ) -> str:
        """报告 Prompt 问题，触发自愈
        
        Args:
            issue_type: 问题类型 ("misunderstanding", "wrong_tool", "missing_step")
            problem: 问题描述
            suggested_fix: 建议修复方案
        
        Returns:
            str: 纠偏记录 ID
        """
        correction_id = self.prompt_healing.record_correction(
            issue_type, problem, suggested_fix
        )
        
        self._log_evolution("prompt_healing", {
            "correction_id": correction_id,
            "issue_type": issue_type,
            "problem": problem
        })
        
        return correction_id
    
    def get_prompt_corrections(self, issue_type: Optional[str] = None) -> List[Dict]:
        """获取 Prompt 纠偏记录"""
        corrections = [
            {
                "id": c.correction_id,
                "timestamp": c.timestamp,
                "issue_type": c.issue_type,
                "problem": c.problem,
                "suggested_fix": c.suggested_fix,
                "effectiveness": c.effectiveness
            }
            for c in self.prompt_healing.corrections
        ]
        
        if issue_type:
            corrections = [c for c in corrections if c["issue_type"] == issue_type]
        
        return sorted(corrections, key=lambda x: x["timestamp"], reverse=True)
    
    # ==================== 环境自适应接口 ====================
    
    def get_adapted_command(self, command_type: str, **kwargs) -> str:
        """获取适配当前环境的命令"""
        return self.env_adaptive.get_adapted_command(command_type, **kwargs)
    
    def install_package(self, package: str) -> str:
        """安装包（环境自适应）"""
        return self.env_adaptive.get_package_manager_command("install", package)
    
    def remove_package(self, package: str) -> str:
        """删除包（环境自适应）"""
        return self.env_adaptive.get_package_manager_command("remove", package)
    
    def update_packages(self) -> str:
        """更新包（环境自适应）"""
        return self.env_adaptive.get_package_manager_command("update", package="")
    
    def start_service(self, service: str) -> str:
        """启动服务（环境自适应）"""
        return self.env_adaptive.get_service_command("start", service)
    
    def stop_service(self, service: str) -> str:
        """停止服务（环境自适应）"""
        return self.env_adaptive.get_service_command("stop", service)
    
    def check_service_status(self, service: str) -> str:
        """检查服务状态（环境自适应）"""
        return self.env_adaptive.get_service_command("status", service)
    
    def get_environment_info(self) -> Dict:
        """获取环境信息"""
        if self.env_adaptive.profile:
            return {
                "distro": self.env_adaptive.profile.distro,
                "version": self.env_adaptive.profile.version,
                "package_manager": self.env_adaptive.profile.package_manager,
                "init_system": self.env_adaptive.profile.init_system,
                "python_path": self.env_adaptive.profile.python_path,
                "node_path": self.env_adaptive.profile.node_path,
                "last_updated": self.env_adaptive.profile.last_updated
            }
        return {}
    
    def relearn_environment(self):
        """重新学习环境"""
        self.env_adaptive.relearn_environment()
        self._log_evolution("environment_relearned", self.get_environment_info())
    
    # ==================== 进化报告 ====================
    
    def generate_evolution_report(self) -> Dict:
        """生成进化报告"""
        # 获取工具工厂统计
        tool_suggestions = self.get_tool_suggestions()
        pattern_count = len(self.tool_factory.patterns)
        
        # 获取 Prompt 纠偏统计
        corrections = self.get_prompt_corrections()
        correction_count = len(corrections)
        
        # 按类型统计
        corrections_by_type = {}
        for c in corrections:
            itype = c["issue_type"]
            corrections_by_type[itype] = corrections_by_type.get(itype, 0) + 1
        
        # 获取环境信息
        env_info = self.get_environment_info()
        
        # 统计进化日志
        evolution_by_type = {}
        for log in self.evolution_log:
            etype = log["type"]
            evolution_by_type[etype] = evolution_by_type.get(etype, 0) + 1
        
        return {
            "summary": {
                "total_patterns": pattern_count,
                "tool_suggestions": len(tool_suggestions),
                "total_corrections": correction_count,
                "environment": f"{env_info.get('distro', 'unknown')} {env_info.get('version', '')}",
                "total_evolutions": len(self.evolution_log)
            },
            "tool_factory": {
                "patterns_tracked": pattern_count,
                "ready_for_creation": len([s for s in tool_suggestions if s["usage_count"] >= 3]),
                "suggestions": tool_suggestions[:5]  # 只返回前5个
            },
            "prompt_healing": {
                "total_corrections": correction_count,
                "by_type": corrections_by_type,
                "recent": corrections[:5]
            },
            "environment": env_info,
            "evolution_history": {
                "by_type": evolution_by_type,
                "recent": self.evolution_log[-5:] if self.evolution_log else []
            }
        }


# ==================== 全局实例 ====================

# 创建全局进化管理器实例
_evolution_manager: Optional[EvolutionManager] = None


def get_evolution_manager(db_path: str = "./experience_db") -> EvolutionManager:
    """获取进化管理器实例（单例）"""
    global _evolution_manager
    if _evolution_manager is None:
        _evolution_manager = EvolutionManager(db_path)
    return _evolution_manager


# ==================== 便捷函数 ====================

def track_commands(commands: List[str], task_type: str = "general") -> Optional[str]:
    """追踪命令使用"""
    return get_evolution_manager().track_command_usage(commands, task_type)


def get_env_command(command_type: str, **kwargs) -> str:
    """获取环境适配的命令"""
    return get_evolution_manager().get_adapted_command(command_type, **kwargs)


def install(package: str) -> str:
    """安装包（环境自适应）"""
    return get_evolution_manager().install_package(package)


def report_issue(issue_type: str, problem: str, fix: str) -> str:
    """报告 Prompt 问题"""
    return get_evolution_manager().report_prompt_issue(issue_type, problem, fix)


def get_evolution_report() -> Dict:
    """获取进化报告"""
    return get_evolution_manager().generate_evolution_report()

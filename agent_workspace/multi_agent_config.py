"""Multi-agent 配置类"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AgentBehaviorConfig:
    """Agent 行为配置"""
    max_retries_per_error: int = 3
    search_attempts_before_consult: int = 2
    enable_rag: bool = True
    
    def __post_init__(self):
        """验证配置"""
        if self.max_retries_per_error < 1:
            raise ValueError("max_retries_per_error must be at least 1")
        if self.search_attempts_before_consult < 0:
            raise ValueError("search_attempts_before_consult cannot be negative")


@dataclass
class MultiAgentConfig:
    """多 AI Agent 完整配置"""
    primary_config: 'AIConfig'
    secondary_configs: list = field(default_factory=list)
    behavior: AgentBehaviorConfig = field(default_factory=AgentBehaviorConfig)
    prompt_type: str = "default"
    experience_db_path: str = "./experience_db"
    
    @classmethod
    def from_params(
        cls,
        primary_config: 'AIConfig',
        secondary_configs: list = None,
        max_retries_per_error: int = 3,
        search_attempts_before_consult: int = 2,
        prompt_type: str = "default",
        enable_rag: bool = True,
        experience_db_path: str = "./experience_db"
    ):
        """从传统参数创建配置（向后兼容）"""
        return cls(
            primary_config=primary_config,
            secondary_configs=secondary_configs or [],
            behavior=AgentBehaviorConfig(
                max_retries_per_error=max_retries_per_error,
                search_attempts_before_consult=search_attempts_before_consult,
                enable_rag=enable_rag
            ),
            prompt_type=prompt_type,
            experience_db_path=experience_db_path
        )

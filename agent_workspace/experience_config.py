"""Experience RAG 配置类"""

from dataclasses import dataclass, field


@dataclass
class ExperienceConfig:
    """经验系统配置"""
    db_path: str = "./experience_db"
    embedding_model: str = "all-MiniLM-L6-v2"
    use_local_embedding: bool = True
    enable_vector_db: bool = True
    json_backup_enabled: bool = True
    max_experiences: int = 1000
    
    def __post_init__(self):
        """验证配置"""
        if self.max_experiences < 1:
            raise ValueError("max_experiences must be at least 1")


@dataclass
class ExperienceSaveRequest:
    """保存请求数据类"""
    problem: str
    solution: str
    steps: list
    tools_used: list
    errors_encountered: list
    docs_consulted: list
    success: bool
    timestamp: str
    tags: list = field(default_factory=list)
    
    @classmethod
    def create(
        cls,
        problem: str,
        solution: str,
        steps: list,
        tools_used: list,
        errors_encountered: list,
        docs_consulted: list,
        success: bool,
        timestamp: str,
        tags: list = None
    ):
        """创建保存请求（向后兼容）"""
        return cls(
            problem=problem,
            solution=solution,
            steps=steps,
            tools_used=tools_used,
            errors_encountered=errors_encountered,
            docs_consulted=docs_consulted,
            success=success,
            timestamp=timestamp,
            tags=tags or []
        )

"""RAG-based experience learning system for the agent."""

import json
import os
import hashlib
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, asdict

# 使用轻量级向量数据库
try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMA = True
except ImportError:
    HAS_CHROMA = False

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False


@dataclass
class Experience:
    """一条经验记录"""
    id: str
    problem: str           # 用户的原始问题
    solution: str          # 成功的解决方案
    steps: list[str]       # 执行的步骤
    tools_used: list[str]  # 使用的工具
    errors_encountered: list[str]  # 遇到的错误
    docs_consulted: list[str]      # 查阅的文档
    success: bool          # 是否成功
    timestamp: str         # 时间戳
    tags: list[str]        # 标签（用于分类）


class ExperienceRAG:
    """基于 RAG 的经验学习系统。
    
    功能：
    1. 保存成功解决问题的经验
    2. 遇到新问题时检索相似经验
    3. 将相关经验注入到 prompt 中
    """
    
    def __init__(
        self,
        db_path: str = "./experience_db",
        embedding_model: str = "all-MiniLM-L6-v2",
        use_local_embedding: bool = True
    ):
        self.db_path = db_path
        self.embedding_model_name = embedding_model
        self.use_local_embedding = use_local_embedding
        
        self.collection = None
        self.embedding_model = None
        self._initialized = False
        
        # 简单的 JSON 备份（当向量库不可用时）
        self.json_backup_path = os.path.join(db_path, "experiences.json")
    
    def initialize(self) -> bool:
        """初始化 RAG 系统"""
        os.makedirs(self.db_path, exist_ok=True)
        
        if HAS_CHROMA and HAS_SENTENCE_TRANSFORMERS:
            try:
                # 初始化 embedding 模型
                print(f"   Loading embedding model: {self.embedding_model_name}...")
                self.embedding_model = SentenceTransformer(self.embedding_model_name)
                
                # 初始化 ChromaDB
                self.client = chromadb.PersistentClient(
                    path=self.db_path,
                    settings=Settings(anonymized_telemetry=False)
                )
                
                self.collection = self.client.get_or_create_collection(
                    name="agent_experiences",
                    metadata={"description": "Agent problem-solving experiences"}
                )
                
                self._initialized = True
                count = self.collection.count()
                print(f"   ✅ RAG system initialized ({count} experiences)")
                return True
                
            except Exception as e:
                print(f"   ⚠️ RAG initialization failed: {e}")
                print(f"   Falling back to JSON storage")
                self._initialized = False
                return False
        else:
            missing = []
            if not HAS_CHROMA:
                missing.append("chromadb")
            if not HAS_SENTENCE_TRANSFORMERS:
                missing.append("sentence-transformers")
            print(f"   ⚠️ Missing packages: {', '.join(missing)}")
            print(f"   Install with: pip install {' '.join(missing)}")
            print(f"   Falling back to JSON storage")
            return False
    
    def _generate_id(self, problem: str) -> str:
        """生成经验 ID"""
        content = f"{problem}{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _extract_tags(self, problem: str, tools_used: list[str]) -> list[str]:
        """从问题和工具中提取标签"""
        tags = []
        
        # 基于关键词的标签
        keywords = {
            "nginx": ["nginx", "web-server", "reverse-proxy"],
            "docker": ["docker", "container"],
            "mysql": ["mysql", "database"],
            "postgresql": ["postgresql", "database"],
            "redis": ["redis", "cache"],
            "ssh": ["ssh", "remote"],
            "systemd": ["systemd", "service"],
            "网络": ["network"],
            "磁盘": ["disk", "storage"],
            "内存": ["memory"],
            "cpu": ["cpu", "performance"],
            "python": ["python"],
            "node": ["nodejs"],
            "git": ["git", "version-control"],
        }
        
        problem_lower = problem.lower()
        for keyword, tag_list in keywords.items():
            if keyword in problem_lower:
                tags.extend(tag_list)
        
        # 基于工具的标签
        tool_tags = {
            "run_command": "command",
            "web_search": "search",
            "fetch_webpage": "documentation",
            "read_file": "file-operation",
            "write_file": "file-operation",
            "get_system_stats": "monitoring",
        }
        for tool in tools_used:
            if tool in tool_tags:
                tags.append(tool_tags[tool])
        
        return list(set(tags))
    
    def save_experience(
        self,
        problem: str,
        solution: str,
        steps: list[str],
        tools_used: list[str],
        errors_encountered: list[str] = None,
        docs_consulted: list[str] = None,
        success: bool = True
    ) -> str:
        """保存一条经验"""
        exp_id = self._generate_id(problem)
        tags = self._extract_tags(problem, tools_used)
        
        experience = Experience(
            id=exp_id,
            problem=problem,
            solution=solution,
            steps=steps,
            tools_used=tools_used,
            errors_encountered=errors_encountered or [],
            docs_consulted=docs_consulted or [],
            success=success,
            timestamp=datetime.now().isoformat(),
            tags=tags
        )
        
        # 保存到向量数据库
        if self._initialized and self.collection:
            try:
                # 生成 embedding
                text_to_embed = f"{problem}\n{solution}\n{' '.join(tags)}"
                embedding = self.embedding_model.encode(text_to_embed).tolist()
                
                self.collection.add(
                    ids=[exp_id],
                    embeddings=[embedding],
                    documents=[json.dumps(asdict(experience), ensure_ascii=False)],
                    metadatas=[{
                        "problem": problem[:500],
                        "success": str(success),
                        "tags": ",".join(tags),
                        "timestamp": experience.timestamp
                    }]
                )
                print(f"   💾 Experience saved to vector DB: {exp_id}")
            except Exception as e:
                print(f"   ⚠️ Failed to save to vector DB: {e}")
        
        # 同时保存到 JSON 备份
        self._save_to_json(experience)
        
        return exp_id
    
    def _save_to_json(self, experience: Experience):
        """保存到 JSON 文件"""
        experiences = []
        if os.path.exists(self.json_backup_path):
            try:
                with open(self.json_backup_path, "r", encoding="utf-8") as f:
                    experiences = json.load(f)
            except:
                experiences = []
        
        experiences.append(asdict(experience))
        
        # 只保留最近 1000 条
        if len(experiences) > 1000:
            experiences = experiences[-1000:]
        
        os.makedirs(os.path.dirname(self.json_backup_path), exist_ok=True)
        with open(self.json_backup_path, "w", encoding="utf-8") as f:
            json.dump(experiences, f, ensure_ascii=False, indent=2)
    
    def search_similar(
        self,
        query: str,
        top_k: int = 3,
        success_only: bool = True
    ) -> list[Experience]:
        """搜索相似的经验"""
        results = []
        
        # 优先使用向量搜索
        if self._initialized and self.collection:
            try:
                query_embedding = self.embedding_model.encode(query).tolist()
                
                where_filter = {"success": "True"} if success_only else None
                
                search_results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k,
                    where=where_filter
                )
                
                if search_results and search_results["documents"]:
                    for doc in search_results["documents"][0]:
                        try:
                            exp_dict = json.loads(doc)
                            results.append(Experience(**exp_dict))
                        except:
                            continue
                
                return results
            except Exception as e:
                print(f"   ⚠️ Vector search failed: {e}")
        
        # 回退到简单的关键词搜索
        return self._search_json_fallback(query, top_k, success_only)
    
    def _search_json_fallback(
        self,
        query: str,
        top_k: int,
        success_only: bool
    ) -> list[Experience]:
        """JSON 文件的简单关键词搜索"""
        if not os.path.exists(self.json_backup_path):
            return []
        
        try:
            with open(self.json_backup_path, "r", encoding="utf-8") as f:
                experiences = json.load(f)
        except:
            return []
        
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        scored = []
        for exp_dict in experiences:
            if success_only and not exp_dict.get("success", False):
                continue
            
            problem = exp_dict.get("problem", "").lower()
            tags = exp_dict.get("tags", [])
            
            # 简单的相关性评分
            score = 0
            for word in query_words:
                if word in problem:
                    score += 2
                if word in tags:
                    score += 1
            
            if score > 0:
                scored.append((score, Experience(**exp_dict)))
        
        # 按分数排序
        scored.sort(key=lambda x: x[0], reverse=True)
        return [exp for _, exp in scored[:top_k]]
    
    def format_experiences_for_prompt(
        self,
        experiences: list[Experience],
        max_length: int = 2000
    ) -> str:
        """将经验格式化为 prompt 可用的文本"""
        if not experiences:
            return ""
        
        lines = ["## 相关历史经验\n"]
        total_length = 0
        
        for i, exp in enumerate(experiences, 1):
            exp_text = f"""
### 经验 {i}
**问题**: {exp.problem[:200]}
**解决方案**: {exp.solution[:300]}
**使用的工具**: {', '.join(exp.tools_used[:5])}
**关键步骤**: {'; '.join(exp.steps[:3])}
"""
            if exp.docs_consulted:
                exp_text += f"**参考文档**: {', '.join(exp.docs_consulted[:2])}\n"
            
            if total_length + len(exp_text) > max_length:
                break
            
            lines.append(exp_text)
            total_length += len(exp_text)
        
        lines.append("\n请参考以上经验，但根据当前情况灵活调整。\n")
        return "".join(lines)
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        stats = {
            "total_experiences": 0,
            "successful": 0,
            "failed": 0,
            "vector_db_available": self._initialized
        }
        
        if self._initialized and self.collection:
            stats["total_experiences"] = self.collection.count()
        
        if os.path.exists(self.json_backup_path):
            try:
                with open(self.json_backup_path, "r", encoding="utf-8") as f:
                    experiences = json.load(f)
                    stats["json_backup_count"] = len(experiences)
                    stats["successful"] = sum(1 for e in experiences if e.get("success"))
                    stats["failed"] = len(experiences) - stats["successful"]
            except:
                pass
        
        return stats


# 全局实例
_experience_rag: Optional[ExperienceRAG] = None


def get_experience_rag(db_path: str = "./experience_db") -> ExperienceRAG:
    """获取全局 RAG 实例"""
    global _experience_rag
    if _experience_rag is None:
        _experience_rag = ExperienceRAG(db_path=db_path)
        _experience_rag.initialize()
    return _experience_rag

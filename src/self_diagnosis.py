"""
Phase 2: 自我诊断系统

让 AI 能够自动评估自己的表现并生成改进建议
"""

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Optional
from enum import Enum


class ImprovementType(Enum):
    """改进类型"""
    PROMPT = "prompt"
    TOOL = "tool"
    STRATEGY = "strategy"


class Priority(Enum):
    """优先级"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class TaskEvaluation:
    """任务评估结果"""
    task_id: str
    task: str
    timestamp: str
    
    # 评估维度 (0-100)
    success_score: float
    efficiency_score: float
    tool_usage_score: float
    error_handling_score: float
    user_satisfaction_score: float
    
    # 总分
    overall_score: float
    
    # 评语
    comments: list[str]
    
    # 原始数据
    execution_time: float
    steps_count: int
    tools_used: list[str]
    errors_count: int


@dataclass
class ImprovementSuggestion:
    """改进建议"""
    id: str
    type: ImprovementType
    priority: Priority
    
    issue: str  # 识别的问题
    suggestion: str  # 具体建议
    expected_improvement: str  # 预期效果
    
    # 相关数据
    affected_area: str  # 影响的领域
    evidence: list[str]  # 证据
    
    timestamp: str
    status: str = "pending"  # pending/applied/rejected


@dataclass
class MetaExperience:
    """元经验 - 关于自我改进的经验"""
    id: str
    improvement_type: str
    
    problem_identified: str
    solution_applied: str
    
    # 改进前后的指标
    before_metrics: dict
    after_metrics: dict
    
    # 有效性 (0-1)
    effectiveness: float
    
    timestamp: str
    notes: str = ""
    
    def is_effective(self) -> bool:
        """判断改进是否有效"""
        return self.effectiveness > 0.2  # 提升超过 20%


class TaskEvaluator:
    """任务评估器"""
    
    def __init__(self):
        self.evaluation_history = []
    
    def evaluate_task(
        self,
        task: str,
        result: str,
        steps: list[str],
        tools_used: list[str],
        errors: list[str],
        execution_time: float,
        success: bool
    ) -> TaskEvaluation:
        """评估单个任务"""
        
        task_id = self._generate_id(task)
        
        # 评估各个维度
        success_score = self._evaluate_success(success, errors)
        efficiency_score = self._evaluate_efficiency(steps, execution_time)
        tool_usage_score = self._evaluate_tool_usage(tools_used, task)
        error_handling_score = self._evaluate_error_handling(errors)
        user_satisfaction_score = self._estimate_satisfaction(result, success)
        
        # 计算总分（加权平均）
        overall_score = (
            success_score * 0.35 +
            efficiency_score * 0.20 +
            tool_usage_score * 0.15 +
            error_handling_score * 0.15 +
            user_satisfaction_score * 0.15
        )
        
        # 生成评语
        comments = self._generate_comments({
            "success": success_score,
            "efficiency": efficiency_score,
            "tool_usage": tool_usage_score,
            "error_handling": error_handling_score,
            "user_satisfaction": user_satisfaction_score
        })
        
        evaluation = TaskEvaluation(
            task_id=task_id,
            task=task[:200],
            timestamp=datetime.now().isoformat(),
            success_score=success_score,
            efficiency_score=efficiency_score,
            tool_usage_score=tool_usage_score,
            error_handling_score=error_handling_score,
            user_satisfaction_score=user_satisfaction_score,
            overall_score=overall_score,
            comments=comments,
            execution_time=execution_time,
            steps_count=len(steps),
            tools_used=tools_used,
            errors_count=len(errors)
        )
        
        self.evaluation_history.append(evaluation)
        return evaluation
    
    def _evaluate_success(self, success: bool, errors: list[str]) -> float:
        """评估成功度"""
        if success and not errors:
            return 100.0
        elif success and errors:
            return 80.0 - min(len(errors) * 10, 30)
        else:
            return max(20.0 - len(errors) * 5, 0)
    
    def _evaluate_efficiency(self, steps: list[str], execution_time: float) -> float:
        """评估效率"""
        # 步骤数评分
        if len(steps) <= 3:
            step_score = 100
        elif len(steps) <= 5:
            step_score = 80
        elif len(steps) <= 8:
            step_score = 60
        else:
            step_score = max(40 - (len(steps) - 8) * 5, 20)
        
        # 时间评分
        if execution_time < 10:
            time_score = 100
        elif execution_time < 30:
            time_score = 80
        elif execution_time < 60:
            time_score = 60
        else:
            time_score = max(40 - (execution_time - 60) / 10, 20)
        
        return (step_score + time_score) / 2
    
    def _evaluate_tool_usage(self, tools_used: list[str], task: str) -> float:
        """评估工具使用"""
        if not tools_used:
            return 50.0
        
        # 工具多样性
        unique_tools = len(set(tools_used))
        diversity_score = min(unique_tools * 20, 100)
        
        # 工具相关性（简单启发式）
        task_lower = task.lower()
        relevant_tools = 0
        
        if "文件" in task_lower or "代码" in task_lower:
            if any(t in ["read_file", "write_file", "edit_file"] for t in tools_used):
                relevant_tools += 1
        
        if "搜索" in task_lower or "查找" in task_lower:
            if any(t in ["web_search", "search_in_files"] for t in tools_used):
                relevant_tools += 1
        
        if "系统" in task_lower or "监控" in task_lower:
            if any(t in ["get_system_stats", "get_cpu_info"] for t in tools_used):
                relevant_tools += 1
        
        relevance_score = min(relevant_tools * 30, 100)
        
        return (diversity_score * 0.4 + relevance_score * 0.6)
    
    def _evaluate_error_handling(self, errors: list[str]) -> float:
        """评估错误处理"""
        if not errors:
            return 100.0
        
        # 错误数量越少越好
        error_count_score = max(100 - len(errors) * 15, 0)
        
        return error_count_score
    
    def _estimate_satisfaction(self, result: str, success: bool) -> float:
        """估算用户满意度"""
        if not success:
            return 30.0
        
        # 基于结果长度和内容的简单估算
        if len(result) < 50:
            return 60.0
        elif len(result) < 200:
            return 80.0
        else:
            return 90.0
    
    def _generate_comments(self, dimensions: dict) -> list[str]:
        """生成评语"""
        comments = []
        
        if dimensions["success"] >= 90:
            comments.append("✅ 任务完成度优秀")
        elif dimensions["success"] < 60:
            comments.append("⚠️ 任务完成度需要改进")
        
        if dimensions["efficiency"] >= 80:
            comments.append("⚡ 执行效率很高")
        elif dimensions["efficiency"] < 60:
            comments.append("🐌 执行效率偏低，可以优化")
        
        if dimensions["tool_usage"] < 60:
            comments.append("🔧 工具使用可以更合理")
        
        if dimensions["error_handling"] < 70:
            comments.append("🐛 错误处理需要加强")
        
        return comments
    
    def _generate_id(self, task: str) -> str:
        """生成任务 ID"""
        import hashlib
        content = f"{task}{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]


class SuggestionGenerator:
    """改进建议生成器"""
    
    def __init__(self, db_path: str = "./experience_db"):
        self.db_path = db_path
        self.suggestions_file = os.path.join(db_path, "suggestions.json")
    
    def generate_suggestions(
        self,
        evaluations: list[TaskEvaluation],
        focus_area: str = "all",
        priority: str = "all"
    ) -> list[ImprovementSuggestion]:
        """基于评估结果生成改进建议"""
        
        suggestions = []
        
        # 分析评估数据
        analysis = self._analyze_evaluations(evaluations)
        
        # 生成不同类型的建议
        if focus_area in ["prompt", "all"]:
            suggestions.extend(self._generate_prompt_suggestions(analysis))
        
        if focus_area in ["tool", "all"]:
            suggestions.extend(self._generate_tool_suggestions(analysis))
        
        if focus_area in ["strategy", "all"]:
            suggestions.extend(self._generate_strategy_suggestions(analysis))
        
        # 过滤优先级
        if priority != "all":
            suggestions = [s for s in suggestions if s.priority.value == priority]
        
        # 保存建议
        self._save_suggestions(suggestions)
        
        return suggestions
    
    def _analyze_evaluations(self, evaluations: list[TaskEvaluation]) -> dict:
        """分析评估数据"""
        if not evaluations:
            return {}
        
        total = len(evaluations)
        
        return {
            "total_tasks": total,
            "avg_success": sum(e.success_score for e in evaluations) / total,
            "avg_efficiency": sum(e.efficiency_score for e in evaluations) / total,
            "avg_tool_usage": sum(e.tool_usage_score for e in evaluations) / total,
            "avg_error_handling": sum(e.error_handling_score for e in evaluations) / total,
            "total_errors": sum(e.errors_count for e in evaluations),
            "avg_execution_time": sum(e.execution_time for e in evaluations) / total,
            "all_tools_used": [tool for e in evaluations for tool in e.tools_used]
        }
    
    def _generate_prompt_suggestions(self, analysis: dict) -> list[ImprovementSuggestion]:
        """生成 Prompt 优化建议"""
        suggestions = []
        
        # 成功率低
        if analysis.get("avg_success", 100) < 70:
            suggestions.append(ImprovementSuggestion(
                id=self._generate_id("prompt_success"),
                type=ImprovementType.PROMPT,
                priority=Priority.HIGH,
                issue=f"任务成功率偏低 ({analysis['avg_success']:.1f}%)",
                suggestion="在 SYSTEM_PROMPT 中强化'先探索后行动'原则，要求 AI 在不确定时先使用工具收集信息",
                expected_improvement="预计提升成功率 15-20%",
                affected_area="prompts.py - SYSTEM_PROMPT_V2",
                evidence=[
                    f"最近 {analysis['total_tasks']} 个任务的平均成功率: {analysis['avg_success']:.1f}%",
                    "建议添加更多错误处理指导"
                ],
                timestamp=datetime.now().isoformat()
            ))
        
        # 效率低
        if analysis.get("avg_efficiency", 100) < 60:
            suggestions.append(ImprovementSuggestion(
                id=self._generate_id("prompt_efficiency"),
                type=ImprovementType.PROMPT,
                priority=Priority.MEDIUM,
                issue=f"执行效率偏低 ({analysis['avg_efficiency']:.1f}分)",
                suggestion="在 Prompt 中添加'一次性获取足够信息'的指导，减少重复工具调用",
                expected_improvement="预计减少 30% 的执行时间",
                affected_area="prompts.py - 工具使用策略",
                evidence=[
                    f"平均执行时间: {analysis.get('avg_execution_time', 0):.1f}秒",
                    "建议优化工具调用策略"
                ],
                timestamp=datetime.now().isoformat()
            ))
        
        return suggestions
    
    def _generate_tool_suggestions(self, analysis: dict) -> list[ImprovementSuggestion]:
        """生成工具改进建议"""
        suggestions = []
        
        # 工具使用单一
        unique_tools = len(set(analysis.get("all_tools_used", [])))
        if unique_tools < 5:
            suggestions.append(ImprovementSuggestion(
                id=self._generate_id("tool_diversity"),
                type=ImprovementType.TOOL,
                priority=Priority.MEDIUM,
                issue=f"工具使用种类较少 (只用了 {unique_tools} 种工具)",
                suggestion="扩展工具集，添加更多专用工具（如 search_in_files, analyze_trends 等）",
                expected_improvement="提高问题解决能力 25%",
                affected_area="tools.py - 工具定义",
                evidence=[
                    f"常用工具: {list(set(analysis.get('all_tools_used', [])))[:5]}",
                    "建议添加更多专用工具"
                ],
                timestamp=datetime.now().isoformat()
            ))
        
        return suggestions
    
    def _generate_strategy_suggestions(self, analysis: dict) -> list[ImprovementSuggestion]:
        """生成策略调整建议"""
        suggestions = []
        
        # 错误处理差
        if analysis.get("avg_error_handling", 100) < 60:
            suggestions.append(ImprovementSuggestion(
                id=self._generate_id("strategy_error"),
                type=ImprovementType.STRATEGY,
                priority=Priority.HIGH,
                issue=f"错误处理能力不足 (总错误数: {analysis.get('total_errors', 0)})",
                suggestion="实施'三次重试'策略：遇到错误时，先分析原因，调整方法，最多重试3次",
                expected_improvement="减少 40% 的失败任务",
                affected_area="执行策略",
                evidence=[
                    f"总错误数: {analysis.get('total_errors', 0)}",
                    "建议加强错误恢复机制"
                ],
                timestamp=datetime.now().isoformat()
            ))
        
        return suggestions
    
    def _save_suggestions(self, suggestions: list[ImprovementSuggestion]):
        """保存建议到文件"""
        os.makedirs(self.db_path, exist_ok=True)
        
        # 读取现有建议
        existing = []
        if os.path.exists(self.suggestions_file):
            try:
                with open(self.suggestions_file, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except:
                existing = []
        
        # 添加新建议（转换 Enum 为字符串）
        for suggestion in suggestions:
            suggestion_dict = asdict(suggestion)
            # 转换 Enum 为字符串
            suggestion_dict["type"] = suggestion.type.value
            suggestion_dict["priority"] = suggestion.priority.value
            existing.append(suggestion_dict)
        
        # 只保留最近 100 条
        if len(existing) > 100:
            existing = existing[-100:]
        
        # 保存
        with open(self.suggestions_file, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
    
    def _generate_id(self, prefix: str) -> str:
        """生成建议 ID"""
        import hashlib
        content = f"{prefix}{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]


class MetaExperienceManager:
    """元经验管理器"""
    
    def __init__(self, db_path: str = "./experience_db"):
        self.db_path = db_path
        self.meta_file = os.path.join(db_path, "meta_experiences.json")
    
    def record_improvement(
        self,
        improvement_type: str,
        problem: str,
        solution: str,
        before_metrics: dict,
        after_metrics: dict
    ) -> MetaExperience:
        """记录一次改进"""
        
        # 计算有效性
        effectiveness = self._calculate_effectiveness(before_metrics, after_metrics)
        
        meta_exp = MetaExperience(
            id=self._generate_id(problem),
            improvement_type=improvement_type,
            problem_identified=problem,
            solution_applied=solution,
            before_metrics=before_metrics,
            after_metrics=after_metrics,
            effectiveness=effectiveness,
            timestamp=datetime.now().isoformat()
        )
        
        # 保存
        self._save_meta_experience(meta_exp)
        
        return meta_exp
    
    def get_effective_improvements(
        self,
        improvement_type: str = "all",
        min_effectiveness: float = 0.2
    ) -> list[MetaExperience]:
        """获取有效的改进"""
        
        all_meta = self._load_meta_experiences()
        
        # 过滤
        filtered = [
            m for m in all_meta
            if m.effectiveness >= min_effectiveness
            and (improvement_type == "all" or m.improvement_type == improvement_type)
        ]
        
        # 按有效性排序
        filtered.sort(key=lambda x: x.effectiveness, reverse=True)
        
        return filtered
    
    def _calculate_effectiveness(self, before: dict, after: dict) -> float:
        """计算改进有效性"""
        if not before or not after:
            return 0.0
        
        # 计算主要指标的改进
        improvements = []
        
        for key in ["success_rate", "efficiency", "error_rate"]:
            if key in before and key in after:
                before_val = before[key]
                after_val = after[key]
                
                if before_val > 0:
                    if key == "error_rate":
                        # 错误率降低是好事
                        improvement = (before_val - after_val) / before_val
                    else:
                        # 其他指标提升是好事
                        improvement = (after_val - before_val) / before_val
                    
                    improvements.append(improvement)
        
        if not improvements:
            return 0.0
        
        # 返回平均改进率
        return sum(improvements) / len(improvements)
    
    def _save_meta_experience(self, meta_exp: MetaExperience):
        """保存元经验"""
        os.makedirs(self.db_path, exist_ok=True)
        
        all_meta = self._load_meta_experiences()
        all_meta.append(meta_exp)
        
        # 只保留最近 50 条
        if len(all_meta) > 50:
            all_meta = all_meta[-50:]
        
        with open(self.meta_file, "w", encoding="utf-8") as f:
            json.dump(
                [asdict(m) for m in all_meta],
                f,
                ensure_ascii=False,
                indent=2
            )
    
    def _load_meta_experiences(self) -> list[MetaExperience]:
        """加载元经验"""
        if not os.path.exists(self.meta_file):
            return []
        
        try:
            with open(self.meta_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [MetaExperience(**item) for item in data]
        except:
            return []
    
    def _generate_id(self, problem: str) -> str:
        """生成 ID"""
        import hashlib
        content = f"{problem}{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]


# 全局实例
_evaluator: Optional[TaskEvaluator] = None
_suggestion_generator: Optional[SuggestionGenerator] = None
_meta_manager: Optional[MetaExperienceManager] = None


def get_evaluator() -> TaskEvaluator:
    """获取全局评估器"""
    global _evaluator
    if _evaluator is None:
        _evaluator = TaskEvaluator()
    return _evaluator


def get_suggestion_generator() -> SuggestionGenerator:
    """获取全局建议生成器"""
    global _suggestion_generator
    if _suggestion_generator is None:
        _suggestion_generator = SuggestionGenerator()
    return _suggestion_generator


def get_meta_manager() -> MetaExperienceManager:
    """获取全局元经验管理器"""
    global _meta_manager
    if _meta_manager is None:
        _meta_manager = MetaExperienceManager()
    return _meta_manager

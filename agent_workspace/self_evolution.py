"""
Phase 3: 自我进化系统

让 AI 能够自动修改自己、测试改进、持续进化
"""

import json
import os
import shutil
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional
import asyncio


@dataclass
class CodeVersion:
    """代码版本"""
    version_id: str
    timestamp: str
    description: str
    files_modified: dict[str, str]  # {文件路径: 修改内容}
    reason: str
    expected_improvement: str


@dataclass
class EvolutionCycle:
    """进化周期"""
    cycle_id: str
    start_time: str
    end_time: Optional[str]
    
    # 改进前的指标
    before_metrics: dict
    
    # 应用的改进
    improvements_applied: list[dict]
    
    # 改进后的指标
    after_metrics: Optional[dict]
    
    # 结果
    success: bool
    effectiveness: float  # 0-1
    
    # 是否回滚
    rolled_back: bool
    rollback_reason: Optional[str]


class PromptEvolver:
    """Prompt 进化器 - 自动优化系统提示词"""
    
    def __init__(self, prompt_file: str = "src/prompts.py"):
        self.prompt_file = prompt_file
        self.backup_dir = ".evolution_backups/prompts"
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def backup_current_prompt(self) -> str:
        """备份当前 Prompt"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(self.backup_dir, f"prompts_{timestamp}.py")
        shutil.copy2(self.prompt_file, backup_path)
        return backup_path
    
    def apply_improvement(self, suggestion: dict) -> bool:
        """应用改进建议到 Prompt"""
        try:
            # 备份
            backup_path = self.backup_current_prompt()
            print(f"   📦 备份当前 Prompt: {backup_path}")
            
            # 读取当前 Prompt
            with open(self.prompt_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 根据建议类型应用改进
            suggestion_text = suggestion.get("suggestion", "")
            issue = suggestion.get("issue", "")
            
            # 简单的改进应用逻辑
            if "成功率" in issue and "先探索后行动" in suggestion_text:
                # 强化"先探索后行动"原则
                new_principle = """
5. **验证后执行**: 在执行关键操作前，先验证条件是否满足
6. **错误预防**: 预见可能的错误，提前采取预防措施"""
                
                if "## 核心原则" in content and new_principle not in content:
                    content = content.replace(
                        "4. **高效执行**: 尽量减少不必要的工具调用，一次获取足够信息",
                        "4. **高效执行**: 尽量减少不必要的工具调用，一次获取足够信息" + new_principle
                    )
            
            elif "效率" in issue and "一次性获取" in suggestion_text:
                # 添加效率优化指导
                efficiency_guide = """

### 效率优化原则
- 批量操作优于多次单独操作
- 一次性获取所有需要的信息
- 避免重复的工具调用
- 使用缓存避免重复查询"""
                
                if "## 工具使用策略" in content and efficiency_guide not in content:
                    content = content.replace(
                        "## 工具使用策略",
                        "## 工具使用策略" + efficiency_guide
                    )
            
            elif "工具" in issue and "扩展工具集" in suggestion_text:
                # 添加工具使用指导
                tool_guide = """

### 工具选择策略
- 优先使用专用工具而非通用工具
- 组合使用多个工具解决复杂问题
- 定期探索新工具的使用场景"""
                
                if "## 工具使用策略" in content and tool_guide not in content:
                    content = content.replace(
                        "## 工具使用策略",
                        "## 工具使用策略" + tool_guide
                    )
            
            # 写入修改后的内容
            with open(self.prompt_file, "w", encoding="utf-8") as f:
                f.write(content)
            
            print(f"   ✅ 已应用改进到 Prompt")
            return True
            
        except Exception as e:
            print(f"   ❌ 应用改进失败: {e}")
            return False
    
    def rollback(self, backup_path: str) -> bool:
        """回滚到备份版本"""
        try:
            shutil.copy2(backup_path, self.prompt_file)
            print(f"   ↩️  已回滚到: {backup_path}")
            return True
        except Exception as e:
            print(f"   ❌ 回滚失败: {e}")
            return False


class EvolutionEngine:
    """进化引擎 - 协调整个自我进化过程"""
    
    def __init__(self, db_path: str = "./experience_db"):
        self.db_path = db_path
        self.evolution_log = os.path.join(db_path, "evolution_log.json")
        self.prompt_evolver = PromptEvolver()
        
        self.cycles: list[EvolutionCycle] = []
        self._load_cycles()
    
    def _load_cycles(self):
        """加载进化历史"""
        if os.path.exists(self.evolution_log):
            try:
                with open(self.evolution_log, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.cycles = [EvolutionCycle(**c) for c in data]
            except Exception:
                # 文件不存在或损坏，使用空列表
                self.cycles = []
    
    def _save_cycles(self):
        """保存进化历史"""
        os.makedirs(self.db_path, exist_ok=True)
        with open(self.evolution_log, "w", encoding="utf-8") as f:
            json.dump(
                [asdict(c) for c in self.cycles],
                f,
                ensure_ascii=False,
                indent=2
            )
    
    async def run_evolution_cycle(
        self,
        test_tasks: list[str] = None,
        auto_apply: bool = False
    ) -> EvolutionCycle:
        """运行一个完整的进化周期"""
        
        cycle_id = f"cycle_{len(self.cycles) + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print(f"\n{'='*60}")
        print(f"🧬 开始进化周期: {cycle_id}")
        print(f"{'='*60}")
        
        # 1. 收集当前指标
        print("\n📊 步骤 1: 收集当前性能指标")
        before_metrics = await self._collect_metrics()
        print(f"   当前成功率: {before_metrics.get('success_rate', 0)*100:.1f}%")
        print(f"   当前平均效率: {before_metrics.get('avg_efficiency', 0):.1f}")
        
        # 2. 生成改进建议
        print("\n💡 步骤 2: 生成改进建议")
        suggestions = await self._generate_suggestions()
        
        if not suggestions:
            print("   ℹ️  当前表现已经很好，无需改进")
            return None
        
        print(f"   生成了 {len(suggestions)} 条改进建议")
        for i, s in enumerate(suggestions[:3], 1):
            print(f"   {i}. [{s['priority']}] {s['issue']}")
        
        # 3. 选择要应用的改进
        print("\n🎯 步骤 3: 选择改进方案")
        selected = suggestions[0]  # 选择优先级最高的
        print(f"   选择: {selected['issue']}")
        print(f"   方案: {selected['suggestion'][:80]}...")
        
        if not auto_apply:
            response = input("\n   是否应用此改进？(y/n): ")
            if response.lower() != 'y':
                print("   ⏭️  跳过此改进")
                return None
        
        # 4. 应用改进
        print("\n🔧 步骤 4: 应用改进")
        backup_path = None
        
        if selected['type'] == 'prompt':
            success = self.prompt_evolver.apply_improvement(selected)
            if success:
                backup_path = self.prompt_evolver.backup_dir
        else:
            print(f"   ⚠️  暂不支持 {selected['type']} 类型的自动应用")
            success = False
        
        if not success:
            print("   ❌ 应用改进失败")
            return None
        
        # 5. 测试改进效果
        print("\n🧪 步骤 5: 测试改进效果")
        print("   运行测试任务...")
        
        if test_tasks:
            # 运行测试任务
            await self._run_test_tasks(test_tasks)
        else:
            # 等待一段时间收集数据
            print("   等待收集新数据...")
            await asyncio.sleep(2)
        
        # 6. 收集改进后的指标
        print("\n📈 步骤 6: 收集改进后的指标")
        after_metrics = await self._collect_metrics()
        print(f"   新成功率: {after_metrics.get('success_rate', 0)*100:.1f}%")
        print(f"   新平均效率: {after_metrics.get('avg_efficiency', 0):.1f}")
        
        # 7. 计算改进效果
        print("\n📊 步骤 7: 评估改进效果")
        effectiveness = self._calculate_effectiveness(before_metrics, after_metrics)
        print(f"   改进有效性: {effectiveness*100:.1f}%")
        
        # 8. 决定是否保留改进
        success = effectiveness > 0.1  # 提升超过 10% 才算成功
        
        if success:
            print(f"   ✅ 改进有效！保留此改进")
            rolled_back = False
            rollback_reason = None
        else:
            print(f"   ❌ 改进无效，回滚...")
            if backup_path:
                # 找到最新的备份
                backups = sorted(os.listdir(backup_path))
                if backups:
                    latest_backup = os.path.join(backup_path, backups[-1])
                    self.prompt_evolver.rollback(latest_backup)
            rolled_back = True
            rollback_reason = f"改进效果不佳 (仅提升 {effectiveness*100:.1f}%)"
        
        # 9. 记录进化周期
        cycle = EvolutionCycle(
            cycle_id=cycle_id,
            start_time=datetime.now().isoformat(),
            end_time=datetime.now().isoformat(),
            before_metrics=before_metrics,
            improvements_applied=[selected],
            after_metrics=after_metrics,
            success=success,
            effectiveness=effectiveness,
            rolled_back=rolled_back,
            rollback_reason=rollback_reason
        )
        
        self.cycles.append(cycle)
        self._save_cycles()
        
        # 10. 记录元经验
        if success:
            await self._record_meta_experience(selected, before_metrics, after_metrics, effectiveness)
        
        print(f"\n{'='*60}")
        print(f"🎉 进化周期完成: {'成功' if success else '失败'}")
        print(f"{'='*60}\n")
        
        return cycle
    
    async def _collect_metrics(self) -> dict:
        """收集当前性能指标"""
        from .self_diagnosis import get_evaluator
        
        evaluator = get_evaluator()
        
        if not evaluator.evaluation_history:
            return {
                "success_rate": 0.5,
                "avg_efficiency": 50.0,
                "avg_tool_usage": 50.0,
                "error_count": 0
            }
        
        # 只看最近的评估
        recent = evaluator.evaluation_history[-10:]
        
        return {
            "success_rate": sum(e.success_score for e in recent) / len(recent) / 100,
            "avg_efficiency": sum(e.efficiency_score for e in recent) / len(recent),
            "avg_tool_usage": sum(e.tool_usage_score for e in recent) / len(recent),
            "error_count": sum(e.errors_count for e in recent)
        }
    
    async def _generate_suggestions(self) -> list[dict]:
        """生成改进建议"""
        from .self_diagnosis import get_evaluator, get_suggestion_generator
        
        evaluator = get_evaluator()
        generator = get_suggestion_generator()
        
        if not evaluator.evaluation_history:
            return []
        
        suggestions = generator.generate_suggestions(
            evaluations=evaluator.evaluation_history,
            focus_area="all",
            priority="high"
        )
        
        return [
            {
                "type": s.type.value,
                "priority": s.priority.value,
                "issue": s.issue,
                "suggestion": s.suggestion,
                "expected_improvement": s.expected_improvement
            }
            for s in suggestions
        ]
    
    async def _run_test_tasks(self, tasks: list[str]):
        """运行测试任务"""
        # 这里可以实际运行一些测试任务
        # 暂时只是模拟
        for task in tasks[:3]:
            print(f"   - 测试: {task}")
            await asyncio.sleep(0.5)
    
    def _calculate_effectiveness(self, before: dict, after: dict) -> float:
        """计算改进有效性"""
        improvements = []
        
        for key in ["success_rate", "avg_efficiency", "avg_tool_usage"]:
            if key in before and key in after:
                before_val = before[key]
                after_val = after[key]
                
                if before_val > 0:
                    improvement = (after_val - before_val) / before_val
                    improvements.append(improvement)
        
        # 错误数量减少是好事
        if "error_count" in before and "error_count" in after:
            before_errors = before["error_count"]
            after_errors = after["error_count"]
            if before_errors > 0:
                error_improvement = (before_errors - after_errors) / before_errors
                improvements.append(error_improvement)
        
        if not improvements:
            return 0.0
        
        return sum(improvements) / len(improvements)
    
    async def _record_meta_experience(
        self,
        improvement: dict,
        before: dict,
        after: dict,
        effectiveness: float
    ):
        """记录元经验"""
        from .self_diagnosis import get_meta_manager
        
        manager = get_meta_manager()
        manager.record_improvement(
            improvement_type=improvement['type'],
            problem=improvement['issue'],
            solution=improvement['suggestion'],
            before_metrics=before,
            after_metrics=after
        )
    
    def get_evolution_history(self) -> list[dict]:
        """获取进化历史"""
        return [
            {
                "cycle_id": c.cycle_id,
                "start_time": c.start_time,
                "success": c.success,
                "effectiveness": f"{c.effectiveness*100:.1f}%",
                "improvements": len(c.improvements_applied),
                "rolled_back": c.rolled_back
            }
            for c in self.cycles
        ]
    
    def get_evolution_stats(self) -> dict:
        """获取进化统计"""
        if not self.cycles:
            return {
                "total_cycles": 0,
                "successful_cycles": 0,
                "success_rate": 0,
                "avg_effectiveness": 0
            }
        
        successful = [c for c in self.cycles if c.success]
        
        return {
            "total_cycles": len(self.cycles),
            "successful_cycles": len(successful),
            "success_rate": len(successful) / len(self.cycles),
            "avg_effectiveness": sum(c.effectiveness for c in successful) / len(successful) if successful else 0,
            "total_improvements": sum(len(c.improvements_applied) for c in self.cycles),
            "rollbacks": sum(1 for c in self.cycles if c.rolled_back)
        }


class AutoEvolutionScheduler:
    """自动进化调度器 - 定期运行进化周期"""
    
    def __init__(self, engine: EvolutionEngine):
        self.engine = engine
        self.running = False
    
    async def start(
        self,
        interval_hours: int = 24,
        min_tasks_before_evolution: int = 10
    ):
        """启动自动进化"""
        self.running = True
        
        print(f"\n🤖 自动进化调度器已启动")
        print(f"   检查间隔: {interval_hours} 小时")
        print(f"   最小任务数: {min_tasks_before_evolution}")
        
        while self.running:
            try:
                # 检查是否有足够的数据
                from .self_diagnosis import get_evaluator
                evaluator = get_evaluator()
                
                if len(evaluator.evaluation_history) >= min_tasks_before_evolution:
                    print(f"\n⏰ 触发自动进化 (已完成 {len(evaluator.evaluation_history)} 个任务)")
                    await self.engine.run_evolution_cycle(auto_apply=True)
                
                # 等待下一个周期
                await asyncio.sleep(interval_hours * 3600)
                
            except Exception as e:
                print(f"❌ 自动进化出错: {e}")
                await asyncio.sleep(3600)  # 出错后等待1小时
    
    def stop(self):
        """停止自动进化"""
        self.running = False
        print("\n🛑 自动进化调度器已停止")


# 全局实例
_evolution_engine: Optional[EvolutionEngine] = None
_auto_scheduler: Optional[AutoEvolutionScheduler] = None


def get_evolution_engine() -> EvolutionEngine:
    """获取全局进化引擎"""
    global _evolution_engine
    if _evolution_engine is None:
        _evolution_engine = EvolutionEngine()
    return _evolution_engine


def get_auto_scheduler() -> AutoEvolutionScheduler:
    """获取全局自动调度器"""
    global _auto_scheduler
    if _auto_scheduler is None:
        _auto_scheduler = AutoEvolutionScheduler(get_evolution_engine())
    return _auto_scheduler

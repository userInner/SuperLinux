# Phase 2: 自我诊断 - 实施计划

## 🎯 目标

让 AI 能够自动评估自己的表现并生成改进建议，不仅能"看到"自己，还能"诊断"自己。

## 📅 时间规划

**预计时间**: 2-3 周  
**开始时间**: Phase 1 完成后  
**前置条件**: Phase 1 的自我感知能力

## 🔧 核心功能

### 1. 自动任务后评估 (Auto Task Evaluation)

#### 功能描述
每次任务完成后，AI 自动评估自己的表现。

#### 实现要点
```python
class TaskEvaluator:
    """任务评估器"""
    
    def evaluate_task(
        self,
        task: str,
        result: str,
        steps: list[str],
        tools_used: list[str],
        errors: list[str],
        execution_time: float
    ) -> TaskEvaluation:
        """评估单个任务"""
        
        # 评估维度
        dimensions = {
            "success": self._evaluate_success(result, errors),
            "efficiency": self._evaluate_efficiency(steps, execution_time),
            "tool_usage": self._evaluate_tool_usage(tools_used),
            "error_handling": self._evaluate_error_handling(errors),
            "user_satisfaction": self._estimate_satisfaction(result)
        }
        
        # 计算总分
        overall_score = self._calculate_score(dimensions)
        
        # 生成评语
        comments = self._generate_comments(dimensions)
        
        return TaskEvaluation(
            score=overall_score,
            dimensions=dimensions,
            comments=comments,
            timestamp=datetime.now()
        )
```

#### 评估维度

1. **成功度** (0-100)
   - 任务是否完成
   - 结果是否符合预期
   - 是否有未解决的错误

2. **效率** (0-100)
   - 执行步骤数
   - 执行时间
   - 工具调用次数

3. **工具使用** (0-100)
   - 是否使用了合适的工具
   - 是否有冗余的工具调用
   - 是否遗漏了有用的工具

4. **错误处理** (0-100)
   - 遇到错误时的反应
   - 是否有效恢复
   - 是否学习了错误

5. **用户满意度** (0-100)
   - 估算用户是否满意
   - 响应是否清晰
   - 是否需要用户多次澄清

#### 新增工具

```python
ToolSchema(
    name="evaluate_last_task",
    description="评估刚完成的任务，分析表现并生成改进建议",
    parameters={
        "type": "object",
        "properties": {
            "include_suggestions": {
                "type": "boolean",
                "description": "是否包含改进建议",
                "default": True
            }
        }
    }
)
```

### 2. 智能改进建议生成 (Improvement Suggestions)

#### 功能描述
基于评估结果，自动生成具体的改进建议。

#### 建议类型

1. **Prompt 优化建议**
   ```python
   {
       "type": "prompt_optimization",
       "issue": "在软件包安装任务中经常忘记更新包列表",
       "suggestion": "在 SYSTEM_PROMPT 中添加：'安装软件包前先运行 apt-get update'",
       "expected_improvement": "减少 50% 的安装失败",
       "priority": "high"
   }
   ```

2. **工具改进建议**
   ```python
   {
       "type": "tool_improvement",
       "issue": "web_search 工具经常返回 403 错误",
       "suggestion": "添加重试机制和多个 User-Agent 轮换",
       "expected_improvement": "提高 30% 的搜索成功率",
       "priority": "medium"
   }
   ```

3. **策略调整建议**
   ```python
   {
       "type": "strategy_adjustment",
       "issue": "复杂任务经常一次性失败",
       "suggestion": "将复杂任务分解为多个子任务，逐步验证",
       "expected_improvement": "提高 40% 的复杂任务成功率",
       "priority": "high"
   }
   ```

#### 新增工具

```python
ToolSchema(
    name="generate_improvement_plan",
    description="基于历史表现生成详细的改进计划",
    parameters={
        "type": "object",
        "properties": {
            "focus_area": {
                "type": "string",
                "enum": ["prompts", "tools", "strategy", "all"],
                "default": "all"
            },
            "priority": {
                "type": "string",
                "enum": ["high", "medium", "low", "all"],
                "default": "high"
            }
        }
    }
)
```

### 3. 元经验系统 (Meta-Experience)

#### 功能描述
不仅记录"如何解决问题"，还记录"如何改进自己"。

#### 数据结构

```python
@dataclass
class MetaExperience:
    """元经验 - 关于自我改进的经验"""
    id: str
    improvement_type: str  # prompt/tool/strategy
    problem_identified: str  # 识别的问题
    solution_applied: str  # 应用的解决方案
    before_metrics: dict  # 改进前的指标
    after_metrics: dict  # 改进后的指标
    effectiveness: float  # 改进效果 (0-1)
    timestamp: str
    
    def is_effective(self) -> bool:
        """判断改进是否有效"""
        return self.effectiveness > 0.2  # 提升超过 20%
```

#### 示例

```python
meta_exp = MetaExperience(
    id="meta_001",
    improvement_type="prompt",
    problem_identified="软件包安装失败率高 (40%)",
    solution_applied="在 prompt 中添加'安装前先更新包列表'",
    before_metrics={"success_rate": 0.6, "avg_retries": 2.3},
    after_metrics={"success_rate": 0.85, "avg_retries": 1.1},
    effectiveness=0.42,  # 提升 42%
    timestamp="2026-01-20T10:00:00"
)
```

#### 新增工具

```python
ToolSchema(
    name="review_meta_experiences",
    description="查看关于自我改进的元经验，了解哪些改进有效",
    parameters={
        "type": "object",
        "properties": {
            "improvement_type": {
                "type": "string",
                "enum": ["prompt", "tool", "strategy", "all"]
            },
            "min_effectiveness": {
                "type": "number",
                "description": "最小有效性阈值 (0-1)",
                "default": 0.2
            }
        }
    }
)
```

### 4. 趋势分析 (Trend Analysis)

#### 功能描述
跟踪能力随时间的变化，识别进步和退化。

#### 分析维度

1. **成功率趋势**
   ```python
   {
       "metric": "success_rate",
       "trend": "improving",  # improving/stable/declining
       "current": 0.85,
       "last_week": 0.78,
       "last_month": 0.72,
       "change_rate": "+18%"
   }
   ```

2. **效率趋势**
   ```python
   {
       "metric": "avg_execution_time",
       "trend": "improving",
       "current": 12.5,  # 秒
       "last_week": 15.2,
       "change_rate": "-17.8%"
   }
   ```

3. **错误率趋势**
   ```python
   {
       "metric": "error_rate",
       "trend": "declining",  # 好事！
       "current": 0.15,
       "last_week": 0.22,
       "change_rate": "-31.8%"
   }
   ```

#### 退化检测

```python
class RegressionDetector:
    """退化检测器"""
    
    def detect_regression(
        self,
        metric: str,
        current: float,
        historical: list[float],
        threshold: float = 0.1
    ) -> Optional[RegressionAlert]:
        """检测能力退化"""
        
        avg_historical = sum(historical) / len(historical)
        
        # 如果当前值比历史平均低 10% 以上
        if current < avg_historical * (1 - threshold):
            return RegressionAlert(
                metric=metric,
                current=current,
                expected=avg_historical,
                severity="high" if current < avg_historical * 0.8 else "medium",
                message=f"{metric} 下降了 {(1 - current/avg_historical)*100:.1f}%"
            )
        
        return None
```

#### 新增工具

```python
ToolSchema(
    name="analyze_trends",
    description="分析能力随时间的变化趋势，识别进步和退化",
    parameters={
        "type": "object",
        "properties": {
            "time_window": {
                "type": "string",
                "enum": ["week", "month", "all"],
                "default": "week"
            },
            "metrics": {
                "type": "array",
                "items": {"type": "string"},
                "description": "要分析的指标",
                "default": ["success_rate", "efficiency", "error_rate"]
            }
        }
    }
)
```

## 📊 实现步骤

### Week 1: 自动评估系统

**目标**: 实现任务自动评估

- [ ] Day 1-2: 设计评估框架
  - 定义评估维度
  - 设计评分算法
  - 创建数据结构

- [ ] Day 3-4: 实现评估器
  - 实现 `TaskEvaluator` 类
  - 实现各个评估维度
  - 添加 `evaluate_last_task` 工具

- [ ] Day 5: 集成和测试
  - 集成到主流程
  - 编写测试
  - 验证评估准确性

### Week 2: 改进建议系统

**目标**: 实现智能改进建议生成

- [ ] Day 1-2: 建议生成器
  - 实现 `SuggestionGenerator` 类
  - 定义建议模板
  - 实现优先级排序

- [ ] Day 3-4: 元经验系统
  - 实现 `MetaExperience` 数据结构
  - 实现元经验存储和检索
  - 添加 `review_meta_experiences` 工具

- [ ] Day 5: 测试和优化
  - 验证建议质量
  - 优化生成算法
  - 编写文档

### Week 3: 趋势分析和整合

**目标**: 实现趋势分析和系统整合

- [ ] Day 1-2: 趋势分析
  - 实现 `TrendAnalyzer` 类
  - 实现退化检测
  - 添加 `analyze_trends` 工具

- [ ] Day 3-4: 系统整合
  - 更新 Prompt
  - 集成所有新功能
  - 端到端测试

- [ ] Day 5: 文档和发布
  - 编写完整文档
  - 创建演示脚本
  - 发布 Phase 2

## 🧪 测试计划

### 单元测试

```python
# test_phase2.py

async def test_task_evaluation():
    """测试任务评估"""
    evaluator = TaskEvaluator()
    
    result = evaluator.evaluate_task(
        task="安装 nginx",
        result="成功安装",
        steps=["更新包列表", "安装 nginx", "启动服务"],
        tools_used=["run_command"],
        errors=[],
        execution_time=15.2
    )
    
    assert result.score > 80
    assert result.dimensions["success"] == 100

async def test_suggestion_generation():
    """测试建议生成"""
    generator = SuggestionGenerator()
    
    suggestions = generator.generate_suggestions(
        focus_area="prompts",
        priority="high"
    )
    
    assert len(suggestions) > 0
    assert all(s.priority == "high" for s in suggestions)

async def test_trend_analysis():
    """测试趋势分析"""
    analyzer = TrendAnalyzer()
    
    trends = analyzer.analyze_trends(
        time_window="week",
        metrics=["success_rate"]
    )
    
    assert "success_rate" in trends
    assert trends["success_rate"]["trend"] in ["improving", "stable", "declining"]
```

### 集成测试

```python
async def test_full_cycle():
    """测试完整的自我诊断循环"""
    
    # 1. 执行任务
    result = await agent.chat("安装 nginx")
    
    # 2. 自动评估
    evaluation = await agent.evaluate_last_task()
    assert evaluation.score > 0
    
    # 3. 生成建议
    suggestions = await agent.generate_improvement_plan()
    assert len(suggestions) > 0
    
    # 4. 查看趋势
    trends = await agent.analyze_trends()
    assert "success_rate" in trends
```

## 📈 成功指标

### 定量指标

- ✅ 评估准确率 > 85%
- ✅ 建议采纳率 > 60%
- ✅ 改进有效率 > 70%
- ✅ 趋势预测准确率 > 80%

### 定性指标

- ✅ AI 能准确评估自己的表现
- ✅ 生成的建议具体、可操作
- ✅ 能识别能力退化并预警
- ✅ 元经验系统有效运作

## 🔒 安全考虑

### Phase 2 的安全性

- ✅ 只评估和建议，不自动修改
- ✅ 所有建议需要人工审核
- ✅ 元经验数据可以回滚
- ✅ 趋势分析只读取数据

### 为 Phase 3 做准备

Phase 3 将允许 AI 修改自己的代码，需要：
- 沙盒测试环境
- 自动回滚机制
- 人工审核流程
- 版本控制系统

## 💡 创新点

### 1. 多维度评估
不只看成功/失败，还看效率、工具使用、错误处理等

### 2. 元学习
不仅学习"如何解决问题"，还学习"如何改进自己"

### 3. 趋势预测
不仅看当前状态，还预测未来趋势

### 4. 退化检测
主动识别能力下降，及时预警

## 📚 参考资料

- [Phase 1 实现文档](PHASE1_SELF_AWARENESS.md)
- [Experience RAG 系统](../src/experience_rag.py)
- [自我进化 AI 系统计划书](../自我进化AI系统-项目计划书.md)

## 🚀 Phase 3 预览

Phase 2 完成后，Phase 3 将实现：

### 自我修改能力
- AI 能修改自己的 Prompt
- AI 能优化工具实现
- AI 能调整策略参数

### 安全机制
- 沙盒测试
- 自动回滚
- 人工审核
- 版本控制

### 预期时间
3-4 周

---

**Phase 2 状态**: 📋 计划中  
**开始时间**: Phase 1 完成后  
**预计完成**: 2-3 周

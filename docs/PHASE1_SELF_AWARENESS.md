# Phase 1: 自我感知 - 实现文档

## 🎯 目标

让 AI 能够"看到"自己的代码和运行状态，这是自我进化的第一步。

## ✅ 已实现的功能

### 1. 读取自己的代码 (`read_own_code`)

AI 现在可以读取自己的源代码，理解自己是如何实现的。

**功能**:
- 读取指定模块的源代码（tools, prompts, agent, experience_rag, multi_agent）
- 支持搜索特定内容（使用正则表达式）
- 自动提取函数和类的列表
- 限制输出大小，避免信息过载

**使用场景**:
```python
# 查看自己的 prompt 设计
await execute_tool("read_own_code", {
    "module": "prompts"
})

# 搜索特定功能的实现
await execute_tool("read_own_code", {
    "module": "tools",
    "search_pattern": "web_search"
})
```

**示例对话**:
```
用户: 你是如何处理错误的？
AI: 让我查看一下自己的代码... [调用 read_own_code]
    我发现在 tools.py 中，每个工具都有 try-except 包装...
```

### 2. 分析自己的性能 (`analyze_performance`)

AI 可以分析自己的执行统计，识别弱点和改进机会。

**功能**:
- 统计成功率（成功/失败任务数）
- 分析最常见的错误
- 统计工具使用频率
- 生成改进建议

**使用场景**:
```python
# 分析最近一天的表现
await execute_tool("analyze_performance", {
    "time_range": "last_day",
    "focus": "all"
})

# 只关注错误
await execute_tool("analyze_performance", {
    "time_range": "last_week",
    "focus": "errors"
})
```

**输出示例**:
```json
{
  "overall_stats": {
    "total_experiences": 45,
    "successful": 38,
    "failed": 7
  },
  "analysis": {
    "success_rate": {
      "success_percentage": 84.44,
      "total_tasks": 45
    },
    "errors": {
      "total_errors": 12,
      "top_errors": [
        {"error": "Command not found: xyz", "count": 3}
      ]
    }
  },
  "improvement_suggestions": [
    "⚠️ 发现 12 个错误，建议优化错误处理策略",
    "🔍 最常见错误: 'Command not found' (出现 3 次)"
  ]
}
```

### 3. 查看历史经验 (`review_experiences`)

AI 可以主动查看历史经验，从成功和失败中学习。

**功能**:
- 过滤经验（失败/成功/最近/全部）
- 分析经验中的模式（常见问题、有效工具、标签）
- 深度分析选项

**使用场景**:
```python
# 查看最近的失败案例
await execute_tool("review_experiences", {
    "filter": "failures",
    "limit": 5,
    "analyze": True
})

# 查看成功案例学习
await execute_tool("review_experiences", {
    "filter": "successes",
    "limit": 10
})
```

**输出示例**:
```json
{
  "total_found": 5,
  "experiences": [
    {
      "id": "abc123",
      "problem": "安装 nginx 失败",
      "success": false,
      "errors": ["Package not found"],
      "tools_used": ["run_command", "web_search"]
    }
  ],
  "patterns": {
    "common_problems": {"nginx": 3, "docker": 2},
    "effective_tools": {"web_search": 8, "run_command": 15},
    "common_tags": ["web-server", "command"]
  }
}
```

## 🔄 工作流程

### 典型的自我感知循环

```
1. 遇到问题
   ↓
2. 查看历史经验 (review_experiences)
   "之前遇到过类似问题吗？"
   ↓
3. 尝试解决
   ↓
4. 如果失败，分析原因 (analyze_performance)
   "我在这类问题上的成功率如何？"
   ↓
5. 查看自己的实现 (read_own_code)
   "我的错误处理逻辑是否需要改进？"
   ↓
6. 记录经验（自动）
   ↓
7. 下次遇到类似问题时，从步骤 2 开始
```

## 📊 Prompt 更新

更新了 `SYSTEM_PROMPT_V2`，添加了：

1. **自我感知能力说明** - 让 AI 知道自己有这些能力
2. **使用场景指导** - 何时应该使用这些工具
3. **自我改进循环** - 如何形成学习闭环

关键更新：
```python
## 🧠 自我感知能力（新增！）

你现在可以"看到"自己的内部实现，分析自己的表现，并从历史经验中学习：

### 何时使用自我感知工具

✅ **应该使用的场景**:
1. **遇到重复错误时** - 用 analyze_performance 查看是否之前也遇到过
2. **开始复杂任务前** - 用 review_experiences 查找相似的成功案例
3. **用户询问你的能力时** - 用 read_own_code 了解自己的实现
4. **任务失败后** - 用 analyze_performance 分析失败原因
5. **定期自我反思** - 主动分析自己的表现趋势
```

## 🧪 测试

运行测试脚本验证功能：

```bash
# 基础功能测试
python test_self_awareness.py

# 交互式演示
python examples/self_awareness_demo.py
```

## 📈 效果评估

### 成功指标

- ✅ AI 能读取自己的源代码
- ✅ AI 能分析自己的性能统计
- ✅ AI 能查看和分析历史经验
- ✅ AI 能基于分析提出改进建议

### 预期行为变化

**之前**:
```
用户: 安装 nginx
AI: [尝试] → 失败 → "抱歉，失败了"
```

**现在**:
```
用户: 安装 nginx
AI: [查看历史] → "我之前成功安装过，使用了 apt-get update 然后..."
    [尝试] → 成功！
```

## 🚀 下一步：Phase 2

Phase 1 让 AI 能"看到"自己，Phase 2 将让 AI 能"诊断"自己：

### Phase 2: 自我诊断（计划）

1. **自动任务后评估**
   - 每次任务完成后自动触发自我评估
   - 评分：成功/失败、效率、用户满意度

2. **生成改进建议**
   - 基于评估结果生成具体建议
   - 建议类型：Prompt 优化、工具改进、策略调整

3. **记录元经验**
   - 不仅记录"如何解决问题"
   - 还记录"如何改进自己"

4. **趋势分析**
   - 跟踪能力随时间的变化
   - 识别退化（某些能力变差）

## 💡 使用建议

### 对于用户

1. **鼓励 AI 自我反思**
   ```
   "分析一下你最近的表现"
   "你在哪些方面做得好？哪些需要改进？"
   ```

2. **让 AI 从失败中学习**
   ```
   "刚才失败了，查看一下你之前是否遇到过类似问题"
   "总结一下你在这类任务上的成功率"
   ```

3. **定期让 AI 自我检查**
   ```
   "查看你的代码，确认你的错误处理是否完善"
   "分析你最常用的工具，是否需要扩展工具集？"
   ```

### 对于开发者

1. **监控自我感知工具的使用频率**
   - 如果 AI 从不使用这些工具，可能需要调整 prompt
   - 如果过度使用，可能需要优化触发条件

2. **分析 AI 的改进建议**
   - AI 提出的建议是否合理？
   - 可以作为系统优化的参考

3. **扩展自我感知能力**
   - 添加更多分析维度（响应时间、资源使用等）
   - 支持更细粒度的代码分析

## 🔒 安全考虑

### 当前限制

- ✅ AI 只能**读取**自己的代码，不能修改
- ✅ 分析仅基于已记录的经验数据
- ✅ 不会访问系统关键文件

### Phase 3 的安全挑战

Phase 3 将允许 AI 修改自己的代码，需要：
- 沙盒测试环境
- 自动回滚机制
- 人工审核流程
- 版本控制

## 📚 参考资料

- [自我进化 AI 系统 - 项目计划书](../自我进化AI系统-项目计划书.md)
- [Experience RAG 实现](../src/experience_rag.py)
- [工具实现](../src/tools.py)
- [Prompt 设计](../src/prompts.py)

---

**Phase 1 完成时间**: 2026-01-17  
**下一个里程碑**: Phase 2 - 自我诊断

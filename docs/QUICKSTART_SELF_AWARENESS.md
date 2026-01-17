# 🧠 自我感知能力 - 快速入门

## 5 分钟上手

### 1. 验证功能

```bash
# 运行测试
python3 test_self_awareness.py
```

应该看到：
```
✅ 所有测试通过！AI 已具备自我感知能力。
```

### 2. 与 AI 对话

启动 AI：
```bash
python3 -m src.cli
```

### 3. 试试这些对话

#### 让 AI 查看自己的代码

```
你: 查看你的 prompts 模块，告诉我你的核心原则是什么？

AI: [调用 read_own_code] 
    我查看了自己的 prompts.py，发现我的核心原则包括：
    1. 自主解决问题 - 持续工作直到完全解决
    2. 先探索后行动 - 不确定时先收集信息
    3. 从经验中学习 - 查看历史经验
    4. 高效执行 - 减少不必要的工具调用
```

#### 让 AI 分析自己的表现

```
你: 分析一下你最近的表现，成功率如何？

AI: [调用 analyze_performance]
    我分析了最近的表现：
    - 成功率: 84.4% (38/45 任务)
    - 最常见错误: "Command not found" (3次)
    - 最常用工具: run_command (15次), web_search (8次)
    
    改进建议：
    - 在执行命令前先检查命令是否存在
    - 优化错误处理策略
```

#### 让 AI 从失败中学习

```
你: 查看你最近的失败案例，总结一下你在哪些方面容易失败？

AI: [调用 review_experiences filter=failures]
    我查看了最近的 5 个失败案例：
    
    1. 软件包安装失败 (3次)
       - 原因: 没有先更新包列表
       - 改进: 安装前先运行 apt-get update
    
    2. 网络请求失败 (2次)
       - 原因: 超时或 403 错误
       - 改进: 添加重试机制和更好的错误处理
    
    我发现我在软件包管理方面需要改进。
```

#### 让 AI 主动自我改进

```
你: 基于你对自己的分析，提出 3 个改进建议

AI: 基于我的自我分析，我提出以下改进建议：
    
    1. **优化软件包安装流程**
       - 当前问题: 经常忘记更新包列表
       - 改进方案: 在 prompts 中添加"安装前先更新"的提醒
       - 预期效果: 减少 50% 的安装失败
    
    2. **增强错误处理**
       - 当前问题: 遇到 403 错误就放弃
       - 改进方案: 添加重试机制，尝试不同的 User-Agent
       - 预期效果: 提高网络请求成功率
    
    3. **扩展工具集**
       - 当前问题: 只用了 5 种工具
       - 改进方案: 学习使用更多工具（如 search_in_files）
       - 预期效果: 更高效地解决问题
```

## 🎯 实际应用场景

### 场景 1: 重复错误

```
你: 安装 nginx
AI: [尝试] → 失败
你: 你之前遇到过这个错误吗？
AI: [调用 analyze_performance focus=errors]
    是的，我发现这个错误出现过 3 次，都是因为没有先更新包列表。
    让我先运行 apt-get update...
    [成功安装]
```

### 场景 2: 复杂任务

```
你: 配置一个 Web 服务器
AI: [调用 review_experiences] 
    我查看了历史，发现之前成功配置过类似的服务器。
    我会按照这个流程：
    1. 安装 nginx
    2. 配置虚拟主机
    3. 启动服务
    4. 测试连接
    [开始执行]
```

### 场景 3: 能力查询

```
你: 你能做什么？
AI: [调用 read_own_code module=all]
    让我查看一下自己的实现...
    
    我具备以下能力：
    - 文件操作: 读写、编辑、搜索
    - 系统监控: CPU、内存、磁盘、服务
    - 网络功能: 搜索、获取网页
    - 命令执行: 安全的 Linux 命令
    - 自我感知: 查看代码、分析性能、学习经验
    
    [调用 analyze_performance]
    我的历史成功率是 84.4%，擅长系统管理和问题诊断。
```

## 🔄 自我改进循环

AI 现在会自动形成学习循环：

```
任务 → 查看历史 → 执行 → 记录结果 → 分析表现 → 改进策略 → 下次任务
```

### 观察 AI 的进化

1. **第一次遇到问题**: 可能失败
2. **第二次遇到**: 查看历史，成功率提高
3. **第三次遇到**: 直接应用最佳实践，快速成功

## 📊 监控 AI 的成长

### 查看统计

```python
from src.experience_rag import get_experience_rag

rag = get_experience_rag()
stats = rag.get_stats()
print(stats)
```

输出：
```json
{
  "total_experiences": 45,
  "successful": 38,
  "failed": 7,
  "vector_db_available": true,
  "json_backup_count": 45
}
```

### 查看经验数据库

```bash
# 查看 JSON 备份
cat experience_db/experiences.json | jq '.[] | {problem, success, tools_used}'
```

## 💡 最佳实践

### 1. 定期让 AI 自我反思

每天或每周：
```
你: 分析一下你这周的表现，有什么改进？
```

### 2. 失败后立即分析

任务失败时：
```
你: 刚才失败了，查看一下你之前是否遇到过类似问题
```

### 3. 复杂任务前查看历史

开始新任务前：
```
你: 在开始之前，查看你是否有相关经验
```

### 4. 鼓励 AI 提出建议

定期询问：
```
你: 你认为自己应该如何改进？
```

## 🚀 下一步

Phase 1 让 AI 能"看到"自己，接下来：

- **Phase 2**: 自我诊断 - 自动评估和生成改进建议
- **Phase 3**: 自我修改 - AI 能修改自己的代码
- **Phase 4**: 持续进化 - 版本管理和 A/B 测试

## 🐛 故障排除

### 问题: AI 不使用自我感知工具

**原因**: Prompt 可能需要调整

**解决**:
```python
# 在对话中明确要求
"请使用 analyze_performance 工具分析..."
```

### 问题: 没有历史经验数据

**原因**: 刚开始使用，还没有积累经验

**解决**:
```bash
# 多使用几次 AI，让它积累经验
python3 -m src.cli
# 执行一些任务...
```

### 问题: 向量数据库初始化失败

**原因**: 缺少依赖

**解决**:
```bash
pip install chromadb sentence-transformers
```

## 📚 更多资源

- [完整文档](PHASE1_SELF_AWARENESS.md)
- [演示脚本](../examples/self_awareness_demo.py)
- [测试脚本](../test_self_awareness.py)
- [项目计划](../自我进化AI系统-项目计划书.md)

---

**开始使用**: `python3 -m src.cli`  
**运行测试**: `python3 test_self_awareness.py`  
**查看演示**: `python3 examples/self_awareness_demo.py`

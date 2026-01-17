# LangGraph + MCP Linux Agent

基于 LangGraph 和 MCP (Model Context Protocol) 的 Linux 智能体系统，具备自主思考与工具执行能力。

## 特性

- 🧠 **智能编排**: 基于 LangGraph 的 ReAct 循环，支持多步推理
- 🔧 **工具解耦**: 通过 MCP 协议实现大脑与工具的彻底解耦
- 🔒 **安全控制**: 沙盒化文件操作、危险命令检测、人工审批机制
- 💾 **状态持久化**: 支持断点续传和会话恢复
- 🔌 **多模型支持**: 支持 OpenAI、Anthropic Claude、DeepSeek 等模型
- 🌟 **自我感知** (新!): AI 能查看自己的代码、分析性能、从历史中学习

## 快速开始

### 安装

```bash
# 克隆项目
git clone <repository-url>
cd langgraph-mcp-agent

# 安装依赖
pip install -e ".[dev]"
```

### 配置

```bash
# 复制配置模板
cp config.example.yaml config.yaml

# 设置 API Key
export OPENAI_API_KEY=sk-your-key-here
```

### 运行

```bash
# 交互模式
python -m src.cli

# 或使用配置文件
python -m src.cli --config config.yaml

# 单次命令
python -m src.cli --command "查看当前系统 CPU 使用率"
```

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                      用户交互层                              │
│                    (CLI / API)                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Orchestrator 层                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ ReActGraph  │  │ LLMEngine   │  │ CheckpointManager   │ │
│  │ (状态机)    │  │ (模型抽象)  │  │ (状态持久化)        │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    MCP Client 层                            │
│  ┌─────────────────┐  ┌─────────────────────────────────┐  │
│  │ StdioTransport  │  │ HTTPTransport                   │  │
│  └─────────────────┘  └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   MCP Server 层                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐│
│  │SystemMonitor │ │FileManager   │ │NetworkServer         ││
│  │(系统监控)    │ │(文件管理)    │ │(网络请求)            ││
│  └──────────────┘ └──────────────┘ └──────────────────────┘│
│  ┌──────────────────────────────────────────────────────┐  │
│  │ServiceManager (服务管理)                              │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 🧠 自我感知与诊断能力 (Phase 1 & 2) ✅

SuperLinux 现在具备完整的自我感知和自我诊断能力！

### Phase 1: 自我感知 ✅

- `read_own_code` - AI 可以读取自己的源代码，理解自己的实现
- `analyze_performance` - AI 可以分析自己的执行统计，识别弱点
- `review_experiences` - AI 可以查看历史经验，从成功和失败中学习

### Phase 2: 自我诊断 ✅ (新!)

- `evaluate_last_task` - AI 可以评估刚完成的任务，自动打分并生成改进建议
- `generate_improvement_plan` - AI 可以基于历史表现生成详细的改进计划
- `review_meta_experiences` - AI 可以查看"如何改进自己"的元经验，了解哪些改进有效

### 快速体验

```bash
# 运行 Phase 1 测试
python3 test_self_awareness.py

# 运行 Phase 2 测试
python3 test_phase2_diagnosis.py

# 与 AI 对话
python3 -m src.cli
```

试试这些对话：
```
你: 分析一下你最近的表现，成功率如何？
你: 评估一下你刚才完成的任务
你: 生成一个改进计划，重点是提高成功率
你: 查看你之前应用的改进，哪些是有效的？
```

### 完整的自我进化循环

```
遇到问题 → 查看历史经验 → 尝试解决 → 记录结果 → 
评估表现 → 生成改进计划 → 应用改进 → 跟踪效果 → 持续优化
```

### 文档

- [Phase 1 文档](docs/PHASE1_SELF_AWARENESS.md) - 自我感知实现
- [Phase 1 快速入门](docs/QUICKSTART_SELF_AWARENESS.md) - 5 分钟上手
- [Phase 2 完成报告](PHASE2_COMPLETED.md) - 自我诊断实现
- [快速参考](QUICK_REFERENCE.md) - 工具速查

### AI 现在会：
- ✅ 遇到重复错误时，主动查看历史
- ✅ 开始复杂任务前，查找相似的成功案例
- ✅ 任务完成后，自动评估自己的表现
- ✅ 定期生成改进计划，识别需要改进的地方
- ✅ 跟踪改进的有效性，持续优化自己

## 可用工具

### 自我感知与诊断 (Phase 1 & 2) 🆕
- `read_own_code` - 读取自己的源代码
- `analyze_performance` - 分析执行统计和性能
- `review_experiences` - 查看和分析历史经验
- `evaluate_last_task` - 评估刚完成的任务 (Phase 2)
- `generate_improvement_plan` - 生成改进计划 (Phase 2)
- `review_meta_experiences` - 查看元经验 (Phase 2)

### 系统监控 (system-monitor)
- `get_system_stats` - 获取 CPU、内存、磁盘使用情况
- `get_cpu_info` - 获取详细 CPU 信息
- `get_memory_info` - 获取详细内存信息
- `get_disk_info` - 获取磁盘使用信息

### 文件管理 (file-manager)
- `read_file` - 读取文件内容
- `write_file` - 写入文件内容
- `list_directory` - 列出目录内容
- `delete_file` - 删除文件 (需要审批)
- `file_info` - 获取文件信息

### 网络交互 (network)
- `fetch_api` - 发起 HTTP 请求 (GET/POST/PUT/DELETE)
- `check_url` - 检查 URL 可访问性

### 服务管理 (service-manager)
- `get_service_status` - 获取服务状态
- `start_service` - 启动服务
- `stop_service` - 停止服务 (需要审批)
- `restart_service` - 重启服务 (需要审批)
- `list_services` - 列出所有服务

## 安全特性

1. **沙盒化文件操作**: 所有文件操作限制在指定沙盒目录内
2. **危险命令检测**: 自动检测并阻止危险命令模式
3. **人工审批**: 高风险操作需要用户确认
4. **最小权限**: 建议以非 root 用户运行

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 运行类型检查
mypy src/

# 运行代码格式化
ruff format src/
```

## 许可证

MIT License

# LangGraph + MCP Linux Agent

基于 LangGraph 和 MCP (Model Context Protocol) 的 Linux 智能体系统，具备自主思考与工具执行能力。

## 特性

- 🧠 **智能编排**: 基于 LangGraph 的 ReAct 循环，支持多步推理
- 🔧 **工具解耦**: 通过 MCP 协议实现大脑与工具的彻底解耦
- 🔒 **安全控制**: 沙盒化文件操作、危险命令检测、人工审批机制
- 💾 **状态持久化**: 支持断点续传和会话恢复
- 🔌 **多模型支持**: 支持 OpenAI、Anthropic Claude、DeepSeek 等模型

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

## 可用工具

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

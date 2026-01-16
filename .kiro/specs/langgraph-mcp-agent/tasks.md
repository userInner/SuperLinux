# Implementation Plan: LangGraph + MCP Linux 智能体系统

## Overview

本实现计划将系统分为 6 个主要阶段：项目基础设施、MCP Server 实现、MCP Client 实现、Orchestrator 核心、安全与持久化、集成与测试。每个阶段都包含具体的编码任务和对应的属性测试。

## Tasks

- [x] 1. 项目基础设施搭建
  - [x] 1.1 创建项目目录结构和配置文件
    - 创建 `src/` 目录结构：`orchestrator/`, `mcp_client/`, `mcp_servers/`, `common/`
    - 创建 `pyproject.toml` 配置 Python 项目依赖
    - 创建 `requirements.txt` 包含：langgraph, langchain, mcp, hypothesis, pytest, aiohttp, psutil
    - _Requirements: 项目基础_

  - [x] 1.2 定义核心数据模型和类型
    - 在 `src/common/models.py` 中定义 `ToolSchema`, `ToolCall`, `ToolResult`, `AgentResponse`
    - 在 `src/common/config.py` 中定义 `MCPServerConfig`, `AgentConfig`
    - 在 `src/common/exceptions.py` 中定义所有自定义异常类
    - _Requirements: 2.3, 3.3_

  - [ ]* 1.3 编写数据模型属性测试
    - **Property 6: Tool Schema 结构完整性**
    - **Validates: Requirements 2.3**

- [x] 2. MCP Server 实现
  - [x] 2.1 实现 BaseMCPServer 基类
    - 在 `src/mcp_servers/base.py` 中创建 `BaseMCPServer` 抽象基类
    - 实现 `list_tools()` 和 `call_tool()` 处理器注册
    - _Requirements: 2.1_

  - [x] 2.2 实现 SystemMonitorServer
    - 在 `src/mcp_servers/system_monitor.py` 中实现系统监控服务
    - 使用 psutil 获取 CPU、内存、磁盘信息
    - 定义 `get_system_stats` 工具 Schema
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [ ]* 2.3 编写 SystemMonitorServer 属性测试
    - **Property 10: 系统监控数据完整性**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4**

  - [x] 2.4 实现 FileManagerServer
    - 在 `src/mcp_servers/file_manager.py` 中实现文件管理服务
    - 实现沙盒路径验证 `_validate_path()`
    - 实现 `read_file`, `write_file`, `list_directory` 工具
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ]* 2.5 编写 FileManagerServer 属性测试
    - **Property 11: 沙盒路径安全性**
    - **Property 12: 文件读写往返一致性**
    - **Property 13: 目录列表准确性**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**

  - [x] 2.6 实现 NetworkServer
    - 在 `src/mcp_servers/network.py` 中实现网络交互服务
    - 使用 aiohttp 实现 HTTP 请求
    - 实现 `fetch_api` 工具支持 GET/POST/PUT/DELETE
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [ ]* 2.7 编写 NetworkServer 属性测试
    - **Property 14: HTTP 方法支持完整性**
    - **Property 15: HTTP 请求参数传递**
    - **Property 16: HTTP 错误响应结构**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4**

  - [x] 2.8 实现 ServiceManagerServer
    - 在 `src/mcp_servers/service_manager.py` 中实现服务管理服务
    - 使用 subprocess 调用 systemctl 命令
    - 实现危险服务检测和审批标记
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ]* 2.9 编写 ServiceManagerServer 属性测试
    - **Property 17: 服务状态查询有效性**
    - **Validates: Requirements 7.4**

- [x] 3. Checkpoint - MCP Server 完成
  - 确保所有 MCP Server 测试通过
  - 如有问题请询问用户

- [x] 4. MCP Client 实现
  - [x] 4.1 实现 Transport 抽象层
    - 在 `src/mcp_client/transport.py` 中定义 `Transport` 协议
    - 实现 `StdioTransport` 类（子进程通信）
    - 实现 `HTTPTransport` 类（HTTP/SSE 通信）
    - _Requirements: 3.1, 3.2_

  - [x] 4.2 实现 MCPClient 核心
    - 在 `src/mcp_client/client.py` 中实现 `MCPClient` 类
    - 实现 `connect()`, `list_tools()`, `call_tool()`, `disconnect()` 方法
    - 实现 JSON-RPC 2.0 消息封装
    - _Requirements: 2.1, 2.4, 3.4_

  - [ ]* 4.3 编写 MCPClient 属性测试
    - **Property 5: 工具发现完整性**
    - **Property 7: 参数验证正确性**
    - **Property 8: JSON-RPC 协议合规性**
    - **Property 9: 通信错误结构化**
    - **Validates: Requirements 2.1, 2.4, 3.3, 3.4**

- [x] 5. Checkpoint - MCP Client 完成
  - 确保 MCP Client 能正确连接 Server 并调用工具
  - 如有问题请询问用户

- [x] 6. Orchestrator 核心实现
  - [x] 6.1 实现 AgentState 和状态管理
    - 在 `src/orchestrator/state.py` 中定义 `AgentState` TypedDict
    - 实现消息累加器 `add_messages`
    - _Requirements: 1.2_

  - [ ]* 6.2 编写 AgentState 属性测试
    - **Property 1: 状态历史完整性**
    - **Validates: Requirements 1.2**

  - [x] 6.3 实现 LLMEngine 抽象层
    - 在 `src/orchestrator/llm_engine.py` 中定义 `LLMEngine` 抽象基类
    - 实现 `OpenAIEngine`, `ClaudeEngine`, `DeepSeekEngine`
    - 实现工具绑定 `bind_tools()` 方法
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

  - [ ]* 6.4 编写 LLMEngine 属性测试
    - **Property 20: 模型配置切换**
    - **Property 21: Function Calling 能力**
    - **Validates: Requirements 10.4, 10.5**

  - [x] 6.5 实现 ReActGraph 核心循环
    - 在 `src/orchestrator/graph.py` 中实现 `ReActGraph` 类
    - 实现 `reason_node`, `act_node`, `approve_node`, `respond_node` 节点
    - 实现 `should_continue` 条件边逻辑
    - _Requirements: 1.1, 1.3_

  - [ ]* 6.6 编写 ReActGraph 属性测试
    - **Property 2: 工具调用决策正确性**
    - **Validates: Requirements 1.3**

  - [x] 6.7 实现错误恢复机制
    - 在 `src/orchestrator/recovery.py` 中实现 `ErrorRecoveryStrategy`
    - 实现参数重生成、连接重试、安全违规处理
    - _Requirements: 1.4_

  - [ ]* 6.8 编写错误恢复属性测试
    - **Property 3: 错误恢复机制**
    - **Validates: Requirements 1.4**

- [x] 7. Checkpoint - Orchestrator 核心完成
  - 确保 ReAct 循环能正确执行
  - 如有问题请询问用户

- [x] 8. 安全与持久化
  - [x] 8.1 实现 SecurityValidator
    - 在 `src/common/security.py` 中实现 `SecurityValidator` 类
    - 定义 `DANGEROUS_PATTERNS` 正则表达式列表
    - 实现 `validate_command()` 和 `sanitize_path()` 方法
    - _Requirements: 8.2, 8.4_

  - [ ]* 8.2 编写 SecurityValidator 属性测试
    - **Property 18: 危险命令拒绝**
    - **Validates: Requirements 8.2, 8.4**

  - [x] 8.3 实现 ApprovalManager
    - 在 `src/orchestrator/approval.py` 中实现 `ApprovalManager` 类
    - 定义 `HIGH_RISK_OPERATIONS` 集合
    - 实现 `request_approval()` 交互方法
    - _Requirements: 1.5, 7.5_

  - [ ]* 8.4 编写 ApprovalManager 属性测试
    - **Property 4: 高风险操作审批**
    - **Validates: Requirements 1.5, 7.5**

  - [x] 8.5 实现 CheckpointManager
    - 在 `src/orchestrator/checkpoint.py` 中实现 `CheckpointManager` 类
    - 集成 LangGraph SqliteSaver
    - 实现 `list_threads()`, `get_thread_state()` 方法
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

  - [ ]* 8.6 编写 CheckpointManager 属性测试
    - **Property 19: 状态持久化往返一致性**
    - **Validates: Requirements 9.1, 9.2, 9.3**

- [x] 9. Checkpoint - 安全与持久化完成
  - 确保安全验证和状态持久化正常工作
  - 如有问题请询问用户

- [x] 10. 集成与入口
  - [x] 10.1 实现 Agent 主类
    - 在 `src/agent.py` 中实现 `LinuxAgent` 主类
    - 整合 MCPClient、ReActGraph、CheckpointManager
    - 实现 `run()` 主循环方法
    - _Requirements: 1.1, 2.1, 2.2_

  - [x] 10.2 实现 CLI 入口
    - 在 `src/cli.py` 中实现命令行界面
    - 支持配置文件加载
    - 支持交互式对话模式
    - _Requirements: 用户交互_

  - [x] 10.3 创建配置文件模板
    - 创建 `config.example.yaml` 配置模板
    - 包含 LLM 配置、MCP Server 配置示例
    - _Requirements: 10.4_

- [x] 11. 最终检查点
  - 确保所有测试通过
  - 确保端到端流程正常工作
  - 如有问题请询问用户

## Notes

- 标记 `*` 的任务为可选属性测试任务，可跳过以加快 MVP 开发
- 每个属性测试都引用了设计文档中的具体属性编号
- Checkpoint 任务用于阶段性验证，确保增量开发的正确性
- 属性测试使用 hypothesis 库，每个测试至少运行 100 次

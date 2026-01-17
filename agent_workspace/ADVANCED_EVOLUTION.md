# 高级进化机制 - Phase 4

## 概述

实现了三个核心的自主进化能力，让 AI Agent 能够持续自我优化：

1. **自主工具工厂** (Tool Factory)
2. **Prompt 自愈能力** (Prompt Self-Healing)
3. **环境自适应** (Environment Adaptation)

---

## 1. 自主工具工厂 🏭

### 功能说明

当 Agent 连续三次（或更多次）使用相同的命令流来完成同一任务时，系统会自动将这组命令封装为一个标准的 Python 工具函数，并永久加入工具库。

### 核心特性

- ✅ **智能模式识别**: 自动检测重复的命令模式
- ✅ **参数提取**: 自动识别命令中的变量参数（如 `{package}`, `{file}`）
- ✅ **工具生成**: 自动生成带文档说明的 Python 工具
- ✅ **持续追踪**: 记录每次使用情况，智能触发创建

### 使用示例

```python
from evolution_integration import get_evolution_manager

# 获取进化管理器
manager = get_evolution_manager()

# Agent 执行系统检查任务
commands = [
    "df -h",
    "free -h", 
    "uptime",
    "whoami"
]

# 记录命令使用（第1次）
manager.track_command_usage(commands, "system_check")

# ... 后续任务中再次使用相同命令流 ...

# 第3次使用时，自动创建工具
tool_path = manager.track_command_usage(commands, "system_check")
# 输出: ./experience_db/generated_tools/auto_system_check_xxxxx.py
```

### 生成的工具示例

```python
"""
自动生成的工具: auto_system_check_9249af84
描述: 自动生成的 system_check 工具
生成时间: 2026-01-17 18:07:23
"""

def auto_system_check_9249af84() -> Dict[str, Any]:
    """自动生成的 system_check 工具
    
    运行系统健康检查命令流
    
    Returns:
        Dict[str, Any]: 执行结果
    """
    result_0 = subprocess.run("df -h", shell=True, capture_output=True, text=True)
    result_1 = subprocess.run("free -h", shell=True, capture_output=True, text=True)
    result_2 = subprocess.run("uptime", shell=True, capture_output=True, text=True)
    result_3 = subprocess.run("whoami", shell=True, capture_output=True, text=True)
    
    return {
        "success": True,
        "output": {...},
        "error": {...}
    }
```

### 触发条件

- 命令流连续使用 **3次或以上**
- 命令序列保持 **80%以上相似度**
- 任务类型必须一致

---

## 2. Prompt 自愈能力 🩺

### 功能说明

当 Agent 发现某条 System Prompt 经常导致理解偏差时（通过纠偏记录分析），它可以自动分析问题模式，并提议修改 Prompt 文件，修复常见误解。

### 核心特性

- ✅ **问题追踪**: 记录每次 Prompt 导致的误解
- ✅ **模式识别**: 自动检测频繁出现的问题类型
- ✅ **智能修复**: 根据问题类型自动应用修复方案
- ✅ **备份回滚**: 自动备份，支持回滚

### 问题类型

| 类型 | 说明 | 自动修复策略 |
|------|------|-------------|
| `misunderstanding` | 理解偏差 | 添加"常见误解纠正"章节 |
| `wrong_tool` | 工具选择错误 | 添加"工具选择指导" |
| `missing_step` | 缺少必要步骤 | 添加"重要步骤提醒" |

### 使用示例

```python
from evolution_integration import get_evolution_manager

manager = get_evolution_manager()

# Agent 发现 Prompt 导致理解偏差
manager.report_prompt_issue(
    issue_type="misunderstanding",
    problem="经常误将文件编辑理解为创建新文件",
    suggested_fix="在 prompt 中明确区分 edit_file 和 write_file 的使用场景"
)

# 多次报告相同问题后，自动触发自愈修复
# 系统会自动在 prompts.py 中添加纠偏说明
```

### 自动修复示例

```python
# 检测到频繁问题（出现 3+ 次）
# 自动在 prompts.py 中添加：

### 常见误解纠正
- 经常误将文件编辑理解为创建新文件
- 解决方案: 在 prompt 中明确区分 edit_file 和 write_file 的使用场景
```

### 触发条件

- 相同问题报告 **3次或以上**
- 问题类型一致
- 修复方案明确

---

## 3. 环境自适应 🌍

### 功能说明

Agent 根据运行环境（Ubuntu/CentOS/Debian 等）自动调整其默认的包管理命令和服务管理命令，无需手动适配。

### 支持的发行版

| 发行版 | 包管理器 | 服务管理 |
|--------|----------|----------|
| Ubuntu | `apt` | `systemctl` |
| CentOS 7 | `yum` | `systemctl` |
| CentOS 8+ | `dnf` | `systemctl` |
| Debian | `apt-get` | `systemctl` |

### 使用示例

```python
from evolution_integration import get_evolution_manager

manager = get_evolution_manager()

# 自动适配环境安装包
install_cmd = manager.install_package("nginx")
# Ubuntu: "apt install -y nginx"
# CentOS: "yum install -y nginx" 或 "dnf install -y nginx"

# 自动适配环境管理服务
start_cmd = manager.start_service("nginx")
# 输出: "systemctl start nginx"

# 获取环境信息
env_info = manager.get_environment_info()
# {
#     "distro": "ubuntu",
#     "version": "22.04",
#     "package_manager": "apt",
#     "init_system": "systemd",
#     "python_path": "/usr/bin/python3",
#     "node_path": "/usr/bin/node"
# }
```

### 支持的命令类型

| 命令类型 | Ubuntu | CentOS | Debian |
|----------|--------|--------|--------|
| 安装包 | `apt install -y {pkg}` | `yum/dnf install -y {pkg}` | `apt-get install -y {pkg}` |
| 更新包 | `apt update && apt upgrade -y` | `yum/dnf update -y` | `apt-get update && apt-get upgrade -y` |
| 删除包 | `apt remove -y {pkg}` | `yum/dnf remove -y {pkg}` | `apt-get remove -y {pkg}` |
| 启动服务 | `systemctl start {svc}` | `systemctl start {svc}` | `systemctl start {svc}` |
| 停止服务 | `systemctl stop {svc}` | `systemctl stop {svc}` | `systemctl stop {svc}` |
| 查看状态 | `systemctl status {svc}` | `systemctl status {svc}` | `systemctl status {svc}` |

### 环境检测

```bash
# 自动检测系统环境
🔍 环境自适应: 检测系统环境...
   ✅ 检测完成: ubuntu 22.04
   包管理器: apt
   Init 系统: systemd
   Python 路径: /usr/bin/python3
```

---

## 进化报告 📊

系统自动生成详细的进化报告，追踪所有进化事件。

```python
from evolution_integration import get_evolution_report

report = get_evolution_report()

# 报告内容：
{
    "summary": {
        "total_patterns": 1,           # 追踪的命令模式
        "tool_suggestions": 1,          # 工具创建建议
        "total_corrections": 10,        # Prompt 纠偏次数
        "environment": "ubuntu 22.04",  # 当前环境
        "total_evolutions": 14          # 总进化次数
    },
    "tool_factory": {
        "patterns_tracked": 1,
        "ready_for_creation": 1,
        "suggestions": [...]
    },
    "prompt_healing": {
        "total_corrections": 10,
        "by_type": {
            "misunderstanding": 6,
            "wrong_tool": 2,
            "missing_step": 2
        },
        "recent": [...]
    },
    "environment": {...},
    "evolution_history": {
        "by_type": {
            "tool_created": 4,
            "prompt_healing": 10
        },
        "recent": [...]
    }
}
```

---

## 数据存储 💾

所有进化数据存储在 `./experience_db/` 目录：

```
experience_db/
├── command_patterns.json      # 命令模式记录
├── generated_tools/            # 自动生成的工具
│   └── auto_*.py
├── prompt_corrections.json     # Prompt 纠偏记录
├── prompt_backups/             # Prompt 备份
│   └── prompt_*.py
├── environment_profile.json    # 环境配置
└── evolution_log.json          # 进化日志
```

---

## 测试结果 ✅

运行测试脚本 `test_advanced_evolution.py`，所有测试通过：

```
============================================================
  测试 1: 自主工具工厂
============================================================
🔧 自主工具工厂: 创建新工具 auto_system_check_9249af84
   来源: 4 个命令，使用 3 次
✅ 工具已创建

============================================================
  测试 2: Prompt 自愈能力
============================================================
🔍 Prompt 自愈: 检测到频繁问题 (出现 4 次)
✅ Prompt 自愈: 已应用修复

============================================================
  测试 3: 环境自适应
============================================================
🖥️  系统环境: ubuntu 22.04
   包管理器: apt
   Init 系统: systemd

============================================================
  测试 4: 进化报告
============================================================
📊 进化摘要:
   追踪的命令模式: 1
   工具创建建议: 1
   Prompt 纠偏: 10
   系统环境: ubuntu 22.04
   总进化次数: 14

✅ 所有测试完成!
```

---

## 集成到现有系统 🔗

### 1. 在 Agent 中集成

```python
from evolution_integration import (
    get_evolution_manager,
    track_commands,
    install,
    report_issue,
    get_evolution_report
)

# 初始化
evolution = get_evolution_manager()

# 追踪命令使用
if similar_commands_used_before:
    track_commands(command_list, task_type)

# 使用环境自适应命令
cmd = install("nginx")
run_command(cmd)

# 报告 Prompt 问题
if prompt_misunderstanding_detected:
    report_issue("misunderstanding", problem, solution)
```

### 2. 在自我进化周期中使用

```python
from advanced_evolution import ToolFactory, PromptSelfHealing, EnvironmentAdaptive

# 这些模块可以集成到 self_evolution.py 中
# 作为 Phase 4 的核心进化能力
```

---

## 未来改进方向 🚀

1. **工具工厂增强**:
   - 支持更复杂的命令模式识别
   - 自动生成单元测试
   - 工具质量评估和优化

2. **Prompt 自愈增强**:
   - 使用 NLP 技术智能分析问题
   - A/B 测试不同 Prompt 版本
   - 集成顾问 AI 的反馈

3. **环境自适应增强**:
   - 支持更多 Linux 发行版
   - Windows/macOS 环境支持
   - 容器环境特殊处理

---

## 总结

三个高级进化机制让 AI Agent 真正具备了**持续自我进化**的能力：

- 🏭 **自主工具工厂**: 从重复中创造新工具
- 🩺 **Prompt 自愈**: 从错误中自我修复
- 🌍 **环境自适应**: 在不同环境中灵活适应

这些机制共同构成了一个完整的进化闭环，让 Agent 在使用中不断学习、优化、进化。

[STATUS: COMPLETED]

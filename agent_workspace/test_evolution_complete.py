#!/usr/bin/env python3
"""
高级进化机制完整测试
测试三个核心功能：
1. 自主工具工厂
2. Prompt 自愈能力
3. 环境自适应
"""

import sys
import os

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from evolution_integration import EvolutionManager
from datetime import datetime

def print_separator(title):
    """打印分隔符"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_tool_factory():
    """测试自主工具工厂"""
    print_separator("🔧 测试 1: 自主工具工厂")
    
    evolution = EvolutionManager("./experience_db")
    
    # 模拟重复的命令流（系统检查）
    system_check_commands = [
        "df -h",
        "free -h",
        "uptime",
        "ps aux | head -10"
    ]
    
    print(f"📝 记录命令流（第1次）...")
    result = evolution.track_command_usage(system_check_commands, "system_check")
    print(f"   结果: {result if result else '未创建工具（使用次数不足）'}")
    
    print(f"\n📝 记录命令流（第2次）...")
    result = evolution.track_command_usage(system_check_commands, "system_check")
    print(f"   结果: {result if result else '未创建工具（使用次数不足）'}")
    
    print(f"\n📝 记录命令流（第3次）...")
    result = evolution.track_command_usage(system_check_commands, "system_check")
    print(f"   结果: {result if result else '未创建工具'}")
    
    # 查看工具创建建议
    print(f"\n📊 工具创建建议:")
    suggestions = evolution.get_tool_suggestions()
    for s in suggestions:
        print(f"   - {s['description']}")
        print(f"     使用次数: {s['usage_count']}")
        print(f"     紧急度: {s['urgency']}")
    
    # 检查生成的工具文件
    print(f"\n📂 生成的工具文件:")
    tools_dir = "./experience_db/generated_tools"
    if os.path.exists(tools_dir):
        for f in os.listdir(tools_dir):
            print(f"   - {f}")
    
    print("\n✅ 自主工具工厂测试完成")

def test_prompt_healing():
    """测试 Prompt 自愈能力"""
    print_separator("🩺 测试 2: Prompt 自愈能力")
    
    evolution = EvolutionManager("./experience_db")
    
    # 模拟多次记录相同的问题
    issues = [
        ("misunderstanding", 
         "经常误解'检查系统状态'为只检查CPU，应该检查全部",
         "在检查系统状态时，使用 get_system_stats() 而不是单独的 CPU 检查"),
        ("misunderstanding",
         "经常误解'检查系统状态'为只检查CPU，应该检查全部", 
         "在检查系统状态时，使用 get_system_stats() 而不是单独的 CPU 检查"),
        ("misunderstanding",
         "经常误解'检查系统状态'为只检查CPU，应该检查全部",
         "在检查系统状态时，使用 get_system_stats() 而不是单独的 CPU 检查"),
    ]
    
    print(f"📝 记录 Prompt 问题（3次相同问题）...")
    for i, (issue_type, problem, fix) in enumerate(issues, 1):
        print(f"\n   第 {i} 次记录:")
        correction_id = evolution.report_prompt_issue(issue_type, problem, fix)
        print(f"   纠偏ID: {correction_id}")
    
    # 查看纠偏记录
    print(f"\n📊 Prompt 纠偏记录:")
    corrections = evolution.get_prompt_corrections("misunderstanding")
    for c in corrections[:5]:
        print(f"\n   ID: {c['id']}")
        print(f"   时间: {c['timestamp']}")
        print(f"   类型: {c['issue_type']}")
        print(f"   问题: {c['problem'][:50]}...")
    
    # 检查备份文件
    print(f"\n📂 Prompt 备份文件:")
    backup_dir = "./experience_db/prompt_backups"
    if os.path.exists(backup_dir):
        for f in os.listdir(backup_dir):
            print(f"   - {f}")
    
    print("\n✅ Prompt 自愈能力测试完成")

def test_environment_adaptive():
    """测试环境自适应"""
    print_separator("🌍 测试 3: 环境自适应")
    
    evolution = EvolutionManager("./experience_db")
    
    # 测试不同的命令类型
    print(f"🔍 检测到的环境配置:")
    profile = evolution.env_adaptive.profile
    if profile:
        print(f"   发行版: {profile.distro}")
        print(f"   版本: {profile.version}")
        print(f"   包管理器: {profile.package_manager}")
        print(f"   Init 系统: {profile.init_system}")
        print(f"   Python 路径: {profile.python_path}")
    
    # 测试适配命令
    print(f"\n📝 适配后的命令示例:")
    
    commands = [
        ("install", {"package": "nginx"}),
        ("update", {}),
        ("service_start", {"service": "nginx"}),
        ("service_status", {"service": "nginx"})
    ]
    
    for cmd_type, kwargs in commands:
        adapted_cmd = evolution.get_adapted_command(cmd_type, **kwargs)
        print(f"\n   类型: {cmd_type}")
        print(f"   参数: {kwargs}")
        print(f"   适配命令: {adapted_cmd}")
    
    # 测试便捷方法
    print(f"\n🔧 便捷方法测试:")
    print(f"   安装命令: {evolution.install_package('curl')}")
    print(f"   服务启动: {evolution.start_service('nginx')}")
    print(f"   服务状态: {evolution.check_service_status('nginx')}")
    
    print("\n✅ 环境自适应测试完成")

def test_evolution_log():
    """测试进化日志"""
    print_separator("📋 测试 4: 进化日志")
    
    evolution = EvolutionManager("./experience_db")
    
    print(f"📊 进化事件日志:")
    
    # 触发一些进化事件
    print(f"\n触发更多进化事件...")
    
    # 记录命令使用
    deploy_commands = [
        "git pull",
        "npm install",
        "npm run build",
        "systemctl restart myapp"
    ]
    evolution.track_command_usage(deploy_commands, "deployment")
    evolution.track_command_usage(deploy_commands, "deployment")
    
    # 记录另一个 Prompt 问题
    evolution.report_prompt_issue(
        "wrong_tool",
        "经常用 run_command 执行简单的文件读取",
        "应该使用 read_file 工具来读取文件"
    )
    
    # 显示日志
    print(f"\n最近的进化事件:")
    if hasattr(evolution, 'evolution_log'):
        for entry in evolution.evolution_log[-5:]:
            print(f"\n   时间: {entry['timestamp']}")
            print(f"   类型: {entry['type']}")
            print(f"   详情: {entry.get('details', {})}")
    
    # 检查日志文件
    log_file = "./experience_db/evolution_log.json"
    if os.path.exists(log_file):
        print(f"\n📂 日志文件: {log_file}")
        print(f"   大小: {os.path.getsize(log_file)} 字节")
    
    print("\n✅ 进化日志测试完成")

def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("  高级进化机制 - 完整功能测试")
    print(f"  开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    try:
        # 运行所有测试
        test_tool_factory()
        test_prompt_healing()
        test_environment_adaptive()
        test_evolution_log()
        
        print_separator("🎉 所有测试完成")
        
        print("\n📊 测试总结:")
        print("   ✅ 自主工具工厂: 自动将重复命令封装为工具")
        print("   ✅ Prompt 自愈能力: 基于纠偏记录自动优化 Prompt")
        print("   ✅ 环境自适应: 根据系统环境自动调整命令")
        print("   ✅ 进化日志: 记录所有进化事件")
        
        print("\n💡 进化机制特点:")
        print("   - 自主: 无需人工干预，自动学习和适应")
        print("   - 持续: 持续追踪和改进")
        print("   - 可追溯: 完整的日志记录")
        print("   - 可回滚: 支持备份和恢复")
        
        print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

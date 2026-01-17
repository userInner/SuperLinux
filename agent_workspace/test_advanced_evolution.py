#!/usr/bin/env python3
"""
高级进化机制测试脚本

测试三个核心功能：
1. 自主工具工厂
2. Prompt 自愈能力
3. 环境自适应
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from evolution_integration import (
    get_evolution_manager,
    track_commands,
    get_env_command,
    install,
    report_issue,
    get_evolution_report
)


def print_section(title: str):
    """打印分节标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def test_tool_factory():
    """测试自主工具工厂"""
    print_section("测试 1: 自主工具工厂")
    
    manager = get_evolution_manager()
    
    # 模拟重复使用的命令流
    system_check_commands = [
        "df -h",
        "free -h",
        "uptime",
        "whoami"
    ]
    
    print("\n📝 记录系统检查命令流（第1次）...")
    track_commands(system_check_commands, "system_check")
    
    print("\n📝 记录系统检查命令流（第2次）...")
    track_commands(system_check_commands, "system_check")
    
    print("\n📝 记录系统检查命令流（第3次 - 触发工具创建）...")
    tool_path = track_commands(system_check_commands, "system_check")
    
    if tool_path:
        print(f"✅ 工具已创建: {tool_path}")
    else:
        print("ℹ️  工具创建可能需要更多使用次数")
    
    # 获取工具建议
    suggestions = manager.get_tool_suggestions()
    print(f"\n📊 当前工具建议: {len(suggestions)} 个")
    for i, s in enumerate(suggestions[:3], 1):
        print(f"   {i}. {s['description']} (使用 {s['usage_count']} 次)")


def test_prompt_healing():
    """测试 Prompt 自愈"""
    print_section("测试 2: Prompt 自愈能力")
    
    manager = get_evolution_manager()
    
    # 模拟报告 Prompt 问题
    print("\n📝 报告理解偏差问题（第1次）...")
    report_issue(
        "misunderstanding",
        "经常误将文件编辑理解为创建新文件",
        "在 prompt 中明确区分 edit_file 和 write_file 的使用场景"
    )
    
    print("\n📝 报告理解偏差问题（第2次）...")
    report_issue(
        "misunderstanding",
        "经常误将文件编辑理解为创建新文件",
        "在 prompt 中明确区分 edit_file 和 write_file 的使用场景"
    )
    
    print("\n📝 报告理解偏差问题（第3次 - 触发自愈）...")
    report_issue(
        "misunderstanding",
        "经常误将文件编辑理解为创建新文件",
        "在 prompt 中明确区分 edit_file 和 write_file 的使用场景"
    )
    
    # 获取纠偏记录
    corrections = manager.get_prompt_corrections("misunderstanding")
    print(f"\n📊 理解偏差纠偏记录: {len(corrections)} 条")
    for i, c in enumerate(corrections[:3], 1):
        print(f"   {i}. {c['problem'][:50]}...")
    
    # 测试其他类型的问题
    report_issue(
        "wrong_tool",
        "使用 read_file 而非 list_directory 列出目录",
        "明确 list_directory 应优先用于目录操作"
    )
    
    report_issue(
        "missing_step",
        "忘记验证文件是否存在后再编辑",
        "添加验证步骤到工作流程"
    )


def test_environment_adaptive():
    """测试环境自适应"""
    print_section("测试 3: 环境自适应")
    
    manager = get_evolution_manager()
    
    # 获取环境信息
    env_info = manager.get_environment_info()
    print(f"\n🖥️  系统环境:")
    print(f"   发行版: {env_info.get('distro', 'unknown')} {env_info.get('version', '')}")
    print(f"   包管理器: {env_info.get('package_manager', 'unknown')}")
    print(f"   Init 系统: {env_info.get('init_system', 'unknown')}")
    print(f"   Python 路径: {env_info.get('python_path', 'unknown')}")
    
    # 测试自适应命令
    print("\n🔧 测试自适应命令:")
    
    install_cmd = manager.install_package("nginx")
    print(f"   安装命令: {install_cmd}")
    
    update_cmd = manager.update_packages()
    print(f"   更新命令: {update_cmd}")
    
    start_cmd = manager.start_service("nginx")
    print(f"   启动服务: {start_cmd}")
    
    status_cmd = manager.check_service_status("nginx")
    print(f"   检查状态: {status_cmd}")
    
    # 测试便捷函数
    print("\n📦 使用便捷函数:")
    print(f"   install('nginx'): {install('nginx')}")
    print(f"   get_env_command('install', package='docker'): {get_env_command('install', package='docker')}")


def test_evolution_report():
    """测试进化报告"""
    print_section("测试 4: 进化报告")
    
    report = get_evolution_report()
    
    print(f"\n📊 进化摘要:")
    summary = report["summary"]
    print(f"   追踪的命令模式: {summary['total_patterns']}")
    print(f"   工具创建建议: {summary['tool_suggestions']}")
    print(f"   Prompt 纠偏: {summary['total_corrections']}")
    print(f"   系统环境: {summary['environment']}")
    print(f"   总进化次数: {summary['total_evolutions']}")
    
    print(f"\n🔧 工具工厂状态:")
    tf = report["tool_factory"]
    print(f"   可创建工具: {tf['ready_for_creation']}")
    if tf['suggestions']:
        for i, s in enumerate(tf['suggestions'][:2], 1):
            print(f"   {i}. {s['description']} (紧急度: {s['urgency']})")
    
    print(f"\n💬 Prompt 自愈状态:")
    ph = report["prompt_healing"]
    print(f"   按类型统计: {ph['by_type']}")
    
    print(f"\n📜 进化历史:")
    eh = report["evolution_history"]
    print(f"   按类型统计: {eh['by_type']}")
    if eh['recent']:
        for i, log in enumerate(eh['recent'][-3:], 1):
            print(f"   {i}. [{log['type']}] {log['timestamp'][:19]}")


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("  高级进化机制测试")
    print("="*60)
    
    try:
        # 运行所有测试
        test_tool_factory()
        test_prompt_healing()
        test_environment_adaptive()
        test_evolution_report()
        
        print("\n" + "="*60)
        print("  ✅ 所有测试完成!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

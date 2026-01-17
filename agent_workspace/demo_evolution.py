#!/usr/bin/env python3
"""
高级进化机制 - 实际使用演示
展示如何在日常工作中使用自主进化能力
"""

import sys
import os

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from evolution_integration import EvolutionManager
import json

def print_header(title):
    """打印标题"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def demo_tool_factory():
    """演示工具工厂"""
    print_header("🔧 演示 1: 自主工具工厂")
    
    evolution = EvolutionManager("./experience_db")
    
    print("💡 场景：系统管理员经常需要检查系统状态")
    print("   重复执行以下命令：")
    print("   1. df -h          (检查磁盘使用)")
    print("   2. free -h        (检查内存使用)")
    print("   3. uptime         (检查系统负载)")
    print("   4. ps aux | head  (检查进程)")
    
    # 模拟多次使用
    print("\n📝 模拟使用场景：")
    
    for i in range(1, 4):
        print(f"\n   第 {i} 次执行系统检查...")
        commands = [
            "df -h",
            "free -h",
            "uptime",
            "ps aux | head -10"
        ]
        
        result = evolution.track_command_usage(commands, "system_check")
        
        if result:
            print(f"   ✅ 工具工厂检测到重复使用，自动创建工具！")
            print(f"   📦 工具路径: {result}")
        else:
            print(f"   📊 记录使用模式 (使用次数: {i})")
    
    print("\n🎉 演示完成！")
    print("   💡 现在系统检查已成为一个可重用的工具")
    print("   💡 未来可以直接调用该工具，无需重复输入命令")

def demo_prompt_healing():
    """演示 Prompt 自愈"""
    print_header("🩺 演示 2: Prompt 自愈能力")
    
    evolution = EvolutionManager("./experience_db")
    
    print("💡 场景：AI 经常误解用户指令")
    print("   问题：用户说'检查系统状态'时，AI 只检查了 CPU")
    print("   正确做法：应该使用 get_system_stats() 检查全部")
    
    print("\n📝 模拟问题报告：")
    
    for i in range(1, 4):
        print(f"\n   第 {i} 次报告同样的问题...")
        
        correction_id = evolution.report_prompt_issue(
            issue_type="misunderstanding",
            problem="经常误解'检查系统状态'为只检查CPU，应该检查全部",
            suggested_fix="在检查系统状态时，使用 get_system_stats() 而不是单独的 CPU 检查"
        )
        
        print(f"   📋 纠偏ID: {correction_id}")
    
    print("\n🔍 查看 Prompt 纠偏记录：")
    corrections = evolution.get_prompt_corrections("misunderstanding")
    
    print(f"\n   共有 {len(corrections)} 条纠偏记录")
    
    # 统计问题频率
    from collections import Counter
    problem_counts = Counter([c['problem'][:30] for c in corrections])
    
    print("\n   问题频率统计：")
    for problem, count in problem_counts.most_common(3):
        print(f"   - {problem}... (出现 {count} 次)")
    
    print("\n🎉 演示完成！")
    print("   💡 系统已自动识别频繁问题")
    print("   💡 会在 Prompt 中添加更明确的指导")

def demo_environment_adaptive():
    """演示环境自适应"""
    print_header("🌍 演示 3: 环境自适应")
    
    evolution = EvolutionManager("./experience_db")
    
    print("💡 场景：部署应用到不同的 Linux 发行版")
    
    # 获取环境信息
    env_info = evolution.get_environment_info()
    
    print("\n🔍 当前环境：")
    print(f"   发行版: {env_info['distro']} {env_info['version']}")
    print(f"   包管理器: {env_info['package_manager']}")
    print(f"   Init 系统: {env_info['init_system']}")
    print(f"   Python: {env_info['python_path']}")
    
    print("\n📝 适配不同环境的命令：")
    
    # 软件包安装
    print("\n   1️⃣  安装软件包：")
    print(f"      当前环境: {evolution.install_package('nginx')}")
    print(f"      如果是 CentOS: yum install -y nginx")
    print(f"      如果是 Debian: apt-get install -y nginx")
    
    # 系统更新
    print("\n   2️⃣  更新系统：")
    print(f"      当前环境: {evolution.update_packages()}")
    print(f"      如果是 CentOS 8+: dnf upgrade -y")
    
    # 服务管理
    print("\n   3️⃣  管理服务：")
    print(f"      启动: {evolution.start_service('nginx')}")
    print(f"      停止: {evolution.stop_service('nginx')}")
    print(f"      状态: {evolution.check_service_status('nginx')}")
    
    print("\n🎉 演示完成！")
    print("   💡 系统自动适配当前环境的命令")
    print("   💡 代码无需修改即可在不同发行版运行")

def demo_evolution_report():
    """演示进化报告"""
    print_header("📊 演示 4: 进化报告")
    
    evolution = EvolutionManager("./experience_db")
    
    print("💡 生成完整的进化报告：")
    
    report = evolution.generate_evolution_report()
    
    print("\n📈 摘要统计：")
    summary = report['summary']
    print(f"   追踪的命令模式: {summary['total_patterns']}")
    print(f"   工具创建建议: {summary['tool_suggestions']}")
    print(f"   Prompt 纠偏总数: {summary['total_corrections']}")
    print(f"   系统环境: {summary['environment']}")
    print(f"   进化事件: {summary['total_evolutions']}")
    
    print("\n🔧 工具工厂状态：")
    tool_factory = report['tool_factory']
    print(f"   追踪的模式数: {tool_factory['patterns_tracked']}")
    print(f"   准备创建的工具: {tool_factory['ready_for_creation']}")
    
    if tool_factory['suggestions']:
        print("\n   建议创建的工具：")
        for s in tool_factory['suggestions']:
            print(f"   - {s['description']}")
            print(f"     使用次数: {s['usage_count']}")
    
    print("\n🩺 Prompt 自愈状态：")
    prompt_healing = report['prompt_healing']
    print(f"   纠偏记录总数: {prompt_healing['total_corrections']}")
    
    if prompt_healing['by_type']:
        print("\n   问题类型分布：")
        for issue_type, count in prompt_healing['by_type'].items():
            print(f"   - {issue_type}: {count} 次")
    
    print("\n🌍 环境配置：")
    environment = report['environment']
    for key, value in environment.items():
        print(f"   {key}: {value}")
    
    print("\n📋 最近的进化事件：")
    evolution_history = report['evolution_history']
    for event in evolution_history['recent']:
        print(f"\n   时间: {event['timestamp']}")
        print(f"   类型: {event['type']}")
        print(f"   详情: {event['details']}")
    
    print("\n🎉 演示完成！")
    print("   💡 完整的进化报告帮助你了解系统学习进展")

def main():
    """运行所有演示"""
    print("\n" + "="*70)
    print("  高级进化机制 - 实际使用演示")
    print("="*70)
    
    try:
        # 运行演示
        demo_tool_factory()
        demo_prompt_healing()
        demo_environment_adaptive()
        demo_evolution_report()
        
        print_header("🎓 总结")
        
        print("✅ 自主工具工厂:")
        print("   - 自动将重复命令封装为工具")
        print("   - 减少重复劳动，提高效率")
        print("   - 工具可重用，易于维护")
        
        print("\n✅ Prompt 自愈能力:")
        print("   - 自动识别理解偏差")
        print("   - 持续优化 Prompt 配置")
        print("   - 支持 3 种问题类型")
        
        print("\n✅ 环境自适应:")
        print("   - 自动检测系统环境")
        print("   - 适配不同发行版")
        print("   - 一套代码多环境运行")
        
        print("\n💡 使用建议:")
        print("   1. 在日常工作中使用 evolution.track_command_usage() 追踪命令")
        print("   2. 发现问题时用 evolution.report_prompt_issue() 报告")
        print("   3. 使用 evolution.get_adapted_command() 获取适配命令")
        print("   4. 定期用 evolution.generate_evolution_report() 查看进展")
        
        print("\n📚 更多信息:")
        print("   - 实现代码: src/advanced_evolution.py")
        print("   - 集成接口: src/evolution_integration.py")
        print("   - 完整测试: test_evolution_complete.py")
        print("   - 详细报告: EVOLUTION_SUMMARY.md")
        
        print("\n" + "="*70)
        
    except Exception as e:
        print(f"\n❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

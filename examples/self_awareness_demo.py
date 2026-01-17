#!/usr/bin/env python3
"""
演示 AI 如何使用自我感知能力

这个脚本展示了 AI 如何：
1. 查看自己的代码实现
2. 分析自己的表现
3. 从历史经验中学习
"""

import asyncio
from src.common.config import AgentConfig
from src.agent import LinuxAgent


async def demo_self_reflection():
    """演示 AI 的自我反思能力"""
    
    # 创建 agent
    config = AgentConfig.from_yaml("config.yaml")
    agent = LinuxAgent(config)
    
    async with agent:
        print("\n" + "="*70)
        print("🧠 SuperLinux 自我感知演示")
        print("="*70)
        
        # 场景 1: AI 查看自己的实现
        print("\n📖 场景 1: AI 想了解自己是如何实现的")
        print("-"*70)
        
        response = await agent.chat(
            "请使用 read_own_code 工具查看你的 prompts 模块，"
            "告诉我你的系统提示词中包含哪些核心原则？"
        )
        print(f"AI: {response}\n")
        
        # 场景 2: AI 分析自己的表现
        print("\n📊 场景 2: AI 分析自己的历史表现")
        print("-"*70)
        
        response = await agent.chat(
            "请使用 analyze_performance 工具分析你最近的表现，"
            "告诉我你的成功率如何？有哪些需要改进的地方？"
        )
        print(f"AI: {response}\n")
        
        # 场景 3: AI 从历史中学习
        print("\n🔍 场景 3: AI 从历史经验中学习")
        print("-"*70)
        
        response = await agent.chat(
            "请使用 review_experiences 工具查看最近的失败案例，"
            "分析一下你在哪些类型的问题上容易失败？"
        )
        print(f"AI: {response}\n")
        
        # 场景 4: AI 主动自我改进
        print("\n💡 场景 4: AI 提出自我改进建议")
        print("-"*70)
        
        response = await agent.chat(
            "基于你对自己代码和表现的分析，"
            "你认为应该如何改进自己？请给出 3 个具体建议。"
        )
        print(f"AI: {response}\n")
        
        print("="*70)
        print("✅ 演示完成！")
        print("="*70)


async def demo_learning_from_failure():
    """演示 AI 如何从失败中学习"""
    
    config = AgentConfig.from_yaml("config.yaml")
    agent = LinuxAgent(config)
    
    async with agent:
        print("\n" + "="*70)
        print("📚 演示: AI 从失败中学习")
        print("="*70)
        
        # 模拟一个失败的任务
        print("\n❌ 第一次尝试（可能失败）")
        print("-"*70)
        
        response = await agent.chat(
            "安装一个不存在的软件包 'nonexistent-package-xyz'"
        )
        print(f"AI: {response}\n")
        
        # AI 分析失败原因
        print("\n🔍 AI 分析失败原因")
        print("-"*70)
        
        response = await agent.chat(
            "刚才的任务失败了，请使用 analyze_performance 查看类似的失败案例，"
            "总结一下在软件包安装方面你经常遇到什么问题？"
        )
        print(f"AI: {response}\n")
        
        # AI 提出改进策略
        print("\n💡 AI 提出改进策略")
        print("-"*70)
        
        response = await agent.chat(
            "基于这次失败和历史经验，下次遇到软件包安装问题时，"
            "你应该采取什么策略？"
        )
        print(f"AI: {response}\n")


async def demo_proactive_learning():
    """演示 AI 的主动学习能力"""
    
    config = AgentConfig.from_yaml("config.yaml")
    agent = LinuxAgent(config)
    
    async with agent:
        print("\n" + "="*70)
        print("🎯 演示: AI 的主动学习")
        print("="*70)
        
        # AI 主动查看自己的弱点
        print("\n🔍 AI 主动识别自己的弱点")
        print("-"*70)
        
        response = await agent.chat(
            "请主动分析你自己：\n"
            "1. 使用 analyze_performance 查看你的整体表现\n"
            "2. 使用 review_experiences 查看失败案例\n"
            "3. 总结你在哪些方面需要改进\n"
            "4. 提出具体的改进计划"
        )
        print(f"AI: {response}\n")
        
        # AI 制定学习计划
        print("\n📝 AI 制定学习计划")
        print("-"*70)
        
        response = await agent.chat(
            "基于刚才的分析，请制定一个自我改进计划，"
            "包括：需要学习什么、如何验证改进效果、预期目标"
        )
        print(f"AI: {response}\n")


if __name__ == "__main__":
    import sys
    
    demos = {
        "1": ("自我反思", demo_self_reflection),
        "2": ("从失败中学习", demo_learning_from_failure),
        "3": ("主动学习", demo_proactive_learning),
    }
    
    print("\n选择演示场景:")
    for key, (name, _) in demos.items():
        print(f"  {key}. {name}")
    print("  all. 运行所有演示")
    
    choice = input("\n请选择 (1-3 或 all): ").strip()
    
    if choice == "all":
        for name, demo_func in demos.values():
            print(f"\n{'='*70}")
            print(f"运行演示: {name}")
            print(f"{'='*70}")
            asyncio.run(demo_func())
    elif choice in demos:
        name, demo_func = demos[choice]
        asyncio.run(demo_func())
    else:
        print("无效选择")
        sys.exit(1)

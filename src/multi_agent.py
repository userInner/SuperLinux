"""Multi-AI collaborative agent with fallback to secondary AI."""

import asyncio
import json
import uuid
from typing import Any
from dataclasses import dataclass

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, SystemMessage

from .orchestrator.llm_engine import create_llm_engine, LLMEngine
from .tools import execute_tool, get_all_tools


@dataclass
class AIConfig:
    """Configuration for an AI model."""
    name: str
    provider: str
    model: str
    api_key: str
    role: str = "primary"  # primary, consultant, specialist


class MultiAIAgent:
    """Agent that can collaborate with multiple AI models."""
    
    def __init__(
        self,
        primary_config: AIConfig,
        secondary_configs: list[AIConfig] = None,
        max_retries: int = 3,
        search_attempts_before_consult: int = 2
    ):
        self.primary_config = primary_config
        self.secondary_configs = secondary_configs or []
        self.max_retries = max_retries
        self.search_attempts_before_consult = search_attempts_before_consult
        
        # Initialize engines
        self.primary_engine = None
        self.secondary_engines: dict[str, LLMEngine] = {}
        
        self.tools = get_all_tools()
        self.primary_llm = None
        
        # Tracking
        self.problem_history = []
        self.consultation_count = 0
    
    async def initialize(self) -> None:
        """Initialize all AI engines."""
        # Primary AI
        self.primary_engine = create_llm_engine(
            provider=self.primary_config.provider,
            model=self.primary_config.model,
            api_key=self.primary_config.api_key
        )
        self.primary_llm = self.primary_engine.bind_tools(self.tools)
        
        print(f"✅ Primary AI: {self.primary_config.name} ({self.primary_config.model})")
        
        # Secondary AIs
        for config in self.secondary_configs:
            engine = create_llm_engine(
                provider=config.provider,
                model=config.model,
                api_key=config.api_key
            )
            self.secondary_engines[config.name] = engine
            print(f"✅ Secondary AI: {config.name} ({config.model}) - {config.role}")
        
        print(f"✅ Loaded {len(self.tools)} tools")
    
    async def consult_secondary_ai(
        self,
        ai_name: str,
        problem_summary: str,
        attempted_solutions: list[str],
        errors: list[str]
    ) -> str:
        """Consult a secondary AI for help."""
        if ai_name not in self.secondary_engines:
            return f"Secondary AI '{ai_name}' not configured"
        
        engine = self.secondary_engines[ai_name]
        
        consultation_prompt = f"""你是一个专家顾问，另一个 AI 助手在解决问题时遇到了困难，需要你的帮助。

## 原始问题
{problem_summary}

## 已尝试的解决方案
{chr(10).join(f"- {s}" for s in attempted_solutions) if attempted_solutions else "无"}

## 遇到的错误
{chr(10).join(f"- {e}" for e in errors) if errors else "无"}

## 请求
请分析这个问题，提供：
1. 问题的根本原因分析
2. 具体的解决步骤（可以直接执行的命令）
3. 可能的替代方案
4. 需要注意的事项

请给出具体、可操作的建议。"""

        print(f"\n   🤝 Consulting {ai_name}...")
        
        response = await engine.llm.ainvoke([HumanMessage(content=consultation_prompt)])
        self.consultation_count += 1
        
        return response.content
    
    async def chat(self, message: str) -> str:
        """Process a message with multi-AI collaboration."""
        if not self.primary_llm:
            await self.initialize()
        
        system_prompt = """你是一个智能 Linux 系统管理助手，具备自主学习和多 AI 协作能力。

## 可用工具
- get_system_stats: 获取系统状态
- get_cpu_info / get_memory_info / get_disk_info: 详细硬件信息
- list_services: 列出系统服务
- web_search: 搜索互联网
- fetch_webpage: 获取网页内容
- run_command: 执行 Linux 命令

## 工作策略
1. 首先尝试直接解决问题
2. 失败时搜索解决方案
3. 如果收到其他 AI 的建议，认真分析并尝试执行
4. 始终解释你的思考过程"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=message)
        ]
        
        max_iterations = 15
        error_count = 0
        search_count = 0
        attempted_solutions = []
        errors = []
        consulted = False
        
        for iteration in range(max_iterations):
            # Call primary LLM
            response = await self.primary_llm.ainvoke(messages)
            messages.append(response)
            
            if not response.tool_calls:
                return response.content
            
            # Execute tool calls
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call["id"]
                
                print(f"   🔧 [{iteration+1}] {tool_name}")
                
                result = await execute_tool(tool_name, tool_args)
                
                # Track attempts
                if tool_name == "run_command":
                    attempted_solutions.append(tool_args.get("command", ""))
                elif tool_name == "web_search":
                    search_count += 1
                
                # Check for errors
                try:
                    result_data = json.loads(result)
                    is_error = result_data.get("error", False)
                except:
                    is_error = False
                
                if is_error:
                    error_count += 1
                    error_msg = result_data.get("message", "Unknown error")
                    errors.append(error_msg)
                    print(f"   ❌ Error #{error_count}: {error_msg[:50]}")
                    
                    # Check if we should consult secondary AI
                    should_consult = (
                        not consulted and
                        self.secondary_engines and
                        error_count >= self.max_retries and
                        search_count >= self.search_attempts_before_consult
                    )
                    
                    if should_consult:
                        consulted = True
                        
                        # Get consultation from secondary AI
                        secondary_name = list(self.secondary_engines.keys())[0]
                        advice = await self.consult_secondary_ai(
                            secondary_name,
                            message,
                            attempted_solutions,
                            errors
                        )
                        
                        # Add advice to conversation
                        consultation_msg = f"""
[来自 {secondary_name} 的专家建议]

{advice}

请根据以上建议，重新尝试解决问题。"""
                        
                        messages.append(ToolMessage(content=result, tool_call_id=tool_id))
                        messages.append(HumanMessage(content=consultation_msg))
                        
                        # Reset counters for new attempt
                        error_count = 0
                        search_count = 0
                        continue
                else:
                    error_count = 0  # Reset on success
                
                messages.append(ToolMessage(content=result, tool_call_id=tool_id))
        
        return "达到最大迭代次数。问题可能需要人工介入。"
    
    async def run_interactive(self) -> None:
        """Run in interactive mode."""
        await self.initialize()
        
        print("\n" + "=" * 60)
        print("🤖 Multi-AI Linux Agent")
        print("=" * 60)
        print(f"Primary: {self.primary_config.name}")
        for cfg in self.secondary_configs:
            print(f"Consultant: {cfg.name} ({cfg.role})")
        print("-" * 60)
        print("Commands: 'quit', 'help', 'stats'")
        print("-" * 60 + "\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ("quit", "exit"):
                    print("\nGoodbye! 👋")
                    break
                
                if user_input.lower() == "stats":
                    print(f"\n📊 Stats: {self.consultation_count} AI consultations\n")
                    continue
                
                if user_input.lower() == "help":
                    print("""
示例:
  - 查看系统状态
  - 帮我配置 nginx 反向代理
  - 如何优化 MySQL 性能
  - 排查服务器 CPU 占用过高的问题
""")
                    continue
                
                print("\n🤔 Processing...\n")
                response = await self.chat(user_input)
                print(f"\nAgent: {response}\n")
                
            except KeyboardInterrupt:
                print("\n\nInterrupted.\n")
            except EOFError:
                break


def load_config_from_file(config_path: str = None):
    """Load configuration from YAML file."""
    import os
    from .common.config import MultiAgentConfig
    
    # Try to find config file
    if config_path is None:
        for path in ["config.yaml", "config.yml"]:
            if os.path.exists(path):
                config_path = path
                break
    
    if config_path and os.path.exists(config_path):
        print(f"📄 Loading config from: {config_path}")
        return MultiAgentConfig.from_yaml(config_path)
    
    return None


def load_config_from_env():
    """Load configuration from environment variables (fallback)."""
    import os
    
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    
    if not deepseek_key and not openai_key and not gemini_key:
        return None, None
    
    # Primary AI (priority: DeepSeek > OpenAI > Gemini)
    if deepseek_key:
        primary = AIConfig(name="DeepSeek", provider="deepseek", 
                          model="deepseek-chat", api_key=deepseek_key, role="primary")
    elif openai_key:
        primary = AIConfig(name="GPT-4", provider="openai",
                          model="gpt-4o", api_key=openai_key, role="primary")
    else:
        primary = AIConfig(name="Gemini", provider="gemini",
                          model="gemini-2.5-flash", api_key=gemini_key, role="primary")
    
    # Secondary AIs
    secondary = []
    if gemini_key and primary.provider != "gemini":
        secondary.append(AIConfig(name="Gemini-Consultant", provider="gemini",
                                  model="gemini-2.5-flash", api_key=gemini_key, role="consultant"))
    if openai_key and primary.provider != "openai":
        secondary.append(AIConfig(name="GPT-4-Consultant", provider="openai",
                                  model="gpt-4o", api_key=openai_key, role="consultant"))
    if deepseek_key and primary.provider != "deepseek":
        secondary.append(AIConfig(name="DeepSeek-Consultant", provider="deepseek",
                                  model="deepseek-chat", api_key=deepseek_key, role="consultant"))
    
    return primary, secondary


async def main():
    """Main entry point."""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="Multi-AI Linux Agent")
    parser.add_argument("-c", "--config", help="Path to config.yaml file")
    args = parser.parse_args()
    
    # Try loading from config file first
    config = load_config_from_file(args.config)
    
    if config:
        # Use config file
        primary = AIConfig(
            name=config.primary_ai.name,
            provider=config.primary_ai.provider,
            model=config.primary_ai.model,
            api_key=config.primary_ai.api_key,
            role="primary"
        )
        secondary = [
            AIConfig(
                name=ai.name,
                provider=ai.provider,
                model=ai.model,
                api_key=ai.api_key,
                role=ai.role
            ) for ai in config.secondary_ais
        ]
        max_retries = config.agent.max_retries
        search_attempts = config.agent.search_attempts_before_consult
    else:
        # Fallback to environment variables
        print("📄 No config file found, using environment variables")
        primary, secondary = load_config_from_env()
        max_retries = 3
        search_attempts = 2
    
    if not primary or not primary.api_key:
        print("Error: No API key configured!")
        print("\nOption 1: Create config.yaml from config.example.yaml")
        print("Option 2: Set environment variables:")
        print("  - DEEPSEEK_API_KEY")
        print("  - OPENAI_API_KEY") 
        print("  - GEMINI_API_KEY")
        sys.exit(1)
    
    agent = MultiAIAgent(
        primary_config=primary,
        secondary_configs=secondary,
        max_retries=max_retries,
        search_attempts_before_consult=search_attempts
    )
    
    await agent.run_interactive()


if __name__ == "__main__":
    asyncio.run(main())

"""Multi-AI collaborative agent with fallback to secondary AI."""

import asyncio
import json
import uuid
from typing import Any
from dataclasses import dataclass
from enum import Enum

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, SystemMessage

from .orchestrator.llm_engine import create_llm_engine, LLMEngine
from .tools import execute_tool, get_all_tools
from .prompts import get_prompt
from .experience_rag import get_experience_rag, ExperienceRAG


class TaskStatus(Enum):
    """任务状态"""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_INPUT = "needs_input"


@dataclass
class AIConfig:
    """Configuration for an AI model."""
    name: str
    provider: str
    model: str
    api_key: str
    role: str = "primary"  # primary, consultant, specialist
    base_url: str = None


class MultiAIAgent:
    """基于任务完成状态的多 AI 协作 Agent。
    
    核心理念：以问题解决为导向，持续工作直到任务完成。
    遇到困难时优先查阅官方文档，必要时咨询其他 AI。
    支持 RAG 经验学习，从历史成功案例中学习。
    """
    
    def __init__(
        self,
        primary_config: AIConfig,
        secondary_configs: list[AIConfig] = None,
        max_retries_per_error: int = 3,
        search_attempts_before_consult: int = 2,
        prompt_type: str = "default",
        enable_rag: bool = True,
        experience_db_path: str = "./experience_db"
    ):
        self.primary_config = primary_config
        self.secondary_configs = secondary_configs or []
        self.max_retries_per_error = max_retries_per_error
        self.search_attempts_before_consult = search_attempts_before_consult
        self.prompt_type = prompt_type
        self.enable_rag = enable_rag
        self.experience_db_path = experience_db_path
        
        # Initialize engines
        self.primary_engine = None
        self.secondary_engines: dict[str, LLMEngine] = {}
        
        self.tools = get_all_tools()
        self.primary_llm = None
        
        # RAG 经验系统
        self.experience_rag: ExperienceRAG = None
        
        # Tracking
        self.consultation_count = 0
    
    async def initialize(self) -> None:
        """Initialize all AI engines."""
        self.primary_engine = create_llm_engine(
            provider=self.primary_config.provider,
            model=self.primary_config.model,
            api_key=self.primary_config.api_key
        )
        self.primary_llm = self.primary_engine.bind_tools(self.tools)
        
        print(f"✅ Primary AI: {self.primary_config.name} ({self.primary_config.model})")
        
        for config in self.secondary_configs:
            engine = create_llm_engine(
                provider=config.provider,
                model=config.model,
                api_key=config.api_key
            )
            self.secondary_engines[config.name] = engine
            print(f"✅ Secondary AI: {config.name} ({config.model}) - {config.role}")
        
        print(f"✅ Loaded {len(self.tools)} tools")
        
        # 初始化 RAG 经验系统
        if self.enable_rag:
            print("📚 Initializing experience RAG system...")
            self.experience_rag = get_experience_rag(self.experience_db_path)
            stats = self.experience_rag.get_stats()
            print(f"   📊 {stats.get('total_experiences', 0)} experiences loaded")
    
    def _get_task_oriented_prompt(self) -> str:
        """获取以任务为导向的系统提示词"""
        base_prompt = get_prompt(self.prompt_type)
        
        task_completion_instructions = """

## 任务完成机制

你必须在回复中明确标注任务状态。在最终回复末尾使用：

- `[STATUS: COMPLETED]` - 任务已完成
- `[STATUS: NEEDS_INPUT]` - 需要用户提供更多信息
- `[STATUS: FAILED: 原因]` - 任务失败
- `[STATUS: IN_PROGRESS]` - 任务进行中，需要继续

### 核心原则

1. **持续工作直到完成**: 不要中途停止，除非任务完成或需要用户输入
2. **遇到困难优先查官方文档**: 
   - 搜索 "[软件名] official documentation [问题]"
   - 使用 fetch_webpage 获取文档详细内容
   - 按照官方指导操作
3. **不要轻易放弃**: 尝试多种方法，搜索解决方案
4. **如果收到其他 AI 的建议**: 认真分析并执行

### 判断任务完成的标准

- 用户要求的操作已成功执行
- 用户的问题已得到解答
- 结果已清晰展示给用户
"""
        return base_prompt + task_completion_instructions
    
    def _parse_status(self, content: str) -> tuple[TaskStatus, str]:
        """从回复中解析任务状态"""
        content_lower = content.lower()
        
        if "[status: completed]" in content_lower:
            return TaskStatus.COMPLETED, content.replace("[STATUS: COMPLETED]", "").strip()
        elif "[status: needs_input]" in content_lower:
            return TaskStatus.NEEDS_INPUT, content.replace("[STATUS: NEEDS_INPUT]", "").strip()
        elif "[status: failed" in content_lower:
            return TaskStatus.FAILED, content
        elif "[status: in_progress]" in content_lower:
            return TaskStatus.IN_PROGRESS, content.replace("[STATUS: IN_PROGRESS]", "").strip()
        
        return TaskStatus.IN_PROGRESS, content
    
    def _save_experience(
        self,
        problem: str,
        solution: str,
        steps: list[str],
        tools_used: list[str],
        errors: list[str],
        docs_consulted: list[str],
        success: bool
    ):
        """保存经验到 RAG 系统"""
        if not self.experience_rag:
            return
        
        try:
            exp_id = self.experience_rag.save_experience(
                problem=problem,
                solution=solution[:1000],  # 限制长度
                steps=steps[-10:],  # 最后 10 步
                tools_used=tools_used,
                errors_encountered=errors[-5:],  # 最后 5 个错误
                docs_consulted=docs_consulted[-5:],
                success=success
            )
            if success:
                print(f"   💾 Experience saved: {exp_id}")
        except Exception as e:
            print(f"   ⚠️ Failed to save experience: {e}")
    
    async def consult_secondary_ai(
        self,
        ai_name: str,
        problem_summary: str,
        attempted_solutions: list[str],
        errors: list[str],
        docs_consulted: list[str] = None
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

## 已查阅的文档
{chr(10).join(f"- {d}" for d in (docs_consulted or [])) if docs_consulted else "无"}

## 请求
请分析这个问题，提供：
1. 问题的根本原因分析
2. 推荐查阅的官方文档链接
3. 具体的解决步骤（可以直接执行的命令）
4. 可能的替代方案

请给出具体、可操作的建议。"""

        print(f"\n   🤝 Consulting {ai_name}...")
        
        response = await engine.llm.ainvoke([HumanMessage(content=consultation_prompt)])
        self.consultation_count += 1
        
        return response.content
    
    async def chat(self, message: str) -> str:
        """基于任务完成状态的对话循环，支持多 AI 协作和 RAG 经验学习"""
        if not self.primary_llm:
            await self.initialize()
        
        system_prompt = self._get_task_oriented_prompt()
        
        # RAG: 检索相关经验
        experience_context = ""
        if self.experience_rag:
            similar_experiences = self.experience_rag.search_similar(message, top_k=3)
            if similar_experiences:
                experience_context = self.experience_rag.format_experiences_for_prompt(similar_experiences)
                print(f"   📚 Found {len(similar_experiences)} relevant experiences")
        
        # 构建消息
        if experience_context:
            system_prompt = system_prompt + "\n" + experience_context
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=message)
        ]
        
        # 追踪状态（用于保存经验）
        error_tracker = {}
        total_tool_calls = 0
        consecutive_no_progress = 0
        last_tool_results = []
        
        attempted_solutions = []
        all_steps = []  # 记录所有步骤
        errors = []
        docs_consulted = []
        tools_used = []
        search_count = 0
        consulted = False
        final_response = ""
        task_success = False
        
        while True:
            # 调用主 LLM
            response = await self.primary_llm.ainvoke(messages)
            messages.append(response)
            
            # 如果没有工具调用，检查状态
            if not response.tool_calls:
                status, clean_content = self._parse_status(response.content)
                final_response = clean_content
                
                if status == TaskStatus.COMPLETED:
                    print("   ✅ Task completed")
                    task_success = True
                    # 保存成功经验
                    self._save_experience(
                        message, clean_content, all_steps, tools_used,
                        errors, docs_consulted, success=True
                    )
                    return clean_content
                elif status == TaskStatus.NEEDS_INPUT:
                    print("   ❓ Needs user input")
                    return clean_content
                elif status == TaskStatus.FAILED:
                    print("   ❌ Task failed")
                    # 保存失败经验（也有价值）
                    self._save_experience(
                        message, clean_content, all_steps, tools_used,
                        errors, docs_consulted, success=False
                    )
                    return clean_content
                else:
                    consecutive_no_progress += 1
                    if consecutive_no_progress >= 2:
                        # 假设完成，保存经验
                        self._save_experience(
                            message, response.content, all_steps, tools_used,
                            errors, docs_consulted, success=True
                        )
                        return response.content
                    messages.append(HumanMessage(
                        content="请确认任务是否完成，并标注状态 [STATUS: COMPLETED] 或继续执行。"
                    ))
                    continue
            
            consecutive_no_progress = 0
            
            # 执行工具调用
            current_results = []
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call["id"]
                
                total_tool_calls += 1
                print(f"   🔧 [{total_tool_calls}] {tool_name}")
                if tool_args:
                    args_str = str(tool_args)
                    if len(args_str) > 60:
                        args_str = args_str[:60] + "..."
                    print(f"      Args: {args_str}")
                
                result = await execute_tool(tool_name, tool_args)
                current_results.append((tool_name, result))
                
                # 记录步骤和工具
                step_desc = f"{tool_name}: {str(tool_args)[:100]}"
                all_steps.append(step_desc)
                if tool_name not in tools_used:
                    tools_used.append(tool_name)
                
                # 追踪尝试
                if tool_name == "run_command":
                    attempted_solutions.append(tool_args.get("command", ""))
                elif tool_name == "web_search":
                    search_count += 1
                elif tool_name == "fetch_webpage":
                    docs_consulted.append(tool_args.get("url", ""))
                
                # 检查错误
                try:
                    result_data = json.loads(result)
                    is_error = result_data.get("error", False)
                    error_msg = result_data.get("message", "")
                except:
                    is_error = False
                    error_msg = ""
                
                if is_error:
                    error_key = f"{tool_name}:{error_msg[:50]}"
                    error_tracker[error_key] = error_tracker.get(error_key, 0) + 1
                    errors.append(error_msg)
                    
                    print(f"   ❌ Error: {error_msg[:60]}")
                    
                    # 检查是否需要特殊处理
                    if error_tracker[error_key] >= self.max_retries_per_error:
                        # 检查是否应该咨询其他 AI
                        should_consult = (
                            not consulted and
                            self.secondary_engines and
                            search_count >= self.search_attempts_before_consult
                        )
                        
                        if should_consult:
                            consulted = True
                            secondary_name = list(self.secondary_engines.keys())[0]
                            advice = await self.consult_secondary_ai(
                                secondary_name,
                                message,
                                attempted_solutions,
                                errors,
                                docs_consulted
                            )
                            
                            consultation_msg = f"""
[来自 {secondary_name} 的专家建议]

{advice}

请根据以上建议，重新尝试解决问题。优先按照建议中提到的官方文档操作。"""
                            
                            messages.append(ToolMessage(content=result, tool_call_id=tool_id))
                            messages.append(HumanMessage(content=consultation_msg))
                            error_tracker[error_key] = 0  # 重置计数
                            continue
                        else:
                            # 提示优先查阅官方文档
                            hint = f"""
这个错误已经出现 {error_tracker[error_key]} 次了: {error_msg}

请按以下优先级尝试解决:
1. **优先查阅官方文档**: 使用 web_search 搜索 "[软件名] official documentation [错误关键词]"
2. 使用 fetch_webpage 获取官方文档的详细内容
3. 根据官方文档的指导重新尝试
4. 如果官方文档没有答案，再搜索社区解决方案 (Stack Overflow, GitHub Issues)
5. 如果确实无法解决，标记 [STATUS: FAILED: 原因]
"""
                            messages.append(ToolMessage(content=result, tool_call_id=tool_id))
                            messages.append(HumanMessage(content=hint))
                            continue
                else:
                    print(f"   ✓ Success")
                
                messages.append(ToolMessage(content=result, tool_call_id=tool_id))
            
            # 检测循环
            if current_results == last_tool_results:
                consecutive_no_progress += 1
                if consecutive_no_progress >= 3:
                    messages.append(HumanMessage(
                        content="检测到重复操作。请尝试不同的方法，或标记 [STATUS: COMPLETED]。"
                    ))
            else:
                last_tool_results = current_results
    
    async def run_interactive(self) -> None:
        """Run in interactive mode."""
        await self.initialize()
        
        print("\n" + "=" * 60)
        print("🤖 Multi-AI Linux Agent - 任务导向模式")
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
                    print(f"\n📊 AI Consultations: {self.consultation_count}")
                    if self.experience_rag:
                        rag_stats = self.experience_rag.get_stats()
                        print(f"📚 Experiences: {rag_stats.get('total_experiences', 0)} total")
                        print(f"   ✅ Successful: {rag_stats.get('successful', 0)}")
                        print(f"   ❌ Failed: {rag_stats.get('failed', 0)}")
                        print(f"   💾 Vector DB: {'Yes' if rag_stats.get('vector_db_available') else 'No (using JSON)'}")
                    print()
                    continue
                
                if user_input.lower() == "help":
                    print("""
示例:
  - 查看系统状态
  - 帮我配置 nginx 反向代理
  - 如何优化 MySQL 性能
  - 排查服务器 CPU 占用过高的问题
  - 创建一个监控脚本
""")
                    continue
                
                print("\n🤔 Working on your task...\n")
                response = await self.chat(user_input)
                print(f"\nAgent: {response}\n")
                
            except KeyboardInterrupt:
                print("\n\n⚠️ Interrupted.\n")
            except EOFError:
                break


def load_config_from_file(config_path: str = None):
    """Load configuration from YAML file."""
    import os
    from .common.config import MultiAgentConfig
    
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
    
    if deepseek_key:
        primary = AIConfig(name="DeepSeek", provider="deepseek", 
                          model="deepseek-chat", api_key=deepseek_key, role="primary")
    elif openai_key:
        primary = AIConfig(name="GPT-4", provider="openai",
                          model="gpt-4o", api_key=openai_key, role="primary")
    else:
        primary = AIConfig(name="Gemini", provider="gemini",
                          model="gemini-2.5-flash", api_key=gemini_key, role="primary")
    
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
    
    config = load_config_from_file(args.config)
    
    if config:
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
        max_retries_per_error=max_retries,
        search_attempts_before_consult=search_attempts,
        prompt_type="default"
    )
    
    await agent.run_interactive()


if __name__ == "__main__":
    asyncio.run(main())

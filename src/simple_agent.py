"""Simplified agent that works without MCP subprocess."""

import asyncio
import json
import uuid
from typing import Any
from enum import Enum

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, SystemMessage

from .common.config import AgentConfig
from .orchestrator.llm_engine import create_llm_engine
from .tools import execute_tool, get_all_tools
from .prompts import get_prompt


class TaskStatus(Enum):
    """任务状态"""
    IN_PROGRESS = "in_progress"      # 进行中
    COMPLETED = "completed"          # 已完成
    FAILED = "failed"                # 失败
    NEEDS_INPUT = "needs_input"      # 需要用户输入
    BLOCKED = "blocked"              # 被阻塞


class SimpleLinuxAgent:
    """基于任务完成状态的智能 Agent。
    
    核心理念：以问题解决为导向，而不是迭代次数限制。
    Agent 会持续工作直到：
    1. 任务完成
    2. 需要用户输入
    3. 遇到无法解决的问题
    """
    
    def __init__(
        self,
        llm_provider: str = "deepseek",
        llm_model: str = "deepseek-chat",
        api_key: str = "",
        max_retries_per_error: int = 3,
        prompt_type: str = "default"
    ):
        self.llm_engine = create_llm_engine(
            provider=llm_provider,
            model=llm_model,
            api_key=api_key
        )
        self.tools = get_all_tools()
        self.llm_with_tools = None
        self._current_thread_id = str(uuid.uuid4())
        self.max_retries_per_error = max_retries_per_error
        self.prompt_type = prompt_type
    
    async def initialize(self) -> None:
        """Initialize the agent with tools."""
        self.llm_with_tools = self.llm_engine.bind_tools(self.tools)
        print(f"✅ Agent initialized with {len(self.tools)} tools:")
        for tool in self.tools:
            print(f"   - {tool.name}: {tool.description[:40]}...")
    
    def _get_task_oriented_prompt(self) -> str:
        """获取以任务为导向的系统提示词"""
        base_prompt = get_prompt(self.prompt_type)
        
        task_completion_instructions = """

## 任务完成机制

你必须在回复中明确标注任务状态。在你的最终回复末尾，使用以下格式之一：

- `[STATUS: COMPLETED]` - 任务已完成，用户的问题已解决
- `[STATUS: NEEDS_INPUT]` - 需要用户提供更多信息才能继续
- `[STATUS: FAILED: 原因]` - 任务失败，说明原因
- `[STATUS: IN_PROGRESS]` - 任务仍在进行中，需要继续执行工具

### 重要规则

1. **持续工作直到完成**: 如果任务未完成，继续调用工具，不要停止
2. **不要过早结束**: 只有当你确信问题已解决时才标记 COMPLETED
3. **主动解决问题**: 遇到错误时，先尝试搜索解决方案，不要立即放弃
4. **清晰沟通**: 如果需要用户输入，明确说明需要什么信息

### 判断任务完成的标准

- 用户要求的操作已执行成功
- 用户的问题已得到回答
- 所有必要的步骤都已完成
- 结果已向用户展示

### 示例

用户: "查看系统内存使用情况"
→ 调用 get_memory_info
→ 展示结果
→ [STATUS: COMPLETED]

用户: "安装 nginx"
→ 调用 run_command 安装
→ 如果失败，搜索解决方案
→ 重试或报告问题
→ [STATUS: COMPLETED] 或 [STATUS: FAILED: 原因]
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
        
        # 如果没有明确状态，根据内容判断
        # 有工具调用 = 进行中，无工具调用 = 可能完成
        return TaskStatus.IN_PROGRESS, content
    
    async def chat(self, message: str) -> str:
        """基于任务完成状态的对话循环"""
        if not self.llm_with_tools:
            await self.initialize()
        
        system_prompt = self._get_task_oriented_prompt()
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=message)
        ]
        
        # 错误追踪
        error_tracker = {}  # {error_type: count}
        total_tool_calls = 0
        consecutive_no_progress = 0
        last_tool_results = []
        
        while True:
            # 调用 LLM
            response = await self.llm_with_tools.ainvoke(messages)
            messages.append(response)
            
            # 如果没有工具调用，检查状态并返回
            if not response.tool_calls:
                status, clean_content = self._parse_status(response.content)
                
                if status == TaskStatus.COMPLETED:
                    print("   ✅ Task completed")
                    return clean_content
                elif status == TaskStatus.NEEDS_INPUT:
                    print("   ❓ Needs user input")
                    return clean_content
                elif status == TaskStatus.FAILED:
                    print("   ❌ Task failed")
                    return clean_content
                else:
                    # 没有工具调用但也没有明确完成状态
                    # 可能是 LLM 忘记标记了，假设已完成
                    consecutive_no_progress += 1
                    if consecutive_no_progress >= 2:
                        return response.content
                    # 提醒 LLM 标记状态
                    messages.append(HumanMessage(
                        content="请确认任务是否完成，并在回复末尾标注状态 [STATUS: COMPLETED] 或继续执行。"
                    ))
                    continue
            
            # 重置无进展计数
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
                
                # 执行工具
                result = await execute_tool(tool_name, tool_args)
                current_results.append((tool_name, result))
                
                # 检查错误
                try:
                    result_data = json.loads(result)
                    is_error = result_data.get("error", False)
                    error_msg = result_data.get("message", "")
                except:
                    is_error = False
                    error_msg = ""
                
                if is_error:
                    # 追踪错误
                    error_key = f"{tool_name}:{error_msg[:50]}"
                    error_tracker[error_key] = error_tracker.get(error_key, 0) + 1
                    
                    print(f"   ❌ Error: {error_msg[:60]}")
                    
                    # 检查是否重复错误太多次
                    if error_tracker[error_key] >= self.max_retries_per_error:
                        # 添加提示让 LLM 优先查阅官方文档
                        hint = f"""
这个错误已经出现 {error_tracker[error_key]} 次了: {error_msg}

请按以下优先级尝试解决:
1. **优先查阅官方文档**: 使用 web_search 搜索 "官方文档 + 关键词" 或 "official docs + keyword"
2. 使用 fetch_webpage 获取官方文档的详细内容
3. 根据官方文档的指导重新尝试
4. 如果官方文档没有答案，再搜索社区解决方案
5. 如果确实无法解决，标记 [STATUS: FAILED: 原因]
"""
                        messages.append(ToolMessage(content=result, tool_call_id=tool_id))
                        messages.append(HumanMessage(content=hint))
                        continue
                else:
                    print(f"   ✓ Success")
                
                messages.append(ToolMessage(content=result, tool_call_id=tool_id))
            
            # 检测循环（相同的工具调用产生相同的结果）
            if current_results == last_tool_results:
                consecutive_no_progress += 1
                if consecutive_no_progress >= 3:
                    messages.append(HumanMessage(
                        content="检测到重复操作。请尝试不同的方法，或者如果任务已完成请标记 [STATUS: COMPLETED]。"
                    ))
            else:
                last_tool_results = current_results
    
    async def run_interactive(self) -> None:
        """Run in interactive mode."""
        await self.initialize()
        
        print("\n" + "=" * 60)
        print("🤖 Linux Agent - 任务导向模式")
        print("=" * 60)
        print("特性: 持续工作直到任务完成")
        print("输入 'quit' 退出, 'help' 查看帮助")
        print("-" * 60 + "\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ("quit", "exit"):
                    print("\nGoodbye! 👋")
                    break
                
                if user_input.lower() == "help":
                    print("""
可用命令示例:
  - 查看系统状态
  - 检查 nginx 服务状态
  - 搜索 Docker 安装教程
  - 执行 df -h 命令
  - 如何配置 SSH 免密登录
  - 创建一个 Python 脚本来监控 CPU
""")
                    continue
                
                print("\n🤔 Working on your task...\n")
                response = await self.chat(user_input)
                print(f"\nAgent: {response}\n")
                
            except KeyboardInterrupt:
                print("\n\n⚠️ Interrupted. Type 'quit' to exit.\n")
            except EOFError:
                print("\nGoodbye! 👋")
                break


async def main():
    """Main entry point."""
    import os
    import sys
    
    # Get API key from environment
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY", "")
        provider = "openai"
        model = "gpt-4o"
    else:
        provider = "deepseek"
        model = "deepseek-chat"
    
    if not api_key:
        print("Error: Please set DEEPSEEK_API_KEY or OPENAI_API_KEY")
        sys.exit(1)
    
    agent = SimpleLinuxAgent(
        llm_provider=provider,
        llm_model=model,
        api_key=api_key,
        max_retries_per_error=3,
        prompt_type="default"
    )
    
    await agent.run_interactive()


if __name__ == "__main__":
    asyncio.run(main())

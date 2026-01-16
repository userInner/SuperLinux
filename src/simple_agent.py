"""Simplified agent that works without MCP subprocess."""

import asyncio
import json
import uuid
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, SystemMessage

from .common.config import AgentConfig
from .orchestrator.llm_engine import create_llm_engine
from .tools import execute_tool, get_all_tools


class SimpleLinuxAgent:
    """Simplified agent with auto-retry and search fallback."""
    
    def __init__(
        self,
        llm_provider: str = "deepseek",
        llm_model: str = "deepseek-chat",
        api_key: str = "",
        max_retries: int = 3
    ):
        self.llm_engine = create_llm_engine(
            provider=llm_provider,
            model=llm_model,
            api_key=api_key
        )
        self.tools = get_all_tools()
        self.llm_with_tools = None
        self._current_thread_id = str(uuid.uuid4())
        self.max_retries = max_retries
    
    async def initialize(self) -> None:
        """Initialize the agent with tools."""
        self.llm_with_tools = self.llm_engine.bind_tools(self.tools)
        print(f"✅ Agent initialized with {len(self.tools)} tools:")
        for tool in self.tools:
            print(f"   - {tool.name}: {tool.description[:40]}...")
    
    async def chat(self, message: str) -> str:
        """Send a message and get a response with auto-retry and search fallback."""
        if not self.llm_with_tools:
            await self.initialize()
        
        system_prompt = """你是一个智能 Linux 系统管理助手，具备自主学习和问题解决能力。

## 可用工具
- get_system_stats: 获取 CPU、内存、磁盘使用情况
- get_cpu_info: 获取详细 CPU 信息
- get_memory_info: 获取详细内存信息
- get_disk_info: 获取磁盘信息
- list_services: 列出系统服务
- web_search: 搜索互联网获取信息、教程、文档
- fetch_webpage: 获取网页详细内容
- run_command: 执行 Linux 命令

## 工作策略
1. 首先尝试使用系统工具或命令解决问题
2. 如果遇到错误或不确定如何操作，使用 web_search 搜索解决方案
3. 找到相关文档后，使用 fetch_webpage 获取详细内容
4. 根据搜索到的信息重新尝试解决问题
5. 始终向用户解释你的思考过程和采取的行动

## 错误处理
- 如果命令执行失败，分析错误信息
- 搜索错误信息以找到解决方案
- 尝试不同的方法，最多重试 3 次
- 如果仍然失败，向用户解释原因并提供建议"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=message)
        ]
        
        max_iterations = 10
        error_count = 0
        last_error = None
        attempted_solutions = []
        
        for iteration in range(max_iterations):
            # Call LLM
            response = await self.llm_with_tools.ainvoke(messages)
            messages.append(response)
            
            # Check for tool calls
            if not response.tool_calls:
                return response.content
            
            # Execute tool calls
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call["id"]
                
                print(f"   🔧 [{iteration+1}] Calling: {tool_name}")
                if tool_args:
                    args_preview = str(tool_args)[:50]
                    print(f"      Args: {args_preview}...")
                
                # Execute the tool
                result = await execute_tool(tool_name, tool_args)
                
                # Check if result is an error
                try:
                    result_data = json.loads(result)
                    is_error = result_data.get("error", False)
                except:
                    is_error = False
                
                if is_error:
                    error_count += 1
                    last_error = result
                    print(f"   ❌ Error #{error_count}: {result_data.get('message', 'Unknown')[:60]}")
                    
                    # If we've had multiple errors, suggest searching
                    if error_count >= self.max_retries and tool_name not in ["web_search", "fetch_webpage"]:
                        # Add a hint to search for solutions
                        search_hint = f"""
操作失败了 {error_count} 次。错误信息: {result_data.get('message', 'Unknown')}

请使用 web_search 工具搜索这个错误的解决方案，或者搜索相关的官方文档来找到正确的方法。
之前尝试过的方案: {attempted_solutions}
"""
                        messages.append(ToolMessage(content=result, tool_call_id=tool_id))
                        messages.append(HumanMessage(content=search_hint))
                        continue
                else:
                    # Success - reset error count
                    if error_count > 0:
                        print(f"   ✅ Success after {error_count} retries!")
                    error_count = 0
                    
                    # Track what we tried
                    if tool_name == "run_command":
                        attempted_solutions.append(tool_args.get("command", ""))
                
                messages.append(ToolMessage(content=result, tool_call_id=tool_id))
        
        return "达到最大迭代次数。请尝试简化您的请求或分步骤执行。"
    
    async def run_interactive(self) -> None:
        """Run in interactive mode."""
        await self.initialize()
        
        print("\n" + "=" * 60)
        print("🤖 Linux Agent - 智能助手模式")
        print("=" * 60)
        print("特性: 自动重试 + 搜索回退 + 文档查阅")
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
""")
                    continue
                
                print("\n🤔 Thinking...\n")
                response = await self.chat(user_input)
                print(f"\nAgent: {response}\n")
                
            except KeyboardInterrupt:
                print("\n\nInterrupted. Type 'quit' to exit.\n")
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
        max_retries=3
    )
    
    await agent.run_interactive()


if __name__ == "__main__":
    asyncio.run(main())

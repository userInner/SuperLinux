"""Test Claude API with custom endpoint."""
import asyncio

async def test_claude():
    print("Testing Claude API (custom endpoint)...")
    
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage
    
    # 自定义 API 端点
    llm = ChatAnthropic(
        model="claude-sonnet-4-5",
        api_key="sk-AB3uYbTGnrPRpSCD4z7Gz8Ykf4ZzT2DyTIMgTjIBKGsT7ep3",
        base_url="https://api.coolyeah.net",
    )
    
    print("Sending request...")
    try:
        response = await asyncio.wait_for(
            llm.ainvoke([HumanMessage(content="Say hello in Chinese, just 5 words")]),
            timeout=60
        )
        print(f"✅ Response: {response.content}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_claude_with_tools():
    print("\nTesting Claude with tools...")
    
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage
    
    llm = ChatAnthropic(
        model="claude-sonnet-4-5",
        api_key="sk-AB3uYbTGnrPRpSCD4z7Gz8Ykf4ZzT2DyTIMgTjIBKGsT7ep3",
        base_url="https://api.coolyeah.net",
    )
    
    tools = [{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"]
            }
        }
    }]
    
    llm_with_tools = llm.bind_tools(tools)
    
    try:
        response = await asyncio.wait_for(
            llm_with_tools.ainvoke([HumanMessage(content="What's the weather in Beijing?")]),
            timeout=60
        )
        print(f"✅ Tool calls: {response.tool_calls}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_claude())
    asyncio.run(test_claude_with_tools())

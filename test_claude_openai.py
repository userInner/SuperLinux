"""Test Claude API with OpenAI-compatible format."""
import asyncio

async def test():
    print("Testing Claude via OpenAI-compatible API...")
    
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage
    
    # 使用 OpenAI 兼容格式
    llm = ChatOpenAI(
        model="claude-sonnet-4-5",
        api_key="sk-AB3uYbTGnrPRpSCD4z7Gz8Ykf4ZzT2DyTIMgTjIBKGsT7ep3",
        base_url="https://api.coolyeah.net/v1",  # 注意加 /v1
    )
    
    print("Sending request...")
    try:
        response = await asyncio.wait_for(
            llm.ainvoke([HumanMessage(content="Say hello in Chinese, 5 words only")]),
            timeout=60
        )
        print(f"✅ Response: {response.content}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

asyncio.run(test())

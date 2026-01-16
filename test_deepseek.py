"""Test DeepSeek API only."""
import asyncio

async def test():
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage
    
    print("Testing DeepSeek...")
    
    llm = ChatOpenAI(
        model="deepseek-chat",
        api_key="sk-ba34d2478d7d4dc29ef05e92b3e17e62",
        base_url="https://api.deepseek.com/v1",
    )
    
    try:
        response = await asyncio.wait_for(
            llm.ainvoke([HumanMessage(content="Say hi")]),
            timeout=60
        )
        print(f"✅ Response: {response.content}")
    except Exception as e:
        print(f"❌ Error: {e}")

asyncio.run(test())

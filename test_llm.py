"""Test LLM connection directly."""
import asyncio
import os

async def test_gemini():
    """Test Gemini API directly."""
    print("Testing Gemini API...")
    
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage
    
    api_key = "AIzaSyChw4JX7u9Ppj-V-h3RdSu-LjSzBadHokY"
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
    )
    
    print("Sending request...")
    try:
        response = await asyncio.wait_for(
            llm.ainvoke([HumanMessage(content="Say hello in 5 words")]),
            timeout=30
        )
        print(f"Response type: {type(response)}")
        print(f"Content type: {type(response.content)}")
        print(f"Content: {response.content}")
        print("✅ Gemini works!")
    except asyncio.TimeoutError:
        print("❌ Timeout!")
    except Exception as e:
        print(f"❌ Error: {e}")


async def test_gemini_with_tools():
    """Test Gemini with tools."""
    print("\nTesting Gemini with tools...")
    
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage
    
    api_key = "AIzaSyChw4JX7u9Ppj-V-h3RdSu-LjSzBadHokY"
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
    )
    
    # Simple tool
    tools = [{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather for a city",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"}
                },
                "required": ["city"]
            }
        }
    }]
    
    llm_with_tools = llm.bind_tools(tools)
    
    print("Sending request with tools...")
    try:
        response = await asyncio.wait_for(
            llm_with_tools.ainvoke([HumanMessage(content="What's the weather in Beijing?")]),
            timeout=30
        )
        print(f"Response type: {type(response)}")
        print(f"Content: {response.content}")
        print(f"Tool calls: {response.tool_calls}")
        print("✅ Gemini with tools works!")
    except asyncio.TimeoutError:
        print("❌ Timeout!")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def test_deepseek():
    """Test DeepSeek API."""
    print("\nTesting DeepSeek API...")
    
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage
    
    api_key = "sk-ba34d2478d7d4dc29ef05e92b3e17e62"
    
    llm = ChatOpenAI(
        model="deepseek-chat",
        api_key=api_key,
        base_url="https://api.deepseek.com/v1",
    )
    
    print("Sending request...")
    try:
        response = await asyncio.wait_for(
            llm.ainvoke([HumanMessage(content="Say hello in 5 words")]),
            timeout=30
        )
        print(f"Content: {response.content}")
        print("✅ DeepSeek works!")
    except asyncio.TimeoutError:
        print("❌ Timeout!")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_gemini())
    asyncio.run(test_gemini_with_tools())
    asyncio.run(test_deepseek())

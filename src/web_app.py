"""Web interface for Multi-AI Linux Agent with streaming support."""

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage, AIMessageChunk

from .orchestrator.llm_engine import create_llm_engine, LLMEngine
from .tools import execute_tool, get_all_tools
from .multi_agent import AIConfig, load_config_from_file, load_config_from_env
from .prompts import get_prompt
from .experience_rag import get_experience_rag

app = FastAPI(title="Linux AI Agent")


class StreamingWebAgent:
    """Agent with streaming output support and task-oriented completion."""
    
    def __init__(self, websocket: WebSocket):
        self.ws = websocket
        self.primary_engine = None
        self.secondary_engines = {}
        self.tools = get_all_tools()
        self.primary_llm = None
        
        # 持久化对话历史
        self.messages = []
        self.initialized = False
        
        # 任务控制
        self.should_stop = False
        
        # RAG 经验系统
        self.experience_rag = None
    
    async def send_event(self, event_type: str, data: dict):
        """Send event to frontend."""
        try:
            await self.ws.send_json({"type": event_type, **data})
        except:
            pass
    
    async def initialize(self):
        """Initialize AI engines from config."""
        if self.initialized:
            return True
            
        config = load_config_from_file()
        
        if config:
            primary = AIConfig(
                name=config.primary_ai.name,
                provider=config.primary_ai.provider,
                model=config.primary_ai.model,
                api_key=config.primary_ai.api_key,
                role="primary",
                base_url=config.primary_ai.base_url
            )
            secondary_list = [
                AIConfig(name=ai.name, provider=ai.provider, model=ai.model,
                        api_key=ai.api_key, role=ai.role, base_url=ai.base_url)
                for ai in config.secondary_ais
            ]
            self.max_retries = config.agent.max_retries
            self.search_before_consult = config.agent.search_attempts_before_consult
        else:
            primary, secondary_list = load_config_from_env()
            self.max_retries = 3
            self.search_before_consult = 2
        
        if not primary or not primary.api_key:
            await self.send_event("error", {"message": "No API key configured"})
            return False
        
        # Initialize primary with streaming enabled
        kwargs = {}
        if primary.base_url:
            kwargs['base_url'] = primary.base_url
        
        self.primary_engine = create_llm_engine(
            provider=primary.provider, model=primary.model, api_key=primary.api_key,
            **kwargs
        )
        self.primary_llm = self.primary_engine.bind_tools(self.tools)
        
        await self.send_event("status", {
            "message": f"✅ Primary AI: {primary.name} ({primary.model})"
        })
        
        # Initialize secondary
        for cfg in (secondary_list or []):
            kwargs = {}
            if cfg.base_url:
                kwargs['base_url'] = cfg.base_url
            engine = create_llm_engine(provider=cfg.provider, model=cfg.model, api_key=cfg.api_key, **kwargs)
            self.secondary_engines[cfg.name] = {"engine": engine, "config": cfg}
            await self.send_event("status", {
                "message": f"✅ Secondary AI: {cfg.name} ({cfg.model})"
            })
        
        # 初始化系统提示 - 使用新的提示词系统
        base_prompt = get_prompt("default")
        
        task_completion_instructions = """

## 任务完成机制

在最终回复末尾标注状态：
- `[STATUS: COMPLETED]` - 任务已完成
- `[STATUS: NEEDS_INPUT]` - 需要用户提供更多信息
- `[STATUS: FAILED: 原因]` - 任务失败

### 核心原则
1. **持续工作直到完成**: 不要中途停止
2. **遇到困难优先查官方文档**: 搜索 "[软件名] official documentation [问题]"
3. **写代码时**: 先创建目录，再逐个创建完整文件
"""
        
        system_prompt = base_prompt + task_completion_instructions

        self.messages = [SystemMessage(content=system_prompt)]
        self.initialized = True
        
        # 初始化 RAG 经验系统
        try:
            self.experience_rag = get_experience_rag()
            stats = self.experience_rag.get_stats()
            await self.send_event("status", {"message": f"📚 RAG: {stats.get('total_experiences', 0)} experiences"})
        except Exception as e:
            await self.send_event("status", {"message": f"⚠️ RAG init failed: {e}"})
        
        await self.send_event("status", {"message": f"✅ Loaded {len(self.tools)} tools"})
        return True
    
    def stop_current_task(self):
        """Stop the current running task."""
        self.should_stop = True
    
    async def stream_response(self, iteration: int):
        """Stream LLM response token by token."""
        full_content = ""
        tool_calls = []
        tool_call_chunks = {}
        
        await self.send_event("stream_start", {"iteration": iteration})
        
        try:
            async for chunk in self.primary_llm.astream(self.messages):
                if self.should_stop:
                    break
                
                # 处理文本内容 - 兼容不同格式
                if chunk.content:
                    content_text = ""
                    if isinstance(chunk.content, str):
                        content_text = chunk.content
                    elif isinstance(chunk.content, list):
                        # Gemini 可能返回 list 格式
                        for item in chunk.content:
                            if isinstance(item, str):
                                content_text += item
                            elif isinstance(item, dict) and item.get('text'):
                                content_text += item['text']
                    
                    if content_text:
                        full_content += content_text
                        await self.send_event("stream_token", {"token": content_text})
                
                # 处理工具调用（流式）- 使用 tool_call_chunks 属性
                if hasattr(chunk, 'tool_call_chunks') and chunk.tool_call_chunks:
                    for tc_chunk in chunk.tool_call_chunks:
                        idx = tc_chunk.get('index', 0)
                        if idx not in tool_call_chunks:
                            tool_call_chunks[idx] = {
                                'id': '',
                                'name': '',
                                'args': ''
                            }
                        
                        if tc_chunk.get('id'):
                            tool_call_chunks[idx]['id'] = tc_chunk['id']
                        if tc_chunk.get('name'):
                            tool_call_chunks[idx]['name'] = tc_chunk['name']
                        if tc_chunk.get('args'):
                            tool_call_chunks[idx]['args'] += tc_chunk['args']
                            # 流式显示工具参数
                            await self.send_event("stream_tool_arg", {
                                "index": idx,
                                "name": tool_call_chunks[idx]['name'],
                                "arg_chunk": tc_chunk['args']
                            })
                
                # 有些模型直接返回完整的 tool_calls
                if hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                    for tc in chunk.tool_calls:
                        # 检查是否是完整的工具调用（有 name 和 args）
                        if isinstance(tc, dict) and tc.get('name') and 'args' in tc:
                            tool_calls.append(tc)
            
            # 从 chunks 组装工具调用
            for idx in sorted(tool_call_chunks.keys()):
                tc = tool_call_chunks[idx]
                if tc['name'] and tc['args']:
                    try:
                        args = json.loads(tc['args'])
                    except json.JSONDecodeError:
                        # 参数解析失败，跳过这个工具调用
                        await self.send_event("status", {"message": f"⚠️ 工具参数解析失败: {tc['name']}"})
                        continue
                    
                    # 检查是否已经存在相同的工具调用
                    exists = any(
                        t.get('name') == tc['name'] and t.get('args') == args 
                        for t in tool_calls
                    )
                    if not exists:
                        tool_calls.append({
                            'id': tc['id'] or f"call_{idx}",
                            'name': tc['name'],
                            'args': args
                        })
            
            await self.send_event("stream_end", {})
            
            # 构建 AI 消息
            if tool_calls:
                response = AIMessage(content=full_content, tool_calls=tool_calls)
            else:
                response = AIMessage(content=full_content)
            
            return response
            
        except Exception as e:
            await self.send_event("error", {"message": f"Stream error: {str(e)}"})
            return None
    
    async def chat(self, message: str):
        """Process message with task-oriented completion and RAG support."""
        if not await self.initialize():
            return
        
        self.should_stop = False
        
        # RAG: 检索相关经验
        if self.experience_rag:
            try:
                similar = self.experience_rag.search_similar(message, top_k=2)
                if similar:
                    exp_context = self.experience_rag.format_experiences_for_prompt(similar)
                    await self.send_event("status", {"message": f"📚 Found {len(similar)} relevant experiences"})
                    # 将经验作为系统消息添加
                    self.messages.append(SystemMessage(content=exp_context))
            except Exception as e:
                await self.send_event("status", {"message": f"⚠️ RAG search failed: {e}"})
        
        # 添加用户消息到历史
        self.messages.append(HumanMessage(content=message))
        
        # 追踪状态（用于保存经验）
        all_steps = []
        tools_used = []
        errors = []
        docs_consulted = []
        error_tracker = {}
        consecutive_no_progress = 0
        
        while True:  # 任务导向循环，不限制迭代次数
            if self.should_stop:
                await self.send_event("stopped", {"message": "任务已中断"})
                return
            
            try:
                await self.send_event("thinking", {"iteration": len(all_steps) + 1})
                
                # 流式获取响应
                full_content = ""
                tool_call_chunks = {}
                chunk_count = 0
                
                await self.send_event("stream_start", {})
                
                try:
                    # 设置最大 chunk 数量限制，防止无限生成
                    MAX_CHUNKS = 5000
                    STREAM_TIMEOUT = 180  # 流式响应最大 180 秒
                    stream_start_time = asyncio.get_event_loop().time()
                    forced_stop = False  # 标记是否强制停止
                    
                    async for chunk in self.primary_llm.astream(self.messages):
                        if self.should_stop:
                            break
                        
                        chunk_count += 1
                        
                        # 超过最大 chunk 数量，强制停止
                        if chunk_count >= MAX_CHUNKS:
                            await self.send_event("status", {"message": f"⚠️ 达到最大 chunk 限制 ({MAX_CHUNKS})，强制结束"})
                            forced_stop = True
                            break
                        
                        # 超时检查
                        elapsed = asyncio.get_event_loop().time() - stream_start_time
                        if elapsed > STREAM_TIMEOUT:
                            await self.send_event("status", {"message": f"⚠️ 流式响应超时 ({STREAM_TIMEOUT}s)，强制结束"})
                            forced_stop = True
                            break
                        
                        if chunk_count % 100 == 0:
                            # 显示当前生成的内容预览
                            preview = full_content[-200:] if len(full_content) > 200 else full_content
                            preview = preview.replace('\n', ' ')[:100]  # 单行预览
                            await self.send_event("status", {"message": f"📦 {chunk_count} chunks | 预览: {preview}..."})
                        
                        # 处理文本内容
                        if chunk.content:
                            text = ""
                            if isinstance(chunk.content, str):
                                text = chunk.content
                            elif isinstance(chunk.content, list):
                                for item in chunk.content:
                                    if isinstance(item, str):
                                        text += item
                                    elif isinstance(item, dict) and item.get('text'):
                                        text += item['text']
                            
                            if text:
                                full_content += text
                                await self.send_event("stream_token", {"token": text})
                        
                        # 累积工具调用 chunks
                        if hasattr(chunk, 'tool_call_chunks') and chunk.tool_call_chunks:
                            for tc_chunk in chunk.tool_call_chunks:
                                idx = tc_chunk.get('index', 0)
                                if idx not in tool_call_chunks:
                                    tool_call_chunks[idx] = {'id': '', 'name': '', 'args': ''}
                                
                                if tc_chunk.get('id'):
                                    tool_call_chunks[idx]['id'] = tc_chunk['id']
                                if tc_chunk.get('name'):
                                    tool_call_chunks[idx]['name'] = tc_chunk['name']
                                    await self.send_event("status", {"message": f"🔧 检测到工具: {tc_chunk['name']}"})
                                if tc_chunk.get('args'):
                                    tool_call_chunks[idx]['args'] += tc_chunk['args']
                        
                        if hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                            for i, tc in enumerate(chunk.tool_calls):
                                if isinstance(tc, dict) and tc.get('name') and tc.get('args'):
                                    idx = tc.get('index', i)
                                    tool_call_chunks[idx] = {
                                        'id': tc.get('id', f'call_{idx}'),
                                        'name': tc['name'],
                                        'args': json.dumps(tc['args']) if isinstance(tc['args'], dict) else tc['args']
                                    }
                                    await self.send_event("status", {"message": f"🔧 工具调用: {tc['name']}"})
                
                except asyncio.TimeoutError:
                    await self.send_event("error", {"message": "流式响应超时"})
                    return
                
                await self.send_event("stream_end", {"chunks": chunk_count})
                
                # 解析工具调用
                tool_calls = []
                for idx in sorted(tool_call_chunks.keys()):
                    tc = tool_call_chunks[idx]
                    if tc['name']:
                        try:
                            args = json.loads(tc['args']) if tc['args'] else {}
                        except json.JSONDecodeError:
                            args = {}
                        
                        if args or tc['name'] in ['get_system_stats', 'get_cpu_info', 'get_memory_info', 'get_disk_info']:
                            tool_calls.append({
                                'id': tc['id'] or f'call_{idx}',
                                'name': tc['name'],
                                'args': args
                            })
                
                # 构建响应消息
                if tool_calls:
                    response = AIMessage(content=full_content, tool_calls=tool_calls)
                else:
                    response = AIMessage(content=full_content)
                
                self.messages.append(response)
                
                # 检查任务状态
                if not tool_calls:
                    # 如果是强制停止，直接返回已生成的内容
                    if forced_stop:
                        await self.send_event("response", {"content": full_content + "\n\n⚠️ (内容生成被截断)"})
                        return
                    
                    # 解析状态
                    content_lower = full_content.lower()
                    task_completed = "[status: completed]" in content_lower
                    task_failed = "[status: failed" in content_lower
                    needs_input = "[status: needs_input]" in content_lower
                    
                    clean_content = full_content
                    for tag in ["[STATUS: COMPLETED]", "[STATUS: NEEDS_INPUT]", "[STATUS: IN_PROGRESS]"]:
                        clean_content = clean_content.replace(tag, "").strip()
                    
                    if task_completed or task_failed:
                        # 保存经验
                        if self.experience_rag:
                            try:
                                self.experience_rag.save_experience(
                                    problem=message,
                                    solution=clean_content[:500],
                                    steps=all_steps[-10:],
                                    tools_used=tools_used,
                                    errors_encountered=errors[-5:],
                                    docs_consulted=docs_consulted[-5:],
                                    success=task_completed
                                )
                                await self.send_event("status", {"message": "💾 Experience saved"})
                            except:
                                pass
                        
                        await self.send_event("response", {"content": clean_content})
                        return
                    elif needs_input:
                        await self.send_event("response", {"content": clean_content})
                        return
                    else:
                        # 没有明确状态，检查是否卡住
                        consecutive_no_progress += 1
                        if consecutive_no_progress >= 2:
                            await self.send_event("response", {"content": full_content})
                            return
                        # 提醒标记状态
                        self.messages.append(HumanMessage(
                            content="请确认任务是否完成，并标注 [STATUS: COMPLETED] 或继续执行。"
                        ))
                        continue
                
                consecutive_no_progress = 0
                
                # 执行工具调用
                for tool_call in tool_calls:
                    if self.should_stop:
                        await self.send_event("stopped", {"message": "任务已中断"})
                        return
                    
                    tool_name = tool_call['name']
                    tool_args = tool_call['args']
                    tool_id = tool_call['id']
                    
                    # 记录步骤
                    step_desc = f"{tool_name}: {str(tool_args)[:80]}"
                    all_steps.append(step_desc)
                    if tool_name not in tools_used:
                        tools_used.append(tool_name)
                    
                    if tool_name == "fetch_webpage":
                        docs_consulted.append(tool_args.get("url", ""))
                    
                    await self.send_event("tool_call", {
                        "name": tool_name,
                        "args": tool_args,
                        "iteration": len(all_steps)
                    })
                    
                    try:
                        result = await asyncio.wait_for(
                            execute_tool(tool_name, tool_args),
                            timeout=120
                        )
                    except asyncio.TimeoutError:
                        result = json.dumps({"error": True, "message": "Tool execution timed out"})
                    
                    try:
                        result_data = json.loads(result)
                        is_error = result_data.get("error", False)
                        error_msg = result_data.get("message", "")
                    except:
                        is_error = False
                        error_msg = ""
                    
                    await self.send_event("tool_result", {
                        "name": tool_name,
                        "result": result[:3000],
                        "is_error": is_error
                    })
                    
                    if is_error:
                        errors.append(error_msg)
                        error_key = f"{tool_name}:{error_msg[:50]}"
                        error_tracker[error_key] = error_tracker.get(error_key, 0) + 1
                        
                        # 重复错误提示查官方文档
                        if error_tracker[error_key] >= 3:
                            hint = f"""
这个错误已出现 {error_tracker[error_key]} 次: {error_msg}

请优先查阅官方文档:
1. web_search 搜索 "[软件名] official documentation [错误关键词]"
2. fetch_webpage 获取文档内容
3. 按官方指导操作
"""
                            self.messages.append(ToolMessage(content=result, tool_call_id=tool_id))
                            self.messages.append(HumanMessage(content=hint))
                            continue
                    
                    # 简化写文件结果
                    if tool_name == "write_file" and not is_error:
                        try:
                            simplified = {"success": True, "path": result_data.get("path"), "size": result_data.get("size")}
                            result_for_history = json.dumps(simplified, ensure_ascii=False)
                        except:
                            result_for_history = result[:1000]
                    else:
                        result_for_history = result[:5000] if len(result) > 5000 else result
                    
                    self.messages.append(ToolMessage(content=result_for_history, tool_call_id=tool_id))
                    
            except Exception as e:
                await self.send_event("error", {"message": f"错误: {str(e)}"})
                import traceback
                traceback.print_exc()
                return
    
    async def clear_history(self):
        """Clear conversation history but keep system prompt."""
        if self.messages:
            self.messages = self.messages[:1]
        await self.send_event("cleared", {"message": "对话历史已清除"})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for chat."""
    await websocket.accept()
    agent = StreamingWebAgent(websocket)
    current_task = None
    
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            if msg_type == "chat":
                if current_task and not current_task.done():
                    agent.stop_current_task()
                    await asyncio.sleep(0.1)
                
                agent.should_stop = False
                current_task = asyncio.create_task(agent.chat(data.get("message", "")))
            elif msg_type == "stop":
                agent.stop_current_task()
            elif msg_type == "clear":
                await agent.clear_history()
                
    except WebSocketDisconnect:
        if current_task:
            agent.stop_current_task()


@app.get("/")
async def get_index():
    return HTMLResponse(HTML_CONTENT)


HTML_CONTENT = '''
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Linux AI Agent</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .header {
            background: #16213e;
            padding: 12px 20px;
            border-bottom: 1px solid #0f3460;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .header h1 { font-size: 1.2em; color: #00d9ff; display: flex; align-items: center; gap: 10px; }
        .header-btns { display: flex; gap: 10px; }
        .header-btns button {
            padding: 6px 12px;
            border: 1px solid #444;
            border-radius: 5px;
            background: transparent;
            color: #aaa;
            cursor: pointer;
            font-size: 0.85em;
        }
        .header-btns button:hover { background: #333; color: #fff; }
        .main { flex: 1; display: flex; overflow: hidden; }
        .chat-panel { flex: 1; display: flex; flex-direction: column; }
        .log-panel {
            width: 500px;
            display: flex;
            flex-direction: column;
            background: #0f0f1a;
            border-left: 1px solid #0f3460;
        }
        .panel-header {
            padding: 10px 15px;
            background: #16213e;
            font-weight: 600;
            font-size: 0.85em;
            color: #888;
            display: flex;
            justify-content: space-between;
        }
        .messages { flex: 1; overflow-y: auto; padding: 15px; }
        .message {
            margin-bottom: 12px;
            padding: 10px 14px;
            border-radius: 8px;
            max-width: 90%;
            line-height: 1.6;
            white-space: pre-wrap;
        }
        .message.user { background: #0f3460; margin-left: auto; }
        .message.assistant { background: #1e1e30; border: 1px solid #333; }
        .message.system { background: #2a2a3a; color: #888; font-size: 0.9em; text-align: center; max-width: 100%; }
        .message.streaming { border: 1px solid #00d9ff; }
        .input-area {
            padding: 12px 15px;
            background: #16213e;
            display: flex;
            gap: 10px;
        }
        input[type="text"] {
            flex: 1;
            padding: 10px 14px;
            border: none;
            border-radius: 6px;
            background: #1a1a2e;
            color: #fff;
            font-size: 0.95em;
        }
        input[type="text"]:focus { outline: 2px solid #00d9ff; }
        .input-area button {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
        }
        .btn-send { background: #00d9ff; color: #000; }
        .btn-stop { background: #ff4757; color: #fff; }
        .logs {
            flex: 1;
            overflow-y: auto;
            padding: 8px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.75em;
        }
        .log-entry {
            padding: 6px 8px;
            margin-bottom: 4px;
            border-radius: 4px;
            background: #1a1a2e;
        }
        .log-entry.tool { border-left: 3px solid #ffd700; }
        .log-entry.result { border-left: 3px solid #00ff88; }
        .log-entry.error { border-left: 3px solid #ff4444; }
        .log-entry.status { border-left: 3px solid #00d9ff; color: #888; }
        .log-entry.stream { border-left: 3px solid #aa88ff; background: #1a1a30; }
        .log-entry.stream .log-content { 
            max-height: 400px; 
            font-size: 0.8em;
            line-height: 1.4;
        }
        .log-label { font-weight: 600; margin-bottom: 3px; }
        .log-content {
            color: #aaa;
            white-space: pre-wrap;
            word-break: break-all;
            max-height: 200px;
            overflow-y: auto;
        }
        .status-dot { width: 8px; height: 8px; border-radius: 50%; background: #555; }
        .status-dot.connected { background: #00ff88; }
        .status-dot.working { background: #ffd700; animation: pulse 1s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        .stream-content { color: #00d9ff; font-family: monospace; }
        .cursor { animation: blink 1s infinite; }
        @keyframes blink { 0%, 50% { opacity: 1; } 51%, 100% { opacity: 0; } }
        /* Markdown 样式 */
        .message.assistant h1, .message.assistant h2, .message.assistant h3 { 
            margin: 12px 0 8px 0; color: #00d9ff; 
        }
        .message.assistant h1 { font-size: 1.4em; }
        .message.assistant h2 { font-size: 1.2em; }
        .message.assistant h3 { font-size: 1.1em; }
        .message.assistant ul, .message.assistant ol { margin: 8px 0; padding-left: 20px; }
        .message.assistant li { margin: 4px 0; }
        .message.assistant code { 
            background: #2a2a3a; padding: 2px 6px; border-radius: 4px; 
            font-family: 'Monaco', 'Consolas', monospace; font-size: 0.9em;
        }
        .message.assistant pre { 
            background: #1a1a2e; padding: 12px; border-radius: 6px; 
            overflow-x: auto; margin: 10px 0;
        }
        .message.assistant pre code { background: none; padding: 0; }
        .message.assistant table { border-collapse: collapse; margin: 10px 0; width: 100%; }
        .message.assistant th, .message.assistant td { 
            border: 1px solid #444; padding: 8px; text-align: left; 
        }
        .message.assistant th { background: #2a2a3a; }
        .message.assistant blockquote { 
            border-left: 3px solid #00d9ff; margin: 10px 0; padding-left: 12px; color: #aaa; 
        }
        .message.assistant hr { border: none; border-top: 1px solid #444; margin: 15px 0; }
        .message.assistant strong { color: #fff; }
        .message.assistant a { color: #00d9ff; }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script>
        // 确保 marked 加载完成
        if (typeof marked !== 'undefined') {
            marked.setOptions({ breaks: true, gfm: true });
        }
    </script>
</head>
<body>
    <div class="header">
        <h1><span class="status-dot" id="status"></span> Linux AI Agent (Streaming)</h1>
        <div class="header-btns">
            <button onclick="clearChat()">清除对话</button>
            <button onclick="clearLogs()">清除日志</button>
        </div>
    </div>
    <div class="main">
        <div class="chat-panel">
            <div class="messages" id="messages"></div>
            <div class="input-area">
                <input type="text" id="input" placeholder="输入指令..." />
                <button class="btn-send" id="sendBtn" onclick="sendMessage()">发送</button>
                <button class="btn-stop" id="stopBtn" onclick="stopTask()" style="display:none;">停止</button>
            </div>
        </div>
        <div class="log-panel">
            <div class="panel-header">
                <span>📋 执行日志 (实时流)</span>
                <span id="msgCount">0 条</span>
            </div>
            <div class="logs" id="logs"></div>
        </div>
    </div>
    <script>
        let ws, isWorking = false, msgCount = 0;
        let currentStreamDiv = null, currentStreamContent = '';
        let currentToolStreamDiv = null, currentToolArgs = {};
        
        const messages = document.getElementById('messages');
        const logs = document.getElementById('logs');
        const input = document.getElementById('input');
        const sendBtn = document.getElementById('sendBtn');
        const stopBtn = document.getElementById('stopBtn');
        const status = document.getElementById('status');

        function connect() {
            ws = new WebSocket(`ws://${location.host}/ws`);
            ws.onopen = () => { status.className = 'status-dot connected'; addLog('status', '已连接', ''); };
            ws.onclose = () => { status.className = 'status-dot'; setTimeout(connect, 2000); };
            ws.onmessage = (e) => handleEvent(JSON.parse(e.data));
        }

        function setWorking(working) {
            isWorking = working;
            status.className = working ? 'status-dot working' : 'status-dot connected';
            sendBtn.style.display = working ? 'none' : 'block';
            stopBtn.style.display = working ? 'block' : 'none';
        }

        function handleEvent(event) {
            switch(event.type) {
                case 'status':
                    addLog('status', '状态', event.message);
                    break;
                case 'thinking':
                    setWorking(true);
                    addLog('status', `🤔 迭代 #${event.iteration}`, '思考中...');
                    break;
                case 'ai_text':
                    addLog('status', '💭 AI', event.content);
                    break;
                case 'stream_start':
                    currentStreamContent = '';
                    currentStreamDiv = document.createElement('div');
                    currentStreamDiv.className = 'log-entry stream';
                    currentStreamDiv.innerHTML = '<div class="log-label">📝 AI 生成中...</div><div class="log-content stream-content"></div>';
                    logs.appendChild(currentStreamDiv);
                    break;
                case 'stream_token':
                    if (currentStreamDiv) {
                        currentStreamContent += event.token;
                        const contentDiv = currentStreamDiv.querySelector('.stream-content');
                        // 显示最后 800 字符，让用户看到更多内容
                        contentDiv.textContent = currentStreamContent.slice(-800) + '▌';
                        logs.scrollTop = logs.scrollHeight;
                    }
                    break;
                case 'stream_end':
                    if (currentStreamDiv) {
                        const contentDiv = currentStreamDiv.querySelector('.stream-content');
                        const info = event.chunks ? ` (${event.chunks} chunks)` : '';
                        contentDiv.textContent = currentStreamContent ? currentStreamContent.slice(-300) + info : '(调用工具中...)';
                    }
                    currentStreamDiv = null;
                    break;
                case 'tool_call':
                    addLog('tool', `🔧 ${event.name}`, JSON.stringify(event.args, null, 2));
                    break;
                case 'tool_result':
                    addLog(event.is_error ? 'error' : 'result', 
                           event.is_error ? '❌ 错误' : '✅ 结果', event.result);
                    break;
                case 'response':
                    setWorking(false);
                    addMessage('assistant', event.content);
                    break;
                case 'stopped':
                    setWorking(false);
                    addLog('status', '⏹️ 已停止', event.message);
                    break;
                case 'cleared':
                    addMessage('system', event.message);
                    break;
                case 'error':
                    setWorking(false);
                    addLog('error', '❌ 错误', event.message);
                    break;
            }
        }

        function addMessage(role, content) {
            msgCount++;
            document.getElementById('msgCount').textContent = `${msgCount} 条`;
            const div = document.createElement('div');
            div.className = `message ${role}`;
            // AI 回复用 Markdown 渲染
            if (role === 'assistant') {
                if (typeof marked !== 'undefined' && marked.parse) {
                    try {
                        div.innerHTML = marked.parse(content);
                    } catch(e) {
                        div.innerHTML = simpleMarkdown(content);
                    }
                } else {
                    div.innerHTML = simpleMarkdown(content);
                }
            } else {
                div.textContent = content;
            }
            messages.appendChild(div);
            messages.scrollTop = messages.scrollHeight;
        }
        
        // 简单的 Markdown 解析备用方案 - 不使用正则
        function simpleMarkdown(text) {
            if (!text) return '';
            // 直接用 split/join 替换，避免正则
            var html = String(text);
            html = html.split('&').join('&amp;');
            html = html.split('<').join('&lt;');
            html = html.split('>').join('&gt;');
            html = html.split(String.fromCharCode(10)).join('<br>');
            return html;
        }

        function addLog(type, label, content) {
            const div = document.createElement('div');
            div.className = `log-entry ${type}`;
            div.innerHTML = `<div class="log-label">${label}</div>${content ? `<div class="log-content">${escapeHtml(content)}</div>` : ''}`;
            logs.appendChild(div);
            logs.scrollTop = logs.scrollHeight;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function sendMessage() {
            const msg = input.value.trim();
            if (!msg || !ws || ws.readyState !== 1) return;
            addMessage('user', msg);
            ws.send(JSON.stringify({type: 'chat', message: msg}));
            input.value = '';
            setWorking(true);
        }

        function stopTask() {
            if (ws && ws.readyState === 1) ws.send(JSON.stringify({type: 'stop'}));
        }

        function clearChat() {
            if (ws && ws.readyState === 1) ws.send(JSON.stringify({type: 'clear'}));
            messages.innerHTML = '';
            msgCount = 0;
            document.getElementById('msgCount').textContent = '0 条';
        }

        function clearLogs() { logs.innerHTML = ''; }

        input.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });
        connect();
    </script>
</body>
</html>
'''

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

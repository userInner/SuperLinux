"""Web interface for Multi-AI Linux Agent."""

import asyncio
import json
from typing import AsyncGenerator
from dataclasses import dataclass

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, SystemMessage

from .orchestrator.llm_engine import create_llm_engine, LLMEngine
from .tools import execute_tool, get_all_tools
from .multi_agent import AIConfig, load_config_from_file, load_config_from_env

app = FastAPI(title="Linux AI Agent")


class WebAgent:
    """Agent that streams events to websocket."""
    
    def __init__(self, websocket: WebSocket):
        self.ws = websocket
        self.primary_engine = None
        self.secondary_engines = {}
        self.tools = get_all_tools()
        self.primary_llm = None
        self.config = None
    
    async def send_event(self, event_type: str, data: dict):
        """Send event to frontend."""
        await self.ws.send_json({"type": event_type, **data})
    
    async def initialize(self):
        """Initialize AI engines from config."""
        config = load_config_from_file()
        
        if config:
            primary = AIConfig(
                name=config.primary_ai.name,
                provider=config.primary_ai.provider,
                model=config.primary_ai.model,
                api_key=config.primary_ai.api_key,
                role="primary"
            )
            secondary_list = [
                AIConfig(name=ai.name, provider=ai.provider, model=ai.model,
                        api_key=ai.api_key, role=ai.role)
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
        
        # Initialize primary
        self.primary_engine = create_llm_engine(
            provider=primary.provider, model=primary.model, api_key=primary.api_key
        )
        self.primary_llm = self.primary_engine.bind_tools(self.tools)
        
        await self.send_event("status", {
            "message": f"Primary AI: {primary.name} ({primary.model})"
        })
        
        # Initialize secondary
        for cfg in (secondary_list or []):
            engine = create_llm_engine(provider=cfg.provider, model=cfg.model, api_key=cfg.api_key)
            self.secondary_engines[cfg.name] = {"engine": engine, "config": cfg}
            await self.send_event("status", {
                "message": f"Secondary AI: {cfg.name} ({cfg.model})"
            })
        
        return True
    
    async def consult_secondary(self, ai_name: str, problem: str, attempts: list, errors: list) -> str:
        """Consult secondary AI."""
        if ai_name not in self.secondary_engines:
            return "Secondary AI not available"
        
        engine = self.secondary_engines[ai_name]["engine"]
        
        prompt = f"""你是专家顾问，另一个 AI 遇到困难需要帮助。

## 问题
{problem}

## 已尝试
{chr(10).join(f"- {a}" for a in attempts) if attempts else "无"}

## 错误
{chr(10).join(f"- {e}" for e in errors) if errors else "无"}

请提供具体可操作的解决建议。"""

        await self.send_event("consulting", {"ai": ai_name})
        response = await engine.llm.ainvoke([HumanMessage(content=prompt)])
        return response.content
    
    async def chat(self, message: str):
        """Process message and stream events."""
        if not self.primary_llm:
            if not await self.initialize():
                return
        
        system_prompt = """你是智能 Linux 系统管理助手。

可用工具: get_system_stats, get_cpu_info, get_memory_info, get_disk_info, 
list_services, web_search, fetch_webpage, run_command

策略: 1.直接解决 2.失败则搜索 3.仍失败则请求顾问帮助"""

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=message)]
        
        error_count = 0
        search_count = 0
        attempts = []
        errors = []
        consulted = False
        
        for iteration in range(15):
            await self.send_event("thinking", {"iteration": iteration + 1})
            
            response = await self.primary_llm.ainvoke(messages)
            messages.append(response)
            
            if not response.tool_calls:
                await self.send_event("response", {"content": response.content})
                return
            
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call["id"]
                
                await self.send_event("tool_call", {
                    "name": tool_name,
                    "args": tool_args,
                    "iteration": iteration + 1
                })
                
                result = await execute_tool(tool_name, tool_args)
                
                # Track
                if tool_name == "run_command":
                    attempts.append(tool_args.get("command", ""))
                elif tool_name == "web_search":
                    search_count += 1
                
                # Check error
                try:
                    result_data = json.loads(result)
                    is_error = result_data.get("error", False)
                except:
                    is_error = False
                
                await self.send_event("tool_result", {
                    "name": tool_name,
                    "result": result[:2000],  # Truncate for display
                    "is_error": is_error
                })
                
                if is_error:
                    error_count += 1
                    errors.append(result_data.get("message", "Unknown"))
                    
                    # Consult secondary?
                    if (not consulted and self.secondary_engines and 
                        error_count >= self.max_retries and 
                        search_count >= self.search_before_consult):
                        
                        consulted = True
                        secondary_name = list(self.secondary_engines.keys())[0]
                        advice = await self.consult_secondary(secondary_name, message, attempts, errors)
                        
                        await self.send_event("advice", {"from": secondary_name, "content": advice})
                        
                        messages.append(ToolMessage(content=result, tool_call_id=tool_id))
                        messages.append(HumanMessage(content=f"[来自 {secondary_name} 的建议]\n\n{advice}\n\n请根据建议重试。"))
                        error_count = 0
                        search_count = 0
                        continue
                else:
                    error_count = 0
                
                messages.append(ToolMessage(content=result, tool_call_id=tool_id))
        
        await self.send_event("response", {"content": "达到最大迭代次数，可能需要人工介入。"})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for chat."""
    await websocket.accept()
    agent = WebAgent(websocket)
    
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "chat":
                await agent.chat(data.get("message", ""))
    except WebSocketDisconnect:
        pass


@app.get("/")
async def get_index():
    """Serve the main page."""
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
            padding: 15px 20px;
            border-bottom: 1px solid #0f3460;
        }
        .header h1 { font-size: 1.3em; color: #00d9ff; }
        .main {
            flex: 1;
            display: flex;
            overflow: hidden;
        }
        .chat-panel {
            flex: 1;
            display: flex;
            flex-direction: column;
            border-right: 1px solid #0f3460;
        }
        .log-panel {
            width: 400px;
            display: flex;
            flex-direction: column;
            background: #0f0f1a;
        }
        .panel-header {
            padding: 10px 15px;
            background: #16213e;
            font-weight: 600;
            font-size: 0.9em;
            color: #888;
        }
        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 15px;
        }
        .message {
            margin-bottom: 15px;
            padding: 12px 15px;
            border-radius: 10px;
            max-width: 85%;
        }
        .message.user {
            background: #0f3460;
            margin-left: auto;
        }
        .message.assistant {
            background: #1a1a2e;
            border: 1px solid #333;
        }
        .message.thinking {
            background: #2d2d44;
            color: #aaa;
            font-style: italic;
        }
        .input-area {
            padding: 15px;
            background: #16213e;
            display: flex;
            gap: 10px;
        }
        input[type="text"] {
            flex: 1;
            padding: 12px 15px;
            border: none;
            border-radius: 8px;
            background: #1a1a2e;
            color: #fff;
            font-size: 1em;
        }
        input[type="text"]:focus { outline: 2px solid #00d9ff; }
        button {
            padding: 12px 25px;
            border: none;
            border-radius: 8px;
            background: #00d9ff;
            color: #000;
            font-weight: 600;
            cursor: pointer;
        }
        button:hover { background: #00b8d9; }
        button:disabled { background: #555; cursor: not-allowed; }
        .logs {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.8em;
        }
        .log-entry {
            padding: 8px 10px;
            margin-bottom: 5px;
            border-radius: 5px;
            background: #1a1a2e;
        }
        .log-entry.tool { border-left: 3px solid #ffd700; }
        .log-entry.result { border-left: 3px solid #00ff88; }
        .log-entry.error { border-left: 3px solid #ff4444; }
        .log-entry.consult { border-left: 3px solid #ff00ff; }
        .log-entry.status { border-left: 3px solid #00d9ff; color: #888; }
        .log-label {
            font-weight: 600;
            margin-bottom: 5px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .log-content {
            color: #aaa;
            white-space: pre-wrap;
            word-break: break-all;
            max-height: 150px;
            overflow-y: auto;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #555;
        }
        .status-dot.connected { background: #00ff88; }
        .status-dot.thinking { background: #ffd700; animation: pulse 1s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 Linux AI Agent <span class="status-dot" id="status"></span></h1>
    </div>
    <div class="main">
        <div class="chat-panel">
            <div class="messages" id="messages"></div>
            <div class="input-area">
                <input type="text" id="input" placeholder="输入指令，如：查看系统状态、帮我配置nginx..." />
                <button id="send" onclick="sendMessage()">发送</button>
            </div>
        </div>
        <div class="log-panel">
            <div class="panel-header">📋 执行日志</div>
            <div class="logs" id="logs"></div>
        </div>
    </div>
    <script>
        let ws;
        const messages = document.getElementById('messages');
        const logs = document.getElementById('logs');
        const input = document.getElementById('input');
        const sendBtn = document.getElementById('send');
        const status = document.getElementById('status');

        function connect() {
            ws = new WebSocket(`ws://${location.host}/ws`);
            ws.onopen = () => { status.className = 'status-dot connected'; };
            ws.onclose = () => { status.className = 'status-dot'; setTimeout(connect, 2000); };
            ws.onmessage = (e) => handleEvent(JSON.parse(e.data));
        }

        function handleEvent(event) {
            switch(event.type) {
                case 'status':
                    addLog('status', '状态', event.message);
                    break;
                case 'thinking':
                    status.className = 'status-dot thinking';
                    break;
                case 'tool_call':
                    addLog('tool', `🔧 ${event.name}`, JSON.stringify(event.args, null, 2));
                    break;
                case 'tool_result':
                    addLog(event.is_error ? 'error' : 'result', 
                           event.is_error ? '❌ 错误' : '✅ 结果', 
                           event.result);
                    break;
                case 'consulting':
                    addLog('consult', '🤝 咨询', `正在咨询 ${event.ai}...`);
                    break;
                case 'advice':
                    addLog('consult', `💡 ${event.from} 建议`, event.content);
                    break;
                case 'response':
                    status.className = 'status-dot connected';
                    addMessage('assistant', event.content);
                    sendBtn.disabled = false;
                    break;
                case 'error':
                    addLog('error', '错误', event.message);
                    sendBtn.disabled = false;
                    break;
            }
        }

        function addMessage(role, content) {
            const div = document.createElement('div');
            div.className = `message ${role}`;
            div.innerHTML = content.replace(/\\n/g, '<br>');
            messages.appendChild(div);
            messages.scrollTop = messages.scrollHeight;
        }

        function addLog(type, label, content) {
            const div = document.createElement('div');
            div.className = `log-entry ${type}`;
            div.innerHTML = `<div class="log-label">${label}</div><div class="log-content">${escapeHtml(content)}</div>`;
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
            sendBtn.disabled = true;
            logs.innerHTML = '';
        }

        input.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });
        connect();
    </script>
</body>
</html>
'''

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

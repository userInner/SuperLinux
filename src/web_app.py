"""Web interface for SuperLinux Agent with streaming support."""

import asyncio
import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage, AIMessageChunk

from .orchestrator.llm_engine import create_llm_engine, LLMEngine
from .tools import execute_tool, get_all_tools
from .multi_agent import AIConfig, load_config_from_file, load_config_from_env
from .prompts import get_prompt
from .experience_rag import get_experience_rag

# 全局自动进化调度器
_evolution_scheduler: Optional[asyncio.Task] = None
_evolution_enabled = False


async def _auto_evolution_loop():
    """自动进化循环 - 无限运行，一轮结束立即开始下一轮"""
    from .self_evolution import get_evolution_engine
    from .self_diagnosis import get_evaluator
    from .code_auditor import get_auditor
    from .auto_fixer import auto_fix_code
    
    config = load_config_from_file()
    if not config:
        return
    
    # 读取配置
    evolution_config = getattr(config.agent, 'auto_evolution', None)
    if not evolution_config or not getattr(evolution_config, 'enabled', False):
        return
    
    interval_hours = getattr(evolution_config, 'check_interval_hours', 24)
    min_tasks = getattr(evolution_config, 'min_tasks_before_evolution', 10)
    auto_apply = getattr(evolution_config, 'auto_apply_improvements', False)
    
    # 如果 min_tasks 为 0，说明是无限进化模式
    infinite_mode = (min_tasks == 0)
    
    if infinite_mode:
        print(f"\n🧬 无限进化模式已启动 - 永不停止")
        print(f"   模式: 一轮结束立即开始下一轮")
        print(f"   自动应用: 是\n")
    else:
        print(f"\n🧬 自动进化模式已启动")
        print(f"   检查间隔: {interval_hours} 小时")
        print(f"   最小任务数: {min_tasks}\n")
    
    cycle_count = 0
    successful_cycles = 0
    total_fixes = 0
    
    while _evolution_enabled:
        try:
            cycle_count += 1
            print(f"\n{'='*60}")
            print(f"🧬 进化周期 #{cycle_count}")
            from datetime import datetime
            print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}")
            
            # 1. 审计代码
            print("\n[1/3] 📊 审计代码...")
            auditor = get_auditor()
            issues = auditor.audit_all()
            
            high_priority = [i for i in issues if i.severity == "high"]
            medium_priority = [i for i in issues if i.severity == "medium"]
            
            print(f"   发现 {len(issues)} 个问题")
            print(f"   高优先级: {len(high_priority)} 个")
            print(f"   中优先级: {len(medium_priority)} 个")
            
            # 2. 自动修复
            fixed_count = 0
            if high_priority or medium_priority:
                print(f"\n[2/3] 🔧 自动修复...")
                
                # 先修复高优先级
                if high_priority:
                    print(f"   修复高优先级问题...")
                    results = auto_fix_code(focus="all", max_fixes=min(len(high_priority), 10))
                    fixed_count += results.get('successful', 0)
                
                # 再修复中优先级
                if medium_priority and infinite_mode:
                    print(f"   修复中优先级问题...")
                    results = auto_fix_code(focus="all", max_fixes=min(len(medium_priority), 5))
                    fixed_count += results.get('successful', 0)
                
                if fixed_count > 0:
                    print(f"   ✅ 成功修复 {fixed_count} 个问题")
                    successful_cycles += 1
                    total_fixes += fixed_count
                else:
                    print(f"   ⚠️  未能修复问题")
            else:
                print(f"\n[2/3] ✅ 代码质量优秀，无需修复")
                successful_cycles += 1
            
            # 3. 显示统计
            print(f"\n[3/3] 📊 累计统计:")
            print(f"   总周期: {cycle_count}")
            print(f"   成功: {successful_cycles}")
            print(f"   成功率: {successful_cycles/cycle_count*100:.1f}%")
            print(f"   总修复: {total_fixes} 个问题")
            
            # 4. 决定下一步
            if infinite_mode:
                # 无限模式：立即开始下一轮
                print(f"\n⚡ 立即开始下一轮进化...")
                await asyncio.sleep(1)  # 短暂暂停，避免过于频繁
            else:
                # 普通模式：等待间隔
                print(f"\n⏰ 等待 {interval_hours} 小时后继续...")
                await asyncio.sleep(interval_hours * 3600)
                
        except asyncio.CancelledError:
            print(f"\n🛑 进化循环被取消")
            break
        except Exception as e:
            print(f"\n❌ 进化周期出错: {e}")
            import traceback
            traceback.print_exc()
            # 出错后短暂等待
            await asyncio.sleep(10)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global _evolution_scheduler, _evolution_enabled
    
    # 启动时
    config = load_config_from_file()
    if config:
        evolution_config = getattr(config.agent, 'auto_evolution', None)
        if evolution_config and getattr(evolution_config, 'enabled', False):
            _evolution_enabled = True
            _evolution_scheduler = asyncio.create_task(_auto_evolution_loop())
            print("✅ 自动进化调度器已启动")
    
    yield
    
    # 关闭时
    if _evolution_scheduler:
        _evolution_enabled = False
        _evolution_scheduler.cancel()
        try:
            await _evolution_scheduler
        except asyncio.CancelledError:
            pass
        print("🛑 自动进化调度器已停止")


app = FastAPI(title="SuperLinux Agent", lifespan=lifespan)


class SuperLinuxAgent:
    """SuperLinux Agent with streaming output, multi-AI collaboration, and task-oriented completion."""
    
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
        
        # 多 AI 协作
        self.consultation_count = 0
        self.max_retries = 3
        self.search_before_consult = 2
        
        # 对话保存
        self.conversation_id = None
        self.conversation_dir = "conversations"
        os.makedirs(self.conversation_dir, exist_ok=True)
    
    def save_conversation(self):
        """保存对话历史"""
        if not self.messages or len(self.messages) <= 1:  # 只有系统提示
            return
        
        try:
            from datetime import datetime
            
            if not self.conversation_id:
                self.conversation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            filepath = os.path.join(self.conversation_dir, f"conversation_{self.conversation_id}.json")
            
            # 转换消息为可序列化格式
            messages_data = []
            for msg in self.messages:
                msg_dict = {
                    "type": msg.__class__.__name__,
                    "content": msg.content if hasattr(msg, 'content') else ""
                }
                
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    msg_dict["tool_calls"] = [
                        {
                            "name": tc.get("name", ""),
                            "args": tc.get("args", {})
                        }
                        for tc in msg.tool_calls
                    ]
                
                messages_data.append(msg_dict)
            
            data = {
                "conversation_id": self.conversation_id,
                "timestamp": datetime.now().isoformat(),
                "message_count": len(messages_data),
                "messages": messages_data
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return filepath
        except Exception as e:
            print(f"保存对话失败: {e}")
            return None
    
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

**重要：禁止在回复中输出代码！所有代码必须用 write_file 工具写入文件！**

在最终回复末尾标注状态：
- `[STATUS: COMPLETED]` - 任务已完成
- `[STATUS: NEEDS_INPUT]` - 需要用户提供更多信息
- `[STATUS: FAILED: 原因]` - 任务失败

### 核心原则
1. **持续工作直到完成**: 不要中途停止
2. **遇到困难优先查官方文档**: 搜索 "[软件名] official documentation [问题]"
3. **写代码时**: 先创建目录，再用 write_file 工具写入每个文件，不要在回复中输出代码内容
4. **回复要简短**: 每次回复不超过 50 字，说明要做什么，然后立即调用工具
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
    
    async def consult_secondary_ai(self, problem: str, context: str) -> str:
        """咨询顾问 AI 获取建议。
        
        Args:
            problem: 遇到的问题描述
            context: 相关上下文信息
            
        Returns:
            顾问 AI 的建议
        """
        if not self.secondary_engines:
            return None
        
        self.consultation_count += 1
        
        # 选择第一个顾问 AI（可以扩展为智能选择）
        consultant_name = list(self.secondary_engines.keys())[0]
        consultant = self.secondary_engines[consultant_name]
        
        await self.send_event("status", {
            "message": f"🤝 咨询 {consultant_name}..."
        })
        
        consultation_prompt = f"""你是一个专业顾问，帮助解决技术问题。

**问题**: {problem}

**上下文**: {context}

请提供简洁的解决建议（不超过200字）。"""
        
        try:
            response = await consultant["engine"].llm.ainvoke([
                HumanMessage(content=consultation_prompt)
            ])
            
            advice = response.content
            await self.send_event("status", {
                "message": f"💡 {consultant_name}: {advice[:100]}..."
            })
            
            return advice
        except Exception as e:
            await self.send_event("status", {
                "message": f"⚠️ 咨询失败: {str(e)}"
            })
            return None
    
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
        
        while True:  # 不限制迭代次数
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
                    # 不限制 chunk 数量，让 AI 自由生成
                    stream_start_time = asyncio.get_event_loop().time()
                    forced_stop = False
                    
                    async for chunk in self.primary_llm.astream(self.messages):
                        if self.should_stop:
                            break
                        
                        chunk_count += 1
                        
                        # 每 100 chunks 显示进度
                        if chunk_count % 100 == 0:
                            elapsed = int(asyncio.get_event_loop().time() - stream_start_time)
                            await self.send_event("status", {"message": f"📦 {chunk_count} chunks ({elapsed}s)"})
                        
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
                        
                        # 保存对话
                        saved_path = self.save_conversation()
                        if saved_path:
                            await self.send_event("status", {"message": f"💬 对话已保存"})
                        
                        await self.send_event("response", {"content": clean_content})
                        return
                    elif needs_input:
                        # 保存对话
                        self.save_conversation()
                        await self.send_event("response", {"content": clean_content})
                        return
                    else:
                        # 没有明确状态，检查是否卡住
                        consecutive_no_progress += 1
                        if consecutive_no_progress >= 3:  # 增加到3次，给AI更多机会
                            # 保存对话
                            self.save_conversation()
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
                        
                        # 重复错误处理：先查文档，再咨询顾问
                        if error_tracker[error_key] >= self.max_retries:
                            # 检查是否应该咨询顾问 AI
                            should_consult = (
                                self.secondary_engines and 
                                len(all_steps) >= self.search_before_consult and
                                self.consultation_count < 2  # 最多咨询2次
                            )
                            
                            if should_consult:
                                # 咨询顾问 AI
                                context = f"工具: {tool_name}\n参数: {tool_args}\n错误: {error_msg}\n已尝试: {error_tracker[error_key]} 次"
                                advice = await self.consult_secondary_ai(
                                    problem=f"{tool_name} 执行失败",
                                    context=context
                                )
                                
                                if advice:
                                    consultation_msg = f"""
顾问 AI 的建议:
{advice}

请根据建议尝试解决问题。
"""
                                    self.messages.append(ToolMessage(content=result, tool_call_id=tool_id))
                                    self.messages.append(HumanMessage(content=consultation_msg))
                                    error_tracker[error_key] = 0  # 重置计数
                                    continue
                            
                            # 没有顾问或咨询失败，提示查文档
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
    agent = SuperLinuxAgent(websocket)
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


@app.get("/api/experience_stats")
async def get_experience_stats():
    """获取经验统计"""
    try:
        from .experience_rag import get_experience_rag
        rag = get_experience_rag()
        
        # 只在第一次调用时初始化
        if not rag._initialized:
            rag.initialize()
        
        stats = rag.get_stats()
        
        total = stats.get('total_experiences', 0)
        successful = stats.get('successful', 0)
        
        return {
            "total": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": f"{(successful/total*100):.1f}%" if total > 0 else "0%"
        }
    except:
        return {"total": 0, "successful": 0, "failed": 0, "success_rate": "0%"}


@app.get("/api/performance_metrics")
async def get_performance_metrics():
    """获取性能指标"""
    try:
        from .self_diagnosis import get_evaluator
        evaluator = get_evaluator()
        
        if not evaluator.evaluation_history:
            return {"overall": "-", "efficiency": "-", "success": "-"}
        
        recent = evaluator.evaluation_history[-10:]
        overall = sum(e.overall_score for e in recent) / len(recent)
        efficiency = sum(e.efficiency_score for e in recent) / len(recent)
        success = sum(e.success_score for e in recent) / len(recent)
        
        return {
            "overall": f"{overall:.0f}",
            "efficiency": f"{efficiency:.0f}",
            "success": f"{success:.0f}"
        }
    except:
        return {"overall": "-", "efficiency": "-", "success": "-"}


@app.get("/api/evolution_stats")
async def get_evolution_stats():
    """获取进化统计"""
    try:
        from .self_evolution import get_evolution_engine
        from .experience_rag import get_experience_rag
        from datetime import datetime
        
        engine = get_evolution_engine()
        stats = engine.get_evolution_stats()
        
        # 获取最近的活动
        recent_activities = []
        
        # 从进化历史中获取
        if engine.cycles:
            for cycle in engine.cycles[-5:]:
                time_str = datetime.fromisoformat(cycle.start_time).strftime('%H:%M')
                if cycle.success:
                    recent_activities.append({
                        "type": "improved",
                        "time": time_str,
                        "message": f"✅ 进化成功，提升 {cycle.effectiveness*100:.1f}%"
                    })
                else:
                    recent_activities.append({
                        "type": "evolving",
                        "time": time_str,
                        "message": f"🔄 进化尝试，已回滚"
                    })
        
        # 添加学习活动（不重新初始化）
        rag = get_experience_rag()
        if rag._initialized:
            exp_stats = rag.get_stats()
            
            if exp_stats.get('total_experiences', 0) > 0:
                recent_activities.insert(0, {
                    "type": "learning",
                    "time": datetime.now().strftime('%H:%M'),
                    "message": f"📚 已学习 {exp_stats['total_experiences']} 个经验"
                })
        
        return {
            "total_cycles": stats.get('total_cycles', 0),
            "successful": stats.get('successful_cycles', 0),
            "avg_improvement": f"{stats.get('avg_effectiveness', 0)*100:.1f}%",
            "recent_improvement": f"{stats.get('avg_effectiveness', 0)*100:.0f}%" if stats.get('successful_cycles', 0) > 0 else "-",
            "recent_activities": recent_activities[-5:]
        }
    except Exception as e:
        print(f"获取进化统计失败: {e}")
        return {
            "total_cycles": 0,
            "successful": 0,
            "avg_improvement": "0%",
            "recent_improvement": "-",
            "recent_activities": []
        }


@app.get("/api/evolution_log")
async def get_evolution_log():
    """获取完整的进化日志"""
    try:
        from .self_evolution import get_evolution_engine
        from datetime import datetime
        
        engine = get_evolution_engine()
        
        logs = []
        for cycle in engine.cycles:
            logs.append({
                "id": cycle.cycle_id,
                "time": cycle.start_time,
                "success": cycle.success,
                "effectiveness": cycle.effectiveness,
                "improvements": cycle.improvements_applied,
                "before_metrics": cycle.before_metrics,
                "after_metrics": cycle.after_metrics,
                "rolled_back": cycle.rolled_back,
                "rollback_reason": cycle.rollback_reason
            })
        
        return {"logs": logs}
    except Exception as e:
        return {"logs": [], "error": str(e)}


@app.get("/api/experiences")
async def get_experiences():
    """获取所有经验"""
    try:
        from .experience_rag import get_experience_rag
        import os
        import json
        
        rag = get_experience_rag()
        json_path = os.path.join(rag.db_path, "experiences.json")
        
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                experiences = json.load(f)
            return {"experiences": experiences[-50:]}  # 最近50个
        
        return {"experiences": []}
    except Exception as e:
        return {"experiences": [], "error": str(e)}


@app.get("/api/conversations")
async def get_conversations():
    """获取所有保存的对话"""
    try:
        import os
        import json
        from datetime import datetime
        
        conv_dir = "conversations"
        if not os.path.exists(conv_dir):
            return {"conversations": []}
        
        conversations = []
        for filename in os.listdir(conv_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(conv_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # 提取第一条用户消息作为标题
                    title = "未命名对话"
                    for msg in data.get('messages', []):
                        if msg.get('type') == 'HumanMessage':
                            title = msg.get('content', '')[:50]
                            break
                    
                    conversations.append({
                        "id": data.get('conversation_id'),
                        "title": title,
                        "timestamp": data.get('timestamp'),
                        "message_count": data.get('message_count', 0),
                        "filename": filename
                    })
                except:
                    continue
        
        # 按时间倒序
        conversations.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return {"conversations": conversations}
    except Exception as e:
        return {"conversations": [], "error": str(e)}


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """获取特定对话的详细内容"""
    try:
        import os
        import json
        
        filepath = os.path.join("conversations", f"conversation_{conversation_id}.json")
        
        if not os.path.exists(filepath):
            return {"error": "对话不存在"}
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data
    except Exception as e:
        return {"error": str(e)}


@app.get("/evolution")
async def get_evolution_page():
    """进化日志页面"""
    return HTMLResponse(EVOLUTION_PAGE_HTML)


@app.get("/conversations")
async def get_conversations_page():
    """历史对话页面"""
    return HTMLResponse(CONVERSATIONS_PAGE_HTML)


HTML_CONTENT = '''
<!DOCTYPE html>
<html lang="zh" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SuperLinux Agent</title>
    <style>
        :root[data-theme="dark"] {
            --bg-primary: #0d0d0d;
            --bg-secondary: #1a1a1a;
            --bg-tertiary: #0a0a0a;
            --border-color: #2a2a2a;
            --text-primary: #e8e8e8;
            --text-secondary: #999;
            --accent: #00d9ff;
            --user-msg: #2a2a2a;
            --ai-msg: #1a1a1a;
            --code-bg: #1e1e1e;
            --hover-bg: #2a2a2a;
        }
        :root[data-theme="light"] {
            --bg-primary: #f5f5f5;
            --bg-secondary: #ffffff;
            --bg-tertiary: #fafafa;
            --border-color: #e0e0e0;
            --text-primary: #333;
            --text-secondary: #666;
            --accent: #0066cc;
            --user-msg: #e3f2fd;
            --ai-msg: #f5f5f5;
            --code-bg: #f0f0f0;
            --hover-bg: #e8e8e8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            height: 100vh;
            display: flex;
            flex-direction: column;
            transition: background 0.3s, color 0.3s;
        }
        .header {
            background: var(--bg-secondary);
            padding: 12px 20px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .header h1 { 
            font-size: 1.2em; 
            color: var(--accent); 
            display: flex; 
            align-items: center; 
            gap: 10px; 
        }
        .header-btns { display: flex; gap: 10px; align-items: center; }
        .header-btns button, .theme-toggle {
            padding: 6px 12px;
            border: 1px solid var(--border-color);
            border-radius: 5px;
            background: transparent;
            color: var(--text-secondary);
            cursor: pointer;
            font-size: 0.85em;
            transition: all 0.2s;
        }
        .header-btns button:hover, .theme-toggle:hover { 
            background: var(--hover-bg); 
            color: var(--text-primary); 
        }
        .theme-toggle { font-size: 1.2em; padding: 6px 10px; }
        .main { flex: 1; display: flex; overflow: hidden; }
        .chat-panel { flex: 1; display: flex; flex-direction: column; }
        .log-panel {
            width: 400px;
            display: flex;
            flex-direction: column;
            background: var(--bg-tertiary);
            border-left: 1px solid var(--border-color);
        }
        .evolution-panel {
            width: 300px;
            display: flex;
            flex-direction: column;
            background: var(--bg-tertiary);
            border-left: 1px solid var(--border-color);
        }
        .evolution-stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            padding: 10px;
        }
        .stat-card {
            background: var(--bg-secondary);
            padding: 12px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
        }
        .stat-label {
            font-size: 0.75em;
            color: var(--text-secondary);
            margin-bottom: 5px;
        }
        .stat-value {
            font-size: 1.5em;
            font-weight: 700;
            color: var(--accent);
            margin-bottom: 3px;
        }
        .stat-sub {
            font-size: 0.7em;
            color: var(--text-secondary);
        }
        .evolution-log {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
            font-size: 0.75em;
        }
        .log-title {
            font-weight: 600;
            color: var(--text-secondary);
            margin-bottom: 8px;
            padding-bottom: 5px;
            border-bottom: 1px solid var(--border-color);
        }
        .evo-entry {
            padding: 8px;
            margin-bottom: 6px;
            background: var(--bg-secondary);
            border-radius: 5px;
            border-left: 3px solid var(--accent);
            animation: slideIn 0.3s ease-out;
        }
        .evo-entry.learning { border-left-color: #00ff88; }
        .evo-entry.evolving { border-left-color: #ffd700; }
        .evo-entry.improved { border-left-color: #00d9ff; }
        .evo-time {
            font-size: 0.7em;
            color: var(--text-secondary);
            margin-bottom: 3px;
        }
        .evo-content {
            color: var(--text-primary);
            line-height: 1.4;
        }
        .panel-header {
            padding: 10px 15px;
            background: var(--bg-secondary);
            font-weight: 600;
            font-size: 0.85em;
            color: var(--text-secondary);
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
            animation: fadeIn 0.3s ease-in;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .message.user { background: var(--user-msg); margin-left: auto; }
        .message.assistant { background: var(--ai-msg); border: 1px solid var(--border-color); }
        .message.system { 
            background: var(--code-bg); 
            color: var(--text-secondary); 
            font-size: 0.9em; 
            text-align: center; 
            max-width: 100%; 
        }
        /* 代码块样式优化 */
        .message.assistant pre {
            position: relative;
            background: var(--code-bg);
            padding: 12px;
            border-radius: 6px;
            overflow-x: auto;
            margin: 10px 0;
        }
        .message.assistant pre code {
            background: none;
            padding: 0;
            font-family: 'Monaco', 'Consolas', 'Courier New', monospace;
            font-size: 0.9em;
            line-height: 1.5;
        }
        .message.assistant code {
            background: var(--code-bg);
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.9em;
        }
        /* 复制按钮 */
        .copy-btn {
            position: absolute;
            top: 8px;
            right: 8px;
            padding: 4px 8px;
            background: var(--accent);
            color: #fff;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.75em;
            opacity: 0;
            transition: opacity 0.2s;
        }
        .message.assistant pre:hover .copy-btn { opacity: 1; }
        .copy-btn:hover { opacity: 0.8 !important; }
        .copy-btn.copied { background: #10b981; }
        .message.assistant h1, .message.assistant h2, .message.assistant h3 {
            margin: 12px 0 8px 0;
            color: var(--accent);
        }
        .message.assistant h1 { font-size: 1.4em; }
        .message.assistant h2 { font-size: 1.2em; }
        .message.assistant h3 { font-size: 1.1em; }
        .message.assistant ul, .message.assistant ol { margin: 8px 0; padding-left: 20px; }
        .message.assistant li { margin: 4px 0; }
        .message.assistant strong { color: var(--text-primary); font-weight: 600; }
        .message.assistant a { color: var(--accent); text-decoration: none; }
        .message.assistant a:hover { text-decoration: underline; }
        .input-area {
            padding: 12px 15px;
            background: var(--bg-secondary);
            border-top: 1px solid var(--border-color);
            display: flex;
            gap: 10px;
        }
        input[type="text"] {
            flex: 1;
            padding: 10px 14px;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            background: var(--bg-primary);
            color: var(--text-primary);
            font-size: 0.95em;
            transition: border-color 0.2s;
        }
        input[type="text"]:focus { 
            outline: none;
            border-color: var(--accent);
        }
        .input-area button {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-send { background: var(--accent); color: #fff; }
        .btn-send:hover { opacity: 0.9; transform: translateY(-1px); }
        .btn-stop { background: #ff4757; color: #fff; }
        .btn-stop:hover { opacity: 0.9; }
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
            background: var(--bg-primary);
            animation: slideIn 0.2s ease-out;
        }
        @keyframes slideIn {
            from { opacity: 0; transform: translateX(-10px); }
            to { opacity: 1; transform: translateX(0); }
        }
        .log-entry.tool { border-left: 3px solid #ffd700; }
        .log-entry.result { border-left: 3px solid #00ff88; }
        .log-entry.error { border-left: 3px solid #ff4444; }
        .log-entry.status { border-left: 3px solid var(--accent); color: var(--text-secondary); }
        .log-entry.stream { border-left: 3px solid #aa88ff; }
        .log-entry.stream .log-content {
            max-height: 400px;
            font-size: 0.8em;
            line-height: 1.4;
        }
        .log-label { font-weight: 600; margin-bottom: 3px; }
        .log-content {
            color: var(--text-secondary);
            white-space: pre-wrap;
            word-break: break-all;
            max-height: 200px;
            overflow-y: auto;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #555;
            transition: background 0.3s;
        }
        .status-dot.connected { background: #00ff88; }
        .status-dot.working { background: #ffd700; animation: pulse 1s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        .stream-content { color: var(--accent); font-family: monospace; }
        /* 模态框样式 */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }
        .modal.active { display: flex; }
        .modal-content {
            background: var(--bg-secondary);
            padding: 25px;
            border-radius: 12px;
            max-width: 600px;
            width: 90%;
            max-height: 70vh;
            overflow-y: auto;
            border: 1px solid var(--border-color);
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid var(--border-color);
        }
        .modal-header h2 {
            color: var(--accent);
            font-size: 1.3em;
        }
        .modal-close {
            background: #ff4444;
            border: none;
            color: white;
            padding: 6px 14px;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
        }
        .modal-close:hover { opacity: 0.8; }
        .conversation-item {
            background: var(--bg-primary);
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
            cursor: pointer;
            transition: all 0.2s;
        }
        .conversation-item:hover {
            background: var(--hover-bg);
            border-color: var(--accent);
            transform: translateX(5px);
        }
        .conversation-item-title {
            font-weight: bold;
            color: var(--accent);
            margin-bottom: 5px;
        }
        .conversation-item-meta {
            font-size: 0.85em;
            color: var(--text-secondary);
        }
        .empty-conversations {
            text-align: center;
            padding: 40px 20px;
            color: var(--text-secondary);
        }
        /* 移动端适配 */
        @media (max-width: 768px) {
            .main { flex-direction: column; }
            .log-panel {
                width: 100%;
                height: 40%;
                border-left: none;
                border-top: 1px solid var(--border-color);
            }
            .header h1 { font-size: 1em; }
            .header-btns button { padding: 4px 8px; font-size: 0.8em; }
            .message { max-width: 95%; }
        }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script>
        if (typeof marked !== 'undefined') {
            marked.setOptions({ breaks: true, gfm: true });
        }
    </script>
</head>
<body>
    <div class="header">
        <h1><span class="status-dot" id="status"></span> SuperLinux Agent</h1>
        <div class="header-btns">
            <a href="/evolution" style="padding: 8px 16px; background: linear-gradient(45deg, #00d4ff, #7b2ff7); border-radius: 8px; text-decoration: none; color: white; font-weight: bold; margin-right: 10px;">🧬 进化日志</a>
            <a href="/conversations" style="padding: 8px 16px; background: linear-gradient(45deg, #ff6b6b, #feca57); border-radius: 8px; text-decoration: none; color: white; font-weight: bold; margin-right: 10px;">💬 历史对话</a>
            <button onclick="showLoadConversationModal()" style="background: linear-gradient(45deg, #48c774, #00d1b2); color: white; font-weight: bold;">📂 恢复对话</button>
            <button class="theme-toggle" onclick="toggleTheme()" title="切换主题">🌓</button>
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
        <div class="evolution-panel">
            <div class="panel-header">
                <span>🧬 学习 & 进化状态</span>
                <button onclick="refreshEvolution()" style="background:none;border:none;color:var(--accent);cursor:pointer;">🔄</button>
            </div>
            <div class="evolution-stats" id="evolutionStats">
                <div class="stat-card">
                    <div class="stat-label">📚 经验库</div>
                    <div class="stat-value" id="expCount">-</div>
                    <div class="stat-sub">成功率: <span id="expSuccess">-</span></div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">📊 当前性能</div>
                    <div class="stat-value" id="perfScore">-</div>
                    <div class="stat-sub">效率: <span id="perfEff">-</span></div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">🧬 进化周期</div>
                    <div class="stat-value" id="evoCycles">-</div>
                    <div class="stat-sub">成功: <span id="evoSuccess">-</span></div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">💪 总提升</div>
                    <div class="stat-value" id="evoImprovement">-</div>
                    <div class="stat-sub">最近: <span id="evoRecent">-</span></div>
                </div>
            </div>
            <div class="evolution-log" id="evolutionLog">
                <div class="log-title">最近活动</div>
            </div>
        </div>
    </div>
    
    <!-- 恢复对话模态框 -->
    <div id="loadConversationModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>📂 恢复历史对话</h2>
                <button class="modal-close" onclick="closeLoadConversationModal()">关闭</button>
            </div>
            <div id="conversationList"></div>
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
                        // 为代码块添加复制按钮
                        div.querySelectorAll('pre').forEach(pre => {
                            const btn = document.createElement('button');
                            btn.className = 'copy-btn';
                            btn.textContent = '复制';
                            btn.onclick = () => copyCode(btn, pre);
                            pre.style.position = 'relative';
                            pre.appendChild(btn);
                        });
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
        
        // 复制代码功能
        function copyCode(btn, pre) {
            const code = pre.querySelector('code');
            const text = code ? code.textContent : pre.textContent;
            navigator.clipboard.writeText(text).then(() => {
                btn.textContent = '已复制!';
                btn.classList.add('copied');
                setTimeout(() => {
                    btn.textContent = '复制';
                    btn.classList.remove('copied');
                }, 2000);
            });
        }
        
        // 主题切换
        function toggleTheme() {
            const html = document.documentElement;
            const currentTheme = html.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            html.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        }
        
        // 加载保存的主题
        const savedTheme = localStorage.getItem('theme') || 'dark';
        document.documentElement.setAttribute('data-theme', savedTheme);
        
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
        
        // 自动刷新进化状态
        setInterval(refreshEvolution, 5000);
        refreshEvolution();
        
        async function refreshEvolution() {
            try {
                // 获取经验统计
                const expResp = await fetch('/api/experience_stats');
                const expData = await expResp.json();
                
                document.getElementById('expCount').textContent = expData.total || '0';
                document.getElementById('expSuccess').textContent = expData.success_rate || '0%';
                
                // 获取性能指标
                const perfResp = await fetch('/api/performance_metrics');
                const perfData = await perfResp.json();
                
                document.getElementById('perfScore').textContent = perfData.overall || '-';
                document.getElementById('perfEff').textContent = perfData.efficiency || '-';
                
                // 获取进化统计
                const evoResp = await fetch('/api/evolution_stats');
                const evoData = await evoResp.json();
                
                document.getElementById('evoCycles').textContent = evoData.total_cycles || '0';
                document.getElementById('evoSuccess').textContent = evoData.successful || '0';
                document.getElementById('evoImprovement').textContent = evoData.avg_improvement || '0%';
                document.getElementById('evoRecent').textContent = evoData.recent_improvement || '-';
                
                // 更新活动日志
                if (evoData.recent_activities) {
                    updateEvolutionLog(evoData.recent_activities);
                }
            } catch(e) {
                console.log('刷新进化状态失败:', e);
            }
        }
        
        function updateEvolutionLog(activities) {
            const logDiv = document.getElementById('evolutionLog');
            const existingTitle = logDiv.querySelector('.log-title');
            logDiv.innerHTML = '';
            if (existingTitle) logDiv.appendChild(existingTitle);
            
            activities.forEach(activity => {
                const entry = document.createElement('div');
                entry.className = `evo-entry ${activity.type}`;
                entry.innerHTML = `
                    <div class="evo-time">${activity.time}</div>
                    <div class="evo-content">${activity.message}</div>
                `;
                logDiv.appendChild(entry);
            });
        }
        
        // 恢复对话功能
        async function showLoadConversationModal() {
            const modal = document.getElementById('loadConversationModal');
            const listDiv = document.getElementById('conversationList');
            
            listDiv.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-secondary);">加载中...</div>';
            modal.classList.add('active');
            
            try {
                const res = await fetch('/api/conversations');
                const data = await res.json();
                
                if (!data.conversations || data.conversations.length === 0) {
                    listDiv.innerHTML = '<div class="empty-conversations"><div style="font-size:3em;margin-bottom:10px;">💬</div><p>还没有保存的对话</p></div>';
                    return;
                }
                
                listDiv.innerHTML = data.conversations.map(conv => `
                    <div class="conversation-item" onclick="loadConversation('${conv.id}')">
                        <div class="conversation-item-title">${escapeHtml(conv.title)}</div>
                        <div class="conversation-item-meta">
                            ${new Date(conv.timestamp).toLocaleString('zh-CN')} · ${conv.message_count} 条消息
                        </div>
                    </div>
                `).join('');
            } catch (e) {
                console.error('加载对话列表失败:', e);
                listDiv.innerHTML = '<div class="empty-conversations"><div style="font-size:3em;margin-bottom:10px;">❌</div><p>加载失败: ' + e.message + '</p></div>';
            }
        }
        
        function closeLoadConversationModal() {
            document.getElementById('loadConversationModal').classList.remove('active');
        }
        
        async function loadConversation(id) {
            try {
                const res = await fetch(`/api/conversations/${id}`);
                const data = await res.json();
                
                if (data.error) {
                    alert('加载对话失败: ' + data.error);
                    return;
                }
                
                // 清空当前对话
                messages.innerHTML = '';
                
                // 加载历史消息，包括系统消息
                let loadedCount = 0;
                data.messages.forEach(msg => {
                    if (msg.type === 'HumanMessage') {
                        addMessage('user', msg.content);
                        loadedCount++;
                    } else if (msg.type === 'AIMessage') {
                        addMessage('assistant', msg.content);
                        loadedCount++;
                    } else if (msg.type === 'SystemMessage') {
                        addMessage('system', msg.content);
                        loadedCount++;
                    }
                    // 跳过 ToolMessage，不显示在聊天框中
                });
                
                closeLoadConversationModal();
                addLog('status', '对话已恢复', `已加载 ${loadedCount} 条消息`);
            } catch (e) {
                console.error('加载对话失败:', e);
                alert('加载对话失败: ' + e.message);
            }
        }
        
        // 点击模态框外部关闭
        document.getElementById('loadConversationModal').addEventListener('click', function(e) {
            if (e.target === this) {
                closeLoadConversationModal();
            }
        });
    </script>
</body>
</html>
'''

EVOLUTION_PAGE_HTML = '''
<!DOCTYPE html>
<html lang="zh" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🧬 AI 进化日志 - SuperLinux Agent</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            padding: 20px;
            min-height: 100vh;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #00d4ff, #7b2ff7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: rgba(255,255,255,0.05);
            padding: 20px;
            border-radius: 10px;
            border: 1px solid rgba(255,255,255,0.1);
            text-align: center;
        }
        
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            margin: 10px 0;
            color: #00d4ff;
        }
        
        .stat-label {
            color: #888;
            font-size: 0.9em;
        }
        
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            border-bottom: 2px solid rgba(255,255,255,0.1);
        }
        
        .tab {
            padding: 15px 30px;
            background: transparent;
            border: none;
            color: #888;
            cursor: pointer;
            font-size: 1em;
            transition: all 0.3s;
            border-bottom: 3px solid transparent;
        }
        
        .tab.active {
            color: #00d4ff;
            border-bottom-color: #00d4ff;
        }
        
        .tab:hover {
            color: #00d4ff;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .log-entry {
            background: rgba(255,255,255,0.05);
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 10px;
            border-left: 4px solid #00d4ff;
        }
        
        .log-entry.success {
            border-left-color: #00ff88;
        }
        
        .log-entry.failed {
            border-left-color: #ff4444;
        }
        
        .log-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .log-time {
            color: #888;
            font-size: 0.9em;
        }
        
        .log-badge {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
        }
        
        .badge-success {
            background: rgba(0,255,136,0.2);
            color: #00ff88;
        }
        
        .badge-failed {
            background: rgba(255,68,68,0.2);
            color: #ff4444;
        }
        
        .log-details {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-top: 15px;
        }
        
        .metric {
            background: rgba(0,0,0,0.3);
            padding: 10px;
            border-radius: 5px;
        }
        
        .metric-label {
            color: #888;
            font-size: 0.85em;
            margin-bottom: 5px;
        }
        
        .metric-value {
            font-size: 1.2em;
            font-weight: bold;
        }
        
        .improvement-list {
            margin-top: 15px;
            padding: 15px;
            background: rgba(0,0,0,0.3);
            border-radius: 5px;
        }
        
        .improvement-item {
            padding: 10px;
            margin: 5px 0;
            background: rgba(255,255,255,0.05);
            border-radius: 5px;
        }
        
        .experience-card {
            background: rgba(255,255,255,0.05);
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 8px;
            border-left: 3px solid #7b2ff7;
        }
        
        .experience-card.success {
            border-left-color: #00ff88;
        }
        
        .experience-card.failed {
            border-left-color: #ff4444;
        }
        
        .experience-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
        }
        
        .experience-problem {
            font-weight: bold;
            margin-bottom: 10px;
        }
        
        .experience-tools {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin-top: 10px;
        }
        
        .tool-tag {
            padding: 3px 10px;
            background: rgba(0,212,255,0.2);
            border-radius: 15px;
            font-size: 0.8em;
            color: #00d4ff;
        }
        
        .back-link {
            display: inline-block;
            margin-bottom: 20px;
            padding: 10px 20px;
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
            color: #00d4ff;
            text-decoration: none;
            transition: all 0.3s;
        }
        
        .back-link:hover {
            background: rgba(0,212,255,0.2);
        }
        
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #888;
        }
        
        .empty-state-icon {
            font-size: 4em;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <a href="/" class="back-link">← 返回主界面</a>
    
    <div class="header">
        <h1>🧬 AI 进化日志</h1>
        <p>实时查看 AI 的学习和进化过程</p>
    </div>
    
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-label">总进化周期</div>
            <div class="stat-value" id="total-cycles">0</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">成功改进</div>
            <div class="stat-value" id="successful-cycles">0</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">平均提升</div>
            <div class="stat-value" id="avg-improvement">0%</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">学习经验数</div>
            <div class="stat-value" id="total-experiences">0</div>
        </div>
    </div>
    
    <div class="tabs">
        <button class="tab active" onclick="switchTab('evolution')">🧬 进化历史</button>
        <button class="tab" onclick="switchTab('experiences')">📚 学习经验</button>
    </div>
    
    <div id="evolution-tab" class="tab-content active">
        <div id="evolution-logs"></div>
    </div>
    
    <div id="experiences-tab" class="tab-content">
        <div id="experiences-list"></div>
    </div>
    
    <script>
        function switchTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            event.target.classList.add('active');
            document.getElementById(tab + '-tab').classList.add('active');
        }
        
        async function loadStats() {
            try {
                const [evolutionRes, experienceRes] = await Promise.all([
                    fetch('/api/evolution_stats'),
                    fetch('/api/experience_stats')
                ]);
                
                const evolution = await evolutionRes.json();
                const experience = await experienceRes.json();
                
                document.getElementById('total-cycles').textContent = evolution.total_cycles;
                document.getElementById('successful-cycles').textContent = evolution.successful;
                document.getElementById('avg-improvement').textContent = evolution.avg_improvement;
                document.getElementById('total-experiences').textContent = experience.total;
            } catch (e) {
                console.error('加载统计失败:', e);
            }
        }
        
        async function loadEvolutionLogs() {
            try {
                const res = await fetch('/api/evolution_log');
                const data = await res.json();
                
                const container = document.getElementById('evolution-logs');
                
                if (!data.logs || data.logs.length === 0) {
                    container.innerHTML = `
                        <div class="empty-state">
                            <div class="empty-state-icon">🌱</div>
                            <h3>还没有进化记录</h3>
                            <p>AI 正在积累经验，很快就会开始进化...</p>
                        </div>
                    `;
                    return;
                }
                
                container.innerHTML = data.logs.reverse().map(log => {
                    const time = new Date(log.time).toLocaleString('zh-CN');
                    const statusClass = log.success ? 'success' : 'failed';
                    const statusBadge = log.success ? 'badge-success' : 'badge-failed';
                    const statusText = log.success ? '✅ 成功' : '❌ 失败';
                    const effectiveness = (log.effectiveness * 100).toFixed(1);
                    
                    let improvementsHtml = '';
                    if (log.improvements && log.improvements.length > 0) {
                        improvementsHtml = `
                            <div class="improvement-list">
                                <strong>应用的改进:</strong>
                                ${log.improvements.map(imp => `
                                    <div class="improvement-item">
                                        <div><strong>${imp.type}</strong> - ${imp.priority}</div>
                                        <div style="color: #888; font-size: 0.9em; margin-top: 5px;">
                                            ${imp.issue}
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        `;
                    }
                    
                    let rollbackHtml = '';
                    if (log.rolled_back) {
                        rollbackHtml = `
                            <div style="margin-top: 10px; padding: 10px; background: rgba(255,68,68,0.1); border-radius: 5px; color: #ff4444;">
                                ↩️ 已回滚: ${log.rollback_reason || '改进效果不佳'}
                            </div>
                        `;
                    }
                    
                    return `
                        <div class="log-entry ${statusClass}">
                            <div class="log-header">
                                <div>
                                    <strong>${log.id}</strong>
                                    <div class="log-time">${time}</div>
                                </div>
                                <span class="log-badge ${statusBadge}">${statusText}</span>
                            </div>
                            
                            <div class="log-details">
                                <div class="metric">
                                    <div class="metric-label">改进效果</div>
                                    <div class="metric-value" style="color: ${log.success ? '#00ff88' : '#ff4444'}">
                                        ${effectiveness}%
                                    </div>
                                </div>
                                <div class="metric">
                                    <div class="metric-label">成功率变化</div>
                                    <div class="metric-value">
                                        ${(log.before_metrics?.success_rate * 100 || 0).toFixed(0)}% 
                                        → 
                                        ${(log.after_metrics?.success_rate * 100 || 0).toFixed(0)}%
                                    </div>
                                </div>
                            </div>
                            
                            ${improvementsHtml}
                            ${rollbackHtml}
                        </div>
                    `;
                }).join('');
            } catch (e) {
                console.error('加载进化日志失败:', e);
            }
        }
        
        async function loadExperiences() {
            try {
                const res = await fetch('/api/experiences');
                const data = await res.json();
                
                const container = document.getElementById('experiences-list');
                
                if (!data.experiences || data.experiences.length === 0) {
                    container.innerHTML = `
                        <div class="empty-state">
                            <div class="empty-state-icon">📚</div>
                            <h3>还没有学习经验</h3>
                            <p>开始与 AI 对话，它会自动记录和学习...</p>
                        </div>
                    `;
                    return;
                }
                
                container.innerHTML = data.experiences.reverse().map(exp => {
                    const statusClass = exp.success ? 'success' : 'failed';
                    const statusIcon = exp.success ? '✅' : '❌';
                    const time = new Date(exp.timestamp).toLocaleString('zh-CN');
                    
                    const toolsHtml = exp.tools_used && exp.tools_used.length > 0 ? `
                        <div class="experience-tools">
                            ${exp.tools_used.map(tool => `
                                <span class="tool-tag">${tool}</span>
                            `).join('')}
                        </div>
                    ` : '';
                    
                    return `
                        <div class="experience-card ${statusClass}">
                            <div class="experience-header">
                                <span>${statusIcon} ${exp.success ? '成功' : '失败'}</span>
                                <span style="color: #888; font-size: 0.9em;">${time}</span>
                            </div>
                            <div class="experience-problem">${exp.problem}</div>
                            ${exp.solution ? `<div style="color: #888; font-size: 0.9em;">${exp.solution.substring(0, 200)}...</div>` : ''}
                            ${toolsHtml}
                        </div>
                    `;
                }).join('');
            } catch (e) {
                console.error('加载经验失败:', e);
            }
        }
        
        // 初始加载
        loadStats();
        loadEvolutionLogs();
        loadExperiences();
        
        // 每10秒刷新一次
        setInterval(() => {
            loadStats();
            loadEvolutionLogs();
            loadExperiences();
        }, 10000);
    </script>
</body>
</html>
'''

CONVERSATIONS_PAGE_HTML = '''
<!DOCTYPE html>
<html lang="zh" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>💬 历史对话 - SuperLinux Agent</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            padding: 20px;
            min-height: 100vh;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #ff6b6b, #feca57);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .back-link {
            display: inline-block;
            margin-bottom: 20px;
            padding: 10px 20px;
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
            color: #00d4ff;
            text-decoration: none;
        }
        
        .conversation-list {
            display: grid;
            gap: 15px;
        }
        
        .conversation-card {
            background: rgba(255,255,255,0.05);
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #ff6b6b;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .conversation-card:hover {
            background: rgba(255,255,255,0.1);
            transform: translateX(5px);
        }
        
        .conversation-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
        }
        
        .conversation-title {
            font-weight: bold;
            font-size: 1.1em;
            color: #feca57;
        }
        
        .conversation-time {
            color: #888;
            font-size: 0.9em;
        }
        
        .conversation-meta {
            color: #888;
            font-size: 0.9em;
        }
        
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #888;
        }
        
        .empty-state-icon {
            font-size: 4em;
            margin-bottom: 20px;
        }
        
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            overflow-y: auto;
        }
        
        .modal.active {
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .modal-content {
            background: #1a1a2e;
            padding: 30px;
            border-radius: 15px;
            max-width: 800px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
        }
        
        .modal-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 20px;
        }
        
        .close-btn {
            background: #ff4444;
            border: none;
            color: white;
            padding: 8px 16px;
            border-radius: 5px;
            cursor: pointer;
        }
        
        .message {
            margin: 15px 0;
            padding: 15px;
            border-radius: 8px;
        }
        
        .message.human {
            background: rgba(0,212,255,0.1);
            border-left: 3px solid #00d4ff;
        }
        
        .message.ai {
            background: rgba(123,47,247,0.1);
            border-left: 3px solid #7b2ff7;
        }
        
        .message.system {
            background: rgba(255,255,255,0.05);
            border-left: 3px solid #888;
            font-size: 0.9em;
        }
        
        .message-type {
            font-weight: bold;
            margin-bottom: 8px;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <a href="/" class="back-link">← 返回主界面</a>
    
    <div class="header">
        <h1>💬 历史对话</h1>
        <p>查看所有保存的对话记录</p>
    </div>
    
    <div id="conversation-list" class="conversation-list"></div>
    
    <div id="modal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="modal-title">对话详情</h2>
                <button class="close-btn" onclick="closeModal()">关闭</button>
            </div>
            <div id="modal-body"></div>
        </div>
    </div>
    
    <script>
        async function loadConversations() {
            try {
                console.log('正在加载对话列表...');
                const res = await fetch('/api/conversations');
                const data = await res.json();
                
                console.log('加载到的对话:', data);
                
                const container = document.getElementById('conversation-list');
                
                if (!data.conversations || data.conversations.length === 0) {
                    container.innerHTML = `
                        <div class="empty-state">
                            <div class="empty-state-icon">💬</div>
                            <h3>还没有保存的对话</h3>
                            <p>开始与 AI 对话，对话会自动保存</p>
                        </div>
                    `;
                    return;
                }
                
                console.log('显示', data.conversations.length, '个对话');
                
                container.innerHTML = data.conversations.map(conv => {
                    const time = new Date(conv.timestamp).toLocaleString('zh-CN');
                    
                    return `
                        <div class="conversation-card" onclick="viewConversation('${conv.id}')">
                            <div class="conversation-header">
                                <div class="conversation-title">${conv.title}</div>
                                <div class="conversation-time">${time}</div>
                            </div>
                            <div class="conversation-meta">
                                ${conv.message_count} 条消息
                            </div>
                        </div>
                    `;
                }).join('');
            } catch (e) {
                console.error('加载对话失败:', e);
                document.getElementById('conversation-list').innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">❌</div>
                        <h3>加载失败</h3>
                        <p>${e.message}</p>
                    </div>
                `;
            }
        }
        
        async function viewConversation(id) {
            try {
                const res = await fetch(`/api/conversations/${id}`);
                const data = await res.json();
                
                if (data.error) {
                    alert('加载对话失败: ' + data.error);
                    return;
                }
                
                const modal = document.getElementById('modal');
                const modalBody = document.getElementById('modal-body');
                
                modalBody.innerHTML = data.messages.map(msg => {
                    let typeClass = 'system';
                    let typeName = '系统';
                    
                    if (msg.type === 'HumanMessage') {
                        typeClass = 'human';
                        typeName = '👤 用户';
                    } else if (msg.type === 'AIMessage') {
                        typeClass = 'ai';
                        typeName = '🤖 AI';
                    } else if (msg.type === 'ToolMessage') {
                        typeClass = 'system';
                        typeName = '🔧 工具';
                    }
                    
                    let content = msg.content || '';
                    if (content.length > 1000) {
                        content = content.substring(0, 1000) + '... [已截断]';
                    }
                    
                    // 转义 HTML 并替换换行符
                    content = content.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\\n/g, '<br>');
                    
                    return `
                        <div class="message ${typeClass}">
                            <div class="message-type">${typeName}</div>
                            <div>${content}</div>
                        </div>
                    `;
                }).join('');
                
                modal.classList.add('active');
            } catch (e) {
                console.error('查看对话失败:', e);
                alert('查看对话失败');
            }
        }
        
        function closeModal() {
            document.getElementById('modal').classList.remove('active');
        }
        
        // 点击模态框外部关闭
        document.getElementById('modal').addEventListener('click', function(e) {
            if (e.target === this) {
                closeModal();
            }
        });
        
        // 初始加载
        loadConversations();
        
        // 每30秒刷新一次
        setInterval(loadConversations, 30000);
    </script>
</body>
</html>
'''

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

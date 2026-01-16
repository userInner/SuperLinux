"""ReAct Graph implementation using LangGraph."""

import json
from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import END, StateGraph

from ..common.models import ToolCall, ToolSchema
from ..mcp_client.client import MCPClientManager
from .llm_engine import LLMEngine
from .state import AgentState


class ReActGraph:
    """ReAct (Reasoning and Acting) graph implementation."""
    
    # Operations that require human approval
    HIGH_RISK_OPERATIONS = {
        "delete_file",
        "stop_service",
        "restart_service",
        "start_service",
    }
    
    def __init__(
        self,
        llm_engine: LLMEngine,
        mcp_manager: MCPClientManager,
        max_iterations: int = 10
    ):
        """Initialize the ReAct graph.
        
        Args:
            llm_engine: The LLM engine for reasoning.
            mcp_manager: The MCP client manager for tool execution.
            max_iterations: Maximum number of reasoning iterations.
        """
        self.llm_engine = llm_engine
        self.mcp_manager = mcp_manager
        self.max_iterations = max_iterations
        self._tools: list[tuple[str, ToolSchema]] = []
        self._graph = None
    
    async def initialize(self) -> None:
        """Initialize the graph with available tools."""
        # Discover all tools
        self._tools = await self.mcp_manager.list_all_tools()
        
        # Bind tools to LLM
        tool_schemas = [schema for _, schema in self._tools]
        self.llm_engine.bind_tools(tool_schemas)
        
        # Build the graph
        self._graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph.
        
        Returns:
            Compiled state graph.
        """
        graph = StateGraph(AgentState)
        
        # Add nodes
        graph.add_node("reason", self._reason_node)
        graph.add_node("act", self._act_node)
        graph.add_node("approve", self._approve_node)
        graph.add_node("respond", self._respond_node)
        
        # Set entry point
        graph.set_entry_point("reason")
        
        # Add conditional edges from reason node
        graph.add_conditional_edges(
            "reason",
            self._should_continue,
            {
                "act": "act",
                "approve": "approve",
                "respond": "respond"
            }
        )
        
        # Add edges back to reason after action/approval
        graph.add_edge("act", "reason")
        graph.add_edge("approve", "reason")
        
        # Respond ends the graph
        graph.add_edge("respond", END)
        
        return graph.compile()
    
    async def _reason_node(self, state: AgentState) -> dict[str, Any]:
        """Reasoning node - calls LLM to decide next action.
        
        Args:
            state: Current agent state.
            
        Returns:
            State updates with LLM response.
        """
        # Get tool schemas for binding
        tool_schemas = [schema for _, schema in self._tools]
        
        # Call LLM
        response = await self.llm_engine.invoke(
            list(state["messages"]),
            tools=tool_schemas
        )
        
        return {"messages": [response]}
    
    async def _act_node(self, state: AgentState) -> dict[str, Any]:
        """Action node - executes tool calls.
        
        Args:
            state: Current agent state.
            
        Returns:
            State updates with tool results.
        """
        # Get the last message (should be AI message with tool calls)
        last_message = state["messages"][-1]
        
        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            return {}
        
        tool_messages = []
        tool_results = []
        
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_id = tool_call["id"]
            
            # Find the server for this tool
            server_name = None
            for srv_name, schema in self._tools:
                if schema.name == tool_name:
                    server_name = srv_name
                    break
            
            if not server_name:
                result_content = json.dumps({
                    "error": True,
                    "error_code": "TOOL_NOT_FOUND",
                    "message": f"Tool '{tool_name}' not found"
                })
                tool_messages.append(ToolMessage(
                    content=result_content,
                    tool_call_id=tool_id
                ))
                tool_results.append({
                    "tool_name": tool_name,
                    "result": result_content,
                    "is_error": True
                })
                continue
            
            # Execute the tool
            call = ToolCall(id=tool_id, name=tool_name, arguments=tool_args)
            result = await self.mcp_manager.call_tool(server_name, call)
            
            tool_messages.append(ToolMessage(
                content=result.content,
                tool_call_id=tool_id
            ))
            tool_results.append({
                "tool_name": tool_name,
                "result": result.content,
                "is_error": result.is_error
            })
        
        return {
            "messages": tool_messages,
            "tool_results": state["tool_results"] + tool_results
        }
    
    async def _approve_node(self, state: AgentState) -> dict[str, Any]:
        """Approval node - handles human-in-the-loop approval.
        
        Args:
            state: Current agent state.
            
        Returns:
            State updates after approval handling.
        """
        approval_request = state.get("approval_request")
        
        if not approval_request:
            return {"pending_approval": False}
        
        # In a real implementation, this would wait for user input
        # For now, we'll add a message indicating approval is needed
        approval_message = HumanMessage(
            content=f"[APPROVAL REQUIRED] Operation: {approval_request['operation']}\n"
                    f"Details: {json.dumps(approval_request['details'], indent=2)}\n"
                    f"Please respond with 'approved' or 'denied'."
        )
        
        return {
            "messages": [approval_message],
            "pending_approval": False,
            "approval_request": None
        }
    
    async def _respond_node(self, state: AgentState) -> dict[str, Any]:
        """Response node - generates final response to user.
        
        Args:
            state: Current agent state.
            
        Returns:
            Empty dict (terminal node).
        """
        # The last AI message is the response
        return {}
    
    def _should_continue(
        self, state: AgentState
    ) -> Literal["act", "approve", "respond"]:
        """Determine the next node based on state.
        
        Args:
            state: Current agent state.
            
        Returns:
            The name of the next node.
        """
        # Check if pending approval
        if state.get("pending_approval"):
            return "approve"
        
        # Get the last message
        messages = state.get("messages", [])
        if not messages:
            return "respond"
        
        last_message = messages[-1]
        
        # If not an AI message, respond
        if not isinstance(last_message, AIMessage):
            return "respond"
        
        # Check for tool calls
        tool_calls = getattr(last_message, "tool_calls", None)
        if not tool_calls:
            return "respond"
        
        # Check if any tool call requires approval
        for tool_call in tool_calls:
            tool_name = tool_call.get("name", "")
            if tool_name in self.HIGH_RISK_OPERATIONS:
                # Check if the tool result indicates approval needed
                # This would be set by the tool itself
                pass
        
        return "act"
    
    async def run(self, user_input: str, thread_id: str | None = None) -> str:
        """Run the agent with user input.
        
        Args:
            user_input: The user's message.
            thread_id: Optional thread ID for persistence.
            
        Returns:
            The agent's response.
        """
        if not self._graph:
            await self.initialize()
        
        # Create initial state
        initial_state: AgentState = {
            "messages": [HumanMessage(content=user_input)],
            "current_task": user_input,
            "tool_results": [],
            "pending_approval": False,
            "approval_request": None,
            "error_count": 0,
            "last_error": None
        }
        
        # Run the graph
        config = {}
        if thread_id:
            config["configurable"] = {"thread_id": thread_id}
        
        final_state = await self._graph.ainvoke(initial_state, config)
        
        # Extract the final response
        messages = final_state.get("messages", [])
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and not msg.tool_calls:
                return msg.content
            elif isinstance(msg, AIMessage) and msg.content:
                return msg.content
        
        return "I was unable to generate a response."

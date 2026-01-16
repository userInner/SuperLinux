"""Agent state management for LangGraph."""

from typing import Annotated, Any, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State definition for the ReAct agent.
    
    Attributes:
        messages: Conversation history with automatic message accumulation.
        current_task: Description of the current task being executed.
        tool_results: List of tool execution results.
        pending_approval: Whether waiting for human approval.
        approval_request: Details of the pending approval request.
        error_count: Number of consecutive errors.
        last_error: Details of the last error.
    """
    
    messages: Annotated[Sequence[BaseMessage], add_messages]
    current_task: str
    tool_results: list[dict[str, Any]]
    pending_approval: bool
    approval_request: dict[str, Any] | None
    error_count: int
    last_error: dict[str, Any] | None


def create_initial_state(task: str = "") -> AgentState:
    """Create an initial agent state.
    
    Args:
        task: Optional initial task description.
        
    Returns:
        A new AgentState with default values.
    """
    return AgentState(
        messages=[],
        current_task=task,
        tool_results=[],
        pending_approval=False,
        approval_request=None,
        error_count=0,
        last_error=None
    )


def add_tool_result(
    state: AgentState,
    tool_name: str,
    result: Any,
    is_error: bool = False
) -> AgentState:
    """Add a tool result to the state.
    
    Args:
        state: Current state.
        tool_name: Name of the tool that was called.
        result: The tool result.
        is_error: Whether the result is an error.
        
    Returns:
        Updated state with the new tool result.
    """
    new_result = {
        "tool_name": tool_name,
        "result": result,
        "is_error": is_error
    }
    
    return AgentState(
        messages=state["messages"],
        current_task=state["current_task"],
        tool_results=[*state["tool_results"], new_result],
        pending_approval=state["pending_approval"],
        approval_request=state["approval_request"],
        error_count=state["error_count"] + (1 if is_error else 0),
        last_error=new_result if is_error else state["last_error"]
    )


def set_pending_approval(
    state: AgentState,
    operation: str,
    details: dict[str, Any]
) -> AgentState:
    """Set the state to pending approval.
    
    Args:
        state: Current state.
        operation: The operation requiring approval.
        details: Details about the approval request.
        
    Returns:
        Updated state with pending approval.
    """
    return AgentState(
        messages=state["messages"],
        current_task=state["current_task"],
        tool_results=state["tool_results"],
        pending_approval=True,
        approval_request={
            "operation": operation,
            "details": details
        },
        error_count=state["error_count"],
        last_error=state["last_error"]
    )


def clear_approval(state: AgentState) -> AgentState:
    """Clear the pending approval state.
    
    Args:
        state: Current state.
        
    Returns:
        Updated state with approval cleared.
    """
    return AgentState(
        messages=state["messages"],
        current_task=state["current_task"],
        tool_results=state["tool_results"],
        pending_approval=False,
        approval_request=None,
        error_count=state["error_count"],
        last_error=state["last_error"]
    )


def reset_error_count(state: AgentState) -> AgentState:
    """Reset the error count after successful operation.
    
    Args:
        state: Current state.
        
    Returns:
        Updated state with error count reset.
    """
    return AgentState(
        messages=state["messages"],
        current_task=state["current_task"],
        tool_results=state["tool_results"],
        pending_approval=state["pending_approval"],
        approval_request=state["approval_request"],
        error_count=0,
        last_error=None
    )

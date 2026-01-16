"""Error recovery strategies for the agent."""

import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from ..common.exceptions import (
    ConnectionTimeoutError,
    MCPCommunicationError,
    ParameterValidationError,
    SecurityViolationError,
    ToolExecutionError,
)
from .state import AgentState

logger = logging.getLogger(__name__)


class ErrorRecoveryStrategy:
    """Handles error recovery for the agent."""
    
    def __init__(self, max_retries: int = 3):
        """Initialize the recovery strategy.
        
        Args:
            max_retries: Maximum number of retry attempts.
        """
        self.max_retries = max_retries
    
    async def handle_error(
        self,
        error: Exception,
        state: AgentState
    ) -> tuple[AgentState, str | None]:
        """Handle an error and determine recovery action.
        
        Args:
            error: The exception that occurred.
            state: Current agent state.
            
        Returns:
            Tuple of (updated_state, recovery_message).
            recovery_message is None if no recovery is possible.
        """
        error_count = state.get("error_count", 0)
        
        # Check if we've exceeded max retries
        if error_count >= self.max_retries:
            logger.warning(f"Max retries ({self.max_retries}) exceeded")
            return self._create_failure_state(state, error), None
        
        # Handle specific error types
        if isinstance(error, ParameterValidationError):
            return await self._handle_parameter_error(error, state)
        elif isinstance(error, ConnectionTimeoutError):
            return await self._handle_timeout_error(error, state)
        elif isinstance(error, SecurityViolationError):
            return await self._handle_security_error(error, state)
        elif isinstance(error, MCPCommunicationError):
            return await self._handle_communication_error(error, state)
        elif isinstance(error, ToolExecutionError):
            return await self._handle_tool_error(error, state)
        else:
            return await self._handle_generic_error(error, state)
    
    async def _handle_parameter_error(
        self,
        error: ParameterValidationError,
        state: AgentState
    ) -> tuple[AgentState, str]:
        """Handle parameter validation errors by asking LLM to regenerate.
        
        Args:
            error: The parameter validation error.
            state: Current agent state.
            
        Returns:
            Updated state and recovery message.
        """
        recovery_message = (
            f"The parameter '{error.param_name}' for tool '{error.tool_name}' "
            f"was invalid: {error.reason}. Please try again with corrected parameters."
        )
        
        new_state = self._increment_error_count(state, {
            "type": "parameter_validation",
            "tool_name": error.tool_name,
            "param_name": error.param_name,
            "reason": error.reason
        })
        
        # Add a message to guide the LLM
        messages = list(state["messages"])
        messages.append(HumanMessage(content=recovery_message))
        new_state["messages"] = messages
        
        return new_state, recovery_message
    
    async def _handle_timeout_error(
        self,
        error: ConnectionTimeoutError,
        state: AgentState
    ) -> tuple[AgentState, str]:
        """Handle connection timeout by suggesting retry.
        
        Args:
            error: The timeout error.
            state: Current agent state.
            
        Returns:
            Updated state and recovery message.
        """
        recovery_message = (
            f"Connection timed out after {error.timeout}s. "
            "Retrying the operation..."
        )
        
        new_state = self._increment_error_count(state, {
            "type": "connection_timeout",
            "timeout": error.timeout,
            "transport": error.transport_type
        })
        
        return new_state, recovery_message
    
    async def _handle_security_error(
        self,
        error: SecurityViolationError,
        state: AgentState
    ) -> tuple[AgentState, str | None]:
        """Handle security violations - no automatic recovery.
        
        Args:
            error: The security violation error.
            state: Current agent state.
            
        Returns:
            Updated state and None (no recovery).
        """
        logger.error(f"Security violation: {error.violation_type} - {error.details}")
        
        # Security violations should not be retried
        failure_message = (
            f"Security violation detected: {error.violation_type}. "
            f"This operation has been blocked for safety reasons."
        )
        
        new_state = self._create_failure_state(state, error)
        messages = list(state["messages"])
        messages.append(AIMessage(content=failure_message))
        new_state["messages"] = messages
        
        return new_state, None
    
    async def _handle_communication_error(
        self,
        error: MCPCommunicationError,
        state: AgentState
    ) -> tuple[AgentState, str]:
        """Handle MCP communication errors.
        
        Args:
            error: The communication error.
            state: Current agent state.
            
        Returns:
            Updated state and recovery message.
        """
        recovery_message = (
            f"Communication error with MCP server ({error.transport_type}): "
            f"{error.message}. Attempting to reconnect..."
        )
        
        new_state = self._increment_error_count(state, {
            "type": "communication",
            "transport": error.transport_type,
            "code": error.error_code,
            "message": error.message
        })
        
        return new_state, recovery_message
    
    async def _handle_tool_error(
        self,
        error: ToolExecutionError,
        state: AgentState
    ) -> tuple[AgentState, str]:
        """Handle general tool execution errors.
        
        Args:
            error: The tool execution error.
            state: Current agent state.
            
        Returns:
            Updated state and recovery message.
        """
        recovery_message = (
            f"Tool '{error.tool_name}' failed with error: {error.error_type}. "
            "Please try a different approach or tool."
        )
        
        new_state = self._increment_error_count(state, {
            "type": "tool_execution",
            "tool_name": error.tool_name,
            "error_type": error.error_type,
            "details": error.details
        })
        
        messages = list(state["messages"])
        messages.append(HumanMessage(content=recovery_message))
        new_state["messages"] = messages
        
        return new_state, recovery_message
    
    async def _handle_generic_error(
        self,
        error: Exception,
        state: AgentState
    ) -> tuple[AgentState, str]:
        """Handle unknown/generic errors.
        
        Args:
            error: The exception.
            state: Current agent state.
            
        Returns:
            Updated state and recovery message.
        """
        logger.exception(f"Unexpected error: {error}")
        
        recovery_message = (
            f"An unexpected error occurred: {str(error)}. "
            "Attempting to continue..."
        )
        
        new_state = self._increment_error_count(state, {
            "type": "unknown",
            "error_class": error.__class__.__name__,
            "message": str(error)
        })
        
        return new_state, recovery_message
    
    def _increment_error_count(
        self,
        state: AgentState,
        error_details: dict[str, Any]
    ) -> AgentState:
        """Increment error count and record error details.
        
        Args:
            state: Current state.
            error_details: Details about the error.
            
        Returns:
            Updated state.
        """
        return AgentState(
            messages=state["messages"],
            current_task=state["current_task"],
            tool_results=state["tool_results"],
            pending_approval=state["pending_approval"],
            approval_request=state["approval_request"],
            error_count=state["error_count"] + 1,
            last_error=error_details
        )
    
    def _create_failure_state(
        self,
        state: AgentState,
        error: Exception
    ) -> AgentState:
        """Create a failure state when recovery is not possible.
        
        Args:
            state: Current state.
            error: The final error.
            
        Returns:
            Updated state indicating failure.
        """
        return AgentState(
            messages=state["messages"],
            current_task=state["current_task"],
            tool_results=state["tool_results"],
            pending_approval=False,
            approval_request=None,
            error_count=state["error_count"],
            last_error={
                "type": "fatal",
                "error_class": error.__class__.__name__,
                "message": str(error),
                "recoverable": False
            }
        )

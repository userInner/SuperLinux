"""Core data models for the LangGraph + MCP Agent system."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolSchema:
    """Tool metadata following MCP protocol."""
    
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema format
    
    def validate(self) -> bool:
        """Validate that the schema has all required fields."""
        if not self.name or not isinstance(self.name, str):
            return False
        if not self.description or not isinstance(self.description, str):
            return False
        if not isinstance(self.parameters, dict):
            return False
        # Check JSON Schema structure
        if "type" not in self.parameters:
            return False
        return True


@dataclass
class ToolCall:
    """Represents a tool invocation request."""
    
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ToolResult:
    """Result from a tool execution."""
    
    tool_call_id: str
    content: str
    is_error: bool = False
    error_code: str | None = None
    error_message: str | None = None


@dataclass
class AgentResponse:
    """Response from the agent."""
    
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    requires_approval: bool = False
    approval_details: dict[str, Any] | None = None

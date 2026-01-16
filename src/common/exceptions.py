"""Custom exceptions for the LangGraph + MCP Agent system."""


class AgentError(Exception):
    """Base exception for all agent errors."""
    pass


# Communication Errors
class MCPCommunicationError(AgentError):
    """MCP communication error."""
    
    def __init__(self, transport_type: str, error_code: str, message: str):
        self.transport_type = transport_type
        self.error_code = error_code
        self.message = message
        super().__init__(f"[{transport_type}] {error_code}: {message}")


class ConnectionTimeoutError(MCPCommunicationError):
    """Connection timeout error."""
    
    def __init__(self, transport_type: str, timeout: float):
        super().__init__(
            transport_type,
            "CONNECTION_TIMEOUT",
            f"Connection timed out after {timeout}s"
        )
        self.timeout = timeout


class ServerNotFoundError(MCPCommunicationError):
    """Server not found error."""
    
    def __init__(self, transport_type: str, server_name: str):
        super().__init__(
            transport_type,
            "SERVER_NOT_FOUND",
            f"Server '{server_name}' not found"
        )
        self.server_name = server_name


# Tool Execution Errors
class ToolExecutionError(AgentError):
    """Tool execution error."""
    
    def __init__(self, tool_name: str, error_type: str, details: dict | None = None):
        self.tool_name = tool_name
        self.error_type = error_type
        self.details = details or {}
        super().__init__(f"Tool '{tool_name}' failed: {error_type}")


class ParameterValidationError(ToolExecutionError):
    """Parameter validation failed."""
    
    def __init__(self, tool_name: str, param_name: str, reason: str):
        super().__init__(
            tool_name,
            "PARAMETER_VALIDATION",
            {"param_name": param_name, "reason": reason}
        )
        self.param_name = param_name
        self.reason = reason


class SecurityViolationError(ToolExecutionError):
    """Security violation detected."""
    
    def __init__(self, tool_name: str, violation_type: str, details: str):
        super().__init__(
            tool_name,
            "SECURITY_VIOLATION",
            {"violation_type": violation_type, "details": details}
        )
        self.violation_type = violation_type


# State Errors
class CheckpointError(AgentError):
    """Checkpoint operation error."""
    
    def __init__(self, operation: str, message: str):
        self.operation = operation
        super().__init__(f"Checkpoint {operation} failed: {message}")


class StateRecoveryError(AgentError):
    """State recovery error."""
    
    def __init__(self, thread_id: str, message: str):
        self.thread_id = thread_id
        super().__init__(f"Failed to recover state for thread '{thread_id}': {message}")

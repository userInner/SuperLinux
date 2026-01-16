"""Configuration models for the LangGraph + MCP Agent system."""

import os
import re
from dataclasses import dataclass, field
from typing import Literal


def resolve_env_vars(value: str) -> str:
    """Resolve environment variables in a string.
    
    Supports ${VAR_NAME} syntax.
    """
    if not isinstance(value, str):
        return value
    
    pattern = r'\$\{([^}]+)\}'
    
    def replacer(match):
        var_name = match.group(1)
        return os.environ.get(var_name, "")
    
    return re.sub(pattern, replacer, value)


@dataclass
class AIModelConfig:
    """Configuration for an AI model."""
    
    name: str
    provider: Literal["openai", "anthropic", "deepseek", "gemini"]
    model: str
    api_key: str
    role: str = "primary"  # primary, consultant, specialist
    base_url: str | None = None  # 自定义 API 端点
    
    def __post_init__(self):
        """Resolve environment variables in api_key."""
        self.api_key = resolve_env_vars(self.api_key)


@dataclass
class AgentBehaviorConfig:
    """Configuration for agent behavior."""
    
    max_retries: int = 3
    search_attempts_before_consult: int = 2
    max_iterations: int = 15


@dataclass
class MCPServerConfig:
    """Configuration for an MCP Server connection."""
    
    name: str
    transport: Literal["stdio", "http"]
    command: str | None = None
    args: list[str] = field(default_factory=list)
    url: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0
    
    def validate(self) -> bool:
        """Validate configuration based on transport type."""
        if self.transport == "stdio":
            return self.command is not None
        elif self.transport == "http":
            return self.url is not None
        return False


@dataclass 
class MultiAgentConfig:
    """Full configuration for multi-AI agent system."""
    
    primary_ai: AIModelConfig
    secondary_ais: list[AIModelConfig] = field(default_factory=list)
    agent: AgentBehaviorConfig = field(default_factory=AgentBehaviorConfig)
    mcp_servers: list[MCPServerConfig] = field(default_factory=list)
    checkpoint_db: str = "checkpoints.db"
    sandbox_path: str = "/tmp/agent_sandbox"
    workspace_path: str = "~/agent_workspace"
    
    @classmethod
    def from_yaml(cls, path: str) -> "MultiAgentConfig":
        """Load configuration from a YAML file."""
        import yaml
        
        with open(path) as f:
            data = yaml.safe_load(f)
        
        # Parse primary AI
        primary_data = data.get("primary_ai", {})
        primary_ai = AIModelConfig(
            name=primary_data.get("name", "Primary"),
            provider=primary_data.get("provider", "deepseek"),
            model=primary_data.get("model", "deepseek-chat"),
            api_key=primary_data.get("api_key", ""),
            role="primary",
            base_url=primary_data.get("base_url")
        )
        
        # Parse secondary AIs
        secondary_ais = []
        for ai_data in data.get("secondary_ais", []):
            api_key = resolve_env_vars(ai_data.get("api_key", ""))
            if api_key:  # Only add if API key is available
                secondary_ais.append(AIModelConfig(
                    name=ai_data.get("name", "Secondary"),
                    provider=ai_data.get("provider", "openai"),
                    model=ai_data.get("model", "gpt-4o"),
                    api_key=api_key,
                    role=ai_data.get("role", "consultant"),
                    base_url=ai_data.get("base_url")
                ))
        
        # Parse agent behavior
        agent_data = data.get("agent", {})
        agent = AgentBehaviorConfig(
            max_retries=agent_data.get("max_retries", 3),
            search_attempts_before_consult=agent_data.get("search_attempts_before_consult", 2),
            max_iterations=agent_data.get("max_iterations", 15)
        )
        
        # Parse MCP servers
        mcp_servers = [
            MCPServerConfig(**server) 
            for server in data.get("mcp_servers", [])
        ]
        
        # Parse workspace path (expand ~)
        workspace_path = data.get("workspace_path", "~/agent_workspace")
        workspace_path = os.path.expanduser(workspace_path)
        
        return cls(
            primary_ai=primary_ai,
            secondary_ais=secondary_ais,
            agent=agent,
            mcp_servers=mcp_servers,
            checkpoint_db=data.get("checkpoint_db", "checkpoints.db"),
            sandbox_path=data.get("sandbox_path", "/tmp/agent_sandbox"),
            workspace_path=workspace_path,
        )


# Legacy config for backward compatibility
@dataclass
class AgentConfig:
    """Main configuration for the agent (legacy)."""
    
    llm_provider: Literal["openai", "anthropic", "deepseek", "gemini"]
    llm_model: str
    api_key: str
    mcp_servers: list[MCPServerConfig] = field(default_factory=list)
    checkpoint_db: str = "checkpoints.db"
    max_retries: int = 3
    sandbox_path: str = "/tmp/agent_sandbox"
    
    @classmethod
    def from_yaml(cls, path: str) -> "AgentConfig":
        """Load configuration from a YAML file."""
        import yaml
        
        with open(path) as f:
            data = yaml.safe_load(f)
        
        # Support both old and new config format
        if "primary_ai" in data:
            # New format - extract primary AI settings
            primary = data["primary_ai"]
            api_key = resolve_env_vars(primary.get("api_key", ""))
            return cls(
                llm_provider=primary.get("provider", "deepseek"),
                llm_model=primary.get("model", "deepseek-chat"),
                api_key=api_key,
                mcp_servers=[MCPServerConfig(**s) for s in data.get("mcp_servers", [])],
                checkpoint_db=data.get("checkpoint_db", "checkpoints.db"),
                max_retries=data.get("agent", {}).get("max_retries", 3),
                sandbox_path=data.get("sandbox_path", "/tmp/agent_sandbox"),
            )
        else:
            # Old format
            api_key = resolve_env_vars(data.get("api_key", ""))
            return cls(
                llm_provider=data["llm_provider"],
                llm_model=data["llm_model"],
                api_key=api_key,
                mcp_servers=[MCPServerConfig(**s) for s in data.get("mcp_servers", [])],
                checkpoint_db=data.get("checkpoint_db", "checkpoints.db"),
                max_retries=data.get("max_retries", 3),
                sandbox_path=data.get("sandbox_path", "/tmp/agent_sandbox"),
            )

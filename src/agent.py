"""Main Linux Agent implementation."""

import asyncio
import logging
import uuid
from typing import Any

from .common.config import AgentConfig, MCPServerConfig
from .mcp_client.client import MCPClientManager
from .orchestrator.approval import ApprovalManager
from .orchestrator.checkpoint import CheckpointManager
from .orchestrator.graph import ReActGraph
from .orchestrator.llm_engine import create_llm_engine
from .orchestrator.recovery import ErrorRecoveryStrategy

logger = logging.getLogger(__name__)


class LinuxAgent:
    """Main agent class that orchestrates all components."""
    
    def __init__(self, config: AgentConfig):
        """Initialize the Linux agent.
        
        Args:
            config: Agent configuration.
        """
        self.config = config
        
        # Initialize components
        self.llm_engine = create_llm_engine(
            provider=config.llm_provider,
            model=config.llm_model,
            api_key=config.api_key
        )
        
        self.mcp_manager = MCPClientManager()
        self.checkpoint_manager = CheckpointManager(config.checkpoint_db)
        self.approval_manager = ApprovalManager()
        self.recovery_strategy = ErrorRecoveryStrategy(max_retries=config.max_retries)
        
        self._graph: ReActGraph | None = None
        self._initialized = False
        self._current_thread_id: str | None = None
    
    async def initialize(self) -> None:
        """Initialize the agent and connect to MCP servers."""
        if self._initialized:
            return
        
        logger.info("Initializing Linux Agent...")
        
        # Connect to MCP servers
        for server_config in self.config.mcp_servers:
            try:
                logger.info(f"Connecting to MCP server: {server_config.name}")
                await self.mcp_manager.add_server(server_config)
                logger.info(f"Connected to {server_config.name}")
            except Exception as e:
                logger.error(f"Failed to connect to {server_config.name}: {e}")
        
        # Create the ReAct graph
        self._graph = ReActGraph(
            llm_engine=self.llm_engine,
            mcp_manager=self.mcp_manager
        )
        await self._graph.initialize()
        
        self._initialized = True
        logger.info("Linux Agent initialized successfully")
    
    async def chat(
        self,
        message: str,
        thread_id: str | None = None
    ) -> str:
        """Send a message to the agent and get a response.
        
        Args:
            message: The user's message.
            thread_id: Optional thread ID for conversation continuity.
            
        Returns:
            The agent's response.
        """
        if not self._initialized:
            await self.initialize()
        
        assert self._graph is not None
        
        # Use provided thread_id or create new one
        if thread_id:
            self._current_thread_id = thread_id
        elif not self._current_thread_id:
            self._current_thread_id = str(uuid.uuid4())
        
        try:
            response = await self._graph.run(
                user_input=message,
                thread_id=self._current_thread_id
            )
            return response
        except Exception as e:
            logger.exception(f"Error during chat: {e}")
            return f"An error occurred: {str(e)}"
    
    async def run_interactive(self) -> None:
        """Run the agent in interactive mode."""
        if not self._initialized:
            await self.initialize()
        
        print("\n" + "=" * 60)
        print("🤖 Linux Agent - Interactive Mode")
        print("=" * 60)
        print("Type 'quit' or 'exit' to end the session.")
        print("Type 'new' to start a new conversation.")
        print("Type 'threads' to list saved conversations.")
        print("-" * 60 + "\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ("quit", "exit"):
                    print("\nGoodbye! 👋")
                    break
                
                if user_input.lower() == "new":
                    self._current_thread_id = str(uuid.uuid4())
                    print(f"\n📝 Started new conversation: {self._current_thread_id[:8]}...\n")
                    continue
                
                if user_input.lower() == "threads":
                    threads = await self.checkpoint_manager.list_threads()
                    if threads:
                        print("\n📚 Saved conversations:")
                        for t in threads[:10]:
                            print(f"  - {t['thread_id'][:8]}... (last: {t['last_updated']})")
                    else:
                        print("\n📚 No saved conversations.")
                    print()
                    continue
                
                # Get response
                print("\n🤔 Thinking...\n")
                response = await self.chat(user_input)
                print(f"Agent: {response}\n")
                
            except KeyboardInterrupt:
                print("\n\nInterrupted. Type 'quit' to exit.\n")
            except EOFError:
                print("\nGoodbye! 👋")
                break
    
    async def shutdown(self) -> None:
        """Shutdown the agent and cleanup resources."""
        logger.info("Shutting down Linux Agent...")
        
        await self.mcp_manager.disconnect_all()
        self.checkpoint_manager.close()
        
        self._initialized = False
        logger.info("Linux Agent shutdown complete")
    
    async def __aenter__(self) -> "LinuxAgent":
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.shutdown()


async def create_agent_from_config(config_path: str) -> LinuxAgent:
    """Create an agent from a configuration file.
    
    Args:
        config_path: Path to the YAML configuration file.
        
    Returns:
        Configured LinuxAgent instance.
    """
    config = AgentConfig.from_yaml(config_path)
    return LinuxAgent(config)


async def create_agent_simple(
    llm_provider: str = "openai",
    llm_model: str = "gpt-4o",
    api_key: str = "",
    sandbox_path: str = "/tmp/agent_sandbox"
) -> LinuxAgent:
    """Create an agent with simple configuration.
    
    Args:
        llm_provider: The LLM provider (openai, anthropic, deepseek).
        llm_model: The model name.
        api_key: The API key.
        sandbox_path: Path for file operations sandbox.
        
    Returns:
        Configured LinuxAgent instance.
    """
    # Create default MCP server configs
    mcp_servers = [
        MCPServerConfig(
            name="system-monitor",
            transport="stdio",
            command="python",
            args=["-m", "src.mcp_servers.system_monitor"]
        ),
        MCPServerConfig(
            name="file-manager",
            transport="stdio",
            command="python",
            args=["-m", "src.mcp_servers.file_manager", sandbox_path]
        ),
        MCPServerConfig(
            name="network",
            transport="stdio",
            command="python",
            args=["-m", "src.mcp_servers.network"]
        ),
        MCPServerConfig(
            name="service-manager",
            transport="stdio",
            command="python",
            args=["-m", "src.mcp_servers.service_manager"]
        ),
    ]
    
    config = AgentConfig(
        llm_provider=llm_provider,
        llm_model=llm_model,
        api_key=api_key,
        mcp_servers=mcp_servers,
        sandbox_path=sandbox_path
    )
    
    return LinuxAgent(config)

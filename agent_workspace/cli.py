"""Command-line interface for the Linux Agent."""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

from .agent import LinuxAgent, create_agent_from_config, create_agent_simple
from .common.config import AgentConfig


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration.
    
    Args:
        verbose: Enable verbose (DEBUG) logging.
    """
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stderr)
        ]
    )
    
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.
    
    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Linux Agent - An intelligent assistant powered by LangGraph + MCP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with config file
  linux-agent --config config.yaml
  
  # Run with environment variables
  export OPENAI_API_KEY=sk-...
  linux-agent --provider openai --model gpt-4o
  
  # Run a single command
  linux-agent --command "What's the current CPU usage?"
  
  # Run in verbose mode
  linux-agent --verbose
"""
    )
    
    # Configuration options
    config_group = parser.add_argument_group("Configuration")
    config_group.add_argument(
        "-c", "--config",
        type=str,
        help="Path to YAML configuration file"
    )
    config_group.add_argument(
        "--provider",
        type=str,
        choices=["openai", "anthropic", "deepseek"],
        default="openai",
        help="LLM provider (default: openai)"
    )
    config_group.add_argument(
        "--model",
        type=str,
        default="gpt-4o",
        help="Model name (default: gpt-4o)"
    )
    config_group.add_argument(
        "--api-key",
        type=str,
        help="API key (or use environment variable)"
    )
    config_group.add_argument(
        "--sandbox",
        type=str,
        default="/tmp/agent_sandbox",
        help="Sandbox directory for file operations"
    )
    
    # Execution options
    exec_group = parser.add_argument_group("Execution")
    exec_group.add_argument(
        "--command",
        type=str,
        help="Run a single command and exit"
    )
    exec_group.add_argument(
        "--thread",
        type=str,
        help="Thread ID for conversation continuity"
    )
    
    # Output options
    output_group = parser.add_argument_group("Output")
    output_group.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    output_group.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress non-essential output"
    )
    
    return parser.parse_args()


def get_api_key(args: argparse.Namespace) -> str:
    """Get API key from arguments or environment.
    
    Args:
        args: Parsed arguments.
        
    Returns:
        The API key.
        
    Raises:
        SystemExit: If no API key is found.
    """
    if args.api_key:
        return args.api_key
    
    # Check environment variables based on provider
    env_vars = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
    }
    
    env_var = env_vars.get(args.provider, "OPENAI_API_KEY")
    api_key = os.environ.get(env_var)
    
    if not api_key:
        print(f"Error: No API key provided. Set {env_var} or use --api-key", file=sys.stderr)
        sys.exit(1)
    
    return api_key


async def run_single_command(agent: LinuxAgent, command: str, thread_id: str | None) -> None:
    """Run a single command and print the response.
    
    Args:
        agent: The agent instance.
        command: The command to run.
        thread_id: Optional thread ID.
    """
    response = await agent.chat(command, thread_id=thread_id)
    print(response)


async def async_main(args: argparse.Namespace) -> int:
    """Async main function.
    
    Args:
        args: Parsed arguments.
        
    Returns:
        Exit code.
    """
    # Create agent
    if args.config:
        if not Path(args.config).exists():
            print(f"Error: Config file not found: {args.config}", file=sys.stderr)
            return 1
        agent = await create_agent_from_config(args.config)
    else:
        api_key = get_api_key(args)
        agent = await create_agent_simple(
            llm_provider=args.provider,
            llm_model=args.model,
            api_key=api_key,
            sandbox_path=args.sandbox
        )
    
    try:
        async with agent:
            if args.command:
                # Single command mode
                await run_single_command(agent, args.command, args.thread)
            else:
                # Interactive mode
                await agent.run_interactive()
        
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130
    except Exception as e:
        logging.exception(f"Fatal error: {e}")
        return 1


def main() -> None:
    """Main entry point."""
    args = parse_args()
    
    # Setup logging
    if not args.quiet:
        setup_logging(args.verbose)
    
    # Run async main
    exit_code = asyncio.run(async_main(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

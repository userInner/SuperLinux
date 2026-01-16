"""LLM Engine abstraction layer for multiple model providers."""

from abc import ABC, abstractmethod
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage

from ..common.models import ToolSchema


class LLMEngine(ABC):
    """Abstract base class for LLM engines."""
    
    def __init__(self, model: str, api_key: str, **kwargs: Any):
        """Initialize the LLM engine.
        
        Args:
            model: The model name/identifier.
            api_key: The API key for authentication.
            **kwargs: Additional provider-specific options.
        """
        self.model = model
        self.api_key = api_key
        self.options = kwargs
        self._llm: BaseChatModel | None = None
        self._llm_with_tools: BaseChatModel | None = None
    
    @abstractmethod
    def _create_llm(self) -> BaseChatModel:
        """Create the underlying LLM instance.
        
        Returns:
            The configured LLM instance.
        """
        pass
    
    @property
    def llm(self) -> BaseChatModel:
        """Get the LLM instance, creating if needed."""
        if self._llm is None:
            self._llm = self._create_llm()
        return self._llm
    
    def bind_tools(self, tools: list[ToolSchema]) -> BaseChatModel:
        """Bind tools to the LLM for function calling.
        
        Args:
            tools: List of tool schemas to bind.
            
        Returns:
            LLM instance with tools bound.
        """
        # Convert ToolSchema to LangChain tool format
        langchain_tools = []
        for tool in tools:
            langchain_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            })
        
        self._llm_with_tools = self.llm.bind_tools(langchain_tools)
        return self._llm_with_tools
    
    async def invoke(
        self,
        messages: list[BaseMessage],
        tools: list[ToolSchema] | None = None
    ) -> BaseMessage:
        """Invoke the LLM with messages.
        
        Args:
            messages: The conversation messages.
            tools: Optional tools to use for this invocation.
            
        Returns:
            The LLM response message.
        """
        if tools:
            llm = self.bind_tools(tools)
        elif self._llm_with_tools:
            llm = self._llm_with_tools
        else:
            llm = self.llm
        
        return await llm.ainvoke(messages)


class OpenAIEngine(LLMEngine):
    """OpenAI GPT engine implementation."""
    
    def _create_llm(self) -> BaseChatModel:
        from langchain_openai import ChatOpenAI
        
        return ChatOpenAI(
            model=self.model,
            api_key=self.api_key,
            temperature=self.options.get("temperature", 0.7),
            max_tokens=self.options.get("max_tokens"),
        )


class ClaudeEngine(LLMEngine):
    """Anthropic Claude engine implementation."""
    
    def _create_llm(self) -> BaseChatModel:
        from langchain_anthropic import ChatAnthropic
        
        return ChatAnthropic(
            model=self.model,
            api_key=self.api_key,
            temperature=self.options.get("temperature", 0.7),
            max_tokens=self.options.get("max_tokens", 4096),
        )


class DeepSeekEngine(LLMEngine):
    """DeepSeek engine implementation (OpenAI-compatible API)."""
    
    def _create_llm(self) -> BaseChatModel:
        from langchain_openai import ChatOpenAI
        
        return ChatOpenAI(
            model=self.model,
            api_key=self.api_key,
            base_url="https://api.deepseek.com/v1",
            temperature=self.options.get("temperature", 0.7),
            max_tokens=self.options.get("max_tokens"),
        )


class GeminiEngine(LLMEngine):
    """Google Gemini engine implementation."""
    
    def _create_llm(self) -> BaseChatModel:
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        return ChatGoogleGenerativeAI(
            model=self.model,
            google_api_key=self.api_key,
            temperature=self.options.get("temperature", 0.7),
            max_output_tokens=self.options.get("max_tokens"),
        )


def create_llm_engine(
    provider: str,
    model: str,
    api_key: str,
    **kwargs: Any
) -> LLMEngine:
    """Factory function to create an LLM engine.
    
    Args:
        provider: The provider name (openai, anthropic, deepseek).
        model: The model name.
        api_key: The API key.
        **kwargs: Additional options.
        
    Returns:
        Configured LLM engine.
        
    Raises:
        ValueError: If provider is unknown.
    """
    engines = {
        "openai": OpenAIEngine,
        "anthropic": ClaudeEngine,
        "deepseek": DeepSeekEngine,
        "gemini": GeminiEngine,
    }
    
    engine_class = engines.get(provider.lower())
    if not engine_class:
        raise ValueError(f"Unknown LLM provider: {provider}. Supported: {list(engines.keys())}")
    
    return engine_class(model=model, api_key=api_key, **kwargs)

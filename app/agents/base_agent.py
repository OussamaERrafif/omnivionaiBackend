"""
Base Agent Class for Academic Research Paper Generator
"""

import logging
from typing import Any, Optional

from langchain_openai import ChatOpenAI
from langchain_core.runnables import Runnable, RunnableLambda

from .config import Config, LLMProvider, SearchSettings


logger = logging.getLogger(__name__)


class BaseAgent:
    """
    Base class for all specialized agents in the AI Deep Search system.
    
    This class provides common functionality for all agents including LLM initialization
    and configuration. All specialized agents (QueryAnalyzer, Research, etc.) inherit
    from this base class.
    
    Attributes:
        name (str): The name identifier for this agent
        llm (ChatOpenAI): The language model instance used by this agent
    """

    def __init__(self, name: str, llm: Optional[Runnable] = None):
        """
        Initialize a base agent with a name and optional LLM instance.
        
        Args:
            name (str): The name identifier for this agent (e.g., "Research", "Summarizer")
            llm (Optional[ChatOpenAI]): Optional pre-configured LLM instance. If not provided,
                                       a new instance will be created using _create_llm()
        """
        # def __init__(self, name: str, llm: Optional[ChatGoogleGenerativeAI] = None):  # Old Google API
        self.name = name
        self.settings: SearchSettings = Config.default_search_settings()
        self.llm = llm or self._create_llm()

    def _create_llm(self) -> Runnable:
        """
        Create and configure an OpenAI LLM instance for this agent.
        
        Builds one OpenAI-compatible client per configured provider. A failed
        request automatically retries the next provider in priority order.
        
        Returns:
            Runnable: A failover-capable LangChain runnable.
        """
        providers = Config.get_llm_providers()
        if not providers:
            raise RuntimeError(
                "No LLM provider is configured. Set at least one of "
                "OPENAI_API_KEY, NVIDIA_API_KEY, or GROQ_API_KEY."
            )

        clients = [(provider, self._build_client(provider)) for provider in providers]
        return RunnableLambda(self._ainvoke_with_fallback(clients), name=f"{self.name}LLMFallback")

    @staticmethod
    def _build_client(provider: LLMProvider) -> ChatOpenAI:
        """Create a provider client without logging or exposing its API key."""
        options: dict[str, Any] = {
            "model": provider.model,
            "api_key": provider.api_key,
            "temperature": 0.3,
            "max_tokens": Config.LLM_MAX_TOKENS,
            "timeout": Config.LLM_TIMEOUT_SECONDS,
            "streaming": False,
        }
        if provider.base_url:
            options["base_url"] = provider.base_url
        return ChatOpenAI(**options)

    @staticmethod
    def _ainvoke_with_fallback(clients: list[tuple[LLMProvider, ChatOpenAI]]):
        """Return an async runnable function that tries providers in order."""
        async def invoke(input_value: Any, config: Any = None) -> Any:
            failures: list[str] = []
            for provider, client in clients:
                try:
                    return await client.ainvoke(input_value, config=config)
                except Exception as error:
                    failures.append(provider.name)
                    logger.warning(
                        "LLM provider '%s' failed with %s; trying the next provider.",
                        provider.name,
                        type(error).__name__,
                    )

            raise RuntimeError(
                "All configured LLM providers failed (" + ", ".join(failures) + ")."
            )

        return invoke

    async def process(self, *args, **kwargs):
        """
        Abstract method to be implemented by subclasses.
        
        Each specialized agent must implement this method to define its
        specific processing logic (e.g., query analysis, research, summarization).
        
        Args:
            *args: Positional arguments specific to the agent type
            **kwargs: Keyword arguments specific to the agent type
            
        Raises:
            NotImplementedError: If called on BaseAgent directly without subclass implementation
        """
        raise NotImplementedError


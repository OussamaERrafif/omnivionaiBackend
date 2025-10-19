"""
Base Agent Class for Academic Research Paper Generator
"""

from typing import Optional, Dict
import hashlib
# Google API imports (commented out - replaced with OpenAI)
# from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.callbacks import StreamingStdOutCallbackHandler

from .config import Config


class BaseAgent:
    """
    Base class for all specialized agents in the AI Deep Search system.
    
    This class provides common functionality for all agents including LLM initialization
    and configuration. All specialized agents (QueryAnalyzer, Research, etc.) inherit
    from this base class.
    
    Attributes:
        name (str): The name identifier for this agent
        llm (ChatOpenAI): The language model instance used by this agent
        _llm_cache (Dict[str, str]): Simple in-memory cache for LLM responses
    """

    def __init__(self, name: str, llm: Optional[ChatOpenAI] = None):
        """
        Initialize a base agent with a name and optional LLM instance.
        
        Args:
            name (str): The name identifier for this agent (e.g., "Research", "Summarizer")
            llm (Optional[ChatOpenAI]): Optional pre-configured LLM instance. If not provided,
                                       a new instance will be created using _create_llm()
        """
        # def __init__(self, name: str, llm: Optional[ChatGoogleGenerativeAI] = None):  # Old Google API
        self.name = name
        self.llm = llm or self._create_llm()
        self._llm_cache: Dict[str, str] = {}  # Simple in-memory cache for LLM responses

    def _create_llm(self):
        """
        Create and configure an OpenAI LLM instance for this agent.
        
        Creates a ChatOpenAI instance configured with:
        - Model from Config.MODEL_NAME
        - API key from Config.OPENAI_API_KEY
        - Temperature of 0.3 (for more deterministic outputs)
        - Maximum output tokens of 16000
        - Streaming enabled with stdout callback
        
        Returns:
            ChatOpenAI: Configured language model instance
        """
        # Old Google Gemini LLM creation (commented out)
        # return ChatGoogleGenerativeAI(
        #     model=Config.MODEL_NAME,
        #     google_api_key=Config.GOOGLE_API_KEY,
        #     temperature=0.3,
        #     max_output_tokens=4096,  # Increased to prevent truncation
        #     streaming=True,
        #     callbacks=[StreamingStdOutCallbackHandler()]
        # )
        
        # New OpenAI LLM creation
        return ChatOpenAI(
            model=Config.MODEL_NAME,
            openai_api_key=Config.OPENAI_API_KEY,
            temperature=0.3,
            max_tokens=16000,  # Significantly increased to prevent truncation (GPT-4o supports up to 16k output)
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()]
        )

    def _get_cache_key(self, prompt: str) -> str:
        """
        Generate a cache key for the given prompt.
        
        Args:
            prompt (str): The prompt to generate a key for
            
        Returns:
            str: MD5 hash of the prompt as cache key
        """
        return hashlib.md5(prompt.encode('utf-8')).hexdigest()

    def _get_cached_response(self, prompt: str) -> Optional[str]:
        """
        Get a cached LLM response for the given prompt.
        
        Args:
            prompt (str): The prompt to check cache for
            
        Returns:
            Optional[str]: Cached response if available, None otherwise
        """
        cache_key = self._get_cache_key(prompt)
        return self._llm_cache.get(cache_key)

    def _cache_response(self, prompt: str, response: str) -> None:
        """
        Cache an LLM response for the given prompt.
        
        Args:
            prompt (str): The prompt that generated the response
            response (str): The response to cache
        """
        cache_key = self._get_cache_key(prompt)
        self._llm_cache[cache_key] = response

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


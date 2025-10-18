"""
Base Agent Class for Academic Research Paper Generator
"""

from typing import Optional
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


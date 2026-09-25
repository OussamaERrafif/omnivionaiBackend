"""
Configuration for Academic Research Paper Generator
"""

import os
from dataclasses import dataclass
from typing import Mapping


def _positive_int_from_env(name: str, default: int) -> int:
    """Read a positive integer without making application startup brittle."""
    try:
        value = int(os.getenv(name, str(default)))
        return value if value > 0 else default
    except ValueError:
        return default


def _positive_float_from_env(name: str, default: float) -> float:
    """Read a positive float without making application startup brittle."""
    try:
        value = float(os.getenv(name, str(default)))
        return value if value > 0 else default
    except ValueError:
        return default


@dataclass(frozen=True)
class LLMProvider:
    """Configuration for one OpenAI-compatible LLM provider."""

    name: str
    api_key: str
    model: str
    base_url: str | None = None


@dataclass(frozen=True)
class SearchSettings:
    """Per-request settings that must not be shared between concurrent searches."""

    max_results_per_search: int
    max_content_length: int
    max_research_iterations: int
    enable_iterative_research: bool
    rate_limit_delay: float
    request_timeout: int
    max_retries: int


class Config:
    """
    System-wide configuration for the AI Deep Search application.
    
    This class contains all configuration parameters including:
    - API keys and model settings
    - Search and content extraction limits
    - Rate limiting parameters
    - Domain diversity controls
    - Iterative research settings
    
    Configuration values are loaded from environment variables with fallback defaults.
    """
    # Google API Configuration (commented out - replaced with OpenAI)
    # GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    # MODEL_NAME = "gemini-2.5-flash"  # Free tier model
    
    # LLM provider configuration. Providers use OpenAI-compatible APIs and are tried
    # in LLM_PROVIDER_ORDER whenever a request fails. Never put real keys in source.
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
    NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "").strip()
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-nano-2025-08-07").strip()
    NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b").strip()
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
    # OpenAI is optional. Keep the default path on the configured NVIDIA and
    # Groq providers so an expired OpenAI key cannot delay or block searches.
    LLM_PROVIDER_ORDER = os.getenv("LLM_PROVIDER_ORDER", "nvidia,groq").strip()
    LLM_MAX_TOKENS = _positive_int_from_env("LLM_MAX_TOKENS", 4096)
    LLM_TIMEOUT_SECONDS = _positive_float_from_env("LLM_TIMEOUT_SECONDS", 60.0)

    # Backwards-compatible alias for integrations that only display the primary model.
    MODEL_NAME = OPENAI_MODEL
    
    MAX_RESULTS_PER_SEARCH = 10  # OPTIMIZED: Increased from 2 to 10 for comprehensive search
    """int: Maximum number of search results to retrieve per search query"""
    
    MAX_CONTENT_LENGTH = 2000  # Increased for better content extraction
    """int: Maximum character length for extracted content from web pages"""
    
    REQUEST_TIMEOUT = 10  # Increased timeout for better content extraction
    """int: HTTP request timeout in seconds for web scraping"""
    
    MAX_RETRIES = 3
    """int: Maximum number of retries for failed HTTP requests"""

    # OPTIMIZED: Reduced rate limits for faster parallel execution
    RATE_LIMIT_DELAY = 0.1  # OPTIMIZED: Reduced from 1.0s to 0.1s for faster execution
    """float: Delay in seconds between API calls to respect rate limits"""
    
    # OPTIMIZED: Parallel processing configuration
    MAX_CONCURRENT_SCRAPING = 8  # Maximum concurrent web scraping requests
    """int: Maximum number of concurrent web scraping operations"""
    
    MAX_CONCURRENT_LLM_CALLS = 10  # Maximum concurrent LLM API calls
    """int: Maximum number of concurrent LLM API calls for summarization/verification"""

    # Domain diversity limits - increased for more sources
    MAX_SOURCES_PER_DOMAIN_PER_TERM = 2  # Allow more sources per domain per term
    """int: Maximum sources allowed from same domain for a single search term"""

    # Search Mode Configurations
    SEARCH_MODES = {
        "deep": {
            "max_results_per_search": 10,  # OPTIMIZED: Increased from 5 to 10
            "max_content_length": 3000,
            "max_research_iterations": 3,
            "enable_iterative_research": False,  # OPTIMIZED: Disabled for faster execution
            "rate_limit_delay": 0.1,  # OPTIMIZED: Reduced from 1.0 to 0.1
            "request_timeout": 10,
            "max_retries": 3,
            "max_search_queries": 5,
            "skip_validation": False,
            "skip_verification": False,
            "skip_reasoning": False,
            "description": "Comprehensive deep search with maximum accuracy"
        },
        "moderate": {
            "max_results_per_search": 10,  # OPTIMIZED: Increased from 3 to 10
            "max_content_length": 2000,
            "max_research_iterations": 2,
            "enable_iterative_research": False,  # OPTIMIZED: Disabled for faster execution
            "rate_limit_delay": 0.1,  # OPTIMIZED: Reduced from 0.5 to 0.1
            "request_timeout": 7,
            "max_retries": 2,
            "max_search_queries": 3,
            "skip_validation": False,
            "skip_verification": False,
            "skip_reasoning": True,
            "description": "Balanced search with good accuracy and speed"
        },
        "quick": {
            "max_results_per_search": 10,  # OPTIMIZED: Increased from 2 to 10
            "max_content_length": 1200,
            "max_research_iterations": 1,
            "enable_iterative_research": False,
            "rate_limit_delay": 0.1,  # OPTIMIZED: Reduced from 0.2 to 0.1
            "request_timeout": 5,
            "max_retries": 1,
            "max_search_queries": 2,
            "skip_validation": False,
            "skip_verification": True,
            "skip_reasoning": True,
            "description": "Fast search for quick answers"
        },
        "sla": {
            "max_results_per_search": 10,  # OPTIMIZED: Increased from 1 to 10
            "max_content_length": 800,
            "max_research_iterations": 0,
            "enable_iterative_research": False,
            "rate_limit_delay": 0.1,
            "request_timeout": 3,
            "max_retries": 1,
            "max_search_queries": 1,
            "skip_validation": False,
            "skip_verification": True,
            "skip_reasoning": True,
            "description": "Ultra-fast SLA-compliant search"
        }
    }
    """dict: Search mode configurations with different parameters"""

    @classmethod
    def get_llm_providers(cls, environ: Mapping[str, str] | None = None) -> tuple[LLMProvider, ...]:
        """Return configured providers in priority order without exposing secrets."""
        env = os.environ if environ is None else environ
        provider_order = env.get("LLM_PROVIDER_ORDER", cls.LLM_PROVIDER_ORDER)
        names = [name.strip().lower() for name in provider_order.split(",") if name.strip()]

        candidates = {
            "openai": LLMProvider(
                name="openai",
                api_key=env.get("OPENAI_API_KEY", cls.OPENAI_API_KEY).strip(),
                model=env.get("OPENAI_MODEL", cls.OPENAI_MODEL).strip() or cls.OPENAI_MODEL,
            ),
            "nvidia": LLMProvider(
                name="nvidia",
                api_key=env.get("NVIDIA_API_KEY", cls.NVIDIA_API_KEY).strip(),
                model=env.get("NVIDIA_MODEL", cls.NVIDIA_MODEL).strip() or cls.NVIDIA_MODEL,
                base_url="https://integrate.api.nvidia.com/v1",
            ),
            "groq": LLMProvider(
                name="groq",
                api_key=env.get("GROQ_API_KEY", cls.GROQ_API_KEY).strip(),
                model=env.get("GROQ_MODEL", cls.GROQ_MODEL).strip() or cls.GROQ_MODEL,
                base_url="https://api.groq.com/openai/v1",
            ),
        }

        # Ignore unknown names and duplicate entries, while preserving configured order.
        providers = []
        seen = set()
        for name in names:
            if name in candidates and name not in seen:
                seen.add(name)
                provider = candidates[name]
                if provider.api_key:
                    providers.append(provider)
        return tuple(providers)

    @classmethod
    def get_search_settings(cls, search_mode: str) -> SearchSettings:
        """Build isolated settings for one search request."""
        mode = cls.SEARCH_MODES.get(search_mode, cls.SEARCH_MODES["deep"])
        return SearchSettings(
            max_results_per_search=mode["max_results_per_search"],
            max_content_length=mode["max_content_length"],
            max_research_iterations=mode["max_research_iterations"],
            enable_iterative_research=mode["enable_iterative_research"],
            rate_limit_delay=mode["rate_limit_delay"],
            request_timeout=mode["request_timeout"],
            max_retries=mode["max_retries"],
        )

    @classmethod
    def default_search_settings(cls) -> SearchSettings:
        """Return settings equivalent to the legacy global defaults."""
        return SearchSettings(
            max_results_per_search=cls.MAX_RESULTS_PER_SEARCH,
            max_content_length=cls.MAX_CONTENT_LENGTH,
            max_research_iterations=cls.MAX_RESEARCH_ITERATIONS,
            enable_iterative_research=cls.ENABLE_ITERATIVE_RESEARCH,
            rate_limit_delay=cls.RATE_LIMIT_DELAY,
            request_timeout=cls.REQUEST_TIMEOUT,
            max_retries=cls.MAX_RETRIES,
        )
    
    MAX_SOURCES_PER_DOMAIN_FINAL = 5    # Allow more sources per domain in final result
    """int: Maximum sources allowed from same domain in final aggregated results"""
    
    MAX_TOTAL_SOURCES = 10  # OPTIMIZED: Increased from 8 to 10 for more comprehensive results
    """int: Maximum total number of sources to analyze across all searches"""
    
    # Iterative research settings
    MAX_RESEARCH_ITERATIONS = 2          # Maximum number of research rounds
    """int: Maximum number of iterative research rounds to perform"""
    
    ENABLE_ITERATIVE_RESEARCH = False    # OPTIMIZED: Disabled by default for faster execution
    """bool: Whether to enable multi-round iterative research for deeper analysis"""
    
    # Quality filtering settings
    MIN_RELEVANCE_SCORE = 0.35          # Minimum relevance score to include a source (increased for better quality)
    """float: Minimum relevance score (0.0-1.0) required to include a source in results"""
    
    ENABLE_AI_RELEVANCE_CHECK = True     # Enable AI-based relevance verification
    """bool: Whether to use AI to verify source relevance to query before including"""
    
    # Blacklisted domains (low-quality sources to exclude)
    BLACKLISTED_DOMAINS = {
        # Dictionaries and vocabulary sites
        'merriam-webster.com',
        'dictionary.com',
        'thesaurus.com',
        'vocabulary.com',
        'yourdictionary.com',
        'collinsdictionary.com',
        'macmillandictionary.com',
        'oxfordlearnersdictionaries.com',
        'ldoceonline.com',
        'thefreedictionary.com',
        
        # Generic content farms and low-quality sites
        'ehow.com',
        'answers.com',
        'ask.com',
        'chacha.com',
        'wiki.answers.com',
        
        # Social media and forums (can be unreliable)
        'reddit.com',
        'quora.com',
        'pinterest.com',
        'tumblr.com',
        'medium.com',  # Can have unverified content
        
        # Commercial/promotional sites
        'amazon.com',
        'ebay.com',
        'walmart.com',
        'target.com',
        
        # Generic community sites
        'discussions.apple.com',
        'support.apple.com',
        'community.microsoft.com',
        
        # Translation and language sites
        'translate.google.com',
        'linguee.com',
        'reverso.net',
        
        # Other low-quality sources
        'wikihow.com',
        'thoughtco.com',
        'reference.com',
    }
    """set: Domain names to exclude from search results (dictionaries, spam sites, etc.)"""


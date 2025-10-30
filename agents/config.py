"""
Configuration for Academic Research Paper Generator
"""

import os


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
    # GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyB23DLvZZEhF6wHvI9Ir0pg1MHfNfJVoyA")
    # MODEL_NAME = "gemini-2.5-flash"  # Free tier model
    
    # OpenAI API Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-api-key-here")
    """str: OpenAI API key loaded from environment variable OPENAI_API_KEY"""
    
    MODEL_NAME = "gpt-5-nano-2025-08-07"  # Valid OpenAI model
    """str: The OpenAI model name to use for all LLM operations"""
    
    MAX_RESULTS_PER_SEARCH = 2  # Increased for more comprehensive search
    """int: Maximum number of search results to retrieve per search query"""
    
    MAX_CONTENT_LENGTH = 2000  # Increased for better content extraction
    """int: Maximum character length for extracted content from web pages"""
    
    REQUEST_TIMEOUT = 10  # Increased timeout for better content extraction
    """int: HTTP request timeout in seconds for web scraping"""
    
    MAX_RETRIES = 3
    """int: Maximum number of retries for failed HTTP requests"""

    # Free tier rate limits (slightly slower for parallel searches)
    RATE_LIMIT_DELAY = 1.0  # Slightly faster for more sources
    """float: Delay in seconds between API calls to respect rate limits"""

    # Domain diversity limits - increased for more sources
    MAX_SOURCES_PER_DOMAIN_PER_TERM = 2  # Allow more sources per domain per term
    """int: Maximum sources allowed from same domain for a single search term"""

    # Search Mode Configurations
    SEARCH_MODES = {
        "deep": {
            "max_results_per_search": 5,
            "max_content_length": 3000,
            "max_research_iterations": 3,
            "enable_iterative_research": True,
            "rate_limit_delay": 1.0,
            "request_timeout": 10,
            "max_retries": 3,
            "max_search_queries": 5,
            "skip_validation": False,
            "skip_verification": False,
            "skip_reasoning": False,
            "description": "Comprehensive deep search with maximum accuracy"
        },
        "moderate": {
            "max_results_per_search": 3,
            "max_content_length": 2000,
            "max_research_iterations": 2,
            "enable_iterative_research": True,
            "rate_limit_delay": 0.5,
            "request_timeout": 7,
            "max_retries": 2,
            "max_search_queries": 3,
            "skip_validation": False,
            "skip_verification": False,
            "skip_reasoning": True,
            "description": "Balanced search with good accuracy and speed"
        },
        "quick": {
            "max_results_per_search": 2,
            "max_content_length": 1200,
            "max_research_iterations": 1,
            "enable_iterative_research": False,
            "rate_limit_delay": 0.2,
            "request_timeout": 5,
            "max_retries": 1,
            "max_search_queries": 2,
            "skip_validation": False,
            "skip_verification": True,
            "skip_reasoning": True,
            "description": "Fast search for quick answers"
        },
        "sla": {
            "max_results_per_search": 1,
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
    
    MAX_SOURCES_PER_DOMAIN_FINAL = 5    # Allow more sources per domain in final result
    """int: Maximum sources allowed from same domain in final aggregated results"""
    
    MAX_TOTAL_SOURCES = 8               # Maximum total sources to analyze (reduced for performance)
    """int: Maximum total number of sources to analyze across all searches"""
    
    # Iterative research settings
    MAX_RESEARCH_ITERATIONS = 2          # Maximum number of research rounds
    """int: Maximum number of iterative research rounds to perform"""
    
    ENABLE_ITERATIVE_RESEARCH = True     # Enable/disable iterative research
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


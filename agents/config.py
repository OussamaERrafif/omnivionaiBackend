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
    
    MAX_SOURCES_PER_DOMAIN_FINAL = 5    # Allow more sources per domain in final result
    """int: Maximum sources allowed from same domain in final aggregated results"""
    
    MAX_TOTAL_SOURCES = 8               # Maximum total sources to analyze (reduced for performance)
    """int: Maximum total number of sources to analyze across all searches"""
    
    # Iterative research settings
    MAX_RESEARCH_ITERATIONS = 2          # Maximum number of research rounds
    """int: Maximum number of iterative research rounds to perform"""
    
    ENABLE_ITERATIVE_RESEARCH = True     # Enable/disable iterative research
    """bool: Whether to enable multi-round iterative research for deeper analysis"""
    
    # LLM Batch Processing Configuration
    SUMMARIZATION_BATCH_SIZE = 2         # Reduced from 3 for stability
    """int: Number of sources to process in parallel during summarization"""
    
    VERIFICATION_BATCH_SIZE = 2          # Reduced from 4 for stability
    """int: Number of claims to process in parallel during verification"""


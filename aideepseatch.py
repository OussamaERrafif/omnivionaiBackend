"""
AI Deep Search - Academic Research Paper Generator with Multi-Agent System.

This is the main entry point for the command-line interface of AI Deep Search.
It provides an interactive console application for executing research queries
and generating academic research papers with comprehensive citations.

The system uses a multi-agent architecture powered by OpenAI's language models
to perform deep research across the web, synthesize findings, verify facts,
and generate properly cited research papers.

Features:
- Interactive CLI for research queries
- Multi-agent research pipeline (validation, analysis, research, etc.)
- Comprehensive citation tracking
- Markdown and JSON output formats
- Custom filename support for saving results
- Trust-based source evaluation

Usage:
    python aideepseatch.py
    
Requirements:
    - OpenAI API key set in environment variable OPENAI_API_KEY
    - All dependencies from requirements.txt installed
"""

import os
import json
import asyncio
import datetime

# Import from agents package
from agents import Orchestrator, Config

# Trusted domains system
from trusted_domains import TrustedDomains


async def main():
    """
    Main entry point for the interactive research application.
    
    Provides an interactive command-line interface for:
    - Entering research queries
    - Viewing example queries
    - Executing multi-agent research pipeline
    - Saving results in markdown and JSON formats
    - Custom filename support
    
    The function runs in a loop, processing queries until the user exits.
    Each query is processed through the full research pipeline and results
    are saved to disk.
    
    Environment Requirements:
        OPENAI_API_KEY: Must be set to a valid OpenAI API key
        
    Interactive Commands:
        - Enter any research question to begin research
        - Type 'quit', 'exit', or 'q' to exit the application
    """

    # Setup
    print("🎓 Academic Research Paper Generator")
    print("📚 Multi-Agent Deep Search with Citation Tracking")
    print("=" * 60)

    # Check API key
    # Old Google API key validation (commented out)
    # if Config.GOOGLE_API_KEY == "your-api-key-here":
    #     print("\n⚠️  Please set your GOOGLE_API_KEY environment variable!")
    #     print("   Get a free API key from: https://makersuite.google.com/app/apikey")
    #     print("\n   Example: export GOOGLE_API_KEY='your-actual-key'")
    #     return
    
    # New OpenAI API key validation
    if Config.OPENAI_API_KEY == "your-openai-api-key-here":
        print("\n⚠️  Please set your OPENAI_API_KEY environment variable!")
        print("   Get a free API key from: https://platform.openai.com/api-keys")
        print("\n   Example: export OPENAI_API_KEY='your-actual-key'")
        return

    # Create orchestrator
    orchestrator = Orchestrator()

    # Example queries
    example_queries = [
        "What are the latest developments in quantum computing in 2024?",
        "How does photosynthesis work in plants?",
        "What are the health benefits of meditation?",
    ]

    print("\n📌 Example queries:")
    for i, q in enumerate(example_queries, 1):
        print(f"   {i}. {q}")

    # Interactive mode
    while True:
        print("\n" + "=" * 50)
        query = input("\n🔍 Enter your search query (or 'quit' to exit): ").strip()

        if query.lower() in ['quit', 'exit', 'q']:
            print("\n👋 Goodbye!")
            break

        if not query:
            print("⚠️  Please enter a valid query!")
            continue

        try:
            # Execute search
            result = await orchestrator.search(query)

            # Save additional copies with custom names (optional)
            save_custom = input("\n💾 Save additional copy with custom filename? (y/n): ").strip().lower()
            if save_custom == 'y':
                custom_name = input("Enter filename (without .md extension): ").strip()
                if custom_name:
                    custom_filename = f"{custom_name}.md"
                    try:
                        with open(custom_filename, 'w', encoding='utf-8') as f:
                            f.write(result.markdown_content)
                        print(f"✅ Custom research paper saved as: {custom_filename}")
                    except Exception as e:
                        print(f"⚠️  Could not save custom file: {e}")

                # Also save JSON version
                json_filename = f"{custom_name}_data.json" if custom_name else f"search_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                try:
                    with open(json_filename, 'w', encoding='utf-8') as f:
                        json.dump({
                            'query': query,
                            'answer': result.answer,
                            'markdown_content': result.markdown_content,
                            'citations': [
                                {
                                    'url': c.url,
                                    'title': c.title,
                                    'section': c.section,
                                    'relevance': c.relevance_score
                                } for c in result.citations
                            ],
                            'confidence': result.confidence_score,
                            'timestamp': datetime.now().isoformat()
                        }, f, indent=2, ensure_ascii=False)
                    print(f"✅ Research data saved as: {json_filename}")
                except Exception as e:
                    print(f"⚠️  Could not save JSON file: {e}")

        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Please try again or check your internet connection.")


# ============================================
# Run the Application
# ============================================

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())

"""
INSTALLATION INSTRUCTIONS:
==========================

1. Install required packages:
   # Old Google API packages (commented out)
   # pip install langchain langchain-google-genai beautifulsoup4 requests duckduckgo-search aiohttp
   
   # New OpenAI API packages
   pip install langchain langchain-openai beautifulsoup4 requests duckduckgo-search aiohttp

2. Get your OpenAI API key:
   # Old Google/Gemini API setup (commented out)
   # - Visit: https://makersuite.google.com/app/apikey
   # - Create a new API key
   # - Set it as environment variable:
   #   export GOOGLE_API_KEY='your-api-key-here'
   
   # New OpenAI API setup
   - Visit: https://platform.openai.com/api-keys
   - Create a new API key
   - Set it as environment variable:
     export OPENAI_API_KEY='your-api-key-here'

3. Run the system:
   python multi_agent_search.py

FEATURES:
=========
✅ OpenAI API (gpt-3.5-turbo) - replaced Gemini API
✅ Free web search (DuckDuckGo)
✅ Precise citation tracking
✅ Section-level source attribution
✅ Confidence scoring
✅ Rate limiting for API tier
✅ Async processing for efficiency
✅ Save results to JSON

CUSTOMIZATION:
=============
- Adjust Config class parameters
- Modify agent prompts for specific domains
- Add custom search sources
- Implement caching for repeated queries
- Add more sophisticated ranking algorithms
"""


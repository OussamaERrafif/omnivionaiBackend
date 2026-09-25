"""
Test script to verify search quality improvements.
Run this to test if the filtering is working correctly.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.research_agent import ResearchAgent
from app.agents.config import Config

async def run_search_quality():
    """Test search quality with various queries"""
    
    print("=" * 70)
    print("SEARCH QUALITY TEST")
    print("=" * 70)
    
    # Test queries that previously gave poor results
    test_queries = [
        {
            "main_topic": "black holes",
            "search_terms": ["black holes", "black hole physics", "event horizon"],
            "expected_domains": ["nasa.gov", "eso.org", "space.com", "nature.com"]
        },
        {
            "main_topic": "quantum computing",
            "search_terms": ["quantum computing", "qubit technology", "quantum algorithms"],
            "expected_domains": ["nature.com", "science.org", "arxiv.org", "ibm.com"]
        }
    ]
    
    agent = ResearchAgent()
    
    for i, test in enumerate(test_queries, 1):
        print(f"\n{'=' * 70}")
        print(f"TEST {i}: {test['main_topic'].upper()}")
        print(f"{'=' * 70}\n")
        
        print(f"Search terms: {', '.join(test['search_terms'])}")
        print(f"Expected trusted domains: {', '.join(test['expected_domains'])}")
        print(f"\nExecuting search...\n")
        
        try:
            sources = await agent.process(test)
            
            # Analyze results
            print(f"\n{'─' * 70}")
            print(f"RESULTS ANALYSIS")
            print(f"{'─' * 70}\n")
            
            print(f"Total sources found: {len(sources)}")
            
            # Count trusted vs untrusted
            trusted = [s for s in sources if s.is_trusted]
            untrusted = [s for s in sources if not s.is_trusted]
            
            print(f"  - Trusted sources: {len(trusted)} ({len(trusted)/len(sources)*100:.1f}%)")
            print(f"  - Untrusted sources: {len(untrusted)} ({len(untrusted)/len(sources)*100:.1f}%)")
            
            # Check for blacklisted domains
            blacklisted_found = []
            for source in sources:
                domain = source.domain.lower()
                if any(bad in domain for bad in Config.BLACKLISTED_DOMAINS):
                    blacklisted_found.append(domain)
            
            if blacklisted_found:
                print(f"\n  ⚠️ WARNING: Found {len(blacklisted_found)} blacklisted domains:")
                for domain in blacklisted_found:
                    print(f"     - {domain}")
            else:
                print(f"\n  ✅ No blacklisted domains found")
            
            # Check average relevance score
            avg_relevance = sum(s.relevance_score for s in sources) / len(sources) if sources else 0
            print(f"\n  Average relevance score: {avg_relevance:.2%}")
            print(f"  Minimum relevance score: {min(s.relevance_score for s in sources):.2%}")
            print(f"  Maximum relevance score: {max(s.relevance_score for s in sources):.2%}")
            
            # Display top sources
            print(f"\n{'─' * 70}")
            print(f"TOP 5 SOURCES")
            print(f"{'─' * 70}\n")
            
            for i, source in enumerate(sources[:5], 1):
                trust_icon = "🛡️" if source.is_trusted else "⚠️"
                print(f"{i}. {trust_icon} {source.title[:50]}...")
                print(f"   Domain: {source.domain}")
                print(f"   Relevance: {source.relevance_score:.2%} | Trust: {source.trust_score}/100")
                print(f"   Category: {source.trust_category}")
                print()
            
            # Check for expected domains
            found_expected = []
            for source in sources:
                for expected in test['expected_domains']:
                    if expected in source.domain.lower():
                        found_expected.append(expected)
                        break
            
            if found_expected:
                print(f"✅ Found {len(found_expected)} expected trusted domains: {', '.join(found_expected)}")
            else:
                print(f"⚠️ No expected trusted domains found")
            
            # Check for quality issues
            print(f"\n{'─' * 70}")
            print(f"QUALITY CHECK")
            print(f"{'─' * 70}\n")
            
            issues = []
            
            # Check for dictionary content
            dictionary_words = ['definition', 'dictionary', 'thesaurus', 'meaning of']
            for source in sources:
                if any(word in source.title.lower() for word in dictionary_words):
                    issues.append(f"Possible dictionary content: {source.title}")
            
            # Check for foreign language
            foreign_indicators = ['auteur:', 'última', 'letzte']
            for source in sources:
                if any(indicator in source.content.lower() for indicator in foreign_indicators):
                    issues.append(f"Possible foreign language: {source.title}")
            
            if issues:
                print("⚠️ Quality issues found:")
                for issue in issues:
                    print(f"   - {issue}")
            else:
                print("✅ No quality issues detected")
            
        except Exception as e:
            print(f"❌ Error during search: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'=' * 70}")
    print("TEST COMPLETE")
    print(f"{'=' * 70}\n")

if __name__ == "__main__":
    # Run the test
    asyncio.run(run_search_quality())

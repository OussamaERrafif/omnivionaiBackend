"""
Configuration checker and tuning guide for search quality settings.
Shows current settings and provides recommendations.
"""

from agents.config import Config
from trusted_domains import TrustedDomains

def display_config():
    """Display current configuration and recommendations"""
    
    print("=" * 80)
    print(" " * 20 + "SEARCH QUALITY CONFIGURATION")
    print("=" * 80)
    
    # Quality Settings
    print("\n📊 QUALITY SETTINGS")
    print("─" * 80)
    print(f"Minimum Relevance Score:     {Config.MIN_RELEVANCE_SCORE}")
    print(f"   Recommendation: 0.30-0.40 (Higher = stricter, fewer but better sources)")
    print(f"   Current: {'✅ Good' if 0.30 <= Config.MIN_RELEVANCE_SCORE <= 0.40 else '⚠️ Consider adjusting'}")
    
    print(f"\nAI Relevance Check:           {Config.ENABLE_AI_RELEVANCE_CHECK}")
    print(f"   Recommendation: True (Filters off-topic sources, slight performance cost)")
    print(f"   Current: {'✅ Enabled' if Config.ENABLE_AI_RELEVANCE_CHECK else '⚠️ Disabled'}")
    
    # Search Settings
    print("\n🔍 SEARCH SETTINGS")
    print("─" * 80)
    print(f"Max Results per Search:       {Config.MAX_RESULTS_PER_SEARCH}")
    print(f"   Recommendation: 2-5 (More = better coverage but slower)")
    
    print(f"\nMax Total Sources:            {Config.MAX_TOTAL_SOURCES}")
    print(f"   Recommendation: 8-15 (More = comprehensive but slower AI processing)")
    
    print(f"\nIterative Research:           {Config.ENABLE_ITERATIVE_RESEARCH}")
    print(f"   Recommendation: True for deep research, False for quick answers")
    
    print(f"\nMax Research Iterations:      {Config.MAX_RESEARCH_ITERATIONS}")
    print(f"   Recommendation: 2-3 (More = deeper but much slower)")
    
    # Domain Diversity
    print("\n🌐 DOMAIN DIVERSITY")
    print("─" * 80)
    print(f"Max Sources per Domain (search): {Config.MAX_SOURCES_PER_DOMAIN_PER_TERM}")
    print(f"   Recommendation: 2-3 (Prevents single-domain bias)")
    
    print(f"\nMax Sources per Domain (final):  {Config.MAX_SOURCES_PER_DOMAIN_FINAL}")
    print(f"   Recommendation: 3-5 (Balance between depth and diversity)")
    
    # Blacklist
    print("\n🚫 BLACKLISTED DOMAINS")
    print("─" * 80)
    print(f"Total blacklisted domains:    {len(Config.BLACKLISTED_DOMAINS)}")
    print(f"\nCategories blocked:")
    
    categories = {
        "Dictionaries": ['dictionary', 'thesaurus', 'vocabulary'],
        "Forums": ['reddit', 'quora', 'discussions', 'community'],
        "Commercial": ['amazon', 'ebay', 'walmart'],
        "Translation": ['translate', 'linguee', 'reverso'],
        "Low-quality": ['wikihow', 'answers', 'ask.com']
    }
    
    for category, keywords in categories.items():
        count = sum(1 for domain in Config.BLACKLISTED_DOMAINS 
                   if any(kw in domain for kw in keywords))
        print(f"   - {category}: {count} domains")
    
    # Trusted Domains
    print("\n🛡️ TRUSTED DOMAINS")
    print("─" * 80)
    
    all_trusted = TrustedDomains.get_all_trusted_domains()
    print(f"Total trusted domains:        {len(all_trusted)}")
    
    trust_categories = {
        "Academic & Research": TrustedDomains.ACADEMIC_DOMAINS,
        "Government": TrustedDomains.GOVERNMENT_DOMAINS,
        "Scientific Publishers": TrustedDomains.SCIENCE_DOMAINS,
        "Established Media": TrustedDomains.MEDIA_DOMAINS,
        "Technology": TrustedDomains.TECH_DOMAINS,
        "Educational": TrustedDomains.EDUCATIONAL_DOMAINS,
        "Fact-Checking": TrustedDomains.FACTCHECK_DOMAINS
    }
    
    print("\nBy category:")
    for category, domains in trust_categories.items():
        print(f"   - {category}: {len(domains)} domains")
    
    # Trust Scores
    print("\n📈 TRUST SCORES")
    print("─" * 80)
    for flag, score in TrustedDomains.TRUST_FLAGS.items():
        category_name = TrustedDomains._get_category_name(flag)
        print(f"   {score}/100 - {category_name}")
    
    # Performance Settings
    print("\n⚡ PERFORMANCE SETTINGS")
    print("─" * 80)
    print(f"Request Timeout:              {Config.REQUEST_TIMEOUT}s")
    print(f"   Recommendation: 10-15s (Higher = more reliable but slower)")
    
    print(f"\nRate Limit Delay:             {Config.RATE_LIMIT_DELAY}s")
    print(f"   Recommendation: 0.5-2.0s (Prevents rate limiting)")
    
    print(f"\nMax Content Length:           {Config.MAX_CONTENT_LENGTH} chars")
    print(f"   Recommendation: 2000-5000 (More = better context but slower)")
    
    # Recommendations Summary
    print("\n" + "=" * 80)
    print(" " * 25 + "TUNING RECOMMENDATIONS")
    print("=" * 80)
    
    recommendations = []
    
    if Config.MIN_RELEVANCE_SCORE < 0.30:
        recommendations.append("⚠️ Consider increasing MIN_RELEVANCE_SCORE to 0.35 for better quality")
    
    if not Config.ENABLE_AI_RELEVANCE_CHECK:
        recommendations.append("💡 Enable AI_RELEVANCE_CHECK to filter off-topic sources")
    
    if Config.MAX_TOTAL_SOURCES < 8:
        recommendations.append("💡 Consider increasing MAX_TOTAL_SOURCES to 10-15 for more comprehensive results")
    
    if Config.MAX_RESEARCH_ITERATIONS > 3:
        recommendations.append("⚠️ Iterations > 3 may be very slow, consider reducing")
    
    if recommendations:
        print("\n📝 Suggestions:")
        for rec in recommendations:
            print(f"   {rec}")
    else:
        print("\n✅ Configuration looks good!")
    
    # Quick adjustment guide
    print("\n" + "=" * 80)
    print(" " * 28 + "QUICK TUNING GUIDE")
    print("=" * 80)
    print("\n🎯 For HIGHER QUALITY (stricter filtering):")
    print("   - Increase MIN_RELEVANCE_SCORE to 0.40-0.45")
    print("   - Enable ENABLE_AI_RELEVANCE_CHECK = True")
    print("   - Add more domains to BLACKLISTED_DOMAINS")
    
    print("\n📚 For MORE COMPREHENSIVE (more sources):")
    print("   - Increase MAX_TOTAL_SOURCES to 15-20")
    print("   - Increase MAX_RESULTS_PER_SEARCH to 5-7")
    print("   - Enable ENABLE_ITERATIVE_RESEARCH = True")
    
    print("\n⚡ For FASTER SEARCHES:")
    print("   - Disable ENABLE_ITERATIVE_RESEARCH")
    print("   - Reduce MAX_RESEARCH_ITERATIONS to 1")
    print("   - Reduce MAX_TOTAL_SOURCES to 5-8")
    print("   - Disable ENABLE_AI_RELEVANCE_CHECK")
    
    print("\n🎯 For BALANCED (recommended):")
    print("   - MIN_RELEVANCE_SCORE = 0.35")
    print("   - ENABLE_AI_RELEVANCE_CHECK = True")
    print("   - MAX_TOTAL_SOURCES = 10")
    print("   - ENABLE_ITERATIVE_RESEARCH = True")
    print("   - MAX_RESEARCH_ITERATIONS = 2")
    
    print("\n" + "=" * 80)
    print()

if __name__ == "__main__":
    display_config()

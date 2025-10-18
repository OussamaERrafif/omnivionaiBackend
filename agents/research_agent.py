"""
Research Agent for Academic Research Paper Generator
"""

import asyncio
import hashlib
import json
from typing import List, Dict, Any

import requests
from bs4 import BeautifulSoup
from langchain.prompts import PromptTemplate
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from urllib.parse import urlparse

from trusted_domains import TrustedDomains

from .base_agent import BaseAgent
from .config import Config
from .data_models import SourceMetadata


class ResearchAgent(BaseAgent):
    """
    Performs web research and extracts content with comprehensive citation metadata.
    
    This agent is responsible for the core research activities including:
    - Performing web searches using DuckDuckGo
    - Extracting and parsing content from web pages
    - Scoring content relevance using multi-factor analysis
    - Tracking source metadata for proper citation
    - Managing domain diversity to ensure varied sources
    - Applying trust-based ranking to prioritize reliable sources
    
    The agent uses an advanced relevance scoring algorithm that considers:
    - Keyword matching (exact and partial)
    - Content quality and length
    - Title and section relevance
    - Keyword density and diversity
    - Content structure indicators
    - Domain trust scores from TrustedDomains
    
    Attributes:
        search_wrapper (DuckDuckGoSearchAPIWrapper): Web search API wrapper
    """

    def __init__(self):
        """Initialize the research agent with search capabilities."""
        super().__init__("Research")
        self.search_wrapper = DuckDuckGoSearchAPIWrapper()

    def _calculate_advanced_relevance_score(self, content: str, keywords: List[str], section_name: str, title: str, url: str) -> float:
        """
        Calculate comprehensive relevance score for content using multiple quality factors.
        
        This method uses a sophisticated scoring algorithm that evaluates content based on:
        1. Keyword matching (exact and partial matches)
        2. Content length and quality
        3. Title and section relevance
        4. Keyword density (avoiding spam)
        5. Keyword diversity (multiple aspects covered)
        6. Content structure (academic language indicators)
        7. Domain trust score (boosting reliable sources)
        
        Args:
            content (str): The extracted content text
            keywords (List[str]): Keywords to match against
            section_name (str): Name of the section containing the content
            title (str): Page/document title
            url (str): Source URL for trust evaluation
            
        Returns:
            float: Relevance score between 0.0 and 1.0, with higher scores indicating
                   better relevance and quality. Trusted domains receive score boosts.
        """
        if not content or not keywords:
            return 0.0

        content_lower = content.lower()
        section_lower = section_name.lower()
        title_lower = title.lower()

        # Base keyword matching score (0.0 to 1.0) - more generous scoring
        exact_matches = sum(1 for kw in keywords if kw.lower() in content_lower)
        partial_matches = sum(1 for kw in keywords for part in kw.lower().split() if part in content_lower and part not in kw.lower())
        
        # Give credit for both exact and partial matches
        total_matches = exact_matches + (partial_matches * 0.5)
        base_score = min(1.0, total_matches / len(keywords)) if keywords else 0.0
        
        # Boost base score slightly to be less conservative  
        base_score = min(1.0, base_score * 1.2)

        # Content quality factors
        quality_multiplier = 1.0

        # 1. Content length factor (prefer substantial content, less penalty for short)
        content_length = len(content.strip())
        if content_length < 50:
            quality_multiplier *= 0.6  # Less harsh penalty for very short content
        elif content_length < 200:
            quality_multiplier *= 0.85  # Less harsh penalty for short content
        elif content_length > 1000:
            quality_multiplier *= 1.3  # Substantial content gets bigger boost

        # 2. Title/section relevance bonus
        title_section_bonus = 0.0
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in title_lower:
                title_section_bonus += 0.15  # Title match is very valuable
            if kw_lower in section_lower:
                title_section_bonus += 0.10  # Section match is valuable

        # 3. Keyword density factor (avoid keyword stuffing, prefer natural distribution)
        total_words = len(content.split())
        if total_words > 0:
            keyword_density = exact_matches / total_words
            if keyword_density > 0.1:  # Too dense = likely spam
                quality_multiplier *= 0.5
            elif keyword_density > 0.05:  # Good density
                quality_multiplier *= 1.1

        # 4. Multiple keyword presence bonus (content covering multiple aspects)
        unique_keywords_found = len(set(kw.lower() for kw in keywords if kw.lower() in content_lower))
        partial_keywords_found = len(set(kw.lower() for kw in keywords for part in kw.lower().split() if part in content_lower))
        total_unique_found = max(unique_keywords_found, partial_keywords_found * 0.5)
        
        if total_unique_found > 1:
            diversity_bonus = min(0.3, (total_unique_found - 1) * 0.1)  # Increased bonus
        else:
            diversity_bonus = 0.0

        # 5. Content structure indicators (prefer well-structured content)
        structure_bonus = 0.0
        if any(indicator in content_lower for indicator in ['according to', 'research shows', 'study found']):
            structure_bonus += 0.05
        if any(indicator in content_lower for indicator in ['however', 'therefore', 'furthermore']):
            structure_bonus += 0.03  # Analytical language

        # 6. TRUST MULTIPLIER - Apply trust scoring to boost trusted sources
        trust_info = TrustedDomains.get_domain_trust_info(url)
        trust_multiplier = 1.0

        if trust_info['is_trusted']:
            # Boost trusted domains based on their trust score
            trust_score_normalized = trust_info['trust_score'] / 100  # 0.75 to 0.95
            trust_multiplier = 1.0 + (trust_score_normalized * 0.5)  # 1.375 to 1.475 multiplier
            print(f"   ✅ TRUSTED SOURCE: {trust_info['domain']} ({trust_info['category']}) - Trust boost: {trust_multiplier:.2f}x")

        # Combine all factors with trust multiplier
        final_score = ((base_score * quality_multiplier) + title_section_bonus + diversity_bonus + structure_bonus) * trust_multiplier

        # Ensure score stays within reasonable bounds
        return min(1.0, max(0.0, final_score))

    def search_web(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Perform web search using DuckDuckGo search API.
        
        Uses the free DuckDuckGo search service to find relevant web pages.
        Includes fallback mechanism with different parameters if initial search fails.
        
        Args:
            query (str): Search query string
            max_results (int): Maximum number of results to return (default: 5)
            
        Returns:
            List[Dict]: List of search results, each containing:
                - title: Page title
                - href/link: URL
                - body/snippet: Text excerpt
                
        Note:
            Returns empty list if both primary and fallback searches fail.
        """
        try:
            from ddgs import DDGS

            # Initialize DDGS without context manager for better compatibility
            ddgs = DDGS()
            results = list(ddgs.text(query, max_results=max_results))
            print(f"   Search returned {len(results)} results")
            return results
        except Exception as e:
            print(f"Search error: {e}")
            # Try alternative approach with different parameters
            try:
                from ddgs import DDGS
                ddgs = DDGS()
                results = list(ddgs.text(query, region='us-en', safesearch='moderate', max_results=max_results))
                print(f"   Fallback search returned {len(results)} results")
                return results
            except Exception as e2:
                print(f"Fallback search also failed: {e2}")
                return []

    def extract_content_with_sections(self, url: str, keywords: List[str]) -> List[SourceMetadata]:
        """
        Extract structured content from a URL with section-level tracking.
        
        Scrapes a web page and extracts content organized by sections (h1-h4 headings).
        For each section, extracts paragraphs and calculates relevance scores. Includes
        complete metadata for citation purposes including trust information.
        
        Args:
            url (str): The URL to scrape and extract content from
            keywords (List[str]): Keywords for relevance scoring
            
        Returns:
            List[SourceMetadata]: List of extracted content sections, each with:
                - Full source metadata (URL, title, section, paragraph ID)
                - Content text
                - Relevance score
                - Trust information from TrustedDomains
                
        Note:
            Handles HTTP errors gracefully, returning empty list on failure.
            Respects Config.REQUEST_TIMEOUT and Config.MAX_CONTENT_LENGTH.
        """
        sections = []

        try:
            response = requests.get(url, timeout=Config.REQUEST_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract title
            title = soup.find('title')
            title_text = title.text if title else "Untitled"

            # Extract content by sections
            for idx, heading in enumerate(soup.find_all(['h1', 'h2', 'h3', 'h4'])):
                section_content = []
                section_name = heading.get_text(strip=True)

                # Get content after heading until next heading
                for sibling in heading.find_next_siblings():
                    if sibling.name and sibling.name.startswith('h'):
                        break
                    if sibling.name in ['p', 'ul', 'ol', 'blockquote']:
                        section_content.append(sibling.get_text(strip=True))

                content = ' '.join(section_content)

                # Check relevance - be more lenient, include content with good length or keyword matches
                has_keyword_match = any(kw.lower() in content.lower() for kw in keywords)
                has_partial_match = any(any(part in content.lower() for part in kw.lower().split()) for kw in keywords)
                is_substantial = len(content.strip()) > 100
                
                if content and (is_substantial or has_keyword_match or has_partial_match):
                    # Calculate enhanced relevance score with trust
                    relevance = self._calculate_advanced_relevance_score(content, keywords, section_name, title_text, url)

                    # Get trust information
                    trust_info = TrustedDomains.get_domain_trust_info(url)

                    # Create unique paragraph ID
                    para_id = f"p{idx}_{hashlib.md5(content[:100].encode()).hexdigest()[:8]}"

                    sections.append(SourceMetadata(
                        url=url,
                        title=title_text,
                        section=section_name,
                        paragraph_id=para_id,
                        content=content[:Config.MAX_CONTENT_LENGTH],
                        relevance_score=relevance,
                        trust_flag=trust_info['trust_flag'],
                        trust_score=trust_info['trust_score'],
                        is_trusted=trust_info['is_trusted'],
                        trust_category=trust_info['category'],
                        domain=trust_info['domain']
                    ))

            # If no sections found, try to extract main content
            if not sections:
                main_content = soup.find_all(['p'])
                if main_content:
                    content = ' '.join([p.get_text(strip=True) for p in main_content[:10]])
                    if content:
                        # Calculate relevance for main content too
                        relevance = self._calculate_advanced_relevance_score(content, keywords, "Main Content", title_text, url)

                        # Get trust information
                        trust_info = TrustedDomains.get_domain_trust_info(url)

                        sections.append(SourceMetadata(
                            url=url,
                            title=title_text,
                            section="Main Content",
                            paragraph_id="main",
                            content=content[:Config.MAX_CONTENT_LENGTH],
                            relevance_score=relevance,
                            trust_flag=trust_info['trust_flag'],
                            trust_score=trust_info['trust_score'],
                            is_trusted=trust_info['is_trusted'],
                            trust_category=trust_info['category'],
                            domain=trust_info['domain']
                        ))

        except Exception as e:
            print(f"Error extracting from {url}: {e}")

        return sections

    async def process(self, query_analysis: Dict[str, Any]) -> List[SourceMetadata]:
        """Process search and extraction with multi-keyword deep search"""
        all_sources = []
        seen_urls = set()

        # Get search terms and main topic
        search_terms = query_analysis.get('search_terms', [])
        main_topic = query_analysis.get('main_topic', '')

        # Optional: Expand search terms semantically using Gemini
        try:
            expansion_prompt = f"""Expand these search terms into related detailed queries for deeper research: {', '.join(search_terms)}

Return ONLY a JSON list of unique, meaningful phrases (max 6 additional terms).
Example format: ["machine learning agent", "autonomous software", "AI system architecture"]"""

            from langchain.prompts import PromptTemplate
            prompt = PromptTemplate(input_variables=["text"], template="{text}")
            chain = prompt | self.llm
            result = await chain.ainvoke({"text": expansion_prompt})
            expansion_text = result.content if hasattr(result, 'content') else str(result)

            # Clean and parse the response
            cleaned_text = expansion_text.strip()
            # Remove markdown code blocks if present
            if "```" in cleaned_text:
                cleaned_text = cleaned_text.split("```")[1] if "```" in cleaned_text else cleaned_text
                cleaned_text = cleaned_text.replace("json", "").strip()

            # Parse expanded terms
            expanded_terms = json.loads(cleaned_text)
            if isinstance(expanded_terms, list):
                # Add expanded terms while avoiding duplicates
                original_terms = [term.lower() for term in search_terms]
                new_terms = [term for term in expanded_terms if isinstance(term, str) and term.lower() not in original_terms]
                search_terms.extend(new_terms[:4])  # Add max 4 new terms
                print(f"   🧩 Expanded search terms: {new_terms[:4]}")

        except Exception as e:
            print(f"   ⚠️ Expansion failed, using original terms: {e}")

        print(f"   🔎 Running {len(search_terms)} searches in parallel...")

        async def search_and_extract(term: str):
            """Inner coroutine: search and extract for one term"""
            try:
                # Run the synchronous search in a thread to avoid blocking
                results = await asyncio.to_thread(self.search_web, term, Config.MAX_RESULTS_PER_SEARCH)
                print(f"   ✅ Found {len(results)} results for: '{term}'")

                local_sources = []
                domain_counts = {}  # Track domains to prevent bias

                # Sort results to prioritize trusted domains
                trusted_results = []
                untrusted_results = []

                for result in results:
                    url = result.get('href') or result.get('link', '')
                    if not url:
                        continue

                    # Check if domain is trusted
                    if TrustedDomains.is_trusted_domain(url):
                        trusted_results.append(result)
                    else:
                        untrusted_results.append(result)

                # Process trusted sources first, then untrusted
                prioritized_results = trusted_results + untrusted_results
                print(f"   🛡️ Found {len(trusted_results)} trusted and {len(untrusted_results)} other sources")

                for result in prioritized_results:
                    url = result.get('href') or result.get('link', '')
                    if not url or url in seen_urls:
                        continue

                    # Extract domain for bias prevention
                    from urllib.parse import urlparse
                    domain = urlparse(url).netloc.lower()

                    # Check trust status
                    is_trusted = TrustedDomains.is_trusted_domain(url)

                    # More lenient limits for trusted domains
                    max_per_domain = Config.MAX_SOURCES_PER_DOMAIN_PER_TERM * 2 if is_trusted else Config.MAX_SOURCES_PER_DOMAIN_PER_TERM

                    if domain_counts.get(domain, 0) >= max_per_domain:
                        trust_indicator = "🛡️" if is_trusted else "⚠️"
                        print(f"   {trust_indicator} Skipping {domain} (domain limit reached)")
                        continue

                    seen_urls.add(url)
                    domain_counts[domain] = domain_counts.get(domain, 0) + 1

                    # Run content extraction in thread pool as well since it involves web requests
                    sources = await asyncio.to_thread(self.extract_content_with_sections, url, search_terms)
                    local_sources.extend(sources)

                    trust_indicator = "🛡️ TRUSTED" if is_trusted else "📄"
                    print(f"   {trust_indicator} Extracted {len(sources)} sections from: {domain}")

                    await asyncio.sleep(Config.RATE_LIMIT_DELAY)

                return local_sources

            except Exception as e:
                print(f"   ⚠️ Error searching '{term}': {e}")
                return []

        # Run searches for each term concurrently
        tasks = [search_and_extract(term) for term in search_terms]
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results (handle exceptions)
        for result_list in results_lists:
            if isinstance(result_list, list):
                all_sources.extend(result_list)
            else:
                print(f"   ⚠️ Task failed: {result_list}")

        # Deduplicate based on (url, paragraph_id) pairs
        print(f"   🧹 Deduplicating {len(all_sources)} total extracted sections...")
        unique_sources = []
        seen_paragraphs = set()
        for src in all_sources:
            key = (src.url, src.paragraph_id)
            if key not in seen_paragraphs:
                seen_paragraphs.add(key)
                unique_sources.append(src)

        # Enhanced final selection with trust prioritization
        from urllib.parse import urlparse
        final_sources = []
        domain_final_counts = {}
        trusted_counts = {}

        # Separate trusted and untrusted sources
        trusted_sources = [src for src in unique_sources if src.is_trusted]
        untrusted_sources = [src for src in unique_sources if not src.is_trusted]

        # Sort each group by relevance score
        trusted_sources.sort(key=lambda x: x.relevance_score, reverse=True)
        untrusted_sources.sort(key=lambda x: x.relevance_score, reverse=True)

        print(f"   🛡️ Trust analysis: {len(trusted_sources)} trusted, {len(untrusted_sources)} untrusted sources")

        # First pass: Select trusted sources (more lenient domain limits)
        for src in trusted_sources:
            domain = src.domain or urlparse(src.url).netloc.lower()
            trusted_limit = Config.MAX_SOURCES_PER_DOMAIN_FINAL * 2  # Allow more trusted sources per domain

            if domain_final_counts.get(domain, 0) < trusted_limit:
                final_sources.append(src)
                domain_final_counts[domain] = domain_final_counts.get(domain, 0) + 1
                trusted_counts[domain] = trusted_counts.get(domain, 0) + 1

                if len(final_sources) >= Config.MAX_TOTAL_SOURCES * 0.5:  # Reserve 50% for trusted
                    break

        # Second pass: Fill remaining slots with best untrusted sources
        remaining_slots = Config.MAX_TOTAL_SOURCES - len(final_sources)
        for src in untrusted_sources:
            if remaining_slots <= 0:
                break

            domain = src.domain or urlparse(src.url).netloc.lower()
            if domain_final_counts.get(domain, 0) < Config.MAX_SOURCES_PER_DOMAIN_FINAL:
                final_sources.append(src)
                domain_final_counts[domain] = domain_final_counts.get(domain, 0) + 1
                remaining_slots -= 1

        # Third pass: Ensure minimum sources (relaxed domain limits if needed)
        MIN_SOURCES = 15
        if len(final_sources) < MIN_SOURCES:
            print(f"   📊 Only {len(final_sources)} sources selected, adding more to reach minimum of {MIN_SOURCES}...")
            # Combine all remaining sources and sort by relevance
            remaining_sources = []
            for src in unique_sources:
                if src not in final_sources:
                    remaining_sources.append(src)

            remaining_sources.sort(key=lambda x: x.relevance_score, reverse=True)

            # Add sources until we reach minimum, with relaxed domain limits
            for src in remaining_sources:
                if len(final_sources) >= MIN_SOURCES:
                    break
                domain = src.domain or urlparse(src.url).netloc.lower()
                # Allow up to double the normal domain limit for minimum guarantee
                if domain_final_counts.get(domain, 0) < Config.MAX_SOURCES_PER_DOMAIN_FINAL * 2:
                    final_sources.append(src)
                    domain_final_counts[domain] = domain_final_counts.get(domain, 0) + 1

        print(f"   🧠 Final selection: {len(final_sources)} sources from {len(domain_final_counts)} domains")
        print(f"   🛡️ Trusted sources: {sum(trusted_counts.values())} from {len(trusted_counts)} trusted domains")

        # Log trust distribution
        if trusted_counts:
            print(f"   📊 Trusted domains: {dict(list(trusted_counts.items())[:3])}")

        return final_sources

    async def process_iterative(self, query_analysis: Dict[str, Any], max_iterations: int = 3, progress_callback=None) -> List[SourceMetadata]:
        """Iterative research: search → analyze → refine → repeat"""
        all_sources = []
        search_history = set()
        
        print(f"\n🔄 Starting iterative research with {max_iterations} rounds...")
        
        # Helper function for progress with detailed info
        async def emit_iteration_progress(round_num: int, status: str, details: str, search_queries=None, sites=None, sources_count=None):
            if progress_callback:
                progress = 30.0 + (round_num / max_iterations * 10.0)  # 30-40% range
                await progress_callback(
                    "research", 
                    status, 
                    f"Round {round_num}: {details}", 
                    progress,
                    search_queries=search_queries,
                    sites_visited=sites,
                    sources_found=sources_count
                )
        
        # Round 1: Initial search with original query
        print(f"\n📍 Round 1: Initial search")
        initial_terms = query_analysis.get('search_terms', [])[:5]
        
        # Don't emit the search queries here - orchestrator already showed them in query_analysis phase
        await emit_iteration_progress(
            1, 
            "started", 
            "Searching across the web with initial queries",
            search_queries=None,  # Don't duplicate - already shown by orchestrator
            sites=None,
            sources_count=0
        )
        
        initial_sources = await self.process(query_analysis)
        all_sources.extend(initial_sources)
        
        # Get unique domains from initial sources
        initial_domains = list(set(s.domain for s in initial_sources if hasattr(s, 'domain') and s.domain))[:10]
        
        await emit_iteration_progress(
            1, 
            "completed", 
            f"Found {len(initial_sources)} sources from {len(initial_domains)} domains",
            search_queries=None,  # Clear queries on completion
            sites=initial_domains,
            sources_count=len(initial_sources)
        )
        
        # Track what we've searched
        original_terms = set(query_analysis.get('search_terms', []))
        search_history.update(original_terms)
        
        # Iterative rounds
        for iteration in range(2, max_iterations + 1):
            print(f"\n📍 Round {iteration}: Analyzing previous results and searching deeper...")
            await emit_iteration_progress(
                iteration, 
                "started", 
                "Analyzing results to find deeper insights",
                search_queries=None,
                sites=None,
                sources_count=len(all_sources)
            )
            
            # Extract new search directions from current sources
            new_search_terms = await self._extract_follow_up_topics(all_sources, search_history, query_analysis)
            
            if not new_search_terms:
                print("   ✅ No new search directions found, research complete")
                await emit_iteration_progress(
                    iteration, 
                    "completed", 
                    "Research complete - comprehensive coverage achieved",
                    search_queries=None,
                    sites=None,
                    sources_count=len(all_sources)
                )
                break
            
            # Report the new search terms
            await emit_iteration_progress(
                iteration, 
                "searching", 
                f"Exploring {len(new_search_terms)} related topics for deeper insights",
                search_queries=new_search_terms[:5],  # Send as list of questions
                sites=None,
                sources_count=len(all_sources)
            )
            
            # Create modified query analysis for this iteration
            iteration_query = {
                **query_analysis,
                'search_terms': new_search_terms
            }
            
            # Search with new terms
            iteration_sources = await self.process(iteration_query)
            
            # Filter out duplicates and add to collection
            new_sources = []
            existing_urls = {src.url + src.paragraph_id for src in all_sources}
            
            for src in iteration_sources:
                source_key = src.url + src.paragraph_id
                if source_key not in existing_urls:
                    new_sources.append(src)
                    existing_urls.add(source_key)
            
            all_sources.extend(new_sources)
            print(f"   📈 Added {len(new_sources)} new sources from round {iteration}")
            
            # Get unique domains from this iteration
            iter_domains = list(set(s.domain for s in new_sources if hasattr(s, 'domain') and s.domain))[:10]
            
            await emit_iteration_progress(
                iteration, 
                "completed", 
                f"Added {len(new_sources)} sources from {len(iter_domains)} new domains",
                search_queries=None,  # Clear queries on completion
                sites=iter_domains,
                sources_count=len(all_sources)
            )
            
            # Update search history
            search_history.update(new_search_terms)
        
        # Final deduplication and selection
        print(f"\n🎯 Iterative research complete: {len(all_sources)} total sources found")
        return self._final_iterative_selection(all_sources)
    
    async def _extract_follow_up_topics(self, sources: List[SourceMetadata], search_history: set, original_query: Dict[str, Any]) -> List[str]:
        """Extract new search topics from existing sources"""
        if not sources:
            return []
        
        # Sample content from top sources for analysis
        sample_content = []
        for src in sorted(sources, key=lambda x: x.relevance_score, reverse=True)[:10]:
            sample_content.append(f"Title: {src.title}\nSection: {src.section}\nContent: {src.content[:300]}")
        
        combined_content = "\n\n---\n\n".join(sample_content)
        
        prompt = f"""Based on this research content about "{original_query.get('main_topic', '')}", identify 3-5 specific follow-up search topics that would provide deeper insights.

Content analyzed:
{combined_content[:2000]}

Already searched terms: {', '.join(search_history)}

Focus on:
1. Technical details mentioned but not fully explained
2. Related technologies, frameworks, or concepts referenced
3. Specific use cases, applications, or implementations mentioned
4. Key challenges, limitations, or solutions hinted at
5. Important subtopics that need more depth

Return ONLY a JSON list of specific, focused search terms (avoid duplicating already searched terms):
["specific term 1", "specific term 2", ...]"""

        try:
            from langchain.prompts import PromptTemplate
            chain = PromptTemplate(input_variables=["text"], template="{text}") | self.llm
            result = await chain.ainvoke({"text": prompt})
            
            response_text = result.content if hasattr(result, 'content') else str(result)
            
            # Clean and parse response
            cleaned_text = response_text.strip()
            if "```" in cleaned_text:
                cleaned_text = cleaned_text.split("```")[1] if "```" in cleaned_text else cleaned_text
                cleaned_text = cleaned_text.replace("json", "").strip()
            
            follow_up_terms = json.loads(cleaned_text)
            
            if isinstance(follow_up_terms, list):
                # Filter out terms we've already searched and ensure they're strings
                new_terms = []
                for term in follow_up_terms:
                    if isinstance(term, str) and term.lower() not in {s.lower() for s in search_history}:
                        new_terms.append(term)
                
                print(f"   🧩 Identified follow-up topics: {new_terms[:5]}")
                return new_terms[:5]  # Limit to 5 new terms per iteration
                
        except Exception as e:
            print(f"   ⚠️ Follow-up topic extraction failed: {e}")
        
        return []
    
    def _final_iterative_selection(self, all_sources: List[SourceMetadata]) -> List[SourceMetadata]:
        """Select best sources from iterative research with enhanced diversity"""
        if not all_sources:
            return []
        
        # Enhanced selection for iterative results
        from urllib.parse import urlparse
        final_sources = []
        domain_counts = {}
        trusted_counts = {}
        
        # Separate by trust and sort by relevance
        trusted_sources = sorted([src for src in all_sources if src.is_trusted], 
                                key=lambda x: x.relevance_score, reverse=True)
        untrusted_sources = sorted([src for src in all_sources if not src.is_trusted], 
                                  key=lambda x: x.relevance_score, reverse=True)
        
        print(f"   📊 Iterative selection from {len(trusted_sources)} trusted + {len(untrusted_sources)} untrusted sources")
        
        # Generous limits for iterative research
        MAX_ITERATIVE_SOURCES = Config.MAX_TOTAL_SOURCES  # Use the configured max sources
        MAX_PER_DOMAIN_ITERATIVE = Config.MAX_SOURCES_PER_DOMAIN_FINAL * 3
        
        # Select trusted sources first (more generous limits)
        for src in trusted_sources:
            if len(final_sources) >= MAX_ITERATIVE_SOURCES * 0.6:  # 60% can be trusted
                break
                
            domain = src.domain or urlparse(src.url).netloc.lower()
            if domain_counts.get(domain, 0) < MAX_PER_DOMAIN_ITERATIVE:
                final_sources.append(src)
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
                trusted_counts[domain] = trusted_counts.get(domain, 0) + 1
        
        # Fill remaining with untrusted sources
        for src in untrusted_sources:
            if len(final_sources) >= MAX_ITERATIVE_SOURCES:
                break
                
            domain = src.domain or urlparse(src.url).netloc.lower()
            if domain_counts.get(domain, 0) < MAX_PER_DOMAIN_ITERATIVE:
                final_sources.append(src)
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
        
        print(f"   🎯 Final iterative selection: {len(final_sources)} sources from {len(domain_counts)} domains")
        print(f"   🛡️ Including {sum(trusted_counts.values())} trusted sources from {len(trusted_counts)} domains")
        
        return final_sources


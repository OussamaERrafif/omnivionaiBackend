"""
Source Citer Agent for Academic Research Paper Generator
"""

from datetime import datetime
from typing import List
from urllib.parse import urlparse

from .base_agent import BaseAgent
from .data_models import ProcessedContent


class SourceCiterAgent(BaseAgent):
    """
    Formats source citations in academic style with trust and relevance metadata.
    
    This agent generates properly formatted citations for all sources used in the
    research, including trust indicators, relevance scores, and source categorization.
    Citations follow academic standards and include metadata helpful for evaluating
    source quality.
    
    Citation format includes:
    - Citation number [1], [2], etc.
    - Trust indicator (🛡️ for trusted sources)
    - Source title
    - Source category (Academic, Government, etc.)
    - Section information
    - URL
    - Relevance score
    - Trust score
    """

    def __init__(self):
        """Initialize the source citer agent."""
        super().__init__("SourceCiter")

    def format_citations(self, summaries: List[ProcessedContent]) -> str:
        """
        Format citations in academic style with trust and relevance information.
        
        Generates a formatted list of citations with metadata about each source including
        trust level, relevance, and categorization.
        
        Args:
            summaries (List[ProcessedContent]): List of processed content with source metadata
            
        Returns:
            str: Formatted citation list with one citation per line, numbered sequentially
            
        Example output:
            [1] 🛡️ Quantum Computing Advances. (Academic & Research Institution). 
                Retrieved from: https://example.edu/. Relevance: 95%. Trust Score: 98/100.
        """
        citations = []

        for i, summary in enumerate(summaries, 1):
            source = summary.source

            # Use trust category if available, otherwise fall back to domain classification
            if hasattr(source, 'trust_category') and source.trust_category:
                source_type = source.trust_category
                trust_indicator = f"🛡️ " if source.is_trusted else ""
            else:
                # Fallback to old classification
                from urllib.parse import urlparse
                domain = urlparse(source.url).netloc.lower()

                if 'wikipedia' in domain:
                    source_type = "Encyclopedia"
                elif any(x in domain for x in ['edu', 'gov', 'org']):
                    source_type = "Institutional"
                elif any(x in domain for x in ['journal', 'academic', 'research']):
                    source_type = "Academic"
                else:
                    source_type = "Web Resource"
                trust_indicator = ""

            # Create enhanced citation with trust information
            title = source.title if source.title else "Untitled Document"
            section_info = f", Section: {source.section}" if source.section else ""

            # Add trust score if available
            trust_info = ""
            if hasattr(source, 'trust_score') and source.trust_score:
                trust_info = f" Trust Score: {source.trust_score}/100."

            # Format: [1] 🛡️ Title. (Academic & Research Institution), Section: Name. Retrieved from: URL. Relevance: 85% Trust Score: 95/100
            citation = f"[{i}] {trust_indicator}{title}. ({source_type}){section_info}. Retrieved from: {source.url}. Relevance: {source.relevance_score:.0%}.{trust_info}"

            citations.append(citation)

        return "\n".join(citations)

    def format_sources_section(self, summaries: List[ProcessedContent]) -> str:
        """Create a formatted References section organized by trust category"""
        if not summaries:
            return ""

        sources_section = "\n## References\n\n"

        # Group sources by trust category first
        trust_categories = {}
        web_resources = []

        for i, summary in enumerate(summaries, 1):
            source = summary.source

            # Use trust category if available
            if hasattr(source, 'trust_category') and source.trust_category and source.is_trusted:
                category = source.trust_category
                if category not in trust_categories:
                    trust_categories[category] = []
            else:
                # Fallback for untrusted sources
                category = "Web Resources"

            # Format academic reference
            title = source.title if source.title else "Untitled Document"
            section_info = f" Section: {source.section}." if source.section else ""
            timestamp = source.timestamp[:10] if source.timestamp else "n.d."

            trust_indicator = "🛡️ " if getattr(source, 'is_trusted', False) else ""
            reference = f"[{i}] {trust_indicator}{title}.{section_info} Retrieved {timestamp}, from {source.url}"

            if category in trust_categories:
                trust_categories[category].append(reference)
            else:
                web_resources.append(reference)

        # Output trusted sources first, grouped by category
        for category in sorted(trust_categories.keys()):
            if trust_categories[category]:
                sources_section += f"### {category}\n"
                for ref in trust_categories[category]:
                    sources_section += f"{ref}\n"
                sources_section += "\n"

        # Output other web resources last
        if web_resources:
            sources_section += "### Web Resources\n"
            for ref in web_resources:
                sources_section += f"{ref}\n"
            sources_section += "\n"

        return sources_section

    def create_markdown_research_paper(self, query: str, answer: str, summaries: List[ProcessedContent], confidence: float) -> str:
        """Create a complete markdown research paper with trust metrics"""
        sources_section = self.format_sources_section(summaries)
        citations_section = self.format_citations(summaries)

        # Count unique sources and domains
        unique_sources = len(set(s.source.url for s in summaries))
        from urllib.parse import urlparse
        unique_domains = len(set(urlparse(s.source.url).netloc for s in summaries))

        # Calculate trust statistics
        trusted_sources = sum(1 for s in summaries if getattr(s.source, 'is_trusted', False))
        trust_percentage = (trusted_sources / len(summaries) * 100) if summaries else 0

        # Get trust category distribution
        trust_categories = {}
        for s in summaries:
            if hasattr(s.source, 'trust_category') and getattr(s.source, 'is_trusted', False):
                category = s.source.trust_category
                trust_categories[category] = trust_categories.get(category, 0) + 1

        # Calculate average trust score
        trust_scores = [getattr(s.source, 'trust_score', 50) for s in summaries]
        avg_trust_score = sum(trust_scores) / len(trust_scores) if trust_scores else 50

        markdown_content = f"""**Research Date**: {datetime.now().strftime('%B %d, %Y')}
**Confidence Level**: {confidence:.1%}
**Sources Analyzed**: {len(summaries)} sections from {unique_sources} unique sources
**Domain Diversity**: {unique_domains} different domains
**Trust Assessment**: {trusted_sources}/{len(summaries)} sources from verified institutions ({trust_percentage:.1f}%)
**Average Trust Score**: {avg_trust_score:.0f}/100

---

{answer}

{sources_section}
---

*Generated by Academic Research Paper Generator with Multi-Agent Deep Search*
*Powered by LangChain and Gemini AI*
"""
        return markdown_content


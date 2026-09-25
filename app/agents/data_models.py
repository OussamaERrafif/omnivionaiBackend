"""
Data Models for Academic Research Paper Generator
"""

from typing import List
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SourceMetadata:
    """
    Comprehensive metadata for tracking and citing research sources.
    
    This class stores all information about a source including its content,
    relevance, trust level, and citation details. Used throughout the system
    to maintain proper attribution and source tracking.
    
    Attributes:
        url (str): The URL of the source
        title (str): The title of the source document/page
        section (str): The specific section within the source where content was found
        paragraph_id (str): Unique identifier for the paragraph/content block
        content (str): The actual extracted content from the source
        relevance_score (float): Computed relevance score (0.0-1.0) based on query match
        timestamp (str): ISO format timestamp of when the source was retrieved
        trust_flag (str): Trust verification status (e.g., "verified", "unverified")
        trust_score (int): Numeric trust score (0-100) based on domain reputation
        is_trusted (bool): Whether the source is from a trusted domain
        trust_category (str): Category of trust (e.g., "Academic Source", "Verified Media")
        domain (str): The domain name of the source
        images (List[dict]): List of images extracted from the source with url, alt text, and context
    """
    url: str
    title: str = ""
    section: str = ""
    paragraph_id: str = ""
    content: str = ""
    relevance_score: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    # Trust information
    trust_flag: str = "unverified"
    trust_score: int = 50
    is_trusted: bool = False
    trust_category: str = "Unverified Source"
    domain: str = ""
    images: List[dict] = field(default_factory=list)


@dataclass
class ProcessedContent:
    """
    Processed and summarized content with full citation metadata.
    
    Represents content that has been extracted, summarized, and linked to its source.
    Used in the intermediate stages of the research pipeline.
    
    Attributes:
        summary (str): The summarized/processed content
        source (SourceMetadata): Complete metadata about the source of this content
        confidence_score (float): Confidence score (0.0-1.0) in the accuracy of the summary
    """
    summary: str
    source: SourceMetadata
    confidence_score: float = 0.0


@dataclass
class FinalAnswer:
    """
    Complete research result with answer, citations, and formatted output.
    
    The final output of the research pipeline containing the synthesized answer,
    all source citations, confidence metrics, and formatted markdown content.
    
    Attributes:
        answer (str): The synthesized answer to the research query
        citations (List[SourceMetadata]): All sources cited in the answer
        confidence_score (float): Overall confidence score (0.0-1.0) for the answer
        # markdown_content (str): Formatted markdown version of the complete research paper - COMMENTED OUT FOR PERFORMANCE
    """
    answer: str
    citations: List[SourceMetadata]
    confidence_score: float = 0.0
    # markdown_content: str = ""  # COMMENTED OUT FOR PERFORMANCE


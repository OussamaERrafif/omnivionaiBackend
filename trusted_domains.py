"""
Trusted Domains Configuration for AI Research System.

This module manages trusted domain verification for the AI Deep Search system.
It provides a comprehensive database of high-trust domains across multiple categories
(academic, government, scientific publishers, etc.) and utilities for evaluating
source credibility.

Based on high-trust domain categories with verified reputation standards.
"""

import re
from typing import Dict, List, Set, Optional, Any

class TrustedDomains:
    """
    Configuration and utilities for trusted domain verification.
    
    This class maintains categorized lists of trusted domains and provides methods
    for evaluating source credibility. Domains are organized into categories such as
    academic institutions, government sites, peer-reviewed publishers, established
    media, and fact-checking organizations.
    
    Each category has an associated trust score (0-100) that reflects the general
    reliability of sources from that category. The class provides methods to:
    - Check if a domain is trusted
    - Get trust scores and categories for URLs
    - Classify sources based on domain patterns
    
    Trust Categories:
    - Academic & Research Institutions (95): .edu domains, major universities
    - Government & Intergovernmental (90): .gov domains, UN, WHO, etc.
    - Scientific Publishers (90): Nature, Science, IEEE, etc.
    - Established Media (80): BBC, Reuters, NYT, etc.
    - Technology Documentation (85): Official tech docs, standards organizations
    - Educational Repositories (75): Wikipedia, Khan Academy, etc.
    - Fact-Checking Organizations (85): Snopes, PolitiFact, etc.
    """
    
    # Trust flags and categories
    TRUST_FLAGS = {
        'academic_research_trusted': 95,
        'official_government_trusted': 90,
        'peer_reviewed_science': 90,
        'mainstream_verified_media': 80,
        'technical_documentation_trusted': 85,
        'educational_open_trusted': 75,
        'independent_factcheck_trusted': 85
    }
    
    # Academic & Research Institutions
    ACADEMIC_DOMAINS = {
        # Major Universities (.edu domains)
        'harvard.edu', 'stanford.edu', 'mit.edu', 'berkeley.edu', 'caltech.edu',
        'princeton.edu', 'yale.edu', 'columbia.edu', 'uchicago.edu', 'cornell.edu',
        'upenn.edu', 'duke.edu', 'dartmouth.edu', 'brown.edu', 'northwestern.edu',
        'vanderbilt.edu', 'rice.edu', 'georgetown.edu', 'carnegiemellon.edu',
        
        # International Universities
        'ox.ac.uk', 'cam.ac.uk', 'imperial.ac.uk', 'ucl.ac.uk', 'kcl.ac.uk',
        'ed.ac.uk', 'manchester.ac.uk', 'bristol.ac.uk', 'warwick.ac.uk',
        'u-tokyo.ac.jp', 'kyoto-u.ac.jp', 'utoronto.ca', 'mcgill.ca', 'ubc.ca',
        'anu.edu.au', 'sydney.edu.au', 'melbourne.edu.au', 'unsw.edu.au',
        'ethz.ch', 'epfl.ch', 'sorbonne-universite.fr', 'ens.psl.eu'
    }
    
    # Government and Intergovernmental Sites
    GOVERNMENT_DOMAINS = {
        # U.S. Government (.gov domains)
        'nasa.gov', 'nih.gov', 'nsf.gov', 'nist.gov', 'cdc.gov', 'fda.gov',
        'epa.gov', 'noaa.gov', 'usgs.gov', 'doe.gov', 'energy.gov',
        'data.gov', 'census.gov', 'whitehouse.gov', 'state.gov', 'treasury.gov',
        'justice.gov', 'defense.gov', 'va.gov', 'sec.gov', 'ftc.gov',
        
        # International Organizations
        'europa.eu', 'un.org', 'who.int', 'unesco.org', 'unicef.org',
        'imf.org', 'worldbank.org', 'oecd.org', 'wto.org', 'iaea.org',
        'esa.int', 'cern.ch', 'ecb.europa.eu', 'eurostat.ec.europa.eu'
    }
    
    # Scientific & Technical Publishers
    SCIENCE_DOMAINS = {
        'nature.com', 'science.org', 'sciencedirect.com', 'springer.com',
        'wiley.com', 'taylorfrancis.com', 'plos.org', 'mdpi.com',
        'acm.org', 'ieee.org', 'arxiv.org', 'biorxiv.org', 'medrxiv.org',
        'pubmed.ncbi.nlm.nih.gov', 'ncbi.nlm.nih.gov', 'doi.org',
        'jstor.org', 'sage.com', 'cambridge.org', 'oxfordjournals.org',
        'aaas.org', 'cell.com', 'thelancet.com', 'nejm.org', 'bmj.com'
    }
    
    # Established News & Media Organizations
    MEDIA_DOMAINS = {
        'bbc.com', 'reuters.com', 'apnews.com', 'nytimes.com', 'theguardian.com',
        'washingtonpost.com', 'wsj.com', 'npr.org', 'pbs.org', 'cnn.com',
        'abc.go.com', 'cbsnews.com', 'nbcnews.com', 'usatoday.com',
        'financialtimes.com', 'bloomberg.com', 'economist.com', 'theatlantic.com',
        'newyorker.com', 'time.com', 'newsweek.com', 'foreignaffairs.com',
        'ft.com', 'telegraph.co.uk', 'independent.co.uk', 'sky.com'
    }
    
    # Technology & Industry Authorities
    TECH_DOMAINS = {
        'openai.com', 'google.ai', 'ai.google', 'deepmind.com', 'microsoft.com',
        'aws.amazon.com', 'cloud.google.com', 'azure.microsoft.com',
        'developer.mozilla.org', 'w3.org', 'tensorflow.org', 'pytorch.org',
        'github.com', 'stackoverflow.com', 'docker.com', 'kubernetes.io',
        'apache.org', 'oracle.com', 'ibm.com', 'intel.com', 'nvidia.com',
        'apple.com', 'meta.com', 'facebook.com', 'twitter.com', 'linkedin.com',
        'salesforce.com', 'adobe.com', 'cisco.com', 'vmware.com'
    }
    
    # Knowledge Repositories & Educational Nonprofits
    EDUCATIONAL_DOMAINS = {
        'wikipedia.org', 'britannica.com', 'khanacademy.org', 'coursera.org',
        'edx.org', 'udacity.com', 'futurelearn.com', 'mitopencourseware.org',
        'ted.com', 'tedmed.com', 'smithsonianmag.com', 'nationalgeographic.com',
        'scientificamerican.com', 'newscientist.com', 'livescience.com',
        'howstuffworks.com', 'explainxkcd.com', 'stackexchange.com'
    }
    
    # Independent Fact-Checking Organizations
    FACTCHECK_DOMAINS = {
        'snopes.com', 'politifact.com', 'factcheck.org', 'fullfact.org',
        'afp.com', 'checkyourfact.com', 'truthorfiction.com', 'leadstories.com',
        'mediabiasfactcheck.com', 'allsides.com', 'factchecker.in'
    }
    
    # Domain patterns for automatic detection
    DOMAIN_PATTERNS = {
        'academic_research_trusted': [
            r'\.edu$',  # U.S. educational institutions
            r'\.ac\.uk$',  # UK academic institutions
            r'\.edu\.au$',  # Australian universities
            r'\.ac\.jp$',  # Japanese academic institutions
            r'\.ca$'  # Some Canadian institutions
        ],
        'official_government_trusted': [
            r'\.gov$',  # U.S. government
            r'\.gov\.uk$',  # UK government
            r'\.gov\.au$',  # Australian government
            r'\.gc\.ca$',  # Canadian government
            r'\.europa\.eu$',  # European Union
            r'\.int$'  # International organizations
        ]
    }
    
    @classmethod
    def get_domain_trust_info(cls, url: str) -> Dict[str, Any]:
        """
        Analyze a URL and return comprehensive trust information.
        
        Checks the URL's domain against trusted domain lists and patterns to determine
        its trust level and category. Returns detailed trust metadata that can be used
        for source ranking, filtering, and citation formatting.
        
        Args:
            url (str): The full URL to analyze
            
        Returns:
            Dict[str, Any]: Trust information containing:
                - trust_flag (str): Internal trust category identifier
                - trust_score (int): Numerical trust score (0-100)
                - is_trusted (bool): Whether the domain is in a trusted category
                - category (str): Human-readable category name
                - domain (str): Extracted domain name
                
        Examples:
            >>> TrustedDomains.get_domain_trust_info("https://stanford.edu/research")
            {'trust_flag': 'academic_research_trusted', 'trust_score': 95, 
             'is_trusted': True, 'category': 'Academic & Research Institution',
             'domain': 'stanford.edu'}
             
            >>> TrustedDomains.get_domain_trust_info("https://example.com/page")
            {'trust_flag': 'unverified', 'trust_score': 50, 'is_trusted': False,
             'category': 'Unverified Source', 'domain': 'example.com'}
        """
        domain = cls._extract_domain(url)
        
        # Check specific domains first
        for category, domains in [
            ('academic_research_trusted', cls.ACADEMIC_DOMAINS),
            ('official_government_trusted', cls.GOVERNMENT_DOMAINS),
            ('peer_reviewed_science', cls.SCIENCE_DOMAINS),
            ('mainstream_verified_media', cls.MEDIA_DOMAINS),
            ('technical_documentation_trusted', cls.TECH_DOMAINS),
            ('educational_open_trusted', cls.EDUCATIONAL_DOMAINS),
            ('independent_factcheck_trusted', cls.FACTCHECK_DOMAINS)
        ]:
            if domain in domains:
                return {
                    'trust_flag': category,
                    'trust_score': cls.TRUST_FLAGS[category],
                    'is_trusted': True,
                    'category': cls._get_category_name(category),
                    'domain': domain
                }
        
        # Check domain patterns
        for category, patterns in cls.DOMAIN_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, domain):
                    return {
                        'trust_flag': category,
                        'trust_score': cls.TRUST_FLAGS[category],
                        'is_trusted': True,
                        'category': cls._get_category_name(category),
                        'domain': domain
                    }
        
        # Not a trusted domain
        return {
            'trust_flag': 'unverified',
            'trust_score': 50,  # Neutral score
            'is_trusted': False,
            'category': 'Unverified Source',
            'domain': domain
        }
    
    @classmethod
    def _extract_domain(cls, url: str) -> str:
        """
        Extract the domain name from a full URL.
        
        Parses the URL and extracts the domain (netloc), removing the 'www.' prefix
        if present. Returns lowercase domain for consistent comparison.
        
        Args:
            url (str): Full URL to parse
            
        Returns:
            str: Extracted domain name (lowercase, without www.), or empty string on error
        """
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Remove www. prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except:
            return ""
    
    @classmethod
    def _get_category_name(cls, trust_flag: str) -> str:
        """
        Convert internal trust flag to human-readable category name.
        
        Args:
            trust_flag (str): Internal trust category identifier
            
        Returns:
            str: Human-readable category name suitable for display
        """
        category_names = {
            'academic_research_trusted': 'Academic & Research Institution',
            'official_government_trusted': 'Government & Intergovernmental',
            'peer_reviewed_science': 'Scientific & Technical Publisher',
            'mainstream_verified_media': 'Established News & Media',
            'technical_documentation_trusted': 'Technology & Industry Authority',
            'educational_open_trusted': 'Educational & Knowledge Repository',
            'independent_factcheck_trusted': 'Independent Fact-Checking Organization'
        }
        return category_names.get(trust_flag, 'Unknown Category')
    
    @classmethod
    def get_all_trusted_domains(cls) -> Set[str]:
        """Get all trusted domains as a set"""
        all_domains = set()
        all_domains.update(cls.ACADEMIC_DOMAINS)
        all_domains.update(cls.GOVERNMENT_DOMAINS)
        all_domains.update(cls.SCIENCE_DOMAINS)
        all_domains.update(cls.MEDIA_DOMAINS)
        all_domains.update(cls.TECH_DOMAINS)
        all_domains.update(cls.EDUCATIONAL_DOMAINS)
        all_domains.update(cls.FACTCHECK_DOMAINS)
        return all_domains
    
    @classmethod
    def is_trusted_domain(cls, url: str) -> bool:
        """Quick check if a domain is trusted"""
        return cls.get_domain_trust_info(url)['is_trusted']
    
    @classmethod
    def get_trust_score(cls, url: str) -> int:
        """Get numerical trust score for a domain"""
        return cls.get_domain_trust_info(url)['trust_score']


# Example usage and testing
if __name__ == "__main__":
    # Test some domains
    test_urls = [
        "https://harvard.edu/research/ai",
        "https://nasa.gov/news/climate",
        "https://nature.com/articles/science",
        "https://bbc.com/news/technology",
        "https://stackoverflow.com/questions/python",
        "https://randomwebsite.com/info"
    ]
    
    for url in test_urls:
        trust_info = TrustedDomains.get_domain_trust_info(url)
        print(f"URL: {url}")
        print(f"Trust Info: {trust_info}")
        print("-" * 50)


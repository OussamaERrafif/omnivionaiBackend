"""
Image Analyzer Agent for Academic Research Paper Generator
"""

from typing import List, Dict
from .base_agent import BaseAgent


class ImageAnalyzerAgent(BaseAgent):
    """
    Analyzes images and generates AI-powered descriptions for contextual placement.
    
    This agent examines images extracted from web pages and uses AI to generate
    detailed descriptions that help determine the most relevant section for each image
    in the research paper.
    
    Key responsibilities:
    - Analyze image metadata (alt text, title, context)
    - Generate AI descriptions of what the image depicts
    - Determine image relevance to research topics
    - Enhance image metadata for better placement decisions
    """

    def __init__(self):
        """Initialize the image analyzer agent."""
        super().__init__("ImageAnalyzer")

    async def analyze_images(self, images: List[Dict], query: str, main_topic: str) -> List[Dict]:
        """
        Analyze images and generate AI descriptions for better contextual placement.
        
        Args:
            images (List[Dict]): List of image dictionaries with url, alt, title, context
            query (str): The research query/question
            main_topic (str): The main topic being researched
            
        Returns:
            List[Dict]: Enhanced images with ai_description and relevance_keywords
        """
        if not images:
            return []
        
        print(f"   🖼️  Analyzing {len(images)} images with AI...")
        
        enhanced_images = []
        filtered_count = 0
        
        for i, img in enumerate(images, 1):
            try:
                # Minimal filter: Only skip the most obvious non-content images
                alt_lower = (img.get('alt', '') + ' ' + img.get('title', '')).lower()
                
                # Only skip very obvious indicators (reduced list)
                skip_indicators = ['icon', 'pixel', 'tracker', '1x1']
                
                if any(indicator in alt_lower for indicator in skip_indicators):
                    print(f"   🚫 Skipped image {i}: Icon/tracker")
                    filtered_count += 1
                    continue
                
                # Build context from existing metadata
                existing_context = f"""
Image Metadata:
- Alt Text: {img.get('alt', 'N/A')[:150]}
- Title: {img.get('title', 'N/A')[:100]}
- Context: {img.get('context', 'N/A')[:150]}

Research Topic: {main_topic}
"""
                
                # More lenient AI prompt - focus on usefulness rather than strict matching
                description_prompt = f"""{existing_context}

Analyze this image for a research paper about "{main_topic}".

Is this image potentially USEFUL for understanding {main_topic}? 
- Include diagrams, charts, photos, screenshots, illustrations
- Accept images that help explain concepts, show examples, or visualize data
- Only reject obvious decorative content like logos, icons, or tracking pixels

If USEFUL:
1. Provide a SHORT description (max 10 words) 
2. Provide 2-3 relevant keywords

Format:
RELEVANT: YES/NO
DESCRIPTION: [short description]
KEYWORDS: [keyword1, keyword2, keyword3]"""

                from langchain_core.prompts import PromptTemplate
                prompt = PromptTemplate(input_variables=["text"], template="{text}")
                chain = prompt | self.llm
                result = await chain.ainvoke({"text": description_prompt})
                
                response = result.content if hasattr(result, 'content') else str(result)
                
                # Parse the response
                is_relevant = False
                ai_description = ""
                relevance_keywords = []
                
                lines = response.strip().split('\n')
                for line in lines:
                    if line.startswith('RELEVANT:'):
                        is_relevant = 'YES' in line.upper()
                    elif line.startswith('DESCRIPTION:'):
                        ai_description = line.replace('DESCRIPTION:', '').strip()
                    elif line.startswith('KEYWORDS:'):
                        keywords_str = line.replace('KEYWORDS:', '').strip()
                        keywords_str = keywords_str.strip('[]')
                        relevance_keywords = [kw.strip() for kw in keywords_str.split(',') if kw.strip()][:3]  # Max 3 keywords
                
                # Skip if AI determined it's not relevant
                if not is_relevant or not ai_description:
                    print(f"   🚫 Skipped image {i}: Not relevant to topic")
                    filtered_count += 1
                    continue
                
                # Create enhanced image object
                enhanced_img = {
                    **img,
                    'ai_description': ai_description[:80],  # Limit to 80 chars
                    'relevance_keywords': relevance_keywords,
                    'analyzed': True
                }
                
                enhanced_images.append(enhanced_img)
                
                print(f"   ✅ Analyzed image {i}/{len(images)}: {ai_description[:50]}...")
                
            except Exception as e:
                print(f"   ⚠️  Failed to analyze image {i}: {e}")
                filtered_count += 1
                continue
        
        print(f"   🎯 Kept {len(enhanced_images)} relevant images, filtered out {filtered_count}")
        return enhanced_images

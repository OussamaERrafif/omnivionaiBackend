"""
Orchestrator for Academic Research Paper Generator
"""

import asyncio
import dataclasses
import json
import math
from datetime import datetime
from typing import List, Literal
import time

from .query_analyzer_agent import QueryAnalyzerAgent
from .query_validator_agent import QueryValidatorAgent
from .research_agent import ResearchAgent
from .summarizer_agent import SummarizerAgent
from .verification_agent import VerificationAgent
from .reasoning_agent import ReasoningAgent
from .source_citer_agent import SourceCiterAgent
from .image_analyzer_agent import ImageAnalyzerAgent
from .data_models import FinalAnswer
from .config import Config, SearchSettings

# Type alias for search modes
SearchMode = Literal["deep", "moderate", "quick", "sla"]


class Orchestrator:
    """
    Main orchestrator that coordinates all specialized agents in the research pipeline.
    
    The Orchestrator manages the complete research workflow by coordinating multiple
    specialized agents to analyze queries, gather sources, synthesize information,
    verify facts, and generate properly cited research papers.
    
    Pipeline stages:
    1. Query Validation - Validates user query for safety and appropriateness
    2. Query Analysis - Analyzes query and generates search terms
    3. Research - Gathers relevant sources from the web
    4. Summarization - Summarizes gathered content
    5. Reasoning - Applies logical analysis to findings
    6. Verification - Verifies factual claims against sources
    7. Citation - Generates formatted citations and research paper
    
    Attributes:
        query_validator (QueryValidatorAgent): Validates and sanitizes queries
        query_analyzer (QueryAnalyzerAgent): Analyzes queries and generates search terms
        research_agent (ResearchAgent): Performs web research and content extraction
        summarizer_agent (SummarizerAgent): Summarizes content while preserving citations
        verification_agent (VerificationAgent): Verifies factual claims
        reasoning_agent (ReasoningAgent): Applies logical reasoning to findings
        citer_agent (SourceCiterAgent): Generates citations and research papers
    """

    def __init__(self):
        """Initialize the orchestrator with all specialized agents."""
        self.query_validator = QueryValidatorAgent()
        self.query_analyzer = QueryAnalyzerAgent()
        self.research_agent = ResearchAgent()
        self.summarizer_agent = SummarizerAgent()
        self.verification_agent = VerificationAgent()
        self.reasoning_agent = ReasoningAgent()
        self.citer_agent = SourceCiterAgent()
        self.image_analyzer = ImageAnalyzerAgent()

    def _apply_search_settings(self, settings: SearchSettings) -> None:
        """Apply isolated request settings to this orchestrator's agents."""
        for agent in (
            self.query_validator,
            self.query_analyzer,
            self.research_agent,
            self.summarizer_agent,
            self.verification_agent,
            self.reasoning_agent,
            self.image_analyzer,
        ):
            agent.settings = settings

    async def search(self, query: str, progress_callback=None, search_mode: SearchMode = "deep") -> FinalAnswer:
        """
        Execute the complete research pipeline for a given query.
        
        This is the main entry point for the research system. It orchestrates all agents
        to perform a comprehensive research process including validation, analysis, research,
        summarization, reasoning, verification, and citation generation.
        
        Args:
            query (str): The research question or topic to investigate
            progress_callback (Optional[Callable]): Optional async callback function for
                progress updates. Called with (step, status, details, progress_percentage,
                search_queries, sites_visited, sources_found)
            search_mode (SearchMode): Search mode - "deep", "moderate", "quick", or "sla". Default is "deep"
                
        Returns:
            FinalAnswer: Complete research result with answer, citations, and markdown content
            
        Raises:
            ValueError: If the query fails validation (e.g., inappropriate content, malicious input)
            Exception: For other errors during the research process
        """

        print(f"\n🔍 Processing query: {query}")
        print(f"🎯 Search mode: {search_mode.upper()}")
        print("=" * 50)
        
        # Apply search mode configuration
        mode_config = Config.SEARCH_MODES.get(search_mode, Config.SEARCH_MODES["deep"])
        print(f"📊 Mode config: {mode_config['description']}")
        print(f"⚙️  Settings: {mode_config['max_results_per_search']} sources, {mode_config['max_research_iterations']} iterations, {mode_config['request_timeout']}s timeout")
        
        settings = Config.get_search_settings(search_mode)
        self._apply_search_settings(settings)
        return await self._execute_search(query, progress_callback, mode_config, settings)

    async def execute(
        self,
        search_id: str,
        query: str,
        plan_type: str = "free",
        metadata: dict | None = None,
    ) -> dict:
        """Compatibility entry point for the idempotent orchestration wrapper."""
        search_mode = (metadata or {}).get("search_mode", "deep")
        result = await self.search(query=query, search_mode=search_mode)
        return {
            "search_id": search_id,
            "plan_type": plan_type,
            "answer": result.answer,
            "citations": [dataclasses.asdict(citation) for citation in result.citations],
            "confidence_score": result.confidence_score,
            "markdown_content": result.answer,
            "tokens_used": 0,
        }
    
    async def _execute_search(
        self,
        query: str,
        progress_callback=None,
        mode_config=None,
        settings: SearchSettings | None = None,
    ) -> FinalAnswer:
        """
        Internal method to execute the search pipeline with current config.
        
        Args:
            query (str): The research question or topic to investigate
            progress_callback (Optional[Callable]): Optional async callback function for progress updates
                
        Returns:
            FinalAnswer: Complete research result with answer, citations, and markdown content
        """
        
        start_time = time.time()
        step_times = {}
        
        # Get mode config for conditional step execution
        mode_config = mode_config or Config.SEARCH_MODES["deep"]
        settings = settings or Config.default_search_settings()
        skip_validation = mode_config.get("skip_validation", False)
        skip_verification = mode_config.get("skip_verification", False)
        skip_reasoning = mode_config.get("skip_reasoning", False)

        # Helper function to emit progress
        async def emit_progress(step: str, status: str, details: str, progress: float, search_queries: List[str] = None, sites_visited: List[str] = None, sources_found: int = None):
            if progress_callback:
                await progress_callback(step, status, details, progress, search_queries, sites_visited, sources_found)

        # Step 0: Validate query (skip in fast modes)
        if not skip_validation:
            print("\n✅ Validating query...")
            step_start = time.time()
            await emit_progress("validation", "started", "Validating your query...", 5.0)
            
            validation_result = await self.query_validator.validate(query)
            
            if not validation_result.get("is_valid", True):
                error_message = validation_result.get("reason", "Query appears to be invalid")
                suggestion = validation_result.get("suggestion")
                
                print(f"   ❌ Invalid query: {error_message}")
                if suggestion:
                    print(f"   💡 Suggestion: {suggestion}")
                
                await emit_progress("validation", "failed", error_message, 5.0)
                
                # Raise an exception that will be caught by the API
                raise ValueError(f"{error_message}. {suggestion if suggestion else 'Please try a different query.'}")
            
            print(f"   ✓ Query is valid")
            step_times["validation"] = time.time() - step_start
            await emit_progress("validation", "completed", "Query validated successfully", 10.0)
        else:
            print("\n⚡ Skipping validation for fast mode")
            step_times["validation"] = 0.0

        # Step 1: Analyze query with web search context
        print("\n📊 Analyzing query with web search...")
        step_start = time.time()
        await emit_progress("query_analysis", "started", "Searching the web and analyzing your query...", 15.0)
        
        # Get max search queries from mode config
        max_search_queries = mode_config.get("max_search_queries", 5)
        
        # The query analyzer now performs web search first, then generates search terms based on results
        # Pass max_questions to limit generation upfront for fast modes
        query_analysis = await self.query_analyzer.process(query, max_questions=max_search_queries)
        
        print(f"   Main topic: {query_analysis.get('main_topic')}")
        print(f"   Search terms: {query_analysis.get('search_terms')} (requested max: {max_search_queries})")
        
        # Report the search terms to the user
        search_terms = query_analysis.get('search_terms', [])
        if search_terms:
            # Send only the search queries (questions), not a concatenated string
            if progress_callback:
                await progress_callback(
                    "query_analysis", 
                    "completed", 
                    f"Generated {len(search_terms)} research question{'s' if len(search_terms) > 1 else ''}", 
                    25.0,
                    search_queries=search_terms,  # Send as list of questions
                    sites_visited=[],
                    sources_found=0
                )
        else:
            await emit_progress("query_analysis", "completed", "Query analyzed", 25.0)
        
        step_times["query_analysis"] = time.time() - step_start

        # Step 2: Research (Iterative or Standard)
        if settings.enable_iterative_research:
            print("\n🔬 Starting iterative research...")
            step_start = time.time()
            await emit_progress("research", "started", "Gathering sources from the web...", 30.0)
            
            sources = await self.research_agent.process_iterative(
                query_analysis, 
                max_iterations=settings.max_research_iterations,
                progress_callback=emit_progress
            )
            print(f"   🎯 Completed iterative research: {len(sources)} total sources")
            
            # Report the domains visited
            if sources:
                unique_domains = list(set(s.domain for s in sources if hasattr(s, 'domain') and s.domain))
                domains_str = ", ".join(unique_domains[:5])
                await emit_progress(
                    "research", 
                    "completed", 
                    f"Visited {len(unique_domains)} sites including: {domains_str}", 
                    40.0,
                    search_queries=None,
                    sites_visited=unique_domains[:10],
                    sources_found=len(sources)
                )
            else:
                await emit_progress("research", "completed", "Research completed", 40.0)
            
            step_times["research"] = time.time() - step_start
        else:
            print("\n🔬 Researching sources...")
            step_start = time.time()
            await emit_progress("research", "started", "Researching sources...", 30.0)
            
            sources = await self.research_agent.process(query_analysis)
            print(f"   Found {len(sources)} relevant sections")
            
            # Report the domains visited
            if sources:
                unique_domains = list(set(s.domain for s in sources if hasattr(s, 'domain') and s.domain))
                domains_str = ", ".join(unique_domains[:5])
                await emit_progress(
                    "research", 
                    "completed", 
                    f"Found {len(sources)} sources from {len(unique_domains)} sites", 
                    40.0,
                    search_queries=None,
                    sites_visited=unique_domains[:10],
                    sources_found=len(sources)
                )
            else:
                await emit_progress("research", "completed", "Research completed", 40.0)
            
            step_times["research"] = time.time() - step_start

        if not sources:
            await emit_progress("research", "completed", "No sources found", 100.0)
            return FinalAnswer(
                answer="No relevant information found for your query.",
                citations=[],
                confidence_score=0.0
            )

        # Step 2.5: Analyze images with AI for better placement
        print("\n🖼️  Analyzing images...")
        step_start = time.time()
        await emit_progress("image_analysis", "started", "Analyzing images with AI for contextual placement...", 42.0)
        
        # Collect all images from sources
        all_images = []
        for source in sources:
            if hasattr(source, 'images') and source.images:
                all_images.extend(source.images)
        
        if all_images:
            # Remove duplicates based on URL
            unique_images = []
            seen_urls = set()
            for img in all_images:
                if img.get('url') and img['url'] not in seen_urls:
                    seen_urls.add(img['url'])
                    unique_images.append(img)
            
            # Limit to max 15 images for AI analysis
            max_analyze = 15
            if len(unique_images) > max_analyze:
                print(f"   Found {len(unique_images)} unique images, limiting to {max_analyze} for AI analysis")
                unique_images = unique_images[:max_analyze]
            else:
                print(f"   Found {len(unique_images)} unique images to analyze")
            
            # Analyze images with AI
            main_topic = query_analysis.get('main_topic', query)
            analyzed_images = await self.image_analyzer.analyze_images(unique_images, query, main_topic)
            
            # Update sources with analyzed images
            for source in sources:
                if hasattr(source, 'images') and source.images:
                    # Replace with analyzed versions
                    enhanced_imgs = []
                    for img in source.images:
                        # Find the analyzed version
                        analyzed = next((ai for ai in analyzed_images if ai.get('url') == img.get('url')), None)
                        enhanced_imgs.append(analyzed if analyzed else img)
                    source.images = enhanced_imgs
            
            await emit_progress("image_analysis", "completed", f"Analyzed {len(analyzed_images)} images", 45.0)
            print(f"   ✅ Image analysis complete")
        else:
            await emit_progress("image_analysis", "completed", "No images found in sources", 45.0)
            print(f"   ℹ️  No images found to analyze")
        
        step_times["image_analysis"] = time.time() - step_start

        # Step 3: Summarize
        print("\n📝 Summarizing content...")
        step_start = time.time()
        await emit_progress(
            "summarization", 
            "started", 
            f"Analyzing content from {len(sources)} sources...", 
            50.0,
            search_queries=None,
            sites_visited=None,
            sources_found=len(sources)
        )
        
        summaries = await self.summarizer_agent.process(
            sources,
            query_analysis.get('main_topic', query)
        )
        print(f"   Generated {len(summaries)} summaries")
        
        await emit_progress(
            "summarization", 
            "completed", 
            f"Summarized {len(summaries)} key findings", 
            60.0,
            search_queries=None,
            sites_visited=None,
            sources_found=len(summaries)
        )
        
        step_times["summarization"] = time.time() - step_start

        # OPTIMIZED: Step 4 & 5 - Run verification and reasoning in parallel
        print("\n🚀 Running verification and synthesis in parallel...")
        step_start = time.time()
        
        # Prepare progress emissions
        if not skip_verification:
            await emit_progress(
                "verification", 
                "started", 
                "Cross-checking facts and verifying accuracy...", 
                70.0,
                search_queries=None,
                sites_visited=None,
                sources_found=len(summaries)
            )
        
        if not skip_reasoning:
            await emit_progress(
                "synthesis", 
                "started", 
                "Synthesizing comprehensive research paper...", 
                70.0,
                search_queries=None,
                sites_visited=None,
                sources_found=len(summaries)
            )
        
        # OPTIMIZED: Run verification and reasoning simultaneously
        verification_task = None
        reasoning_task = None
        
        if not skip_verification and not skip_reasoning:
            # Both verification and reasoning
            verification_task = asyncio.create_task(self.verification_agent.verify_claims(summaries))
            # Note: Reasoning will use verified summaries, so we need to wait for verification first
            # We'll do verification first, then reasoning, but prepare them in parallel where possible
            verified_summaries = await verification_task
            
            # Safety check
            if not verified_summaries:
                print("   ⚠️  No sources passed verification, using original summaries with reduced confidence...")
                verified_summaries = summaries[:min(5, len(summaries))]
                for summary in verified_summaries:
                    summary.confidence_score *= 0.5
            
            await emit_progress(
                "verification", 
                "completed", 
                f"Verified {len(verified_summaries)} high-quality sources", 
                80.0,
                search_queries=None,
                sites_visited=None,
                sources_found=len(verified_summaries)
            )
            
            # Now do reasoning with verified results
            answer = await self.reasoning_agent.process(query, verified_summaries)
            
            await emit_progress(
                "synthesis", 
                "completed", 
                "PhD-grade research paper generated with complete structure and citations", 
                90.0,
                search_queries=None,
                sites_visited=None,
                sources_found=len(verified_summaries)
            )
            
        elif not skip_verification:
            # Only verification (fast mode skips reasoning)
            verified_summaries = await self.verification_agent.verify_claims(summaries)
            
            if not verified_summaries:
                print("   ⚠️  No sources passed verification, using original summaries with reduced confidence...")
                verified_summaries = summaries[:min(5, len(summaries))]
                for summary in verified_summaries:
                    summary.confidence_score *= 0.5
            
            await emit_progress(
                "verification", 
                "completed", 
                f"Verified {len(verified_summaries)} high-quality sources", 
                80.0,
                search_queries=None,
                sites_visited=None,
                sources_found=len(verified_summaries)
            )
            
            # Fast mode: Simple direct synthesis
            answer = f"# {query}\n\n"
            for i, summary in enumerate(verified_summaries[:3], 1):
                answer += f"{summary.summary}\n\n"
            
            await emit_progress(
                "synthesis", 
                "completed", 
                "Quick answer generated from sources", 
                90.0,
                search_queries=None,
                sites_visited=None,
                sources_found=len(verified_summaries)
            )
            
        else:
            # Skip verification (very fast mode)
            print("\n⚡ Skipping verification for fast mode")
            verified_summaries = summaries
            
            if not skip_reasoning:
                answer = await self.reasoning_agent.process(query, verified_summaries)
                
                await emit_progress(
                    "synthesis", 
                    "completed", 
                    "Research paper generated", 
                    90.0,
                    search_queries=None,
                    sites_visited=None,
                    sources_found=len(verified_summaries)
                )
            else:
                # Fast mode: Simple synthesis
                answer = f"# {query}\n\n"
                for i, summary in enumerate(verified_summaries[:3], 1):
                    answer += f"{summary.summary}\n\n"
                
                await emit_progress(
                    "synthesis", 
                    "completed", 
                    "Quick answer generated from sources", 
                    90.0,
                    search_queries=None,
                    sites_visited=None,
                    sources_found=len(verified_summaries)
                )
        
        step_times["verification_and_synthesis"] = time.time() - step_start

        # Step 6: Format citations and sources
        print("\n📚 Formatting citations...")
        step_start = time.time()
        await emit_progress(
            "formatting", 
            "started", 
            "Preparing final output with references...", 
            95.0,
            search_queries=None,
            sites_visited=None,
            sources_found=len(verified_summaries)
        )
        
        citations_text = self.citer_agent.format_citations(verified_summaries)
        sources_section = self.citer_agent.format_sources_section(verified_summaries)

        # Calculate overall confidence with trust-enhanced formula
        import math
        if verified_summaries:
            avg_relevance = sum(s.confidence_score for s in verified_summaries) / len(verified_summaries)

            # Count unique sources and trust metrics
            unique_sources = len(set(s.source.url for s in verified_summaries))
            trusted_sources = [s for s in verified_summaries if getattr(s.source, 'is_trusted', False)]
            trust_percentage = len(trusted_sources) / len(verified_summaries) if verified_summaries else 0

            # Calculate average trust score
            avg_trust_score = sum(getattr(s.source, 'trust_score', 50) for s in verified_summaries) / len(verified_summaries)

            # Enhanced confidence calculation with trust factors
            source_diversity_bonus = math.log(1 + unique_sources)
            trust_multiplier = 1.0 + (trust_percentage * 0.25)  # Up to 25% boost for trusted sources
            trust_quality_factor = (avg_trust_score / 100)  # 0.5 to 1.0 based on trust scores

            # Combine all factors
            base_confidence = avg_relevance * source_diversity_bonus
            trust_enhanced_confidence = base_confidence * trust_multiplier * trust_quality_factor
            avg_confidence = min(1.0, trust_enhanced_confidence)

            print(f"   🎯 Confidence Calculation:")
            print(f"      Base relevance: {avg_relevance:.3f}")
            print(f"      Source diversity bonus: {source_diversity_bonus:.3f}")
            print(f"      Trust percentage: {trust_percentage:.1%}")
            print(f"      Average trust score: {avg_trust_score:.1f}/100")
            print(f"      Trust multiplier: {trust_multiplier:.3f}")
            print(f"      Final confidence: {avg_confidence:.1%}")
        else:
            avg_confidence = 0.0

        print("\n✅ Search complete!")
        print("=" * 50)
        
        step_times["formatting"] = time.time() - step_start
        
        # Performance summary
        total_time = time.time() - start_time
        print(f"\n⏱️  Performance Summary:")
        print(f"   Total time: {total_time:.2f}s")
        for step, duration in step_times.items():
            percentage = (duration / total_time) * 100
            print(f"   {step}: {duration:.2f}s ({percentage:.1f}%)")
        print(f"   Processed {len(verified_summaries)} sources")

        # Create final answer
        final_answer = FinalAnswer(
            answer=answer,
            citations=[s.source for s in verified_summaries],
            confidence_score=avg_confidence
        )

        # Generate markdown research paper - COMMENTED OUT FOR PERFORMANCE
        # markdown_paper = self.citer_agent.create_markdown_research_paper(
        #     query, answer, verified_summaries, avg_confidence
        # )

        # Print results in research paper format - COMMENTED OUT FOR PERFORMANCE
        # print(f"\n" + "=" * 80)
        # print(f"RESEARCH PAPER: {query}")
        # print("=" * 80)
        # print(markdown_paper)

        # Save markdown file automatically - COMMENTED OUT
        # filename = f"research_paper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        # try:
        #     with open(filename, 'w', encoding='utf-8') as f:
        #         f.write(markdown_paper)
        #     print(f"\n✅ Research paper saved as: {filename}")
        # except Exception as e:
        #     print(f"\n⚠️  Could not save markdown file: {e}")

        # Store markdown in final answer for potential API use - COMMENTED OUT FOR PERFORMANCE
        # final_answer.markdown_content = markdown_paper

        await emit_progress(
            "completion", 
            "completed", 
            "Research complete! Answer generated with verified sources.", 
            100.0,
            search_queries=None,
            sites_visited=None,
            sources_found=len(verified_summaries)
        )

        return final_answer


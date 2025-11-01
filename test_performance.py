"""
Performance Test Suite for AI Deep Search
Tests performance improvements from optimizations
"""

import asyncio
import time
from typing import Dict, List
from datetime import datetime

# Import the orchestrator and config
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.orchestrator import Orchestrator
from agents.config import Config


class PerformanceTracker:
    """Track performance metrics for search operations"""
    
    def __init__(self):
        self.metrics = {
            "total_time": 0,
            "query_analysis_time": 0,
            "research_time": 0,
            "summarization_time": 0,
            "verification_time": 0,
            "synthesis_time": 0,
            "sources_found": 0,
            "summaries_generated": 0,
            "verified_sources": 0,
            "avg_confidence": 0.0
        }
        self.step_times = []
    
    async def track_progress(self, step, status, details, progress, search_queries=None, sites_visited=None, sources_found=None):
        """Track progress callback"""
        timestamp = time.time()
        self.step_times.append({
            "step": step,
            "status": status,
            "details": details,
            "progress": progress,
            "timestamp": timestamp,
            "sources": sources_found or 0
        })
        
        # Update metrics based on step
        if step == "research" and status == "completed":
            self.metrics["sources_found"] = sources_found or 0
        elif step == "summarization" and status == "completed":
            self.metrics["summaries_generated"] = sources_found or 0
        elif step == "verification" and status == "completed":
            self.metrics["verified_sources"] = sources_found or 0


async def run_performance_test(query: str, mode: str = "deep") -> Dict:
    """
    Run a performance test with the given query
    
    Args:
        query: The search query to test
        mode: Search mode ("deep", "moderate", "quick", "sla")
    
    Returns:
        Dict with performance metrics
    """
    print(f"\n{'='*80}")
    print(f"PERFORMANCE TEST: {query}")
    print(f"Mode: {mode.upper()}")
    print(f"{'='*80}\n")
    
    orchestrator = Orchestrator()
    tracker = PerformanceTracker()
    
    start_time = time.time()
    
    try:
        result = await orchestrator.search(
            query=query,
            progress_callback=tracker.track_progress,
            search_mode=mode
        )
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Update final metrics
        tracker.metrics["total_time"] = total_time
        tracker.metrics["avg_confidence"] = result.confidence_score
        
        # Calculate step times from tracked progress
        step_durations = {}
        for i in range(len(tracker.step_times) - 1):
            current = tracker.step_times[i]
            next_step = tracker.step_times[i + 1]
            
            if current["status"] == "started":
                duration = next_step["timestamp"] - current["timestamp"]
                step_name = current["step"]
                if step_name not in step_durations:
                    step_durations[step_name] = 0
                step_durations[step_name] += duration
        
        # Print results
        print(f"\n{'='*80}")
        print(f"PERFORMANCE RESULTS")
        print(f"{'='*80}")
        print(f"Total Time: {total_time:.2f}s")
        print(f"Sources Found: {tracker.metrics['sources_found']}")
        print(f"Summaries Generated: {tracker.metrics['summaries_generated']}")
        print(f"Verified Sources: {tracker.metrics['verified_sources']}")
        print(f"Average Confidence: {tracker.metrics['avg_confidence']:.1%}")
        
        print(f"\nStep Breakdown:")
        for step, duration in step_durations.items():
            percentage = (duration / total_time * 100) if total_time > 0 else 0
            print(f"  {step}: {duration:.2f}s ({percentage:.1f}%)")
        
        # Calculate metrics
        sources_per_second = tracker.metrics['sources_found'] / total_time if total_time > 0 else 0
        print(f"\nThroughput:")
        print(f"  Sources per second: {sources_per_second:.2f}")
        
        return {
            "query": query,
            "mode": mode,
            "total_time": total_time,
            "metrics": tracker.metrics,
            "step_durations": step_durations,
            "sources_per_second": sources_per_second,
            "answer_length": len(result.answer),
            "citations_count": len(result.citations)
        }
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "query": query,
            "mode": mode,
            "error": str(e),
            "total_time": time.time() - start_time
        }


async def run_benchmark_suite():
    """Run a comprehensive benchmark suite"""
    print("\n" + "="*80)
    print("AI DEEP SEARCH PERFORMANCE BENCHMARK SUITE")
    print("="*80)
    
    # Test queries
    test_queries = [
        "What is quantum computing?",
        "Explain machine learning algorithms",
        "History of artificial intelligence"
    ]
    
    # Test modes
    test_modes = ["deep", "moderate", "quick"]
    
    all_results = []
    
    for query in test_queries:
        for mode in test_modes:
            print(f"\n\n{'#'*80}")
            print(f"Testing: '{query}' in {mode.upper()} mode")
            print(f"{'#'*80}")
            
            result = await run_performance_test(query, mode)
            all_results.append(result)
            
            # Wait between tests to avoid rate limiting
            print("\nWaiting 5 seconds before next test...")
            await asyncio.sleep(5)
    
    # Print summary
    print("\n\n" + "="*80)
    print("BENCHMARK SUMMARY")
    print("="*80)
    
    for result in all_results:
        if "error" in result:
            print(f"\n❌ {result['query']} ({result['mode']}): FAILED - {result['error']}")
        else:
            print(f"\n✅ {result['query']} ({result['mode']}):")
            print(f"   Time: {result['total_time']:.2f}s")
            print(f"   Sources: {result['metrics']['sources_found']}")
            print(f"   Confidence: {result['metrics']['avg_confidence']:.1%}")
            print(f"   Throughput: {result['sources_per_second']:.2f} sources/s")
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"benchmark_results_{timestamp}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("AI DEEP SEARCH PERFORMANCE BENCHMARK RESULTS\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write("="*80 + "\n\n")
        
        for result in all_results:
            f.write(f"Query: {result['query']}\n")
            f.write(f"Mode: {result['mode']}\n")
            
            if "error" in result:
                f.write(f"Status: FAILED\n")
                f.write(f"Error: {result['error']}\n")
            else:
                f.write(f"Status: SUCCESS\n")
                f.write(f"Total Time: {result['total_time']:.2f}s\n")
                f.write(f"Sources Found: {result['metrics']['sources_found']}\n")
                f.write(f"Summaries: {result['metrics']['summaries_generated']}\n")
                f.write(f"Verified: {result['metrics']['verified_sources']}\n")
                f.write(f"Confidence: {result['metrics']['avg_confidence']:.1%}\n")
                f.write(f"Throughput: {result['sources_per_second']:.2f} sources/s\n")
                
                f.write("\nStep Breakdown:\n")
                for step, duration in result['step_durations'].items():
                    percentage = (duration / result['total_time'] * 100)
                    f.write(f"  {step}: {duration:.2f}s ({percentage:.1f}%)\n")
            
            f.write("\n" + "-"*80 + "\n\n")
    
    print(f"\n✅ Results saved to: {filename}")


async def compare_before_after():
    """
    Compare performance before and after optimizations
    Uses known metrics to show improvement
    """
    print("\n" + "="*80)
    print("PERFORMANCE COMPARISON: BEFORE vs AFTER OPTIMIZATIONS")
    print("="*80)
    
    # These would be your actual before metrics (example values)
    before_metrics = {
        "sources": 6,
        "rate_limit_delay": 1.0,
        "concurrent_scraping": 1,
        "concurrent_llm": 1,
        "iterative_research": True,
        "estimated_time_per_source": 3.0  # seconds
    }
    
    # After metrics (actual current config)
    after_metrics = {
        "sources": Config.MAX_TOTAL_SOURCES,
        "rate_limit_delay": Config.RATE_LIMIT_DELAY,
        "concurrent_scraping": Config.MAX_CONCURRENT_SCRAPING,
        "concurrent_llm": Config.MAX_CONCURRENT_LLM_CALLS,
        "iterative_research": Config.ENABLE_ITERATIVE_RESEARCH,
        "estimated_time_per_source": 0.5  # seconds with parallelization
    }
    
    print("\nConfiguration Comparison:")
    print(f"{'Metric':<30} {'Before':<15} {'After':<15} {'Improvement':<15}")
    print("-" * 75)
    
    improvements = []
    
    # Sources
    before_sources = before_metrics["sources"]
    after_sources = after_metrics["sources"]
    source_improvement = ((after_sources - before_sources) / before_sources) * 100
    print(f"{'Max Sources':<30} {before_sources:<15} {after_sources:<15} {source_improvement:>+.0f}%")
    improvements.append(("Sources", source_improvement))
    
    # Rate limit delay
    before_delay = before_metrics["rate_limit_delay"]
    after_delay = after_metrics["rate_limit_delay"]
    delay_improvement = ((before_delay - after_delay) / before_delay) * 100
    print(f"{'Rate Limit Delay (s)':<30} {before_delay:<15.1f} {after_delay:<15.1f} {delay_improvement:>+.0f}%")
    improvements.append(("Rate Limit", delay_improvement))
    
    # Concurrent scraping
    before_concurrent = before_metrics["concurrent_scraping"]
    after_concurrent = after_metrics["concurrent_scraping"]
    concurrent_improvement = ((after_concurrent - before_concurrent) / before_concurrent) * 100
    print(f"{'Concurrent Scraping':<30} {before_concurrent:<15} {after_concurrent:<15} {concurrent_improvement:>+.0f}%")
    improvements.append(("Concurrency", concurrent_improvement))
    
    # Concurrent LLM
    before_llm = before_metrics["concurrent_llm"]
    after_llm = after_metrics["concurrent_llm"]
    llm_improvement = ((after_llm - before_llm) / before_llm) * 100
    print(f"{'Concurrent LLM Calls':<30} {before_llm:<15} {after_llm:<15} {llm_improvement:>+.0f}%")
    improvements.append(("LLM Parallelization", llm_improvement))
    
    # Iterative research
    before_iter = "Enabled" if before_metrics["iterative_research"] else "Disabled"
    after_iter = "Enabled" if after_metrics["iterative_research"] else "Disabled"
    print(f"{'Iterative Research':<30} {before_iter:<15} {after_iter:<15} {'Optimized':<15}")
    
    print("\n" + "="*80)
    print("ESTIMATED PERFORMANCE IMPACT")
    print("="*80)
    
    # Estimated time calculations
    before_time = before_sources * before_metrics["estimated_time_per_source"]
    after_time = (after_sources / after_concurrent) * after_metrics["estimated_time_per_source"]
    time_improvement = ((before_time - after_time) / before_time) * 100
    
    print(f"\nEstimated Search Time:")
    print(f"  Before: {before_time:.1f}s")
    print(f"  After: {after_time:.1f}s")
    print(f"  Improvement: {time_improvement:.0f}% faster")
    
    print(f"\nKey Optimizations Applied:")
    print(f"  ✅ Parallel web scraping (1 → {after_concurrent} concurrent)")
    print(f"  ✅ Parallel LLM calls (1 → {after_llm} concurrent)")
    print(f"  ✅ Rate limit reduction ({before_delay}s → {after_delay}s)")
    print(f"  ✅ Increased sources ({before_sources} → {after_sources})")
    print(f"  ✅ Disabled iterative loops by default")
    print(f"  ✅ Simultaneous verification + reasoning")
    
    return {
        "before": before_metrics,
        "after": after_metrics,
        "improvements": improvements,
        "estimated_speedup": time_improvement
    }


if __name__ == "__main__":
    print("AI Deep Search Performance Test Suite")
    print("=" * 80)
    print("\nOptions:")
    print("1. Run single test")
    print("2. Run full benchmark suite")
    print("3. Show before/after comparison")
    print("4. Quick performance check")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    if choice == "1":
        query = input("Enter search query: ").strip()
        mode = input("Enter mode (deep/moderate/quick/sla) [deep]: ").strip() or "deep"
        asyncio.run(run_performance_test(query, mode))
    
    elif choice == "2":
        confirm = input("This will run multiple tests and may take a while. Continue? (y/n): ").strip().lower()
        if confirm == 'y':
            asyncio.run(run_benchmark_suite())
    
    elif choice == "3":
        asyncio.run(compare_before_after())
    
    elif choice == "4":
        # Quick test with a simple query
        print("\nRunning quick performance check...")
        asyncio.run(run_performance_test("What is AI?", "quick"))
    
    else:
        print("Invalid option")

"""
FastAPI application for AI Deep Search.

This module provides the REST API for the AI Deep Search system, offering endpoints
for executing research queries with optional real-time progress updates. The API
supports both standard and streaming responses, allowing clients to choose between
immediate results or real-time progress tracking.

Main endpoints:
- POST /search: Execute research with standard JSON response
- GET /search/{query}: Execute research with Server-Sent Events (SSE) for progress
- GET /search/sync/{query}: Execute research without streaming (compatibility fallback)
- GET /: API information and endpoint listing
- GET /health: Health check endpoint
"""

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Callable
import asyncio
import uvicorn
import json
from datetime import datetime
import uuid
import dataclasses

# Import the existing search functionality
from aideepseatch import Orchestrator
from agents.data_models import FinalAnswer, SourceMetadata

# Import subscription middleware
from subscription_middleware import check_user_quota, increment_user_search, get_quota_headers

# Import history service
from history_service import save_search_history, get_search_history, delete_search_history_item, clear_all_history

# Import auth utilities
from auth_utils import extract_user_from_token, get_optional_user_from_token

# Import new backend-authoritative services
from search_service import search_service
from quota_service import quota_service

# Import security middleware
from security_middleware import (
    SecurityMiddleware,
    require_auth,
    optional_auth,
    InputSanitizer,
    webhook_idempotency,
    security_logger
)

# Import performance optimizations
from performance_optimization import (
    init_redis_cache,
    cleanup_redis_cache,
    get_redis_cache,
    perf_monitor,
    hash_query,
    normalize_query
)
import os
import time

# Pydantic models for request/response
class SearchRequest(BaseModel):
    """
    Request model for search queries.
    
    Attributes:
        query (str): The research question or topic to investigate
    """
    query: str

class CitationModel(BaseModel):
    """
    Model representing a single source citation with metadata.
    
    Attributes:
        url (str): Source URL
        title (str): Document/page title
        section (str): Section name where content was found
        paragraph_id (str): Unique paragraph identifier
        content (str): Extracted content text
        relevance_score (float): Relevance score (0.0-1.0)
        timestamp (str): ISO format timestamp of retrieval
        trust_flag (str): Trust category identifier
        trust_score (int): Trust score (0-100)
        is_trusted (bool): Whether source is from trusted domain
        trust_category (str): Human-readable trust category
        domain (str): Domain name of the source
    """
    url: str
    title: str
    section: str
    paragraph_id: str
    content: str
    relevance_score: float
    timestamp: str
    trust_flag: str
    trust_score: int
    is_trusted: bool
    trust_category: str
    domain: str

class SearchResponse(BaseModel):
    """
    Complete search result with answer and citations.
    
    Attributes:
        answer (str): Synthesized answer to the query
        citations (List[CitationModel]): All sources cited in the answer
        confidence_score (float): Overall confidence in the answer (0.0-1.0)
        # markdown_content (str): Full research paper in markdown format - COMMENTED OUT FOR PERFORMANCE
    """
    answer: str
    citations: List[CitationModel]
    confidence_score: float
    # markdown_content: str  # COMMENTED OUT FOR PERFORMANCE

class ProgressUpdate(BaseModel):
    """
    Real-time progress update for streaming responses.
    
    Attributes:
        step (str): Current pipeline step (e.g., "validation", "research")
        status (str): Step status (e.g., "started", "completed", "failed")
        details (str): Human-readable progress description
        timestamp (str): ISO format timestamp
        progress_percentage (float): Overall progress (0.0-100.0)
        search_queries (Optional[List[str]]): Search queries being used (if applicable)
        sites_visited (Optional[List[str]]): URLs being visited (if applicable)
        sources_found (Optional[int]): Number of sources found (if applicable)
    """
    step: str
    status: str
    details: str
    timestamp: str
    progress_percentage: float
    search_queries: Optional[List[str]] = None
    sites_visited: Optional[List[str]] = None
    sources_found: Optional[int] = None

class StreamingSearchResponse(BaseModel):
    """
    Wrapper for streaming search responses (SSE format).
    
    Attributes:
        type (str): Response type - "progress", "result", or "error"
        data (Optional[Dict[str, Any]]): Generic data payload (for errors)
        progress (Optional[ProgressUpdate]): Progress update (if type="progress")
        result (Optional[SearchResponse]): Final result (if type="result")
    """
    type: str  # "progress" or "result"
    data: Optional[Dict[str, Any]] = None
    progress: Optional[ProgressUpdate] = None
    result: Optional[SearchResponse] = None

# Create FastAPI app
app = FastAPI(
    title="Omnivionai API",
    description="Academic Research Paper Generator with Multi-Agent Deep Search",
    version="1.0.0"
)

# Add Security Middleware (FIRST - before CORS)
app.add_middleware(SecurityMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global orchestrator instance
orchestrator = Orchestrator()

# ============================================================================
# Application Lifecycle Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    print("🚀 Starting Omnivionai API...")
    
    # Initialize Redis cache (optional)
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        await init_redis_cache(redis_url)
        print("✅ Redis cache initialized")
    except Exception as e:
        print(f"⚠️  Redis cache not available: {e}")
        print("   System will run without caching (performance may be reduced)")
    
    print("✅ Omnivionai API ready!")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown."""
    print("🛑 Shutting down Omnivionai API...")
    
    await cleanup_redis_cache()
    
    print("✅ Cleanup complete")

# ============================================================================
# Main Endpoints
# ============================================================================

@app.get("/")
@app.head("/")
async def root():
    """
    Root endpoint providing API information and available endpoints.
    
    Returns:
        Dict: API metadata including version and endpoint descriptions
    """
    redis_status = "enabled" if get_redis_cache() and get_redis_cache().enabled else "disabled"
    
    return {
        "message": "Omnivionai API",
        "version": "1.0.0",
        "performance": {
            "redis_cache": redis_status,
            "async": "enabled",
            "streaming": "enabled"
        },
        "endpoints": {
            "/search": "POST - Execute research query (standard response)",
            "/search/{query}": "GET - Execute research query with real-time progress (Server-Sent Events)",
            "/search/sync/{query}": "GET - Execute research query without streaming (fallback)",
            "/health": "GET - Health check",
            "/metrics": "GET - Performance metrics"
        }
    }

@app.get("/health")
@app.head("/health")
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns:
        Dict: Health status
    """
    redis_cache = get_redis_cache()
    redis_healthy = redis_cache and redis_cache.enabled
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "redis": "healthy" if redis_healthy else "unavailable"
    }

@app.get("/metrics")
async def get_metrics():
    """
    Get performance metrics.
    
    Returns:
        Dict: Performance statistics
    """
    return {
        "performance_stats": perf_monitor.get_all_stats(),
        "timestamp": datetime.utcnow().isoformat()
    }


# ==================== HISTORY ENDPOINTS (Backend Authoritative) ====================

@app.get("/history")
@require_auth
async def get_history(
    req: Request,
    limit: int = 20,
    offset: int = 0
):
    """
    Get search history for the authenticated user.
    
    **Backend Authoritative**: Only backend can write history.
    Frontend reads history via this endpoint only.
    
    **Security:**
    - JWT validation required
    - Rate limiting enforced
    - Pagination limits enforced
    
    Args:
        req: FastAPI Request object
        limit: Number of results to return (max 100)
        offset: Pagination offset
        
    Returns:
        Dict containing paginated history
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 429: Rate limited
    """
    # Extract user_id from request state (set by @require_auth)
    user_id = req.state.user_id
    
    # Limit validation
    limit = min(max(1, limit), 100)  # Between 1-100
    offset = max(0, offset)  # Non-negative
    
    # Get history from backend service
    history_data = await get_search_history(user_id, limit, offset)
    
    return JSONResponse(content=history_data)


@app.delete("/history/{search_id}")
@require_auth
async def delete_history(
    req: Request,
    search_id: str
):
    """
    Delete a specific search history item.
    
    **Backend Authoritative**: Only backend can delete history.
    
    **Security:**
    - JWT validation required
    - Input validation (UUID format)
    - Ownership verification
    
    Args:
        req: FastAPI Request object
        search_id: ID of search to delete
        
    Returns:
        Dict with deletion status
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 400: Invalid search_id format
    """
    # Extract user_id from request state (set by @require_auth)
    user_id = req.state.user_id
    
    # Validate UUID format
    if not InputSanitizer.validate_uuid(search_id):
        raise HTTPException(status_code=400, detail="Invalid search_id format")
    
    # Delete history item
    result = await delete_search_history_item(user_id, search_id)
    
    return JSONResponse(content=result)


@app.delete("/history")
@require_auth
async def clear_history(
    req: Request
):
    """
    Clear all search history for the authenticated user.
    
    **Backend Authoritative**: Only backend can clear history.
    
    **Security:**
    - JWT validation required
    - Rate limiting enforced
    
    Args:
        req: FastAPI Request object
        
    Returns:
        Dict with clear status
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 429: Rate limited
    """
    # Extract user_id from request state (set by @require_auth)
    user_id = req.state.user_id
    
    # Clear all history
    result = await clear_all_history(user_id)
    
    return JSONResponse(content=result)

@app.get("/test-search/{query}")
async def test_search(query: str):
    """
    Test search endpoint for debugging and development.
    
    Returns mock search results without executing actual research pipeline.
    Useful for frontend development and API testing.
    
    Args:
        query (str): Test query string
        
    Returns:
        SearchResponse: Mock search response with test data
    """
    print(f"🧪 Test search received: {query}")
    
    # Create mock response for testing
    mock_citation = {
        "url": "https://example.com",
        "title": "Test Article",
        "section": "Introduction",
        "paragraph_id": "p1",
        "content": f"This is a test search result for: {query}",
        "relevance_score": 0.8,
        "timestamp": datetime.now().isoformat(),
        "trust_flag": "verified",
        "trust_score": 85,
        "is_trusted": True,
        "trust_category": "Academic Source",
        "domain": "example.com"
    }
    
    return {
        "answer": f"This is a test response for your query: {query}",
        "citations": [mock_citation],
        "confidence_score": 0.8,
        "markdown_content": f"# Test Result\n\nThis is a test markdown response for: {query}"
    }


# ============================================================================
# NEW BACKEND-AUTHORITATIVE SEARCH ENDPOINTS
# ============================================================================

@app.post("/api/search")
@require_auth
async def backend_authoritative_search(
    req: Request,
    request: SearchRequest
):
    """
    **Backend-Authoritative Search Endpoint**
    
    Complete search lifecycle with atomic quota enforcement:
    1. Validates JWT and authenticates user
    2. Checks and decrements quota atomically (prevents race conditions)
    3. Creates pending search history entry
    4. Executes multi-agent orchestrator
    5. Updates search history with results/failure
    6. Logs usage for analytics
    7. Refunds quota on failure
    
    **Ownership Model:**
    - Backend owns ALL writes (quota, history, usage logs)
    - Frontend reads via API only
    - No client can bypass quota limits
    - Atomic operations prevent race conditions
    
    **Quota Enforcement:**
    - Atomic decrement using database function
    - Supports concurrent searches per user
    - Automatic refund on search failure
    
    **Security:**
    - JWT validation required
    - Input sanitization (XSS, SQL injection prevention)
    - Rate limiting enforced
    - Request logging
    
    **Performance:**
    - Redis cache for duplicate queries
    - Async execution with asyncio
    - Performance tracking
    - Optional queue for long searches
    
    Args:
        req: FastAPI Request object
        request: SearchRequest with query
        
    Returns:
        Complete search results with quota info
        
    Raises:
        HTTPException 401: Not authenticated
        HTTPException 429: Quota exceeded or rate limited
        HTTPException 500: Search failed
    """
    start_time = time.time()
    
    try:
        # Extract user_id from request state (set by @require_auth)
        user_id = req.state.user_id
        
        # Sanitize and validate query
        if not request.query or not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Sanitize query (prevent XSS, SQL injection)
        query = InputSanitizer.sanitize_search_query(request.query.strip())
        
        if not query:
            raise HTTPException(status_code=400, detail="Invalid query after sanitization")
        
        # Log successful authentication
        security_logger.log_auth_success(user_id, req)
        
        print(f"🔍 Backend-authoritative search: {query} (user: {user_id})")
        
        # Check Redis cache for duplicate query
        redis_cache = get_redis_cache()
        query_hash = hash_query(query)
        
        if redis_cache and redis_cache.enabled:
            cached_result = await redis_cache.get_search_result(query_hash)
            if cached_result:
                print(f"✅ Cache HIT - returning cached result")
                
                # Track cache hit performance
                duration = time.time() - start_time
                await perf_monitor.track("search_cache_hit", duration)
                
                return JSONResponse(content=cached_result)
        
        # Get user's plan type for token limits
        from subscription_middleware import supabase as sub_supabase
        sub_result = sub_supabase.table('user_subscriptions') \
            .select('plan_type') \
            .eq('user_id', user_id) \
            .single() \
            .execute()
        
        plan_type = sub_result.data.get('plan_type', 'free') if sub_result.data else 'free'
        
        # Execute backend-authoritative search lifecycle with idempotent agents
        result = await search_service.execute_search(
            user_id=user_id,
            query=query,
            plan_type=plan_type,  # For token usage limits
            metadata={
                "endpoint": "/api/search",
                "timestamp": datetime.utcnow().isoformat(),
                "query_hash": query_hash
            }
        )
        
        print(f"✅ Search completed: {result['search_id']}")
        
        # Cache the result
        if redis_cache and redis_cache.enabled and result.get('status') == 'success':
            await redis_cache.cache_search_result(
                query_hash,
                result,
                ttl=3600  # Cache for 1 hour
            )
        
        # Track performance
        duration = time.time() - start_time
        await perf_monitor.track("search_execution", duration)
        print(f"⏱️  Search duration: {duration:.2f}s")
        
        return JSONResponse(
            content=result,
            headers=get_quota_headers({
                "searches_remaining": result['quota']['searches_remaining'],
                "plan_type": result['quota']['plan_type'],
                "reset_date": ""  # TODO: Add from subscription
            })
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Search error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/api/search/stream")
async def backend_authoritative_search_stream(
    query: str,
    authorization: Optional[str] = Header(None)
):
    """
    **Backend-Authoritative Search with SSE Streaming**
    
    Same as /api/search but streams progress updates via Server-Sent Events.
    
    **Real-time Updates:**
    - Quota check status
    - Search creation
    - Agent step progress
    - Final completion
    
    **Ownership Model:**
    - Backend owns all state transitions
    - Frontend receives read-only updates
    - Quota enforced before streaming starts
    
    Args:
        query: Search query string
        authorization: Bearer token (required)
        
    Returns:
        StreamingResponse with SSE events
        
    Raises:
        HTTPException 401: Not authenticated
        HTTPException 429: Quota exceeded
    """
    try:
        # Extract and validate user from JWT
        user_id = await extract_user_from_token(authorization)
        
        if not query or not query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        query = query.strip()
        print(f"🔍 Streaming search: {query} (user: {user_id})")
        
        # Stream search progress
        async def event_generator():
            try:
                async for event in search_service.stream_search_progress(user_id, query):
                    yield event
            except Exception as e:
                error_event = f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
                yield error_event
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Streaming error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Streaming failed: {str(e)}")


@app.get("/api/quota")
@require_auth
async def get_quota_status(
    req: Request
):
    """
    Get current quota status without decrementing
    
    **Backend Authoritative**: Only backend tracks quota
    
    **Security:**
    - JWT validation required
    - Read-only operation
    - Rate limiting enforced
    
    Args:
        req: FastAPI Request object
        
    Returns:
        Current quota information
        
    Raises:
        HTTPException 401: Not authenticated
        HTTPException 429: Rate limited
    """
    user_id = req.state.user_id
    quota_status = await quota_service.get_quota_status(user_id)
    return JSONResponse(content=quota_status)


# ============================================================================
# LEGACY SEARCH ENDPOINTS (Deprecated - use /api/search instead)
# ============================================================================

@app.post("/search", response_model=SearchResponse)
async def search_research_paper(
    request: SearchRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Execute AI Deep Search research and return complete results.
    
    This endpoint executes the full research pipeline including query validation,
    analysis, web research, summarization, reasoning, verification, and citation
    generation. Returns the complete result as a single JSON response.
    
    For real-time progress updates, use GET /search/{query} instead.
    
    **Quota Enforcement**: Free users are limited to 3 searches per day.
    
    Args:
        request (SearchRequest): Request body containing the search query
        authorization (Optional[str]): Bearer token for authentication
        
    Returns:
        SearchResponse: Complete search result with answer, citations, and markdown content
        
    Raises:
        HTTPException 400: If query is empty or fails validation
        HTTPException 429: If user has exceeded search quota
        HTTPException 500: If research process encounters an error
        
    Example:
        ```
        POST /search
        {
            "query": "What is quantum computing?"
        }
        ```
    """
    try:
        if not request.query or not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        print(f"🔍 Received search request: {request.query.strip()}")
        
        # Check user quota before processing
        quota_info = await check_user_quota(authorization)
        print(f"✅ Quota check passed: {quota_info.get('searches_remaining', 0)} searches remaining")
        
        # Generate unique search ID
        search_id = str(uuid.uuid4())
        
        # Execute the search
        result: FinalAnswer = await orchestrator.search(request.query.strip())

        print(f"✅ Search completed with {len(result.citations)} citations")
        
        # Increment search count after successful search
        increment_result = await increment_user_search(
            search_id=search_id,
            query_preview=request.query.strip(),
            authorization=authorization
        )
        print(f"📊 Search count updated: {increment_result.get('searches_used', 0)} used, {increment_result.get('searches_remaining', 0)} remaining")

        # Convert citations to dict format for JSON response (optimized)
        citations_data = [dataclasses.asdict(citation) for citation in result.citations]

        # Create response with quota information
        response_data = SearchResponse(
            answer=result.answer,
            citations=citations_data,
            confidence_score=result.confidence_score
            # markdown_content=result.markdown_content  # COMMENTED OUT FOR PERFORMANCE
        )
        
        # Return response with quota headers
        return JSONResponse(
            content=response_data.dict(),
            headers=get_quota_headers({
                "searches_remaining": increment_result.get('searches_remaining', 0),
                "plan_type": quota_info.get('plan_type', 'free'),
                "reset_date": quota_info.get('reset_date', '')
            })
        )

    except ValueError as e:
        # Handle validation errors (invalid query)
        print(f"⚠️ Invalid query: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Search error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/search/{query}")
async def search_research_paper_get(
    query: str,
    authorization: Optional[str] = Header(None)
):
    """
    Execute AI Deep Search with real-time progress updates (Server-Sent Events).
    
    This endpoint provides the same research functionality as POST /search but streams
    progress updates in real-time using Server-Sent Events (SSE). Clients receive
    incremental updates about each stage of the research process.
    
    Progress updates include:
    - Query validation status
    - Query analysis results with generated search terms
    - Research progress with sites being visited
    - Summarization and reasoning progress
    - Verification status
    - Citation generation
    - Final complete result
    
    **Quota Enforcement**: Free users are limited to 3 searches per day.
    
    Args:
        query (str): The research query (URL encoded in path)
        authorization (Optional[str]): Bearer token for authentication
        
    Returns:
        StreamingResponse: SSE stream with progress updates and final result
        
    Raises:
        HTTPException 400: If query is empty or fails validation
        HTTPException 429: If user has exceeded search quota
        
    Response Format:
        Each event contains a JSON object with type="progress" or type="result"
        - Progress events: {"type": "progress", "progress": {...}}
        - Result event: {"type": "result", "result": {...}}
        - Error events: {"type": "error", "data": {...}}
        
    Example:
        ```
        GET /search/What%20is%20quantum%20computing
        
        data: {"type":"progress","progress":{"step":"validation","status":"started",...}}
        data: {"type":"progress","progress":{"step":"query_analysis","status":"completed",...}}
        ...
        data: {"type":"result","result":{"answer":"...","citations":[...],...}}
        ```
    """
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    print(f"🔍 Received streaming search request: {query.strip()}")
    
    # Check user quota before processing
    try:
        quota_info = await check_user_quota(authorization)
        print(f"✅ Quota check passed: {quota_info.get('searches_remaining', 0)} searches remaining")
    except HTTPException as e:
        print(f"❌ Quota check failed: {e.detail}")
        raise

    async def generate_search_stream():
        try:
            print(f"🚀 Starting search stream for: {query.strip()}")
            
            # Create a queue for progress updates
            progress_queue = asyncio.Queue()
            
            # Modified progress callback that puts data in queue
            async def queued_progress_callback(step: str, status: str, details: str, progress: float, search_queries=None, sites_visited=None, sources_found=None):
                print(f"📈 Progress: {step} - {status} - {details} ({progress}%)")
                
                progress_update = ProgressUpdate(
                    step=step,
                    status=status,
                    details=details,
                    timestamp=datetime.now().isoformat(),
                    progress_percentage=progress,
                    search_queries=search_queries,
                    sites_visited=sites_visited,
                    sources_found=sources_found
                )
                
                response = StreamingSearchResponse(
                    type="progress",
                    progress=progress_update
                )
                
                await progress_queue.put(f"data: {response.model_dump_json()}\n\n")

            # Start the search in a separate task
            search_task = asyncio.create_task(orchestrator.search(query.strip(), queued_progress_callback))
            
            # Yield progress updates as they come
            while not search_task.done():
                try:
                    # Wait for progress update with timeout
                    progress_data = await asyncio.wait_for(progress_queue.get(), timeout=0.1)
                    yield progress_data
                except asyncio.TimeoutError:
                    continue
            
            # Get any remaining progress updates
            while not progress_queue.empty():
                try:
                    progress_data = await asyncio.wait_for(progress_queue.get(), timeout=0.1)
                    yield progress_data
                except asyncio.TimeoutError:
                    break
            
            # Get the final result
            result: FinalAnswer = await search_task
            
            print(f"✅ Search completed with {len(result.citations)} citations")
            
            # Generate unique search ID and increment search count
            search_id = str(uuid.uuid4())
            increment_result = await increment_user_search(
                search_id=search_id,
                query_preview=query.strip(),
                authorization=authorization
            )
            print(f"📊 Search count updated: {increment_result.get('searches_used', 0)} used, {increment_result.get('searches_remaining', 0)} remaining")

            # Convert citations to dict format for JSON response (optimized)
            citations_data = [dataclasses.asdict(citation) for citation in result.citations]

            # Send final result
            final_response = SearchResponse(
                answer=result.answer,
                citations=citations_data,
                confidence_score=result.confidence_score
                # markdown_content=result.markdown_content  # COMMENTED OUT FOR PERFORMANCE
            )
            
            response = StreamingSearchResponse(
                type="result",
                result=final_response
            )
            
            yield f"data: {response.model_dump_json()}\n\n"

        except ValueError as e:
            # Send validation error as final message
            error_response = StreamingSearchResponse(
                type="error",
                data={"error": str(e), "validation_error": True}
            )
            yield f"data: {error_response.model_dump_json()}\n\n"
        except Exception as e:
            # Send error as final message
            error_response = StreamingSearchResponse(
                type="error",
                data={"error": f"Search failed: {str(e)}"}
            )
            yield f"data: {error_response.model_dump_json()}\n\n"

    return StreamingResponse(
        generate_search_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        }
    )

@app.get("/search/sync/{query}", response_model=SearchResponse)
async def search_research_paper_sync(query: str):
    """
    Execute AI Deep Search via GET request without streaming (compatibility endpoint).
    
    This endpoint provides the same functionality as POST /search but accepts the
    query as a URL path parameter. It does not provide progress updates, returning
    only the final result. Useful for clients that cannot handle POST requests or
    streaming responses.
    
    Args:
        query (str): The research query (URL encoded in path)
        
    Returns:
        SearchResponse: Complete search result with answer, citations, and markdown content
        
    Raises:
        HTTPException 400: If query is empty or fails validation
        HTTPException 500: If research process encounters an error
        
    Example:
        ```
        GET /search/sync/What%20is%20quantum%20computing
        
        Returns JSON:
        {
            "answer": "...",
            "citations": [...],
            "confidence_score": 0.95,
            "markdown_content": "..."
        }
        ```
    """
    try:
        if not query or not query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        # Execute the search without progress callback (original behavior)
        result: FinalAnswer = await orchestrator.search(query.strip())

        # Convert citations to dict format for JSON response (optimized)
        citations_data = [dataclasses.asdict(citation) for citation in result.citations]

        return SearchResponse(
            answer=result.answer,
            citations=citations_data,
            confidence_score=result.confidence_score
            # markdown_content=result.markdown_content  # COMMENTED OUT FOR PERFORMANCE
        )

    except ValueError as e:
        # Handle validation errors (invalid query)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )


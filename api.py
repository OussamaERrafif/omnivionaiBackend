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

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Callable
import asyncio
import uvicorn
import json
from datetime import datetime
import uuid

# Import the existing search functionality
from aideepseatch import Orchestrator
from agents.data_models import FinalAnswer, SourceMetadata

# Import subscription middleware
from subscription_middleware import check_user_quota, increment_user_search, get_quota_headers

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
        markdown_content (str): Full research paper in markdown format
    """
    answer: str
    citations: List[CitationModel]
    confidence_score: float
    markdown_content: str

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

@app.get("/")
@app.head("/")
async def root():
    """
    Root endpoint providing API information and available endpoints.
    
    Returns:
        Dict: API metadata including version and endpoint descriptions
    """
    return {
        "message": "Omnivionai API",
        "version": "1.0.0",
        "endpoints": {
            "/search": "POST - Execute research query (standard response)",
            "/search/{query}": "GET - Execute research query with real-time progress (Server-Sent Events)",
            "/search/sync/{query}": "GET - Execute research query without streaming (fallback)",
            "/health": "GET - Health check"
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
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

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

        # Convert citations to dict format for JSON response
        citations_data = []
        for citation in result.citations:
            citations_data.append({
                "url": citation.url,
                "title": citation.title,
                "section": citation.section,
                "paragraph_id": citation.paragraph_id,
                "content": citation.content,
                "relevance_score": citation.relevance_score,
                "timestamp": citation.timestamp,
                "trust_flag": citation.trust_flag,
                "trust_score": citation.trust_score,
                "is_trusted": citation.is_trusted,
                "trust_category": citation.trust_category,
                "domain": citation.domain
            })

        # Create response with quota information
        response_data = SearchResponse(
            answer=result.answer,
            citations=citations_data,
            confidence_score=result.confidence_score,
            markdown_content=result.markdown_content
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

            # Convert citations to dict format for JSON response
            citations_data = []
            for citation in result.citations:
                citations_data.append({
                    "url": citation.url,
                    "title": citation.title,
                    "section": citation.section,
                    "paragraph_id": citation.paragraph_id,
                    "content": citation.content,
                    "relevance_score": citation.relevance_score,
                    "timestamp": citation.timestamp,
                    "trust_flag": citation.trust_flag,
                    "trust_score": citation.trust_score,
                    "is_trusted": citation.is_trusted,
                    "trust_category": citation.trust_category,
                    "domain": citation.domain
                })

            # Send final result
            final_response = SearchResponse(
                answer=result.answer,
                citations=citations_data,
                confidence_score=result.confidence_score,
                markdown_content=result.markdown_content
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

        # Convert citations to dict format for JSON response
        citations_data = []
        for citation in result.citations:
            citations_data.append({
                "url": citation.url,
                "title": citation.title,
                "section": citation.section,
                "paragraph_id": citation.paragraph_id,
                "content": citation.content,
                "relevance_score": citation.relevance_score,
                "timestamp": citation.timestamp,
                "trust_flag": citation.trust_flag,
                "trust_score": citation.trust_score,
                "is_trusted": citation.is_trusted,
                "trust_category": citation.trust_category,
                "domain": citation.domain
            })

        return SearchResponse(
            answer=result.answer,
            citations=citations_data,
            confidence_score=result.confidence_score,
            markdown_content=result.markdown_content
        )

    except ValueError as e:
        # Handle validation errors (invalid query)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host="localhost",
        port=8000,
        reload=True
    )


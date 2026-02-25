# AI Deep Search - Repository Explanation (0 to 100)

## Executive Summary
**AI Deep Search** is an advanced, multi-agent research paper generator designed to produce PhD-grade research papers with comprehensive citations. It leverages OpenAI's GPT models (specifically targeting `gpt-5-nano-2025-08-07`) and a specialized pipeline of autonomous agents to validate queries, gather web sources, synthesize information, verify facts, and format academic-style output.

The system is built as a robust FastAPI backend that integrates with Supabase for authentication, database storage, and real-time quota management.

## Technology Stack
- **Backend Framework**: FastAPI (Python)
- **AI/LLM**: OpenAI GPT models via LangChain & OpenAI API
- **Database & Auth**: Supabase (PostgreSQL with RLS, Supabase Auth)
- **Caching**: Redis (Optional, currently configured for in-memory fallback)
- **Deployment**: Configured for Vercel, Docker, and traditional servers (Gunicorn/Uvicorn)
- **Search**: DuckDuckGo Search API (free, no-key required)
- **Streaming**: Server-Sent Events (SSE) for real-time progress tracking

---

## 1. Backend Architecture & Security

### Entry Point (`app.py`)
The application is a FastAPI-based REST API. It supports:
- **Standard POST requests** for research queries.
- **SSE Streaming** (`/search/{query}`) to provide real-time updates as agents work.
- **Backend-Authoritative Endpoints** (`/api/search`) which handle the entire lifecycle including quota enforcement and history persistence.

### Security Layers
- **Authentication (`auth_utils.py`)**: Uses JWT verification against the `SUPABASE_JWT_SECRET`. It includes decorators like `@require_auth` and `@optional_auth` to protect endpoints.
- **Rate Limiting (`security_middleware.py`)**: Implements plan-based rate limits (Free, Pro, Enterprise) using an in-memory tracker (extensible to Redis).
- **Input Sanitization (`security_middleware.py`)**: Uses advanced regex patterns to detect and block SQL injection, NoSQL injection, path traversal, and XSS attacks.
- **Security Headers**: Middleware adds `X-Frame-Options`, `Content-Security-Policy`, and other essential headers to every response.
- **Webhook Security (`webhook_security.py`)**: Validates Lemon Squeezy signatures and implements replay protection and idempotency for subscription events.

### Authoritative Backend Model
The system follows a strict authoritative model where the backend owns all state transitions:
1. **Quota Management**: Atomic decrementing of search credits via Supabase RPC functions (`decrement_search_quota`) to prevent race conditions.
2. **Search Lifecycle**: `search_service.py` manages the creation (Pending), execution (Processing), and completion (Success/Failed) states of research.
3. **History Persistence**: All searches are automatically saved to `encrypted_search_history` in Supabase.

---

## 2. Multi-Agent Research Pipeline

The "brain" of the system is the **Orchestrator** (`agents/orchestrator.py`), which coordinates a sequential (and sometimes parallel) pipeline of specialized agents:

1. **Query Validator (`query_validator_agent.py`)**: Ensures the query is safe, appropriate, and researchable.
2. **Query Analyzer (`query_analyzer_agent.py`)**: Breaks down the main query into multiple search strategies and specific research questions.
3. **Research Agent (`research_agent.py`)**: Performs asynchronous web searches, scrapes content from relevant sites, and filters for high-quality data.
4. **Image Analyzer (`image_analyzer_agent.py`)**: Identifies and analyzes relevant images from the gathered sources for contextual placement in the paper.
5. **Summarizer Agent (`summarizer_agent.py`)**: Extracts the most pertinent information from scraped content while maintaining citation mapping.
6. **Verification Agent (`verification_agent.py`)**: Cross-references claims across multiple sources to ensure factual accuracy and filter out hallucinations.
7. **Reasoning Agent (`reasoning_agent.py`)**: Synthesizes the verified findings into a coherent, logically structured research paper.
8. **Source Citer Agent (`source_citer_agent.py`)**: Formats the final citations and ensures the research paper follows academic standards.

---

## 3. Infrastructure & Core Services

### Search Modes
The system supports four distinct modes (configured in `agents/config.py`):
- **Deep**: Maximum accuracy, multiple iterations, full verification.
- **Moderate**: Balanced speed and accuracy.
- **Quick**: Focused on speed, skips deep reasoning/verification.
- **SLA**: Ultra-fast, single-source lookup for immediate results.

### Trusted Domains (`trusted_domains.py`)
A sophisticated ranking system that prioritizes sources based on domain credibility:
- **95/100**: Academic (.edu) & Research institutions.
- **90/100**: Government (.gov) & Scientific publishers (Nature, Science, etc.).
- **80/100**: Established media (BBC, NYT, Reuters).
- Includes an extensive blacklist (e.g., dictionaries, forums, low-quality content farms).

### Idempotency & Token Tracking (`idempotent_agents.py`)
- **Execution Cache**: Caches agent results to prevent redundant LLM calls on retries.
- **Token Limiter**: Tracks token usage per search and enforces limits based on the user's subscription plan.

---

## 4. Performance Optimizations
- **Asynchronous Execution**: Fully async I/O for web scraping and LLM calls.
- **GZIP Compression**: Reduces bandwidth usage by 70-80%.
- **Parallel Processing**: Agents run tasks like verification and synthesis in parallel where possible.
- **Redis Caching**: Configured to cache search results for 1 hour to handle duplicate queries instantly.

---

## 5. Deployment & Configuration
- **Environment Variables**: Managed via `.env` (API keys for OpenAI, Supabase credentials, etc.).
- **Configuration (`agents/config.py`)**: Centralized control for search limits, model selection, and quality thresholds.
- **Migrations**: SQL scripts provided for setting up RLS policies, security audits, and atomic database functions.

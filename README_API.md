# AI Deep Search API

A FastAPI-based REST API for the AI Deep Search system - Academic Research Paper Generator with Multi-Agent Deep Search.

## Features

- **Multi-Agent Research Pipeline**: Orchestrated AI agents for comprehensive research
  - Query Validation & Analysis
  - Web Research & Content Extraction
  - Summarization & Synthesis
  - Fact Verification
  - Citation Generation
- **Real-time Progress Updates**: Server-Sent Events (SSE) for live progress tracking
- **Trust-Based Source Ranking**: Prioritizes academic, government, and verified sources
- **Comprehensive Citations**: Detailed source metadata with trust scores
- **Structured Output**: JSON and Markdown formats
- **CORS Support**: Cross-origin resource sharing enabled
- **Async Processing**: Efficient asynchronous request handling
- **OpenAPI Documentation**: Interactive API docs with Swagger UI

## Installation

### Prerequisites

- Python 3.11+ installed
- OpenAI API key (required)
- Supabase account (optional, for auth features)

### Setup Steps

1. **Install dependencies**:
   ```bash
   cd Backend
   pip install -r requirements.txt
   ```

2. **Set up environment variables**:
   Create a `.env` file in the Backend directory:
   ```bash
   OPENAI_API_KEY=your-openai-api-key-here
   SUPABASE_URL=your-supabase-url
   SUPABASE_ANON_KEY=your-supabase-anon-key
   ```
   
   Get your OpenAI API key from: https://platform.openai.com/api-keys

## Usage

### Starting the API Server

```bash
cd backend
python api.py
```

The server will start on `http://localhost:8000`

### API Endpoints

#### GET `/`
Returns API information and available endpoints.

#### GET `/health`
Health check endpoint.

#### POST `/search`
Execute a research query with standard JSON response.

**Request Body:**
```json
{
  "query": "What are the latest developments in quantum computing?"
}
```

**Response:**
```json
{
  "answer": "Comprehensive answer synthesized from multiple sources...",
  "citations": [
    {
      "url": "https://example.edu/quantum-computing",
      "title": "Advances in Quantum Computing",
      "section": "Recent Developments",
      "paragraph_id": "p1",
      "content": "Recent breakthroughs in quantum computing include...",
      "relevance_score": 0.92,
      "timestamp": "2024-01-15T10:30:00",
      "trust_flag": "academic_research_trusted",
      "trust_score": 95,
      "is_trusted": true,
      "trust_category": "Academic & Research Institution",
      "domain": "example.edu"
    }
  ],
  "confidence_score": 0.94,
  "markdown_content": "# Research Paper: Quantum Computing Developments\n\n## Abstract\n..."
}
```

#### GET `/search/{query}`
Execute research with **real-time progress updates** via Server-Sent Events (SSE).

**Example:**
```
GET /search/What%20are%20the%20latest%20developments%20in%20quantum%20computing%3F
```

**Response Stream (SSE):**
```
data: {"type":"progress","progress":{"step":"validation","status":"started","details":"Validating query...","progress_percentage":5.0}}

data: {"type":"progress","progress":{"step":"query_analysis","status":"completed","details":"Generated search questions","progress_percentage":25.0,"search_queries":["What is quantum computing?","How does quantum computing work?"]}}

data: {"type":"progress","progress":{"step":"research","status":"in_progress","details":"Gathering sources...","progress_percentage":45.0}}

data: {"type":"result","result":{"answer":"...","citations":[...],"confidence_score":0.94,"markdown_content":"..."}}
```

**Use Cases:**
- Real-time progress tracking in UI
- Live status updates during long searches
- Better user experience with visibility

#### GET `/search/sync/{query}`
Alternative GET endpoint without streaming (compatibility fallback).

**Example:**
```
GET /search/sync/What%20are%20the%20latest%20developments%20in%20quantum%20computing%3F
```

**Response:** Same as POST `/search` (standard JSON)

## Testing the API

### Using curl

```bash
# Standard POST request
curl -X POST "http://localhost:8000/search" \
     -H "Content-Type: application/json" \
     -d '{"query": "What are the benefits of renewable energy?"}'

# Streaming GET request (SSE)
curl -N "http://localhost:8000/search/What%20are%20the%20benefits%20of%20renewable%20energy%3F"

# Non-streaming GET request
curl "http://localhost:8000/search/sync/What%20are%20the%20benefits%20of%20renewable%20energy%3F"

# Health check
curl "http://localhost:8000/health"
```

### Using Python

```python
import requests
import json

# Standard POST request
response = requests.post(
    "http://localhost:8000/search",
    json={"query": "What are the latest AI developments?"}
)
result = response.json()
print(f"Answer: {result['answer']}")
print(f"Citations: {len(result['citations'])}")
print(f"Confidence: {result['confidence_score']}")

# Streaming request with SSE
import sseclient
response = requests.get(
    "http://localhost:8000/search/What%20are%20the%20latest%20AI%20developments%3F",
    stream=True
)
client = sseclient.SSEClient(response)
for event in client.events():
    data = json.loads(event.data)
    if data['type'] == 'progress':
        print(f"Progress: {data['progress']['step']} - {data['progress']['details']}")
    elif data['type'] == 'result':
        print(f"Final result received!")
        print(f"Answer: {data['result']['answer'][:100]}...")
```

### Using JavaScript/TypeScript

```typescript
// Standard fetch request
const response = await fetch('http://localhost:8000/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: 'What is machine learning?' })
});
const result = await response.json();
console.log(result);

// Server-Sent Events (SSE)
const eventSource = new EventSource(
  'http://localhost:8000/search/What%20is%20machine%20learning%3F'
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'progress') {
    console.log(`Progress: ${data.progress.step} - ${data.progress.details}`);
  } else if (data.type === 'result') {
    console.log('Final result:', data.result);
    eventSource.close();
  }
};

eventSource.onerror = (error) => {
  console.error('SSE Error:', error);
  eventSource.close();
};
```

## Response Format

The API returns research results in the following JSON structure:

- `answer`: The main research paper content
- `citations`: Array of source citations with metadata
- `confidence_score`: Overall confidence in the results (0.0 to 1.0)
- `markdown_content`: Complete research paper in Markdown format

## Citation Metadata

Each citation includes:

- `url`: Source URL
- `title`: Page/article title
- `section`: Section of the content
- `content`: Extracted content snippet
- `relevance_score`: How relevant this source is to the query (0.0 to 1.0)
- `trust_score`: Trustworthiness score (0-100)
- `is_trusted`: Whether the source is from a verified trusted domain
- `trust_category`: Category of trust (e.g., "Academic & Research Institution")

## Error Handling

The API returns appropriate HTTP status codes:

- `200`: Success
- `400`: Bad request (empty query)
- `500`: Internal server error (search failure)

Error responses include a `detail` field with error information.

## Integration with Frontend

The API is designed to work with the React frontend in the `../frontend/` directory. It includes CORS middleware to allow cross-origin requests from web applications.

## Configuration

The API uses the configuration from `agents/config.py`. Key settings:

**API Keys:**
- `OPENAI_API_KEY`: Required for LLM operations
- `SUPABASE_URL`: Optional, for authentication
- `SUPABASE_ANON_KEY`: Optional, for authentication

**Search Settings:**
- `MAX_RESULTS_PER_SEARCH`: Maximum search results per query (default: 2)
- `MAX_CONTENT_LENGTH`: Maximum content length to extract (default: 2000)
- `REQUEST_TIMEOUT`: HTTP request timeout in seconds (default: 10)
- `RATE_LIMIT_DELAY`: Delay between API calls (default: 1.0)

**Model Settings:**
- `MODEL_NAME`: OpenAI model to use (default: "gpt-5-nano-2025-08-07")
- Can be changed to "gpt-4", "gpt-3.5-turbo", etc.

**Research Settings:**
- `ENABLE_ITERATIVE_RESEARCH`: Enable multi-round research (default: True)
- `MAX_RESEARCH_ITERATIONS`: Maximum research rounds (default: 2)

**Trust System:**
- Configured in `trusted_domains.py`
- Includes major universities, government sites, scientific publishers
- Trust scores range from 75-95

## Development

### Running in Development Mode

```bash
# With auto-reload
python api.py

# Or using uvicorn directly
uvicorn api:app --reload --host 0.0.0.0 --port 8000

# With custom port
uvicorn api:app --reload --host 0.0.0.0 --port 8080
```

### Development Tools

**Interactive API Documentation:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

**Testing:**
```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=agents tests/
```

## Production Deployment

### Using Gunicorn with Uvicorn Workers

```bash
gunicorn api:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Using Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t aideepsearch-api .
docker run -p 8000:8000 -e OPENAI_API_KEY=your_key aideepsearch-api
```

## Performance Considerations

- **Async Operations**: All I/O operations are asynchronous for better performance
- **Rate Limiting**: Configurable delays between API calls to respect rate limits
- **Timeouts**: HTTP requests have configurable timeouts to prevent hanging
- **Streaming**: SSE streaming reduces perceived latency for long-running requests

## Security Best Practices

- **Never expose API keys**: Use environment variables, not hardcoded values
- **CORS Configuration**: Update `allow_origins` in production to specific domains
- **Input Validation**: All queries are validated before processing
- **Prompt Injection Protection**: Security measures in all agent prompts
- **Rate Limiting**: Consider adding rate limiting middleware for production

## Monitoring and Logging

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# View logs
# Logs show progress through research pipeline
# Including search results, agent processing, and errors
```

## Troubleshooting

### Common Issues

**"OpenAI API Key not found"**
- Ensure `.env` file exists with correct key
- Check environment variable is loaded: `echo $OPENAI_API_KEY`

**"Port already in use"**
- Change port: `uvicorn api:app --port 8001`
- Or kill process using port 8000

**"Module not found"**
- Reinstall dependencies: `pip install -r requirements.txt`
- Ensure virtual environment is activated

**Slow responses**
- Adjust `MAX_RESULTS_PER_SEARCH` to lower value
- Increase `RATE_LIMIT_DELAY` if hitting rate limits
- Check internet connection and DuckDuckGo availability

## API Limits

**OpenAI API:**
- Rate limits depend on your OpenAI tier
- Free tier: Lower rate limits
- Paid tier: Higher limits and better models

**DuckDuckGo Search:**
- Free search API
- May have rate limiting
- Use reasonable delays between requests

## Additional Resources

- [API Architecture Documentation](../ARCHITECTURE.md)
- [Developer Guide](../DEVELOPER_GUIDE.md)
- [Contributing Guidelines](../CONTRIBUTING.md)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [OpenAI API Documentation](https://platform.openai.com/docs)


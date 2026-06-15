# DeepDive Agent

A multi-agent research assistant powered by **LangGraph**, **Claude**, and **Tavily Search API**. Breaks down complex queries into focused sub-questions, runs parallel web searches, and synthesizes results into a comprehensive, source-cited answer.

## Architecture

```
Query
  │
  ▼
┌─────────────┐
│   Planner   │  (Claude) breaks query → 2–4 sub-questions
└─────────────┘
  │
  ├──▶ [Search 1] ──┐
  ├──▶ [Search 2] ──┤  (Tavily) parallel web search per sub-question
  └──▶ [Search 3] ──┤
                    │
                    ▼
            ┌──────────────────┐
            │   Summarizer     │  (Claude) synthesizes + cites sources
            └──────────────────┘
                    │
                   END
```

## Features

- **Parallel execution** — Sub-questions searched in parallel (via LangGraph `Send` API)
- **Source attribution** — Every claim in the final answer is cited with URLs
- **Fast iteration** — Local development with hot reload, Docker-ready
- **Production-grade logging** — Structured logs for debugging and monitoring

## Quick Start

### Local Setup

1. **Clone and install:**
   ```bash
   cd deepdive-ai
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and fill in:
   # - ANTHROPIC_API_KEY=sk-...
   # - TAVILY_API_KEY=...
   ```

3. **Start the server:**
   ```bash
   uvicorn api.main:app --reload
   ```

4. **Test it:**
   ```bash
   curl -X POST http://localhost:8000/research \
     -H "Content-Type: application/json" \
     -d '{"query": "What is machine learning and what are its applications?"}'
   ```

### Docker

```bash
# Build and run
docker compose up --build

# In another terminal
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"query": "latest advances in quantum computing"}'
```

## API

### `POST /research`

**Request:**
```json
{
  "query": "What is machine learning?"
}
```

**Response:**
```json
{
  "query": "What is machine learning?",
  "final_answer": "Machine learning is...\n\n[1] defines ML as...\n\n## Sources\n[1] https://example.com/ml-guide",
  "sources": ["https://example.com/ml-guide", "https://example.com/ai-trends"]
}
```

### `GET /health`

Returns `{"status": "ok"}` for healthchecks.

### `GET /cache/stats`

Get cache statistics:
```json
{"size": 5, "max_size": 100, "ttl_seconds": 3600}
```

### `DELETE /cache`

Clear all cached entries:
```json
{"message": "Cache cleared"}
```

### `POST /research/stream`

Stream research progress and final answer in real-time using newline-delimited JSON.

**Request:**
```json
{"query": "What is machine learning?"}
```

**Response stream (NDJSON):**
```json
{"event": "planning", "query": "What is machine learning?"}
{"event": "searching", "sub_questions": [...], "num_results": 15}
{"event": "summarizing"}
{"event": "token", "data": "Machine"}
{"event": "token", "data": " learning"}
{"event": "token", "data": " is"}
...
{"event": "complete", "sources": ["https://...", "https://..."]}
```

**Events:**
- `planning` — planner is decomposing the query
- `searching` — search results gathered
- `summarizing` — Claude is synthesizing the answer
- `token` — single token of the final answer (stream these to show real-time typing)
- `complete` — done, includes sources
- `cached` — result was cached (entire response in one event)
- `error` — something went wrong

**Example: curl with jq to pretty-print**
```bash
curl -X POST http://localhost:8000/research/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "What is machine learning?"}' \
  | jq -R 'fromjson?' 2>/dev/null
```

**Example: Python client**
```bash
python examples_stream_client.py "What is machine learning?"
```

## Project Structure

```
deepdive-ai/
├── agents/
│   ├── state.py          # AgentState Typedicts
│   ├── planner.py        # Query decomposition node
│   ├── search.py         # Parallel Tavily search nodes
│   ├── summarizer.py     # Result synthesis node (+ streaming variant)
│   ├── graph.py          # LangGraph wiring
│   ├── cache.py          # Response caching with TTL
│   ├── retry.py          # Exponential backoff retry logic
│   └── logging_config.py # Structured logging
├── api/
│   └── main.py           # FastAPI app (+ streaming endpoint)
├── examples/
│   └── stream_client.py  # Example streaming client
├── tests/
│   ├── conftest.py       # Pytest fixtures
│   ├── test_planner.py   # Planner unit tests
│   ├── test_search.py    # Search unit tests
│   ├── test_cache.py     # Cache unit tests
│   └── test_retry.py     # Retry logic unit tests
├── requirements.txt
├── .env.example
├── Dockerfile
└── docker-compose.yml
```

## Running Tests

```bash
pytest tests/
# With coverage:
pytest tests/ --cov=agents --cov-report=html
```

## Streaming vs Non-Streaming

**`POST /research` (non-streaming):**
- Waits for full pipeline to complete
- Returns single JSON response
- Simpler for clients
- Good for: batch processing, APIs that need final result only

**`POST /research/stream` (streaming):**
- Returns events as they happen
- Shows real-time progress to user
- Tokens stream as Claude writes the answer
- Good for: web UIs, real-time feedback, better UX

**When to use streaming:**
- User is waiting in real-time (web browser)
- Query is complex and takes 10+ seconds
- Want to show "typing" effect of Claude's response

**When NOT to use streaming:**
- Batch/automated processing
- Client can't handle newline-delimited JSON
- Need traditional request/response cycle

### 1. Technical Deep-Dive
```bash
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the key differences between LangGraph and AutoGen for building multi-agent systems?"}'
```

### 2. Current Events + Analysis
```bash
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the current state of fusion energy research and when might it become commercially viable?"}'
```

### 3. Conceptual Explanation
```bash
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"query": "How does the transformer attention mechanism work and what are its main limitations?"}'
```

## Logging

Logs are written to stdout with timestamps and levels:

```
[2026-06-15 10:30:45] deepdive - INFO - POST /research: What is AI?
[2026-06-15 10:30:46] deepdive - INFO - Planning query: What is AI?
[2026-06-15 10:30:47] deepdive - INFO - Generated 3 sub-questions: [...]
[2026-06-15 10:30:48] deepdive - INFO - Searching: What is artificial intelligence?
...
```

To adjust log level, set `DEEPDIVE_LOG_LEVEL=DEBUG` in `.env`.

## Caching

By default, research results are cached in-memory with a 1-hour TTL (time-to-live). Identical queries return cached results instantly.

**Cache behavior:**
- **Query normalization** — `"What is AI?"` and `"  what is ai?  "` are treated as the same query
- **TTL** — Cached entries expire after the configured TTL; expired entries are removed on access
- **Size limit** — When the cache reaches max capacity, the oldest entry is evicted
- **Lookup speed** — Queries are hashed for O(1) lookup

**Control caching:**
```bash
# Check cache stats
curl http://localhost:8000/cache/stats

# Clear cache
curl -X DELETE http://localhost:8000/cache
```

**Configure caching:**
Set these in `.env`:
- `CACHE_TTL_SECONDS=3600` — How long to keep results (default 1 hour)
- `CACHE_MAX_SIZE=100` — Maximum cached queries (default 100)

## Retry Logic

API calls are automatically retried on transient failures with exponential backoff.

**Retryable errors:**
- Timeouts
- Rate limits (429)
- Temporary unavailability (502, 503)
- Connection errors

**Non-retryable errors (fail immediately):**
- Authentication failures
- Invalid input
- 404 Not Found
- Other permanent errors

**Retry behavior:**
- Up to 3 retry attempts per call (configurable)
- Initial delay: 1 second, doubles on each retry (1s → 2s → 4s)
- Maximum delay: 60 seconds
- Jitter added to prevent thundering herd

**Example log output:**
```
[WARN] search_node attempt 1/4 failed: Timeout. Retrying in 1.05s...
[WARN] search_node attempt 2/4 failed: Timeout. Retrying in 2.08s...
[INFO] Found 5 sources for: What is machine learning?
```

Retry configuration is built-in with sensible defaults. For custom retry behavior, edit `RetryConfig` in `agents/retry.py`.

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | — | Anthropic API key for Claude |
| `TAVILY_API_KEY` | Yes | — | Tavily Search API key |
| `DEEPDIVE_LOG_LEVEL` | No | `INFO` | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `CACHE_TTL_SECONDS` | No | `3600` | Cache entry lifetime in seconds (1 hour) |
| `CACHE_MAX_SIZE` | No | `100` | Maximum number of cached queries |

## Next Steps / Future Improvements

- [x] Response caching — cache recent queries with TTL
- [x] Better error recovery — retry logic with exponential backoff for transient failures
- [x] Streaming responses — stream the final answer as it's generated
- [ ] Configuration file — move hardcoded values (model names, search depth) to `config.yaml`
- [ ] Conversation history — accept `previous_context` to enable follow-up questions
- [ ] Source ranking — deduplicate and rank sources by relevance/authority
- [ ] Metrics/tracing — emit latency and token-usage metrics for monitoring
- [ ] Redis caching — scale caching across multiple workers with Redis backend

## License

MIT

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

## Project Structure

```
deepdive-ai/
├── agents/
│   ├── state.py          # AgentState Typedicts
│   ├── planner.py        # Query decomposition node
│   ├── search.py         # Parallel Tavily search nodes
│   ├── summarizer.py     # Result synthesis node
│   ├── graph.py          # LangGraph wiring
│   └── logging_config.py # Structured logging
├── api/
│   └── main.py           # FastAPI app
├── tests/
│   ├── conftest.py       # Pytest fixtures
│   ├── test_planner.py   # Planner unit tests
│   └── test_search.py    # Search unit tests
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

## Example Queries

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

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | — | Anthropic API key for Claude |
| `TAVILY_API_KEY` | Yes | — | Tavily Search API key |
| `DEEPDIVE_LOG_LEVEL` | No | `INFO` | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

## Next Steps / Future Improvements

- [ ] Streaming responses — stream the final answer as it's generated
- [ ] Response caching — cache recent queries with TTL
- [ ] Configuration file — move hardcoded values (model names, search depth) to `config.yaml`
- [ ] Conversation history — accept `previous_context` to enable follow-up questions
- [ ] Better error recovery — retry logic with exponential backoff for transient failures
- [ ] Source ranking — deduplicate and rank sources by relevance/authority
- [ ] Metrics/tracing — emit latency and token-usage metrics for monitoring

## License

MIT

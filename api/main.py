import logging
import os
import json
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

load_dotenv()

from agents.graph import compiled_graph  # noqa: E402 — must load after dotenv
from agents.cache import ResearchCache
from agents.logging_config import logger
from agents.summarizer import summarizer_stream


class ResearchRequest(BaseModel):
    query: str


class ResearchResponse(BaseModel):
    query: str
    final_answer: str
    sources: list[str]
    cached: bool = False


cache = ResearchCache(
    ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "3600")),
    max_size=int(os.getenv("CACHE_MAX_SIZE", "100")),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Cache initialized: {cache.stats()}")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="DeepDive Agent",
    description="Multi-agent research assistant powered by LangGraph + Claude",
    version="0.1.0",
    lifespan=lifespan,
)


@app.post("/research", response_model=ResearchResponse)
async def research(request: ResearchRequest):
    if not request.query.strip():
        raise HTTPException(status_code=422, detail="Query must not be empty")

    logger.info(f"POST /research: {request.query}")

    # Check cache first
    cached_result = cache.get(request.query)
    if cached_result is not None:
        logger.info("Cache hit")
        return ResearchResponse(
            query=request.query,
            final_answer=cached_result["final_answer"],
            sources=cached_result["sources"],
            cached=True,
        )

    logger.info("Cache miss — running graph")

    initial_state = {
        "query": request.query,
        "sub_questions": [],
        "search_results": [],
        "final_answer": "",
        "sources": [],
    }

    try:
        result = await compiled_graph.ainvoke(initial_state)
    except Exception as exc:
        logger.error(f"Graph execution failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    # Cache the result
    cache.set(request.query, result)

    logger.info(f"Research complete: {len(result['sources'])} sources cited")
    return ResearchResponse(
        query=request.query,
        final_answer=result["final_answer"],
        sources=result["sources"],
        cached=False,
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


async def _stream_generator(query: str):
    """
    Generator that yields SSE events:
    - planning: planner is working
    - searching: parallel searches complete
    - token: single token of the final answer
    - complete: done, includes sources
    """
    # Check cache
    cached_result = cache.get(query)
    if cached_result is not None:
        logger.info("Cache hit (streaming)")
        yield json.dumps({
            "event": "cached",
            "query": query,
            "final_answer": cached_result["final_answer"],
            "sources": cached_result["sources"],
        }) + "\n"
        return

    logger.info("Cache miss — running graph (streaming)")

    initial_state = {
        "query": query,
        "sub_questions": [],
        "search_results": [],
        "final_answer": "",
        "sources": [],
    }

    # Run planner + searches
    yield json.dumps({"event": "planning", "query": query}) + "\n"

    try:
        result = await compiled_graph.ainvoke(initial_state)
    except Exception as exc:
        logger.error(f"Graph execution failed: {exc}", exc_info=True)
        yield json.dumps({
            "event": "error",
            "message": str(exc),
        }) + "\n"
        return

    yield json.dumps({
        "event": "searching",
        "sub_questions": result["sub_questions"],
        "num_results": len(result["search_results"]),
    }) + "\n"

    # Stream the summarizer
    yield json.dumps({"event": "summarizing"}) + "\n"

    full_answer = ""
    try:
        generator = summarizer_stream(result)
        for token in generator:
            full_answer += token
            yield json.dumps({"event": "token", "data": token}) + "\n"
    except StopIteration as e:
        # Generator return value: (sources, full_answer)
        sources, _ = e.value
    except Exception as exc:
        logger.error(f"Summarizer failed: {exc}", exc_info=True)
        yield json.dumps({
            "event": "error",
            "message": str(exc),
        }) + "\n"
        return

    # Cache and send final event
    final_state = {**result, "final_answer": full_answer}
    cache.set(query, final_state)

    yield json.dumps({
        "event": "complete",
        "sources": sources,
    }) + "\n"

    logger.info(f"Research complete (streaming): {len(sources)} sources")


@app.post("/research/stream")
async def research_stream(request: ResearchRequest):
    """Stream the research process and final answer in real-time using Server-Sent Events."""
    if not request.query.strip():
        raise HTTPException(status_code=422, detail="Query must not be empty")

    logger.info(f"POST /research/stream: {request.query}")

    return StreamingResponse(
        _stream_generator(request.query),
        media_type="application/x-ndjson",  # newline-delimited JSON
    )


@app.get("/cache/stats")
async def cache_stats():
    """Get cache statistics."""
    return cache.stats()


@app.delete("/cache")
async def clear_cache():
    """Clear all cached entries."""
    logger.info("Clearing cache")
    cache.clear()
    return {"message": "Cache cleared"}

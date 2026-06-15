import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv()

from agents.graph import compiled_graph  # noqa: E402 — must load after dotenv
from agents.logging_config import logger


class ResearchRequest(BaseModel):
    query: str


class ResearchResponse(BaseModel):
    query: str
    final_answer: str
    sources: list[str]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Graph is compiled at import time; nothing async to warm up
    yield


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

    logger.info(f"Research complete: {len(result['sources'])} sources cited")
    return ResearchResponse(
        query=request.query,
        final_answer=result["final_answer"],
        sources=result["sources"],
    )


@app.get("/health")
async def health():
    return {"status": "ok"}

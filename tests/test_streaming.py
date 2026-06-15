import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from agents.state import AgentState


@pytest.mark.asyncio
async def test_stream_generator_with_cache():
    """Test that cached results return immediately."""
    from api.main import _stream_generator, cache

    query = "Test query"
    cached_state: AgentState = {
        "query": query,
        "sub_questions": ["Q1"],
        "search_results": [],
        "final_answer": "Test answer",
        "sources": ["https://example.com"],
    }

    # Pre-populate cache
    cache.set(query, cached_state)

    events = []
    async for line in _stream_generator(query):
        if line.strip():
            events.append(json.loads(line))

    assert len(events) == 1
    assert events[0]["event"] == "cached"
    assert events[0]["final_answer"] == "Test answer"

    # Clean up
    cache.clear()


@pytest.mark.asyncio
async def test_stream_generator_planning_event():
    """Test that planning event is sent."""
    from api.main import _stream_generator, cache

    query = "What is AI?"

    with patch("api.main.compiled_graph") as mock_graph:
        mock_graph.ainvoke = AsyncMock(return_value={
            "query": query,
            "sub_questions": ["Q1", "Q2"],
            "search_results": [],
            "final_answer": "",
            "sources": [],
        })

        with patch("api.main.summarizer_stream") as mock_summarizer:
            mock_summarizer.return_value = iter(["token1", "token2"])

            events = []
            try:
                async for line in _stream_generator(query):
                    if line.strip():
                        events.append(json.loads(line))
            except StopIteration:
                pass

        # Should have planning and searching events
        assert any(e["event"] == "planning" for e in events)
        assert any(e["event"] == "searching" for e in events)

    # Clean up
    cache.clear()


@pytest.mark.asyncio
async def test_stream_generator_error_handling():
    """Test that errors are properly streamed."""
    from api.main import _stream_generator, cache

    query = "Error query"

    with patch("api.main.compiled_graph") as mock_graph:
        mock_graph.ainvoke = AsyncMock(side_effect=Exception("API Error"))

        events = []
        async for line in _stream_generator(query):
            if line.strip():
                events.append(json.loads(line))

        # Should have error event
        assert any(e["event"] == "error" for e in events)

    # Clean up
    cache.clear()

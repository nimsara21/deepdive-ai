import time
import pytest
from agents.cache import ResearchCache
from agents.state import AgentState


@pytest.fixture
def cache():
    return ResearchCache(ttl_seconds=2, max_size=3)


@pytest.fixture
def sample_state() -> AgentState:
    return {
        "query": "Test query",
        "sub_questions": ["Q1"],
        "search_results": [],
        "final_answer": "Test answer",
        "sources": ["https://example.com"],
    }


def test_cache_set_and_get(cache, sample_state):
    """Test basic cache set and get."""
    query = "What is AI?"
    cache.set(query, sample_state)
    result = cache.get(query)

    assert result is not None
    assert result["final_answer"] == "Test answer"


def test_cache_miss(cache):
    """Test cache miss returns None."""
    result = cache.get("Nonexistent query")
    assert result is None


def test_cache_expiration(cache, sample_state):
    """Test that cached entries expire after TTL."""
    query = "Test query"
    cache.set(query, sample_state)

    # Should be in cache
    assert cache.get(query) is not None

    # Wait for TTL to expire
    time.sleep(2.1)

    # Should be expired
    assert cache.get(query) is None


def test_cache_query_normalization(cache, sample_state):
    """Test that queries are normalized (case-insensitive, whitespace-trimmed)."""
    query1 = "What is AI?"
    query2 = "  WHAT IS AI?  "

    cache.set(query1, sample_state)
    result = cache.get(query2)

    assert result is not None
    assert result["final_answer"] == "Test answer"


def test_cache_max_size_eviction(cache, sample_state):
    """Test that cache evicts oldest entry when max size is reached."""
    state1 = {**sample_state, "final_answer": "Answer 1"}
    state2 = {**sample_state, "final_answer": "Answer 2"}
    state3 = {**sample_state, "final_answer": "Answer 3"}
    state4 = {**sample_state, "final_answer": "Answer 4"}

    cache.set("Query 1", state1)
    time.sleep(0.1)
    cache.set("Query 2", state2)
    time.sleep(0.1)
    cache.set("Query 3", state3)
    time.sleep(0.1)
    cache.set("Query 4", state4)  # Should evict Query 1

    assert cache.get("Query 1") is None
    assert cache.get("Query 4") is not None


def test_cache_clear(cache, sample_state):
    """Test that clear empties the cache."""
    cache.set("Query 1", sample_state)
    cache.set("Query 2", sample_state)

    assert len(cache._cache) == 2
    cache.clear()
    assert len(cache._cache) == 0


def test_cache_stats(cache, sample_state):
    """Test cache statistics."""
    cache.set("Query 1", sample_state)
    stats = cache.stats()

    assert stats["size"] == 1
    assert stats["max_size"] == 3
    assert stats["ttl_seconds"] == 2

import pytest
from unittest.mock import Mock, patch
from agents.search import search_node
from agents.state import AgentState


def test_search_basic():
    """Test that search node queries Tavily and returns results."""
    state: AgentState = {
        "query": "What is machine learning?",
        "sub_questions": ["What is machine learning?"],
        "search_results": [],
        "final_answer": "",
        "sources": [],
    }

    with patch("agents.search._client") as mock_tavily:
        mock_tavily.search.return_value = {
            "answer": "Machine learning is a subset of AI.",
            "results": [
                {
                    "url": "https://example.com/1",
                    "title": "ML Basics",
                    "content": "ML is about learning from data.",
                },
                {
                    "url": "https://example.com/2",
                    "title": "ML Applications",
                    "content": "ML powers recommendation systems.",
                },
            ],
        }

        result = search_node(state)

        assert "search_results" in result
        assert len(result["search_results"]) == 1
        sr = result["search_results"][0]
        assert sr["sub_question"] == "What is machine learning?"
        assert len(sr["sources"]) == 2
        assert "https://example.com/1" in sr["sources"]
        assert "ML is about learning" in sr["content"]


def test_search_no_results():
    """Test that search node handles empty results gracefully."""
    state: AgentState = {
        "query": "Very obscure query xyz?",
        "sub_questions": ["Very obscure query xyz?"],
        "search_results": [],
        "final_answer": "",
        "sources": [],
    }

    with patch("agents.search._client") as mock_tavily:
        mock_tavily.search.return_value = {
            "answer": None,
            "results": [],
        }

        result = search_node(state)

        sr = result["search_results"][0]
        assert sr["sources"] == []
        assert sr["content"].strip() == ""


def test_search_api_failure():
    """Test that search node propagates API errors."""
    state: AgentState = {
        "query": "Test query",
        "sub_questions": ["Test query"],
        "search_results": [],
        "final_answer": "",
        "sources": [],
    }

    with patch("agents.search._client") as mock_tavily:
        mock_tavily.search.side_effect = Exception("API rate limit exceeded")

        with pytest.raises(Exception):
            search_node(state)

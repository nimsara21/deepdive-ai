import pytest
from unittest.mock import Mock, patch, MagicMock
from agents.state import AgentState


@pytest.fixture
def sample_state() -> AgentState:
    return {
        "query": "What is machine learning?",
        "sub_questions": [],
        "search_results": [],
        "final_answer": "",
        "sources": [],
    }


@pytest.fixture
def mock_llm():
    with patch("agents.planner.ChatAnthropic") as mock:
        yield mock


@pytest.fixture
def mock_tavily():
    with patch("agents.search.TavilyClient") as mock:
        yield mock

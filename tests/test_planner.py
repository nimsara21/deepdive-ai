import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from agents.planner import planner_node
from agents.state import AgentState


def test_planner_basic():
    """Test that planner breaks query into sub-questions."""
    state: AgentState = {
        "query": "How does photosynthesis work and what are its applications?",
        "sub_questions": [],
        "search_results": [],
        "final_answer": "",
        "sources": [],
    }

    with patch("agents.planner._llm") as mock_llm:
        response_data = {
            "sub_questions": [
                "What is the biological process of photosynthesis?",
                "What are the practical applications of photosynthesis in energy?",
            ]
        }
        mock_response = Mock()
        mock_response.content = json.dumps(response_data)
        mock_llm.invoke.return_value = mock_response

        result = planner_node(state)

        assert "sub_questions" in result
        assert len(result["sub_questions"]) == 2
        assert "photosynthesis" in result["sub_questions"][0].lower()


def test_planner_with_markdown_fences():
    """Test that planner handles JSON wrapped in markdown code fences."""
    state: AgentState = {
        "query": "What is AI?",
        "sub_questions": [],
        "search_results": [],
        "final_answer": "",
        "sources": [],
    }

    with patch("agents.planner._llm") as mock_llm:
        response_data = {
            "sub_questions": [
                "What is artificial intelligence?",
                "What are applications of AI?",
                "What are the limitations of AI?",
            ]
        }
        # Simulate markdown-wrapped response
        mock_response = Mock()
        mock_response.content = f"```json\n{json.dumps(response_data)}\n```"
        mock_llm.invoke.return_value = mock_response

        result = planner_node(state)

        assert len(result["sub_questions"]) == 3


def test_planner_invalid_json():
    """Test that planner raises error on invalid JSON."""
    state: AgentState = {
        "query": "What is AI?",
        "sub_questions": [],
        "search_results": [],
        "final_answer": "",
        "sources": [],
    }

    with patch("agents.planner._llm") as mock_llm:
        mock_response = Mock()
        mock_response.content = "not valid json"
        mock_llm.invoke.return_value = mock_response

        with pytest.raises(ValueError):
            planner_node(state)


def test_planner_missing_field():
    """Test that planner raises error when response is missing sub_questions."""
    state: AgentState = {
        "query": "What is AI?",
        "sub_questions": [],
        "search_results": [],
        "final_answer": "",
        "sources": [],
    }

    with patch("agents.planner._llm") as mock_llm:
        mock_response = Mock()
        mock_response.content = json.dumps({"wrong_field": ["test"]})
        mock_llm.invoke.return_value = mock_response

        with pytest.raises(ValueError):
            planner_node(state)

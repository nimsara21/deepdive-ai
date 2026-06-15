from langgraph.graph import StateGraph, END
from langgraph.constants import Send

from .state import AgentState
from .planner import planner_node
from .search import search_node
from .summarizer import summarizer_node


def _fan_out_searches(state: AgentState) -> list[Send]:
    """
    After the planner runs, dispatch one Search node per sub-question.
    Each Send passes a state slice where sub_questions holds exactly
    the one question that node is responsible for.
    """
    return [
        Send("search", {**state, "sub_questions": [q]})
        for q in state["sub_questions"]
    ]


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("planner", planner_node)
    graph.add_node("search", search_node)
    graph.add_node("summarizer", summarizer_node)

    # Entry point
    graph.set_entry_point("planner")

    # Fan-out: planner → N parallel search nodes (one per sub-question)
    graph.add_conditional_edges("planner", _fan_out_searches)

    # Fan-in: all search nodes → summarizer (operator.add merges search_results)
    graph.add_edge("search", "summarizer")

    graph.add_edge("summarizer", END)

    return graph.compile()


# Module-level compiled graph — import this in api/main.py
compiled_graph = build_graph()

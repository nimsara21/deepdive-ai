from tavily import TavilyClient

from .state import AgentState, SearchResult

_client = TavilyClient()  # reads TAVILY_API_KEY from environment


def search_node(state: AgentState) -> dict:
    """
    Called once per sub-question via LangGraph Send.
    state["sub_questions"] contains exactly one question in fan-out mode
    because Send passes a modified state slice to each invocation.
    """
    sub_question = state["sub_questions"][0]

    response = _client.search(
        query=sub_question,
        max_results=5,
        search_depth="advanced",
        include_answer=True,
    )

    sources = [r["url"] for r in response.get("results", [])]
    content_parts = []

    if response.get("answer"):
        content_parts.append(response["answer"])

    for r in response.get("results", []):
        title = r.get("title", "")
        snippet = r.get("content", "")
        if title or snippet:
            content_parts.append(f"[{title}] {snippet}")

    result: SearchResult = {
        "sub_question": sub_question,
        "content": "\n\n".join(content_parts),
        "sources": sources,
    }

    return {"search_results": [result]}

import logging
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from .state import AgentState
from .logging_config import logger

_llm = ChatAnthropic(model="claude-opus-4-8", temperature=0)

_SYSTEM = """You are a research synthesizer. You receive a user query and a set of
search results gathered for specific sub-questions. Your job is to write a
comprehensive, well-structured answer that:

1. Directly addresses the original query
2. Synthesizes information across all sub-questions
3. Cites sources inline using [1], [2], etc. that correspond to the numbered
   source list you are given
4. Is factual — only state what is supported by the search results
5. Is written in clear prose (use headers or bullets only if it genuinely helps)

End your response with a "## Sources" section listing the URLs in the same
numbered order you cited them inline.
"""


def _build_context(state: AgentState) -> str:
    lines = [f"Original query: {state['query']}\n"]

    all_sources: list[str] = []
    source_index: dict[str, int] = {}  # url -> citation number

    for result in state["search_results"]:
        lines.append(f"### Sub-question: {result['sub_question']}")
        lines.append(result["content"])

        for url in result["sources"]:
            if url not in source_index:
                source_index[url] = len(all_sources) + 1
                all_sources.append(url)

        lines.append("")

    lines.append("### Numbered source list (use these numbers for inline citations)")
    for i, url in enumerate(all_sources, 1):
        lines.append(f"[{i}] {url}")

    return "\n".join(lines), all_sources


def summarizer_node(state: AgentState) -> dict:
    logger.info(f"Summarizing {len(state['search_results'])} search results")
    context, sources = _build_context(state)

    response = _llm.invoke([
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=context),
    ])

    logger.info(f"Generated final answer with {len(sources)} sources")
    return {
        "final_answer": response.content,
        "sources": sources,
    }

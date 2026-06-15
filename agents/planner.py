import json
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from .state import AgentState

_llm = ChatAnthropic(model="claude-opus-4-8", temperature=0)

_SYSTEM = """You are a research planner. Given a user query, decompose it into 2-4
focused sub-questions that together cover the topic comprehensively. Each sub-question
should be self-contained and searchable on its own.

Respond with a JSON object in this exact format:
{
  "sub_questions": ["question 1", "question 2", "question 3"]
}

Rules:
- 2 sub-questions minimum, 4 maximum
- Each sub-question should be specific and targeted, not vague
- Together they should fully address the original query
- Do not number the questions inside the strings
"""


def planner_node(state: AgentState) -> dict:
    query = state["query"]

    response = _llm.invoke([
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=f"Query: {query}"),
    ])

    text = response.content
    # Strip markdown code fences if present
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]

    parsed = json.loads(text.strip())
    sub_questions: list[str] = parsed["sub_questions"]

    return {"sub_questions": sub_questions}

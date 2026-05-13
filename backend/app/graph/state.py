from typing import TypedDict


class AgentState(TypedDict):
    kb_id: str
    question: str
    top_k: int
    history: str
    intent: str
    retrieval_results: list[dict]
    tool_result: dict | None
    answer: str
    sources: list[dict]
    error: str | None

import logging

from langgraph.graph import END, StateGraph

from app.graph.nodes import (
    clarification_node,
    intent_classifier,
    kb_qa_node,
    tool_executor_node,
)
from app.graph.state import AgentState
from app.integrations.llm import LLMClient
from app.services.rag_service import RAGService
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# 所有工具意图走同一个节点
TOOL_INTENTS = frozenset({
    "query_inventory",
    "query_order_status",
    "query_material_price",
    "query_wmstask_status",
    "query_purchase_plan",
    "query_invoice_status",
})


def _route_by_intent(state: AgentState) -> str:
    """条件边路由：根据意图选择后续节点。"""
    intent = state.get("intent", "kb_qa")
    if intent in TOOL_INTENTS:
        return "tool_executor"
    if intent == "clarification_required":
        return "clarification"
    return "kb_qa"


def build_graph(
    rag_service: RAGService,
    llm_client: LLMClient,
    tool_registry: ToolRegistry,
) -> StateGraph:
    """构建意图识别 → 路由 → 处理的 LangGraph 图。"""
    graph = StateGraph(AgentState)

    async def run_intent_classifier(state: AgentState) -> dict:
        return await intent_classifier(state, llm_client)

    async def run_kb_qa(state: AgentState) -> dict:
        return await kb_qa_node(state, rag_service)

    async def run_tool_executor(state: AgentState) -> dict:
        return await tool_executor_node(state, tool_registry, llm_client)

    async def run_clarification(state: AgentState) -> dict:
        return await clarification_node(state)

    # 注册节点
    graph.add_node("intent_classifier", run_intent_classifier)
    graph.add_node("kb_qa", run_kb_qa)
    graph.add_node("tool_executor", run_tool_executor)
    graph.add_node("clarification", run_clarification)

    # 边
    graph.set_entry_point("intent_classifier")
    graph.add_conditional_edges(
        "intent_classifier",
        _route_by_intent,
        {
            "kb_qa": "kb_qa",
            "tool_executor": "tool_executor",
            "clarification": "clarification",
        },
    )
    graph.add_edge("kb_qa", END)
    graph.add_edge("tool_executor", END)
    graph.add_edge("clarification", END)

    return graph


async def run_graph(
    graph: StateGraph,
    kb_id: str,
    question: str,
    top_k: int = 5,
    history: str = "",
) -> AgentState:
    """运行图，返回最终状态。"""
    compiled = graph.compile()
    initial_state: AgentState = {
        "kb_id": kb_id,
        "question": question,
        "top_k": top_k,
        "history": history,
        "intent": "kb_qa",
        "retrieval_results": [],
        "tool_result": None,
        "answer": "",
        "sources": [],
        "error": None,
    }
    result = await compiled.ainvoke(initial_state)
    return result

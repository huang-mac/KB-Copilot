import json
import logging

from app.graph.state import AgentState
from app.integrations.llm import LLMClient
from app.services.rag_service import RAGService
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

INTENT_SYSTEM_PROMPT = """你是一个企业业务查询意图分类器。根据用户问题判断意图，只返回以下标签之一，不要返回任何其他内容：

- kb_qa：用户想要从知识库、文档或资料中查找信息、询问业务知识、操作流程、技术问题等。
- query_inventory：用户查询物料库存信息（库存数量、可用量、仓库分布等），问题中通常包含物料编码或物料名称。
- query_order_status：用户查询销售订单的发货状态、物流信息、签收情况等，问题中包含销售订单号。
- query_material_price：用户查询物料的成本价或销售价，问题中包含物料编码。
- query_wmstask_status：用户查询 WMS 仓库任务进度（拣货、复核、装车等），问题中包含 WMS 任务号或关联订单号。
- query_purchase_plan：用户查询未来的采购到货计划、预计到货时间、数量等。
- query_invoice_status：用户查询发票的开票或收票状态，问题中包含发票号或关联订单号。
- clarification_required：用户输入的是闲聊、问候、无法识别的内容，或信息严重不足无法判断意图。"""

TOOL_INTENTS = frozenset({
    "query_inventory",
    "query_order_status",
    "query_material_price",
    "query_wmstask_status",
    "query_purchase_plan",
    "query_invoice_status",
})

PARAM_EXTRACT_PROMPT = """根据用户问题提取工具调用参数。只返回 JSON 格式的参数对象，不要返回任何其他内容。

工具名称：{tool_name}
工具描述：{tool_description}
参数定义：{parameters}

如果用户问题中没有明确提到某个参数，请使用合理的默认值或空字符串。"""


async def intent_classifier(state: AgentState, llm_client: LLMClient) -> dict:
    """意图识别节点：用 LLM 分类用户意图。失败时降级为 kb_qa。"""
    question = state["question"]

    valid_intents = {"kb_qa", "clarification_required"} | TOOL_INTENTS

    try:
        result = await llm_client.generate_text(
            system_prompt=INTENT_SYSTEM_PROMPT,
            user_message=question,
        )
        result = result.strip().lower()
        if result not in valid_intents:
            logger.warning("LLM returned invalid intent %r, falling back to kb_qa", result)
            result = "kb_qa"
    except Exception as exc:
        logger.warning("Intent classification failed: %s, falling back to kb_qa", exc)
        result = "kb_qa"

    return {"intent": result}


async def kb_qa_node(state: AgentState, rag_service: RAGService) -> dict:
    """知识库问答节点：检索 + 生成。"""
    try:
        answer, sources = await rag_service.answer(
            kb_id=state["kb_id"],
            question=state["question"],
            top_k=state.get("top_k", 5),
            history=_parse_history(state.get("history", "")),
        )
        return {
            "answer": answer,
            "sources": [
                {
                    "doc_id": s.doc_id,
                    "filename": s.filename,
                    "chunk_index": s.chunk_index,
                    "score": s.score,
                    "content": s.content,
                    "source_type": s.source_type,
                }
                for s in sources
            ],
        }
    except Exception as exc:
        logger.exception("kb_qa node failed")
        return {
            "answer": f"知识库检索暂时不可用，请稍后重试。（错误详情：{exc}）",
            "sources": [],
            "error": str(exc),
        }


async def tool_executor_node(
    state: AgentState,
    tool_registry: ToolRegistry,
    llm_client: LLMClient,
) -> dict:
    """通用工具执行节点：根据 intent 查找工具 → 提取参数 → 执行 → 生成回答。"""
    intent = state.get("intent", "")
    question = state["question"]

    tool = tool_registry.get(intent)
    if tool is None:
        logger.warning("No tool registered for intent %r", intent)
        return {
            "answer": f"意图 {intent} 对应的查询服务暂不可用。",
            "tool_result": None,
            "error": f"Tool '{intent}' not registered",
        }

    # 1. 提取参数：用 LLM 按工具 schema 从问题中抽取
    params = await _extract_params(llm_client, tool, question)

    # 2. 执行工具
    try:
        tool_result = await tool.execute(**params)
    except Exception as exc:
        logger.exception("Tool %s execution failed", intent)
        return {
            "answer": f"查询失败：{exc}",
            "tool_result": None,
            "error": str(exc),
        }

    # 3. 用工具结果生成自然语言回答
    try:
        answer = await llm_client.generate_answer(
            question=question,
            context=_format_tool_result(tool_result),
            history=state.get("history", ""),
        )
    except Exception as exc:
        logger.exception("LLM answer generation failed in tool_executor_node")
        answer = f"查询结果如下：\n{_format_tool_result(tool_result)}"

    return {
        "answer": answer,
        "tool_result": tool_result,
        "sources": [],
    }


async def clarification_node(state: AgentState) -> dict:
    """澄清节点：返回引导性提示，不进入 RAG 或工具调用。"""
    return {
        "answer": (
            "抱歉，我没有完全理解您的问题。您可以尝试：\n"
            "1. **查询知识库**：输入您想了解的业务问题，我会从知识库中查找答案。\n"
            "2. **查询库存**：输入物料编码（如「查 MAT-001 库存」）。\n"
            "3. **查询订单**：输入销售订单号（如「查 SO-20260501-001 发货状态」）。\n"
            "4. **查询物料价格**：输入物料编码查询成本或售价。\n"
            "5. **查询 WMS 任务**：输入 WMS 任务号查看仓库作业进度。\n"
            "6. **查询到货计划**：查询未来采购到货安排。\n"
            "7. **查询发票**：输入发票号查询开票/收票状态。\n"
            "请补充更多信息后再试。"
        ),
        "sources": [],
        "tool_result": None,
    }


def _parse_history(history: str) -> list[tuple[str, str]]:
    """将格式化的历史字符串解析回 (role, content) 列表。"""
    if not history:
        return []
    pairs: list[tuple[str, str]] = []
    for line in history.split("\n"):
        line = line.strip()
        if not line:
            continue
        if "：" in line:
            label, content = line.split("：", 1)
            role = "user" if label == "用户" else "assistant"
            pairs.append((role, content))
    return pairs


def _format_tool_result(result: dict) -> str:
    lines = []
    for key, value in result.items():
        if key.startswith("_"):
            continue
        if isinstance(value, (list, dict)):
            lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


async def _extract_params(llm_client: LLMClient, tool, question: str) -> dict:
    """用 LLM 从用户问题中提取工具调用参数。失败时返回空字典。"""
    prompt = PARAM_EXTRACT_PROMPT.format(
        tool_name=tool.name,
        tool_description=tool.description,
        parameters=json.dumps(tool.parameters, ensure_ascii=False),
    )
    try:
        raw = await llm_client.generate_text(
            system_prompt=prompt,
            user_message=question,
        )
        params = json.loads(raw.strip())
        if isinstance(params, dict):
            return params
    except (json.JSONDecodeError, Exception) as exc:
        logger.warning("Parameter extraction failed: %s", exc)
    return {}

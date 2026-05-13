from collections.abc import AsyncGenerator

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.core.config import Settings
from app.core.exceptions import ExternalProviderError


class LLMClient:
    async def generate_answer(self, *, question: str, context: str, history: str = "") -> str:
        raise NotImplementedError

    async def astream_answer(
        self, *, question: str, context: str, history: str = ""
    ) -> AsyncGenerator[str, None]:
        raise NotImplementedError

    async def generate_text(
        self, *, system_prompt: str, user_message: str
    ) -> str:
        """通用文本生成，用于意图分类等非问答场景。"""
        raise NotImplementedError

    async def generate_suggestions(
        self, *, question: str, answer: str
    ) -> list[str]:
        """基于当前问答生成 2-3 个追问建议。"""
        raise NotImplementedError


class OpenAIChatClient(LLMClient):
    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.llm_api_key
        self.chat_model = ChatOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url.rstrip("/"),
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            streaming=True,
            timeout=settings.llm_timeout_seconds,
        )

    def _build_messages(self, *, question: str, context: str, history: str = ""):
        return [
            SystemMessage(
                content=(
                    "你是一个企业知识库问答助手。"
                    "请只根据给定资料回答问题；如果资料中没有答案，"
                    "请回答\u201c根据当前知识库资料无法确认\u201d。"
                )
            ),
            HumanMessage(
                content=f"历史对话：\n{history or '无'}\n\n资料：\n{context}\n\n问题：\n{question}"
            ),
        ]

    async def generate_answer(self, *, question: str, context: str, history: str = "") -> str:
        if not self.api_key:
            raise ExternalProviderError(
                "LLM_API_KEY is required for LangChain OpenAI-compatible LLM."
            )

        messages = self._build_messages(question=question, context=context, history=history)

        try:
            response = await self.chat_model.ainvoke(messages)
        except Exception as exc:
            raise ExternalProviderError(f"LLM provider error: {exc}") from exc

        if isinstance(response.content, str):
            return response.content.strip()
        return "".join(
            str(part.get("text", part)) if isinstance(part, dict) else str(part)
            for part in response.content
        ).strip()

    async def astream_answer(
        self, *, question: str, context: str, history: str = ""
    ) -> AsyncGenerator[str, None]:
        if not self.api_key:
            raise ExternalProviderError(
                "LLM_API_KEY is required for LangChain OpenAI-compatible LLM."
            )

        messages = self._build_messages(question=question, context=context, history=history)

        try:
            async for chunk in self.chat_model.astream(messages):
                if isinstance(chunk.content, str):
                    yield chunk.content
                elif hasattr(chunk.content, "__iter__") and not isinstance(chunk.content, str):
                    for part in chunk.content:
                        text = part.get("text", part) if isinstance(part, dict) else str(part)
                        if text:
                            yield text
        except Exception as exc:
            raise ExternalProviderError(f"LLM provider error: {exc}") from exc

    async def generate_text(
        self, *, system_prompt: str, user_message: str
    ) -> str:
        if not self.api_key:
            raise ExternalProviderError(
                "LLM_API_KEY is required for LangChain OpenAI-compatible LLM."
            )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]

        try:
            response = await self.chat_model.ainvoke(messages)
        except Exception as exc:
            raise ExternalProviderError(f"LLM provider error: {exc}") from exc

        if isinstance(response.content, str):
            return response.content.strip()
        return str(response.content).strip()

    async def generate_suggestions(
        self, *, question: str, answer: str
    ) -> list[str]:
        if not self.api_key:
            return []

        try:
            result = await self.generate_text(
                system_prompt=(
                    "你是一个知识库问答助手。根据用户的问题和系统回答，生成 2-3 个可能的追问建议。"
                    "追问应该自然、有用，帮助用户深入探索话题。"
                    "只返回追问列表，每行一个，不要编号，不要其他解释。"
                ),
                user_message=(
                    f"用户问题：{question}\n\n系统回答：{answer}\n\n请生成 2-3 个追问建议："
                ),
            )
        except Exception:
            return []

        suggestions = [line.strip("- ").strip() for line in result.strip().split("\n") if line.strip()]
        return suggestions[:3]


class MockLLMClient(LLMClient):
    async def generate_answer(self, *, question: str, context: str, history: str = "") -> str:
        if not context.strip():
            return "根据当前知识库资料无法确认。"

        preview = context.strip().split("\n\n")[0]
        return (
            "这是 mock 模式生成的回答。系统已检索到与问题相关的资料片段，"
            f"可先参考：{preview[:300]}"
        )

    async def astream_answer(
        self, *, question: str, context: str, history: str = ""
    ) -> AsyncGenerator[str, None]:
        import asyncio

        if not context.strip():
            yield "根据当前知识库资料无法确认。"
            return

        preview = context.strip().split("\n\n")[0]
        answer = (
            "这是 mock 模式生成的回答。系统已检索到与问题相关的资料片段，"
            f"可先参考：{preview[:300]}"
        )
        for i, char in enumerate(answer):
            yield char
            if i % 5 == 0:
                await asyncio.sleep(0.02)

    async def generate_text(
        self, *, system_prompt: str, user_message: str
    ) -> str:
        """Mock 意图分类：基于简单关键词规则。"""
        import re

        q = user_message.lower()

        # 库存查询
        if re.search(r"库存|存货|还有多少|剩余", q):
            return "query_inventory"
        # 发票查询
        if re.search(r"发票|开票|收票|INV-", q, re.IGNORECASE):
            return "query_invoice_status"
        # WMS 任务查询
        if re.search(r"WMS|wms|拣货|复核|装车|仓库任务", q):
            return "query_wmstask_status"
        # 销售订单查询
        if re.search(r"SO-\d+|销售订单|发货|物流|签收|订单状态|订单.*状态", q, re.IGNORECASE):
            return "query_order_status"
        # 物料价格查询
        if re.search(r"价格|成本|售价|多少钱|单价", q):
            return "query_material_price"
        # 采购到货计划
        if re.search(r"到货|采购计划|PO-\d+|预计到货|在途", q, re.IGNORECASE):
            return "query_purchase_plan"

        greetings = {"hello", "hi", "你好", "嗨", "早上好", "晚上好", "再见", "bye"}
        if user_message.strip().lower() in greetings or len(user_message.strip()) <= 3:
            return "clarification_required"
        return "kb_qa"

    async def generate_suggestions(
        self, *, question: str, answer: str
    ) -> list[str]:
        """Mock 追问建议。"""
        return [
            "可以详细说明一下吗？",
            "这个问题的具体步骤是什么？",
            "还有其他相关内容吗？",
        ]


def create_llm_client(settings: Settings) -> LLMClient:
    if settings.llm_provider == "mock":
        return MockLLMClient()
    return OpenAIChatClient(settings)

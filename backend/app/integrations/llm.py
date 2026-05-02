import httpx

from app.core.config import Settings
from app.core.exceptions import ExternalProviderError


class LLMClient:
    async def generate_answer(self, *, question: str, context: str) -> str:
        raise NotImplementedError


class OpenAIChatClient(LLMClient):
    def __init__(self, settings: Settings) -> None:
        self.base_url = settings.llm_base_url.rstrip("/")
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model
        self.temperature = settings.llm_temperature
        self.timeout = settings.llm_timeout_seconds

    async def generate_answer(self, *, question: str, context: str) -> str:
        if not self.api_key:
            raise ExternalProviderError("LLM_API_KEY is required for OpenAI-compatible LLM.")

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个企业知识库问答助手。"
                    "请只根据给定资料回答问题；如果资料中没有答案，"
                    "请回答“根据当前知识库资料无法确认”。"
                ),
            },
            {
                "role": "user",
                "content": f"资料：\n{context}\n\n问题：\n{question}",
            },
        ]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": self.temperature,
                },
            )

        if response.status_code >= 400:
            raise ExternalProviderError(f"LLM provider error: {response.text}")

        data = response.json()
        return data["choices"][0]["message"]["content"].strip()


class MockLLMClient(LLMClient):
    async def generate_answer(self, *, question: str, context: str) -> str:
        if not context.strip():
            return "根据当前知识库资料无法确认。"

        preview = context.strip().split("\n\n")[0]
        return (
            "这是 mock 模式生成的回答。系统已检索到与问题相关的资料片段，"
            f"可先参考：{preview[:300]}"
        )


def create_llm_client(settings: Settings) -> LLMClient:
    if settings.llm_provider == "mock":
        return MockLLMClient()
    return OpenAIChatClient(settings)

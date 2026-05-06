import hashlib
import math

from langchain_openai import OpenAIEmbeddings

from app.core.config import Settings
from app.core.exceptions import ExternalProviderError


class EmbeddingClient:
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    async def embed_query(self, query: str) -> list[float]:
        vectors = await self.embed_texts([query])
        return vectors[0]


class OpenAIEmbeddingClient(EmbeddingClient):
    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.embedding_api_key
        self.client = OpenAIEmbeddings(
            api_key=settings.embedding_api_key,
            base_url=settings.embedding_base_url.rstrip("/"),
            model=settings.embedding_model,
            check_embedding_ctx_length=False,
        )

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key:
            raise ExternalProviderError(
                "EMBEDDING_API_KEY is required for LangChain OpenAI-compatible embedding."
            )

        try:
            return await self.client.aembed_documents(texts)
        except Exception as exc:
            raise ExternalProviderError(f"Embedding provider error: {exc}") from exc


class MockEmbeddingClient(EmbeddingClient):
    """Deterministic local embedding for smoke tests without external API keys."""

    def __init__(self, dimension: int) -> None:
        self.dimension = dimension

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = list(text.lower())
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            vector[index] += 1.0

        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


def create_embedding_client(settings: Settings) -> EmbeddingClient:
    if settings.embedding_provider == "mock":
        return MockEmbeddingClient(settings.embedding_dimension)
    return OpenAIEmbeddingClient(settings)

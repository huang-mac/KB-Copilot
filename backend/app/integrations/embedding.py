import hashlib
import math

import httpx

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
        self.base_url = settings.embedding_base_url.rstrip("/")
        self.api_key = settings.embedding_api_key
        self.model = settings.embedding_model

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key:
            raise ExternalProviderError(
                "EMBEDDING_API_KEY is required for OpenAI-compatible embedding."
            )

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "input": texts},
            )

        if response.status_code >= 400:
            raise ExternalProviderError(f"Embedding provider error: {response.text}")

        data = response.json()
        return [item["embedding"] for item in data["data"]]


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

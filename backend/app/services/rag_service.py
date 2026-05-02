from app.domain.chunks import RetrievedChunk
from app.integrations.embedding import EmbeddingClient
from app.integrations.llm import LLMClient
from app.integrations.qdrant import QdrantVectorStore


class RAGService:
    def __init__(
        self,
        *,
        embedding_client: EmbeddingClient,
        vector_store: QdrantVectorStore,
        llm_client: LLMClient,
    ) -> None:
        self.embedding_client = embedding_client
        self.vector_store = vector_store
        self.llm_client = llm_client

    async def answer(
        self,
        *,
        kb_id: str,
        question: str,
        top_k: int,
    ) -> tuple[str, list[RetrievedChunk]]:
        query_vector = await self.embedding_client.embed_query(question)
        sources = self.vector_store.search(kb_id=kb_id, query_vector=query_vector, top_k=top_k)
        context = self._build_context(sources)
        answer = await self.llm_client.generate_answer(question=question, context=context)
        return answer, sources

    def _build_context(self, sources: list[RetrievedChunk]) -> str:
        blocks = []
        for source in sources:
            blocks.append(
                "\n".join(
                    [
                        f"来源文件：{source.filename}",
                        f"片段序号：{source.chunk_index}",
                        f"内容：{source.content}",
                    ]
                )
            )
        return "\n\n".join(blocks)

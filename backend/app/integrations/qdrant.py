from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.core.config import Settings
from app.domain.chunks import DocumentChunk, RetrievedChunk


class QdrantVectorStore:
    def __init__(self, settings: Settings) -> None:
        if settings.qdrant_url == ":memory:":
            self.client = QdrantClient(":memory:")
        else:
            self.client = QdrantClient(url=settings.qdrant_url)
        self.collection_name = settings.qdrant_collection
        self.vector_size = settings.embedding_dimension

    def ensure_collection(self) -> None:
        collections = self.client.get_collections().collections
        exists = any(collection.name == self.collection_name for collection in collections)
        if exists:
            return

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=self.vector_size,
                distance=models.Distance.COSINE,
            ),
        )

    def upsert_chunks(self, chunks: list[DocumentChunk], vectors: list[list[float]]) -> None:
        self.ensure_collection()
        points = [
            models.PointStruct(
                id=chunk.id,
                vector=vector,
                payload={
                    "kb_id": chunk.kb_id,
                    "doc_id": chunk.doc_id,
                    "filename": chunk.filename,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                },
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        self.client.upsert(collection_name=self.collection_name, points=points)

    def search(self, *, kb_id: str, query_vector: list[float], top_k: int) -> list[RetrievedChunk]:
        self.ensure_collection()
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="kb_id",
                        match=models.MatchValue(value=kb_id),
                    )
                ]
            ),
            limit=top_k,
            with_payload=True,
        )

        retrieved: list[RetrievedChunk] = []
        for result in response.points:
            payload = result.payload or {}
            retrieved.append(
                RetrievedChunk(
                    id=str(result.id),
                    kb_id=str(payload.get("kb_id", "")),
                    doc_id=str(payload.get("doc_id", "")),
                    filename=str(payload.get("filename", "")),
                    chunk_index=int(payload.get("chunk_index", 0)),
                    content=str(payload.get("content", "")),
                    score=float(result.score),
                )
            )
        return retrieved

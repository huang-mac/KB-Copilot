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
            # Ensure text index exists even for pre-existing collections
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="content",
                    field_schema=models.TextIndexParams(
                        type=models.TextIndexType.TEXT,
                        tokenizer=models.TokenizerType.MULTILINGUAL,
                    ),
                )
            except Exception:
                pass  # Index may already exist
            return

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=self.vector_size,
                distance=models.Distance.COSINE,
            ),
        )
        # Create a full-text index on the content field for keyword search
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="content",
            field_schema=models.TextIndexParams(
                type=models.TextIndexType.TEXT,
                tokenizer=models.TokenizerType.MULTILINGUAL,
            ),
        )

    def upsert_chunks(
        self,
        chunks: list[DocumentChunk],
        vectors: list[list[float]],
        *,
        created_at: str,
    ) -> None:
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
                    "created_at": created_at,
                    "content": chunk.content,
                },
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        self.client.upsert(collection_name=self.collection_name, points=points)

    def delete_document(self, *, kb_id: str, doc_id: str) -> None:
        self.ensure_collection()
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="kb_id",
                            match=models.MatchValue(value=kb_id),
                        ),
                        models.FieldCondition(
                            key="doc_id",
                            match=models.MatchValue(value=doc_id),
                        ),
                    ]
                )
            ),
        )

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

    def hybrid_search(
        self, *, kb_id: str, query: str, query_vector: list[float], top_k: int
    ) -> list[RetrievedChunk]:
        """使用 Qdrant 原生 fusion 做向量 + 关键词混合检索 + RRF 融合。

        两路 prefetch：
        - 向量路：用 embedding 向量做语义召回
        - 关键词路：用 content 字段的全文索引做关键词匹配
        Qdrant 内置 RRF 融合两路结果。
        """
        self.ensure_collection()
        response = self.client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                models.Prefetch(
                    query=query_vector,
                    limit=top_k * 2,
                ),
                models.Prefetch(
                    query=models.Query(
                        text=models.QueryText(text=query),
                    ),
                    limit=top_k * 2,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
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
                    source_type="fusion",
                )
            )
        return retrieved

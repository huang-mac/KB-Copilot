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
        """向量检索 + 关键词检索 + 本地 RRF 融合。

        不同 qdrant-client 版本的原生 text query API 差异较大；这里使用稳定的
        `MatchText` filter 做关键词召回，再在应用层执行 RRF，避免依赖 QueryText。
        """
        vector_results = self.search(kb_id=kb_id, query_vector=query_vector, top_k=top_k * 2)
        keyword_results = self.keyword_search(kb_id=kb_id, query=query, top_k=top_k * 2)
        return self._rrf_fuse(
            result_sets=[vector_results, keyword_results],
            top_k=top_k,
        )

    def keyword_search(self, *, kb_id: str, query: str, top_k: int) -> list[RetrievedChunk]:
        self.ensure_collection()
        query = query.strip()
        if not query:
            return []

        try:
            points, _next_page = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="kb_id",
                            match=models.MatchValue(value=kb_id),
                        ),
                        models.FieldCondition(
                            key="content",
                            match=models.MatchText(text=query),
                        ),
                    ]
                ),
                limit=top_k,
                with_payload=True,
                with_vectors=False,
            )
        except Exception:
            points = self._contains_keyword_search(kb_id=kb_id, query=query, top_k=top_k)

        retrieved: list[RetrievedChunk] = []
        for rank, point in enumerate(points, start=1):
            payload = point.payload or {}
            retrieved.append(
                RetrievedChunk(
                    id=str(point.id),
                    kb_id=str(payload.get("kb_id", "")),
                    doc_id=str(payload.get("doc_id", "")),
                    filename=str(payload.get("filename", "")),
                    chunk_index=int(payload.get("chunk_index", 0)),
                    content=str(payload.get("content", "")),
                    score=1.0 / rank,
                    source_type="keyword",
                )
            )
        return retrieved

    def _contains_keyword_search(self, *, kb_id: str, query: str, top_k: int) -> list:
        points, _next_page = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="kb_id",
                        match=models.MatchValue(value=kb_id),
                    )
                ]
            ),
            limit=max(top_k * 10, 50),
            with_payload=True,
            with_vectors=False,
        )
        terms = [term.lower() for term in query.split() if term.strip()]
        if not terms:
            terms = [query.lower()]
        matched = []
        for point in points:
            payload = point.payload or {}
            content = str(payload.get("content", "")).lower()
            if any(term in content for term in terms):
                matched.append(point)
                if len(matched) >= top_k:
                    break
        return matched

    def _rrf_fuse(
        self,
        *,
        result_sets: list[list[RetrievedChunk]],
        top_k: int,
        rank_constant: int = 60,
    ) -> list[RetrievedChunk]:
        scores: dict[str, float] = {}
        chunks: dict[str, RetrievedChunk] = {}
        source_types: dict[str, set[str]] = {}

        for results in result_sets:
            for rank, chunk in enumerate(results, start=1):
                scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (rank_constant + rank)
                chunks[chunk.id] = chunk
                source_types.setdefault(chunk.id, set()).add(chunk.source_type)

        fused_ids = sorted(scores, key=scores.get, reverse=True)[:top_k]
        fused: list[RetrievedChunk] = []
        for chunk_id in fused_ids:
            chunk = chunks[chunk_id]
            sources = source_types.get(chunk_id, set())
            source_type = "fusion" if len(sources) > 1 else next(iter(sources), "fusion")
            fused.append(
                RetrievedChunk(
                    id=chunk.id,
                    kb_id=chunk.kb_id,
                    doc_id=chunk.doc_id,
                    filename=chunk.filename,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    score=scores[chunk_id],
                    source_type=source_type,
                )
            )
        return fused

import uuid

from app.domain.chunks import DocumentChunk
from app.integrations.embedding import EmbeddingClient
from app.integrations.qdrant import QdrantVectorStore
from app.services.document_loader import DocumentLoader
from app.services.text_splitter import TextSplitter


class DocumentIndexService:
    def __init__(
        self,
        *,
        document_loader: DocumentLoader,
        text_splitter: TextSplitter,
        embedding_client: EmbeddingClient,
        vector_store: QdrantVectorStore,
    ) -> None:
        self.document_loader = document_loader
        self.text_splitter = text_splitter
        self.embedding_client = embedding_client
        self.vector_store = vector_store

    async def index_document(
        self,
        *,
        kb_id: str,
        filename: str,
        content: bytes,
    ) -> tuple[str, list[DocumentChunk]]:
        doc_id = str(uuid.uuid4())
        text = self.document_loader.load_text(filename, content)
        chunks = self.text_splitter.split(kb_id=kb_id, doc_id=doc_id, filename=filename, text=text)
        vectors = await self.embedding_client.embed_texts([chunk.content for chunk in chunks])
        self.vector_store.upsert_chunks(chunks, vectors)
        return doc_id, chunks

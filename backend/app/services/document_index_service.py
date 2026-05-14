import uuid

from app.core.exceptions import KBError
from app.domain.chunks import DocumentChunk
from app.domain.documents import DocumentRecord
from app.integrations.embedding import EmbeddingClient
from app.integrations.minio_storage import MinioDocumentStorage
from app.integrations.qdrant import QdrantVectorStore
from app.repositories.documents import DocumentRepository
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
        document_repository: DocumentRepository,
        document_storage: MinioDocumentStorage | None = None,
    ) -> None:
        self.document_loader = document_loader
        self.text_splitter = text_splitter
        self.embedding_client = embedding_client
        self.vector_store = vector_store
        self.document_repository = document_repository
        self.document_storage = document_storage

    async def index_document(
        self,
        *,
        kb_id: str,
        filename: str,
        content: bytes,
        content_type: str | None = None,
    ) -> tuple[DocumentRecord, list[DocumentChunk]]:
        doc_id = str(uuid.uuid4())
        document = self.document_repository.create(
            kb_id=kb_id,
            doc_id=doc_id,
            filename=filename,
            status="indexing",
        )
        try:
            if self.document_storage is not None:
                self.document_storage.upload_document(
                    kb_id=kb_id,
                    doc_id=doc_id,
                    filename=filename,
                    content=content,
                    content_type=content_type,
                )
            text = self.document_loader.load_text(filename, content)
            chunks = self.text_splitter.split(
                kb_id=kb_id,
                doc_id=doc_id,
                filename=filename,
                text=text,
            )
            vectors = await self.embedding_client.embed_texts([chunk.content for chunk in chunks])
            self.vector_store.upsert_chunks(
                chunks,
                vectors,
                created_at=document.created_at.isoformat(),
            )
        except Exception as exc:
            self.document_repository.mark_failed(
                kb_id=kb_id,
                doc_id=doc_id,
                error_message=str(exc),
            )
            raise

        self.document_repository.mark_completed(
            kb_id=kb_id,
            doc_id=doc_id,
            chunk_count=len(chunks),
        )
        return self.document_repository.get(kb_id=kb_id, doc_id=doc_id) or document, chunks

    async def index_existing_document(
        self,
        *,
        kb_id: str,
        doc_id: str,
        filename: str,
        content: bytes,
        content_type: str | None = None,
    ) -> tuple[DocumentRecord, list[DocumentChunk]]:
        document = self.document_repository.get(kb_id=kb_id, doc_id=doc_id)
        if document is None:
            raise KBError("Document not found.")

        self.document_repository.update_status(kb_id=kb_id, doc_id=doc_id, status="processing")
        try:
            if self.document_storage is not None:
                self.document_storage.upload_document(
                    kb_id=kb_id,
                    doc_id=doc_id,
                    filename=filename,
                    content=content,
                    content_type=content_type,
                )
            text = self.document_loader.load_text(filename, content)
            chunks = self.text_splitter.split(
                kb_id=kb_id,
                doc_id=doc_id,
                filename=filename,
                text=text,
            )
            vectors = await self.embedding_client.embed_texts([chunk.content for chunk in chunks])
            self.vector_store.delete_document(kb_id=kb_id, doc_id=doc_id)
            self.vector_store.upsert_chunks(
                chunks,
                vectors,
                created_at=document.created_at.isoformat(),
            )
        except Exception as exc:
            self.document_repository.mark_failed(
                kb_id=kb_id,
                doc_id=doc_id,
                error_message=str(exc),
            )
            raise

        self.document_repository.mark_completed(
            kb_id=kb_id,
            doc_id=doc_id,
            chunk_count=len(chunks),
        )
        return self.document_repository.get(kb_id=kb_id, doc_id=doc_id) or document, chunks

    async def reindex_document(self, *, kb_id: str, doc_id: str) -> DocumentRecord:
        document = self.document_repository.get(kb_id=kb_id, doc_id=doc_id)
        if document is None:
            raise KBError("Document not found.")
        if self.document_storage is None:
            raise KBError("Document storage is not enabled.")

        self.document_repository.mark_indexing(kb_id=kb_id, doc_id=doc_id)
        try:
            content = self.document_storage.download_document(
                kb_id=kb_id,
                doc_id=doc_id,
                filename=document.filename,
            )
            text = self.document_loader.load_text(document.filename, content)
            chunks = self.text_splitter.split(
                kb_id=kb_id,
                doc_id=doc_id,
                filename=document.filename,
                text=text,
            )
            vectors = await self.embedding_client.embed_texts([chunk.content for chunk in chunks])
            self.vector_store.delete_document(kb_id=kb_id, doc_id=doc_id)
            self.vector_store.upsert_chunks(
                chunks,
                vectors,
                created_at=document.created_at.isoformat(),
            )
        except Exception as exc:
            self.document_repository.mark_failed(
                kb_id=kb_id,
                doc_id=doc_id,
                error_message=str(exc),
            )
            raise

        self.document_repository.mark_completed(
            kb_id=kb_id,
            doc_id=doc_id,
            chunk_count=len(chunks),
        )
        return self.document_repository.get(kb_id=kb_id, doc_id=doc_id) or document

    def list_documents(self, *, kb_id: str) -> list[DocumentRecord]:
        return self.document_repository.list_by_kb(kb_id)

    def delete_document(self, *, kb_id: str, doc_id: str) -> None:
        document = self.document_repository.get(kb_id=kb_id, doc_id=doc_id)
        if document is None:
            raise KBError("Document not found.")

        self.vector_store.delete_document(kb_id=kb_id, doc_id=doc_id)
        if self.document_storage is not None:
            self.document_storage.delete_document(
                kb_id=kb_id,
                doc_id=doc_id,
                filename=document.filename,
            )
        self.document_repository.delete(kb_id=kb_id, doc_id=doc_id)

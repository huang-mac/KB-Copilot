from functools import lru_cache

from app.core.config import Settings, get_settings
from app.integrations.embedding import create_embedding_client
from app.integrations.llm import create_llm_client
from app.integrations.qdrant import QdrantVectorStore
from app.services.document_index_service import DocumentIndexService
from app.services.document_loader import DocumentLoader
from app.services.rag_service import RAGService
from app.services.text_splitter import TextSplitter


@lru_cache
def get_vector_store() -> QdrantVectorStore:
    settings = get_settings()
    return QdrantVectorStore(settings)


@lru_cache
def get_document_index_service() -> DocumentIndexService:
    settings: Settings = get_settings()
    return DocumentIndexService(
        document_loader=DocumentLoader(),
        text_splitter=TextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        ),
        embedding_client=create_embedding_client(settings),
        vector_store=get_vector_store(),
    )


@lru_cache
def get_rag_service() -> RAGService:
    settings = get_settings()
    return RAGService(
        embedding_client=create_embedding_client(settings),
        vector_store=get_vector_store(),
        llm_client=create_llm_client(settings),
    )

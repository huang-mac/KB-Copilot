from functools import lru_cache

from app.core.config import Settings, get_settings
from app.graph.graph import build_graph
from app.integrations.embedding import create_embedding_client
from app.integrations.llm import create_llm_client
from app.integrations.minio_storage import MinioDocumentStorage
from app.integrations.qdrant import QdrantVectorStore
from app.repositories.conversations import ConversationRepository
from app.repositories.documents import DocumentRepository
from app.services.document_index_service import DocumentIndexService
from app.services.document_loader import DocumentLoader
from app.services.rag_service import RAGService
from app.services.text_splitter import TextSplitter
from app.tools.business_tools import (
    QueryInventoryTool,
    QueryInvoiceStatusTool,
    QueryMaterialPriceTool,
    QueryOrderStatusTool,
    QueryPurchasePlanTool,
    QueryWmsTaskStatusTool,
)
from app.tools.registry import ToolRegistry


@lru_cache
def get_vector_store() -> QdrantVectorStore:
    settings = get_settings()
    return QdrantVectorStore(settings)


@lru_cache
def get_document_repository() -> DocumentRepository:
    settings = get_settings()
    return DocumentRepository(settings.document_db_path)


@lru_cache
def get_conversation_repository() -> ConversationRepository:
    settings = get_settings()
    return ConversationRepository(settings.document_db_path)


@lru_cache
def get_document_storage() -> MinioDocumentStorage | None:
    settings = get_settings()
    if not settings.minio_enabled:
        return None
    return MinioDocumentStorage(settings)


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
        document_repository=get_document_repository(),
        document_storage=get_document_storage(),
    )


@lru_cache
def get_rag_service() -> RAGService:
    settings = get_settings()
    return RAGService(
        embedding_client=create_embedding_client(settings),
        vector_store=get_vector_store(),
        llm_client=create_llm_client(settings),
    )


@lru_cache
def get_llm_client():
    settings = get_settings()
    return create_llm_client(settings)


@lru_cache
def get_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(QueryInventoryTool())
    registry.register(QueryOrderStatusTool())
    registry.register(QueryMaterialPriceTool())
    registry.register(QueryWmsTaskStatusTool())
    registry.register(QueryPurchasePlanTool())
    registry.register(QueryInvoiceStatusTool())
    return registry


def get_graph():
    """返回已组装的 LangGraph 图（每次请求新建，不缓存编译产物）。"""
    settings = get_settings()
    return build_graph(
        rag_service=get_rag_service(),
        llm_client=create_llm_client(settings),
        tool_registry=get_tool_registry(),
    )

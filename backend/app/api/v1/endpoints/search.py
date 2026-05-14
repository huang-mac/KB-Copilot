from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.core.dependencies import get_rag_service
from app.schemas.chat import Source
from app.schemas.search import SearchRequest, SearchResponse
from app.services.rag_service import RAGService

router = APIRouter(prefix="/kbs/{kb_id}/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search(
    kb_id: str,
    request: SearchRequest,
    rag_service: Annotated[RAGService, Depends(get_rag_service)],
) -> SearchResponse:
    settings = get_settings()
    top_k = request.top_k or settings.top_k
    sources = await rag_service.search(kb_id=kb_id, query=request.query, top_k=top_k)
    return SearchResponse(
        query=request.query,
        sources=[
            Source(
                doc_id=source.doc_id,
                filename=source.filename,
                chunk_index=source.chunk_index,
                score=source.score,
                content=source.content,
                source_type=source.source_type,
            )
            for source in sources
        ],
    )

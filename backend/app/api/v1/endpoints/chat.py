from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import get_settings
from app.core.dependencies import get_rag_service
from app.core.exceptions import KBError
from app.schemas.chat import ChatRequest, ChatResponse, Source
from app.services.rag_service import RAGService

router = APIRouter(prefix="/kbs/{kb_id}/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    kb_id: str,
    request: ChatRequest,
    rag_service: Annotated[RAGService, Depends(get_rag_service)],
) -> ChatResponse:
    settings = get_settings()
    top_k = request.top_k or settings.top_k

    try:
        answer, sources = await rag_service.answer(
            kb_id=kb_id,
            question=request.question,
            top_k=top_k,
        )
    except KBError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return ChatResponse(
        answer=answer,
        sources=[
            Source(
                doc_id=source.doc_id,
                filename=source.filename,
                chunk_index=source.chunk_index,
                score=source.score,
                content=source.content,
            )
            for source in sources
        ],
    )

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import get_settings
from app.core.dependencies import get_conversation_repository, get_rag_service
from app.core.exceptions import KBError
from app.repositories.conversations import ConversationRepository
from app.schemas.chat import ChatRequest, ChatResponse, Source
from app.services.rag_service import RAGService

router = APIRouter(prefix="/kbs/{kb_id}/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    kb_id: str,
    request: ChatRequest,
    rag_service: Annotated[RAGService, Depends(get_rag_service)],
    conversation_repository: Annotated[
        ConversationRepository,
        Depends(get_conversation_repository),
    ],
) -> ChatResponse:
    settings = get_settings()
    top_k = request.top_k or settings.top_k

    try:
        conversation_id = request.conversation_id
        if conversation_id is None:
            conversation_id = str(uuid.uuid4())
            conversation_repository.create(
                kb_id=kb_id,
                conversation_id=conversation_id,
                title=_build_conversation_title(request.question),
            )
        elif conversation_repository.get(kb_id=kb_id, conversation_id=conversation_id) is None:
            raise KBError("Conversation not found.")

        history_messages = conversation_repository.list_messages(
            kb_id=kb_id,
            conversation_id=conversation_id,
        )
        answer, sources = await rag_service.answer(
            kb_id=kb_id,
            question=request.question,
            top_k=top_k,
            history=[(message.role, message.content) for message in history_messages],
        )
    except KBError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    source_payload = [
        {
            "doc_id": source.doc_id,
            "filename": source.filename,
            "chunk_index": source.chunk_index,
            "score": source.score,
            "content": source.content,
        }
        for source in sources
    ]
    conversation_repository.add_message(
        kb_id=kb_id,
        conversation_id=conversation_id,
        message_id=str(uuid.uuid4()),
        role="user",
        content=request.question,
    )
    conversation_repository.add_message(
        kb_id=kb_id,
        conversation_id=conversation_id,
        message_id=str(uuid.uuid4()),
        role="assistant",
        content=answer,
        sources=source_payload,
    )

    return ChatResponse(
        conversation_id=conversation_id,
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


def _build_conversation_title(question: str) -> str:
    title = question.strip().replace("\n", " ")
    if len(title) <= 30:
        return title or "新会话"
    return f"{title[:30]}..."

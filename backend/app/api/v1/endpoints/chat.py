import asyncio
import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
from app.core.dependencies import (
    get_conversation_repository,
    get_graph,
    get_rag_service,
)
from app.core.exceptions import ExternalProviderError, KBError
from app.graph.graph import run_graph
from app.repositories.conversations import ConversationRepository
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatStreamRequest,
    RegenerateRequest,
    Source,
)
from app.services.rag_service import RAGService

router = APIRouter(prefix="/kbs/{kb_id}/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    kb_id: str,
    request: ChatRequest,
    graph: Annotated[object, Depends(get_graph)],
    conversation_repository: Annotated[
        ConversationRepository,
        Depends(get_conversation_repository),
    ],
) -> ChatResponse:
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

        settings = get_settings()
        top_k = request.top_k or settings.top_k

        history_messages = conversation_repository.list_messages(
            kb_id=kb_id,
            conversation_id=conversation_id,
        )
        history_text = _build_history_text(
            [(message.role, message.content) for message in history_messages]
        )

        state = await run_graph(
            graph=graph,
            kb_id=kb_id,
            question=request.question,
            top_k=top_k,
            history=history_text,
        )

        answer = state.get("answer", "")
        sources = state.get("sources", [])
        intent = state.get("intent")
        tool_result = state.get("tool_result")
    except KBError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

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
        sources=sources if sources else None,
    )

    return ChatResponse(
        conversation_id=conversation_id,
        answer=answer,
        sources=[
            Source(
                doc_id=s.get("doc_id", ""),
                filename=s.get("filename", ""),
                chunk_index=s.get("chunk_index", 0),
                score=s.get("score", 0.0),
                content=s.get("content", ""),
            )
            for s in sources
        ],
        intent=intent,
        tool_result=tool_result,
    )


@router.post("/stream")
async def chat_stream(
    kb_id: str,
    request: ChatStreamRequest,
    http_request: Request,
    rag_service: Annotated[RAGService, Depends(get_rag_service)],
    conversation_repository: Annotated[
        ConversationRepository,
        Depends(get_conversation_repository),
    ],
):
    settings = get_settings()
    top_k = request.top_k or settings.top_k

    conversation_id = request.conversation_id
    if conversation_id is None:
        conversation_id = str(uuid.uuid4())
        conversation_repository.create(
            kb_id=kb_id,
            conversation_id=conversation_id,
            title=_build_conversation_title(request.question),
        )
    elif conversation_repository.get(kb_id=kb_id, conversation_id=conversation_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conversation not found.",
        )

    history_messages = conversation_repository.list_messages(
        kb_id=kb_id,
        conversation_id=conversation_id,
    )
    history = [(message.role, message.content) for message in history_messages]

    async def event_generator():
        collected_tokens: list[str] = []
        all_sources: list = []
        assistant_message_id = str(uuid.uuid4())

        try:
            async for event in rag_service.answer_stream(
                kb_id=kb_id,
                question=request.question,
                top_k=top_k,
                history=history,
            ):
                if await http_request.is_disconnected():
                    _persist_partial_message(
                        conversation_repository=conversation_repository,
                        kb_id=kb_id,
                        conversation_id=conversation_id,
                        question=request.question,
                        assistant_message_id=assistant_message_id,
                        content="".join(collected_tokens),
                        sources=all_sources,
                    )
                    return

                if event["type"] == "token":
                    collected_tokens.append(event["data"])
                    yield _sse_event("token", {"token": event["data"]})

                elif event["type"] == "sources":
                    all_sources = [
                        {
                            "doc_id": s.doc_id,
                            "filename": s.filename,
                            "chunk_index": s.chunk_index,
                            "score": s.score,
                            "content": s.content,
                        }
                        for s in event["data"]
                    ]
                    yield _sse_event("sources", {"sources": all_sources})

                elif event["type"] == "done":
                    full_answer = "".join(collected_tokens)
                    _persist_full_conversation(
                        conversation_repository=conversation_repository,
                        kb_id=kb_id,
                        conversation_id=conversation_id,
                        question=request.question,
                        assistant_message_id=assistant_message_id,
                        content=full_answer,
                        sources=all_sources,
                    )
                    yield _sse_event("done", {
                        "conversation_id": conversation_id,
                        "message_id": assistant_message_id,
                    })

        except ExternalProviderError as exc:
            yield _sse_event("error", {
                "error": "LLM_ERROR",
                "detail": str(exc),
            })
        except asyncio.CancelledError:
            _persist_partial_message(
                conversation_repository=conversation_repository,
                kb_id=kb_id,
                conversation_id=conversation_id,
                question=request.question,
                assistant_message_id=assistant_message_id,
                content="".join(collected_tokens),
                sources=all_sources,
            )
        except Exception as exc:
            yield _sse_event("error", {
                "error": "INTERNAL_ERROR",
                "detail": str(exc),
            })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{conversation_id}/regenerate")
async def chat_regenerate(
    kb_id: str,
    conversation_id: str,
    request: RegenerateRequest,
    http_request: Request,
    rag_service: Annotated[RAGService, Depends(get_rag_service)],
    conversation_repository: Annotated[
        ConversationRepository,
        Depends(get_conversation_repository),
    ],
):
    settings = get_settings()
    top_k = request.top_k or settings.top_k

    if conversation_repository.get(kb_id=kb_id, conversation_id=conversation_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conversation not found.",
        )

    messages = conversation_repository.list_messages(
        kb_id=kb_id,
        conversation_id=conversation_id,
    )
    last_user_msg = None
    for msg in reversed(messages):
        if msg.role == "user":
            last_user_msg = msg.content
            break

    if last_user_msg is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No user message found to regenerate.",
        )

    history_messages = [m for m in messages if m.content != last_user_msg or m.role != "user"]
    history = [(m.role, m.content) for m in history_messages]

    async def event_generator():
        collected_tokens: list[str] = []
        all_sources: list = []
        assistant_message_id = str(uuid.uuid4())

        try:
            async for event in rag_service.answer_stream(
                kb_id=kb_id,
                question=last_user_msg,
                top_k=top_k,
                history=history,
            ):
                if await http_request.is_disconnected():
                    _persist_partial_message(
                        conversation_repository=conversation_repository,
                        kb_id=kb_id,
                        conversation_id=conversation_id,
                        question=last_user_msg,
                        assistant_message_id=assistant_message_id,
                        content="".join(collected_tokens),
                        sources=all_sources,
                    )
                    return

                if event["type"] == "token":
                    collected_tokens.append(event["data"])
                    yield _sse_event("token", {"token": event["data"]})

                elif event["type"] == "sources":
                    all_sources = [
                        {
                            "doc_id": s.doc_id,
                            "filename": s.filename,
                            "chunk_index": s.chunk_index,
                            "score": s.score,
                            "content": s.content,
                        }
                        for s in event["data"]
                    ]
                    yield _sse_event("sources", {"sources": all_sources})

                elif event["type"] == "done":
                    full_answer = "".join(collected_tokens)
                    _persist_full_conversation(
                        conversation_repository=conversation_repository,
                        kb_id=kb_id,
                        conversation_id=conversation_id,
                        question=last_user_msg,
                        assistant_message_id=assistant_message_id,
                        content=full_answer,
                        sources=all_sources,
                    )
                    yield _sse_event("done", {
                        "conversation_id": conversation_id,
                        "message_id": assistant_message_id,
                    })

        except ExternalProviderError as exc:
            yield _sse_event("error", {
                "error": "LLM_ERROR",
                "detail": str(exc),
            })
        except asyncio.CancelledError:
            _persist_partial_message(
                conversation_repository=conversation_repository,
                kb_id=kb_id,
                conversation_id=conversation_id,
                question=last_user_msg,
                assistant_message_id=assistant_message_id,
                content="".join(collected_tokens),
                sources=all_sources,
            )
        except Exception as exc:
            yield _sse_event("error", {
                "error": "INTERNAL_ERROR",
                "detail": str(exc),
            })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse_event(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _persist_full_conversation(
    *,
    conversation_repository: ConversationRepository,
    kb_id: str,
    conversation_id: str,
    question: str,
    assistant_message_id: str,
    content: str,
    sources: list,
) -> None:
    conversation_repository.add_message(
        kb_id=kb_id,
        conversation_id=conversation_id,
        message_id=str(uuid.uuid4()),
        role="user",
        content=question,
    )
    conversation_repository.add_message(
        kb_id=kb_id,
        conversation_id=conversation_id,
        message_id=assistant_message_id,
        role="assistant",
        content=content,
        sources=sources,
    )


def _persist_partial_message(
    *,
    conversation_repository: ConversationRepository,
    kb_id: str,
    conversation_id: str,
    question: str,
    assistant_message_id: str,
    content: str,
    sources: list,
) -> None:
    if not content:
        return
    conversation_repository.add_message(
        kb_id=kb_id,
        conversation_id=conversation_id,
        message_id=str(uuid.uuid4()),
        role="user",
        content=question,
    )
    conversation_repository.add_message(
        kb_id=kb_id,
        conversation_id=conversation_id,
        message_id=assistant_message_id,
        role="assistant",
        content=content + " [已中断]",
        sources=sources,
    )


def _build_history_text(history: list[tuple[str, str]]) -> str:
    recent = history[-8:]
    lines = []
    for role, content in recent:
        label = "用户" if role == "user" else "助手"
        lines.append(f"{label}：{content}")
    return "\n".join(lines)


def _build_conversation_title(question: str) -> str:
    title = question.strip().replace("\n", " ")
    if len(title) <= 30:
        return title or "新会话"
    return f"{title[:30]}..."

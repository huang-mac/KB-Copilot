import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_conversation_repository
from app.core.exceptions import KBError
from app.domain.conversations import ConversationMessage, ConversationRecord
from app.repositories.conversations import ConversationRepository
from app.schemas.conversations import (
    ConversationCreateRequest,
    ConversationListResponse,
    ConversationMessageResponse,
    ConversationMessagesResponse,
    ConversationResponse,
)

router = APIRouter(prefix="/kbs/{kb_id}/conversations", tags=["conversations"])


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    kb_id: str,
    conversation_repository: Annotated[
        ConversationRepository,
        Depends(get_conversation_repository),
    ],
) -> ConversationListResponse:
    conversations = conversation_repository.list_by_kb(kb_id)
    return ConversationListResponse(
        conversations=[_to_conversation_response(conversation) for conversation in conversations]
    )


@router.post("", response_model=ConversationResponse)
async def create_conversation(
    kb_id: str,
    request: ConversationCreateRequest,
    conversation_repository: Annotated[
        ConversationRepository,
        Depends(get_conversation_repository),
    ],
) -> ConversationResponse:
    conversation = conversation_repository.create(
        kb_id=kb_id,
        conversation_id=str(uuid.uuid4()),
        title=(request.title or "新会话").strip() or "新会话",
    )
    return _to_conversation_response(conversation)


@router.get("/{conversation_id}/messages", response_model=ConversationMessagesResponse)
async def list_messages(
    kb_id: str,
    conversation_id: str,
    conversation_repository: Annotated[
        ConversationRepository,
        Depends(get_conversation_repository),
    ],
) -> ConversationMessagesResponse:
    conversation = conversation_repository.get(kb_id=kb_id, conversation_id=conversation_id)
    if conversation is None:
        raise KBError("Conversation not found.")

    messages = conversation_repository.list_messages(
        kb_id=kb_id,
        conversation_id=conversation_id,
    )
    return ConversationMessagesResponse(
        messages=[_to_message_response(message) for message in messages]
    )


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    kb_id: str,
    conversation_id: str,
    conversation_repository: Annotated[
        ConversationRepository,
        Depends(get_conversation_repository),
    ],
) -> None:
    deleted = conversation_repository.delete_conversation(
        kb_id=kb_id,
        conversation_id=conversation_id,
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")


def _to_conversation_response(conversation: ConversationRecord) -> ConversationResponse:
    return ConversationResponse(
        kb_id=conversation.kb_id,
        conversation_id=conversation.conversation_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


def _to_message_response(message: ConversationMessage) -> ConversationMessageResponse:
    return ConversationMessageResponse(
        kb_id=message.kb_id,
        conversation_id=message.conversation_id,
        message_id=message.message_id,
        role=message.role,
        content=message.content,
        sources=message.sources,
        created_at=message.created_at,
    )

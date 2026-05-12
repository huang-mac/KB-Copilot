from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.chat import Source

MessageRole = Literal["user", "assistant"]


class ConversationCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=80)


class ConversationResponse(BaseModel):
    kb_id: str
    conversation_id: str
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]


class ConversationMessageResponse(BaseModel):
    kb_id: str
    conversation_id: str
    message_id: str
    role: MessageRole
    content: str
    sources: list[Source] | None = None
    created_at: datetime


class ConversationMessagesResponse(BaseModel):
    messages: list[ConversationMessageResponse]

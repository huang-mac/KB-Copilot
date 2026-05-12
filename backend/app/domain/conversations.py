from dataclasses import dataclass
from datetime import datetime
from typing import Literal

MessageRole = Literal["user", "assistant"]


@dataclass(frozen=True)
class ConversationRecord:
    kb_id: str
    conversation_id: str
    title: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ConversationMessage:
    kb_id: str
    conversation_id: str
    message_id: str
    role: MessageRole
    content: str
    sources: list[dict] | None
    created_at: datetime

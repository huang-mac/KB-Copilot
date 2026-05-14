from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question")
    top_k: int | None = Field(default=None, ge=1, le=20)
    conversation_id: str | None = None


class ChatStreamRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=20)
    conversation_id: str | None = None


class RegenerateRequest(BaseModel):
    top_k: int | None = Field(default=None, ge=1, le=20)


class Source(BaseModel):
    doc_id: str
    filename: str
    chunk_index: int
    score: float
    content: str
    source_type: str | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    sources: list[Source]
    intent: str | None = None
    tool_result: dict | None = None

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question")
    top_k: int | None = Field(default=None, ge=1, le=20)
    conversation_id: str | None = None


class Source(BaseModel):
    doc_id: str
    filename: str
    chunk_index: int
    score: float
    content: str


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    sources: list[Source]

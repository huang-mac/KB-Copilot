from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question")
    top_k: int | None = Field(default=None, ge=1, le=20)


class Source(BaseModel):
    doc_id: str
    filename: str
    chunk_index: int
    score: float
    content: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]

from pydantic import BaseModel, Field

from app.schemas.chat import Source


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=20)


class SearchResponse(BaseModel):
    query: str
    sources: list[Source]

from pydantic import BaseModel


class SuggestionRequest(BaseModel):
    question: str
    answer: str
    conversation_id: str | None = None


class SuggestionResponse(BaseModel):
    suggestions: list[str]

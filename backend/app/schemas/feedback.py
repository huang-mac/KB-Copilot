from pydantic import BaseModel


class FeedbackRequest(BaseModel):
    message_id: str
    rating: str  # "helpful" | "not_helpful"


class FeedbackResponse(BaseModel):
    message: str

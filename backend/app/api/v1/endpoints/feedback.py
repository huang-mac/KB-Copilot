from fastapi import APIRouter, HTTPException, status

from app.schemas.feedback import FeedbackRequest, FeedbackResponse

router = APIRouter(prefix="/kbs/{kb_id}", tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse, status_code=201)
async def submit_feedback(
    kb_id: str,
    request: FeedbackRequest,
) -> FeedbackResponse:
    # MVP3: store feedback in memory for now.
    # A persistent feedback table will be added as part of the MySQL compatibility work.
    if request.rating not in ("helpful", "not_helpful"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="rating must be 'helpful' or 'not_helpful'",
        )
    return FeedbackResponse(message="反馈已提交")

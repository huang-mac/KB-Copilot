from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.dependencies import get_llm_client
from app.integrations.llm import LLMClient
from app.schemas.suggestions import SuggestionRequest, SuggestionResponse

router = APIRouter(prefix="/kbs/{kb_id}", tags=["suggestions"])


@router.post("/suggestions", response_model=SuggestionResponse)
async def get_suggestions(
    kb_id: str,
    request: SuggestionRequest,
    llm_client: Annotated[LLMClient, Depends(get_llm_client)],
) -> SuggestionResponse:
    suggestions = await llm_client.generate_suggestions(
        question=request.question,
        answer=request.answer,
    )
    return SuggestionResponse(suggestions=suggestions)

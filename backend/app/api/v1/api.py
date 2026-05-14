from fastapi import APIRouter

from app.api.v1.endpoints import (
    chat,
    conversations,
    documents,
    feedback,
    health,
    index_jobs,
    metrics,
    search,
    suggestions,
    tools,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(documents.router)
api_router.include_router(index_jobs.router)
api_router.include_router(search.router)
api_router.include_router(conversations.router)
api_router.include_router(chat.router)
api_router.include_router(tools.router)
api_router.include_router(feedback.router)
api_router.include_router(suggestions.router)
api_router.include_router(metrics.router)

from fastapi import APIRouter

from app.api.v1.endpoints import chat, conversations, documents, feedback, health, suggestions, tools

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(documents.router)
api_router.include_router(conversations.router)
api_router.include_router(chat.router)
api_router.include_router(tools.router)
api_router.include_router(feedback.router)
api_router.include_router(suggestions.router)

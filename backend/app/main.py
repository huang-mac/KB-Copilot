from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.core.config import get_settings
from app.core.exceptions import KBError
from app.core.logging import configure_logging

configure_logging()
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="A lightweight RAG knowledge base assistant powered by FastAPI and Qdrant.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(KBError)
async def kb_error_handler(_request: Request, exc: KBError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "KB Copilot API", "docs": "/docs"}


app.include_router(api_router, prefix=settings.api_prefix)

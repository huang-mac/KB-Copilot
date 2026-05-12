from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

DocumentStatus = Literal["indexing", "completed", "failed"]


class DocumentResponse(BaseModel):
    kb_id: str = Field(..., description="Knowledge base id")
    doc_id: str = Field(..., description="Document id")
    filename: str
    chunk_count: int
    status: DocumentStatus
    created_at: datetime
    error_message: str | None = None


class DocumentUploadResponse(DocumentResponse):
    message: str


class DocumentReindexResponse(DocumentResponse):
    message: str


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]


class DocumentDeleteResponse(BaseModel):
    kb_id: str = Field(..., description="Knowledge base id")
    doc_id: str = Field(..., description="Document id")
    message: str

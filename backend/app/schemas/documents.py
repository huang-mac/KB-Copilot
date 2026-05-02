from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    kb_id: str = Field(..., description="Knowledge base id")
    doc_id: str = Field(..., description="Document id")
    filename: str
    chunk_count: int
    message: str

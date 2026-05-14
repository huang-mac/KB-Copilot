from datetime import datetime

from pydantic import BaseModel


class IndexJobResponse(BaseModel):
    kb_id: str
    job_id: str
    doc_id: str
    filename: str
    status: str
    created_at: datetime
    updated_at: datetime
    content_type: str | None = None
    error_message: str | None = None

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

IndexJobStatus = Literal["queued", "processing", "completed", "failed"]


@dataclass(frozen=True)
class IndexJob:
    kb_id: str
    job_id: str
    doc_id: str
    filename: str
    status: IndexJobStatus
    created_at: datetime
    updated_at: datetime
    content_type: str | None = None
    error_message: str | None = None

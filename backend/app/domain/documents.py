from dataclasses import dataclass
from datetime import datetime
from typing import Literal


DocumentStatus = Literal["indexing", "completed", "failed"]


@dataclass(frozen=True)
class DocumentRecord:
    kb_id: str
    doc_id: str
    filename: str
    chunk_count: int
    status: DocumentStatus
    created_at: datetime
    error_message: str | None = None

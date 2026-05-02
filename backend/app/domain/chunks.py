from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentChunk:
    id: str
    kb_id: str
    doc_id: str
    filename: str
    chunk_index: int
    content: str


@dataclass(frozen=True)
class RetrievedChunk:
    id: str
    kb_id: str
    doc_id: str
    filename: str
    chunk_index: int
    content: str
    score: float

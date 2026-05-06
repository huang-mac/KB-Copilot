import uuid

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.domain.chunks import DocumentChunk


class TextSplitter:
    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""],
        )

    def split(self, *, kb_id: str, doc_id: str, filename: str, text: str) -> list[DocumentChunk]:
        normalized = self._normalize_text(text)
        chunks: list[DocumentChunk] = []
        for chunk_index, raw_content in enumerate(self.splitter.split_text(normalized)):
            content = raw_content.strip()
            if content:
                chunks.append(
                    DocumentChunk(
                        id=str(uuid.uuid4()),
                        kb_id=kb_id,
                        doc_id=doc_id,
                        filename=filename,
                        chunk_index=chunk_index,
                        content=content,
                    )
                )

        return chunks

    def _normalize_text(self, text: str) -> str:
        lines = [line.strip() for line in text.replace("\r\n", "\n").split("\n")]
        return "\n".join(line for line in lines if line)

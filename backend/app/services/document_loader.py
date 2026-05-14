from pathlib import Path

from app.core.exceptions import UnsupportedDocumentError


class DocumentLoader:
    supported_suffixes = {".txt", ".md", ".markdown", ".pdf", ".docx"}

    def load_text(self, filename: str, content: bytes) -> str:
        suffix = Path(filename).suffix.lower()
        if suffix not in self.supported_suffixes:
            raise UnsupportedDocumentError(
                f"Unsupported document type '{suffix}'. MVP1 supports txt and md."
            )

        if suffix == ".pdf":
            text = self._load_pdf(content)
        elif suffix == ".docx":
            text = self._load_docx(content)
        else:
            text = self._decode_text(content)
        if not text.strip():
            raise UnsupportedDocumentError("Uploaded document is empty.")
        return text

    def _decode_text(self, content: bytes) -> str:
        for encoding in ("utf-8", "utf-8-sig", "gb18030"):
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        return content.decode("utf-8", errors="ignore")

    def _load_pdf(self, content: bytes) -> str:
        try:
            import fitz
        except ImportError as exc:
            raise UnsupportedDocumentError("PDF parsing requires pymupdf.") from exc

        with fitz.open(stream=content, filetype="pdf") as document:
            return "\n\n".join(page.get_text("text") for page in document)

    def _load_docx(self, content: bytes) -> str:
        try:
            from docx import Document
        except ImportError as exc:
            raise UnsupportedDocumentError("DOCX parsing requires python-docx.") from exc

        from io import BytesIO

        document = Document(BytesIO(content))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)

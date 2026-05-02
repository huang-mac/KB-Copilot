from pathlib import Path

from app.core.exceptions import UnsupportedDocumentError


class DocumentLoader:
    supported_suffixes = {".txt", ".md", ".markdown"}

    def load_text(self, filename: str, content: bytes) -> str:
        suffix = Path(filename).suffix.lower()
        if suffix not in self.supported_suffixes:
            raise UnsupportedDocumentError(
                f"Unsupported document type '{suffix}'. MVP0 supports txt and md."
            )

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

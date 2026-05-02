class KBError(Exception):
    """Base exception for expected application errors."""


class UnsupportedDocumentError(KBError):
    """Raised when an uploaded document format is not supported."""


class ExternalProviderError(KBError):
    """Raised when an LLM, embedding, or vector store provider fails."""

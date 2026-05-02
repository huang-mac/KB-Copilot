from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.dependencies import get_document_index_service
from app.core.exceptions import KBError
from app.schemas.documents import DocumentUploadResponse
from app.services.document_index_service import DocumentIndexService

router = APIRouter(prefix="/kbs/{kb_id}/documents", tags=["documents"])


@router.post("", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    kb_id: str,
    file: Annotated[UploadFile, File(...)],
    document_index_service: Annotated[
        DocumentIndexService,
        Depends(get_document_index_service),
    ],
) -> DocumentUploadResponse:
    try:
        content = await file.read()
        doc_id, chunks = await document_index_service.index_document(
            kb_id=kb_id,
            filename=file.filename or "untitled.txt",
            content=content,
        )
    except KBError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return DocumentUploadResponse(
        kb_id=kb_id,
        doc_id=doc_id,
        filename=file.filename or "untitled.txt",
        chunk_count=len(chunks),
        message="document indexed",
    )

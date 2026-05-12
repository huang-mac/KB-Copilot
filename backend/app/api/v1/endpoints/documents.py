from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.dependencies import get_document_index_service
from app.core.exceptions import KBError
from app.domain.documents import DocumentRecord
from app.schemas.documents import (
    DocumentDeleteResponse,
    DocumentListResponse,
    DocumentReindexResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.services.document_index_service import DocumentIndexService

router = APIRouter(prefix="/kbs/{kb_id}/documents", tags=["documents"])


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    kb_id: str,
    document_index_service: Annotated[
        DocumentIndexService,
        Depends(get_document_index_service),
    ],
) -> DocumentListResponse:
    documents = document_index_service.list_documents(kb_id=kb_id)
    return DocumentListResponse(
        documents=[_to_document_response(document) for document in documents]
    )


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
        document, _chunks = await document_index_service.index_document(
            kb_id=kb_id,
            filename=file.filename or "untitled.txt",
            content=content,
            content_type=file.content_type,
        )
    except KBError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return DocumentUploadResponse(
        **_to_document_response(document).model_dump(),
        message="document indexed",
    )


@router.post("/{doc_id}/reindex", response_model=DocumentReindexResponse)
async def reindex_document(
    kb_id: str,
    doc_id: str,
    document_index_service: Annotated[
        DocumentIndexService,
        Depends(get_document_index_service),
    ],
) -> DocumentReindexResponse:
    try:
        document = await document_index_service.reindex_document(kb_id=kb_id, doc_id=doc_id)
    except KBError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return DocumentReindexResponse(
        **_to_document_response(document).model_dump(),
        message="document reindexed",
    )


@router.delete("/{doc_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    kb_id: str,
    doc_id: str,
    document_index_service: Annotated[
        DocumentIndexService,
        Depends(get_document_index_service),
    ],
) -> DocumentDeleteResponse:
    try:
        document_index_service.delete_document(kb_id=kb_id, doc_id=doc_id)
    except KBError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return DocumentDeleteResponse(
        kb_id=kb_id,
        doc_id=doc_id,
        message="document deleted",
    )


def _to_document_response(document: DocumentRecord) -> DocumentResponse:
    return DocumentResponse(
        kb_id=document.kb_id,
        doc_id=document.doc_id,
        filename=document.filename,
        chunk_count=document.chunk_count,
        status=document.status,
        created_at=document.created_at,
        error_message=document.error_message,
    )

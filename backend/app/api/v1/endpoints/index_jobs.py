from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_index_job_repository
from app.domain.index_jobs import IndexJob
from app.repositories.index_jobs import IndexJobRepository
from app.schemas.index_jobs import IndexJobResponse

router = APIRouter(prefix="/kbs/{kb_id}/index-jobs", tags=["index-jobs"])


@router.get("/{job_id}", response_model=IndexJobResponse)
async def get_index_job(
    kb_id: str,
    job_id: str,
    repository: Annotated[IndexJobRepository, Depends(get_index_job_repository)],
) -> IndexJobResponse:
    job = repository.get(kb_id=kb_id, job_id=job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Index job not found.")
    return _to_response(job)


def _to_response(job: IndexJob) -> IndexJobResponse:
    return IndexJobResponse(
        kb_id=job.kb_id,
        job_id=job.job_id,
        doc_id=job.doc_id,
        filename=job.filename,
        status=job.status,
        created_at=job.created_at,
        updated_at=job.updated_at,
        content_type=job.content_type,
        error_message=job.error_message,
    )

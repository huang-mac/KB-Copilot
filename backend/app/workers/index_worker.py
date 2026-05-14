import asyncio
import logging

from app.repositories.index_jobs import IndexJobRepository
from app.services.document_index_service import DocumentIndexService

logger = logging.getLogger(__name__)


class IndexWorker:
    def __init__(
        self,
        *,
        index_job_repository: IndexJobRepository,
        document_index_service: DocumentIndexService,
        poll_interval_seconds: float = 1.0,
    ) -> None:
        self.index_job_repository = index_job_repository
        self.document_index_service = document_index_service
        self.poll_interval_seconds = poll_interval_seconds
        self._task: asyncio.Task | None = None
        self._stopping = asyncio.Event()

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._stopping.clear()
            self._task = asyncio.create_task(self.run(), name="index-worker")

    async def stop(self) -> None:
        self._stopping.set()
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass

    async def run(self) -> None:
        while not self._stopping.is_set():
            job = self.index_job_repository.claim_next()
            if job is None:
                await asyncio.sleep(self.poll_interval_seconds)
                continue

            payload = self.index_job_repository.get_payload(kb_id=job.kb_id, job_id=job.job_id)
            if payload is None:
                continue

            job, content = payload
            try:
                await self.document_index_service.index_existing_document(
                    kb_id=job.kb_id,
                    doc_id=job.doc_id,
                    filename=job.filename,
                    content=content,
                    content_type=job.content_type,
                )
            except Exception as exc:
                logger.exception("Index job %s failed", job.job_id)
                self.index_job_repository.mark_failed(
                    kb_id=job.kb_id,
                    job_id=job.job_id,
                    error_message=str(exc),
                )
            else:
                self.index_job_repository.mark_completed(kb_id=job.kb_id, job_id=job.job_id)

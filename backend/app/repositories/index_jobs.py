import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from app.domain.index_jobs import IndexJob, IndexJobStatus


class IndexJobRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._ensure_schema()

    def create(
        self,
        *,
        kb_id: str,
        job_id: str,
        doc_id: str,
        filename: str,
        content: bytes,
        content_type: str | None,
    ) -> IndexJob:
        now = datetime.now(UTC)
        with self._connect() as connection, self._lock:
            connection.execute(
                """
                INSERT INTO index_jobs (
                    kb_id, job_id, doc_id, filename, content_type, content,
                    status, error_message, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    kb_id,
                    job_id,
                    doc_id,
                    filename,
                    content_type,
                    content,
                    "queued",
                    None,
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
        return IndexJob(
            kb_id=kb_id,
            job_id=job_id,
            doc_id=doc_id,
            filename=filename,
            content_type=content_type,
            status="queued",
            created_at=now,
            updated_at=now,
        )

    def get(self, *, kb_id: str, job_id: str) -> IndexJob | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT kb_id, job_id, doc_id, filename, content_type, status,
                       error_message, created_at, updated_at
                FROM index_jobs
                WHERE kb_id = ? AND job_id = ?
                """,
                (kb_id, job_id),
            ).fetchone()
        return self._job_from_row(row) if row else None

    def get_payload(self, *, kb_id: str, job_id: str) -> tuple[IndexJob, bytes] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT kb_id, job_id, doc_id, filename, content_type, status,
                       error_message, created_at, updated_at, content
                FROM index_jobs
                WHERE kb_id = ? AND job_id = ?
                """,
                (kb_id, job_id),
            ).fetchone()
        if row is None:
            return None
        return self._job_from_row(row[:9]), bytes(row[9])

    def claim_next(self) -> IndexJob | None:
        with self._connect() as connection, self._lock:
            row = connection.execute(
                """
                SELECT kb_id, job_id, doc_id, filename, content_type, status,
                       error_message, created_at, updated_at
                FROM index_jobs
                WHERE status = ?
                ORDER BY datetime(created_at) ASC
                LIMIT 1
                """,
                ("queued",),
            ).fetchone()
            if row is None:
                return None
            job = self._job_from_row(row)
            now = datetime.now(UTC).isoformat()
            cursor = connection.execute(
                """
                UPDATE index_jobs
                SET status = ?, updated_at = ?
                WHERE kb_id = ? AND job_id = ? AND status = ?
                """,
                ("processing", now, job.kb_id, job.job_id, "queued"),
            )
            if cursor.rowcount != 1:
                return None
        return self.get(kb_id=job.kb_id, job_id=job.job_id)

    def mark_completed(self, *, kb_id: str, job_id: str) -> None:
        self._update_status(kb_id=kb_id, job_id=job_id, status="completed", error_message=None)

    def mark_failed(self, *, kb_id: str, job_id: str, error_message: str) -> None:
        self._update_status(
            kb_id=kb_id,
            job_id=job_id,
            status="failed",
            error_message=error_message[:1000],
        )

    def _update_status(
        self,
        *,
        kb_id: str,
        job_id: str,
        status: IndexJobStatus,
        error_message: str | None,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection, self._lock:
            connection.execute(
                """
                UPDATE index_jobs
                SET status = ?, error_message = ?, updated_at = ?
                WHERE kb_id = ? AND job_id = ?
                """,
                (status, error_message, now, kb_id, job_id),
            )

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS index_jobs (
                    kb_id TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    doc_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    content_type TEXT,
                    content BLOB NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (kb_id, job_id)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_index_jobs_status_created_at
                ON index_jobs(status, created_at)
                """
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _job_from_row(self, row: tuple) -> IndexJob:
        return IndexJob(
            kb_id=row[0],
            job_id=row[1],
            doc_id=row[2],
            filename=row[3],
            content_type=row[4],
            status=row[5],
            error_message=row[6],
            created_at=datetime.fromisoformat(row[7]),
            updated_at=datetime.fromisoformat(row[8]),
        )

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from app.domain.documents import DocumentRecord, DocumentStatus


class DocumentRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._ensure_schema()

    def create(
        self,
        *,
        kb_id: str,
        doc_id: str,
        filename: str,
        status: DocumentStatus,
    ) -> DocumentRecord:
        created_at = datetime.now(UTC)
        with self._connect() as connection, self._lock:
            connection.execute(
                """
                INSERT INTO documents (
                    kb_id, doc_id, filename, chunk_count, status, created_at, error_message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (kb_id, doc_id, filename, 0, status, created_at.isoformat(), None),
            )

        return DocumentRecord(
            kb_id=kb_id,
            doc_id=doc_id,
            filename=filename,
            chunk_count=0,
            status=status,
            created_at=created_at,
        )

    def list_by_kb(self, kb_id: str) -> list[DocumentRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT kb_id, doc_id, filename, chunk_count, status, created_at, error_message
                FROM documents
                WHERE kb_id = ?
                ORDER BY datetime(created_at) DESC
                """,
                (kb_id,),
            ).fetchall()
        return [self._record_from_row(row) for row in rows]

    def get(self, *, kb_id: str, doc_id: str) -> DocumentRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT kb_id, doc_id, filename, chunk_count, status, created_at, error_message
                FROM documents
                WHERE kb_id = ? AND doc_id = ?
                """,
                (kb_id, doc_id),
            ).fetchone()
        return self._record_from_row(row) if row else None

    def mark_indexing(self, *, kb_id: str, doc_id: str) -> None:
        with self._connect() as connection, self._lock:
            connection.execute(
                """
                UPDATE documents
                SET chunk_count = 0, status = ?, error_message = NULL
                WHERE kb_id = ? AND doc_id = ?
                """,
                ("indexing", kb_id, doc_id),
            )

    def mark_completed(self, *, kb_id: str, doc_id: str, chunk_count: int) -> None:
        with self._connect() as connection, self._lock:
            connection.execute(
                """
                UPDATE documents
                SET chunk_count = ?, status = ?, error_message = NULL
                WHERE kb_id = ? AND doc_id = ?
                """,
                (chunk_count, "completed", kb_id, doc_id),
            )

    def mark_failed(self, *, kb_id: str, doc_id: str, error_message: str) -> None:
        with self._connect() as connection, self._lock:
            connection.execute(
                """
                UPDATE documents
                SET status = ?, error_message = ?
                WHERE kb_id = ? AND doc_id = ?
                """,
                ("failed", error_message[:1000], kb_id, doc_id),
            )

    def delete(self, *, kb_id: str, doc_id: str) -> None:
        with self._connect() as connection, self._lock:
            connection.execute(
                "DELETE FROM documents WHERE kb_id = ? AND doc_id = ?",
                (kb_id, doc_id),
            )

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    kb_id TEXT NOT NULL,
                    doc_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    chunk_count INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    error_message TEXT,
                    PRIMARY KEY (kb_id, doc_id)
                )
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

    def _record_from_row(self, row: tuple) -> DocumentRecord:
        return DocumentRecord(
            kb_id=row[0],
            doc_id=row[1],
            filename=row[2],
            chunk_count=row[3],
            status=row[4],
            created_at=datetime.fromisoformat(row[5]),
            error_message=row[6],
        )

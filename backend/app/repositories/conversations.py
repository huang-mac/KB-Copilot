import json
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from app.domain.conversations import ConversationMessage, ConversationRecord, MessageRole


class ConversationRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._ensure_schema()

    def create(self, *, kb_id: str, conversation_id: str, title: str) -> ConversationRecord:
        now = datetime.now(UTC)
        with self._connect() as connection, self._lock:
            connection.execute(
                """
                INSERT INTO conversations (
                    kb_id, conversation_id, title, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (kb_id, conversation_id, title, now.isoformat(), now.isoformat()),
            )

        return ConversationRecord(
            kb_id=kb_id,
            conversation_id=conversation_id,
            title=title,
            created_at=now,
            updated_at=now,
        )

    def list_by_kb(self, kb_id: str) -> list[ConversationRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT kb_id, conversation_id, title, created_at, updated_at
                FROM conversations
                WHERE kb_id = ?
                ORDER BY datetime(updated_at) DESC
                """,
                (kb_id,),
            ).fetchall()
        return [self._conversation_from_row(row) for row in rows]

    def get(self, *, kb_id: str, conversation_id: str) -> ConversationRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT kb_id, conversation_id, title, created_at, updated_at
                FROM conversations
                WHERE kb_id = ? AND conversation_id = ?
                """,
                (kb_id, conversation_id),
            ).fetchone()
        return self._conversation_from_row(row) if row else None

    def add_message(
        self,
        *,
        kb_id: str,
        conversation_id: str,
        message_id: str,
        role: MessageRole,
        content: str,
        sources: list[dict] | None = None,
    ) -> ConversationMessage:
        created_at = datetime.now(UTC)
        sources_json = json.dumps(sources, ensure_ascii=False) if sources is not None else None
        with self._connect() as connection, self._lock:
            connection.execute(
                """
                INSERT INTO conversation_messages (
                    kb_id, conversation_id, message_id, role, content, sources, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    kb_id,
                    conversation_id,
                    message_id,
                    role,
                    content,
                    sources_json,
                    created_at.isoformat(),
                ),
            )
            connection.execute(
                """
                UPDATE conversations
                SET updated_at = ?
                WHERE kb_id = ? AND conversation_id = ?
                """,
                (created_at.isoformat(), kb_id, conversation_id),
            )

        return ConversationMessage(
            kb_id=kb_id,
            conversation_id=conversation_id,
            message_id=message_id,
            role=role,
            content=content,
            sources=sources,
            created_at=created_at,
        )

    def list_messages(self, *, kb_id: str, conversation_id: str) -> list[ConversationMessage]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT kb_id, conversation_id, message_id, role, content, sources, created_at
                FROM conversation_messages
                WHERE kb_id = ? AND conversation_id = ?
                ORDER BY datetime(created_at) ASC
                """,
                (kb_id, conversation_id),
            ).fetchall()
        return [self._message_from_row(row) for row in rows]

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    kb_id TEXT NOT NULL,
                    conversation_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (kb_id, conversation_id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    kb_id TEXT NOT NULL,
                    conversation_id TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sources TEXT,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (kb_id, conversation_id, message_id)
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

    def _conversation_from_row(self, row: tuple) -> ConversationRecord:
        return ConversationRecord(
            kb_id=row[0],
            conversation_id=row[1],
            title=row[2],
            created_at=datetime.fromisoformat(row[3]),
            updated_at=datetime.fromisoformat(row[4]),
        )

    def _message_from_row(self, row: tuple) -> ConversationMessage:
        return ConversationMessage(
            kb_id=row[0],
            conversation_id=row[1],
            message_id=row[2],
            role=row[3],
            content=row[4],
            sources=json.loads(row[5]) if row[5] else None,
            created_at=datetime.fromisoformat(row[6]),
        )

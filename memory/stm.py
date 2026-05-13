from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import sqlite3
from pathlib import Path
from typing import Any, Deque, Dict, Iterable, List, Optional


@dataclass
class Message:
    role: str
    content: str
    ts: datetime


class ShortTermMemory:
    """Recent N-turn message cache with optional summary placeholder."""

    def __init__(
        self,
        max_turns: int = 10,
        summary: Optional[str] = None,
        *,
        db_path: str | Path | None = None,
        user_id: str = "default",
        session_id: str = "default",
    ) -> None:
        if max_turns <= 0:
            raise ValueError("max_turns must be > 0")
        self.max_turns = max_turns
        self._messages: Deque[Message] = deque(maxlen=max_turns)
        self._summary: Optional[str] = summary
        self.db_path = str(db_path) if db_path else None
        self.user_id = user_id or "default"
        self.session_id = session_id or "default"
        if self.db_path:
            self._init_db()
            self._load()

    def add(self, role: str, content: str, ts: Optional[datetime] = None) -> None:
        message = Message(role=role, content=content, ts=ts or datetime.now(timezone.utc))
        self._messages.append(message)
        if self.db_path:
            self._persist_message(message)
            self._trim_persisted_messages()

    def extend(self, messages: Iterable[Dict[str, str]]) -> None:
        for msg in messages:
            self.add(role=msg["role"], content=msg["content"])

    def get_recent(self, n: Optional[int] = None) -> List[Dict[str, str]]:
        items = list(self._messages)
        if n is not None:
            if n <= 0:
                return []
            items = items[-n:]
        return [{"role": m.role, "content": m.content, "ts": m.ts.isoformat()} for m in items]

    def clear(self) -> None:
        self._messages.clear()
        if self.db_path:
            with self._connect() as conn:
                conn.execute(
                    "DELETE FROM stm_messages WHERE user_id = ? AND session_id = ?",
                    (self.user_id, self.session_id),
                )
                conn.execute(
                    "DELETE FROM stm_summaries WHERE user_id = ? AND session_id = ?",
                    (self.user_id, self.session_id),
                )
            self._summary = None

    def list_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List persisted sessions for this user, newest first."""
        if not self.db_path:
            return [
                {
                    "session_id": self.session_id,
                    "title": self._derive_title(self.get_recent()),
                    "message_count": len(self._messages),
                    "updated_at": self._messages[-1].ts.isoformat() if self._messages else "",
                }
            ]
        self._init_db()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT session_id, COUNT(*) AS message_count, MAX(ts) AS updated_at
                FROM stm_messages
                WHERE user_id = ?
                GROUP BY session_id
                ORDER BY updated_at DESC, session_id ASC
                LIMIT ?
                """,
                (self.user_id, max(1, int(limit))),
            ).fetchall()
            sessions: List[Dict[str, Any]] = []
            for session_id, message_count, updated_at in rows:
                messages = conn.execute(
                    """
                    SELECT role, content, ts
                    FROM stm_messages
                    WHERE user_id = ? AND session_id = ?
                    ORDER BY id ASC
                    LIMIT 20
                    """,
                    (self.user_id, session_id),
                ).fetchall()
                items = [
                    {"role": role, "content": content, "ts": ts}
                    for role, content, ts in messages
                ]
                sessions.append(
                    {
                        "session_id": session_id,
                        "title": self._derive_title(items),
                        "message_count": int(message_count or 0),
                        "updated_at": str(updated_at or ""),
                    }
                )
        return sessions

    def set_summary(self, text: Optional[str]) -> None:
        self._summary = text
        if self.db_path:
            with self._connect() as conn:
                if text is None:
                    conn.execute(
                        "DELETE FROM stm_summaries WHERE user_id = ? AND session_id = ?",
                        (self.user_id, self.session_id),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO stm_summaries(user_id, session_id, summary, updated_at)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(user_id, session_id)
                        DO UPDATE SET summary = excluded.summary, updated_at = excluded.updated_at
                        """,
                        (self.user_id, self.session_id, text, datetime.now(timezone.utc).isoformat()),
                    )

    def get_summary(self) -> Optional[str]:
        return self._summary

    @staticmethod
    def _derive_title(messages: Iterable[Dict[str, Any]], limit: int = 24) -> str:
        for msg in messages:
            if str(msg.get("role", "")) != "user":
                continue
            content = str(msg.get("content", "")).strip()
            if content:
                return content[:limit] + ("..." if len(content) > limit else "")
        return "新会话"

    def _connect(self) -> sqlite3.Connection:
        if not self.db_path:
            raise RuntimeError("ShortTermMemory has no db_path configured.")
        path = Path(self.db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS stm_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    ts TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_stm_messages_scope
                ON stm_messages(user_id, session_id, id)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS stm_summaries (
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(user_id, session_id)
                )
                """
            )

    def _load(self) -> None:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT role, content, ts
                FROM stm_messages
                WHERE user_id = ? AND session_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (self.user_id, self.session_id, self.max_turns),
            ).fetchall()
            for role, content, ts_text in reversed(rows):
                try:
                    ts = datetime.fromisoformat(ts_text)
                except ValueError:
                    ts = datetime.now(timezone.utc)
                self._messages.append(Message(role=role, content=content, ts=ts))
            summary_row = conn.execute(
                """
                SELECT summary
                FROM stm_summaries
                WHERE user_id = ? AND session_id = ?
                """,
                (self.user_id, self.session_id),
            ).fetchone()
            if summary_row:
                self._summary = summary_row[0]

    def _persist_message(self, message: Message) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO stm_messages(user_id, session_id, role, content, ts)
                VALUES (?, ?, ?, ?, ?)
                """,
                (self.user_id, self.session_id, message.role, message.content, message.ts.isoformat()),
            )

    def _trim_persisted_messages(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                DELETE FROM stm_messages
                WHERE user_id = ?
                  AND session_id = ?
                  AND id NOT IN (
                    SELECT id
                    FROM stm_messages
                    WHERE user_id = ? AND session_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                  )
                """,
                (self.user_id, self.session_id, self.user_id, self.session_id, self.max_turns),
            )

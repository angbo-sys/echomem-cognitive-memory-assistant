from __future__ import annotations

import sqlite3
import uuid
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .evolution import build_evolution_decision, decay_importance
from .vector_store import VectorStoreBackend


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class LongTermMemory:
    """
    SQLite-backed memory store.
    Schema fields:
    id/user_id/content/type/importance/status/source/ts
    """

    def __init__(self, db_path: str = "memory.db") -> None:
        self.db_path = str(Path(db_path))
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def _managed_conn(self) -> Iterable[sqlite3.Connection]:
        conn = self._connect()
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._managed_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    content TEXT NOT NULL,
                    type TEXT NOT NULL DEFAULT 'fact',
                    importance REAL NOT NULL DEFAULT 1.0,
                    status TEXT NOT NULL DEFAULT 'active',
                    source TEXT NOT NULL DEFAULT 'unknown',
                    ts TEXT NOT NULL
                )
                """
            )
            # Migration path for existing DBs created before user_id was introduced.
            columns = {str(row["name"]) for row in conn.execute("PRAGMA table_info(memories)").fetchall()}
            if "user_id" not in columns:
                conn.execute("ALTER TABLE memories ADD COLUMN user_id TEXT")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_status ON memories(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_ts ON memories(ts)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id)")
            conn.commit()

    def add_memory(
        self,
        content: str,
        mtype: str = "fact",
        importance: float = 1.0,
        status: str = "active",
        source: str = "unknown",
        ts: Optional[str] = None,
        memory_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> str:
        memory_id = memory_id or str(uuid.uuid4())
        ts = ts or _utc_now_iso()
        with self._managed_conn() as conn:
            conn.execute(
                """
                INSERT INTO memories (id, user_id, content, type, importance, status, source, ts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (memory_id, user_id, content, mtype, float(importance), status, source, ts),
            )
            conn.commit()
        return memory_id

    def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        with self._managed_conn() as conn:
            row = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
            return dict(row) if row else None

    def update_status(self, memory_id: str, status: str) -> bool:
        with self._managed_conn() as conn:
            cur = conn.execute("UPDATE memories SET status = ? WHERE id = ?", (status, memory_id))
            conn.commit()
            return cur.rowcount > 0

    def list_memories(
        self,
        status: Optional[str] = "active",
        mtype: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
        order_desc: bool = True,
    ) -> List[Dict[str, Any]]:
        if limit <= 0:
            return []
        where_parts: List[str] = []
        params: List[Any] = []
        if status is not None:
            where_parts.append("status = ?")
            params.append(status)
        if mtype is not None:
            where_parts.append("type = ?")
            params.append(mtype)
        if user_id is not None:
            where_parts.append("user_id = ?")
            params.append(user_id)
        where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
        order = "DESC" if order_desc else "ASC"
        sql = f"SELECT * FROM memories {where_clause} ORDER BY ts {order} LIMIT ?"
        params.append(limit)
        with self._managed_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def text_search(
        self,
        query: str,
        status: Optional[str] = "active",
        user_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        if limit <= 0:
            return []
        where = ["content LIKE ?"]
        params: List[Any] = [f"%{query}%"]
        if status is not None:
            where.append("status = ?")
            params.append(status)
        if user_id is not None:
            where.append("user_id = ?")
            params.append(user_id)
        params.append(limit)
        sql = f"SELECT * FROM memories WHERE {' AND '.join(where)} ORDER BY ts DESC LIMIT ?"
        with self._managed_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def bulk_add(self, items: Iterable[Dict[str, Any]]) -> List[str]:
        ids: List[str] = []
        for item in items:
            ids.append(
                self.add_memory(
                    content=item["content"],
                    mtype=item.get("type", "fact"),
                    importance=float(item.get("importance", 1.0)),
                    status=item.get("status", "active"),
                    source=item.get("source", "unknown"),
                    ts=item.get("ts"),
                    memory_id=item.get("id"),
                    user_id=item.get("user_id"),
                )
            )
        return ids

    def build_vector_index(
        self,
        backend: str = "none",
        collection_name: str = "memories",
        persist_path: Optional[str] = None,
    ) -> int:
        """Build vector index from active memories.

        Returns number of indexed records. If backend is unavailable, returns 0.
        """
        store = VectorStoreBackend(backend=backend, collection_name=collection_name, persist_path=persist_path)
        if not store.available:
            return 0
        rows = self.list_memories(status="active", limit=10000)
        for row in rows:
            store.add(
                doc_id=str(row["id"]),
                content=str(row.get("content", "")),
                metadata={
                    "type": row.get("type"),
                    "importance": row.get("importance"),
                    "status": row.get("status"),
                    "ts": row.get("ts"),
                    "user_id": row.get("user_id"),
                },
            )
        return len(rows)

    def _make_field_memory_content(self, user_id: str, field: str, value: Any) -> str:
        payload = {"user_id": user_id, "field": field, "value": value}
        return json.dumps(payload, ensure_ascii=True, sort_keys=True)

    def _parse_field_memory_content(self, content: str) -> Optional[Dict[str, Any]]:
        try:
            payload = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return None
        if not isinstance(payload, dict):
            return None
        if "user_id" not in payload or "field" not in payload:
            return None
        return payload

    def _find_latest_active_field_memory(self, user_id: str, field: str) -> Optional[Dict[str, Any]]:
        candidates = self.list_memories(
            status="active",
            mtype="profile_field",
            user_id=user_id,
            limit=500,
            order_desc=True,
        )
        for mem in candidates:
            payload = self._parse_field_memory_content(mem.get("content", ""))
            if payload is not None and payload.get("field") == field:
                return mem
        return None

    def _update_memory_status_and_importance(self, memory_id: str, status: str, importance: float) -> bool:
        with self._managed_conn() as conn:
            cur = conn.execute(
                "UPDATE memories SET status = ?, importance = ? WHERE id = ?",
                (status, float(importance), memory_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def detect_conflict_and_update(
        self,
        user_id: str,
        field: str,
        old_value: Any,
        new_value: Any,
        trigger: str,
        confidence: float,
    ) -> Dict[str, Any]:
        """
        Conflict-aware memory evolution.
        - Finds current active memory for (user_id, field)
        - If conflict detected, deprecates old memory and decays its importance
        - Always inserts a new active memory for new_value
        """
        current = self._find_latest_active_field_memory(user_id=user_id, field=field)
        baseline_old = old_value
        if current is not None:
            payload = self._parse_field_memory_content(current.get("content", ""))
            if payload is not None:
                baseline_old = payload.get("value", old_value)

        decision = build_evolution_decision(old_value=baseline_old, new_value=new_value)

        deprecated_memory_id: Optional[str] = None
        if current is not None and decision.conflict:
            old_importance = float(current.get("importance", 1.0))
            new_importance = decay_importance(old_importance, decision.old_importance_multiplier)
            if self._update_memory_status_and_importance(
                memory_id=str(current["id"]),
                status=decision.old_status,
                importance=new_importance,
            ):
                deprecated_memory_id = str(current["id"])

        new_importance_value = max(0.0, min(1.0, float(confidence)))
        new_memory_id = self.add_memory(
            content=self._make_field_memory_content(user_id=user_id, field=field, value=new_value),
            mtype="profile_field",
            importance=new_importance_value,
            status="active",
            source=trigger,
            user_id=user_id,
        )
        return {
            "conflict": decision.conflict,
            "reason": decision.reason,
            "deprecated_memory_id": deprecated_memory_id,
            "new_memory_id": new_memory_id,
        }

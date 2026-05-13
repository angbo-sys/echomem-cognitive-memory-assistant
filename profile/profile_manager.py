from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProfileSnapshot:
    user_id: str
    profile: dict[str, Any]


class ProfileManager:
    """Manage current profile state and change history in SQLite."""

    _ALLOWED_FIELDS: set[str] = {
        # Required fields from the project task spec.
        "learning_goal",
        "preferred_style",
        "weak_subject",
        "emotion_state",
        "knowledge_level",
        "recent_focus",
        # Legacy/general fields for compatibility during iteration.
        "name",
        "nickname",
        "age",
        "location",
        "occupation",
        "interests",
        "preferences",
        "goals",
        "bio",
        "mood",
        "emotion",
    }

    def __init__(self, db_path: str | Path = "profile/profile.db") -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_tables()

    @property
    def db_path(self) -> Path:
        return self._db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def _managed_conn(self):  # type: ignore[no-untyped-def]
        conn = self._connect()
        try:
            yield conn
        finally:
            conn.close()

    def _initialize_tables(self) -> None:
        try:
            with self._managed_conn() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS profile_current (
                        user_id TEXT PRIMARY KEY,
                        profile_json TEXT NOT NULL,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS profile_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        field TEXT NOT NULL,
                        old_value TEXT,
                        new_value TEXT NOT NULL,
                        trigger TEXT NOT NULL,
                        confidence REAL NOT NULL,
                        changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_profile_history_user_time
                    ON profile_history(user_id, changed_at)
                    """
                )
        except sqlite3.Error as exc:
            raise RuntimeError(f"Failed to initialize profile tables: {exc}") from exc

    def _serialize_value(self, value: Any) -> str:
        try:
            return json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Value is not JSON serializable: {value!r}") from exc

    def _deserialize_profile(self, profile_json: str) -> dict[str, Any]:
        try:
            parsed = json.loads(profile_json)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Corrupted profile data: invalid JSON in storage.") from exc
        if not isinstance(parsed, dict):
            raise RuntimeError("Corrupted profile data: expected a JSON object.")
        return parsed

    def get_profile(self, user_id: str) -> dict[str, Any]:
        if not user_id:
            raise ValueError("user_id must be a non-empty string.")
        try:
            with self._managed_conn() as conn:
                row = conn.execute(
                    "SELECT profile_json FROM profile_current WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
        except sqlite3.Error as exc:
            raise RuntimeError(f"Failed to fetch profile for user_id='{user_id}': {exc}") from exc

        if row is None:
            return {}
        return self._deserialize_profile(str(row["profile_json"]))

    def update_field(
        self,
        user_id: str,
        field: str,
        new_value: Any,
        trigger: str,
        confidence: float,
    ) -> ProfileSnapshot:
        if not user_id:
            raise ValueError("user_id must be a non-empty string.")
        if not field:
            raise ValueError("field must be a non-empty string.")
        if field not in self._ALLOWED_FIELDS:
            raise ValueError(
                f"Unsupported profile field '{field}'. Allowed fields: {sorted(self._ALLOWED_FIELDS)}"
            )
        if not trigger:
            raise ValueError("trigger must be a non-empty string.")
        if not (0.0 <= confidence <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0.")

        serialized_new = self._serialize_value(new_value)

        try:
            with self._managed_conn() as conn:
                row = conn.execute(
                    "SELECT profile_json FROM profile_current WHERE user_id = ?",
                    (user_id,),
                ).fetchone()

                if row is None:
                    profile: dict[str, Any] = {}
                else:
                    profile = self._deserialize_profile(str(row["profile_json"]))

                old_value = profile.get(field)
                profile[field] = new_value
                serialized_profile = self._serialize_value(profile)

                conn.execute(
                    """
                    INSERT INTO profile_current (user_id, profile_json, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id) DO UPDATE SET
                        profile_json = excluded.profile_json,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (user_id, serialized_profile),
                )
                conn.execute(
                    """
                    INSERT INTO profile_history
                    (user_id, field, old_value, new_value, trigger, confidence, changed_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (
                        user_id,
                        field,
                        self._serialize_value(old_value),
                        serialized_new,
                        trigger,
                        confidence,
                    ),
                )
                conn.commit()
        except sqlite3.Error as exc:
            raise RuntimeError(
                f"Failed to update field '{field}' for user_id='{user_id}': {exc}"
            ) from exc

        return ProfileSnapshot(user_id=user_id, profile=profile)

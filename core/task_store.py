"""Small persistent task store backed by SQLite."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.config import ROOT


class TaskStore:
    def __init__(self, path: Path | None = None):
        self.path = path or (ROOT / "data" / "phosphene.db")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    categories TEXT NOT NULL,
                    current_category TEXT,
                    progress REAL NOT NULL DEFAULT 0,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "UPDATE runs SET status='interrupted', updated_at=? "
                "WHERE status IN ('queued', 'running', 'stopping')",
                (self._now(),),
            )

    def create(self, categories: list[str]) -> dict[str, Any]:
        task_id = uuid.uuid4().hex
        now = self._now()
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO runs(id,status,categories,created_at,updated_at) VALUES(?,?,?,?,?)",
                (task_id, "queued", json.dumps(categories), now, now),
            )
        return self.get(task_id) or {}

    def update(self, task_id: str, **fields: Any) -> None:
        allowed = {"status", "current_category", "progress", "error"}
        updates = {key: value for key, value in fields.items() if key in allowed}
        if not updates:
            return
        updates["updated_at"] = self._now()
        clause = ", ".join(f"{key}=?" for key in updates)
        values = list(updates.values()) + [task_id]
        with self._lock, self._connect() as connection:
            connection.execute(f"UPDATE runs SET {clause} WHERE id=?", values)

    def get(self, task_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM runs WHERE id=?", (task_id,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["categories"] = json.loads(result["categories"])
        return result

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

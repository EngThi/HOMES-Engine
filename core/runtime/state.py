from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List


class StateStore:
    """SQLite-backed state and event log for long-running capabilities."""

    def __init__(self, path: str = "output/engine_state.sqlite") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS kv (
                    namespace TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (namespace, key)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )

    def set(self, namespace: str, key: str, value: Any) -> None:
        raw = json.dumps(value, separators=(",", ":"))
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO kv(namespace, key, value, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(namespace, key)
                DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (namespace, key, raw, time.time()),
            )

    def get(self, namespace: str, key: str, default: Any = None) -> Any:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM kv WHERE namespace = ? AND key = ?",
                (namespace, key),
            ).fetchone()
        return json.loads(row[0]) if row else default

    def delete(self, namespace: str, key: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM kv WHERE namespace = ? AND key = ?",
                (namespace, key),
            )
            return cursor.rowcount > 0

    def list_namespace(self, namespace: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT key, value, updated_at
                FROM kv
                WHERE namespace = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (namespace, limit),
            ).fetchall()
        return [
            {
                "key": row[0],
                "value": json.loads(row[1]),
                "updated_at": row[2],
            }
            for row in rows
        ]

    def namespaces(self) -> List[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT DISTINCT namespace FROM kv ORDER BY namespace").fetchall()
        return [row[0] for row in rows]

    def append_event(self, event_type: str, payload: Dict[str, Any]) -> int:
        raw = json.dumps(payload, separators=(",", ":"))
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO events(event_type, payload, created_at) VALUES (?, ?, ?)",
                (event_type, raw, time.time()),
            )
            return int(cursor.lastrowid)

    def recent_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, event_type, payload, created_at
                FROM events
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "id": row[0],
                "event_type": row[1],
                "payload": json.loads(row[2]),
                "created_at": row[3],
            }
            for row in rows
        ]

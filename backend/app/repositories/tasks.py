"""Persistent SQLite task queue repository."""
from __future__ import annotations
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
from app.db import Database
from app.models import TaskPage, TaskRead


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _decode_object(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


@dataclass(frozen=True, slots=True)
class ClaimedTask:
    id: str
    type: str
    params: dict[str, Any]


class TaskRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def initialize(self) -> list[int]:
        return self.database.migrate()

    @staticmethod
    def _task_from_row(row: sqlite3.Row) -> TaskRead:
        task_id = str(row["id"])
        return TaskRead(
            id=task_id,
            task_id=task_id,
            type=str(row["type"]),
            status=str(row["status"]),
            progress=float(row["progress"]),
            message=str(row["message"]),
            result=_decode_object(str(row["result_json"])),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def create_task(self, task_type: str, params: dict[str, Any]) -> TaskRead:
        task_type = task_type.strip()
        if not task_type:
            raise ValueError("task type must not be blank")
        task_id = str(uuid4())
        now = _utc_now()
        params_json = json.dumps(params, ensure_ascii=False, separators=(",", ":"))
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO tasks (
                    id, type, status, progress, message, params_json,
                    result_json, created_at, updated_at
                ) VALUES (?, ?, 'pending', 0, '', ?, '{}', ?, ?)
                """,
                (task_id, task_type, params_json, now, now),
            )
            row = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            assert row is not None
            return self._task_from_row(row)

    def get_task(self, task_id: str) -> TaskRead | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return self._task_from_row(row) if row is not None else None

    def get_active_task(self, task_type: str) -> TaskRead | None:
        """Return the oldest pending/running task of a type, if one exists."""
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM tasks
                WHERE type = ? AND status IN ('pending', 'running')
                ORDER BY created_at ASC, id ASC
                LIMIT 1
                """,
                (task_type.strip(),),
            ).fetchone()
        return self._task_from_row(row) if row is not None else None

    def list_tasks(
        self,
        *,
        status: str | None = None,
        task_type: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> TaskPage:
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if task_type.strip():
            clauses.append("type = ?")
            params.append(task_type.strip())
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.database.connect() as connection:
            total = int(
                connection.execute(
                    f"SELECT COUNT(*) AS total FROM tasks {where}", params
                ).fetchone()["total"]
            )
            rows = connection.execute(
                f"""
                SELECT * FROM tasks
                {where}
                ORDER BY created_at DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                (*params, limit, offset),
            ).fetchall()
        return TaskPage(
            items=[self._task_from_row(row) for row in rows],
            total=total,
            limit=limit,
            offset=offset,
        )

    def claim_next(self) -> ClaimedTask | None:
        now = _utc_now()
        with self.database.transaction() as connection:
            row = connection.execute(
                """
                SELECT id, type, params_json FROM tasks
                WHERE status = 'pending'
                ORDER BY created_at ASC, id ASC
                LIMIT 1
                """
            ).fetchone()
            if row is None:
                return None
            cursor = connection.execute(
                """
                UPDATE tasks
                SET status = 'running', message = 'task started', updated_at = ?
                WHERE id = ? AND status = 'pending'
                """,
                (now, row["id"]),
            )
            if cursor.rowcount != 1:
                return None
            return ClaimedTask(
                id=str(row["id"]),
                type=str(row["type"]),
                params=_decode_object(str(row["params_json"])),
            )

    def update_progress(self, task_id: str, progress: float, message: str = "") -> None:
        normalized = min(max(float(progress), 0.0), 1.0)
        with self.database.transaction() as connection:
            connection.execute(
                """
                UPDATE tasks SET progress = ?, message = ?, updated_at = ?
                WHERE id = ? AND status = 'running'
                """,
                (normalized, message, _utc_now(), task_id),
            )

    def complete_task(self, task_id: str, result: dict[str, Any]) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                """
                UPDATE tasks
                SET status = 'completed', progress = 1, message = 'task completed',
                    result_json = ?, updated_at = ?
                WHERE id = ? AND status = 'running'
                """,
                (
                    json.dumps(result, ensure_ascii=False, separators=(",", ":")),
                    _utc_now(),
                    task_id,
                ),
            )

    def fail_task(self, task_id: str, error: str) -> None:
        message = error.strip()[:2000] or "task failed"
        result = json.dumps({"error": message}, ensure_ascii=False, separators=(",", ":"))
        with self.database.transaction() as connection:
            connection.execute(
                """
                UPDATE tasks
                SET status = 'failed', message = ?, result_json = ?, updated_at = ?
                WHERE id = ? AND status = 'running'
                """,
                (message, result, _utc_now(), task_id),
            )

    def recover_running_tasks(self) -> int:
        now = _utc_now()
        result = json.dumps(
            {"error": "service restarted while task was running"}, separators=(",", ":")
        )
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """
                UPDATE tasks
                SET status = 'interrupted', message = 'service restarted',
                    result_json = ?, updated_at = ?
                WHERE status = 'running'
                """,
                (result, now),
            )
            return max(cursor.rowcount, 0)

    def retry_task(self, task_id: str) -> TaskRead | None:
        now = _utc_now()
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """
                UPDATE tasks
                SET status = 'pending', progress = 0, message = '', result_json = '{}',
                    updated_at = ?
                WHERE id = ? AND status IN ('failed', 'interrupted')
                """,
                (now, task_id),
            )
            if cursor.rowcount != 1:
                return None
            row = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            assert row is not None
            return self._task_from_row(row)

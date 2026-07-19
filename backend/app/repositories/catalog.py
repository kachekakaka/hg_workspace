"""SQLite repository for works and episodes."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.db import Database
from app.models import EpisodeRead, StatsRead, WorkImport, WorkPage, WorkRead


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _decode_json_array(raw: str) -> list[Any]:
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return []
    return value if isinstance(value, list) else []


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@dataclass(frozen=True, slots=True)
class UpsertedWork:
    created: bool
    work: WorkRead


class CatalogRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def initialize(self) -> list[int]:
        return self.database.migrate()

    @staticmethod
    def _work_from_row(row: sqlite3.Row) -> WorkRead:
        return WorkRead(
            id=int(row["id"]),
            source=str(row["source"]),
            source_work_id=str(row["source_work_id"]),
            series_name=str(row["series_name"]),
            series_cover=str(row["series_cover"]),
            series_intro=str(row["series_intro"]),
            detail_url=str(row["detail_url"]),
            episode_right_text=str(row["episode_right_text"]),
            tags=[str(item) for item in _decode_json_array(row["tags_json"])],
            celebrities=_decode_json_array(row["celebrities_json"]),
            episode_count=int(row["episode_count"]),
            status=str(row["status"]),
            first_seen_at=str(row["first_seen_at"]),
            last_seen_at=str(row["last_seen_at"]),
            updated_at=str(row["updated_at"]),
        )

    @staticmethod
    def _episode_from_row(row: sqlite3.Row) -> EpisodeRead:
        return EpisodeRead(
            id=int(row["id"]),
            work_id=int(row["work_id"]),
            source_episode_id=str(row["source_episode_id"]),
            episode_index=int(row["episode_index"]),
            title=str(row["title"]),
            duration_ms=int(row["duration_ms"]) if row["duration_ms"] is not None else None,
            updated_at=str(row["updated_at"]),
        )

    def upsert_work(self, payload: WorkImport) -> UpsertedWork:
        now = _utc_now()
        tags_json = json.dumps(payload.tags, ensure_ascii=False, separators=(",", ":"))
        celebrities_json = json.dumps(
            payload.celebrities, ensure_ascii=False, separators=(",", ":")
        )

        with self.database.transaction() as connection:
            existing = connection.execute(
                "SELECT id FROM works WHERE source = ? AND source_work_id = ?",
                (payload.source, payload.source_work_id),
            ).fetchone()
            created = existing is None

            if created:
                cursor = connection.execute(
                    """
                    INSERT INTO works (
                        source, source_work_id, series_name, series_cover, series_intro,
                        detail_url, episode_right_text, tags_json, celebrities_json,
                        episode_count, status, first_seen_at, last_seen_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
                    """,
                    (
                        payload.source,
                        payload.source_work_id,
                        payload.series_name,
                        payload.series_cover,
                        payload.series_intro,
                        payload.detail_url,
                        payload.episode_right_text,
                        tags_json,
                        celebrities_json,
                        payload.status,
                        now,
                        now,
                        now,
                    ),
                )
                work_id = int(cursor.lastrowid)
            else:
                work_id = int(existing["id"])
                connection.execute(
                    """
                    UPDATE works SET
                        series_name = ?, series_cover = ?, series_intro = ?,
                        detail_url = ?, episode_right_text = ?, tags_json = ?,
                        celebrities_json = ?, status = ?, last_seen_at = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        payload.series_name,
                        payload.series_cover,
                        payload.series_intro,
                        payload.detail_url,
                        payload.episode_right_text,
                        tags_json,
                        celebrities_json,
                        payload.status,
                        now,
                        now,
                        work_id,
                    ),
                )

            if payload.episodes is not None:
                incoming_ids: list[str] = []
                for episode in payload.episodes:
                    incoming_ids.append(episode.source_episode_id)
                    connection.execute(
                        """
                        INSERT INTO episodes (
                            work_id, source_episode_id, episode_index, title, duration_ms, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(work_id, source_episode_id) DO UPDATE SET
                            episode_index = excluded.episode_index,
                            title = excluded.title,
                            duration_ms = excluded.duration_ms,
                            updated_at = excluded.updated_at
                        """,
                        (
                            work_id,
                            episode.source_episode_id,
                            episode.episode_index,
                            episode.title,
                            episode.duration_ms,
                            now,
                        ),
                    )

                if incoming_ids:
                    placeholders = ",".join("?" for _ in incoming_ids)
                    connection.execute(
                        f"DELETE FROM episodes WHERE work_id = ? "
                        f"AND source_episode_id NOT IN ({placeholders})",
                        (work_id, *incoming_ids),
                    )
                else:
                    connection.execute("DELETE FROM episodes WHERE work_id = ?", (work_id,))

                connection.execute(
                    """
                    UPDATE works
                    SET episode_count = (SELECT COUNT(*) FROM episodes WHERE work_id = ?)
                    WHERE id = ?
                    """,
                    (work_id, work_id),
                )
            row = connection.execute("SELECT * FROM works WHERE id = ?", (work_id,)).fetchone()
            assert row is not None
            return UpsertedWork(created=created, work=self._work_from_row(row))

    def list_works(
        self,
        *,
        query: str = "",
        status: str | None = None,
        tag: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> WorkPage:
        clauses: list[str] = []
        params: list[object] = []

        if query.strip():
            pattern = f"%{_escape_like(query.strip())}%"
            clauses.append(
                "(series_name LIKE ? ESCAPE '\\' OR series_intro LIKE ? ESCAPE '\\')"
            )
            params.extend((pattern, pattern))
        if status:
            clauses.append("status = ?")
            params.append(status)
        if tag.strip():
            encoded_tag = _escape_like(json.dumps(tag.strip(), ensure_ascii=False))
            clauses.append("tags_json LIKE ? ESCAPE '\\'")
            params.append(f"%{encoded_tag}%")

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.database.connect() as connection:
            total = int(
                connection.execute(
                    f"SELECT COUNT(*) AS total FROM works {where}", params
                ).fetchone()["total"]
            )
            rows = connection.execute(
                f"""
                SELECT * FROM works
                {where}
                ORDER BY updated_at DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                (*params, limit, offset),
            ).fetchall()
        return WorkPage(
            items=[self._work_from_row(row) for row in rows],
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_work(self, work_id: int) -> WorkRead | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM works WHERE id = ?", (work_id,)).fetchone()
        return self._work_from_row(row) if row is not None else None

    def get_work_by_source_id(self, source_work_id: str) -> WorkRead | None:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM works
                WHERE source_work_id = ?
                ORDER BY updated_at DESC, id DESC
                LIMIT 1
                """,
                (source_work_id,),
            ).fetchone()
        return self._work_from_row(row) if row is not None else None

    def list_episodes(self, work_id: int) -> list[EpisodeRead]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM episodes
                WHERE work_id = ?
                ORDER BY episode_index ASC, id ASC
                """,
                (work_id,),
            ).fetchall()
        return [self._episode_from_row(row) for row in rows]

    def stats(self) -> StatsRead:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS active,
                    SUM(CASE WHEN status = 'removed' THEN 1 ELSE 0 END) AS removed
                FROM works
                """
            ).fetchone()
        return StatsRead(
            total=int(row["total"] or 0),
            active=int(row["active"] or 0),
            removed=int(row["removed"] or 0),
        )

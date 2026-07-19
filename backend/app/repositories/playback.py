"""SQLite cache for short-lived playback resolutions."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.db import Database


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")


def _parse_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _decode_headers(raw: str) -> dict[str, str]:
    try:
        value: Any = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items()}


@dataclass(frozen=True, slots=True)
class StoredPlaybackResolution:
    episode_id: int
    provider: str
    source_url: str
    headers: dict[str, str]
    mime_type: str
    allow_direct: bool
    expires_at: datetime
    created_at: str
    updated_at: str


class PlaybackRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def initialize(self) -> list[int]:
        return self.database.migrate()

    @staticmethod
    def _from_row(row: sqlite3.Row) -> StoredPlaybackResolution | None:
        expires_at = _parse_datetime(str(row["expires_at"]))
        if expires_at is None:
            return None
        return StoredPlaybackResolution(
            episode_id=int(row["episode_id"]),
            provider=str(row["provider"]),
            source_url=str(row["source_url"]),
            headers=_decode_headers(str(row["headers_json"])),
            mime_type=str(row["mime_type"]),
            allow_direct=bool(row["allow_direct"]),
            expires_at=expires_at,
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def get_active(
        self,
        episode_id: int,
        *,
        now: datetime | None = None,
    ) -> StoredPlaybackResolution | None:
        reference = (now or _utc_now()).astimezone(timezone.utc)
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM playback_resolutions WHERE episode_id = ?",
                (episode_id,),
            ).fetchone()
        if row is None:
            return None
        resolution = self._from_row(row)
        if resolution is None or resolution.expires_at <= reference:
            return None
        return resolution

    def store(
        self,
        *,
        episode_id: int,
        provider: str,
        source_url: str,
        headers: dict[str, str],
        mime_type: str,
        allow_direct: bool,
        expires_at: datetime,
    ) -> StoredPlaybackResolution:
        now = _utc_now()
        headers_json = json.dumps(
            headers,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO playback_resolutions (
                    episode_id, provider, source_url, headers_json, mime_type,
                    allow_direct, expires_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(episode_id) DO UPDATE SET
                    provider = excluded.provider,
                    source_url = excluded.source_url,
                    headers_json = excluded.headers_json,
                    mime_type = excluded.mime_type,
                    allow_direct = excluded.allow_direct,
                    expires_at = excluded.expires_at,
                    updated_at = excluded.updated_at
                """,
                (
                    episode_id,
                    provider,
                    source_url,
                    headers_json,
                    mime_type,
                    int(allow_direct),
                    _iso(expires_at),
                    _iso(now),
                    _iso(now),
                ),
            )
            row = connection.execute(
                "SELECT * FROM playback_resolutions WHERE episode_id = ?",
                (episode_id,),
            ).fetchone()
            assert row is not None
            resolution = self._from_row(row)
            assert resolution is not None
            return resolution

    def invalidate(self, episode_id: int) -> bool:
        with self.database.transaction() as connection:
            cursor = connection.execute(
                "DELETE FROM playback_resolutions WHERE episode_id = ?",
                (episode_id,),
            )
            return cursor.rowcount == 1

    def clear_expired(self, *, now: datetime | None = None) -> int:
        reference = _iso(now or _utc_now())
        with self.database.transaction() as connection:
            cursor = connection.execute(
                "DELETE FROM playback_resolutions WHERE expires_at <= ?",
                (reference,),
            )
            return max(cursor.rowcount, 0)

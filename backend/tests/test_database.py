from __future__ import annotations

from pathlib import Path

from app.db import Database


EXPECTED_TABLES = {
    "episodes",
    "media_cache",
    "playback_resolutions",
    "schema_migrations",
    "settings",
    "tasks",
    "works",
}


def test_migrations_are_idempotent(tmp_path: Path) -> None:
    database = Database(tmp_path / "catalog.db")

    assert database.migrate() == [1, 2]
    assert database.migrate() == []

    with database.connect() as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        versions = [
            row["version"]
            for row in connection.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            )
        ]

    assert EXPECTED_TABLES <= tables
    assert versions == [1, 2]

"""SQLite connection and versioned migration support."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class MigrationError(RuntimeError):
    """Raised when a versioned database migration cannot be applied."""


class Database:
    """Open short-lived SQLite connections with consistent safety settings."""

    def __init__(self, path: Path | str, *, migrations_dir: Path | None = None) -> None:
        self.path = Path(path)
        self.migrations_dir = migrations_dir or Path(__file__).with_name("migrations")

    def _prepare_parent(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self._prepare_parent()
        connection = sqlite3.connect(
            str(self.path),
            timeout=30,
            isolation_level=None,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
            except BaseException:
                connection.rollback()
                raise
            else:
                connection.commit()

    def migrate(self) -> list[int]:
        """Apply unapplied ``NNNN_name.sql`` files and return applied versions."""

        migration_files = sorted(self.migrations_dir.glob("[0-9][0-9][0-9][0-9]_*.sql"))
        if not migration_files:
            raise MigrationError(f"no migrations found in {self.migrations_dir}")

        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            applied = {
                int(row["version"])
                for row in connection.execute("SELECT version FROM schema_migrations")
            }

            newly_applied: list[int] = []
            for path in migration_files:
                try:
                    version = int(path.name.split("_", 1)[0])
                except ValueError as exc:
                    raise MigrationError(f"invalid migration filename: {path.name}") from exc
                if version in applied:
                    continue

                name = path.name.replace("'", "''")
                sql = path.read_text(encoding="utf-8")
                script = (
                    "BEGIN IMMEDIATE;\n"
                    f"{sql}\n"
                    "INSERT INTO schema_migrations(version, name) "
                    f"VALUES ({version}, '{name}');\n"
                    "COMMIT;"
                )
                try:
                    connection.executescript(script)
                except sqlite3.Error as exc:
                    if connection.in_transaction:
                        connection.rollback()
                    raise MigrationError(f"failed migration {path.name}: {exc}") from exc
                newly_applied.append(version)

        return newly_applied

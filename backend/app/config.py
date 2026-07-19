"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    """Small, explicit settings object for the backend process."""

    database_path: Path
    environment: str = "development"
    backend_port: int = 8000

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir = Path(os.environ.get("HG_DATA_DIR", "/data"))
        database_path = Path(os.environ.get("HG_DATABASE", str(data_dir / "hg.db")))
        try:
            backend_port = int(os.environ.get("HG_BACKEND_PORT", "8000"))
        except ValueError as exc:
            raise ValueError("HG_BACKEND_PORT must be an integer") from exc
        if not 1 <= backend_port <= 65535:
            raise ValueError("HG_BACKEND_PORT must be between 1 and 65535")
        return cls(
            database_path=database_path,
            environment=os.environ.get("HG_ENV", "development"),
            backend_port=backend_port,
        )

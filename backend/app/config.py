"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean")


@dataclass(frozen=True, slots=True)
class Settings:
    """Small, explicit settings object for the backend process."""

    database_path: Path
    environment: str = "development"
    backend_port: int = 8000
    task_worker_enabled: bool = True
    task_poll_interval: float = 0.5

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
        try:
            task_poll_interval = float(os.environ.get("HG_TASK_POLL_INTERVAL", "0.5"))
        except ValueError as exc:
            raise ValueError("HG_TASK_POLL_INTERVAL must be a number") from exc
        if not 0.05 <= task_poll_interval <= 60:
            raise ValueError("HG_TASK_POLL_INTERVAL must be between 0.05 and 60 seconds")
        return cls(
            database_path=database_path,
            environment=os.environ.get("HG_ENV", "development"),
            backend_port=backend_port,
            task_worker_enabled=_env_bool("HG_TASK_WORKER_ENABLED", True),
            task_poll_interval=task_poll_interval,
        )

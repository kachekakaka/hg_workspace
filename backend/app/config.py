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


def _env_float(name: str, default: float, *, minimum: float, maximum: float) -> float:
    try:
        value = float(os.environ.get(name, str(default)))
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def _env_int(name: str, default: int, *, minimum: int, maximum: int) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    """Small, explicit settings object for the backend process."""

    database_path: Path
    environment: str = "development"
    backend_port: int = 8000
    task_worker_enabled: bool = True
    task_poll_interval: float = 0.5
    source_timeout: float = 20.0
    source_retries: int = 3
    source_delay: float = 0.15
    playback_max_ttl_seconds: int = 21_600

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir = Path(os.environ.get("HG_DATA_DIR", "/data"))
        database_path = Path(os.environ.get("HG_DATABASE", str(data_dir / "hg.db")))
        return cls(
            database_path=database_path,
            environment=os.environ.get("HG_ENV", "development"),
            backend_port=_env_int("HG_BACKEND_PORT", 8000, minimum=1, maximum=65535),
            task_worker_enabled=_env_bool("HG_TASK_WORKER_ENABLED", True),
            task_poll_interval=_env_float(
                "HG_TASK_POLL_INTERVAL", 0.5, minimum=0.05, maximum=60
            ),
            source_timeout=_env_float("HG_SOURCE_TIMEOUT", 20, minimum=1, maximum=120),
            source_retries=_env_int("HG_SOURCE_RETRIES", 3, minimum=1, maximum=8),
            source_delay=_env_float("HG_SOURCE_DELAY", 0.15, minimum=0, maximum=10),
            playback_max_ttl_seconds=_env_int(
                "HG_PLAYBACK_MAX_TTL", 21_600, minimum=60, maximum=86_400
            ),
        )

from __future__ import annotations
import pytest
from app.config import Settings


def test_source_settings_load_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("HG_DATABASE", "/tmp/hg-source-settings.db")
    monkeypatch.setenv("HG_SOURCE_TIMEOUT", "12.5")
    monkeypatch.setenv("HG_SOURCE_RETRIES", "4")
    monkeypatch.setenv("HG_SOURCE_DELAY", "0.25")
    settings = Settings.from_env()
    assert settings.source_timeout == 12.5
    assert settings.source_retries == 4
    assert settings.source_delay == 0.25


def test_source_settings_reject_unsafe_ranges(monkeypatch) -> None:
    monkeypatch.setenv("HG_DATABASE", "/tmp/hg-source-settings.db")
    monkeypatch.setenv("HG_SOURCE_RETRIES", "0")
    with pytest.raises(ValueError, match="HG_SOURCE_RETRIES"):
        Settings.from_env()

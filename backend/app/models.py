"""API and repository data models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

TaskStatus = Literal["pending", "running", "completed", "failed", "interrupted"]


class EpisodeImport(BaseModel):
    source_episode_id: str = Field(min_length=1, max_length=256)
    episode_index: int = Field(ge=1)
    title: str = Field(default="", max_length=512)
    duration_ms: int | None = Field(default=None, ge=0)

    @field_validator("source_episode_id")
    @classmethod
    def strip_required_episode_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("source_episode_id must not be blank")
        return stripped

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        return value.strip()


class WorkImport(BaseModel):
    source: str = Field(min_length=1, max_length=128)
    source_work_id: str = Field(min_length=1, max_length=256)
    series_name: str = Field(min_length=1, max_length=512)
    series_cover: str = Field(default="", max_length=4096)
    series_intro: str = Field(default="", max_length=20_000)
    detail_url: str = Field(default="", max_length=4096)
    episode_right_text: str = Field(default="", max_length=512)
    tags: list[str] = Field(default_factory=list, max_length=100)
    celebrities: list[str | dict[str, Any]] = Field(default_factory=list, max_length=100)
    episode_count: int | None = Field(default=None, ge=0)
    status: Literal["active", "removed"] = "active"
    episodes: list[EpisodeImport] | None = Field(default=None, max_length=10_000)

    @field_validator("source", "source_work_id", "series_name")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be blank")
        return stripped

    @field_validator("series_cover", "series_intro", "detail_url", "episode_right_text")
    @classmethod
    def strip_optional_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for value in values:
            tag = value.strip()
            if tag and tag not in seen:
                seen.add(tag)
                normalized.append(tag)
        return normalized

    @model_validator(mode="after")
    def validate_episode_identity(self) -> "WorkImport":
        if self.episodes is None:
            return self
        source_ids = [episode.source_episode_id for episode in self.episodes]
        indexes = [episode.episode_index for episode in self.episodes]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("episode source_episode_id values must be unique")
        if len(indexes) != len(set(indexes)):
            raise ValueError("episode episode_index values must be unique")
        return self


class EpisodeRead(BaseModel):
    id: int
    work_id: int
    source_episode_id: str
    episode_index: int
    title: str
    duration_ms: int | None
    updated_at: str


class WorkRead(BaseModel):
    id: int
    source: str
    source_work_id: str
    series_name: str
    series_cover: str
    series_intro: str
    detail_url: str
    episode_right_text: str
    tags: list[str]
    celebrities: list[str | dict[str, Any]]
    episode_count: int
    status: Literal["active", "removed"]
    first_seen_at: str
    last_seen_at: str
    updated_at: str


class WorkPage(BaseModel):
    items: list[WorkRead]
    total: int
    limit: int
    offset: int


class WorkImportResult(BaseModel):
    created: bool
    work: WorkRead


class StatsRead(BaseModel):
    total: int
    active: int
    removed: int


class TaskRead(BaseModel):
    id: str
    task_id: str
    type: str
    status: TaskStatus
    progress: float = Field(ge=0, le=1)
    message: str
    result: dict[str, Any]
    created_at: str
    updated_at: str


class TaskPage(BaseModel):
    items: list[TaskRead]
    total: int
    limit: int
    offset: int

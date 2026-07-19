"""Pure mapping from legacy catalog/checkpoint JSON into canonical imports."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from app.models import EpisodeImport, WorkImport


class LegacyCatalogError(ValueError):
    """Raised when a legacy catalog cannot be mapped safely."""


def _text(value: object) -> str:
    return str(value).strip() if value is not None else ""


def _string_list(value: object) -> list[str]:
    if isinstance(value, str):
        return [item.strip() for item in re.split(r"[,，|]", value) if item.strip()]
    if isinstance(value, list):
        return [_text(item) for item in value if _text(item)]
    return []


def _nonnegative_int(*values: object) -> int | None:
    for value in values:
        if value is None or value == "":
            continue
        try:
            result = int(value)
        except (TypeError, ValueError):
            continue
        if result >= 0:
            return result
    return None


def _catalog_items(payload: object) -> list[Mapping[str, Any]]:
    root = payload
    if isinstance(root, Mapping) and "works" in root:
        root = root["works"]
    if isinstance(root, Mapping):
        values: list[object] = list(root.values())
    elif isinstance(root, list):
        values = root
    else:
        raise LegacyCatalogError("catalog must be a list, mapping, or object with a works field")
    if not values:
        raise LegacyCatalogError("catalog contains no works")
    if len(values) > 10_000:
        raise LegacyCatalogError("catalog contains more than 10000 works")
    items: list[Mapping[str, Any]] = []
    for index, value in enumerate(values):
        if not isinstance(value, Mapping):
            raise LegacyCatalogError(f"work at index {index} must be an object")
        items.append(value)
    return items


def _episodes(raw: Mapping[str, Any], work_id: str) -> list[EpisodeImport] | None:
    present = "episodes" in raw or "vid_list" in raw
    if not present:
        return None
    value = raw.get("episodes", raw.get("vid_list"))
    if value is None:
        return []
    if not isinstance(value, list):
        raise LegacyCatalogError(f"episodes for {work_id} must be a list")
    episodes: list[EpisodeImport] = []
    for position, item in enumerate(value, start=1):
        if isinstance(item, Mapping):
            source_id = _text(
                item.get("source_episode_id")
                or item.get("episode_id")
                or item.get("vid")
                or item.get("id")
                or f"{work_id}:{position}"
            )
            index = _nonnegative_int(
                item.get("episode_index"), item.get("index"), item.get("episode_num")
            ) or position
            title = _text(item.get("title") or item.get("episode_name") or f"第{index}集")
            duration = _nonnegative_int(item.get("duration_ms"))
        else:
            source_id = _text(item) or f"{work_id}:{position}"
            index = position
            title = f"第{position}集"
            duration = None
        episodes.append(
            EpisodeImport(
                source_episode_id=source_id,
                episode_index=index,
                title=title,
                duration_ms=duration,
            )
        )
    return episodes


def normalize_legacy_catalog(payload: object, *, source: str = "novelquick") -> list[WorkImport]:
    """Validate and normalize a legacy catalog without network or file access."""

    stable_source = source.strip()
    if not stable_source:
        raise LegacyCatalogError("source must not be blank")
    normalized: list[WorkImport] = []
    for index, raw in enumerate(_catalog_items(payload)):
        source_work_id = _text(
            raw.get("source_work_id") or raw.get("series_id") or raw.get("work_id") or raw.get("id")
        )
        series_name = _text(raw.get("series_name") or raw.get("title") or raw.get("name"))
        if not source_work_id:
            raise LegacyCatalogError(f"work at index {index} has no source_work_id/series_id")
        if not series_name:
            raise LegacyCatalogError(f"work {source_work_id} has no series_name/title")
        nested_info = raw.get("series_episode_info")
        nested_info = nested_info if isinstance(nested_info, Mapping) else {}
        raw_celebrities = raw.get("celebrities")
        celebrities = raw_celebrities if isinstance(raw_celebrities, list) else _string_list(raw_celebrities)
        status = "removed" if _text(raw.get("status")).lower() == "removed" else "active"
        try:
            normalized.append(
                WorkImport(
                    source=stable_source,
                    source_work_id=source_work_id,
                    series_name=series_name,
                    series_cover=_text(raw.get("series_cover") or raw.get("cover")),
                    series_intro=_text(raw.get("series_intro") or raw.get("intro") or raw.get("description")),
                    detail_url=_text(raw.get("detail_url")),
                    episode_right_text=_text(raw.get("episode_right_text")),
                    tags=_string_list(raw.get("tags")),
                    celebrities=celebrities,
                    episode_count=_nonnegative_int(
                        raw.get("episode_count"),
                        raw.get("episode_cnt"),
                        nested_info.get("episode_total_cnt"),
                        nested_info.get("episode_cnt"),
                    ),
                    status=status,
                    episodes=_episodes(raw, source_work_id),
                )
            )
        except ValidationError as exc:
            raise LegacyCatalogError(f"invalid work {source_work_id}: {exc}") from exc
    return normalized

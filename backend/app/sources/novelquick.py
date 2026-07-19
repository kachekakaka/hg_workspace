"""Pure parsers for legacy NovelQuick/RedFruit SSR payloads.

The legacy project mixed HTTP access, credential handling, parsing, and CLI
output. Phase 1 migrates only the deterministic parsing and URL-construction
parts. Network access remains intentionally absent until the backend source
adapter, authorization policy, timeouts, and fixtures are designed in Phase 2.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

BASE_URL = "https://novelquickapp.com"
ROUTER_DATA_RE = re.compile(
    r"window\._ROUTER_DATA\s*=\s*(\{.*?\})\s*;?\s*</script>",
    re.DOTALL,
)


class SourceParseError(ValueError):
    """Raised when an expected SSR payload is absent or malformed."""


@dataclass(frozen=True, slots=True)
class EpisodeSeed:
    """Source-level episode identity before persistence in SQLite."""

    source_episode_id: str
    episode_index: int
    title: str


def detail_page_url(series_id: str) -> str:
    return f"{BASE_URL}/detail?series_id={quote(series_id.strip(), safe='')}"


def player_page_url(series_id: str, source_episode_id: str) -> str:
    return (
        f"{BASE_URL}/player/{quote(series_id.strip(), safe='')}"
        f"/{quote(source_episode_id.strip(), safe='')}"
    )


def parse_router_data(html: str) -> dict[str, Any]:
    """Extract and decode ``window._ROUTER_DATA`` from an SSR document."""

    match = ROUTER_DATA_RE.search(html)
    if match is None:
        raise SourceParseError("page does not contain window._ROUTER_DATA")
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise SourceParseError("window._ROUTER_DATA is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise SourceParseError("window._ROUTER_DATA must be a JSON object")
    return payload


def _walk_mappings(value: object) -> Iterator[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _walk_mappings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_mappings(child)


def series_detail_from_html(html: str) -> dict[str, Any]:
    """Return the first SSR object containing a non-empty series name."""

    router_data = parse_router_data(html)
    for mapping in _walk_mappings(router_data.get("loaderData")):
        detail = mapping.get("seriesDetail")
        if isinstance(detail, Mapping) and str(detail.get("series_name") or "").strip():
            return dict(detail)
    raise SourceParseError("SSR payload does not contain a valid seriesDetail")


def player_info_from_html(html: str) -> dict[str, Any] | None:
    """Return ``video_player_info`` when the SSR payload exposes one."""

    router_data = parse_router_data(html)
    for mapping in _walk_mappings(router_data.get("loaderData")):
        player_info = mapping.get("video_player_info")
        if isinstance(player_info, Mapping):
            return dict(player_info)
    return None


def episodes_from_detail(detail: Mapping[str, Any]) -> list[EpisodeSeed]:
    """Normalize string or object entries from the legacy ``vid_list``."""

    raw_episodes = detail.get("vid_list")
    if not isinstance(raw_episodes, list):
        return []

    episodes: list[EpisodeSeed] = []
    for position, raw_episode in enumerate(raw_episodes, start=1):
        source_id = ""
        episode_index = position
        title = f"第 {position} 集"

        if isinstance(raw_episode, str):
            source_id = raw_episode.strip()
        elif isinstance(raw_episode, Mapping):
            source_id = str(
                raw_episode.get("video_id")
                or raw_episode.get("item_id")
                or raw_episode.get("vid")
                or ""
            ).strip()
            try:
                episode_index = int(raw_episode.get("index") or position)
            except (TypeError, ValueError):
                episode_index = position
            title = str(raw_episode.get("title") or f"第 {episode_index} 集").strip()

        if not source_id:
            continue
        episodes.append(
            EpisodeSeed(
                source_episode_id=source_id,
                episode_index=max(episode_index, 1),
                title=title or f"第 {max(episode_index, 1)} 集",
            )
        )

    return episodes

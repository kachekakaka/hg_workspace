"""Pure helpers for selecting the best playable URL from source payloads.

This module is a reviewed migration of the useful, network-free logic from the
legacy ``python/video_quality.py`` script. It deliberately performs no HTTP
requests and reads no credentials. Source adapters may pass decoded JSON-like
payloads here after applying their own authorization and policy checks.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

DEFINITION_RANK: dict[str, int] = {
    "4k": 2160,
    "2160p": 2160,
    "1080p": 1080,
    "1080": 1080,
    "超清": 1080,
    "高清": 720,
    "720p": 720,
    "720": 720,
    "540p": 540,
    "540": 540,
    "480p": 480,
    "480": 480,
    "360p": 360,
    "360": 360,
    "流畅": 360,
}

_URL_KEYS = ("main_url", "url", "video_url", "backup_url", "play_url", "src")
_LIST_KEYS = ("video_list", "play_addr", "play_addr_list", "video_info_list")


def _safe_int(value: object) -> int:
    try:
        return int(value) if value is not None else 0
    except (TypeError, ValueError):
        return 0


def _definition_height(value: object) -> int:
    definition = str(value or "").strip().lower()
    if definition in DEFINITION_RANK:
        return DEFINITION_RANK[definition]
    match = re.search(r"(\d{3,4})p?", definition)
    return int(match.group(1)) if match else 0


def _candidate_url(item: Mapping[str, Any]) -> str | None:
    for key in _URL_KEYS:
        value = item.get(key)
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            return value
    return None


def _dimensions(item: Mapping[str, Any]) -> tuple[int, int]:
    metadata = item.get("video_meta") or item.get("meta")
    metadata = metadata if isinstance(metadata, Mapping) else {}
    width = _safe_int(item.get("width") or metadata.get("width"))
    height = _safe_int(item.get("height") or metadata.get("height"))
    return width, height


def _item_score(item: Mapping[str, Any], url: str) -> int:
    declared_height = max(
        _definition_height(item.get(key))
        for key in ("definition", "quality", "gear_name", "video_quality", "resolution")
    )
    width, height = _dimensions(item)
    measured_height = min(width, height) if width and height else 0
    bitrate = _safe_int(item.get("bitrate") or item.get("bit_rate"))

    # Resolution dominates, followed by bitrate. Some legacy URLs use ds=3 for
    # the highest source variant, so keep it only as a small tie-breaker.
    score = max(declared_height, measured_height) * 10_000
    score += min(max(bitrate, 0), 100_000_000) // 1_000
    if "ds=3" in url:
        score += 1
    return score


def pick_best_from_items(items: Iterable[object]) -> tuple[str | None, dict[str, Any]]:
    """Return the highest-scoring HTTP(S) URL and non-sensitive metadata."""

    best_url: str | None = None
    best_score = -1
    best_metadata: dict[str, Any] = {}

    for raw_item in items:
        if not isinstance(raw_item, Mapping):
            continue
        item = dict(raw_item)
        url = _candidate_url(item)
        if url is None:
            continue

        score = _item_score(item, url)
        if score <= best_score:
            continue

        width, height = _dimensions(item)
        best_url = url
        best_score = score
        best_metadata = {
            "definition": item.get("definition") or item.get("quality"),
            "width": width or None,
            "height": height or None,
            "score": score,
        }

    return best_url, best_metadata


def _decode_video_model(raw: str) -> object | None:
    try:
        padded = raw + ("=" * (-len(raw) % 4))
        decoded = base64.b64decode(padded, validate=False).decode("utf-8")
        return json.loads(decoded)
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return None


def pick_best_play_url(data: object) -> tuple[str | None, dict[str, Any]]:
    """Recursively find a playable URL in a decoded JSON-like payload."""

    return _pick_best_play_url(data, depth=0)


def _pick_best_play_url(data: object, *, depth: int) -> tuple[str | None, dict[str, Any]]:
    if depth > 64:
        return None, {}

    if isinstance(data, Mapping):
        mapping = dict(data)

        for list_key in _LIST_KEYS:
            items = mapping.get(list_key)
            if isinstance(items, Sequence) and not isinstance(items, (str, bytes, bytearray)):
                url, metadata = pick_best_from_items(items)
                if url:
                    return url, {"from": list_key, **metadata}

        encoded_model = mapping.get("video_model")
        if isinstance(encoded_model, str) and encoded_model.strip():
            decoded = _decode_video_model(encoded_model.strip())
            if decoded is not None:
                url, metadata = _pick_best_play_url(decoded, depth=depth + 1)
                if url:
                    return url, {"from": "video_model", **metadata}

        direct_url = _candidate_url(mapping)
        if direct_url:
            return direct_url, {"from": next(key for key in _URL_KEYS if mapping.get(key) == direct_url)}

        for value in mapping.values():
            url, metadata = _pick_best_play_url(value, depth=depth + 1)
            if url:
                return url, metadata

    elif isinstance(data, Sequence) and not isinstance(data, (str, bytes, bytearray)):
        url, metadata = pick_best_from_items(data)
        if url:
            return url, metadata
        for item in data:
            url, metadata = _pick_best_play_url(item, depth=depth + 1)
            if url:
                return url, metadata

    return None, {}

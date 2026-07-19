"""Public SSR metadata adapter for NovelQuick.

The adapter intentionally handles only public work metadata.  It sends no
Cookie/Authorization headers, resolves no playback URLs, and never attempts to
bypass DRM, payment, or access controls.
"""
from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from typing import Any

from app.models import WorkImport
from app.services.legacy_catalog import LegacyCatalogError, normalize_legacy_catalog
from app.sources.base import DiscoveryResult, ScrapeMode, SourceProgress
from app.sources.novelquick import BASE_URL, SourceParseError, parse_router_data

USER_AGENT = (
    "Mozilla/5.0 (compatible; HGWorkspace/0.5; +public-metadata-adapter)"
)
ROW_PARAM_MAP = {
    "全部背景": "background",
    "全部主题": "topic",
    "全部设定": "setting",
    "全部受众": "gender",
    "全部时间": "time",
    "全部推荐": "sort_type",
}
INCREMENTAL_LIMITS = {"全部时间": 3, "全部推荐": 1}
SENSITIVE_MEDIA_FIELDS = {
    "vid_list",
    "video_list",
    "play_addr",
    "play_addr_list",
    "video_model",
    "video_player_info",
}


class SourceRequestError(RuntimeError):
    """Raised when a public source request or response is unsafe or unusable."""


class UrlLibTextFetcher:
    """Bounded HTTPS fetcher restricted to the configured source origin."""

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        timeout: float = 20.0,
        retries: int = 3,
        max_bytes: int = 8 * 1024 * 1024,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        parsed = urllib.parse.urlsplit(base_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("source base_url must use https")
        self.base_url = base_url.rstrip("/")
        self.allowed_host = parsed.hostname.lower()
        self.timeout = timeout
        self.retries = retries
        self.max_bytes = max_bytes
        self.sleep = sleep

    def _validate_url(self, url: str) -> None:
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "https" or (parsed.hostname or "").lower() != self.allowed_host:
            raise SourceRequestError("source request must stay on the configured HTTPS origin")
        if parsed.username or parsed.password:
            raise SourceRequestError("source request URL must not contain credentials")

    def __call__(self, url: str) -> str:
        self._validate_url(url)
        last_error: Exception | None = None
        for attempt in range(self.retries):
            try:
                request = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": USER_AGENT,
                        "Accept": "text/html,application/xhtml+xml",
                    },
                )
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    final_url = response.geturl()
                    self._validate_url(final_url)
                    declared = response.headers.get("Content-Length")
                    if declared and int(declared) > self.max_bytes:
                        raise SourceRequestError("source response exceeds configured size limit")
                    body = response.read(self.max_bytes + 1)
                    if len(body) > self.max_bytes:
                        raise SourceRequestError("source response exceeds configured size limit")
                    charset = response.headers.get_content_charset() or "utf-8"
                    return body.decode(charset, "replace")
            except SourceRequestError:
                raise
            except (
                urllib.error.HTTPError,
                urllib.error.URLError,
                TimeoutError,
                socket.timeout,
                OSError,
                ValueError,
            ) as exc:
                last_error = exc
                if attempt + 1 < self.retries:
                    self.sleep(min(2**attempt, 8))
        raise SourceRequestError(f"source request failed after {self.retries} attempts: {url}") from last_error


class NovelQuickSourceAdapter:
    """Discover public work metadata and return canonical ``WorkImport`` rows."""

    name = "novelquick"

    def __init__(
        self,
        *,
        fetch_text: Callable[[str], str] | None = None,
        base_url: str = BASE_URL,
        timeout: float = 20.0,
        retries: int = 3,
        delay: float = 0.15,
        max_selector_tasks: int = 200,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.sleep = sleep
        self.delay = max(delay, 0.0)
        if not 1 <= max_selector_tasks <= 500:
            raise ValueError("max_selector_tasks must be between 1 and 500")
        self.max_selector_tasks = max_selector_tasks
        self.fetch_text = fetch_text or UrlLibTextFetcher(
            base_url=self.base_url,
            timeout=timeout,
            retries=retries,
            sleep=sleep,
        )

    def _fetch_router_data(self, url: str) -> dict[str, Any]:
        try:
            return parse_router_data(self.fetch_text(url))
        except (SourceParseError, json.JSONDecodeError) as exc:
            raise SourceRequestError(f"source page does not contain valid SSR metadata: {url}") from exc

    @staticmethod
    def _list_items(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        loader = payload.get("loaderData")
        if not isinstance(loader, Mapping):
            return []
        items: list[Mapping[str, Any]] = []
        page = loader.get("page")
        if isinstance(page, Mapping):
            for key in ("videoList", "bannerList", "mBannerList"):
                value = page.get(key)
                if isinstance(value, list):
                    items.extend(item for item in value if isinstance(item, Mapping))
        category = loader.get("category_page")
        if isinstance(category, Mapping):
            value = category.get("recommendList")
            if isinstance(value, list):
                items.extend(item for item in value if isinstance(item, Mapping))
        return items

    @staticmethod
    def _category_page(payload: Mapping[str, Any]) -> Mapping[str, Any]:
        loader = payload.get("loaderData")
        if not isinstance(loader, Mapping):
            return {}
        value = loader.get("category_page")
        return value if isinstance(value, Mapping) else {}

    @staticmethod
    def _selector_tasks(
        category_page: Mapping[str, Any], mode: ScrapeMode
    ) -> list[tuple[dict[str, str], str]]:
        tasks: list[tuple[dict[str, str], str]] = []
        seen: set[tuple[tuple[str, str], ...]] = set()
        rows = category_page.get("selectorList")
        if not isinstance(rows, list):
            return tasks
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            row_name = str(row.get("row_name") or "")
            parameter = ROW_PARAM_MAP.get(row_name)
            if not parameter:
                continue
            if mode == "incremental" and row_name not in INCREMENTAL_LIMITS:
                continue
            values = row.get("items")
            if not isinstance(values, list):
                continue
            if mode == "incremental":
                values = values[: INCREMENTAL_LIMITS[row_name]]
            for selector in values:
                if not isinstance(selector, Mapping):
                    continue
                selector_id = str(selector.get("selector_item_id") or "").strip()
                if not selector_id:
                    continue
                params = {parameter: selector_id}
                key = tuple(sorted(params.items()))
                if key in seen:
                    continue
                seen.add(key)
                label = str(selector.get("show_name") or selector_id).strip()
                tasks.append((params, f"category:{parameter}={label}"))
        return tasks

    def _category_url(self, params: Mapping[str, str]) -> str:
        query = urllib.parse.urlencode(params)
        return f"{self.base_url}/category" + (f"?{query}" if query else "")

    def _merge_items(
        self,
        works: dict[str, dict[str, Any]],
        items: list[Mapping[str, Any]],
    ) -> None:
        for raw in items:
            source_id = str(raw.get("series_id") or raw.get("source_work_id") or "").strip()
            name = str(raw.get("series_name") or raw.get("title") or "").strip()
            if not source_id or not name:
                continue
            candidate = {
                key: value
                for key, value in raw.items()
                if key not in SENSITIVE_MEDIA_FIELDS
            }
            candidate["series_id"] = source_id
            candidate["series_name"] = name
            candidate["detail_url"] = f"{self.base_url}/detail?series_id={urllib.parse.quote(source_id)}"
            existing = works.setdefault(source_id, {})
            for key, value in candidate.items():
                if value in (None, "", [], {}):
                    continue
                current = existing.get(key)
                if key == "series_intro" and len(str(current or "")) > len(str(value)):
                    continue
                if current in (None, "", [], {}) or key == "series_intro":
                    existing[key] = value

    def discover(
        self,
        mode: ScrapeMode,
        *,
        progress: SourceProgress | None = None,
    ) -> DiscoveryResult:
        if mode not in {"full", "incremental"}:
            raise ValueError(f"unsupported scrape mode: {mode}")
        raw_works: dict[str, dict[str, Any]] = {}
        request_count = 0

        homepage = self._fetch_router_data(f"{self.base_url}/")
        request_count += 1
        self._merge_items(raw_works, self._list_items(homepage))
        category_payload = self._fetch_router_data(f"{self.base_url}/category")
        request_count += 1
        category_page = self._category_page(category_payload)
        self._merge_items(raw_works, self._list_items(category_payload))
        tasks = self._selector_tasks(category_page, mode)
        if len(tasks) > self.max_selector_tasks:
            raise SourceRequestError("source exposed too many selector tasks")
        total_requests = 2 + len(tasks)
        if progress:
            progress(1, total_requests, "homepage")
            progress(2, total_requests, "category:default")

        for index, (params, label) in enumerate(tasks, start=3):
            if self.delay:
                self.sleep(self.delay)
            payload = self._fetch_router_data(self._category_url(params))
            request_count += 1
            self._merge_items(raw_works, self._list_items(payload))
            if progress:
                progress(index, total_requests, label)

        if not raw_works:
            raise SourceRequestError("source discovery returned no valid works")
        try:
            works: list[WorkImport] = normalize_legacy_catalog(
                list(raw_works.values()), source=self.name
            )
        except LegacyCatalogError as exc:
            raise SourceRequestError(f"source metadata could not be normalized: {exc}") from exc
        works.sort(key=lambda item: item.source_work_id)
        return DiscoveryResult(
            source=self.name,
            mode=mode,
            works=works,
            request_count=request_count,
        )

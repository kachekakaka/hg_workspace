"""Playback provider orchestration and response safety rules."""
from __future__ import annotations

import re
import urllib.parse
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone

from app.models import PlaybackRead
from app.playback.base import PlaybackCandidate, PlaybackProvider
from app.repositories.catalog import CatalogRepository
from app.repositories.playback import PlaybackRepository, StoredPlaybackResolution

_HEADER_NAME_RE = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
_FORBIDDEN_HEADERS = {
    "connection",
    "content-length",
    "host",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}


class EpisodeNotFoundError(LookupError):
    pass


class PlaybackCacheMissError(LookupError):
    pass


class PlaybackProviderUnavailableError(RuntimeError):
    pass


class PlaybackResolutionError(RuntimeError):
    pass


class PlaybackService:
    def __init__(
        self,
        catalog_repository: CatalogRepository,
        playback_repository: PlaybackRepository,
        *,
        providers: Mapping[str, PlaybackProvider] | None = None,
        max_ttl_seconds: int = 21_600,
    ) -> None:
        self.catalog_repository = catalog_repository
        self.playback_repository = playback_repository
        self.providers = dict(providers or {})
        self.max_ttl_seconds = max_ttl_seconds

    @property
    def configured_sources(self) -> tuple[str, ...]:
        return tuple(sorted(self.providers))

    @staticmethod
    def _validate_url(url: str) -> str:
        stripped = url.strip()
        if len(stripped) > 8192:
            raise PlaybackResolutionError("provider returned an oversized playback URL")
        parsed = urllib.parse.urlsplit(stripped)
        if parsed.scheme != "https" or not parsed.hostname:
            raise PlaybackResolutionError("provider returned a non-HTTPS playback URL")
        if parsed.username or parsed.password:
            raise PlaybackResolutionError("provider returned URL credentials")
        return stripped

    @staticmethod
    def _validate_headers(headers: Mapping[str, str]) -> dict[str, str]:
        if len(headers) > 32:
            raise PlaybackResolutionError("provider returned too many headers")
        normalized: dict[str, str] = {}
        for raw_name, raw_value in headers.items():
            name = str(raw_name).strip()
            value = str(raw_value).strip()
            if (
                not name
                or len(name) > 128
                or not _HEADER_NAME_RE.fullmatch(name)
                or name.lower() in _FORBIDDEN_HEADERS
            ):
                raise PlaybackResolutionError("provider returned an unsafe header name")
            if len(value) > 4096 or "\r" in value or "\n" in value:
                raise PlaybackResolutionError("provider returned an unsafe header value")
            normalized[name] = value
        return normalized

    @staticmethod
    def _validate_mime_type(value: object) -> str:
        mime_type = str(value or "").strip()
        if len(mime_type) > 255 or "\r" in mime_type or "\n" in mime_type:
            raise PlaybackResolutionError("provider returned an unsafe mime type")
        return mime_type

    def _validate_candidate(
        self,
        candidate: PlaybackCandidate,
        *,
        now: datetime,
    ) -> tuple[str, dict[str, str], datetime, bool]:
        url = self._validate_url(candidate.url)
        headers = self._validate_headers(candidate.headers)
        expires_at = candidate.expires_at
        if expires_at.tzinfo is None:
            raise PlaybackResolutionError("provider returned a naive expiry")
        expires_at = expires_at.astimezone(timezone.utc)
        if expires_at <= now:
            raise PlaybackResolutionError("provider returned an expired playback URL")
        max_expiry = now + timedelta(seconds=self.max_ttl_seconds)
        if expires_at > max_expiry:
            expires_at = max_expiry
        allow_direct = bool(candidate.allow_direct and not headers)
        return url, headers, expires_at, allow_direct

    @staticmethod
    def _read(
        resolution: StoredPlaybackResolution,
        *,
        cached: bool,
    ) -> PlaybackRead:
        direct = resolution.allow_direct and not resolution.headers
        return PlaybackRead(
            episode_id=resolution.episode_id,
            provider=resolution.provider,
            delivery="direct" if direct else "external_proxy_required",
            url=resolution.source_url if direct else None,
            mime_type=resolution.mime_type,
            expires_at=resolution.expires_at.isoformat(),
            cached=cached,
        )

    def resolve(self, episode_id: int, *, force: bool = False) -> PlaybackRead:
        context = self.catalog_repository.get_episode_context(episode_id)
        if context is None:
            raise EpisodeNotFoundError(f"episode not found: {episode_id}")
        if not force:
            cached = self.playback_repository.get_active(episode_id)
            if cached is not None:
                return self._read(cached, cached=True)

        provider = self.providers.get(context.work.source)
        if provider is None:
            raise PlaybackProviderUnavailableError(
                f"playback provider is not configured for source: {context.work.source}"
            )
        if str(provider.source).strip() != context.work.source:
            raise PlaybackResolutionError("playback provider source does not match work source")
        try:
            candidate = provider.resolve(context.work, context.episode)
        except PlaybackResolutionError:
            raise
        except Exception as exc:
            raise PlaybackResolutionError("playback provider failed") from exc

        now = datetime.now(timezone.utc)
        url, headers, expires_at, allow_direct = self._validate_candidate(
            candidate,
            now=now,
        )
        provider_name = str(provider.name).strip()
        if not provider_name or len(provider_name) > 128:
            raise PlaybackResolutionError("provider returned an invalid name")
        resolution = self.playback_repository.store(
            episode_id=episode_id,
            provider=provider_name,
            source_url=url,
            headers=headers,
            mime_type=self._validate_mime_type(candidate.mime_type),
            allow_direct=allow_direct,
            expires_at=expires_at,
        )
        return self._read(resolution, cached=False)

    def get_cached(self, episode_id: int) -> PlaybackRead:
        if self.catalog_repository.get_episode_context(episode_id) is None:
            raise EpisodeNotFoundError(f"episode not found: {episode_id}")
        resolution = self.playback_repository.get_active(episode_id)
        if resolution is None:
            raise PlaybackCacheMissError(f"no active playback resolution: {episode_id}")
        return self._read(resolution, cached=True)

    def invalidate(self, episode_id: int) -> bool:
        if self.catalog_repository.get_episode_context(episode_id) is None:
            raise EpisodeNotFoundError(f"episode not found: {episode_id}")
        return self.playback_repository.invalidate(episode_id)

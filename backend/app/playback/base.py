"""Provider-neutral playback resolution contract."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from app.models import EpisodeRead, WorkRead


@dataclass(frozen=True, slots=True)
class PlaybackCandidate:
    """Short-lived server-side result returned by an authorized provider."""

    url: str
    expires_at: datetime
    headers: Mapping[str, str] = field(default_factory=dict)
    mime_type: str = ""
    allow_direct: bool = True


class PlaybackProvider(Protocol):
    """Resolve one canonical episode without exposing provider internals."""

    name: str
    source: str

    def resolve(self, work: WorkRead, episode: EpisodeRead) -> PlaybackCandidate: ...

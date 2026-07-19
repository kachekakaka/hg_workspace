"""Small content-source interface used by persistent scrape tasks."""
from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, Protocol
from app.models import WorkImport

ScrapeMode = Literal["full", "incremental"]
SourceProgress = Callable[[int, int, str], None]

@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    source: str
    mode: ScrapeMode
    works: list[WorkImport]
    request_count: int

class SourceAdapter(Protocol):
    name: str
    def discover(
        self,
        mode: ScrapeMode,
        *,
        progress: SourceProgress | None = None,
    ) -> DiscoveryResult: ...

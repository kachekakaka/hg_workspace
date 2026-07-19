"""Single-process persistent task worker."""
from __future__ import annotations
from collections.abc import Mapping
from threading import Event, Lock, Thread
from typing import Any
from pydantic import ValidationError
from app.models import WorkImport
from app.repositories.catalog import CatalogRepository
from app.repositories.tasks import ClaimedTask, TaskRepository
from app.sources.base import ScrapeMode, SourceAdapter


class TaskWorker:
    """Poll SQLite for pending tasks and execute one task at a time."""

    def __init__(
        self,
        task_repository: TaskRepository,
        catalog_repository: CatalogRepository,
        *,
        poll_interval: float = 0.5,
        source_adapters: Mapping[str, SourceAdapter] | None = None,
    ) -> None:
        self.task_repository = task_repository
        self.catalog_repository = catalog_repository
        self.poll_interval = poll_interval
        self.source_adapters = dict(source_adapters or {})
        self._stop = Event()
        self._state_lock = Lock()
        self._thread: Thread | None = None

    @property
    def supported_sources(self) -> tuple[str, ...]:
        return tuple(sorted(self.source_adapters))

    def start(self) -> None:
        with self._state_lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = Thread(target=self._loop, name="hg-task-worker", daemon=True)
            self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        with self._state_lock:
            thread = self._thread
            self._stop.set()
        if thread is not None:
            thread.join(timeout=timeout)
        with self._state_lock:
            if self._thread is thread and (thread is None or not thread.is_alive()):
                self._thread = None

    def _loop(self) -> None:
        while not self._stop.is_set():
            if not self.run_once():
                self._stop.wait(self.poll_interval)

    def run_once(self) -> bool:
        task = self.task_repository.claim_next()
        if task is None:
            return False
        try:
            if task.type == "catalog_import":
                result = self._run_catalog_import(task)
            elif task.type == "scrape_full":
                result = self._run_source_scrape(task, "full")
            elif task.type == "scrape_incremental":
                result = self._run_source_scrape(task, "incremental")
            else:
                raise ValueError(f"unsupported task type: {task.type}")
        except Exception as exc:  # Worker boundary: persist failure instead of dying.
            self.task_repository.fail_task(task.id, str(exc))
        else:
            self.task_repository.complete_task(task.id, result)
        return True

    def _run_catalog_import(self, task: ClaimedTask) -> dict[str, Any]:
        raw_works = task.params.get("works")
        if not isinstance(raw_works, list) or not raw_works:
            raise ValueError("catalog_import task has no works")
        try:
            works = [WorkImport.model_validate(item) for item in raw_works]
        except ValidationError as exc:
            raise ValueError(f"catalog_import task contains invalid canonical data: {exc}") from exc
        created, updated = self._upsert_works(task.id, works, progress_start=0.0)
        return {
            "total": len(works),
            "added": created,
            "updated": updated,
            "restored": 0,
            "removed": 0,
        }

    def _run_source_scrape(self, task: ClaimedTask, mode: ScrapeMode) -> dict[str, Any]:
        source = str(task.params.get("source") or "").strip()
        if not source:
            raise ValueError("scrape task has no source")
        adapter = self.source_adapters.get(source)
        if adapter is None:
            raise ValueError(f"unsupported source: {source}")

        def report_request(done: int, total: int, label: str) -> None:
            fraction = done / total if total > 0 else 0.0
            self.task_repository.update_progress(
                task.id,
                min(max(fraction * 0.6, 0.0), 0.6),
                f"source request {done}/{total}: {label}"[:2000],
            )

        discovery = adapter.discover(mode, progress=report_request)
        if discovery.source != source:
            raise ValueError("source adapter returned a mismatched source name")
        if not discovery.works:
            raise ValueError("source discovery returned no works")
        created, updated = self._upsert_works(
            task.id,
            discovery.works,
            progress_start=0.6,
        )
        return {
            "source": source,
            "mode": mode,
            "requests": discovery.request_count,
            "discovered": len(discovery.works),
            "total": len(discovery.works),
            "added": created,
            "updated": updated,
            "restored": 0,
            "removed": 0,
        }

    def _upsert_works(
        self,
        task_id: str,
        works: list[WorkImport],
        *,
        progress_start: float,
    ) -> tuple[int, int]:
        if not works:
            raise ValueError("task has no works")
        created = 0
        updated = 0
        progress_span = 1.0 - progress_start
        total = len(works)
        for index, payload in enumerate(works, start=1):
            result = self.catalog_repository.upsert_work(payload)
            if result.created:
                created += 1
            else:
                updated += 1
            self.task_repository.update_progress(
                task_id,
                progress_start + progress_span * (index / total),
                f"saved {index}/{total}",
            )
        return created, updated

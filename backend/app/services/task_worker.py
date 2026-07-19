"""Single-process persistent task worker."""

from __future__ import annotations

from threading import Event, Lock, Thread
from typing import Any

from pydantic import ValidationError

from app.models import WorkImport
from app.repositories.catalog import CatalogRepository
from app.repositories.tasks import ClaimedTask, TaskRepository


class TaskWorker:
    """Poll SQLite for pending tasks and execute one task at a time."""

    def __init__(
        self,
        task_repository: TaskRepository,
        catalog_repository: CatalogRepository,
        *,
        poll_interval: float = 0.5,
    ) -> None:
        self.task_repository = task_repository
        self.catalog_repository = catalog_repository
        self.poll_interval = poll_interval
        self._stop = Event()
        self._state_lock = Lock()
        self._thread: Thread | None = None

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

        created = 0
        updated = 0
        total = len(works)
        for index, payload in enumerate(works, start=1):
            result = self.catalog_repository.upsert_work(payload)
            if result.created:
                created += 1
            else:
                updated += 1
            self.task_repository.update_progress(
                task.id,
                index / total,
                f"imported {index}/{total}",
            )
        return {
            "total": total,
            "added": created,
            "updated": updated,
            "restored": 0,
            "removed": 0,
        }

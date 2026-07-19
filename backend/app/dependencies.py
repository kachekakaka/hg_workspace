"""FastAPI dependencies and lazy application state initialization."""
from __future__ import annotations

from threading import Lock

from fastapi import Request

from app.db import Database
from app.repositories.catalog import CatalogRepository
from app.repositories.playback import PlaybackRepository
from app.repositories.tasks import TaskRepository
from app.services.playback import PlaybackService
from app.services.task_worker import TaskWorker
from app.sources.novelquick_adapter import NovelQuickSourceAdapter


def initialize_catalog_repository(application: object) -> CatalogRepository:
    state = application.state  # type: ignore[attr-defined]
    repository = getattr(state, "catalog_repository", None)
    if repository is not None:
        return repository
    lock: Lock = state.catalog_repository_lock
    with lock:
        repository = getattr(state, "catalog_repository", None)
        if repository is None:
            database = Database(state.settings.database_path)
            repository = CatalogRepository(database)
            repository.initialize()
            state.catalog_repository = repository
    return repository


def initialize_task_repository(application: object) -> TaskRepository:
    state = application.state  # type: ignore[attr-defined]
    repository = getattr(state, "task_repository", None)
    if repository is not None:
        return repository
    lock: Lock = state.task_repository_lock
    with lock:
        repository = getattr(state, "task_repository", None)
        if repository is None:
            database = Database(state.settings.database_path)
            repository = TaskRepository(database)
            repository.initialize()
            state.task_repository = repository
    return repository


def initialize_playback_repository(application: object) -> PlaybackRepository:
    state = application.state  # type: ignore[attr-defined]
    repository = getattr(state, "playback_repository", None)
    if repository is not None:
        return repository
    lock: Lock = state.playback_repository_lock
    with lock:
        repository = getattr(state, "playback_repository", None)
        if repository is None:
            database = Database(state.settings.database_path)
            repository = PlaybackRepository(database)
            repository.initialize()
            repository.clear_expired()
            state.playback_repository = repository
    return repository


def initialize_task_worker(application: object) -> TaskWorker:
    state = application.state  # type: ignore[attr-defined]
    worker = getattr(state, "task_worker", None)
    if worker is not None:
        return worker
    lock: Lock = state.task_worker_lock
    with lock:
        worker = getattr(state, "task_worker", None)
        if worker is None:
            adapter = NovelQuickSourceAdapter(
                timeout=state.settings.source_timeout,
                retries=state.settings.source_retries,
                delay=state.settings.source_delay,
            )
            worker = TaskWorker(
                initialize_task_repository(application),
                initialize_catalog_repository(application),
                poll_interval=state.settings.task_poll_interval,
                source_adapters={adapter.name: adapter},
            )
            state.task_worker = worker
    return worker


def initialize_playback_service(application: object) -> PlaybackService:
    state = application.state  # type: ignore[attr-defined]
    service = getattr(state, "playback_service", None)
    if service is not None:
        return service
    lock: Lock = state.playback_service_lock
    with lock:
        service = getattr(state, "playback_service", None)
        if service is None:
            # Production intentionally starts with no provider. A later batch may
            # register only sources the operator is authorized to access.
            service = PlaybackService(
                initialize_catalog_repository(application),
                initialize_playback_repository(application),
                providers={},
                max_ttl_seconds=state.settings.playback_max_ttl_seconds,
            )
            state.playback_service = service
    return service


def get_catalog_repository(request: Request) -> CatalogRepository:
    return initialize_catalog_repository(request.app)


def get_task_repository(request: Request) -> TaskRepository:
    return initialize_task_repository(request.app)


def get_task_worker(request: Request) -> TaskWorker:
    return initialize_task_worker(request.app)


def get_playback_service(request: Request) -> PlaybackService:
    return initialize_playback_service(request.app)

"""FastAPI dependencies and lazy application state initialization."""

from __future__ import annotations

from threading import Lock

from fastapi import Request

from app.db import Database
from app.repositories.catalog import CatalogRepository


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


def get_catalog_repository(request: Request) -> CatalogRepository:
    return initialize_catalog_repository(request.app)

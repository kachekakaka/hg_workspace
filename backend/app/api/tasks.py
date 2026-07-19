"""Persistent task, source-scrape, and legacy catalog-import HTTP APIs."""
from __future__ import annotations
from typing import Annotated, Any, Literal
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from app.dependencies import get_task_repository, get_task_worker
from app.models import TaskPage, TaskRead
from app.repositories.tasks import TaskRepository
from app.services.legacy_catalog import LegacyCatalogError, normalize_legacy_catalog
from app.services.task_worker import TaskWorker

router = APIRouter()
TaskRepositoryDependency = Annotated[TaskRepository, Depends(get_task_repository)]
TaskWorkerDependency = Annotated[TaskWorker, Depends(get_task_worker)]
CatalogBody = Annotated[Any, Body(description="Legacy catalog list or object with a works field")]


def _not_found(task_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"task not found: {task_id}")


def _queue_catalog_import(
    payload: object,
    *,
    source: str,
    repository: TaskRepository,
) -> TaskRead:
    try:
        works = normalize_legacy_catalog(payload, source=source)
    except LegacyCatalogError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return repository.create_task(
        "catalog_import",
        {"source": source.strip(), "works": [work.model_dump(mode="json") for work in works]},
    )


def _queue_scrape(
    mode: Literal["full", "incremental"],
    *,
    source: str,
    repository: TaskRepository,
    worker: TaskWorker,
) -> TaskRead:
    stable_source = source.strip().lower()
    if stable_source not in worker.supported_sources:
        supported = ", ".join(worker.supported_sources) or "none"
        raise HTTPException(
            status_code=422,
            detail=f"unsupported source: {stable_source}; supported sources: {supported}",
        )
    for active_type in ("scrape_full", "scrape_incremental"):
        active = repository.get_active_task(active_type)
        if active is not None:
            raise HTTPException(
                status_code=409,
                detail=f"scrape task already active: {active.task_id}",
            )
    return repository.create_task(f"scrape_{mode}", {"source": stable_source})


@router.post(
    "/api/v1/imports/catalog",
    response_model=TaskRead,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["imports", "tasks"],
)
def queue_catalog_import_v1(
    payload: CatalogBody,
    repository: TaskRepositoryDependency,
    source: str = Query(default="novelquick", min_length=1, max_length=128),
) -> TaskRead:
    return _queue_catalog_import(payload, source=source, repository=repository)


@router.post(
    "/api/v1/tasks/scrape/full",
    response_model=TaskRead,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["sources", "tasks"],
)
def queue_full_scrape_v1(
    repository: TaskRepositoryDependency,
    worker: TaskWorkerDependency,
    source: str = Query(default="novelquick", min_length=1, max_length=128),
) -> TaskRead:
    return _queue_scrape(
        "full", source=source, repository=repository, worker=worker
    )


@router.post(
    "/api/v1/tasks/scrape/incremental",
    response_model=TaskRead,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["sources", "tasks"],
)
def queue_incremental_scrape_v1(
    repository: TaskRepositoryDependency,
    worker: TaskWorkerDependency,
    source: str = Query(default="novelquick", min_length=1, max_length=128),
) -> TaskRead:
    return _queue_scrape(
        "incremental", source=source, repository=repository, worker=worker
    )


@router.get("/api/v1/tasks", response_model=TaskPage, tags=["tasks"])
def list_tasks_v1(
    repository: TaskRepositoryDependency,
    task_status: Literal["pending", "running", "completed", "failed", "interrupted"]
    | None = Query(default=None, alias="status"),
    task_type: str = Query(default="", alias="type", max_length=128),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> TaskPage:
    return repository.list_tasks(
        status=task_status,
        task_type=task_type,
        limit=limit,
        offset=offset,
    )


@router.get("/api/v1/tasks/{task_id}", response_model=TaskRead, tags=["tasks"])
def get_task_v1(task_id: str, repository: TaskRepositoryDependency) -> TaskRead:
    task = repository.get_task(task_id)
    if task is None:
        raise _not_found(task_id)
    return task


@router.post("/api/v1/tasks/{task_id}/retry", response_model=TaskRead, tags=["tasks"])
def retry_task_v1(task_id: str, repository: TaskRepositoryDependency) -> TaskRead:
    task = repository.get_task(task_id)
    if task is None:
        raise _not_found(task_id)
    retried = repository.retry_task(task_id)
    if retried is None:
        raise HTTPException(status_code=409, detail="only failed or interrupted tasks can be retried")
    return retried


@router.post(
    "/api/works/import",
    response_model=TaskRead,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["legacy-web", "imports"],
)
def queue_catalog_import_legacy(
    payload: CatalogBody,
    repository: TaskRepositoryDependency,
    source: str = Query(default="novelquick", min_length=1, max_length=128),
) -> TaskRead:
    return _queue_catalog_import(payload, source=source, repository=repository)


@router.post(
    "/api/tasks/scrape/full",
    response_model=TaskRead,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["legacy-web", "sources", "tasks"],
)
def queue_full_scrape_legacy(
    repository: TaskRepositoryDependency,
    worker: TaskWorkerDependency,
    source: str = Query(default="novelquick", min_length=1, max_length=128),
) -> TaskRead:
    return _queue_scrape("full", source=source, repository=repository, worker=worker)


@router.post(
    "/api/tasks/scrape/incremental",
    response_model=TaskRead,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["legacy-web", "sources", "tasks"],
)
def queue_incremental_scrape_legacy(
    repository: TaskRepositoryDependency,
    worker: TaskWorkerDependency,
    source: str = Query(default="novelquick", min_length=1, max_length=128),
) -> TaskRead:
    return _queue_scrape(
        "incremental", source=source, repository=repository, worker=worker
    )


@router.get("/api/tasks", tags=["legacy-web"])
def list_tasks_legacy(
    repository: TaskRepositoryDependency,
    limit: int = Query(default=100, ge=1, le=200),
) -> dict[str, object]:
    page = repository.list_tasks(limit=limit, offset=0)
    return {"tasks": [task.model_dump(mode="json") for task in page.items], "total": page.total}


@router.get("/api/tasks/{task_id}", response_model=TaskRead, tags=["legacy-web"])
def get_task_legacy(task_id: str, repository: TaskRepositoryDependency) -> TaskRead:
    return get_task_v1(task_id, repository)

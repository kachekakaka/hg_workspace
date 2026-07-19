"""Works, episodes, enrichment, and compatibility read APIs."""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.dependencies import (
    get_catalog_repository,
    get_task_repository,
    get_task_worker,
)
from app.models import (
    EpisodeRead,
    StatsRead,
    TaskRead,
    WorkImport,
    WorkImportResult,
    WorkPage,
    WorkRead,
)
from app.repositories.catalog import CatalogRepository
from app.repositories.tasks import TaskRepository
from app.services.task_worker import TaskWorker

router = APIRouter()
RepositoryDependency = Annotated[CatalogRepository, Depends(get_catalog_repository)]
TaskRepositoryDependency = Annotated[TaskRepository, Depends(get_task_repository)]
TaskWorkerDependency = Annotated[TaskWorker, Depends(get_task_worker)]


def _not_found(identifier: object) -> HTTPException:
    return HTTPException(status_code=404, detail=f"work not found: {identifier}")


def _queue_enrichment(
    work: WorkRead,
    *,
    task_repository: TaskRepository,
    worker: TaskWorker,
) -> TaskRead:
    if work.source not in worker.supported_sources:
        raise HTTPException(
            status_code=422,
            detail=f"source does not support detail enrichment: {work.source}",
        )
    active = task_repository.get_active_task(
        "enrich_work",
        params_match={"work_id": work.id},
    )
    if active is not None:
        raise HTTPException(
            status_code=409,
            detail=f"enrichment task already active: {active.task_id}",
        )
    return task_repository.create_task("enrich_work", {"work_id": work.id})


def _legacy_work(work: WorkRead) -> dict[str, object]:
    return {
        "id": work.id,
        "source": work.source,
        "series_id": work.source_work_id,
        "source_work_id": work.source_work_id,
        "series_name": work.series_name,
        "series_cover": work.series_cover,
        "series_intro": work.series_intro,
        "detail_url": work.detail_url,
        "episode_right_text": work.episode_right_text,
        "episode_cnt": work.episode_count,
        "episode_count": work.episode_count,
        "tags": work.tags,
        "celebrities": work.celebrities,
        "status": work.status,
        "first_seen_at": work.first_seen_at,
        "last_seen_at": work.last_seen_at,
        "updated_at": work.updated_at,
    }


@router.post(
    "/api/v1/works/import",
    response_model=WorkImportResult,
    responses={200: {"description": "Existing work updated"}, 201: {"description": "Work created"}},
    tags=["works"],
)
def import_work(
    payload: WorkImport,
    response: Response,
    repository: RepositoryDependency,
) -> WorkImportResult:
    result = repository.upsert_work(payload)
    response.status_code = status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
    return WorkImportResult(created=result.created, work=result.work)


@router.get("/api/v1/works", response_model=WorkPage, tags=["works"])
def list_works(
    repository: RepositoryDependency,
    q: str = Query(default="", max_length=512),
    work_status: Literal["active", "removed"] | None = Query(default=None, alias="status"),
    tag: str = Query(default="", max_length=256),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> WorkPage:
    return repository.list_works(
        query=q,
        status=work_status,
        tag=tag,
        limit=limit,
        offset=offset,
    )


@router.get("/api/v1/works/{work_id}", response_model=WorkRead, tags=["works"])
def get_work(work_id: int, repository: RepositoryDependency) -> WorkRead:
    work = repository.get_work(work_id)
    if work is None:
        raise _not_found(work_id)
    return work


@router.get(
    "/api/v1/works/{work_id}/episodes",
    response_model=list[EpisodeRead],
    tags=["episodes"],
)
def list_episodes(work_id: int, repository: RepositoryDependency) -> list[EpisodeRead]:
    if repository.get_work(work_id) is None:
        raise _not_found(work_id)
    return repository.list_episodes(work_id)


@router.post(
    "/api/v1/works/{work_id}/enrich",
    response_model=TaskRead,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["works", "tasks", "sources"],
)
def enrich_work_v1(
    work_id: int,
    repository: RepositoryDependency,
    task_repository: TaskRepositoryDependency,
    worker: TaskWorkerDependency,
) -> TaskRead:
    work = repository.get_work(work_id)
    if work is None:
        raise _not_found(work_id)
    return _queue_enrichment(work, task_repository=task_repository, worker=worker)


@router.get("/api/v1/stats", response_model=StatsRead, tags=["works"])
def get_stats_v1(repository: RepositoryDependency) -> StatsRead:
    return repository.stats()


@router.get("/api/works", tags=["legacy-web"])
def list_works_legacy(
    repository: RepositoryDependency,
    q: str = Query(default="", max_length=512),
    work_status: str = Query(default="", alias="status", max_length=32),
    tag: str = Query(default="", max_length=256),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> dict[str, object]:
    if work_status not in {"", "active", "removed"}:
        raise HTTPException(status_code=422, detail="status must be active, removed, or empty")
    result = repository.list_works(
        query=q,
        status=work_status or None,
        tag=tag,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return {
        "total": result.total,
        "page": page,
        "page_size": page_size,
        "works": [_legacy_work(work) for work in result.items],
    }


@router.get("/api/works/{series_id}", tags=["legacy-web"])
def get_work_legacy(series_id: str, repository: RepositoryDependency) -> dict[str, object]:
    work = repository.get_work_by_source_id(series_id)
    if work is None:
        raise _not_found(series_id)
    return _legacy_work(work)


@router.post(
    "/api/works/{series_id}/enrich",
    response_model=TaskRead,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["legacy-web", "works", "tasks"],
)
def enrich_work_legacy(
    series_id: str,
    repository: RepositoryDependency,
    task_repository: TaskRepositoryDependency,
    worker: TaskWorkerDependency,
) -> TaskRead:
    work = repository.get_work_by_source_id(series_id)
    if work is None:
        raise _not_found(series_id)
    return _queue_enrichment(work, task_repository=task_repository, worker=worker)


@router.get("/api/stats", response_model=StatsRead, tags=["legacy-web"])
def get_stats_legacy(repository: RepositoryDependency) -> StatsRead:
    return repository.stats()


@router.get("/api/status", tags=["legacy-web"])
def get_status_legacy(request: Request, repository: RepositoryDependency) -> dict[str, object]:
    stats = repository.stats()
    settings = request.app.state.settings
    return {
        "version": request.app.version,
        "http_port": settings.backend_port,
        "catalog_total": stats.total,
        "catalog_active": stats.active,
    }

"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from threading import Lock

from fastapi import FastAPI
from pydantic import BaseModel

from app.api.tasks import router as tasks_router
from app.api.works import router as works_router
from app.config import Settings
from app.dependencies import (
    initialize_catalog_repository,
    initialize_task_repository,
    initialize_task_worker,
)


class HealthResponse(BaseModel):
    """Stable response returned by the service health endpoint."""

    status: str
    service: str


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the FastAPI application with explicit, testable settings."""

    resolved_settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        initialize_catalog_repository(application)
        task_repository = initialize_task_repository(application)
        task_repository.recover_running_tasks()
        worker = initialize_task_worker(application)
        if application.state.settings.task_worker_enabled:
            worker.start()
        try:
            yield
        finally:
            worker.stop()

    application = FastAPI(
        title="HG Workspace Backend",
        version="0.3.0",
        docs_url="/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.state.catalog_repository_lock = Lock()
    application.state.task_repository_lock = Lock()
    application.state.task_worker_lock = Lock()
    application.include_router(tasks_router)
    application.include_router(works_router)

    @application.get(
        "/health",
        response_model=HealthResponse,
        tags=["system"],
        summary="Service health check",
    )
    def health() -> HealthResponse:
        return HealthResponse(status="ok", service="hg-backend")

    return application


app = create_app()

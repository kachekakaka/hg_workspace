"""FastAPI application entry point."""

from fastapi import FastAPI
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Stable response returned by the service health endpoint."""

    status: str
    service: str


def create_app() -> FastAPI:
    """Create the FastAPI application.

    Keeping construction in a function makes tests independent and gives later
    phases a clear place to register API routers and lifecycle hooks.
    """

    application = FastAPI(
        title="HG Workspace Backend",
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
    )

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

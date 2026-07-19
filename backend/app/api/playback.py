"""Provider-neutral playback resolution API."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.dependencies import get_playback_service
from app.models import PlaybackRead
from app.services.playback import (
    EpisodeNotFoundError,
    PlaybackCacheMissError,
    PlaybackProviderUnavailableError,
    PlaybackResolutionError,
    PlaybackService,
)

router = APIRouter()
PlaybackServiceDependency = Annotated[PlaybackService, Depends(get_playback_service)]


def _translate_error(error: Exception) -> HTTPException:
    if isinstance(error, EpisodeNotFoundError):
        return HTTPException(status_code=404, detail=str(error))
    if isinstance(error, PlaybackCacheMissError):
        return HTTPException(status_code=404, detail=str(error))
    if isinstance(error, PlaybackProviderUnavailableError):
        return HTTPException(status_code=503, detail=str(error))
    if isinstance(error, PlaybackResolutionError):
        return HTTPException(status_code=502, detail=str(error))
    return HTTPException(status_code=500, detail="playback resolution failed")


@router.post(
    "/api/v1/episodes/{episode_id}/playback/resolve",
    response_model=PlaybackRead,
    tags=["playback"],
)
def resolve_playback(
    episode_id: int,
    service: PlaybackServiceDependency,
    force: bool = Query(default=False),
) -> PlaybackRead:
    try:
        return service.resolve(episode_id, force=force)
    except (
        EpisodeNotFoundError,
        PlaybackProviderUnavailableError,
        PlaybackResolutionError,
    ) as exc:
        raise _translate_error(exc) from exc


@router.get(
    "/api/v1/episodes/{episode_id}/playback",
    response_model=PlaybackRead,
    tags=["playback"],
)
def get_cached_playback(
    episode_id: int,
    service: PlaybackServiceDependency,
) -> PlaybackRead:
    try:
        return service.get_cached(episode_id)
    except (EpisodeNotFoundError, PlaybackCacheMissError) as exc:
        raise _translate_error(exc) from exc


@router.delete(
    "/api/v1/episodes/{episode_id}/playback",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["playback"],
)
def invalidate_playback(
    episode_id: int,
    service: PlaybackServiceDependency,
) -> Response:
    try:
        service.invalidate(episode_id)
    except EpisodeNotFoundError as exc:
        raise _translate_error(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/api/v1/playback/providers", tags=["playback"])
def list_playback_providers(
    service: PlaybackServiceDependency,
) -> dict[str, list[str]]:
    return {"sources": list(service.configured_sources)}

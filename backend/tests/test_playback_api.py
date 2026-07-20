from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.config import Settings
from app.dependencies import initialize_playback_repository, initialize_playback_service
from app.main import create_app
from app.playback.base import PlaybackCandidate


class FakeProvider:
    name = "synthetic-direct"
    source = "manual"

    def __init__(
        self,
        *,
        headers: dict[str, str] | None = None,
        url: str = "https://media.example.test/video.mp4",
    ) -> None:
        self.headers = headers or {}
        self.url = url
        self.calls = 0

    def resolve(self, work, episode) -> PlaybackCandidate:
        self.calls += 1
        return PlaybackCandidate(
            url=self.url,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            headers=self.headers,
            mime_type="video/mp4",
            allow_direct=True,
        )


class BrokenProvider:
    name = "synthetic-broken"
    source = "manual"

    def resolve(self, work, episode) -> PlaybackCandidate:
        raise RuntimeError("provider internal detail must not be exposed")


class MismatchedProvider(FakeProvider):
    source = "other-source"


def _create_episode(client: TestClient) -> int:
    response = client.post(
        "/api/v1/works/import",
        json={
            "source": "manual",
            "source_work_id": "work-playback-001",
            "series_name": "Playback Contract Fixture",
            "episodes": [
                {
                    "source_episode_id": "episode-playback-001",
                    "episode_index": 1,
                    "title": "第一集",
                }
            ],
        },
    )
    assert response.status_code == 201
    work_id = response.json()["work"]["id"]
    episodes = client.get(f"/api/v1/works/{work_id}/episodes")
    assert episodes.status_code == 200
    return episodes.json()[0]["id"]


def _app(tmp_path, *, max_ttl: int = 21_600):
    return create_app(
        Settings(
            database_path=tmp_path / "catalog.db",
            task_worker_enabled=False,
            playback_max_ttl_seconds=max_ttl,
        )
    )


def test_direct_resolution_is_cached_and_can_be_invalidated(tmp_path) -> None:
    app = _app(tmp_path)
    with TestClient(app) as client:
        episode_id = _create_episode(client)
        provider = FakeProvider()
        service = initialize_playback_service(client.app)
        service.providers = {"manual": provider}

        providers = client.get("/api/v1/playback/providers")
        assert providers.status_code == 200
        assert providers.json() == {"sources": ["manual"]}

        first = client.post(f"/api/v1/episodes/{episode_id}/playback/resolve")
        assert first.status_code == 200
        assert first.json()["delivery"] == "direct"
        assert first.json()["url"] == "https://media.example.test/video.mp4"
        assert first.json()["mime_type"] == "video/mp4"
        assert first.json()["cached"] is False
        assert provider.calls == 1

        second = client.post(f"/api/v1/episodes/{episode_id}/playback/resolve")
        assert second.status_code == 200
        assert second.json()["cached"] is True
        assert provider.calls == 1

        cached = client.get(f"/api/v1/episodes/{episode_id}/playback")
        assert cached.status_code == 200
        assert cached.json()["cached"] is True

        forced = client.post(
            f"/api/v1/episodes/{episode_id}/playback/resolve?force=true"
        )
        assert forced.status_code == 200
        assert forced.json()["cached"] is False
        assert provider.calls == 2

        deleted = client.delete(f"/api/v1/episodes/{episode_id}/playback")
        assert deleted.status_code == 204
        assert client.get(f"/api/v1/episodes/{episode_id}/playback").status_code == 404


def test_headers_stay_server_side_and_require_external_proxy(tmp_path) -> None:
    app = _app(tmp_path)
    with TestClient(app) as client:
        episode_id = _create_episode(client)
        provider = FakeProvider(headers={"X-Provider-Session": "temporary-value"})
        service = initialize_playback_service(client.app)
        service.providers = {"manual": provider}

        response = client.post(f"/api/v1/episodes/{episode_id}/playback/resolve")
        assert response.status_code == 200
        assert response.json()["delivery"] == "external_proxy_required"
        assert response.json()["url"] is None
        assert "temporary-value" not in response.text

        stored = initialize_playback_repository(client.app).get_active(episode_id)
        assert stored is not None
        assert stored.headers == {"X-Provider-Session": "temporary-value"}
        assert stored.source_url == "https://media.example.test/video.mp4"

        openapi_paths = client.get("/openapi.json").json()["paths"]
        assert not any("/stream" in path or "/proxy" in path for path in openapi_paths)
        assert client.get(f"/api/v1/episodes/{episode_id}/stream").status_code == 404


def test_missing_provider_episode_and_invalid_candidate_have_clear_errors(tmp_path) -> None:
    app = _app(tmp_path)
    with TestClient(app) as client:
        episode_id = _create_episode(client)

        unavailable = client.post(
            f"/api/v1/episodes/{episode_id}/playback/resolve"
        )
        assert unavailable.status_code == 503
        assert "not configured" in unavailable.json()["detail"]

        service = initialize_playback_service(client.app)
        service.providers = {
            "manual": FakeProvider(url="http://media.example.test/video.mp4")
        }
        invalid = client.post(f"/api/v1/episodes/{episode_id}/playback/resolve")
        assert invalid.status_code == 502
        assert "non-HTTPS" in invalid.json()["detail"]

        service.providers = {"manual": MismatchedProvider()}
        mismatched = client.post(f"/api/v1/episodes/{episode_id}/playback/resolve")
        assert mismatched.status_code == 502
        assert "does not match" in mismatched.json()["detail"]

        service.providers = {"manual": BrokenProvider()}
        failed = client.post(f"/api/v1/episodes/{episode_id}/playback/resolve")
        assert failed.status_code == 502
        assert failed.json()["detail"] == "playback provider failed"
        assert "internal detail" not in failed.text

        assert client.post("/api/v1/episodes/999999/playback/resolve").status_code == 404
        assert client.get("/api/v1/episodes/999999/playback").status_code == 404


def test_resolution_expiry_is_clamped_to_configured_ttl(tmp_path) -> None:
    app = _app(tmp_path, max_ttl=60)
    with TestClient(app) as client:
        episode_id = _create_episode(client)
        provider = FakeProvider()
        service = initialize_playback_service(client.app)
        service.providers = {"manual": provider}

        before = datetime.now(timezone.utc)
        response = client.post(f"/api/v1/episodes/{episode_id}/playback/resolve")
        assert response.status_code == 200
        expiry = datetime.fromisoformat(response.json()["expires_at"])
        assert before + timedelta(seconds=50) <= expiry <= before + timedelta(seconds=61)

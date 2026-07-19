from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.models import EpisodeImport, WorkImport, WorkRead
from app.sources.novelquick_adapter import NovelQuickSourceAdapter


def _html(payload: dict) -> str:
    return (
        "<html><script>window._ROUTER_DATA = "
        + json.dumps(payload, ensure_ascii=False)
        + ";</script></html>"
    )


def _work_read(*, episode_count: int = 12) -> WorkRead:
    return WorkRead(
        id=1,
        source="novelquick",
        source_work_id="series-001",
        series_name="原剧名",
        series_cover="",
        series_intro="旧简介",
        detail_url="",
        episode_right_text="",
        tags=["旧标签"],
        celebrities=[],
        episode_count=episode_count,
        status="active",
        first_seen_at="2026-07-19T00:00:00+00:00",
        last_seen_at="2026-07-19T00:00:00+00:00",
        updated_at="2026-07-19T00:00:00+00:00",
    )


def test_detail_enrichment_maps_public_episode_identifiers_only() -> None:
    payload = {
        "loaderData": {
            "detail_page": {
                "seriesDetail": {
                    "series_name": "新剧名",
                    "series_cover": "https://example.invalid/cover.jpg",
                    "series_intro": "更完整的公开简介",
                    "tags": ["都市", "剧情"],
                    "episode_cnt": 2,
                    "vid_list": [
                        "episode-a",
                        {"video_id": "episode-b", "index": 2, "title": "第二集"},
                    ],
                    "play_addr": "https://media.invalid/should-not-persist.mp4",
                    "video_model": "sensitive-media-payload",
                },
                "video_player_info": {"main_url": "https://media.invalid/not-used.mp4"},
            }
        }
    }
    adapter = NovelQuickSourceAdapter(
        fetch_text=lambda _: _html(payload),
        delay=0,
        sleep=lambda _: None,
    )
    progress: list[tuple[int, int, str]] = []

    result = adapter.enrich_work(
        _work_read(),
        progress=lambda *args: progress.append(args),
    )

    assert result.series_name == "新剧名"
    assert result.series_intro == "更完整的公开简介"
    assert result.episode_count == 2
    assert result.episodes is not None
    assert [episode.source_episode_id for episode in result.episodes] == [
        "episode-a",
        "episode-b",
    ]
    assert [episode.title for episode in result.episodes] == ["第 1 集", "第二集"]
    serialized = result.model_dump_json()
    assert "should-not-persist" not in serialized
    assert "video_player_info" not in serialized
    assert progress == [(1, 1, "detail")]


def test_detail_without_usable_episode_list_preserves_existing_episode_state() -> None:
    payload = {
        "loaderData": {
            "detail_page": {
                "seriesDetail": {
                    "series_name": "原剧名",
                    "series_intro": "新简介",
                    "vid_list": [],
                }
            }
        }
    }
    adapter = NovelQuickSourceAdapter(fetch_text=lambda _: _html(payload), delay=0)

    result = adapter.enrich_work(_work_read(episode_count=12))

    assert result.episodes is None
    assert result.episode_count == 12
    assert result.series_intro == "新简介"


def test_detail_enrichment_rejects_mismatched_series_identity() -> None:
    payload = {
        "loaderData": {
            "detail_page": {
                "seriesDetail": {
                    "series_id": "other-series",
                    "series_name": "错误作品",
                    "vid_list": ["ep-1"],
                }
            }
        }
    }
    adapter = NovelQuickSourceAdapter(fetch_text=lambda _: _html(payload), delay=0)

    from app.sources.novelquick_adapter import SourceRequestError
    import pytest

    with pytest.raises(SourceRequestError, match="mismatched series_id"):
        adapter.enrich_work(_work_read())


class _FakeEnrichmentSource:
    name = "novelquick"

    def discover(self, mode, *, progress=None):  # pragma: no cover - not used here
        raise AssertionError("discover should not be called")

    def enrich_work(self, work, *, progress=None):
        if progress:
            progress(1, 1, "detail")
        return WorkImport(
            source=work.source,
            source_work_id=work.source_work_id,
            series_name=f"{work.series_name}（已刷新）",
            series_intro="公开详情已刷新",
            detail_url=f"https://novelquickapp.com/detail?series_id={work.source_work_id}",
            episode_count=2,
            status=work.status,
            episodes=[
                EpisodeImport(source_episode_id="ep-1", episode_index=1, title="第一集"),
                EpisodeImport(source_episode_id="ep-2", episode_index=2, title="第二集"),
            ],
        )


def _import_work(client: TestClient, source_work_id: str, *, source: str = "novelquick") -> dict:
    response = client.post(
        "/api/v1/works/import",
        json={
            "source": source,
            "source_work_id": source_work_id,
            "series_name": f"作品 {source_work_id}",
            "episode_count": 12,
        },
    )
    assert response.status_code == 201
    return response.json()["work"]


def test_enrichment_task_endpoint_worker_and_legacy_alias(tmp_path) -> None:
    app = create_app(
        Settings(database_path=tmp_path / "catalog.db", task_worker_enabled=False)
    )
    with TestClient(app) as client:
        client.app.state.task_worker.source_adapters = {
            "novelquick": _FakeEnrichmentSource()
        }
        first = _import_work(client, "series-001")
        second = _import_work(client, "series-002")

        queued = client.post(f"/api/v1/works/{first['id']}/enrich")
        assert queued.status_code == 202
        assert queued.json()["type"] == "enrich_work"
        task_id = queued.json()["task_id"]

        duplicate = client.post(f"/api/v1/works/{first['id']}/enrich")
        assert duplicate.status_code == 409
        assert task_id in duplicate.json()["detail"]

        # A different work may be queued while the first one is pending.
        other = client.post(f"/api/v1/works/{second['id']}/enrich")
        assert other.status_code == 202

        assert client.app.state.task_worker.run_once() is True
        task = client.get(f"/api/v1/tasks/{task_id}").json()
        assert task["status"] == "completed"
        assert task["result"]["episode_count"] == 2
        assert task["result"]["source_work_id"] == "series-001"

        episodes = client.get(f"/api/v1/works/{first['id']}/episodes")
        assert episodes.status_code == 200
        assert [item["source_episode_id"] for item in episodes.json()] == ["ep-1", "ep-2"]

        refreshed = client.get("/api/works/series-001").json()
        assert refreshed["series_name"].endswith("（已刷新）")

        # Once the first task has completed, the legacy alias can queue it again.
        legacy = client.post("/api/works/series-001/enrich")
        assert legacy.status_code == 202
        assert legacy.json()["type"] == "enrich_work"


def test_enrichment_rejects_unknown_source_and_missing_work(tmp_path) -> None:
    app = create_app(
        Settings(database_path=tmp_path / "catalog.db", task_worker_enabled=False)
    )
    with TestClient(app) as client:
        unsupported = _import_work(client, "manual-001", source="manual")
        response = client.post(f"/api/v1/works/{unsupported['id']}/enrich")
        assert response.status_code == 422
        assert "does not support" in response.json()["detail"]

        missing = client.post("/api/v1/works/999999/enrich")
        assert missing.status_code == 404

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def make_client(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(
            Settings(
                database_path=tmp_path / "api.db",
                environment="test",
                backend_port=18000,
            )
        )
    )


def test_import_list_detail_episode_and_legacy_reads(
    tmp_path: Path, work_payload: dict[str, Any]
) -> None:
    with make_client(tmp_path) as client:
        created = client.post("/api/v1/works/import", json=work_payload)
        assert created.status_code == 201
        work = created.json()["work"]
        work_id = work["id"]
        assert work["tags"] == ["测试", "喜剧"]

        updated = client.post("/api/v1/works/import", json=work_payload)
        assert updated.status_code == 200
        assert updated.json()["created"] is False

        listing = client.get("/api/v1/works", params={"q": "容器", "limit": 10})
        assert listing.status_code == 200
        assert listing.json()["total"] == 1

        detail = client.get(f"/api/v1/works/{work_id}")
        assert detail.status_code == 200
        assert detail.json()["source_work_id"] == "fixture-001"

        episodes = client.get(f"/api/v1/works/{work_id}/episodes")
        assert episodes.status_code == 200
        assert [item["episode_index"] for item in episodes.json()] == [1, 2]

        legacy_list = client.get(
            "/api/works",
            params={"status": "active", "page": 1, "page_size": 60},
        )
        assert legacy_list.status_code == 200
        assert legacy_list.json()["works"][0]["episode_cnt"] == 2
        assert client.get("/api/works", params={"status": ""}).status_code == 200

        legacy_detail = client.get("/api/works/fixture-001")
        assert legacy_detail.status_code == 200
        assert legacy_detail.json()["series_id"] == "fixture-001"

        stats = client.get("/api/stats")
        assert stats.json() == {"total": 1, "active": 1, "removed": 0}

        service_status = client.get("/api/status")
        assert service_status.status_code == 200
        assert service_status.json()["http_port"] == 18000
        assert service_status.json()["catalog_total"] == 1


def test_import_validation_rejects_duplicate_episode_indexes(
    tmp_path: Path, work_payload: dict[str, Any]
) -> None:
    invalid = deepcopy(work_payload)
    invalid["episodes"][1]["episode_index"] = 1

    with make_client(tmp_path) as client:
        response = client.post("/api/v1/works/import", json=invalid)

    assert response.status_code == 422
    assert "episode_index values must be unique" in response.text


def test_import_validation_rejects_blank_episode_source_id(
    tmp_path: Path, work_payload: dict[str, Any]
) -> None:
    invalid = deepcopy(work_payload)
    invalid["episodes"][0]["source_episode_id"] = "   "

    with make_client(tmp_path) as client:
        response = client.post("/api/v1/works/import", json=invalid)

    assert response.status_code == 422
    assert "source_episode_id must not be blank" in response.text


def test_missing_work_returns_404(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        assert client.get("/api/v1/works/999").status_code == 404
        assert client.get("/api/v1/works/999/episodes").status_code == 404


def test_catalog_persists_across_application_restart(
    tmp_path: Path, work_payload: dict[str, Any]
) -> None:
    database_path = tmp_path / "persistent.db"
    settings = Settings(database_path=database_path, environment="test", backend_port=18000)

    with TestClient(create_app(settings)) as client:
        assert client.post("/api/v1/works/import", json=work_payload).status_code == 201

    with TestClient(create_app(settings)) as restarted_client:
        response = restarted_client.get("/api/v1/works")

    assert response.status_code == 200
    assert response.json()["total"] == 1

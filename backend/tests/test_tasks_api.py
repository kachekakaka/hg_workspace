from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def _fixture() -> dict:
    path = Path(__file__).parent / "fixtures" / "legacy_catalog.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_catalog_import_task_persists_and_imports_works(tmp_path) -> None:
    app = create_app(
        Settings(
            database_path=tmp_path / "catalog.db",
            task_worker_enabled=False,
            task_poll_interval=0.05,
        )
    )
    with TestClient(app) as client:
        response = client.post("/api/v1/imports/catalog", json=_fixture())
        assert response.status_code == 202
        task_id = response.json()["task_id"]
        assert response.json()["status"] == "pending"

        assert client.app.state.task_worker.run_once() is True

        task = client.get(f"/api/v1/tasks/{task_id}")
        assert task.status_code == 200
        assert task.json()["status"] == "completed"
        assert task.json()["result"]["added"] == 2

        works = client.get("/api/v1/works")
        assert works.status_code == 200
        assert works.json()["total"] == 2
        by_id = {item["source_work_id"]: item for item in works.json()["items"]}
        assert by_id["legacy-001"]["episode_count"] == 12
        assert by_id["legacy-002"]["episode_count"] == 2

        legacy_tasks = client.get("/api/tasks")
        assert legacy_tasks.status_code == 200
        assert legacy_tasks.json()["tasks"][0]["task_id"] == task_id


def test_legacy_import_endpoint_queues_same_task(tmp_path) -> None:
    app = create_app(Settings(database_path=tmp_path / "catalog.db", task_worker_enabled=False))
    with TestClient(app) as client:
        response = client.post("/api/works/import?source=legacy", json=_fixture())
        assert response.status_code == 202
        assert response.json()["type"] == "catalog_import"


def test_catalog_import_rejects_invalid_payload(tmp_path) -> None:
    app = create_app(Settings(database_path=tmp_path / "catalog.db", task_worker_enabled=False))
    with TestClient(app) as client:
        response = client.post("/api/v1/imports/catalog", json={"works": [{"series_name": "无 ID"}]})
        assert response.status_code == 422
        assert "source_work_id" in response.json()["detail"]

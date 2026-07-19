from __future__ import annotations
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app
from app.models import WorkImport
from app.sources.base import DiscoveryResult


class FakeSource:
    name = "novelquick"
    def __init__(self) -> None:
        self.modes: list[str] = []
    def discover(self, mode, *, progress=None):
        self.modes.append(mode)
        if progress:
            progress(1, 2, "homepage")
            progress(2, 2, "category:default")
        return DiscoveryResult(
            source=self.name,
            mode=mode,
            request_count=2,
            works=[
                WorkImport(
                    source=self.name,
                    source_work_id=f"{mode}-001",
                    series_name=f"{mode} work",
                    episode_count=12,
                )
            ],
        )


def test_source_task_endpoint_worker_and_legacy_alias(tmp_path) -> None:
    app = create_app(Settings(database_path=tmp_path / "catalog.db", task_worker_enabled=False))
    with TestClient(app) as client:
        fake = FakeSource()
        client.app.state.task_worker.source_adapters = {fake.name: fake}

        response = client.post("/api/v1/tasks/scrape/incremental")
        assert response.status_code == 202
        task_id = response.json()["task_id"]
        assert response.json()["type"] == "scrape_incremental"

        duplicate = client.post("/api/tasks/scrape/full")
        assert duplicate.status_code == 409
        assert task_id in duplicate.json()["detail"]

        assert client.app.state.task_worker.run_once() is True
        task = client.get(f"/api/v1/tasks/{task_id}").json()
        assert task["status"] == "completed"
        assert task["result"] == {
            "source": "novelquick",
            "mode": "incremental",
            "requests": 2,
            "discovered": 1,
            "total": 1,
            "added": 1,
            "updated": 0,
            "restored": 0,
            "removed": 0,
        }
        assert client.get("/api/v1/works").json()["total"] == 1
        assert fake.modes == ["incremental"]

        second = client.post("/api/tasks/scrape/full")
        assert second.status_code == 202
        assert second.json()["type"] == "scrape_full"


def test_source_task_rejects_unknown_source(tmp_path) -> None:
    app = create_app(Settings(database_path=tmp_path / "catalog.db", task_worker_enabled=False))
    with TestClient(app) as client:
        response = client.post("/api/v1/tasks/scrape/full?source=unknown")
        assert response.status_code == 422
        assert "supported sources" in response.json()["detail"]


def test_source_failure_is_persisted(tmp_path) -> None:
    class BrokenSource:
        name = "novelquick"
        def discover(self, mode, *, progress=None):
            raise RuntimeError("synthetic source failure")

    app = create_app(Settings(database_path=tmp_path / "catalog.db", task_worker_enabled=False))
    with TestClient(app) as client:
        client.app.state.task_worker.source_adapters = {"novelquick": BrokenSource()}
        task_id = client.post("/api/v1/tasks/scrape/full").json()["task_id"]
        assert client.app.state.task_worker.run_once() is True
        task = client.get(f"/api/v1/tasks/{task_id}").json()
        assert task["status"] == "failed"
        assert task["result"]["error"] == "synthetic source failure"

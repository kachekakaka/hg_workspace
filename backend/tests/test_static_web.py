from __future__ import annotations
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app


def test_scrape_admin_page_and_assets_are_served(tmp_path) -> None:
    app = create_app(Settings(database_path=tmp_path / "catalog.db", task_worker_enabled=False))
    with TestClient(app) as client:
        page = client.get("/tasks.html")
        assert page.status_code == 200
        assert "任务、公开元数据抓取与本地 catalog 导入" in page.text
        assert "incrementalScrapeButton" in page.text
        assert "fullScrapeButton" in page.text

        api_js = client.get("/js/api.js")
        assert api_js.status_code == 200
        assert "/api/v1/tasks/scrape/${mode}" in api_js.text
        assert "/api/v1/works/${encodeURIComponent(workId)}/enrich" in api_js.text

        tasks_js = client.get("/js/tasks.js")
        assert tasks_js.status_code == 200
        assert "queueSourceScrape" in tasks_js.text
        assert "enrich_work" in tasks_js.text
        assert "scrape_incremental" in tasks_js.text


def test_api_and_openapi_routes_take_precedence_over_static_mount(tmp_path) -> None:
    app = create_app(Settings(database_path=tmp_path / "catalog.db", task_worker_enabled=False))
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok", "service": "hg-backend"}
        status = client.get("/api/status")
        assert status.status_code == 200
        assert status.json()["version"] == "0.7.0"
        schema = client.get("/openapi.json")
        assert schema.status_code == 200
        paths = schema.json()["paths"]
        assert "/api/v1/tasks/scrape/full" in paths
        assert "/api/v1/tasks/scrape/incremental" in paths
        assert "/api/v1/works/{work_id}/enrich" in paths
        assert "/api/v1/episodes/{episode_id}/playback/resolve" in paths
        assert "/api/v1/episodes/{episode_id}/playback" in paths
        assert "/api/v1/playback/providers" in paths


def test_admin_ui_exposes_only_implemented_source_actions(tmp_path) -> None:
    app = create_app(Settings(database_path=tmp_path / "catalog.db", task_worker_enabled=False))
    with TestClient(app) as client:
        combined = "\n".join(
            client.get(path).text for path in ("/tasks.html", "/js/api.js", "/js/tasks.js", "/js/index.js")
        )
        assert "/api/v1/tasks/scrape/${mode}" in combined
        assert "/api/v1/works/${encodeURIComponent(workId)}/enrich" in combined
        assert "WebSocket" not in combined
        assert "Authorization" in combined
        assert "DRM" in combined
        assert "刷新公开详情与分集" in combined
        # The contract exists, but the Web player remains hidden until a real
        # provider and proxy/direct delivery path are implemented.
        assert "/playback/resolve" not in combined

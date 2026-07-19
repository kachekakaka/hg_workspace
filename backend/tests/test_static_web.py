from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_static_admin_pages_and_assets_are_served(tmp_path) -> None:
    app = create_app(Settings(database_path=tmp_path / "catalog.db", task_worker_enabled=False))
    with TestClient(app) as client:
        pages = {
            "/": "作品库",
            "/index.html": "作品库",
            "/stats.html": "作品库统计",
            "/tasks.html": "任务与本地 catalog 导入",
        }
        for path, marker in pages.items():
            response = client.get(path)
            assert response.status_code == 200
            assert marker in response.text
            assert response.headers["content-type"].startswith("text/html")

        css = client.get("/css/style.css")
        assert css.status_code == 200
        assert "--primary" in css.text

        api_js = client.get("/js/api.js")
        assert api_js.status_code == 200
        assert "/api/v1/imports/catalog" in api_js.text


def test_api_and_openapi_routes_take_precedence_over_static_mount(tmp_path) -> None:
    app = create_app(Settings(database_path=tmp_path / "catalog.db", task_worker_enabled=False))
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok", "service": "hg-backend"}
        status = client.get("/api/status")
        assert status.status_code == 200
        assert status.json()["version"] == "0.4.0"
        assert client.get("/openapi.json").status_code == 200
        assert client.get("/docs").status_code == 200


def test_admin_ui_does_not_reference_removed_legacy_actions(tmp_path) -> None:
    app = create_app(Settings(database_path=tmp_path / "catalog.db", task_worker_enabled=False))
    with TestClient(app) as client:
        combined = "\n".join(
            client.get(path).text
            for path in ("/", "/tasks.html", "/js/api.js", "/js/index.js", "/js/tasks.js")
        )
        assert "/api/tasks/scrape/full" not in combined
        assert "/api/tasks/scrape/incremental" not in combined
        assert "/enrich" not in combined
        assert "WebSocket" not in combined

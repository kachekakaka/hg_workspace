from __future__ import annotations

from app.db import Database
from app.models import EpisodeImport, WorkImport
from app.repositories.catalog import CatalogRepository


def test_declared_episode_count_is_used_without_episode_snapshot(tmp_path) -> None:
    repository = CatalogRepository(Database(tmp_path / "catalog.db"))
    repository.initialize()

    first = repository.upsert_work(
        WorkImport(
            source="legacy",
            source_work_id="count-1",
            series_name="声明集数",
            episode_count=88,
        )
    )
    assert first.work.episode_count == 88

    updated = repository.upsert_work(
        WorkImport(
            source="legacy",
            source_work_id="count-1",
            series_name="实际分集",
            episode_count=99,
            episodes=[
                EpisodeImport(source_episode_id="e1", episode_index=1),
                EpisodeImport(source_episode_id="e2", episode_index=2),
            ],
        )
    )
    assert updated.work.episode_count == 2

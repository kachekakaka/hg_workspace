from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from app.db import Database
from app.models import WorkImport
from app.repositories.catalog import CatalogRepository


def make_repository(tmp_path: Path) -> CatalogRepository:
    repository = CatalogRepository(Database(tmp_path / "catalog.db"))
    repository.initialize()
    return repository


def test_upsert_is_idempotent_and_synchronizes_episodes(
    tmp_path: Path, work_payload: dict[str, Any]
) -> None:
    repository = make_repository(tmp_path)

    created = repository.upsert_work(WorkImport.model_validate(work_payload))
    repeated = repository.upsert_work(WorkImport.model_validate(work_payload))

    assert created.created is True
    assert repeated.created is False
    assert repeated.work.id == created.work.id
    assert repeated.work.episode_count == 2

    updated_payload = deepcopy(work_payload)
    updated_payload["series_name"] = "更新后的短剧"
    updated_payload["episodes"] = [
        updated_payload["episodes"][1],
        {
            "source_episode_id": "fixture-001-ep-3",
            "episode_index": 3,
            "title": "第三集",
            "duration_ms": 63000,
        },
    ]
    updated = repository.upsert_work(WorkImport.model_validate(updated_payload))
    episodes = repository.list_episodes(updated.work.id)

    assert updated.created is False
    assert updated.work.series_name == "更新后的短剧"
    assert updated.work.episode_count == 2
    assert [episode.source_episode_id for episode in episodes] == [
        "fixture-001-ep-2",
        "fixture-001-ep-3",
    ]


def test_metadata_only_update_preserves_existing_episodes(
    tmp_path: Path, work_payload: dict[str, Any]
) -> None:
    repository = make_repository(tmp_path)
    created = repository.upsert_work(WorkImport.model_validate(work_payload))

    metadata_only = deepcopy(work_payload)
    metadata_only.pop("episodes")
    metadata_only["series_intro"] = "只更新元数据，不同步分集。"
    updated = repository.upsert_work(WorkImport.model_validate(metadata_only))

    assert updated.created is False
    assert updated.work.episode_count == 2
    assert len(repository.list_episodes(created.work.id)) == 2

    metadata_only["episodes"] = []
    cleared = repository.upsert_work(WorkImport.model_validate(metadata_only))
    assert cleared.work.episode_count == 0
    assert repository.list_episodes(created.work.id) == []


def test_list_search_status_and_tag_filters(
    tmp_path: Path, work_payload: dict[str, Any]
) -> None:
    repository = make_repository(tmp_path)
    repository.upsert_work(WorkImport.model_validate(work_payload))

    removed = deepcopy(work_payload)
    removed["source_work_id"] = "fixture-removed"
    removed["series_name"] = "已下架悬疑剧"
    removed["series_intro"] = "另一个简介"
    removed["tags"] = ["悬疑"]
    removed["status"] = "removed"
    removed["episodes"] = []
    repository.upsert_work(WorkImport.model_validate(removed))

    assert repository.list_works(query="第一部").total == 1
    assert repository.list_works(status="removed").total == 1
    assert repository.list_works(tag="喜剧").total == 1
    page = repository.list_works(limit=1, offset=1)
    assert page.total == 2
    assert len(page.items) == 1

    stats = repository.stats()
    assert stats.model_dump() == {"total": 2, "active": 1, "removed": 1}

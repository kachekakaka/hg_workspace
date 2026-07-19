from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.legacy_catalog import LegacyCatalogError, normalize_legacy_catalog


def _fixture() -> dict:
    path = Path(__file__).parent / "fixtures" / "legacy_catalog.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_normalize_legacy_catalog_uses_stable_source_and_declared_count() -> None:
    works = normalize_legacy_catalog(_fixture(), source="novelquick")

    assert len(works) == 2
    assert works[0].source == "novelquick"
    assert works[0].source_work_id == "legacy-001"
    assert works[0].episode_count == 12
    assert works[0].episodes is None
    assert works[1].tags == ["测试", "已下架"]
    assert [episode.source_episode_id for episode in works[1].episodes or []] == ["vid-1", "vid-2"]


def test_normalize_legacy_checkpoint_mapping() -> None:
    works = normalize_legacy_catalog(
        {"works": {"abc": {"series_id": "abc", "series_name": "映射作品"}}},
        source="novelquick",
    )
    assert works[0].source_work_id == "abc"


def test_normalize_legacy_catalog_rejects_missing_identity() -> None:
    with pytest.raises(LegacyCatalogError, match="source_work_id"):
        normalize_legacy_catalog({"works": [{"series_name": "无 ID"}]})

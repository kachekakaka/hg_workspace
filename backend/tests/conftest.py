from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def work_payload() -> dict[str, Any]:
    path = Path(__file__).parent / "fixtures" / "catalog_work.json"
    return json.loads(path.read_text(encoding="utf-8"))

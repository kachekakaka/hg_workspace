from __future__ import annotations

from app.db import Database
from app.repositories.tasks import TaskRepository


def test_task_lifecycle_and_listing(tmp_path) -> None:
    repository = TaskRepository(Database(tmp_path / "tasks.db"))
    repository.initialize()

    created = repository.create_task("catalog_import", {"works": [{"x": 1}]})
    assert created.status == "pending"

    claimed = repository.claim_next()
    assert claimed is not None
    assert claimed.id == created.id
    assert claimed.params["works"] == [{"x": 1}]

    repository.update_progress(created.id, 0.5, "half")
    repository.complete_task(created.id, {"added": 1})
    completed = repository.get_task(created.id)
    assert completed is not None
    assert completed.status == "completed"
    assert completed.progress == 1
    assert completed.result == {"added": 1}
    assert repository.list_tasks().total == 1


def test_running_tasks_are_interrupted_and_can_be_retried(tmp_path) -> None:
    repository = TaskRepository(Database(tmp_path / "tasks.db"))
    repository.initialize()
    task = repository.create_task("catalog_import", {"works": [{"x": 1}]})
    assert repository.claim_next() is not None

    assert repository.recover_running_tasks() == 1
    interrupted = repository.get_task(task.id)
    assert interrupted is not None
    assert interrupted.status == "interrupted"

    retried = repository.retry_task(task.id)
    assert retried is not None
    assert retried.status == "pending"

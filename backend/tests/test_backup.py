import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import Engine

import app.models  # noqa: F401  (registers tables)
from app.core.config import Settings
from app.core.db import Base, make_engine, make_session_factory
from app.integrations.storage import Bucket
from app.models import Photo
from app.services.backup import BackupService
from tests.fakes import FakeStorage

NOW = datetime(2026, 3, 15, 3, 30, tzinfo=UTC)


@pytest.fixture
def live_engine(tmp_path: Path) -> Engine:
    engine = make_engine(f"sqlite:///{tmp_path / 'live.db'}")
    Base.metadata.create_all(engine)
    with make_session_factory(engine)() as db:
        db.add(Photo(id="p1", title="kept", aspect_ratio=1.5))
        db.commit()
    return engine


def key_for(day: datetime) -> str:
    return f"backups/{day:%Y-%m-%d}.db"


def test_backup_uploads_valid_sqlite_copy(
    live_engine: Engine, storage: FakeStorage, tmp_path: Path
) -> None:
    key = BackupService(live_engine, storage).run(NOW)

    assert key == "backups/2026-03-15.db"
    restored = tmp_path / "restored.db"
    restored.write_bytes(storage.get_bytes(Bucket.PRIVATE, key))
    with sqlite3.connect(restored) as conn:
        assert conn.execute("select title from photo").fetchall() == [("kept",)]
        assert conn.execute("pragma integrity_check").fetchone() == ("ok",)


def test_backups_older_than_30_days_pruned(live_engine: Engine, storage: FakeStorage) -> None:
    for days_old in (29, 30, 31, 90):
        storage.put_bytes(Bucket.PRIVATE, key_for(NOW - timedelta(days=days_old)), b"old", "x/y")
    for unrelated in ("backups/notes.txt", "originals/x.jpg", "backups/2026-13-45.db"):
        storage.put_bytes(Bucket.PRIVATE, unrelated, b"keep", "x/y")

    BackupService(live_engine, storage).run(NOW)

    left = set(storage.list_keys(Bucket.PRIVATE, ""))
    assert key_for(NOW - timedelta(days=30)) in left  # exactly 30 days old is kept
    assert key_for(NOW - timedelta(days=29)) in left
    assert key_for(NOW - timedelta(days=31)) not in left
    assert key_for(NOW - timedelta(days=90)) not in left
    assert {"backups/notes.txt", "originals/x.jpg", "backups/2026-13-45.db"} <= left


def test_backup_failure_raises_and_leaves_existing_backups(
    live_engine: Engine, storage: FakeStorage
) -> None:
    ancient = key_for(NOW - timedelta(days=90))
    storage.put_bytes(Bucket.PRIVATE, ancient, b"old", "x/y")

    def fail(*args: object, **kwargs: object) -> None:
        raise RuntimeError("r2 unreachable")

    storage.put_bytes = fail  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="r2 unreachable"):
        BackupService(live_engine, storage).run(NOW)

    assert storage.exists(Bucket.PRIVATE, ancient)  # nothing is pruned unless the new one is safe


def test_env_example_documents_every_setting() -> None:
    lines = (Path(__file__).parents[1] / ".env.example").read_text().splitlines()
    documented = {line.split("=")[0].strip().lower() for line in lines if "=" in line}
    assert documented == set(Settings.model_fields)

"""Seeding against a real database."""

import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import Chapter, Collection, Photo, Status
from app.services.seed import seed_from_json
from tests.fakes import FakeStorage, FakeUnsplash
from tests.support.seed_data import SEED


def test_a_complete_seed_on_a_real_database_then_a_second_run_changes_nothing(
    tmp_path: Path,
    client: TestClient,
    storage: FakeStorage,
    settings: Settings,
    unsplash: FakeUnsplash,
    db: Session,
) -> None:
    seed_file = tmp_path / "curation.json"
    seed_file.write_text(json.dumps(SEED))
    uow_factory = client.app.state.uow_factory  # type: ignore[attr-defined]

    first = seed_from_json(seed_file, uow_factory, storage, settings, unsplash)
    again = seed_from_json(seed_file, uow_factory, storage, settings, unsplash)

    assert (first.imported, first.collections_created, first.remaining) == (3, 1, [])
    assert (again.imported, again.already_present, again.collections_created) == (0, 3, 0)
    db.expire_all()
    photos = {p.unsplash_id: p for p in db.scalars(select(Photo))}
    assert [p.unsplash_id for p in sorted(photos.values(), key=lambda p: p.sort_position)] == [
        "c",
        "a",
        "b",
    ]
    assert all(p.status is Status.PUBLISHED for p in photos.values())
    collection = db.scalars(select(Collection)).one()
    assert collection.cover_photo_ids == [photos["a"].id, photos["c"].id]
    assert len(db.scalars(select(Chapter)).all()) == 2

"""Seeding against a real database, and the Node script that exports the seed file."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
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
    assert [p.unsplash_id for p in sorted(photos.values(), key=lambda p: p.sort_position)] == ["c", "a", "b"]
    assert all(p.status is Status.PUBLISHED for p in photos.values())
    collection = db.scalars(select(Collection)).one()
    assert collection.cover_photo_ids == [photos["a"].id, photos["c"].id]
    assert len(db.scalars(select(Chapter)).all()) == 2


@pytest.mark.skipif(shutil.which("node") is None, reason="needs node to read curation.ts")
def test_export_script_produces_a_seed_the_backend_accepts(tmp_path: Path) -> None:
    repo = Path(__file__).parents[4]
    out = tmp_path / "curation.json"
    subprocess.run(
        ["node", str(repo / "scripts" / "export-curation.mjs"), str(out)],
        check=True,
        capture_output=True,
    )
    from app.schemas.seed import SeedData

    data = SeedData.model_validate_json(out.read_text())
    snapshot_ids = {p.id for p in data.photos}
    assert len(data.photos) == 43
    assert {c.slug for c in data.collections} == {
        "ujjain-omkareshwar-indore",
        "mumbai",
        "elsewhere",
    }
    for collection in data.collections:
        for chapter in collection.chapters:
            assert set(chapter.photo_ids) <= snapshot_ids

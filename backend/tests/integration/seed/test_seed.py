import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.integrations.storage import Bucket
from app.models import Collection, Photo, Status
from app.services.seed import seed_from_json
from tests.fakes import FakeStorage, FakeUnsplash

SEED: dict[str, Any] = {
    "photos": [
        {
            "id": "a",
            "pid": "p-a",
            "aspectRatio": 1.5,
            "title": "Photo A",
            "place": "Ram Ghat, Ujjain",
            "exif": {"camera": "Sony ZV-E10", "focalLength": 38, "iso": 640},
            "unsplashUrl": "https://unsplash.com/photos/a",
        },
        {"id": "b", "pid": "p-b", "aspectRatio": 1.5, "title": "Photo B", "unsplashUrl": "u/b"},
        {"id": "c", "pid": "p-c", "aspectRatio": 1.5, "title": "Photo C", "unsplashUrl": "u/c"},
    ],
    "order": ["c", "a", "b"],
    "excluded": [],
    "collections": [
        {
            "slug": "ujjain",
            "title": "Ujjain",
            "place": "Madhya Pradesh",
            "year": "2024",
            "intro": "Intro",
            "coverIds": ["a", "c"],
            "chapters": [
                {"title": "One", "note": "First", "photoIds": ["a", "b"]},
                {"title": "Two", "note": "Second", "photoIds": ["c"]},
            ],
        }
    ],
}


@pytest.fixture
def seed_file(tmp_path: Path) -> Path:
    path = tmp_path / "curation.json"
    path.write_text(json.dumps(SEED))
    return path


def seed(
    seed_file: Path, client: TestClient, storage: FakeStorage, settings: Settings, un: FakeUnsplash
) -> Any:
    return seed_from_json(seed_file, client.app.state.session_factory, storage, settings, un)  # type: ignore[attr-defined]


def by_unsplash_id(db: Session) -> dict[str, Photo]:
    db.expire_all()
    return {p.unsplash_id: p for p in db.scalars(select(Photo)) if p.unsplash_id}


def test_creates_published_photos_with_snapshot_titles_in_curated_order(
    seed_file: Path,
    client: TestClient,
    storage: FakeStorage,
    settings: Settings,
    unsplash: FakeUnsplash,
    db: Session,
) -> None:
    report = seed(seed_file, client, storage, settings, unsplash)

    assert (report.imported, report.remaining, report.missing_from_unsplash) == (3, [], [])
    photos = by_unsplash_id(db)
    assert sorted(p.title for p in photos.values()) == ["Photo A", "Photo B", "Photo C"]
    assert photos["a"].place == "Ram Ghat, Ujjain"
    assert photos["a"].unsplash_url == "https://unsplash.com/photos/a"
    assert all(p.status is Status.PUBLISHED for p in photos.values())
    assert all(p.allow_download is False for p in photos.values())
    ordered = sorted(photos.values(), key=lambda p: p.sort_position)
    assert [p.unsplash_id for p in ordered] == ["c", "a", "b"]
    assert storage.exists(Bucket.PRIVATE, f"originals/{photos['a'].id}.jpg")


def test_snapshot_exif_fills_gaps_and_file_exif_wins(
    seed_file: Path,
    client: TestClient,
    storage: FakeStorage,
    settings: Settings,
    unsplash: FakeUnsplash,
    db: Session,
) -> None:
    from tests.support.images import make_jpeg, rich_exif

    unsplash.files["a"] = make_jpeg((300, 200), exif=rich_exif())  # file says Sony ZV-E10, iso 640
    seed(seed_file, client, storage, settings, unsplash)
    exif = by_unsplash_id(db)["a"].exif
    assert exif["camera"] == "Sony ZV-E10"
    assert exif["iso"] == 640 and exif["shutter"] == "1/250"  # from the file
    # a photo whose file has no EXIF falls back to the snapshot
    assert by_unsplash_id(db)["b"].exif == {}


def test_snapshot_exif_used_when_the_file_has_none(
    seed_file: Path,
    client: TestClient,
    storage: FakeStorage,
    settings: Settings,
    unsplash: FakeUnsplash,
    db: Session,
) -> None:
    seed(seed_file, client, storage, settings, unsplash)
    assert by_unsplash_id(db)["a"].exif == {"camera": "Sony ZV-E10", "focal_length": 38, "iso": 640}


def test_collections_chapters_covers_and_photo_assignment(
    seed_file: Path,
    client: TestClient,
    storage: FakeStorage,
    settings: Settings,
    unsplash: FakeUnsplash,
    db: Session,
) -> None:
    report = seed(seed_file, client, storage, settings, unsplash)

    assert report.collections_created == 1
    db.expire_all()
    collection = db.scalars(select(Collection)).one()
    assert (collection.slug, collection.year, collection.intro) == ("ujjain", "2024", "Intro")
    assert collection.status is Status.PUBLISHED
    photos = by_unsplash_id(db)
    chapters = collection.chapters
    assert [(c.title, c.note) for c in chapters] == [("One", "First"), ("Two", "Second")]
    assert [p.id for p in chapters[0].photos] == [photos["a"].id, photos["b"].id]
    assert [p.id for p in chapters[1].photos] == [photos["c"].id]
    assert collection.cover_photo_ids == [photos["a"].id, photos["c"].id]


def test_seeding_twice_changes_nothing_and_makes_no_requests(
    seed_file: Path,
    client: TestClient,
    storage: FakeStorage,
    settings: Settings,
    unsplash: FakeUnsplash,
    db: Session,
) -> None:
    seed(seed_file, client, storage, settings, unsplash)
    tracked = list(unsplash.tracked)
    objects = dict(storage.objects)

    report = seed(seed_file, client, storage, settings, unsplash)

    assert (report.imported, report.already_present, report.collections_created) == (0, 3, 0)
    assert unsplash.tracked == tracked
    assert storage.objects == objects
    assert len(by_unsplash_id(db)) == 3
    assert len(db.scalars(select(Collection)).all()) == 1


def test_rate_limit_stops_cleanly_and_a_second_run_finishes_the_job(
    seed_file: Path,
    client: TestClient,
    storage: FakeStorage,
    settings: Settings,
    unsplash: FakeUnsplash,
    db: Session,
) -> None:
    unsplash.budget = 1  # one download only

    first = seed(seed_file, client, storage, settings, unsplash)

    assert first.imported == 1
    assert first.remaining == ["a", "b"]  # c came first in the curated order
    assert first.collections_created == 0  # collections wait until every photo is in
    assert db.scalars(select(Collection)).all() == []

    unsplash.budget = None
    second = seed(seed_file, client, storage, settings, unsplash)

    assert (second.imported, second.already_present, second.remaining) == (2, 1, [])
    assert second.collections_created == 1
    ordered = sorted(by_unsplash_id(db).values(), key=lambda p: p.sort_position)
    assert [p.unsplash_id for p in ordered] == ["c", "a", "b"]


def test_a_photo_gone_from_unsplash_is_reported_and_left_out_of_collections(
    seed_file: Path,
    client: TestClient,
    storage: FakeStorage,
    settings: Settings,
    unsplash: FakeUnsplash,
    db: Session,
) -> None:
    original = unsplash.download_original

    def download(photo: Any) -> bytes:
        if photo.id == "b":
            raise httpx.HTTPStatusError(
                "gone", request=httpx.Request("GET", "u"), response=httpx.Response(404)
            )
        return original(photo)

    unsplash.download_original = download  # type: ignore[method-assign]

    report = seed(seed_file, client, storage, settings, unsplash)

    assert report.missing_from_unsplash == ["b"]
    assert report.collections_created == 1
    assert set(by_unsplash_id(db)) == {"a", "c"}
    chapters = db.scalars(select(Collection)).one().chapters
    assert [len(c.photos) for c in chapters] == [1, 1]


def test_a_transient_failure_leaves_the_photo_for_the_next_run(
    seed_file: Path,
    client: TestClient,
    storage: FakeStorage,
    settings: Settings,
    unsplash: FakeUnsplash,
    db: Session,
) -> None:
    original = unsplash.download_original
    calls = {"n": 0}

    def flaky(photo: Any) -> bytes:
        if photo.id == "a":
            calls["n"] += 1
            if calls["n"] == 1:
                raise httpx.ConnectError("network blip")
        return original(photo)

    unsplash.download_original = flaky  # type: ignore[method-assign]

    first = seed(seed_file, client, storage, settings, unsplash)
    assert first.remaining == ["a"] and first.collections_created == 0

    second = seed(seed_file, client, storage, settings, unsplash)
    assert second.remaining == [] and second.collections_created == 1


def test_photos_already_synced_from_unsplash_are_reused_not_duplicated(
    seed_file: Path,
    client: TestClient,
    storage: FakeStorage,
    settings: Settings,
    unsplash: FakeUnsplash,
    db: Session,
) -> None:
    from app.services.photos import PhotoService
    from app.uow import SqlAlchemyUnitOfWork
    from tests.support.images import make_jpeg

    synced = PhotoService(
        lambda: SqlAlchemyUnitOfWork(client.app.state.session_factory),  # type: ignore[attr-defined]
        storage,
        settings,
    ).ingest_jpeg(make_jpeg((60, 40)), title="Synced title", unsplash_id="a")
    report = seed(seed_file, client, storage, settings, unsplash)

    assert report.already_present == 1 and report.imported == 2
    photos = by_unsplash_id(db)
    assert photos["a"].id == synced.id
    assert photos["a"].title == "Synced title"  # an existing photo is not overwritten
    assert photos["a"].chapter_id is not None  # but it joins its collection


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

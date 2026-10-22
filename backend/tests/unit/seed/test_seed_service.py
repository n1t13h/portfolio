"""Seeding from the exported snapshot, against the in-memory unit of work, fake storage and a
fake Unsplash: no database and no network."""

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.core.config import Settings
from app.integrations.storage import Bucket
from app.models import Photo, Status
from app.services.photos import PhotoService
from app.services.seed import seed_from_json
from tests.fakes import FakeStorage, FakeUnitOfWork, FakeUnsplash
from tests.support.images import make_jpeg, rich_exif
from tests.support.seed_data import SEED


@pytest.fixture
def seed_file(tmp_path: Path) -> Path:
    path = tmp_path / "curation.json"
    path.write_text(json.dumps(SEED))
    return path


@pytest.fixture
def run(
    seed_file: Path,
    fake_uow: FakeUnitOfWork,
    storage: FakeStorage,
    settings: Settings,
    unsplash: FakeUnsplash,
) -> Any:
    def go() -> Any:
        return seed_from_json(seed_file, lambda: fake_uow, storage, settings, unsplash)

    return go


def by_unsplash_id(uow: FakeUnitOfWork) -> dict[str, Photo]:
    return {p.unsplash_id: p for p in uow.store.photos.values() if p.unsplash_id}


def test_it_creates_published_photos_with_snapshot_titles_in_the_curated_order(
    run: Any, fake_uow: FakeUnitOfWork, storage: FakeStorage
) -> None:
    report = run()

    assert (report.imported, report.remaining, report.missing_from_unsplash) == (3, [], [])
    photos = by_unsplash_id(fake_uow)
    assert sorted(p.title for p in photos.values()) == ["Photo A", "Photo B", "Photo C"]
    assert photos["a"].place == "Ram Ghat, Ujjain"
    assert photos["a"].unsplash_url == "https://unsplash.com/photos/a"
    assert all(p.status is Status.PUBLISHED for p in photos.values())
    assert all(p.allow_download is False for p in photos.values())
    ordered = sorted(photos.values(), key=lambda p: p.sort_position)
    assert [p.unsplash_id for p in ordered] == ["c", "a", "b"]
    assert storage.exists(Bucket.PRIVATE, f"originals/{photos['a'].id}.jpg")


def test_each_photo_is_created_in_its_final_state_in_one_transaction(
    run: Any, fake_uow: FakeUnitOfWork
) -> None:
    """No window where a photo exists as a draft awaiting a second commit to publish it."""
    run()
    assert all(p.status is Status.PUBLISHED for p in fake_uow.store.photos.values())
    assert fake_uow.commits >= 3  # one per photo (plus ordering and collections)


def test_excluded_photos_become_drafts(
    seed_file: Path,
    fake_uow: FakeUnitOfWork,
    storage: FakeStorage,
    settings: Settings,
    unsplash: FakeUnsplash,
) -> None:
    data = json.loads(seed_file.read_text())
    data["excluded"] = ["b"]
    seed_file.write_text(json.dumps(data))

    seed_from_json(seed_file, lambda: fake_uow, storage, settings, unsplash)

    photos = by_unsplash_id(fake_uow)
    assert (photos["a"].status, photos["b"].status) == (Status.PUBLISHED, Status.DRAFT)


def test_the_files_own_exif_wins_and_the_snapshot_fills_the_gaps(
    run: Any, fake_uow: FakeUnitOfWork, unsplash: FakeUnsplash
) -> None:
    unsplash.files["a"] = make_jpeg((300, 200), exif=rich_exif())  # Sony ZV-E10, iso 640, 1/250
    run()
    exif = by_unsplash_id(fake_uow)["a"].exif
    assert exif["camera"] == "Sony ZV-E10" and exif["iso"] == 640 and exif["shutter"] == "1/250"
    assert exif["focal_length"] == 38.0  # the file's value wins over the snapshot's 38 (same here)


def test_the_snapshot_exif_is_used_when_the_file_has_none(
    run: Any, fake_uow: FakeUnitOfWork
) -> None:
    run()
    photos = by_unsplash_id(fake_uow)
    assert photos["a"].exif == {"camera": "Sony ZV-E10", "focal_length": 38, "iso": 640}
    assert photos["b"].exif == {}  # nothing in the snapshot either


def test_collections_chapters_covers_and_photo_assignment(
    run: Any, fake_uow: FakeUnitOfWork
) -> None:
    report = run()

    assert report.collections_created == 1
    [collection] = fake_uow.store.collections.values()
    assert (collection.slug, collection.year, collection.intro) == ("ujjain", "2024", "Intro")
    assert collection.status is Status.PUBLISHED
    photos = by_unsplash_id(fake_uow)
    chapters = fake_uow.collections.list_chapters(collection.id)
    assert [(c.title, c.note) for c in chapters] == [("One", "First"), ("Two", "Second")]
    ids = fake_uow.photos.ids_by_chapter([c.id for c in chapters])
    assert ids[chapters[0].id] == [photos["a"].id, photos["b"].id]
    assert ids[chapters[1].id] == [photos["c"].id]
    assert collection.cover_photo_ids == [photos["a"].id, photos["c"].id]


def test_seeding_twice_changes_nothing_and_makes_no_requests(
    run: Any, fake_uow: FakeUnitOfWork, storage: FakeStorage, unsplash: FakeUnsplash
) -> None:
    run()
    tracked, objects = list(unsplash.tracked), dict(storage.objects)

    report = run()

    assert (report.imported, report.already_present, report.collections_created) == (0, 3, 0)
    assert unsplash.tracked == tracked and storage.objects == objects
    assert len(by_unsplash_id(fake_uow)) == 3 and len(fake_uow.store.collections) == 1


def test_a_rate_limit_stops_cleanly_and_a_second_run_finishes_the_job(
    run: Any, fake_uow: FakeUnitOfWork, unsplash: FakeUnsplash
) -> None:
    unsplash.budget = 1  # one download only

    first = run()

    assert first.imported == 1
    assert first.remaining == ["a", "b"]  # c came first in the curated order
    assert first.collections_created == 0  # collections wait until every photo is in
    assert fake_uow.store.collections == {}

    unsplash.budget = None
    second = run()

    assert (second.imported, second.already_present, second.remaining) == (2, 1, [])
    assert second.collections_created == 1
    ordered = sorted(by_unsplash_id(fake_uow).values(), key=lambda p: p.sort_position)
    assert [p.unsplash_id for p in ordered] == ["c", "a", "b"]


def test_a_photo_gone_from_unsplash_is_reported_and_left_out_of_collections(
    run: Any, fake_uow: FakeUnitOfWork, unsplash: FakeUnsplash
) -> None:
    original = unsplash.download_original

    def download(photo: Any) -> bytes:
        if photo.id == "b":
            raise httpx.HTTPStatusError(
                "gone", request=httpx.Request("GET", "u"), response=httpx.Response(404)
            )
        return original(photo)

    unsplash.download_original = download  # type: ignore[method-assign]

    report = run()

    assert report.missing_from_unsplash == ["b"]
    assert report.collections_created == 1
    assert set(by_unsplash_id(fake_uow)) == {"a", "c"}
    [collection] = fake_uow.store.collections.values()
    chapters = fake_uow.collections.list_chapters(collection.id)
    ids = fake_uow.photos.ids_by_chapter([c.id for c in chapters])
    assert [len(ids[c.id]) for c in chapters] == [1, 1]


def test_a_transient_failure_leaves_the_photo_for_the_next_run(
    run: Any, unsplash: FakeUnsplash
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

    first = run()
    assert first.remaining == ["a"] and first.collections_created == 0

    second = run()
    assert second.remaining == [] and second.collections_created == 1


def test_a_non_404_http_error_is_retried_later_not_treated_as_gone(
    run: Any, unsplash: FakeUnsplash
) -> None:
    original = unsplash.download_original

    def server_error(photo: Any) -> bytes:
        if photo.id == "b":
            raise httpx.HTTPStatusError(
                "oops", request=httpx.Request("GET", "u"), response=httpx.Response(500)
            )
        return original(photo)

    unsplash.download_original = server_error  # type: ignore[method-assign]

    report = run()

    assert report.remaining == ["b"] and report.missing_from_unsplash == []


def test_photos_already_synced_from_unsplash_are_reused_not_duplicated(
    run: Any, fake_uow: FakeUnitOfWork, storage: FakeStorage, settings: Settings
) -> None:
    synced = PhotoService(lambda: fake_uow, storage, settings).ingest_jpeg(
        make_jpeg((60, 40)), title="Synced title", unsplash_id="a"
    )

    report = run()

    assert report.already_present == 1 and report.imported == 2
    photo = by_unsplash_id(fake_uow)["a"]
    assert photo.id == synced.id
    assert photo.title == "Synced title"  # an existing photo is not overwritten
    assert photo.chapter_id is not None  # but it joins its collection


def test_a_collection_that_already_exists_is_skipped_not_duplicated(
    run: Any, fake_uow: FakeUnitOfWork
) -> None:
    run()
    [first] = fake_uow.store.collections.values()
    first.title = "Renamed by the admin"

    report = run()

    assert report.collections_created == 0
    [after] = fake_uow.store.collections.values()
    assert after.title == "Renamed by the admin"


def test_a_failure_while_building_a_collection_leaves_none_half_published_and_the_next_run_repairs_it(
    seed_file: Path,
    fake_uow: FakeUnitOfWork,
    storage: FakeStorage,
    settings: Settings,
    unsplash: FakeUnsplash,
) -> None:
    full = json.loads(seed_file.read_text())
    seed_file.write_text(json.dumps({**full, "collections": []}))
    seed_from_json(seed_file, lambda: fake_uow, storage, settings, unsplash)  # photos only
    seed_file.write_text(json.dumps(full))

    # the second chapter cannot be saved: the collection must not survive half-built
    real_add_chapter = fake_uow.collections.add_chapter
    attempts = {"n": 0}

    def second_chapter_fails(chapter: Any) -> None:
        attempts["n"] += 1
        if attempts["n"] == 2:
            raise RuntimeError("constraint failed")
        real_add_chapter(chapter)

    fake_uow.collections.add_chapter = second_chapter_fails  # type: ignore[method-assign]
    with pytest.raises(RuntimeError):
        seed_from_json(seed_file, lambda: fake_uow, storage, settings, unsplash)
    assert fake_uow.store.collections == {} and fake_uow.store.chapters == {}

    fake_uow.collections.add_chapter = real_add_chapter  # type: ignore[method-assign]
    report = seed_from_json(seed_file, lambda: fake_uow, storage, settings, unsplash)

    assert report.collections_created == 1
    [collection] = fake_uow.store.collections.values()
    assert collection.status is Status.PUBLISHED
    assert len(fake_uow.store.chapters) == 2 and collection.cover_photo_ids

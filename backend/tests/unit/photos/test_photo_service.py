"""PhotoService against the in-memory unit of work and fake storage: no database, no network."""

import re
from typing import Any

import pytest

from app.core.config import Settings
from app.core.errors import Conflict, InvalidRequest, NotFound
from app.integrations.storage import Bucket
from app.models import Photo, Status
from app.services.audit import AuditTrail
from app.services.images import InvalidImage
from app.services.photos import PhotoService
from tests.fakes import FakeClock, FakeStorage, FakeUnitOfWork
from tests.support.images import make_jpeg, rich_exif


@pytest.fixture
def service(fake_uow: FakeUnitOfWork, storage: FakeStorage, settings: Settings) -> PhotoService:
    return PhotoService(lambda: fake_uow, storage, settings)


def stored(fake_uow: FakeUnitOfWork) -> dict[str, Photo]:
    return dict(fake_uow.store.photos)


def uploaded(service: PhotoService, storage: FakeStorage, data: bytes) -> str:
    """The browser's side: get a ticket, PUT the bytes. Returns the photo id."""
    ticket = service.request_upload()
    storage.put_bytes(Bucket.PRIVATE, ticket.key, data, "image/jpeg")
    return ticket.photo_id


# -- upload tickets and confirming --------------------------------------------------------


def test_an_upload_ticket_points_at_a_private_original_with_a_fresh_id(
    service: PhotoService,
) -> None:
    ticket = service.request_upload()
    assert re.fullmatch(r"[0-9a-f]{32}", ticket.photo_id)
    assert ticket.key == f"originals/{ticket.photo_id}.jpg"
    assert "/private/" in ticket.put_url and ticket.put_url.endswith("expires=600")
    assert service.request_upload().photo_id != ticket.photo_id


def test_requesting_a_ticket_creates_no_photo(
    service: PhotoService, fake_uow: FakeUnitOfWork
) -> None:
    service.request_upload()
    assert stored(fake_uow) == {}


def test_confirming_creates_a_draft_with_variants_and_keeps_the_original_private(
    service: PhotoService, storage: FakeStorage, fake_uow: FakeUnitOfWork
) -> None:
    photo_id = uploaded(service, storage, make_jpeg((1200, 800)))

    photo = service.confirm_upload(photo_id)

    assert (photo.id, photo.status, photo.allow_download) == (photo_id, Status.DRAFT, False)
    assert photo.aspect_ratio == 1.5
    assert set(photo.variants) == {"800", "1600", "2400"}
    assert photo.variants["800"] == f"https://cdn.test/photos/{photo_id}/800.webp"
    public = {k for (b, k) in storage.objects if b is Bucket.PUBLIC}
    private = {k for (b, k) in storage.objects if b is Bucket.PRIVATE}
    assert public == {f"photos/{photo_id}/{e}.webp" for e in (800, 1600, 2400)}
    assert private == {f"originals/{photo_id}.jpg", f"downloads/{photo_id}.jpg"}
    assert fake_uow.commits == 1


def test_confirmed_photos_are_appended_to_the_global_order(
    service: PhotoService, storage: FakeStorage
) -> None:
    first = service.confirm_upload(uploaded(service, storage, make_jpeg((300, 200))))
    second = service.confirm_upload(uploaded(service, storage, make_jpeg((300, 200))))
    assert (first.sort_position, second.sort_position) == (0, 1)


def test_confirming_twice_is_a_conflict_and_changes_nothing(
    service: PhotoService, storage: FakeStorage, fake_uow: FakeUnitOfWork
) -> None:
    photo_id = uploaded(service, storage, make_jpeg((300, 200)))
    service.confirm_upload(photo_id)
    with pytest.raises(Conflict):
        service.confirm_upload(photo_id)
    assert len(stored(fake_uow)) == 1


def test_confirming_without_an_uploaded_file_is_not_found(service: PhotoService) -> None:
    with pytest.raises(NotFound):
        service.confirm_upload(service.request_upload().photo_id)


def test_a_non_jpeg_is_rejected_and_its_upload_deleted(
    service: PhotoService, storage: FakeStorage, fake_uow: FakeUnitOfWork
) -> None:
    photo_id = uploaded(service, storage, make_jpeg((100, 100), fmt="PNG"))
    with pytest.raises(InvalidImage):
        service.confirm_upload(photo_id)
    assert storage.objects == {} and stored(fake_uow) == {}


def test_an_oversized_file_is_rejected_without_reading_it_and_deleted(
    service: PhotoService, storage: FakeStorage, settings: Settings
) -> None:
    settings.max_upload_bytes = 500
    photo_id = uploaded(service, storage, make_jpeg((400, 400)))
    reads: list[str] = []
    original_get = storage.get_bytes

    def spying_get(bucket: Bucket, key: str) -> bytes:
        reads.append(key)
        return original_get(bucket, key)

    storage.get_bytes = spying_get  # type: ignore[method-assign]

    with pytest.raises(InvalidImage, match="too large"):
        service.confirm_upload(photo_id)

    assert reads == [] and storage.objects == {}


def test_an_image_over_the_pixel_limit_is_rejected(
    service: PhotoService, storage: FakeStorage, settings: Settings
) -> None:
    settings.max_image_pixels = 10_000
    photo_id = uploaded(service, storage, make_jpeg((200, 200)))
    with pytest.raises(InvalidImage):
        service.confirm_upload(photo_id)
    assert storage.objects == {}


# -- ingesting ----------------------------------------------------------------------------


def test_ingest_stores_the_original_unless_told_it_is_already_there(
    service: PhotoService, storage: FakeStorage
) -> None:
    photo = service.ingest_jpeg(make_jpeg((300, 200)))
    assert storage.exists(Bucket.PRIVATE, f"originals/{photo.id}.jpg")

    other = service.ingest_jpeg(make_jpeg((300, 200)), store_original=False)
    assert not storage.exists(Bucket.PRIVATE, f"originals/{other.id}.jpg")


def test_ingest_records_where_a_photo_came_from(service: PhotoService) -> None:
    photo = service.ingest_jpeg(
        make_jpeg((300, 200)),
        title="Ghat",
        place="Ujjain",
        unsplash_id="abc",
        unsplash_url="https://unsplash.com/photos/abc",
    )
    assert (photo.title, photo.place, photo.unsplash_id) == ("Ghat", "Ujjain", "abc")


def test_ingest_can_create_a_photo_directly_in_its_final_status(service: PhotoService) -> None:
    photo = service.ingest_jpeg(make_jpeg((300, 200)), status=Status.PUBLISHED)
    assert photo.status is Status.PUBLISHED


def test_file_exif_wins_over_the_fallback_which_only_fills_gaps(service: PhotoService) -> None:
    data = make_jpeg((300, 200), exif=rich_exif())  # camera Sony ZV-E10, iso 640, shutter 1/250
    photo = service.ingest_jpeg(data, exif_fallback={"camera": "Other", "iso": 1, "lens": "50mm"})
    assert photo.exif["camera"] == "Sony ZV-E10" and photo.exif["iso"] == 640
    assert photo.exif["lens"] == "50mm"


def test_a_failed_save_removes_the_files_it_wrote_and_stores_nothing(
    service: PhotoService, storage: FakeStorage, fake_uow: FakeUnitOfWork
) -> None:
    fake_uow.fail_next_commit(RuntimeError("database is down"))
    with pytest.raises(RuntimeError, match="database is down"):
        service.ingest_jpeg(make_jpeg((300, 200)))
    assert storage.objects == {} and stored(fake_uow) == {}


def test_a_failed_save_keeps_an_original_it_did_not_write(
    service: PhotoService, storage: FakeStorage, fake_uow: FakeUnitOfWork
) -> None:
    photo_id = uploaded(service, storage, make_jpeg((300, 200)))
    fake_uow.fail_next_commit(RuntimeError("database is down"))
    with pytest.raises(RuntimeError):
        service.confirm_upload(photo_id)
    # the browser's upload stays, so confirming can simply be retried
    assert storage.exists(Bucket.PRIVATE, f"originals/{photo_id}.jpg")
    assert service.confirm_upload(photo_id).id == photo_id


def test_ingest_rejects_files_over_the_upload_limit_before_writing_anything(
    service: PhotoService, storage: FakeStorage, settings: Settings
) -> None:
    settings.max_upload_bytes = 500
    with pytest.raises(InvalidImage, match="too large"):
        service.ingest_jpeg(make_jpeg((400, 400)))
    assert storage.objects == {}


# -- reading and editing ------------------------------------------------------------------


def three(service: PhotoService, storage: FakeStorage) -> list[str]:
    return [
        service.confirm_upload(uploaded(service, storage, make_jpeg((300, 200)))).id
        for _ in range(3)
    ]


def test_list_all_follows_the_global_order(service: PhotoService, storage: FakeStorage) -> None:
    ids = three(service, storage)
    assert [p.id for p in service.list_all()] == ids


def test_get_and_every_edit_of_an_unknown_photo_is_not_found(service: PhotoService) -> None:
    for call in (
        lambda: service.get("nope"),
        lambda: service.update("nope", {"title": "x"}),
        lambda: service.set_status("nope", Status.PUBLISHED),
        lambda: service.set_allow_download("nope", True),
        lambda: service.delete("nope"),
    ):
        with pytest.raises(NotFound):
            call()


def test_update_changes_title_and_place(service: PhotoService, storage: FakeStorage) -> None:
    [pid, *_] = three(service, storage)
    updated = service.update(pid, {"title": "Dusk", "place": "Ghat"})
    assert (updated.title, updated.place) == ("Dusk", "Ghat")
    assert service.get(pid).title == "Dusk"


def test_a_place_can_be_cleared_but_a_title_cannot(
    service: PhotoService, storage: FakeStorage
) -> None:
    [pid, *_] = three(service, storage)
    service.update(pid, {"place": "Ghat"})
    assert service.update(pid, {"place": None}).place is None
    with pytest.raises(InvalidRequest, match="title"):
        service.update(pid, {"title": None})


def test_only_title_and_place_are_editable(service: PhotoService, storage: FakeStorage) -> None:
    [pid, *_] = three(service, storage)
    with pytest.raises(InvalidRequest):
        service.update(pid, {"status": "published"})


def test_publishing_and_unpublishing(service: PhotoService, storage: FakeStorage) -> None:
    [pid, *_] = three(service, storage)
    assert service.set_status(pid, Status.PUBLISHED).status is Status.PUBLISHED
    assert service.set_status(pid, Status.DRAFT).status is Status.DRAFT


def test_downloads_can_be_allowed_and_withdrawn(
    service: PhotoService, storage: FakeStorage
) -> None:
    [pid, *_] = three(service, storage)
    assert service.set_allow_download(pid, True).allow_download is True
    assert service.set_allow_download(pid, False).allow_download is False


# -- deleting -----------------------------------------------------------------------------


def test_deleting_removes_the_row_and_every_file(
    service: PhotoService, storage: FakeStorage, fake_uow: FakeUnitOfWork
) -> None:
    [pid, *_] = three(service, storage)
    service.delete(pid)
    assert pid not in stored(fake_uow)
    assert not any(pid in key for (_, key) in storage.objects)


def test_a_storage_failure_while_deleting_does_not_undo_the_delete(
    service: PhotoService, storage: FakeStorage, fake_uow: FakeUnitOfWork
) -> None:
    [pid, *_] = three(service, storage)

    def boom(*args: Any) -> None:
        raise RuntimeError("r2 unreachable")

    storage.delete = boom  # type: ignore[method-assign, assignment]
    service.delete(pid)  # no exception: a leftover file is harmless, a dangling row is not
    assert pid not in stored(fake_uow)


def test_deleting_an_unsplash_photo_remembers_it_so_sync_will_not_bring_it_back(
    service: PhotoService, fake_uow: FakeUnitOfWork
) -> None:
    photo = service.ingest_jpeg(make_jpeg((300, 200)), unsplash_id="u1")
    with fake_uow as uow:
        state = uow.sync_state.get_or_create()
        state.pending = {"u1": 2, "other": 0}
        uow.commit()

    service.delete(photo.id)

    final = fake_uow.store.sync_state
    assert final is not None
    assert final.skipped == {"u1": "deleted"}
    assert final.pending == {"other": 0}


def test_deleting_a_manual_upload_leaves_the_sync_state_alone(
    service: PhotoService, storage: FakeStorage, fake_uow: FakeUnitOfWork
) -> None:
    [pid, *_] = three(service, storage)
    service.delete(pid)
    assert fake_uow.store.sync_state is None


# -- ordering -----------------------------------------------------------------------------


def test_reordering_applies_the_given_order(service: PhotoService, storage: FakeStorage) -> None:
    a, b, c = three(service, storage)
    service.reorder([c, a, b])
    assert [p.id for p in service.list_all()] == [c, a, b]


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "unknown"])
def test_a_bad_id_list_is_rejected_and_nothing_moves(
    service: PhotoService, storage: FakeStorage, mutation: str
) -> None:
    a, b, c = three(service, storage)
    bad = {"missing": [c, b], "duplicate": [c, c, a], "unknown": [c, b, "nope"]}[mutation]
    with pytest.raises(InvalidRequest):
        service.reorder(bad)
    assert [p.id for p in service.list_all()] == [a, b, c]


# -- transactions -------------------------------------------------------------------------


def test_every_write_commits_exactly_once(
    service: PhotoService, storage: FakeStorage, fake_uow: FakeUnitOfWork
) -> None:
    [pid, *_] = three(service, storage)
    before = fake_uow.commits
    service.update(pid, {"title": "x"})
    service.set_status(pid, Status.PUBLISHED)
    service.set_allow_download(pid, True)
    service.delete(pid)
    assert fake_uow.commits - before == 4


def test_reads_never_commit(
    service: PhotoService, storage: FakeStorage, fake_uow: FakeUnitOfWork
) -> None:
    [pid, *_] = three(service, storage)
    before = fake_uow.commits
    service.get(pid)
    service.list_all()
    assert fake_uow.commits == before


# -- covers -------------------------------------------------------------------------------


def collection_with_cover(uow: FakeUnitOfWork, photo_ids: list[str], covers: list[str]) -> None:
    from tests.support.builders import make_chapter, make_collection

    with uow as work:
        work.collections.add(make_collection("c1", cover_photo_ids=covers))
        work.collections.add_chapter(make_chapter("ch1", "c1"))
        for position, photo_id in enumerate(photo_ids):
            photo = work.photos.get(photo_id)
            assert photo is not None
            photo.chapter_id, photo.position_in_chapter = "ch1", position
        work.commit()


def test_deleting_a_cover_photo_removes_it_from_the_collections_covers(
    service: PhotoService, storage: FakeStorage, fake_uow: FakeUnitOfWork
) -> None:
    a, b, _ = three(service, storage)
    collection_with_cover(fake_uow, [a, b], covers=[a, b])

    service.delete(a)

    assert fake_uow.store.collections["c1"].cover_photo_ids == [b]


def test_deleting_a_photo_that_is_not_a_cover_leaves_the_covers_alone(
    service: PhotoService, storage: FakeStorage, fake_uow: FakeUnitOfWork
) -> None:
    a, b, c = three(service, storage)
    collection_with_cover(fake_uow, [a, b], covers=[a])

    service.delete(b)
    service.delete(c)  # in no collection at all

    assert fake_uow.store.collections["c1"].cover_photo_ids == [a]


# -- audit: recorded in the same transaction as the change --------------------------------


@pytest.fixture
def audited(
    fake_uow: FakeUnitOfWork, storage: FakeStorage, settings: Settings, clock: FakeClock
) -> PhotoService:
    return PhotoService(lambda: fake_uow, storage, settings, AuditTrail(clock, "9.9.9.9"))


def entries(uow: FakeUnitOfWork) -> list[tuple[str, str, str]]:
    return [(e.action, e.target, e.ip) for e in uow.store.audit]


def test_manual_uploads_and_every_admin_edit_are_audited_with_the_ip(
    audited: PhotoService, storage: FakeStorage, fake_uow: FakeUnitOfWork
) -> None:
    pid = audited.confirm_upload(uploaded(audited, storage, make_jpeg((300, 200)))).id
    audited.update(pid, {"title": "x"})
    audited.set_status(pid, Status.PUBLISHED)
    audited.set_status(pid, Status.DRAFT)
    audited.set_allow_download(pid, True)
    audited.reorder([pid])
    audited.delete(pid)

    assert entries(fake_uow) == [
        ("photo.upload", pid, "9.9.9.9"),
        ("photo.update", pid, "9.9.9.9"),
        ("photo.publish", pid, "9.9.9.9"),
        ("photo.unpublish", pid, "9.9.9.9"),
        ("photo.allow_download", f"{pid}=True", "9.9.9.9"),
        ("photo.reorder", "", "9.9.9.9"),
        ("photo.delete", pid, "9.9.9.9"),
    ]


def test_an_import_by_the_sync_or_seed_is_not_an_admin_action_and_is_not_audited(
    audited: PhotoService, fake_uow: FakeUnitOfWork
) -> None:
    audited.ingest_jpeg(make_jpeg((300, 200)), unsplash_id="u1")
    assert fake_uow.store.audit == []


def test_a_change_and_its_audit_entry_are_saved_together_or_not_at_all(
    audited: PhotoService, storage: FakeStorage, fake_uow: FakeUnitOfWork
) -> None:
    pid = audited.confirm_upload(uploaded(audited, storage, make_jpeg((300, 200)))).id
    fake_uow.store.audit.clear()
    fake_uow.fail_next_commit(RuntimeError("database is down"))

    with pytest.raises(RuntimeError):
        audited.set_status(pid, Status.PUBLISHED)

    assert fake_uow.store.audit == []
    assert audited.get(pid).status is Status.DRAFT  # neither the change nor the record


def test_without_a_trail_nothing_is_audited(
    service: PhotoService, storage: FakeStorage, fake_uow: FakeUnitOfWork
) -> None:
    [pid, *_] = three(service, storage)
    service.update(pid, {"title": "x"})
    assert fake_uow.store.audit == []

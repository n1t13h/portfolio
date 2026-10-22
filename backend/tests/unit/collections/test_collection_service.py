"""CollectionService against the in-memory unit of work: no database."""

import pytest

from app.core.errors import Conflict, InvalidRequest, NotFound
from app.models import Status
from app.schemas.collections import (
    ChapterDraft,
    ChapterPatch,
    CollectionOut,
    CollectionPatch,
)
from app.services.audit import AuditTrail
from app.services.collections import CollectionService
from tests.fakes import FakeClock, FakeUnitOfWork
from tests.support.builders import make_photo


@pytest.fixture
def service(fake_uow: FakeUnitOfWork) -> CollectionService:
    return CollectionService(lambda: fake_uow)


def add_photos(uow: FakeUnitOfWork, *ids: str) -> None:
    with uow as work:
        for i, photo_id in enumerate(ids):
            work.photos.add(make_photo(photo_id, sort_position=i))
        work.commit()


def photo_chapter(uow: FakeUnitOfWork, photo_id: str) -> str | None:
    photo = uow.store.photos[photo_id]
    return photo.chapter_id


def collection(service: CollectionService, slug: str = "goa", **fields: str) -> CollectionOut:
    return service.create_collection(slug, fields.pop("title", slug.title()), **fields)


# -- collections --------------------------------------------------------------------------


def test_a_new_collection_is_an_empty_draft_appended_to_the_order(
    service: CollectionService,
) -> None:
    first = collection(service, "one", place="India", year="2024", intro="Hi")
    second = collection(service, "two")
    assert (first.status, first.chapters, first.cover_photo_ids) == (Status.DRAFT, [], [])
    assert (first.place, first.year, first.intro) == ("India", "2024", "Hi")
    assert (first.sort_position, second.sort_position) == (0, 1)
    assert [c.slug for c in service.list_collections()] == ["one", "two"]


@pytest.mark.parametrize("slug", ["Has Caps", "has space", "-lead", "trail-", "a/b", "", "a--b"])
def test_slugs_must_be_lowercase_words_joined_by_single_hyphens(
    service: CollectionService, slug: str
) -> None:
    with pytest.raises(InvalidRequest, match="slug"):
        service.create_collection(slug, "T")


def test_a_slug_can_only_be_used_once(service: CollectionService) -> None:
    collection(service, "goa")
    with pytest.raises(Conflict):
        collection(service, "goa")


def test_getting_an_unknown_collection_is_not_found(service: CollectionService) -> None:
    with pytest.raises(NotFound, match="collection"):
        service.get_collection("nope")


def test_updating_edits_the_given_fields_only(service: CollectionService) -> None:
    created = collection(service, "goa", place="India")
    updated = service.update_collection(created.id, CollectionPatch(title="Goa 2024", intro="Rain"))
    assert (updated.title, updated.intro, updated.place, updated.slug) == (
        "Goa 2024",
        "Rain",
        "India",
        "goa",
    )


def test_a_collection_may_keep_its_own_slug_but_not_take_another(
    service: CollectionService,
) -> None:
    a, b = collection(service, "a"), collection(service, "b")
    assert service.update_collection(a.id, CollectionPatch(slug="a")).slug == "a"
    with pytest.raises(Conflict):
        service.update_collection(a.id, CollectionPatch(slug="b"))
    assert service.get_collection(b.id).slug == "b"


def test_a_collection_field_cannot_be_nulled(service: CollectionService) -> None:
    created = collection(service)
    with pytest.raises(InvalidRequest):
        service.update_collection(created.id, CollectionPatch(title=None))


def test_publishing_and_unpublishing(service: CollectionService) -> None:
    created = collection(service)
    assert service.set_status(created.id, Status.PUBLISHED).status is Status.PUBLISHED
    assert service.set_status(created.id, Status.DRAFT).status is Status.DRAFT


def test_every_edit_of_an_unknown_collection_is_not_found(service: CollectionService) -> None:
    for call in (
        lambda: service.update_collection("nope", CollectionPatch(title="x")),
        lambda: service.set_status("nope", Status.PUBLISHED),
        lambda: service.delete_collection("nope"),
        lambda: service.set_covers("nope", []),
        lambda: service.create_chapter("nope"),
        lambda: service.reorder_chapters("nope", []),
    ):
        with pytest.raises(NotFound):
            call()


def test_deleting_a_collection_removes_its_chapters_but_keeps_the_photos(
    service: CollectionService, fake_uow: FakeUnitOfWork
) -> None:
    add_photos(fake_uow, "p1")
    created = collection(service)
    chapter = service.create_chapter(created.id)
    service.assign_photos(chapter.id, ["p1"])

    service.delete_collection(created.id)

    assert service.list_collections() == []
    assert fake_uow.store.chapters == {}
    assert "p1" in fake_uow.store.photos and photo_chapter(fake_uow, "p1") is None


def test_collections_reorder_atomically(service: CollectionService) -> None:
    a, b, c = (collection(service, s) for s in "abc")
    service.reorder_collections([c.id, a.id, b.id])
    assert [x.id for x in service.list_collections()] == [c.id, a.id, b.id]


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "unknown"])
def test_a_bad_collection_order_is_rejected_and_nothing_moves(
    service: CollectionService, mutation: str
) -> None:
    a, b, c = (collection(service, s) for s in "abc")
    bad = {"missing": [c.id, b.id], "duplicate": [c.id, c.id, a.id], "unknown": [c.id, b.id, "x"]}[
        mutation
    ]
    with pytest.raises(InvalidRequest):
        service.reorder_collections(bad)
    assert [x.id for x in service.list_collections()] == [a.id, b.id, c.id]


# -- chapters -----------------------------------------------------------------------------


def test_chapters_are_appended_in_order_and_show_up_on_the_collection(
    service: CollectionService,
) -> None:
    created = collection(service)
    first = service.create_chapter(created.id, "Arrival", "Rain")
    second = service.create_chapter(created.id, "Beaches")
    assert (first.position, second.position) == (0, 1)
    assert (first.title, first.note, first.photo_ids) == ("Arrival", "Rain", [])
    assert [c.title for c in service.get_collection(created.id).chapters] == ["Arrival", "Beaches"]


def test_a_chapter_can_be_edited_but_not_nulled(service: CollectionService) -> None:
    chapter = service.create_chapter(collection(service).id, "Arrival")
    assert service.update_chapter(chapter.id, ChapterPatch(note="Monsoon")).note == "Monsoon"
    with pytest.raises(InvalidRequest):
        service.update_chapter(chapter.id, ChapterPatch(title=None))
    with pytest.raises(NotFound, match="chapter"):
        service.update_chapter("nope", ChapterPatch(title="x"))


def test_chapters_reorder_atomically(service: CollectionService) -> None:
    created = collection(service)
    a, b, c = (service.create_chapter(created.id, t) for t in "abc")
    service.reorder_chapters(created.id, [c.id, a.id, b.id])
    assert [x.id for x in service.get_collection(created.id).chapters] == [c.id, a.id, b.id]

    with pytest.raises(InvalidRequest):
        service.reorder_chapters(created.id, [a.id, b.id])
    assert [x.id for x in service.get_collection(created.id).chapters] == [c.id, a.id, b.id]


def test_deleting_a_chapter_frees_its_photos_and_drops_them_from_the_covers(
    service: CollectionService, fake_uow: FakeUnitOfWork
) -> None:
    add_photos(fake_uow, "p1", "p2")
    created = collection(service)
    keep, doomed = (
        service.create_chapter(created.id, "keep"),
        service.create_chapter(created.id, "doomed"),
    )
    service.assign_photos(keep.id, ["p1"])
    service.assign_photos(doomed.id, ["p2"])
    service.set_covers(created.id, ["p1", "p2"])

    service.delete_chapter(doomed.id)

    assert photo_chapter(fake_uow, "p2") is None and photo_chapter(fake_uow, "p1") == keep.id
    assert service.get_collection(created.id).cover_photo_ids == ["p1"]
    with pytest.raises(NotFound):
        service.delete_chapter(doomed.id)


# -- photos in chapters -------------------------------------------------------------------


def test_assigning_appends_in_the_given_order_after_existing_photos(
    service: CollectionService, fake_uow: FakeUnitOfWork
) -> None:
    add_photos(fake_uow, "p1", "p2", "p3")
    chapter = service.create_chapter(collection(service).id)
    service.assign_photos(chapter.id, ["p1"])
    result = service.assign_photos(chapter.id, ["p3", "p2"])
    assert result.photo_ids == ["p1", "p3", "p2"]


def test_a_photo_is_in_one_chapter_at_a_time_so_assigning_moves_it(
    service: CollectionService, fake_uow: FakeUnitOfWork
) -> None:
    add_photos(fake_uow, "p1")
    created = collection(service)
    a, b = service.create_chapter(created.id, "a"), service.create_chapter(created.id, "b")
    service.assign_photos(a.id, ["p1"])
    service.assign_photos(b.id, ["p1"])
    chapters = {c.title: c.photo_ids for c in service.get_collection(created.id).chapters}
    assert chapters == {"a": [], "b": ["p1"]}


def test_moving_a_photo_to_another_collection_drops_it_from_the_old_covers(
    service: CollectionService, fake_uow: FakeUnitOfWork
) -> None:
    add_photos(fake_uow, "p1")
    one, two = collection(service, "one"), collection(service, "two")
    ch1, ch2 = service.create_chapter(one.id), service.create_chapter(two.id)
    service.assign_photos(ch1.id, ["p1"])
    service.set_covers(one.id, ["p1"])

    service.assign_photos(ch2.id, ["p1"])

    assert service.get_collection(one.id).cover_photo_ids == []


def test_assigning_unknown_or_duplicate_photos_is_rejected_and_nothing_is_assigned(
    service: CollectionService, fake_uow: FakeUnitOfWork
) -> None:
    add_photos(fake_uow, "p1")
    chapter = service.create_chapter(collection(service).id)
    with pytest.raises(InvalidRequest, match="unknown"):
        service.assign_photos(chapter.id, ["p1", "ghost"])
    with pytest.raises(InvalidRequest, match="duplicate"):
        service.assign_photos(chapter.id, ["p1", "p1"])
    assert photo_chapter(fake_uow, "p1") is None
    with pytest.raises(NotFound, match="chapter"):
        service.assign_photos("nope", [])


def test_removing_a_photo_frees_it_and_clears_its_cover(
    service: CollectionService, fake_uow: FakeUnitOfWork
) -> None:
    add_photos(fake_uow, "p1")
    created = collection(service)
    chapter = service.create_chapter(created.id)
    service.assign_photos(chapter.id, ["p1"])
    service.set_covers(created.id, ["p1"])

    service.remove_photo(chapter.id, "p1")

    assert photo_chapter(fake_uow, "p1") is None
    assert service.get_collection(created.id).cover_photo_ids == []
    with pytest.raises(NotFound, match="not in this chapter"):
        service.remove_photo(chapter.id, "p1")


def test_photos_in_a_chapter_reorder_atomically(
    service: CollectionService, fake_uow: FakeUnitOfWork
) -> None:
    add_photos(fake_uow, "p1", "p2", "p3")
    chapter = service.create_chapter(collection(service).id)
    service.assign_photos(chapter.id, ["p1", "p2", "p3"])

    service.reorder_photos(chapter.id, ["p3", "p1", "p2"])
    assert fake_uow.photos.ids_by_chapter([chapter.id]) == {chapter.id: ["p3", "p1", "p2"]}

    for bad in (["p1", "p2"], ["p1", "p1", "p2"], ["p1", "p2", "ghost"]):
        with pytest.raises(InvalidRequest):
            service.reorder_photos(chapter.id, bad)
    assert fake_uow.photos.ids_by_chapter([chapter.id]) == {chapter.id: ["p3", "p1", "p2"]}


# -- covers -------------------------------------------------------------------------------


def test_covers_must_be_distinct_photos_that_are_in_the_collection(
    service: CollectionService, fake_uow: FakeUnitOfWork
) -> None:
    add_photos(fake_uow, "inside", "outside")
    created = collection(service)
    service.assign_photos(service.create_chapter(created.id).id, ["inside"])

    with pytest.raises(InvalidRequest, match="in this collection"):
        service.set_covers(created.id, ["outside"])
    with pytest.raises(InvalidRequest, match="duplicate"):
        service.set_covers(created.id, ["inside", "inside"])
    assert service.set_covers(created.id, ["inside"]).cover_photo_ids == ["inside"]
    assert service.set_covers(created.id, []).cover_photo_ids == []


# -- the read model and transactions ------------------------------------------------------


def test_the_collection_list_includes_each_chapters_photos_in_order(
    service: CollectionService, fake_uow: FakeUnitOfWork
) -> None:
    add_photos(fake_uow, "p1", "p2", "p3")
    one, two = collection(service, "one"), collection(service, "two")
    ch = service.create_chapter(one.id, "A")
    service.assign_photos(ch.id, ["p2", "p1"])
    service.assign_photos(service.create_chapter(two.id, "B").id, ["p3"])

    listed = {
        c.slug: [(x.title, x.photo_ids) for x in c.chapters] for c in service.list_collections()
    }

    assert listed == {"one": [("A", ["p2", "p1"])], "two": [("B", ["p3"])]}


def test_every_write_commits_once_and_reads_never_commit(
    service: CollectionService, fake_uow: FakeUnitOfWork
) -> None:
    created = collection(service)
    before = fake_uow.commits
    service.update_collection(created.id, CollectionPatch(title="x"))
    service.set_status(created.id, Status.PUBLISHED)
    chapter = service.create_chapter(created.id)
    service.update_chapter(chapter.id, ChapterPatch(title="y"))
    assert fake_uow.commits - before == 4

    before = fake_uow.commits
    service.list_collections()
    service.get_collection(created.id)
    assert fake_uow.commits == before


def test_a_failed_write_changes_nothing(
    service: CollectionService, fake_uow: FakeUnitOfWork
) -> None:
    created = collection(service)
    fake_uow.fail_next_commit(RuntimeError("database is down"))
    with pytest.raises(RuntimeError):
        service.update_collection(created.id, CollectionPatch(title="changed"))
    assert service.get_collection(created.id).title == created.title


# -- building a whole collection in one transaction ---------------------------------------


def draft(title: str, *photo_ids: str, note: str = "") -> ChapterDraft:
    return ChapterDraft(title=title, note=note, photo_ids=list(photo_ids))


def test_a_complete_collection_is_created_published_with_chapters_photos_and_covers(
    service: CollectionService, fake_uow: FakeUnitOfWork
) -> None:
    add_photos(fake_uow, "p1", "p2", "p3")

    created = service.create_complete(
        "goa",
        "Goa",
        chapters=[draft("Arrival", "p2", "p1", note="Rain"), draft("Beaches", "p3")],
        cover_photo_ids=["p3", "p1"],
        status=Status.PUBLISHED,
        place="India",
        year="2024",
        intro="Monsoon",
    )

    assert (created.slug, created.status, created.place, created.year) == (
        "goa",
        Status.PUBLISHED,
        "India",
        "2024",
    )
    assert [(c.title, c.note, c.photo_ids) for c in created.chapters] == [
        ("Arrival", "Rain", ["p2", "p1"]),
        ("Beaches", "", ["p3"]),
    ]
    assert created.cover_photo_ids == ["p3", "p1"]
    assert fake_uow.commits >= 1


def test_the_whole_collection_is_one_commit(
    service: CollectionService, fake_uow: FakeUnitOfWork
) -> None:
    add_photos(fake_uow, "p1", "p2")
    before = fake_uow.commits
    service.create_complete(
        "goa",
        "Goa",
        chapters=[draft("A", "p1"), draft("B", "p2")],
        cover_photo_ids=["p1"],
        status=Status.PUBLISHED,
    )
    assert fake_uow.commits - before == 1


def test_a_collection_is_never_left_half_built_when_something_is_wrong(
    service: CollectionService, fake_uow: FakeUnitOfWork
) -> None:
    add_photos(fake_uow, "p1")
    bad_calls = [
        dict(chapters=[draft("A", "p1", "ghost")], cover_photo_ids=[]),  # unknown photo
        dict(chapters=[draft("A", "p1")], cover_photo_ids=["elsewhere"]),  # cover not in it
        dict(chapters=[draft("A", "p1"), draft("B", "p1")], cover_photo_ids=[]),  # same photo twice
    ]
    for call in bad_calls:
        with pytest.raises(InvalidRequest):
            service.create_complete("goa", "Goa", status=Status.PUBLISHED, **call)  # type: ignore[arg-type]
        assert fake_uow.store.collections == {} and fake_uow.store.chapters == {}
        assert photo_chapter(fake_uow, "p1") is None


def test_a_failed_save_leaves_nothing_behind(
    service: CollectionService, fake_uow: FakeUnitOfWork
) -> None:
    add_photos(fake_uow, "p1")
    fake_uow.fail_next_commit(RuntimeError("database is down"))
    with pytest.raises(RuntimeError):
        service.create_complete(
            "goa",
            "Goa",
            chapters=[draft("A", "p1")],
            cover_photo_ids=["p1"],
            status=Status.PUBLISHED,
        )
    assert fake_uow.store.collections == {} and fake_uow.store.chapters == {}
    assert photo_chapter(fake_uow, "p1") is None


def test_a_complete_collection_still_needs_a_free_valid_slug(service: CollectionService) -> None:
    collection(service, "goa")
    with pytest.raises(Conflict):
        service.create_complete(
            "goa", "Again", chapters=[], cover_photo_ids=[], status=Status.DRAFT
        )
    with pytest.raises(InvalidRequest):
        service.create_complete(
            "Bad Slug", "x", chapters=[], cover_photo_ids=[], status=Status.DRAFT
        )


def test_building_a_collection_moves_photos_out_of_their_old_chapters_and_covers(
    service: CollectionService, fake_uow: FakeUnitOfWork
) -> None:
    add_photos(fake_uow, "p1")
    old = collection(service, "old")
    service.assign_photos(service.create_chapter(old.id).id, ["p1"])
    service.set_covers(old.id, ["p1"])

    service.create_complete(
        "new", "New", chapters=[draft("A", "p1")], cover_photo_ids=["p1"], status=Status.DRAFT
    )

    assert service.get_collection(old.id).cover_photo_ids == []
    assert [c.photo_ids for c in service.get_collection(old.id).chapters] == [[]]


# -- audit: recorded in the same transaction as the change --------------------------------


def test_every_collection_and_chapter_change_is_audited_with_the_ip(
    fake_uow: FakeUnitOfWork, clock: FakeClock
) -> None:
    add_photos(fake_uow, "p1", "p2")
    audited = CollectionService(lambda: fake_uow, AuditTrail(clock, "9.9.9.9"))

    col = audited.create_collection("goa", "Goa")
    audited.update_collection(col.id, CollectionPatch(title="Goa 2024"))
    audited.set_status(col.id, Status.PUBLISHED)
    audited.set_status(col.id, Status.DRAFT)
    first = audited.create_chapter(col.id, "A")
    second = audited.create_chapter(col.id, "B")
    audited.update_chapter(first.id, ChapterPatch(note="n"))
    audited.assign_photos(first.id, ["p1", "p2"])
    audited.reorder_photos(first.id, ["p2", "p1"])
    audited.set_covers(col.id, ["p1"])
    audited.remove_photo(first.id, "p2")
    audited.reorder_chapters(col.id, [second.id, first.id])
    audited.delete_chapter(second.id)
    audited.reorder_collections([col.id])
    audited.delete_collection(col.id)

    assert [(e.action, e.ip) for e in fake_uow.store.audit] == [
        ("collection.create", "9.9.9.9"),
        ("collection.update", "9.9.9.9"),
        ("collection.publish", "9.9.9.9"),
        ("collection.unpublish", "9.9.9.9"),
        ("chapter.create", "9.9.9.9"),
        ("chapter.create", "9.9.9.9"),
        ("chapter.update", "9.9.9.9"),
        ("chapter.assign_photos", "9.9.9.9"),
        ("chapter.reorder_photos", "9.9.9.9"),
        ("collection.covers", "9.9.9.9"),
        ("chapter.remove_photo", "9.9.9.9"),
        ("chapter.reorder", "9.9.9.9"),
        ("chapter.delete", "9.9.9.9"),
        ("collection.reorder", "9.9.9.9"),
        ("collection.delete", "9.9.9.9"),
    ]
    assert fake_uow.store.audit[0].target == col.id
    assert fake_uow.store.audit[10].target == f"{first.id}/p2"


def test_a_refused_change_leaves_no_audit_entry(fake_uow: FakeUnitOfWork, clock: FakeClock) -> None:
    audited = CollectionService(lambda: fake_uow, AuditTrail(clock))
    audited.create_collection("goa", "Goa")
    with pytest.raises(Conflict):
        audited.create_collection("goa", "Again")
    assert [e.action for e in fake_uow.store.audit] == ["collection.create"]


def test_without_a_trail_nothing_is_audited(
    service: CollectionService, fake_uow: FakeUnitOfWork
) -> None:
    collection(service)
    assert fake_uow.store.audit == []
